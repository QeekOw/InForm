"""Task 5 (accounts-and-history spec): CORS is restricted to explicit origins
with credentials allowed, not the previous allow_origins=["*"].

allow_credentials=True can never legally pair with a wildcard origin (browsers
refuse it), so this locks down what was previously wide open — flagged to the
user before this task was implemented, per the accounts-and-history design.
"""

from fastapi.testclient import TestClient

from backend.main import _allowed_origins, app

client = TestClient(app)


def test_localhost_dev_origin_is_allowed_by_default():
    assert "http://localhost:3000" in _allowed_origins


def test_preflight_from_allowed_origin_is_permitted():
    resp = client.options(
        "/auth/me",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert resp.status_code == 200
    assert resp.headers.get("access-control-allow-origin") == "http://localhost:3000"
    assert resp.headers.get("access-control-allow-credentials") == "true"


def test_preflight_from_disallowed_origin_is_rejected():
    resp = client.options(
        "/auth/me",
        headers={
            "Origin": "https://not-our-frontend.example.com",
            "Access-Control-Request-Method": "GET",
        },
    )
    # Starlette's CORS middleware answers preflight with 400 when the origin
    # isn't in the allow-list, rather than omitting the header on a 200 — the
    # request never reaches the endpoint either way.
    assert resp.headers.get("access-control-allow-origin") != "https://not-our-frontend.example.com"


def test_actual_request_from_disallowed_origin_lacks_cors_header():
    resp = client.get("/health", headers={"Origin": "https://not-our-frontend.example.com"})
    # The request itself still succeeds (CORS is enforced by the browser, not
    # the server), but without the allow-origin header a browser would block
    # the frontend JS from reading the response.
    assert "access-control-allow-origin" not in {k.lower() for k in resp.headers}
