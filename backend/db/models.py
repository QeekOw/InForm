"""ORM models for Accounts & History (issues #41-#44).

Two tables only, per the accounts-and-history spec's design:

- Account: a durable sign-in identity. Password is stored only as a bcrypt hash
  (see backend/auth.py) — never in plain text, never returned by any endpoint.
  It also carries profile *defaults*, which exist purely to pre-fill a form and
  are never read back as the source of truth for a past plan.
- Scan: an immutable record of one read. The Profile that produced it is frozen
  as a JSON snapshot on the Scan itself rather than referenced by a foreign key
  to a mutable Profile row (issue #29: "the Profile is frozen onto the Scan...
  never referenced by pointer, so changing a goal later never rewrites the
  meaning of a past plan").

No column on either table stores an image, in any form (ADR-0011).
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Account(Base):
    __tablename__ = "accounts"

    # At least one way to sign in must exist, or the row is an account nobody
    # can ever get into. password_hash became nullable so a Google-only account
    # is possible; this is what stops that from also permitting a credential-less
    # one.
    __table_args__ = (
        CheckConstraint(
            "password_hash IS NOT NULL OR google_sub IS NOT NULL",
            name="ck_accounts_has_a_credential",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    # Lowercased before storage (backend/auth.py / the signup endpoint), so the
    # uniqueness constraint is effectively case-insensitive.
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False, index=True)
    # Nullable since an account may be Google-only and have no password at all.
    # The CHECK constraint above keeps "neither" from being a valid row.
    password_hash: Mapped[str | None] = mapped_column(String, nullable=True)
    # Google's stable subject identifier. Not the email: Google allows an account's
    # email to change while `sub` stays put, so `sub` is what an account is matched
    # on. Unfilled until real Google sign-in lands (out of scope here).
    google_sub: Mapped[str | None] = mapped_column(
        String, unique=True, nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # --- Pre-fill defaults, NOT the source of truth for any plan --------------
    #
    # These exist only so a returning person doesn't retype what they already
    # told us. What produced a given plan is the Scan's own frozen `profile`
    # snapshot below, never these columns (issue #42). Editing a default here
    # cannot and must not change the meaning of a Scan already saved.
    #
    # Date of birth rather than age, because age is only true for a year;
    # the Scan freezes the age computed at the time it was taken.
    date_of_birth: Mapped[datetime | None] = mapped_column(Date, nullable=True)
    # Display only. Nothing in the pipeline consumes height: Katch-McArdle works
    # from lean body mass, and deriving BMI from this would be a clinical claim
    # this project does not make.
    height_cm: Mapped[float | None] = mapped_column(Float, nullable=True)
    default_biological_sex: Mapped[str | None] = mapped_column(String, nullable=True)
    default_activity_multiplier: Mapped[float | None] = mapped_column(Float, nullable=True)
    default_fitness_goal: Mapped[str | None] = mapped_column(String, nullable=True)
    # Display name for greetings ("Hello! <name>") and the profile page. Never
    # used by the pipeline, and never part of a Scan's frozen snapshot.
    name: Mapped[str | None] = mapped_column(String, nullable=True)

    scans: Mapped[list["Scan"]] = relationship(
        "Scan", back_populates="account", cascade="all, delete-orphan"
    )


class Scan(Base):
    __tablename__ = "scans"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # clock_timestamp(), not now()/func.now(): now() returns the enclosing
    # transaction's start time and is frozen for that whole transaction, so
    # two Scans saved back-to-back within one transaction (as every test's
    # rolled-back-transaction fixture holds) would otherwise get an identical
    # created_at, breaking "newest first" (issue #42 AC4) and the staleness
    # boundary (issue #43) alike. clock_timestamp() advances on every call.
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.clock_timestamp()
    )

    source_device: Mapped[str | None] = mapped_column(String, nullable=True)
    sample_id: Mapped[str | None] = mapped_column(String, nullable=True)

    # Frozen UserProfile snapshot (age, biological_sex, activity_multiplier, fitness_goal).
    profile: Mapped[dict] = mapped_column(JSONB, nullable=False)
    # Frozen PartialInBody as originally read, before corrections/confirmations.
    measured: Mapped[dict] = mapped_column(JSONB, nullable=False)
    # Frozen InBodyPayload after corrections/confirmations were applied — what the
    # plan was actually computed from.
    effective_inbody: Mapped[dict] = mapped_column(JSONB, nullable=False)
    corrected_fields: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    confirmed_fields: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)

    nutrition: Mapped[dict] = mapped_column(JSONB, nullable=False)
    exercises: Mapped[dict] = mapped_column(JSONB, nullable=False)
    narrative_text: Mapped[str] = mapped_column(Text, nullable=False)
    narrative_source: Mapped[str] = mapped_column(String, nullable=False)

    account: Mapped["Account"] = relationship("Account", back_populates="scans")
