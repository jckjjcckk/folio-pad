"""CK's 2026-11-02 decisions on jobs (018 follow-ups), against fakes, no network:
  - a convert job is visible to every member (`jobs.score_id` set) and still never moves the PDF book's own state;
  - a run paused at its turn limit is shown paused, not failed, and can be continued (`POST /jobs/{id}/resume`);
  - a parked or paused job resumes on the model tier it started on, whatever the profile says by then."""
from __future__ import annotations

import uuid

import pytest

from app import worker
from app.librarian import HANDLERS, Job, JobContext, SIDE_KINDS, paused_state
from tests.test_model_tier import db_with, profile
from tests.test_part_cut import FakeDB
from tests.test_routes import OTHER, OWNER, SCORE, as_user, world  # noqa: F401  (the route fixture)


class Ctx(JobContext):
    def __init__(self, job: Job, db):
        super().__init__(job)
        self._db = db

    @property
    def db(self):
        return self._db


# ---------------------------------------------------------------------------------------------------- convert visible to members

@pytest.fixture
def worker_db(monkeypatch):
    db = FakeDB()
    db.rows["scores"] = [{"id": SCORE, "status": "ready", "progress": 1.0}]
    monkeypatch.setattr(worker, "db", lambda: db)
    monkeypatch.setattr(worker, "JobContext", lambda job: Ctx(job, db))
    return db


def row(kind: str, **kw) -> dict:
    return {"id": str(uuid.uuid4()), "kind": kind, "payload": {"score_id": SCORE}, "score_id": SCORE, "created_by": "u1",
            "attempts": 1, "max_attempts": 1, **kw}


async def test_a_failed_convert_with_its_book_on_the_row_never_fails_the_book(worker_db, monkeypatch):
    assert "omr_convert" in SIDE_KINDS

    async def failing(job, ctx):
        await ctx.progress(0.4, "Reading 3 pages of music")
        raise RuntimeError("The transcription engine could not read this PDF")
    monkeypatch.setitem(HANDLERS, "omr_convert", failing)
    r = row("omr_convert")
    worker_db.rows["jobs"] = [dict(r)]
    await worker.run_one(r)
    assert worker_db.rows["jobs"][0]["status"] == "failed"
    assert worker_db.rows["scores"][0] == {"id": SCORE, "status": "ready", "progress": 1.0}      # neither failed nor moved


async def test_a_book_owning_job_still_fails_its_book(worker_db, monkeypatch):
    async def failing(job, ctx):
        await ctx.progress(0.4)
        raise RuntimeError("boom")
    monkeypatch.setitem(HANDLERS, "import_musicxml", failing)
    r = row("import_musicxml")
    worker_db.rows["jobs"] = [dict(r)]
    await worker.run_one(r)
    s = worker_db.rows["scores"][0]
    assert s["status"] == "failed" and s["progress"] == 0.4


def test_the_convert_route_puts_the_book_on_the_row(monkeypatch):
    from fastapi.testclient import TestClient

    from app.main import app
    from app.routes import convert as convert_routes, scores as scores_routes
    from app.spend import require_budget
    db = FakeDB()
    db.rows["scores"] = [{"id": SCORE, "owner_user_id": "u1", "ensemble_id": None}]
    db.rows["sources"] = [{"id": "pdf1", "score_id": SCORE, "kind": "pdf"}]
    db.rows["members"] = []
    monkeypatch.setattr(scores_routes, "db", lambda: db)
    monkeypatch.setattr(convert_routes, "db", lambda: db)
    app.dependency_overrides[require_budget] = lambda: OWNER
    try:
        j = TestClient(app).post(f"/scores/{SCORE}/convert").json()
    finally:
        app.dependency_overrides.clear()
    assert j["score_id"] == SCORE and j["payload"]["score_id"] == SCORE      # RLS can_read_score shows it to every member


# ---------------------------------------------------------------------------------------------------- paused, not failed

def paused_result(reason: str = "turn_limit") -> dict:
    return {"paused": "Paused: turn limit reached", "agent": {"status": "paused", "pause_reason": reason, "turn": 26, "cost_usd": 0.31},
            "phase": {"page": 3, "pages": 4, "systems_cut": 9}, "model_tier": "contributor"}


def test_a_paused_result_is_marked_paused_with_its_reason():
    out = paused_state(paused_result())
    assert out["state"] == "paused" and out["pause"] == {"reason": "turn_limit", "message": "Paused after its turn allowance",
                                                          "turns": 26, "cost_usd": 0.31, "resumable": True}
    assert paused_state({**paused_result(), "agent": {}, "paused": "Paused: cost limit reached"})["pause"]["reason"] == "cost_limit"
    assert paused_state({"question": "Which staves?", "paused": "x"}) == {"question": "Which staves?", "paused": "x"}
    assert paused_state({"source_id": "s"}) == {"source_id": "s"}


async def test_the_worker_writes_a_paused_run_as_paused(worker_db, monkeypatch):
    async def pausing(job, ctx):
        ctx.result.update(paused_result())
        return ctx.result
    monkeypatch.setitem(HANDLERS, "part_cut", pausing)
    r = row("part_cut")
    worker_db.rows["jobs"] = [dict(r)]
    await worker.run_one(r)
    j = worker_db.rows["jobs"][0]
    assert j["status"] == "done" and j["result"]["state"] == "paused" and j["result"]["pause"]["reason"] == "turn_limit"


def paused_job(db, job_id: str = "job1", **result) -> dict:
    r = {"id": job_id, "kind": "part_cut", "status": "done", "score_id": SCORE, "created_by": "u1",
         "payload": {"score_id": SCORE, "instruments": ["Piano"], "parts_key": "piano"},
         "result": {**paused_state(paused_result()), **result}}
    db.rows.setdefault("jobs", []).append(r)
    return r


def test_resume_queues_the_paused_run_on_its_tier(world):  # noqa: F811
    db, client = world
    paused_job(db)
    as_user(OWNER)
    r = client.post("/jobs/job1/resume")
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["kind"] == "part_cut" and j["status"] == "queued" and j["score_id"] == SCORE and j["created_by"] == "u1"
    assert j["payload"] == {"score_id": SCORE, "instruments": ["Piano"], "parts_key": "piano", "resume_from": "job1", "model_tier": "contributor"}
    assert "answer" not in j["payload"]                                       # part_cut resumes without committing anything
    assert client.post("/jobs/job1/resume").status_code == 409               # continued once


def test_resume_refuses_what_is_not_paused(world):  # noqa: F811
    db, client = world
    as_user(OWNER)
    assert client.post("/jobs/nope/resume").status_code == 404
    paused_job(db, question="Which staves?")
    assert client.post("/jobs/job1/resume").status_code == 409               # a question is answered, not continued
    db.rows["jobs"] = [{"id": "job2", "kind": "part_cut", "status": "done", "score_id": SCORE, "payload": {}, "result": {"source_id": "x"}}]
    assert client.post("/jobs/job2/resume").status_code == 409               # finished
    db.rows["jobs"] = []
    paused_job(db)
    as_user(OTHER)
    assert client.post("/jobs/job1/resume").status_code == 403


def test_the_answer_route_pins_the_tier_the_parked_job_ran_on(world):  # noqa: F811
    db, client = world
    db.rows["jobs"] = [{"id": "job1", "kind": "part_cut", "status": "done", "score_id": SCORE, "created_by": "u1",
                        "payload": {"score_id": SCORE, "instruments": ["Piano"]},
                        "result": {"question": "Which staves?", "question_payload": {"kind": "choose_staves", "page": 1, "system": 1},
                                   "model_tier": "contributor"}}]
    as_user(OWNER)
    r = client.post("/jobs/job1/answer", json={"staves": [1, 2]})
    assert r.status_code == 200 and r.json()["payload"]["model_tier"] == "contributor"


# ---------------------------------------------------------------------------------------------------- the tier a chain started on

def job(payload: dict | None = None) -> Job:
    return Job(str(uuid.uuid4()), "part_cut", payload or {}, SCORE, "u1", 1, 3)


def test_a_job_records_its_tier_at_its_first_read():
    ctx = Ctx(job(), db_with(profile("contributor")))
    assert ctx.model == "muse-spark-1.3-contributor" and ctx.result["model_tier"] == "contributor"


def test_a_resumed_job_runs_on_the_tier_its_chain_started_on_whatever_the_profile_says():
    db = db_with(profile("standard"))                                         # the profile changed after the park
    db.rows["jobs"] = [{"id": "parked", "payload": {}, "result": {"model_tier": "contributor", "question": "Which staves?"}}]
    ctx = Ctx(job({"resume_from": "parked"}), db)
    assert ctx.model_tier == "contributor" and ctx.model == "muse-spark-1.3-contributor"
    assert ctx.result["model_tier"] == "contributor"
    db.rows["jobs"] = [{"id": "parked", "payload": {"model_tier": "standard"}, "result": {}}]
    db.rows["profiles"] = [profile("contributor")]
    assert Ctx(job({"resume_from": "parked"}), db).model_tier == "standard"   # pinned on the parked job's payload


def test_a_pinned_payload_wins_and_an_old_parked_job_falls_back_to_the_profile():
    db = db_with(profile("standard"))
    assert Ctx(job({"model_tier": "contributor", "resume_from": "x"}), db).model_tier == "contributor"
    db.rows["jobs"] = [{"id": "old", "payload": {}, "result": {"question": "?"}}]       # parked before the tier was recorded
    assert Ctx(job({"resume_from": "old"}), db).model_tier == "standard"
    assert Ctx(job({"model_tier": "gold"}), db_with(profile("contributor"))).model_tier == "contributor"   # not a tier: ignored
