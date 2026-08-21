import base64
import mimetypes
from pathlib import Path
from typing import Literal

from openai import OpenAI
from pydantic import BaseModel

from cera.errors import MissingRequiredFieldsError, NotAnInBodySheetError
from cera.inbody import REQUIRED_FIELDS, SEGMENTAL_FIELDS, InBodyPayload, SegmentalLean

_MODEL = "gpt-4o-2024-08-06"

_SYSTEM_PROMPT = (
    "You extract structured body-composition data from a photo of an InBody "
    "270 or InBody 570 result sheet. Set is_inbody_sheet to false if the "
    "image is not an InBody result sheet, and leave every other field unset "
    "in that case. Otherwise, read every field directly off the sheet and "
    "set source_device to the device model printed on it. Never guess a "
    "value: if a field is blurred, glare-washed, or otherwise not "
    "confidently readable, leave it unset rather than estimate it. The "
    "InBody 270 never prints a Visceral Fat Level, and the InBody 570 "
    "sometimes omits it; leave visceral_fat_level unset when the sheet does "
    "not print it — that is expected, not a misread."
)

class _RawSegmentalLean(BaseModel):
    left_arm_kg: float | None = None
    right_arm_kg: float | None = None
    left_leg_kg: float | None = None
    right_leg_kg: float | None = None
    trunk_kg: float | None = None


class _RawExtraction(BaseModel):
    """What the VLM actually commits to. Required InBodyPayload fields are
    nullable here so the model can say "unreadable" instead of guessing."""

    is_inbody_sheet: bool
    weight_kg: float | None = None
    lean_body_mass_kg: float | None = None
    percent_body_fat: float | None = None
    skeletal_muscle_mass_kg: float | None = None
    basal_metabolic_rate_kcal: float | None = None
    segmental_lean: _RawSegmentalLean | None = None
    visceral_fat_level: int | None = None
    source_device: Literal["inbody_270", "inbody_570"] | None = None


def extract(image_path: Path) -> InBodyPayload:
    # POC-only: this cloud VLM call is scoped to synthetic/consented images,
    # never real PHI, until the self-hosted Donut engine lands (ADR-0005).
    client = OpenAI()
    mime_type = mimetypes.guess_type(image_path.name)[0] or "image/png"
    encoded = base64.b64encode(image_path.read_bytes()).decode("ascii")

    completion = client.beta.chat.completions.parse(
        model=_MODEL,
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:{mime_type};base64,{encoded}"},
                    },
                ],
            },
        ],
        response_format=_RawExtraction,
    )
    return _to_payload(completion.choices[0].message.parsed)


def _to_payload(raw: _RawExtraction) -> InBodyPayload:
    if not raw.is_inbody_sheet:
        raise NotAnInBodySheetError()

    missing = [field for field in REQUIRED_FIELDS if getattr(raw, field) is None]
    if raw.segmental_lean is None:
        missing.extend(f"segmental_lean.{field}" for field in SEGMENTAL_FIELDS)
    else:
        missing.extend(
            f"segmental_lean.{field}"
            for field in SEGMENTAL_FIELDS
            if getattr(raw.segmental_lean, field) is None
        )
    if missing:
        raise MissingRequiredFieldsError(missing)

    return InBodyPayload(
        weight_kg=raw.weight_kg,
        lean_body_mass_kg=raw.lean_body_mass_kg,
        percent_body_fat=raw.percent_body_fat,
        skeletal_muscle_mass_kg=raw.skeletal_muscle_mass_kg,
        basal_metabolic_rate_kcal=raw.basal_metabolic_rate_kcal,
        segmental_lean=SegmentalLean(**raw.segmental_lean.model_dump()),
        visceral_fat_level=raw.visceral_fat_level,
        source_device=raw.source_device,
    )
