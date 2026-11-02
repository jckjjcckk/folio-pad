"""The per-profile model tier: read safely (a database without the column is standard), routed per job, set by the
user through PATCH /me. No network."""
from __future__ import annotations

import asyncio
import uuid
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from app import auth, librarian
from app.auth import User, current_user
from app.librarian import Job, JobContext
from app.llm import Completion
from app.main import app
from app.routes import me as me_routes
from app.spend import Charge, Spend
from tests.test_part_cut import FakeDB


def profile(tier: str | None = None, **extra) -> dict:
    p = {"id": "u1", "email": "u1@muse.test", "display_name": "U1", "budget_usd": 5, "spent_usd": 0, **extra}
    if tier is not None:
        p["model_tier"] = tier
    return p


class Ctx(JobContext):
    def __init__(self, db, created_by: str | None = "u1"):
        super().__init__(Job(str(uuid.uuid4()), "part_cut", {}, None, created_by, 1, 3))
        self._db, self.charges = db, []

    @property
    def db(self):
        return self._db

    def charge(self, c):
        self.charges.append(c)
        return {}


def db_with(*profiles: dict) -> FakeDB:
    db = FakeDB()
    db.rows["profiles"] = list(profiles)
    return db


def test_job_context_reads_the_tier():
    assert Ctx(db_with(profile("contributor"))).model == "muse-spark-1.3-contributor"
    assert Ctx(db_with(profile("standard"))).model == "muse-spark-1.3"
    assert Ctx(db_with(profile())).model_tier == "standard"                      # no column yet (migration not applied)
    assert Ctx(db_with(profile("contributor")), created_by=None).model_tier == "standard"
    assert Ctx(db_with()).model_tier == "standard"                               # no profile row


def test_a_failed_read_is_standard():
    class Broken(FakeDB):
        def table(self, name):
            raise RuntimeError("column profiles.model_tier does not exist")
    assert Ctx(Broken()).model == "muse-spark-1.3"


def test_job_complete_sends_the_tier_model(monkeypatch):
    seen = {}

    async def fake(user_text, **kw):
        seen.update(kw)
        return Completion("{}", Charge("meta", kw["model"], "spark", Decimal("0.001"), 10, 1))
    monkeypatch.setattr(librarian, "_complete", fake)
    ctx = Ctx(db_with(profile("contributor")))
    c = asyncio.run(ctx.complete("x", effort="minimal"))
    assert seen["model"] == "muse-spark-1.3-contributor" and ctx.charges[0].model == "muse-spark-1.3-contributor"
    asyncio.run(ctx.complete("x", model="muse-spark-1.3"))                     # an explicit model wins
    assert seen["model"] == "muse-spark-1.3" and c.charge.kind == "spark"


def test_load_user_without_the_column(monkeypatch):
    monkeypatch.setattr(auth, "db", lambda: db_with(profile()))
    u = auth.load_user("u1")
    assert u.model_tier == "standard" and u.model == "muse-spark-1.3"
    monkeypatch.setattr(auth, "db", lambda: db_with(profile("contributor")))
    assert auth.load_user("u1").model == "muse-spark-1.3-contributor"


@pytest.fixture
def me_world(monkeypatch):
    db = db_with(profile())
    db.rows["members"] = []
    monkeypatch.setattr(me_routes, "db", lambda: db)
    monkeypatch.setattr(auth, "db", lambda: db)
    monkeypatch.setattr(me_routes, "shared_spend", lambda: Spend(Decimal("1"), Decimal("60")))
    app.dependency_overrides[current_user] = lambda: User("u1", "u1@muse.test", "U1", Decimal("5"), Decimal("0"))
    yield db, TestClient(app)
    app.dependency_overrides.clear()


def test_me_returns_and_sets_the_tier(me_world):
    db, client = me_world
    r = client.get("/me")
    assert r.status_code == 200 and r.json()["model_tier"] == "standard" and r.json()["model"] == "muse-spark-1.3"
    r = client.patch("/me", json={"model_tier": "contributor"})
    assert r.status_code == 200, r.text
    assert r.json()["model_tier"] == "contributor" and r.json()["model"] == "muse-spark-1.3-contributor"
    assert db.rows["profiles"][0]["model_tier"] == "contributor"
    assert client.patch("/me", json={"model_tier": "free"}).status_code == 422
    assert client.patch("/me", json={"display_name": "x"}).status_code == 422


def test_patch_me_before_the_migration_is_503(me_world, monkeypatch):
    class NoColumn(FakeDB):
        def table(self, name):
            q = super().table(name)
            if name == "profiles":
                q.update = lambda row: (_ for _ in ()).throw(RuntimeError("Could not find the 'model_tier' column of 'profiles'"))
            return q
    monkeypatch.setattr(me_routes, "db", lambda: NoColumn())
    assert me_world[1].patch("/me", json={"model_tier": "contributor"}).status_code == 503
