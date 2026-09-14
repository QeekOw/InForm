from pathlib import Path
import pytest
from inform.inbody import PartialInBody, PartialSegmentalLean
from inform.errors import NotAnInBodySheetError

FIXTURE = Path(__file__).parent / "fixtures" / "inbody_sample.png"


def _sample_partial() -> PartialInBody:
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


def test_predict_returns_extraction_dictionary():
    from space.app import create_predict_fn

    stub_engine = lambda _p: _sample_partial()
    predict = create_predict_fn(engine=stub_engine)

    result = predict(FIXTURE)

    assert result["status"] == "complete"
    assert result["data"]["weight_kg"] == 70.0
    assert result["data"]["lean_body_mass_kg"] == 58.0
    assert result["unread"] == []
    assert result["flagged"] == []


def test_predict_returns_unread_and_flagged_fields():
    from space.app import create_predict_fn

    # Partial with missing trunk_kg (unread) and high BMR (cross-check flagged)
    partial = _sample_partial()
    partial.segmental_lean.trunk_kg = None
    partial.basal_metabolic_rate_kcal = 2500.0  # discrepancy with katch-mcardle

    stub_engine = lambda _p: partial
    predict = create_predict_fn(engine=stub_engine)

    result = predict(FIXTURE)

    assert result["status"] == "complete"
    assert "segmental_lean.trunk_kg" in result["unread"]
    assert "basal_metabolic_rate_kcal" in result["flagged"]


def test_predict_handles_not_an_inbody_sheet():
    from space.app import create_predict_fn

    def refusing_engine(_p):
        raise NotAnInBodySheetError()

    predict = create_predict_fn(engine=refusing_engine)

    result = predict(FIXTURE)

    assert result["status"] == "refused"
    assert result["error"] == "not_an_inbody_sheet"
    assert "does not appear to be an InBody" in result["message"]


def test_predict_handles_floor_reject_all_missing():
    from space.app import create_predict_fn

    # Engine returns empty partial -> all required fields unread -> MissingRequiredFieldsError
    stub_engine = lambda _p: PartialInBody()
    predict = create_predict_fn(engine=stub_engine)

    result = predict(FIXTURE)

    assert result["status"] == "refused"
    assert result["error"] == "missing_required_fields"
    assert len(result["unread"]) > 0


def test_parse_args_defaults():
    from space.app import parse_args

    args = parse_args([])
    assert args.host == "0.0.0.0"
    assert args.port == 7860
    assert args.share is False


def test_parse_args_explicit_flags():
    from space.app import parse_args

    args = parse_args(["--host", "127.0.0.1", "--port", "8080", "--share"])
    assert args.host == "127.0.0.1"
    assert args.port == 8080
    assert args.share is True


def test_parse_args_env_share(monkeypatch):
    from space.app import parse_args

    monkeypatch.setenv("GRADIO_SHARE", "true")
    args = parse_args([])
    assert args.share is True

