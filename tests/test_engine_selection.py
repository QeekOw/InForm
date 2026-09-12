# Engine selection (ADR-0010): Donut is the default runtime engine; an engine
# can be injected to override; a missing checkpoint fails loudly and never
# silently falls back to the cloud VLM. These tests carry NO torch/transformers
# and NO 809 MB checkpoint: a stub engine stands in for Donut, and the fail-loud
# path is exercised by pointing at a nonexistent dir.
from pathlib import Path

import pytest

from inform import extract as extract_mod
from inform.engines import donut
from inform.errors import DonutCheckpointError
from inform.extract import default_engine, extract_inbody
from inform.inbody import PartialInBody, PartialSegmentalLean

FIXTURE = Path(__file__).parent / "fixtures" / "inbody_sample.png"

# The default checkpoint dir (ADR-0010). If a real download is present, one test
# below round-trips it; otherwise that test skips.
_REAL_CKPT = Path("models/donut-both-v5")


def _complete_partial() -> PartialInBody:
    """A fully-read PartialInBody, so a stub engine clears the floor-reject."""
    return PartialInBody(
        weight_kg=70.0,
        lean_body_mass_kg=58.0,
        percent_body_fat=17.1,
        skeletal_muscle_mass_kg=33.0,
        basal_metabolic_rate_kcal=1622.8,
        segmental_lean=PartialSegmentalLean(
            left_arm_kg=3.2, right_arm_kg=3.3, left_leg_kg=8.1, right_leg_kg=8.2, trunk_kg=24.5
        ),
        source_device="inbody_570",
    )


def test_default_engine_builds_donut_from_env(monkeypatch, tmp_path):
    monkeypatch.setenv("INFORM_DONUT_CKPT", str(tmp_path))
    seen: dict[str, Path] = {}
    sentinel: extract_mod.Engine = lambda _p: _complete_partial()

    def fake_load_engine(checkpoint_dir: Path):
        seen["path"] = checkpoint_dir
        return sentinel

    monkeypatch.setattr(donut, "load_engine", fake_load_engine)

    engine = default_engine()

    assert engine is sentinel
    assert seen["path"] == tmp_path


def test_default_engine_missing_checkpoint_fails_loudly(monkeypatch, tmp_path):
    missing = tmp_path / "not-downloaded"
    monkeypatch.setenv("INFORM_DONUT_CKPT", str(missing))
    # If it tried the loader (or any fallback) that would be the bug we're guarding.
    monkeypatch.setattr(
        donut, "load_engine", lambda _p: pytest.fail("must not load on a missing checkpoint")
    )

    with pytest.raises(DonutCheckpointError) as exc:
        default_engine()

    assert str(missing) in str(exc.value)


def test_default_engine_missing_training_extra_fails_loudly(monkeypatch, tmp_path):
    monkeypatch.setenv("INFORM_DONUT_CKPT", str(tmp_path))  # dir exists

    def raise_import_error(_p: Path):
        raise ImportError("No module named 'torch'")

    monkeypatch.setattr(donut, "load_engine", raise_import_error)

    with pytest.raises(DonutCheckpointError) as exc:
        default_engine()

    assert "training" in str(exc.value)  # points the caller at pip install -e ".[training]"


def test_extract_inbody_uses_injected_engine_without_touching_donut(monkeypatch):
    # An explicit engine wins outright; the default resolver is never reached.
    monkeypatch.setattr(
        extract_mod, "default_engine", lambda: pytest.fail("injected engine must win")
    )
    calls: list[Path] = []

    def stub_engine(image_path: Path) -> PartialInBody:
        calls.append(image_path)
        return _complete_partial()

    result = extract_inbody(FIXTURE, engine=stub_engine)

    assert calls == [FIXTURE]
    assert result.is_complete()


def test_extract_inbody_resolves_default_engine_when_none(monkeypatch):
    resolved: list[bool] = []

    def fake_default() -> extract_mod.Engine:
        resolved.append(True)
        return lambda _p: _complete_partial()

    monkeypatch.setattr(extract_mod, "default_engine", fake_default)

    result = extract_inbody(FIXTURE)  # engine defaults to None -> default_engine()

    assert resolved == [True]
    assert result.is_complete()


@pytest.mark.skipif(not _REAL_CKPT.exists(), reason="Donut checkpoint not downloaded")
def test_default_engine_round_trips_real_checkpoint(tmp_path):
    # Only runs when the real 809 MB checkpoint is on disk (needs the training
    # extra). Drives the fine-tune on a synthetic sheet (the distribution it
    # trained on) and asserts it reads the known ground truth back, proving
    # load_checkpoint/load_engine bind a working model, not just that it loads.
    from inform.synthetic import generate_sheet

    png, truth = generate_sheet("inbody_570", seed=1)
    sheet = tmp_path / "sheet.png"
    sheet.write_bytes(png)

    result = extract_inbody(sheet, engine=default_engine())

    assert result.is_complete()
    assert result.data.weight_kg == pytest.approx(truth.weight_kg, abs=0.1)
    assert result.data.lean_body_mass_kg == pytest.approx(truth.lean_body_mass_kg, abs=0.1)
    assert result.data.source_device == truth.source_device
