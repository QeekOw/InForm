import asyncio
import time
from pathlib import Path
from fastapi.testclient import TestClient
import pytest

from backend.main import app, get_engine
from inform.errors import NotAnInBodySheetError
from inform.inbody import PartialInBody
from inform.samples import load_extractions


client = TestClient(app)


def test_create_read_instant_stored_sample():
    """POST /reads with live=False returns complete read immediately from stored extractions."""
    response = client.post("/reads", json={"sample_id": "synthetic_270_clean", "live": False})
    assert response.status_code == 200
    data = response.json()
    assert "read_id" in data
    assert data["sample_id"] == "synthetic_270_clean"
    assert data["live"] is False
    assert data["status"] == "complete"
    assert data["progress"] == 1.0
    assert data["extraction"] is not None
    assert data["extraction"]["data"]["weight_kg"] == 56.7


def test_create_read_live_starts_pending_job():
    """AC: A visible action runs the model live; read starts in pending state."""
    # Stub engine that takes a short time
    def slow_stub(path: Path) -> PartialInBody:
        time.sleep(0.5)
        return PartialInBody(weight_kg=60.0, lean_body_mass_kg=45.0, percent_body_fat=25.0)

    app.dependency_overrides[get_engine] = lambda: slow_stub
    try:
        response = client.post("/reads", json={"sample_id": "synthetic_270_clean", "live": True})
        assert response.status_code == 200
        data = response.json()
        assert "read_id" in data
        assert data["sample_id"] == "synthetic_270_clean"
        assert data["live"] is True
        assert data["status"] == "pending"
        assert data["progress"] >= 0.0
        assert "message" in data
    finally:
        app.dependency_overrides.clear()


def test_poll_read_long_polling_waits_and_returns_complete():
    """AC: Long polling survives past client waits and returns complete when engine finishes."""
    def stub_engine(path: Path) -> PartialInBody:
        time.sleep(0.2)
        return PartialInBody(weight_kg=70.0, lean_body_mass_kg=55.0, percent_body_fat=21.4)

    app.dependency_overrides[get_engine] = lambda: stub_engine
    try:
        # Start live read
        start_resp = client.post("/reads", json={"sample_id": "synthetic_270_clean", "live": True})
        read_id = start_resp.json()["read_id"]

        # Long poll with timeout=1.0s (sufficient for the 0.2s stub)
        poll_resp = client.get(f"/reads/{read_id}?timeout=1.0")
        assert poll_resp.status_code == 200
        poll_data = poll_resp.json()
        assert poll_data["status"] == "complete"
        assert poll_data["progress"] == 1.0
        assert poll_data["extraction"]["data"]["weight_kg"] == 70.0
        assert poll_data["extraction"]["data"]["lean_body_mass_kg"] == 55.0
    finally:
        app.dependency_overrides.clear()


def test_poll_read_times_out_and_returns_pending_surviving_timeout():
    """AC: The read survives past a host request timeout (returns pending with progress)."""
    def very_slow_stub(path: Path) -> PartialInBody:
        time.sleep(1.0)
        return PartialInBody(weight_kg=70.0, lean_body_mass_kg=55.0, percent_body_fat=21.4)

    app.dependency_overrides[get_engine] = lambda: very_slow_stub
    try:
        start_resp = client.post("/reads", json={"sample_id": "synthetic_270_clean", "live": True})
        read_id = start_resp.json()["read_id"]

        # Short timeout (e.g. 0.05s) simulates host chunk timeout before inference finishes
        poll_resp = client.get(f"/reads/{read_id}?timeout=0.05")
        assert poll_resp.status_code == 200
        poll_data = poll_resp.json()
        assert poll_data["status"] == "pending"
        assert 0.0 <= poll_data["progress"] < 1.0
        assert "message" in poll_data

        # Second poll with sufficient timeout completes the read
        poll_resp_2 = client.get(f"/reads/{read_id}?timeout=2.0")
        assert poll_resp_2.status_code == 200
        assert poll_resp_2.json()["status"] == "complete"
    finally:
        app.dependency_overrides.clear()


def test_live_read_returns_same_values_as_stored_reading():
    """AC: A live read of a sheet returns the same values as its stored reading."""
    stored = load_extractions().extractions["synthetic_270_clean"]

    # Stub engine reproduces the exact stored extraction values
    def exact_stub(path: Path) -> PartialInBody:
        return stored.data

    app.dependency_overrides[get_engine] = lambda: exact_stub
    try:
        start_resp = client.post("/reads", json={"sample_id": "synthetic_270_clean", "live": True})
        read_id = start_resp.json()["read_id"]

        poll_resp = client.get(f"/reads/{read_id}?timeout=1.0")
        assert poll_resp.status_code == 200
        poll_data = poll_resp.json()
        assert poll_data["status"] == "complete"
        assert poll_data["extraction"]["data"] == stored.data.model_dump()
        assert poll_data["extraction"]["unread"] == stored.unread
        assert poll_data["extraction"]["flagged"] == stored.flagged
    finally:
        app.dependency_overrides.clear()


def test_live_read_refusal_records_refusal_status():
    """A sheet that fails detection or is refused returns status='refused' rather than 500."""
    def refusing_stub(path: Path) -> PartialInBody:
        raise NotAnInBodySheetError()

    app.dependency_overrides[get_engine] = lambda: refusing_stub
    try:
        start_resp = client.post("/reads", json={"sample_id": "refused_non_sheet", "live": True})
        read_id = start_resp.json()["read_id"]

        poll_resp = client.get(f"/reads/{read_id}?timeout=1.0")
        assert poll_resp.status_code == 200
        poll_data = poll_resp.json()
        assert poll_data["status"] == "refused"
        assert poll_data["extraction"]["status"] == "refused"
        assert poll_data["extraction"]["error"] == "not_an_inbody_sheet"
    finally:
        app.dependency_overrides.clear()


def test_plan_with_completed_read_id():
    """POST /plan supports read_id as the reading source."""
    clean_data = load_extractions().extractions["synthetic_270_clean"].data

    def stub_engine(path: Path) -> PartialInBody:
        return clean_data

    app.dependency_overrides[get_engine] = lambda: stub_engine
    try:
        start_resp = client.post("/reads", json={"sample_id": "synthetic_270_clean", "live": True})
        read_id = start_resp.json()["read_id"]

        poll_resp = client.get(f"/reads/{read_id}?timeout=1.0")
        assert poll_resp.json()["status"] == "complete"

        # Now build a plan using read_id
        plan_resp = client.post(
            "/plan",
            json={
                "user": {
                    "age": 30,
                    "biological_sex": "female",
                    "activity_multiplier": 1.55,
                    "fitness_goal": "fat_loss",
                },
                "read_id": read_id,
            },
        )
        assert plan_resp.status_code == 200
        plan_data = plan_resp.json()
        assert plan_data["nutrition"]["target_calories_kcal"] > 0
        assert plan_data["measured"]["weight_kg"] == clean_data.weight_kg
    finally:
        app.dependency_overrides.clear()


def test_plan_with_pending_read_id_returns_409():
    def hanging_stub(path: Path) -> PartialInBody:
        time.sleep(2.0)
        return PartialInBody(weight_kg=70.0, lean_body_mass_kg=55.0, percent_body_fat=21.4)

    app.dependency_overrides[get_engine] = lambda: hanging_stub
    try:
        start_resp = client.post("/reads", json={"sample_id": "synthetic_270_clean", "live": True})
        read_id = start_resp.json()["read_id"]

        plan_resp = client.post(
            "/plan",
            json={
                "user": {
                    "age": 30,
                    "biological_sex": "female",
                    "activity_multiplier": 1.55,
                    "fitness_goal": "fat_loss",
                },
                "read_id": read_id,
            },
        )
        assert plan_resp.status_code == 409
        assert "in progress" in plan_resp.json()["detail"].lower()
    finally:
        app.dependency_overrides.clear()


def test_unknown_read_id_returns_404():
    poll_resp = client.get("/reads/read_nonexistent?timeout=0.1")
    assert poll_resp.status_code == 404
    assert "not found" in poll_resp.json()["detail"].lower()


def test_create_read_requires_either_sample_or_image():
    """POST /reads rejects requests with neither or both sample_id and image_data."""
    # Neither
    resp_neither = client.post("/reads", json={})
    assert resp_neither.status_code == 422

    # Both
    resp_both = client.post(
        "/reads",
        json={"sample_id": "synthetic_270_clean", "image_data": "data:image/png;base64,abc"},
    )
    assert resp_both.status_code == 422


def test_create_read_with_image_data_starts_and_completes():
    """AC: A person can upload a photo of their own sheet and have it read."""
    import base64
    import io
    from PIL import Image

    # Create a tiny 10x10 PNG image in memory as base64
    img = Image.new("RGB", (10, 10), color=(255, 255, 255))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    b64_str = f"data:image/png;base64,{base64.b64encode(buf.getvalue()).decode('ascii')}"

    def stub_engine(img_input) -> PartialInBody:
        time.sleep(0.1)
        return PartialInBody(
            weight_kg=68.5,
            lean_body_mass_kg=52.0,
            percent_body_fat=24.1,
            skeletal_muscle_mass_kg=30.0,
            basal_metabolic_rate_kcal=1550.0,
            source_device="inbody_270",
        )

    app.dependency_overrides[get_engine] = lambda: stub_engine
    try:
        start_resp = client.post("/reads", json={"image_data": b64_str, "live": True})
        assert start_resp.status_code == 200
        start_data = start_resp.json()
        assert "read_id" in start_data
        assert start_data["sample_id"] is None
        assert start_data["status"] == "pending"

        read_id = start_data["read_id"]
        poll_resp = client.get(f"/reads/{read_id}?timeout=1.0")
        assert poll_resp.status_code == 200
        poll_data = poll_resp.json()
        assert poll_data["status"] == "complete"
        assert poll_data["extraction"]["data"]["weight_kg"] == 68.5
        assert poll_data["extraction"]["data"]["lean_body_mass_kg"] == 52.0
    finally:
        app.dependency_overrides.clear()


def test_unreadable_photo_prompts_retake_rather_than_product_failure():
    """AC: An unreadable photo prompts a retake rather than reporting a product failure."""
    import base64
    import io
    from inform.errors import MissingRequiredFieldsError
    from PIL import Image

    img = Image.new("RGB", (10, 10), color=(200, 200, 200))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    b64_str = f"data:image/png;base64,{base64.b64encode(buf.getvalue()).decode('ascii')}"

    def blurry_stub(img_input) -> PartialInBody:
        raise MissingRequiredFieldsError(["weight_kg", "lean_body_mass_kg"])

    app.dependency_overrides[get_engine] = lambda: blurry_stub
    try:
        start_resp = client.post("/reads", json={"image_data": b64_str, "live": True})
        read_id = start_resp.json()["read_id"]

        poll_resp = client.get(f"/reads/{read_id}?timeout=1.0")
        assert poll_resp.status_code == 200
        poll_data = poll_resp.json()
        assert poll_data["status"] == "refused"
        assert poll_data["extraction"]["status"] == "refused"
        # Prompt retake rather than reporting product failure
        msg = poll_data["extraction"]["message"].lower()
        assert "retake" in msg or "clearer photo" in msg or "re-upload" in msg
        assert "internal error" not in msg
    finally:
        app.dependency_overrides.clear()


def test_invalid_image_format_refuses_with_retake_message():
    """AC: Corrupted or non-image data prompts a retake rather than crashing."""
    start_resp = client.post("/reads", json={"image_data": "not-a-valid-base64-image", "live": True})
    assert start_resp.status_code == 200
    data = start_resp.json()
    assert data["status"] == "refused"
    msg = data["extraction"]["message"].lower()
    assert "retake" in msg or "photo" in msg


def test_uploaded_image_zero_persistence():
    """AC: The photo is never persisted anywhere after the Scan is saved (ADR-0011)."""
    import base64
    import io
    from PIL import Image
    from inform.reads import read_manager

    img = Image.new("RGB", (10, 10), color=(255, 255, 255))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    b64_str = f"data:image/png;base64,{base64.b64encode(buf.getvalue()).decode('ascii')}"

    def stub_engine(img_input) -> PartialInBody:
        return PartialInBody(
            weight_kg=70.0,
            lean_body_mass_kg=55.0,
            percent_body_fat=21.4,
            skeletal_muscle_mass_kg=32.0,
            basal_metabolic_rate_kcal=1600.0,
            source_device="inbody_270",
        )

    app.dependency_overrides[get_engine] = lambda: stub_engine
    try:
        start_resp = client.post("/reads", json={"image_data": b64_str, "live": True})
        read_id = start_resp.json()["read_id"]
        poll_resp = client.get(f"/reads/{read_id}?timeout=1.0")
        assert poll_resp.json()["status"] == "complete"

        # Check job in read_manager does not hold image bytes or base64 string
        job = read_manager.get(read_id)
        assert job is not None
        job_dict = job.to_dict()
        assert "image" not in job_dict
        assert "image_data" not in job_dict
        assert not hasattr(job, "image_data")
        assert not hasattr(job, "raw_bytes")
        assert not hasattr(job, "image_bytes")
    finally:
        app.dependency_overrides.clear()


def test_plan_with_uploaded_sheet_read_id():
    """AC: An uploaded sheet uses the same correction and confirmation flow as a Sample sheet."""
    import base64
    import io
    from PIL import Image
    from inform.inbody import PartialSegmentalLean

    img = Image.new("RGB", (10, 10), color=(255, 255, 255))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    b64_str = f"data:image/png;base64,{base64.b64encode(buf.getvalue()).decode('ascii')}"

    # Return clean measured read with complete fields
    def stub_engine(img_input) -> PartialInBody:
        return PartialInBody(
            weight_kg=75.0,
            lean_body_mass_kg=60.0,
            percent_body_fat=20.0,
            skeletal_muscle_mass_kg=35.0,
            basal_metabolic_rate_kcal=1666.0,
            segmental_lean=PartialSegmentalLean(
                left_arm_kg=3.5, right_arm_kg=3.5, left_leg_kg=9.5, right_leg_kg=9.5, trunk_kg=25.0
            ),
            source_device="inbody_270",
        )

    app.dependency_overrides[get_engine] = lambda: stub_engine
    try:
        start_resp = client.post("/reads", json={"image_data": b64_str, "live": True})
        read_id = start_resp.json()["read_id"]
        poll_resp = client.get(f"/reads/{read_id}?timeout=1.0")
        assert poll_resp.json()["status"] == "complete"

        # Build plan directly from uploaded sheet read_id
        plan_resp = client.post(
            "/plan",
            json={
                "user": {
                    "age": 28,
                    "biological_sex": "male",
                    "activity_multiplier": 1.55,
                    "fitness_goal": "hypertrophy",
                },
                "read_id": read_id,
            },
        )
        assert plan_resp.status_code == 200
        plan_data = plan_resp.json()
        assert plan_data["nutrition"]["target_calories_kcal"] > 0
        assert plan_data["measured"]["weight_kg"] == 75.0
        assert plan_data["exercises"]["exercises"]
    finally:
        app.dependency_overrides.clear()



# --- Honest failure attribution (issue #45 follow-up, ADR-0010) --------------
#
# Three read failures, three causes, three messages. A missing Donut checkpoint
# is a fact about this server; it must never come back as a claim about the
# person's photo, because no retake can fix it.


def _tiny_png_data_url() -> str:
    """A valid, decodable 10x10 PNG — so any refusal is about the engine, not the bytes."""
    import base64
    import io

    from PIL import Image

    img = Image.new("RGB", (10, 10), color=(255, 255, 255))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return f"data:image/png;base64,{base64.b64encode(buf.getvalue()).decode('ascii')}"


def test_live_sample_read_without_checkpoint_reports_engine_unavailable():
    """A live read with no Donut checkpoint blames the server, not the sheet."""
    from inform.errors import DonutCheckpointError

    def no_checkpoint(path):
        raise DonutCheckpointError("models/donut-both-v3")

    app.dependency_overrides[get_engine] = lambda: no_checkpoint
    try:
        start_resp = client.post("/reads", json={"sample_id": "synthetic_270_clean", "live": True})
        read_id = start_resp.json()["read_id"]

        poll_data = client.get(f"/reads/{read_id}?timeout=2.0").json()
        assert poll_data["status"] == "refused"
        assert poll_data["extraction"]["error"] == "engine_unavailable"

        msg = poll_data["extraction"]["message"].lower()
        assert "unavailable" in msg
        # Never attributed to the image (Requirement 1.2)
        assert "blurry" not in msg
        assert "retake" not in msg
    finally:
        app.dependency_overrides.clear()


def test_live_sample_read_failure_does_not_substitute_stored_extraction():
    """A failed live read returns no numbers at all (issue #29 stories 23-25).

    The live read exists to prove the gallery numbers were not typed in by the
    developers. Serving the stored extraction when the model could not run would
    destroy the only reason the action exists.
    """
    from inform.errors import DonutCheckpointError

    stored = load_extractions().extractions["synthetic_270_clean"]
    assert stored.data is not None, "fixture guard: this sample has stored numbers"

    def no_checkpoint(path):
        raise DonutCheckpointError("models/donut-both-v3")

    app.dependency_overrides[get_engine] = lambda: no_checkpoint
    try:
        start_resp = client.post("/reads", json={"sample_id": "synthetic_270_clean", "live": True})
        read_id = start_resp.json()["read_id"]

        poll_data = client.get(f"/reads/{read_id}?timeout=2.0").json()
        assert poll_data["status"] == "refused"
        assert poll_data["extraction"]["data"] is None
        assert poll_data["extraction"]["unread"] == []
        assert poll_data["extraction"]["flagged"] == []
    finally:
        app.dependency_overrides.clear()


def test_uploaded_photo_without_checkpoint_reports_engine_unavailable():
    """A readable photo plus a missing checkpoint is an engine fault, not a photo fault."""
    from inform.errors import DonutCheckpointError

    def no_checkpoint(img_input):
        raise DonutCheckpointError("models/donut-both-v3")

    app.dependency_overrides[get_engine] = lambda: no_checkpoint
    try:
        start_resp = client.post(
            "/reads", json={"image_data": _tiny_png_data_url(), "live": True}
        )
        read_id = start_resp.json()["read_id"]

        poll_data = client.get(f"/reads/{read_id}?timeout=2.0").json()
        assert poll_data["status"] == "refused"
        assert poll_data["extraction"]["error"] == "engine_unavailable"
        assert "blurry" not in poll_data["extraction"]["message"].lower()
    finally:
        app.dependency_overrides.clear()


def test_engine_construction_failure_reports_engine_unavailable():
    """The engine failing to *build* is engine_unavailable too, not just failing to read.

    An eager engine_factory raises on the request thread, before any worker
    starts, so it needs its own guard. Driven through the manager directly
    because a raising FastAPI dependency never reaches the manager at all.
    """
    from inform.errors import DonutCheckpointError
    from inform.reads import read_manager

    def failing_factory():
        raise DonutCheckpointError("models/donut-both-v3")

    upload_job = read_manager.create_read(
        image_data=_tiny_png_data_url(), live=True, engine_factory=failing_factory
    )
    assert upload_job.status == "refused"
    assert upload_job.error == "engine_unavailable"
    assert upload_job.extraction is not None
    assert upload_job.extraction.error == "engine_unavailable"

    sample_job = read_manager.create_read(
        sample_id="synthetic_270_clean", live=True, engine_factory=failing_factory
    )
    assert sample_job.status == "refused"
    assert sample_job.error == "engine_unavailable"
    assert sample_job.extraction is not None
    assert sample_job.extraction.data is None


def test_unreadable_photo_is_not_reported_as_engine_unavailable():
    """The reverse direction of Property 5: a real photo fault stays a photo fault."""
    from inform.errors import MissingRequiredFieldsError

    def blurry(img_input):
        raise MissingRequiredFieldsError(["weight_kg", "lean_body_mass_kg"])

    app.dependency_overrides[get_engine] = lambda: blurry
    try:
        start_resp = client.post(
            "/reads", json={"image_data": _tiny_png_data_url(), "live": True}
        )
        read_id = start_resp.json()["read_id"]

        poll_data = client.get(f"/reads/{read_id}?timeout=2.0").json()
        assert poll_data["extraction"]["error"] == "unreadable_photo"
        assert poll_data["extraction"]["error"] != "engine_unavailable"
    finally:
        app.dependency_overrides.clear()


def test_non_sheet_is_not_reported_as_engine_unavailable():
    """The third mode stays distinct from the other two."""
    def refusing(path):
        raise NotAnInBodySheetError()

    app.dependency_overrides[get_engine] = lambda: refusing
    try:
        start_resp = client.post("/reads", json={"sample_id": "refused_non_sheet", "live": True})
        read_id = start_resp.json()["read_id"]

        poll_data = client.get(f"/reads/{read_id}?timeout=2.0").json()
        assert poll_data["extraction"]["error"] == "not_an_inbody_sheet"
    finally:
        app.dependency_overrides.clear()


def test_instant_sample_path_completes_with_no_checkpoint_present():
    """Requirement 1.1: the gallery works without the Donut checkpoint.

    No engine override is installed, so this exercises the real default engine
    resolution path — which the instant path must never reach.
    """
    for sample_id in ("synthetic_270_clean", "synthetic_570_clean", "real_270_clean"):
        data = client.post("/reads", json={"sample_id": sample_id, "live": False}).json()
        assert data["status"] == "complete", f"{sample_id} did not complete instantly"
        assert data["progress"] == 1.0
        assert data["extraction"]["data"] is not None
        assert data["extraction"]["error"] is None
