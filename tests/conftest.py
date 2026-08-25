from unittest.mock import MagicMock

import pytest

from inform.engines import vlm
from inform.engines.vlm import _RawExtraction, _RawSegmentalLean


@pytest.fixture
def fake_openai(monkeypatch):
    """Set up the VLM engine path against a mocked OpenAI client.

    Also resolves the default engine to the VLM (ADR-0010 made Donut the
    default): these tests exercise the VLM seam and downstream wiring, so the
    default they should see is the mocked VLM, not a real Donut checkpoint.
    """

    def _install(raw: _RawExtraction) -> MagicMock:
        completion = MagicMock()
        completion.choices = [MagicMock(message=MagicMock(parsed=raw))]
        client = MagicMock()
        client.beta.chat.completions.parse.return_value = completion
        monkeypatch.setattr("inform.engines.vlm.OpenAI", lambda **_: client)
        monkeypatch.setattr("inform.extract.default_engine", lambda: vlm.extract)
        return client

    return _install


@pytest.fixture
def raw_segmental():
    def _build(**overrides) -> _RawSegmentalLean:
        fields = dict(
            left_arm_kg=3.2, right_arm_kg=3.3, left_leg_kg=8.1, right_leg_kg=8.2, trunk_kg=24.5
        )
        fields.update(overrides)
        return _RawSegmentalLean(**fields)

    return _build
