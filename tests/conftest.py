from unittest.mock import MagicMock

import pytest

from inform.engines.vlm import _RawExtraction, _RawSegmentalLean


@pytest.fixture
def fake_openai(monkeypatch):
    def _install(raw: _RawExtraction) -> MagicMock:
        completion = MagicMock()
        completion.choices = [MagicMock(message=MagicMock(parsed=raw))]
        client = MagicMock()
        client.beta.chat.completions.parse.return_value = completion
        monkeypatch.setattr("inform.engines.vlm.OpenAI", lambda **_: client)
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
