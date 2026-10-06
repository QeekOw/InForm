from unittest.mock import MagicMock

import pytest
from sqlalchemy.orm import Session

from backend.db.session import get_engine
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


@pytest.fixture
def db():
    """A Session bound to a connection whose outer transaction is rolled back
    after the test, so nothing a test commits ever reaches the real database.

    Deliberately *not* the SAVEPOINT-per-commit recipe some SQLAlchemy+FastAPI
    guides use, which restarts a nested transaction via a `session,
    "after_transaction_end"` event listener: that only works correctly when
    every commit happens on the same thread that set it up, and FastAPI's
    TestClient runs sync endpoints (this project's, throughout) via anyio's
    worker thread pool — a request-triggered commit executes on a different
    thread than the fixture's setup, SQLAlchemy Sessions aren't safe to use
    like that across threads, and the bookkeeping silently breaks, letting a
    commit escape to the real outer transaction (confirmed by testing this
    fixture against a live TestClient call before trusting it).

    Instead: the connection itself holds a real SAVEPOINT (`begin_nested()`)
    underneath the outer transaction, independent of the Session object's own
    thread-affine state. A test or an endpoint calling `session.commit()`
    only commits that savepoint (releasing it), and an endpoint calling
    `session.rollback()` (e.g. after a caught IntegrityError) only rolls back
    to it — the connection's outer transaction, entered once here, is what
    actually reaches Neon, and it is only ever rolled back at teardown.
    """
    engine = get_engine()
    connection = engine.connect()
    outer_transaction = connection.begin()
    connection.begin_nested()
    session = Session(bind=connection)
    try:
        yield session
    finally:
        session.close()
        outer_transaction.rollback()
        connection.close()
