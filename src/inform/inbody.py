from typing import Literal

from pydantic import BaseModel


class SegmentalLean(BaseModel):
    left_arm_kg: float
    right_arm_kg: float
    left_leg_kg: float
    right_leg_kg: float
    trunk_kg: float


class InBodyPayload(BaseModel):
    weight_kg: float
    # Authoritative LBM (ADR-0003): read directly off the sheet, not derived
    # from weight x (1 - PBF/100) — that derivation is a downstream cross-check only.
    lean_body_mass_kg: float
    percent_body_fat: float
    skeletal_muscle_mass_kg: float
    basal_metabolic_rate_kcal: float
    segmental_lean: SegmentalLean
    source_device: Literal["inbody_270", "inbody_570"]
    visceral_fat_level: int | None = None


# Field-name lists derived from the schema, so adding a field to the models
# above flows to every consumer (VLM parser, eval harness) without hand-editing
# each — the schema is the single source of truth. Order follows declaration.
SEGMENTAL_FIELDS: tuple[str, ...] = tuple(SegmentalLean.model_fields)
_SCALAR_FIELDS = [n for n in InBodyPayload.model_fields if n != "segmental_lean"]
REQUIRED_FIELDS: tuple[str, ...] = tuple(
    n for n in _SCALAR_FIELDS if InBodyPayload.model_fields[n].is_required()
)
OPTIONAL_FIELDS: tuple[str, ...] = tuple(
    n for n in _SCALAR_FIELDS if not InBodyPayload.model_fields[n].is_required()
)


class PartialSegmentalLean(BaseModel):
    """Segmental lean where each limb may be unread (None) — the partial-read
    counterpart of SegmentalLean (ADR-0008 amendment: partial extraction)."""

    left_arm_kg: float | None = None
    right_arm_kg: float | None = None
    left_leg_kg: float | None = None
    right_leg_kg: float | None = None
    trunk_kg: float | None = None


class PartialInBody(BaseModel):
    """What an engine actually read: every field is Optional, None = unread.

    InBodyPayload stays the complete/validated downstream contract; this holds
    the possibly-incomplete read before the seam decides floor-reject vs return.

    ponytail: a deliberate parallel schema, hand-kept in sync with InBodyPayload.
    Deriving it (create_model with Optional fields) can't express the nested
    partial — segmental_lean must accept a PartialSegmentalLean where a single
    limb is None — so a derived twin ends up more magic than these two boring
    field lists. If you add a field to InBodyPayload, add it here too.
    """

    weight_kg: float | None = None
    lean_body_mass_kg: float | None = None
    percent_body_fat: float | None = None
    skeletal_muscle_mass_kg: float | None = None
    basal_metabolic_rate_kcal: float | None = None
    segmental_lean: PartialSegmentalLean | None = None
    visceral_fat_level: int | None = None
    source_device: Literal["inbody_270", "inbody_570"] | None = None


class InBodyExtraction(BaseModel):
    """Result of a partial extraction (ADR-0008 amendment): the read values plus
    the required fields that were unread, and the fields flagged by a cross-check
    as suspect ("verify"). Never fabricates — unread carry no value, flagged are
    real reads marked low-confidence. The UI turns unread/flagged into a
    user-facing notice; that rendering is out of this module's scope."""

    data: PartialInBody
    unread: list[str]
    flagged: list[str]

    def is_complete(self) -> bool:
        return not self.unread and not self.flagged

    def as_payload(self) -> InBodyPayload | None:
        """Promote a clean, complete read to a validated InBodyPayload; None if
        anything is unread or flagged (so downstream can't consume a gappy read).

        A complete read has every field non-None, so model_validate reconstructs
        the strict payload directly (the nested segmental dict coerces to
        SegmentalLean) — no field-by-field copy needed."""
        if not self.is_complete():
            return None
        return InBodyPayload.model_validate(self.data.model_dump())


# The segmental limbs under their dotted per-field-accuracy names. Defined once
# here, beside the schema they are derived from, because the seam and both eval
# scorers all need them and three copies of the f-string drift.
SEGMENTAL_DOTTED_FIELDS: tuple[str, ...] = tuple(
    f"segmental_lean.{f}" for f in SEGMENTAL_FIELDS
)

# Every required field named for the partial-extraction seam and eval harness.
REQUIRED_DOTTED_FIELDS: tuple[str, ...] = REQUIRED_FIELDS + SEGMENTAL_DOTTED_FIELDS


def partial_field_value(data: PartialInBody, dotted: str) -> float | int | str | None:
    """Read a (possibly dotted, for segmental) field off a PartialInBody."""
    if dotted.startswith("segmental_lean."):
        segmental = data.segmental_lean
        return None if segmental is None else getattr(segmental, dotted.split(".", 1)[1])
    return getattr(data, dotted)
