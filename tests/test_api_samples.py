from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def test_list_samples_returns_all_manifest_sheets_with_provenance():
    """AC: The gallery lists every Sample sheet with its provenance visible."""
    response = client.get("/samples")
    assert response.status_code == 200
    samples = response.json()

    assert len(samples) >= 5
    sample_ids = {s["id"] for s in samples}
    assert "synthetic_270_clean" in sample_ids
    assert "synthetic_570_clean" in sample_ids
    assert "real_270_clean" in sample_ids
    assert "real_270_flagged" in sample_ids
    assert "refused_non_sheet" in sample_ids

    # Each sample must expose its provenance ('synthetic' or 'real')
    for s in samples:
        assert s["provenance"] in ("synthetic", "real")
        assert "name" in s
        assert "description" in s
        assert "image_url" in s

    # /api/samples route alias also works
    api_resp = client.get("/api/samples")
    assert api_resp.status_code == 200
    assert api_resp.json() == samples


def test_gallery_includes_refused_and_flagged_sheets():
    """AC: A refused sheet and a flagged sheet are both present in the gallery."""
    response = client.get("/samples")
    assert response.status_code == 200
    samples = {s["id"]: s for s in response.json()}

    # Refused sheet present
    assert "refused_non_sheet" in samples

    # Flagged sheet present
    assert "real_270_flagged" in samples


def test_get_sample_returns_stored_extraction_instant():
    """AC: Picking a sheet returns its stored extraction without running the model."""
    response = client.get("/samples/synthetic_270_clean")
    assert response.status_code == 200
    result = response.json()

    assert result["status"] == "complete"
    assert result["data"]["weight_kg"] == 56.7
    assert result["data"]["lean_body_mass_kg"] == 39.0
    assert result["data"]["percent_body_fat"] == 31.2
    assert result["unread"] == []
    assert result["flagged"] == []

    # Alias /api/samples/{id} works
    api_resp = client.get("/api/samples/synthetic_270_clean")
    assert api_resp.status_code == 200
    assert api_resp.json() == result


def test_get_flagged_sample_returns_stored_flags():
    """AC: A flagged sheet returns stored flags as recorded in artifact."""
    response = client.get("/samples/real_270_flagged")
    assert response.status_code == 200
    result = response.json()

    assert result["status"] == "complete"
    assert "weight_kg" in result["flagged"]
    assert "lean_body_mass_kg" in result["flagged"]


def test_get_refused_sample_returns_refusal():
    """AC: A refused sheet returns refusal status and error."""
    response = client.get("/samples/refused_non_sheet")
    assert response.status_code == 200
    result = response.json()

    assert result["status"] == "refused"
    assert result["data"] is None
    assert result["error"] == "missing_required_fields"


def test_get_unknown_sample_returns_404():
    response = client.get("/samples/nonexistent_id")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_get_sample_image_returns_png():
    response = client.get("/samples/synthetic_270_clean/image")
    assert response.status_code == 200
    assert "image/png" in response.headers.get("content-type", "")
    assert len(response.content) > 1000
