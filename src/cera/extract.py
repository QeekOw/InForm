from pathlib import Path

from cera.engines import vlm
from cera.inbody import InBodyPayload


def extract_inbody(image_path: Path) -> InBodyPayload:
    """The single production seam: image in, validated InBodyPayload out.

    Backed by one swappable extraction engine at a time (ADR-0002) —
    currently the VLM baseline.
    """
    return vlm.extract(image_path)
