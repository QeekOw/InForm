"""Google OAuth configuration, code exchange, and ID-token verification."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

import requests
from google.auth.exceptions import GoogleAuthError
from google.auth.transport.requests import Request as GoogleRequest
from google.oauth2 import id_token

GOOGLE_AUTHORIZATION_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"


class GoogleOAuthError(Exception):
    """Raised when Google's OAuth exchange or identity verification fails."""


@dataclass(frozen=True)
class GoogleOAuthSettings:
    client_id: str
    client_secret: str
    redirect_uri: str

    @classmethod
    def from_environment(cls) -> GoogleOAuthSettings | None:
        client_id = os.environ.get("GOOGLE_CLIENT_ID", "").strip()
        client_secret = os.environ.get("GOOGLE_CLIENT_SECRET", "").strip()
        redirect_uri = os.environ.get("GOOGLE_REDIRECT_URI", "").strip()
        if not client_id or not client_secret or not redirect_uri:
            return None
        return cls(client_id, client_secret, redirect_uri)


def exchange_authorization_code(code: str, settings: GoogleOAuthSettings) -> str:
    """Exchange a short-lived authorization code for a Google ID token."""
    try:
        response = requests.post(
            GOOGLE_TOKEN_ENDPOINT,
            data={
                "code": code,
                "client_id": settings.client_id,
                "client_secret": settings.client_secret,
                "redirect_uri": settings.redirect_uri,
                "grant_type": "authorization_code",
            },
            timeout=10,
        )
        response.raise_for_status()
        token_response: Any = response.json()
    except (requests.RequestException, ValueError) as exc:
        raise GoogleOAuthError("Google token exchange failed.") from exc

    if not isinstance(token_response, dict):
        raise GoogleOAuthError("Google token exchange returned an invalid response.")
    identity_token = token_response.get("id_token")
    if not isinstance(identity_token, str) or not identity_token:
        raise GoogleOAuthError("Google token exchange did not return an ID token.")
    return identity_token


def verify_identity_token(identity_token: str, client_id: str) -> dict[str, Any]:
    """Verify the token signature, issuer, audience, and expiration with Google."""
    try:
        claims = id_token.verify_oauth2_token(
            identity_token,
            GoogleRequest(),
            audience=client_id,
        )
    except (GoogleAuthError, ValueError) as exc:
        raise GoogleOAuthError("Google ID token verification failed.") from exc
    return claims
