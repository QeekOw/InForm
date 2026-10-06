import hmac
import os
import secrets
import sys
from pathlib import Path
from urllib.parse import urlencode, urlsplit

# The inform package lives in the repository root (src/inform).
# Modules 2 & 3 are pure Pydantic models and deterministic calculations
# with lightweight dependencies, so adding the root src directory to sys.path
# allows direct importing without requiring a full editable package installation.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

# Loads backend/.env (DATABASE_URL, SESSION_SECRET, ...) for local dev; in
# deployment the real environment variables are set directly, and load_dotenv()
# is a no-op if the file doesn't exist.
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")

import uuid
from datetime import date, datetime, timezone
from typing import Any, Literal

from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse
from pydantic import AliasChoices, BaseModel, Field, field_validator, model_validator
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

# backend/ has no __init__.py, so this module is imported two different ways
# depending on the caller: as top-level `main` (uvicorn, run from backend/,
# per backend/README.md) or as `backend.main` (pytest, run from the repo
# root, importing `from backend.main import app`). A plain `from auth import
# ...` / `from db... import ...` only resolves in the first case; a plain
# `from .auth import ...` only resolves in the second. Without a shared
# package identity, auth.py's own module-level state (and, more importantly,
# get_db's identity for FastAPI's dependency-override lookup in tests) would
# silently duplicate between the two import paths. try/except ImportError
# picks whichever form matches how *this* module itself was imported, so
# every module in backend/ ends up sharing one identity either way.
try:
    from .auth import (
        SESSION_COOKIE_NAME,
        create_session_token,
        get_current_account,
        hash_password,
        verify_password,
    )
    from .db.models import Account, Scan
    from .db.session import get_db
    from .google_oauth import (
        GOOGLE_AUTHORIZATION_ENDPOINT,
        GoogleOAuthError,
        GoogleOAuthSettings,
        exchange_authorization_code,
        verify_identity_token,
    )
except ImportError:
    from auth import (
        SESSION_COOKIE_NAME,
        create_session_token,
        get_current_account,
        hash_password,
        verify_password,
    )
    from db.models import Account, Scan
    from db.session import get_db
    from google_oauth import (
        GOOGLE_AUTHORIZATION_ENDPOINT,
        GoogleOAuthError,
        GoogleOAuthSettings,
        exchange_authorization_code,
        verify_identity_token,
    )

from inform.corrections import (
    CrossCheckFlaggedError,
    UnreadFieldsError,
    UnresolvedFlaggedFieldsError,
    apply_corrections,
)
from inform.exercise import ExercisePlan
from inform.exercise_filter import recommend_exercises
from inform.exercise_pool import DEFAULT_EXERCISE_POOL
from inform.extract import Engine, default_engine
from inform.inbody import InBodyExtraction, InBodyPayload, PartialInBody
from inform.master import DailyPlan, MasterPayload
from inform.nutrition import NutritionTargets
from inform.nutrition_engine import compute_targets
from inform.reads import read_manager
from inform.samples import (
    ExtractionItem,
    load_extractions,
    load_manifest,
)
from inform.synthesis.generate import OpenAIClientProtocol, synthesize_plan
from inform.synthesis.validate import generate_fallback_plan
from inform.user import UserProfile

app = FastAPI(title="InForm API")

# Accounts & History (issue #41) uses a cross-site session cookie, which
# browsers only send with allow_credentials=True paired with an explicit
# origin list — never a wildcard, which is refused outright once credentials
# are involved. ALLOWED_ORIGINS is a comma-separated env var; the local dev
# default covers `npm run dev`'s port, and the deployed Vercel origin is
# added via the real environment variable in production.
_allowed_origins_env = os.environ.get("ALLOWED_ORIGINS")
if _allowed_origins_env:
    _allowed_origins = [origin.strip() for origin in _allowed_origins_env.split(",") if origin.strip()]
else:
    _allowed_origins = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1|.*\.trycloudflare\.com|.*\.loca\.lt|.*\.devtunnels\.ms)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


@app.get("/")
def root() -> dict[str, str]:
    return {
        "service": "inform-api",
        "status": "ok",
        "docs_url": "/docs",
        "health_url": "/health",
    }


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "inform-api"}


# --- Accounts (issue #41) ---------------------------------------------------

# A tolerant but not-network-checking shape check: no DNS/deliverability
# lookups (which would make tests slow/flaky and add a network dependency for
# something issue #41 asks to keep as small as credible). Rejects the obvious
# typos (no "@", no domain) that a person would want caught before submitting.
_EMAIL_PATTERN = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"

# Plausibility bounds for the optional profile defaults. The frontend checks
# these too, for an immediate answer; these are the ones that actually decide,
# since a form check is only a convenience.
_MIN_AGE = 13
_MAX_AGE = 100
# Height is stored for display only and never reaches a calculation, so this is
# just a typo gate ("17" cm, "1780" cm) rather than a clinical range.
_MIN_HEIGHT_CM = 50.0
_MAX_HEIGHT_CM = 260.0
_MAX_NAME_LENGTH = 80
_MIN_PASSWORD_LENGTH = 8
# Spans the five activity levels the UI offers (1.2 sedentary to 1.9 extremely
# active), with a little slack either side.
_MIN_ACTIVITY_MULTIPLIER = 1.0
_MAX_ACTIVITY_MULTIPLIER = 2.5


def _age_on(birth_date: date, today: date | None = None) -> int:
    """Completed years between birth_date and today."""
    now = today or date.today()
    had_birthday_this_year = (now.month, now.day) >= (birth_date.month, birth_date.day)
    return now.year - birth_date.year - (0 if had_birthday_this_year else 1)


class AccountProfileDefaults(BaseModel):
    """Profile values stored on an Account purely to pre-fill a form.

    Never the source of truth for any past plan — a Scan's own frozen `profile`
    snapshot is (issue #42). Every field is optional: the anonymous flow works
    end to end with none of this, and signing up does not require any of it.
    """

    date_of_birth: date | None = None
    # Display only. Nothing in the pipeline consumes height, and no BMI or other
    # height-derived clinical metric is computed from it.
    height_cm: float | None = None
    default_biological_sex: Literal["male", "female"] | None = None
    default_activity_multiplier: float | None = None
    default_fitness_goal: Literal["hypertrophy", "fat_loss"] | None = None
    # Display only (dashboard greeting, profile page); never used by the pipeline.
    name: str | None = None

    @field_validator("name")
    @classmethod
    def _tidy_name(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = " ".join(v.split())
        if not v:
            return None
        if len(v) > _MAX_NAME_LENGTH:
            raise ValueError(f"Keep your name under {_MAX_NAME_LENGTH} characters.")
        return v

    @field_validator("date_of_birth")
    @classmethod
    def _plausible_age(cls, v: date | None) -> date | None:
        if v is None:
            return v
        age = _age_on(v)
        if age < _MIN_AGE or age > _MAX_AGE:
            raise ValueError(
                f"Enter a date of birth that makes you between {_MIN_AGE} and {_MAX_AGE}."
            )
        return v

    @field_validator("height_cm")
    @classmethod
    def _plausible_height(cls, v: float | None) -> float | None:
        if v is None:
            return v
        if not _MIN_HEIGHT_CM <= v <= _MAX_HEIGHT_CM:
            raise ValueError(
                f"Enter a height between {_MIN_HEIGHT_CM:.0f} and {_MAX_HEIGHT_CM:.0f} cm."
            )
        return v

    @field_validator("default_activity_multiplier")
    @classmethod
    def _plausible_activity(cls, v: float | None) -> float | None:
        if v is None:
            return v
        if not _MIN_ACTIVITY_MULTIPLIER <= v <= _MAX_ACTIVITY_MULTIPLIER:
            raise ValueError("Choose one of the listed activity levels.")
        return v


class SignupRequest(AccountProfileDefaults):
    email: str
    password: str

    @field_validator("email")
    @classmethod
    def _valid_email_shape(cls, v: str) -> str:
        import re

        if not re.match(_EMAIL_PATTERN, v):
            raise ValueError("Enter a valid email address.")
        return v.strip().lower()

    @field_validator("password")
    @classmethod
    def _password_min_length(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters.")
        return v


class LoginRequest(BaseModel):
    email: str
    password: str

    @field_validator("email")
    @classmethod
    def _normalize_email(cls, v: str) -> str:
        return v.strip().lower()


class AccountResponse(BaseModel):
    """What an Account looks like to its owner.

    Inherits the profile defaults so the sign-up form's values come straight back
    and can pre-fill the next Scan (Requirement 3.2). `password_hash` and
    `google_sub` are deliberately absent: an explicit field list, so a new column
    on the model cannot start being returned by accident.
    """

    id: uuid.UUID
    email: str
    created_at: datetime

    date_of_birth: date | None = None
    height_cm: float | None = None
    default_biological_sex: str | None = None
    default_activity_multiplier: float | None = None
    default_fitness_goal: str | None = None
    name: str | None = None
    token: str | None = None

    model_config = {"from_attributes": True}


# Cookie lifetime mirrors the session token's own expiry (backend/auth.py) so
# the browser doesn't keep sending a cookie the server would reject anyway.
_SESSION_COOKIE_MAX_AGE_SECONDS = 30 * 24 * 60 * 60
_GOOGLE_FLOW_COOKIE_MAX_AGE_SECONDS = 10 * 60
_GOOGLE_STATE_COOKIE = "inform_google_state"
_GOOGLE_REDIRECT_COOKIE = "inform_google_redirect"

# Secure + SameSite=None is required for the cross-site cookie to work at all
# once the frontend (Vercel) and backend (Render) are on different origins in
# production (Task 5). Both are refused by browsers over plain http://, which
# is what local dev (uvicorn on localhost, TestClient's "testserver") uses —
# so this is gated on an explicit env var rather than always on, matching the
# accounts-and-history design's cross-site cookie wiring plan. Defaults to
# the secure production behavior; local dev opts out explicitly.
_COOKIES_OVER_HTTP = os.environ.get("ALLOW_INSECURE_COOKIES", "false").lower() == "true"


def _set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        max_age=_SESSION_COOKIE_MAX_AGE_SECONDS,
        httponly=True,
        secure=not _COOKIES_OVER_HTTP,
        samesite="lax" if _COOKIES_OVER_HTTP else "none",
        path="/",
    )


def _google_frontend_url(status: str, redirect_path: str) -> str:
    configured_frontend = os.environ.get("FRONTEND_URL")
    if configured_frontend:
        frontend_origin = configured_frontend.rstrip("/")
    elif _allowed_origins:
        frontend_origin = next(
            (
                origin.rstrip("/")
                for origin in _allowed_origins
                if urlsplit(origin).hostname not in {"localhost", "127.0.0.1"}
            ),
            _allowed_origins[0].rstrip("/"),
        )
    else:
        frontend_origin = "http://localhost:3000"
    return f"{frontend_origin}/sign-in?{urlencode({'google': status, 'redirect': redirect_path})}"


def _safe_google_redirect(value: str | None) -> str | None:
    if value is None:
        return "/dashboard"
    parsed = urlsplit(value)
    if (
        not value.startswith("/")
        or value.startswith("//")
        or "\\" in value
        or parsed.scheme
        or parsed.netloc
        or any(ord(character) < 32 for character in value)
    ):
        return None
    return value


def _clear_google_flow_cookies(response: Response) -> None:
    for cookie_name in (_GOOGLE_STATE_COOKIE, _GOOGLE_REDIRECT_COOKIE):
        response.delete_cookie(
            key=cookie_name,
            path="/auth/google",
            secure=not _COOKIES_OVER_HTTP,
            httponly=True,
            samesite="lax",
        )


def _google_result_redirect(status: str, redirect_path: str) -> RedirectResponse:
    response = RedirectResponse(
        _google_frontend_url(status, redirect_path),
        status_code=302,
        headers={"Cache-Control": "no-store"},
    )
    _clear_google_flow_cookies(response)
    return response


@app.get("/auth/google/start")
def google_sign_in_start(redirect: str | None = Query(default=None)) -> Response:
    """Start Google OAuth, or return to sign-in with a clear setup message."""
    redirect_path = _safe_google_redirect(redirect)
    if redirect_path is None:
        raise HTTPException(status_code=400, detail="Invalid sign-in redirect.")

    settings = GoogleOAuthSettings.from_environment()
    if settings is None:
        return _google_result_redirect("unavailable", redirect_path)

    state = secrets.token_urlsafe(32)
    authorization_params = {
        "client_id": settings.client_id,
        "redirect_uri": settings.redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "prompt": "select_account",
    }
    authorization_url = f"{GOOGLE_AUTHORIZATION_ENDPOINT}?{urlencode(authorization_params)}"
    response = RedirectResponse(authorization_url, status_code=302)
    for cookie_name, value in (
        (_GOOGLE_STATE_COOKIE, state),
        (_GOOGLE_REDIRECT_COOKIE, redirect_path),
    ):
        response.set_cookie(
            key=cookie_name,
            value=value,
            max_age=_GOOGLE_FLOW_COOKIE_MAX_AGE_SECONDS,
            httponly=True,
            secure=not _COOKIES_OVER_HTTP,
            samesite="lax",
            path="/auth/google",
        )
    return response


@app.get("/auth/google/callback")
def google_sign_in_callback(
    request: Request,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    db: Session = Depends(get_db),
) -> Response:
    """Verify Google's response, resolve the account, and issue a normal session."""
    redirect_path = _safe_google_redirect(request.cookies.get(_GOOGLE_REDIRECT_COOKIE))
    if redirect_path is None:
        redirect_path = "/dashboard"
    cookie_state = request.cookies.get(_GOOGLE_STATE_COOKIE)
    if (
        not state
        or not state.isascii()
        or not cookie_state
        or not hmac.compare_digest(state, cookie_state)
    ):
        return _google_result_redirect("error", redirect_path)

    if error:
        return _google_result_redirect(
            "cancelled" if error == "access_denied" else "error",
            redirect_path,
        )
    if not code:
        return _google_result_redirect("error", redirect_path)

    settings = GoogleOAuthSettings.from_environment()
    if settings is None:
        return _google_result_redirect("unavailable", redirect_path)

    try:
        identity_token = exchange_authorization_code(code, settings)
        claims = verify_identity_token(identity_token, settings.client_id)
    except GoogleOAuthError:
        return _google_result_redirect("error", redirect_path)

    google_sub = claims.get("sub")
    email = claims.get("email")
    if (
        not isinstance(google_sub, str)
        or not google_sub
        or not isinstance(email, str)
        or not email.strip()
        or claims.get("email_verified") is not True
    ):
        return _google_result_redirect("error", redirect_path)

    normalized_email = email.strip().lower()
    account_by_google = db.query(Account).filter_by(google_sub=google_sub).one_or_none()
    account_by_email = db.query(Account).filter_by(email=normalized_email).one_or_none()
    if account_by_google is not None:
        if account_by_email is not None and account_by_email.id != account_by_google.id:
            return _google_result_redirect("error", redirect_path)
        account = account_by_google
        account.email = normalized_email
    elif account_by_email is not None:
        if account_by_email.google_sub not in (None, google_sub):
            return _google_result_redirect("error", redirect_path)
        account = account_by_email
        account.google_sub = google_sub
    else:
        account = Account(email=normalized_email, google_sub=google_sub)
        db.add(account)

    google_name = claims.get("name")
    if account.name is None and isinstance(google_name, str):
        normalized_name = " ".join(google_name.split())
        if normalized_name and len(normalized_name) <= _MAX_NAME_LENGTH:
            account.name = normalized_name
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        return _google_result_redirect("error", redirect_path)

    token = create_session_token(account.id)
    response = RedirectResponse(
        _google_frontend_url("success", redirect_path),
        status_code=302,
        headers={"Cache-Control": "no-store"},
    )
    _set_session_cookie(response, token)
    _clear_google_flow_cookies(response)
    return response


@app.post("/auth/signup", response_model=AccountResponse, status_code=201)
def signup(request: SignupRequest, response: Response, db: Session = Depends(get_db)) -> AccountResponse:
    """Create an Account and sign in immediately (issue #41).

    A duplicate email returns 409 without touching what the person typed —
    the frontend's responsibility is to leave the form filled in on failure.
    """
    account = Account(
        email=request.email,
        password_hash=hash_password(request.password),
        # Pre-fill defaults, collected in the same single form (Requirement 3.1)
        # so nothing has to be asked twice. None for anything left blank.
        date_of_birth=request.date_of_birth,
        height_cm=request.height_cm,
        default_biological_sex=request.default_biological_sex,
        default_activity_multiplier=request.default_activity_multiplier,
        default_fitness_goal=request.default_fitness_goal,
        name=request.name,
    )
    db.add(account)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="An account with this email already exists.")

    token = create_session_token(account.id)
    _set_session_cookie(response, token)
    res = AccountResponse.model_validate(account)
    res.token = token
    return res


# Identical message for "no such email" and "wrong password" so a caller
# can't use the error to enumerate registered emails (issue #41 AC3).
_INVALID_CREDENTIALS_MESSAGE = "Incorrect email or password."


@app.post("/auth/login", response_model=AccountResponse)
def login(request: LoginRequest, response: Response, db: Session = Depends(get_db)) -> AccountResponse:
    """Sign in an existing Account (issue #41)."""
    account = db.query(Account).filter_by(email=request.email).one_or_none()
    if (
        account is None
        or account.password_hash is None
        or not verify_password(request.password, account.password_hash)
    ):
        raise HTTPException(status_code=401, detail=_INVALID_CREDENTIALS_MESSAGE)

    token = create_session_token(account.id)
    _set_session_cookie(response, token)
    res = AccountResponse.model_validate(account)
    res.token = token
    return res


@app.post("/auth/logout")
def logout(response: Response) -> dict[str, str]:
    """Sign out by clearing the session cookie (issue #41 AC5)."""
    response.delete_cookie(key=SESSION_COOKIE_NAME, path="/")
    return {"status": "ok"}


@app.get("/auth/me", response_model=AccountResponse)
def me(request: Request, account: Account = Depends(get_current_account)) -> AccountResponse:
    """Return the signed-in person's Account, or 401 if not signed in."""
    res = AccountResponse.model_validate(account)
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        res.token = auth_header[len("Bearer ") :].strip()
    else:
        cookie_token = request.cookies.get(SESSION_COOKIE_NAME)
        if cookie_token:
            res.token = cookie_token
    return res


class UpdateProfileRequest(AccountProfileDefaults):
    pass


@app.patch("/auth/me", response_model=AccountResponse)
@app.patch("/account/profile", response_model=AccountResponse)
def update_profile(
    request: UpdateProfileRequest,
    account: Account = Depends(get_current_account),
    db: Session = Depends(get_db),
) -> AccountResponse:
    """Update the signed-in person's profile defaults."""
    if request.date_of_birth is not None:
        account.date_of_birth = request.date_of_birth
    if request.height_cm is not None:
        account.height_cm = request.height_cm
    if request.default_biological_sex is not None:
        account.default_biological_sex = request.default_biological_sex
    if request.default_activity_multiplier is not None:
        account.default_activity_multiplier = request.default_activity_multiplier
    if request.default_fitness_goal is not None:
        account.default_fitness_goal = request.default_fitness_goal
    if request.name is not None:
        account.name = request.name
    db.commit()
    db.refresh(account)
    return AccountResponse.model_validate(account)


class UpdateCredentialsRequest(BaseModel):
    """Change the sign-in email and/or password.

    The current password is always required, so a session left open on a
    shared device can't be used to take the account over.
    """

    current_password: str
    new_email: str | None = None
    new_password: str | None = None

    @field_validator("new_email")
    @classmethod
    def _valid_new_email(cls, v: str | None) -> str | None:
        if v is None:
            return v
        import re

        v = v.strip().lower()
        if not re.match(_EMAIL_PATTERN, v):
            raise ValueError("Enter a valid email address.")
        return v

    @field_validator("new_password")
    @classmethod
    def _new_password_min_length(cls, v: str | None) -> str | None:
        if v is None:
            return v
        if len(v) < _MIN_PASSWORD_LENGTH:
            raise ValueError(f"Password must be at least {_MIN_PASSWORD_LENGTH} characters.")
        return v

    @model_validator(mode="after")
    def _something_to_change(self) -> "UpdateCredentialsRequest":
        if self.new_email is None and self.new_password is None:
            raise ValueError("Provide a new email, a new password, or both.")
        return self


@app.patch("/auth/credentials", response_model=AccountResponse)
def update_credentials(
    request: UpdateCredentialsRequest,
    account: Account = Depends(get_current_account),
    db: Session = Depends(get_db),
) -> AccountResponse:
    """Change the signed-in person's email and/or password (current password required)."""
    if account.password_hash is None or not verify_password(
        request.current_password, account.password_hash
    ):
        raise HTTPException(status_code=403, detail="Your current password is incorrect.")

    if request.new_email is not None and request.new_email != account.email:
        account.email = request.new_email
    if request.new_password is not None:
        account.password_hash = hash_password(request.new_password)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="An account with this email already exists.")
    db.refresh(account)
    return AccountResponse.model_validate(account)


@app.delete("/account", status_code=204)
def delete_account(
    response: Response,
    account: Account = Depends(get_current_account),
    db: Session = Depends(get_db),
) -> None:
    """Permanently delete the signed-in person's Account and every Scan
    belonging to it (issue #44). No soft delete, no retained analytics copy
    (ADR-0011) — the FK's ondelete="CASCADE" (backend/db/models.py) removes
    every Scan in the same transaction as the Account row itself; nothing is
    flagged, archived, or copied elsewhere first.

    The frontend must plainly state what this removes before the person
    confirms (issue #44 AC4) — that confirmation step lives in the UI, not
    here; this endpoint performs the deletion the moment it's called, with no
    further confirmation step of its own.
    """
    db.delete(account)
    db.commit()
    # The just-deleted account's session cookie can no longer authenticate
    # anything (the account row is gone), but clearing it too means a stale
    # browser session doesn't even try.
    response.delete_cookie(key=SESSION_COOKIE_NAME, path="/")


class SampleGalleryItem(BaseModel):
    id: str
    name: str
    provenance: Literal["synthetic", "real"]
    source_device: Literal["inbody_270", "inbody_570"] | None = None
    image_url: str
    description: str


@app.get("/samples", response_model=list[SampleGalleryItem])
@app.get("/api/samples", response_model=list[SampleGalleryItem])
def list_samples() -> list[SampleGalleryItem]:
    """Return all sample sheets in the gallery manifest with provenance labels."""
    manifest = load_manifest()
    return [
        SampleGalleryItem(
            id=s.id,
            name=s.name,
            provenance=s.provenance,
            source_device=s.source_device,
            image_url=f"/samples/{s.id}/image",
            description=s.description,
        )
        for s in manifest.samples
    ]


@app.get("/samples/{sample_id}", response_model=ExtractionItem)
@app.get("/api/samples/{sample_id}", response_model=ExtractionItem)
def get_sample_extraction(sample_id: str) -> ExtractionItem:
    """Return precomputed extraction for a sample sheet instantly without running OCR."""
    extractions_artifact = load_extractions()
    if sample_id not in extractions_artifact.extractions:
        raise HTTPException(status_code=404, detail=f"Sample '{sample_id}' not found")
    return extractions_artifact.extractions[sample_id]


@app.get("/samples/{sample_id}/image")
@app.get("/api/samples/{sample_id}/image")
def get_sample_image(sample_id: str):
    """Serve the thumbnail/photo of a sample sheet from the repository."""
    manifest = load_manifest()
    sample = next((s for s in manifest.samples if s.id == sample_id), None)
    if sample is None:
        raise HTTPException(status_code=404, detail=f"Sample '{sample_id}' not found")

    img_path = Path(sample.image_path)
    if not img_path.is_absolute():
        repo_root = Path(__file__).resolve().parent.parent
        img_path = repo_root / img_path

    if not img_path.exists():
        raise HTTPException(status_code=404, detail="Sample image not found on disk")

    return FileResponse(img_path, media_type="image/png")


def get_engine() -> Engine | None:
    """Module 1's runtime engine; None lets extract_sheet_for_sample use default_engine().

    A FastAPI dependency so tests can inject a stub engine.
    """
    return None


class CapabilitiesResponse(BaseModel):
    live_read_available: bool


# The probe's answer, resolved once per process. None means "not yet asked".
#
# Probing means actually constructing the engine, which on a server that *has*
# the checkpoint loads ~776 MB (ADR-0010) — so this is asked once and the answer
# kept, rather than re-probed per request. Resolved lazily on the first call so
# importing this module (every test run, every `uvicorn` start) never pays for it.
_live_read_probe: bool | None = None


def get_live_read_available() -> bool:
    """Whether this server can run the extraction model on demand.

    A FastAPI dependency so tests can assert both answers without needing a
    776 MB checkpoint on disk to get the True case.
    """
    global _live_read_probe
    if _live_read_probe is None:
        ckpt = os.environ.get("INFORM_DONUT_CKPT", "models/donut-270-v9")
        if Path(ckpt).exists():
            _live_read_probe = True
        else:
            try:
                default_engine()
                _live_read_probe = True
            except Exception:
                _live_read_probe = False
    return _live_read_probe


@app.get("/capabilities", response_model=CapabilitiesResponse)
@app.get("/api/capabilities", response_model=CapabilitiesResponse)
def capabilities(
    live_read_available: bool = Depends(get_live_read_available),
) -> CapabilitiesResponse:
    """Report what this deployment can actually do, so the UI can stop offering
    what it cannot (Requirement 1.6).

    The sample gallery's instant path does not depend on this: those reads were
    computed ahead of time and are served from a stored file, so they work with
    no checkpoint present (Requirement 1.1).
    """
    return CapabilitiesResponse(live_read_available=live_read_available)


class CreateReadRequest(BaseModel):
    sample_id: str | None = None
    image_data: str | None = None
    live: bool = False

    @model_validator(mode="after")
    def _validate_source(self) -> "CreateReadRequest":
        has_sample = self.sample_id is not None
        has_image = self.image_data is not None
        if has_sample == has_image:
            raise ValueError("Provide either sample_id or image_data, not both or neither")
        return self


class ReadJobResponse(BaseModel):
    read_id: str
    sample_id: str | None
    live: bool
    status: Literal["pending", "complete", "refused"]
    progress: float
    message: str
    extraction: ExtractionItem | None = None


@app.post("/reads", response_model=ReadJobResponse)
@app.post("/api/reads", response_model=ReadJobResponse)
def create_read(
    request: CreateReadRequest,
    engine: Engine | None = Depends(get_engine),
) -> ReadJobResponse:
    """Start reading a sheet, returning immediately with a read job identifier."""
    try:
        job = read_manager.create_read(
            sample_id=request.sample_id,
            image_data=request.image_data,
            live=request.live,
            engine_factory=lambda: engine,
        )
        return ReadJobResponse(**job.to_dict())
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@app.get("/reads/{read_id}", response_model=ReadJobResponse)
@app.get("/api/reads/{read_id}", response_model=ReadJobResponse)
async def poll_read(
    read_id: str,
    timeout: float = 10.0,
) -> ReadJobResponse:
    """Long poll a read job with a timeout surviving host network limits."""
    clamped_timeout = max(0.0, min(timeout, 25.0))
    try:
        job = await read_manager.poll(read_id, timeout=clamped_timeout)
        return ReadJobResponse(**job.to_dict())
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


class PlanRequest(BaseModel):
    user: UserProfile
    # A Sample sheet whose stored read the server plans from, with optional human corrections
    sample_id: str | None = None
    # A Read job identifier (stored or live read)
    read_id: str | None = None
    # An explicit measured read with optional human corrections
    measured: PartialInBody | None = None
    # Corrections typed by a person (recorded alongside measured fields, never merged into them)
    corrections: dict[str, Any] | None = None
    # Flagged fields confirmed unchanged by a person
    confirmations: list[str] = Field(
        default_factory=list,
        validation_alias=AliasChoices("confirmations", "confirmed_fields"),
    )
    # Stored or extracted flagged fields for measured/inbody reads
    initial_flagged: list[str] | None = None
    # Direct InBody reading (retained for backward compatibility)
    inbody: InBodyPayload | None = None

    @model_validator(mode="after")
    def _validate_source(self) -> "PlanRequest":
        sources = [s is not None for s in (self.sample_id, self.read_id, self.measured, self.inbody)]
        if sum(sources) != 1:
            raise ValueError("Provide exactly one reading source (sample_id, read_id, measured, or inbody)")
        return self


def get_llm_client() -> OpenAIClientProtocol | None:
    """Module 4's LLM client; None lets synthesize_plan build the default one.

    A FastAPI dependency so tests can inject a fake client."""
    return None


def _apply_plan_corrections(
    base: PartialInBody,
    corrections: dict[str, Any] | None,
    confirmations: list[str] | None = None,
    source_device: Literal["inbody_270", "inbody_570"] | None = None,
    initial_flagged: list[str] | None = None,
) -> tuple[InBodyPayload, list[str], list[str]]:
    """Deduplicated helper to validate and apply corrections and confirmations, mapping domain exceptions to HTTP responses."""
    try:
        return apply_corrections(
            base,
            corrections or {},
            source_device=source_device,
            confirmations=confirmations,
            initial_flagged=initial_flagged,
        )
    except UnreadFieldsError as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "message": "Building a plan is impossible while a required field remains unread.",
                "unread": exc.unread_fields,
            },
        )
    except CrossCheckFlaggedError as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "message": "Building a plan is impossible while a flagged field is unresolved.",
                "unread": [],
                "flagged": exc.flagged_fields,
            },
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


def _require_usable_extraction(extraction: ExtractionItem | None) -> tuple[PartialInBody, str | None, list[str]]:
    """Validate extraction is not refused and has data, returning (measured, source_device, initial_flagged)."""
    if extraction is None or extraction.data is None or extraction.status == "refused":
        message = (
            extraction.message
            if extraction and extraction.message
            else (
                "This image does not appear to be an InBody result sheet. Please upload a clear photo of your InBody 270 or 570 sheet."
                if extraction and extraction.error == "not_an_inbody_sheet"
                else "This sheet was refused (not an InBody sheet or nothing readable came back)."
            )
        )
        raise HTTPException(
            status_code=409,
            detail={
                "message": message,
                "unread": extraction.unread if extraction else [],
                "flagged": extraction.flagged if extraction else [],
                "error": extraction.error if extraction else None,
            },
        )
    return extraction.data, extraction.data.source_device, extraction.flagged


def _inbody_for_plan(request: PlanRequest) -> tuple[InBodyPayload, PartialInBody, list[str], list[str]]:
    """Resolve reading source into (effective_payload, base_measured, corrected_field_keys, confirmed_field_keys)."""
    if request.sample_id is not None:
        extraction = load_extractions().extractions.get(request.sample_id)
        if extraction is None:
            raise HTTPException(status_code=404, detail=f"Sample '{request.sample_id}' not found")
        base_measured, source_device, initial_flagged = _require_usable_extraction(extraction)

    elif request.read_id is not None:
        job = read_manager.get(request.read_id)
        if job is None:
            raise HTTPException(status_code=404, detail=f"Read '{request.read_id}' not found")

        if job.status == "pending":
            raise HTTPException(
                status_code=409,
                detail="Building a plan is impossible while the read is still in progress.",
            )
        base_measured, source_device, initial_flagged = _require_usable_extraction(job.extraction)

    elif request.measured is not None:
        base_measured = request.measured
        source_device = base_measured.source_device
        initial_flagged = request.initial_flagged

    elif request.inbody is not None:
        base_measured = PartialInBody(**request.inbody.model_dump())
        source_device = request.inbody.source_device
        initial_flagged = request.initial_flagged

    else:
        raise HTTPException(status_code=422, detail="No reading source provided")

    payload, corrected, confirmed = _apply_plan_corrections(
        base_measured,
        request.corrections,
        confirmations=request.confirmations,
        source_device=source_device,
        initial_flagged=initial_flagged,
    )
    return payload, base_measured, corrected, confirmed


class PlanResponse(BaseModel):
    # The deterministic numbers (Modules 2 & 3) alongside the narrative
    # (Module 4), not folded into it — "deterministic numbers, generative
    # prose only" means the UI should show the audited figures directly
    # rather than trust them only as restated inside the generated text.
    nutrition: NutritionTargets
    exercises: ExercisePlan
    narrative_text: str
    # "fallback" when Module 4 dropped the LLM's text (unavailable, or it
    # mutated a number) and returned the plain deterministic plan instead.
    narrative_source: Literal["generated", "fallback"]
    # Recorded alongside measured fields, never merged into them
    measured: PartialInBody | None = None
    corrected_fields: list[str] = Field(default_factory=list)
    confirmed_fields: list[str] = Field(default_factory=list)


def _compute_plan(
    request: PlanRequest,
    llm_client: OpenAIClientProtocol | None,
) -> tuple[InBodyPayload, PartialInBody, list[str], list[str], NutritionTargets, ExercisePlan, DailyPlan]:
    """Shared Modules 2->3->4 computation behind both /plan and /scans (issue
    #42 reuses this rather than re-implementing plan computation) — resolves
    the reading source, then runs nutrition, exercises, and narrative
    synthesis exactly as /plan does.
    """
    inbody, base_measured, corrected_fields, confirmed_fields = _inbody_for_plan(request)
    nutrition = compute_targets(request.user, inbody)
    exercises = recommend_exercises(
        request.user,
        inbody,
        DEFAULT_EXERCISE_POOL,
        set(confirmed_fields) | set(corrected_fields),
    )
    master = MasterPayload(
        user=request.user,
        inbody=inbody,
        nutrition=nutrition,
        exercises=exercises,
    )
    daily_plan = synthesize_plan(master, client=llm_client)
    return inbody, base_measured, corrected_fields, confirmed_fields, nutrition, exercises, daily_plan


@app.post("/plan")
def plan(
    request: PlanRequest,
    llm_client: OpenAIClientProtocol | None = Depends(get_llm_client),
) -> PlanResponse:
    """Modules 2 -> 3 -> 4, given a Sample sheet's stored read or a complete reading.

    No OCR (Module 1) here. Module 4 falls back to a deterministic plan when
    the LLM is unavailable or mutates a number.

    Privacy & ADR-0005: When OPENAI_API_KEY is unset, Module 4 automatically
    falls back to a deterministic, local template-based plan narrative so no
    data leaves the host environment. If OPENAI_API_KEY is configured, cloud
    synthesis is used for POC / development testing with consented or synthetic
    data only. Real patient health data must never be sent to external cloud APIs.
    """
    inbody, base_measured, corrected_fields, confirmed_fields, nutrition, exercises, daily_plan = _compute_plan(
        request, llm_client
    )
    master = MasterPayload(user=request.user, inbody=inbody, nutrition=nutrition, exercises=exercises)
    return PlanResponse(
        nutrition=nutrition,
        exercises=exercises,
        narrative_text=daily_plan.narrative_text,
        narrative_source="fallback" if daily_plan == generate_fallback_plan(master) else "generated",
        measured=base_measured,
        corrected_fields=corrected_fields,
        confirmed_fields=confirmed_fields,
    )


# --- Scans & History (issue #42) -------------------------------------------


class SaveScanRequest(PlanRequest):
    """Identical shape to PlanRequest — saving a Scan freezes exactly what
    would otherwise just be returned by /plan, plus which Account it belongs
    to (from the session, not the request body)."""


class ScanDetail(BaseModel):
    id: uuid.UUID
    created_at: datetime
    source_device: str | None
    sample_id: str | None
    profile: UserProfile
    measured: PartialInBody
    effective_inbody: InBodyPayload
    corrected_fields: list[str]
    confirmed_fields: list[str]
    nutrition: NutritionTargets
    exercises: ExercisePlan
    narrative_text: str
    narrative_source: Literal["generated", "fallback"]
    scan_fingerprint: str | None = None

    model_config = {"from_attributes": True}


class ScanSummary(BaseModel):
    """One row per Scan: enough to plot a trend and label a history entry.

    Widened past the original 2-3 headline numbers (issue #42 AC4) to carry the
    metrics the Dashboard charts (Requirement 6.2). Widening this rather than
    adding a time-series endpoint because `GET /scans` already returns one dated
    row per Scan, so the charts and the history list come from one request.

    Every value is read straight out of the Scan's own frozen JSONB. Nothing is
    recomputed here, which is what keeps a past Scan's numbers identical to what
    they were when it was saved (issue #42).
    """

    id: uuid.UUID
    created_at: datetime
    target_calories_kcal: float
    weight_kg: float
    percent_body_fat: float
    lean_body_mass_kg: float
    skeletal_muscle_mass_kg: float
    bmr_kcal: float
    has_corrections: bool
    sample_id: str | None = None
    scan_fingerprint: str | None = None


def _compute_scan_fingerprint(sample_id: str | None, inbody: dict | InBodyPayload) -> str:
    data = inbody.model_dump() if isinstance(inbody, BaseModel) else inbody
    weight = round(float(data.get("weight_kg", 0.0) or 0.0), 1)
    smm = round(float(data.get("skeletal_muscle_mass_kg", 0.0) or 0.0), 1)
    pbf = round(float(data.get("percent_body_fat", 0.0) or 0.0), 1)
    lbm = round(float(data.get("lean_body_mass_kg", 0.0) or 0.0), 1)
    source = sample_id or data.get("source_device") or "inbody"
    return f"{source}|{weight}|{smm}|{pbf}|{lbm}"


def _scan_to_summary(scan: Scan) -> ScanSummary:
    fingerprint = _compute_scan_fingerprint(scan.sample_id, scan.effective_inbody)
    return ScanSummary(
        id=scan.id,
        created_at=scan.created_at,
        target_calories_kcal=scan.nutrition["target_calories_kcal"],
        weight_kg=scan.effective_inbody["weight_kg"],
        percent_body_fat=scan.effective_inbody["percent_body_fat"],
        lean_body_mass_kg=scan.effective_inbody["lean_body_mass_kg"],
        skeletal_muscle_mass_kg=scan.effective_inbody["skeletal_muscle_mass_kg"],
        bmr_kcal=scan.nutrition["bmr_kcal"],
        has_corrections=len(scan.corrected_fields) > 0,
        sample_id=scan.sample_id,
        scan_fingerprint=fingerprint,
    )


@app.post("/scans", response_model=ScanDetail, status_code=201)
def save_scan(
    request: SaveScanRequest,
    account: Account = Depends(get_current_account),
    llm_client: OpenAIClientProtocol | None = Depends(get_llm_client),
    db: Session = Depends(get_db),
) -> ScanDetail:
    """Save a signed-in person's read as an immutable Scan (issue #42).

    Freezes the Profile, the effective InBody reading (measured plus any
    corrections/confirmations applied), and the produced Plan at this fixed
    point in time. Anonymous callers get 401 (get_current_account). No sheet
    image is ever part of this payload (ADR-0011) — SaveScanRequest carries
    the same reading-source shapes /plan does, none of which include one.
    """
    inbody, base_measured, corrected_fields, confirmed_fields, nutrition, exercises, daily_plan = _compute_plan(
        request, llm_client
    )
    master = MasterPayload(user=request.user, inbody=inbody, nutrition=nutrition, exercises=exercises)
    narrative_source = "fallback" if daily_plan == generate_fallback_plan(master) else "generated"

    scan = Scan(
        account_id=account.id,
        source_device=inbody.source_device,
        sample_id=request.sample_id,
        profile=request.user.model_dump(),
        measured=base_measured.model_dump(),
        effective_inbody=inbody.model_dump(),
        corrected_fields=corrected_fields,
        confirmed_fields=confirmed_fields,
        nutrition=nutrition.model_dump(),
        exercises=exercises.model_dump(),
        narrative_text=daily_plan.narrative_text,
        narrative_source=narrative_source,
    )
    db.add(scan)
    db.commit()

    fingerprint = _compute_scan_fingerprint(scan.sample_id, scan.effective_inbody)
    return ScanDetail(
        id=scan.id,
        created_at=scan.created_at,
        source_device=scan.source_device,
        sample_id=scan.sample_id,
        profile=request.user,
        measured=base_measured,
        effective_inbody=inbody,
        corrected_fields=corrected_fields,
        confirmed_fields=confirmed_fields,
        nutrition=nutrition,
        exercises=exercises,
        narrative_text=daily_plan.narrative_text,
        narrative_source=narrative_source,
        scan_fingerprint=fingerprint,
    )


def _scan_to_detail(scan: Scan) -> ScanDetail:
    fingerprint = _compute_scan_fingerprint(scan.sample_id, scan.effective_inbody)
    return ScanDetail(
        id=scan.id,
        created_at=scan.created_at,
        source_device=scan.source_device,
        sample_id=scan.sample_id,
        profile=UserProfile.model_validate(scan.profile),
        measured=PartialInBody.model_validate(scan.measured),
        effective_inbody=InBodyPayload.model_validate(scan.effective_inbody),
        corrected_fields=scan.corrected_fields,
        confirmed_fields=scan.confirmed_fields,
        nutrition=NutritionTargets.model_validate(scan.nutrition),
        exercises=ExercisePlan.model_validate(scan.exercises),
        narrative_text=scan.narrative_text,
        narrative_source=scan.narrative_source,
        scan_fingerprint=fingerprint,
    )


@app.get("/scans", response_model=list[ScanSummary])
def list_scans(
    account: Account = Depends(get_current_account),
    db: Session = Depends(get_db),
) -> list[ScanSummary]:
    """History, newest first (issue #42 AC4). Empty list for a brand-new
    Account — the frontend (Task 9) turns that into the empty-state invite
    (issue #41 AC6) rather than this endpoint doing so itself."""
    scans = (
        db.query(Scan)
        .filter_by(account_id=account.id)
        .order_by(Scan.created_at.desc())
        .all()
    )
    return [_scan_to_summary(scan) for scan in scans]


# --- Staleness (issue #43) ---------------------------------------------------

# The 30-day figure was flagged in issue #29 as not firmly settled — kept as
# a single named constant so changing it is the one-line change the issue
# anticipates, not a hunt through the codebase.
STALENESS_DAYS = 30


class CurrentPlanResponse(ScanDetail):
    age_days: int
    is_stale: bool


# Registered before /scans/{scan_id}: FastAPI matches routes in registration
# order, and a literal path ("current") must be tried before a path parameter
# that would otherwise capture the same segment.
@app.get("/scans/current", response_model=CurrentPlanResponse)
def get_current_scan(
    account: Account = Depends(get_current_account),
    db: Session = Depends(get_db),
) -> CurrentPlanResponse:
    """The most recent Scan, with its age and staleness computed server-side
    (issue #43) — the frontend never computes this itself. A stale plan is
    still returned in full: this endpoint never hides, expires, or recomputes
    it, only adds age_days/is_stale alongside the same ScanDetail fields
    GET /scans/{scan_id} already returns."""
    scan = (
        db.query(Scan)
        .filter_by(account_id=account.id)
        .order_by(Scan.created_at.desc())
        .first()
    )
    if scan is None:
        raise HTTPException(status_code=404, detail="No Scans yet.")

    scan_created_at = scan.created_at
    if scan_created_at.tzinfo is None:
        scan_created_at = scan_created_at.replace(tzinfo=timezone.utc)
    age = datetime.now(timezone.utc) - scan_created_at
    age_days = age.days

    detail = _scan_to_detail(scan)
    return CurrentPlanResponse(
        **detail.model_dump(),
        age_days=age_days,
        is_stale=age_days > STALENESS_DAYS,
    )


@app.get("/scans/{scan_id}", response_model=ScanDetail)
def get_scan(
    scan_id: uuid.UUID,
    account: Account = Depends(get_current_account),
    db: Session = Depends(get_db),
) -> ScanDetail:
    """A past Scan's full stored results (issue #42 AC5). 404 (not 403) for a
    Scan that exists but belongs to someone else, so the response never
    confirms the id exists at all."""
    scan = db.query(Scan).filter_by(id=scan_id, account_id=account.id).one_or_none()
    if scan is None:
        raise HTTPException(status_code=404, detail=f"Scan '{scan_id}' not found")
    return _scan_to_detail(scan)
