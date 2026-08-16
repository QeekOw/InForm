import base64
import mimetypes
from pathlib import Path

from openai import OpenAI

from cera.inbody import InBodyPayload

_MODEL = "gpt-4o-2024-08-06"

_SYSTEM_PROMPT = (
    "You extract structured body-composition data from a photo of an InBody "
    "270 or InBody 570 result sheet. Read every field directly off the sheet "
    "and set source_device to the device model printed on it. The InBody 270 "
    "never prints a Visceral Fat Level, and the InBody 570 sometimes omits "
    "it; leave visceral_fat_level unset when the sheet does not print it."
)


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
        response_format=InBodyPayload,
    )
    return completion.choices[0].message.parsed
