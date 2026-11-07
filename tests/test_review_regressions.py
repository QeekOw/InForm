import copy
import json
import uuid
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from backend.db.models import Scan
from backend.main import _scan_to_detail, app
from inform.samples import load_extractions


PROFILE = {
    "age": 30,
    "biological_sex": "female",
    "activity_multiplier": 1.55,
    "fitness_goal": "fat_loss",
}
LIMBS = [f"segmental_lean.{side}_{pair}_kg" for pair in ("arm", "leg") for side in ("left", "right")]


def test_sample_requirements_include_current_cross_checks_and_missing_values(tmp_path):
    artifact = load_extractions().model_dump(mode="json")
    item = artifact["extractions"]["real_270_clean"]
    item["flagged"] = ["weight_kg"]
    item["unread"] = []
    item["data"]["segmental_lean"].update(left_arm_kg=3.1, right_arm_kg=3.2, left_leg_kg=8.21, trunk_kg=None)
    original_data = copy.deepcopy(item["data"])
    path = tmp_path / "reads.json"
    path.write_text(json.dumps(artifact))

    loaded = load_extractions(path).extractions["real_270_clean"]

    assert set(loaded.flagged) >= {"weight_kg", "segmental_lean.left_arm_kg", "segmental_lean.right_arm_kg"}
    assert "segmental_lean.trunk_kg" in loaded.unread
    assert loaded.data.model_dump(mode="json") == original_data
    assert json.loads(path.read_text()) == artifact


@pytest.mark.parametrize("sample_id", ["real_270_clean", "real_270_flagged", "synthetic_270_clean"])
def test_samples_plan_with_explicit_unchanged_limb_confirmations(sample_id):
    item = load_extractions().extractions[sample_id]
    response = TestClient(app).post("/plan", json={
        "user": PROFILE, "sample_id": sample_id,
        "confirmations": list(dict.fromkeys(item.flagged + LIMBS)),
    })
    assert response.status_code == 200, response.text
    plan = response.json()
    assert plan["exercises"]["unconfirmed_imbalance_pairs"] == []
    assert plan["corrected_fields"] == []
    assert set(plan["confirmed_fields"]) >= set(LIMBS)


def test_legacy_saved_scan_without_assessment_metadata_is_not_assumed_balanced():
    plan_response = TestClient(app).post("/plan", json={"user": PROFILE, "sample_id": "synthetic_270_clean"})
    assert plan_response.status_code == 200
    plan = plan_response.json()
    exercises = copy.deepcopy(plan["exercises"])
    exercises.pop("unconfirmed_imbalance_pairs")
    measured = load_extractions().extractions["synthetic_270_clean"].data.model_dump(mode="json")
    scan = Scan(
        id=uuid.uuid4(), created_at=datetime.now(timezone.utc),
        source_device="inbody_270", sample_id="synthetic_270_clean",
        profile=PROFILE, measured=measured, effective_inbody=measured,
        corrected_fields=[], confirmed_fields=[], nutrition=plan["nutrition"],
        exercises=exercises, narrative_text=plan["narrative_text"], narrative_source=plan["narrative_source"],
    )
    original = copy.deepcopy(scan.exercises)

    detail = _scan_to_detail(scan)

    assert detail.exercises.unconfirmed_imbalance_pairs == ["arm", "leg"]
    assert scan.exercises == original
