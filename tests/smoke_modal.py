"""Run a real Donut upload: python tests/smoke_modal.py https://...modal.run."""

import base64
import json
from pathlib import Path
import sys
import time
from urllib.request import Request, urlopen


def check(base_url: str):
    def request(path, payload=None):
        body = json.dumps(payload).encode() if payload is not None else None
        req = Request(base_url.rstrip("/") + path, data=body, headers={"Content-Type": "application/json"})
        with urlopen(req, timeout=180) as response:
            return json.load(response)

    assert request("/health")["status"] == "ok"
    assert request("/capabilities")["live_read_available"] is True
    image = Path(__file__).resolve().parents[1] / "data/samples/synthetic_270_clean.png"
    job = request("/reads", {"image_data": base64.b64encode(image.read_bytes()).decode(), "source": "photo"})
    assert job["live"] is True
    deadline = time.monotonic() + 180
    while job["status"] == "pending" and time.monotonic() < deadline:
        job = request(f"/reads/{job['read_id']}?timeout=10")
    assert job["status"] == "complete", job["message"]
    data = job["extraction"]["data"]
    assert data["source_device"] == "inbody_270"
    assert data["weight_kg"] > 0
    assert data["skeletal_muscle_mass_kg"] > 0
    print("Health and live Donut upload passed.")


if __name__ == "__main__":
    check(sys.argv[1])
