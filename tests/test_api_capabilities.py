"""GET /capabilities — what this deployment can actually do (Requirement 1.6).

The frontend uses this to stop offering the live-read action on servers without
a Donut checkpoint (ADR-0010), rather than offering an action that can only fail.
"""

import pytest
from fastapi.testclient import TestClient

from backend import main
from backend.main import app, get_live_read_available
from inform.errors import DonutCheckpointError


client = TestClient(app)


@pytest.fixture(autouse=True)
def unresolved_probe(monkeypatch):
    """Start every test with the probe unasked, and drop any dependency override.

    The answer is cached for the life of the process, so without this each test
    would inherit whichever answer ran first.
    """
    monkeypatch.setattr(main, "_live_read_probe", None)
    yield
    app.dependency_overrides.clear()


def test_capabilities_reports_a_boolean():
    """The contract is a plain boolean, whatever this particular machine can do."""
    response = client.get("/capabilities")
    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"live_read_available"}
    assert isinstance(body["live_read_available"], bool)


def test_capabilities_available_under_api_prefix_too():
    assert client.get("/api/capabilities").status_code == 200


def test_missing_checkpoint_reports_live_read_unavailable(monkeypatch):
    def no_checkpoint(*args, **kwargs):
        raise DonutCheckpointError("models/donut-both-v3")

    monkeypatch.setattr(main, "default_engine", no_checkpoint)

    assert client.get("/capabilities").json()["live_read_available"] is False


def test_constructible_engine_reports_live_read_available(monkeypatch):
    monkeypatch.setattr(main, "default_engine", lambda *a, **kw: (lambda img: None))

    assert client.get("/capabilities").json()["live_read_available"] is True


def test_probe_runs_once_and_caches(monkeypatch):
    """Constructing the engine loads a large checkpoint, so ask once and keep it."""
    calls = []

    def counting_engine(*args, **kwargs):
        calls.append(1)
        return lambda img: None

    monkeypatch.setattr(main, "default_engine", counting_engine)

    for _ in range(3):
        assert client.get("/capabilities").json()["live_read_available"] is True

    assert len(calls) == 1


def test_probe_caches_the_negative_answer_too(monkeypatch):
    calls = []

    def counting_failure(*args, **kwargs):
        calls.append(1)
        raise DonutCheckpointError("models/donut-both-v3")

    monkeypatch.setattr(main, "default_engine", counting_failure)

    for _ in range(3):
        assert client.get("/capabilities").json()["live_read_available"] is False

    assert len(calls) == 1


def test_probe_is_resolved_lazily_on_first_request(monkeypatch):
    """Nothing constructs the engine until someone actually asks.

    This is what keeps a 776 MB checkpoint load off the import path and off
    server startup; the probe is only paid for by the first caller.
    """
    monkeypatch.setattr(main, "default_engine", lambda *a, **kw: (lambda img: None))

    assert main._live_read_probe is None
    client.get("/capabilities")
    assert main._live_read_probe is True


def test_capabilities_is_overridable_for_tests():
    app.dependency_overrides[get_live_read_available] = lambda: True
    assert client.get("/capabilities").json()["live_read_available"] is True

    app.dependency_overrides[get_live_read_available] = lambda: False
    assert client.get("/capabilities").json()["live_read_available"] is False


def test_sample_gallery_works_while_live_read_is_unavailable(monkeypatch):
    """Requirement 1.1: the instant path never touches the engine.

    The two facts have to hold together, since this is what makes the app
    demoable on a machine with no checkpoint.
    """
    def no_checkpoint(*args, **kwargs):
        raise DonutCheckpointError("models/donut-both-v3")

    monkeypatch.setattr(main, "default_engine", no_checkpoint)

    assert client.get("/capabilities").json()["live_read_available"] is False

    read = client.post("/reads", json={"sample_id": "synthetic_270_clean", "live": False}).json()
    assert read["status"] == "complete"
    assert read["extraction"]["data"] is not None
