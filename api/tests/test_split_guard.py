"""A split never ends silent (CK 2026-11-02, E2E night item 5): a part cut ends in a cut, a parked question, a parked
pause or a failure with its reason, never `done` with nothing cut; `result.outcome` says which and the log's last line
repeats it. The worker fails a `JobFailure` with the reason as it is, without a retry and without failing the book."""
from __future__ import annotations

import json

import pytest

from app import worker
from app.agent.fake import fake_client, text, tool
from app.librarian import HANDLERS, JobFailure
from app.librarian.part_cut import part_cut
from tests.test_part_cut import HEADER, LABEL, LABEL_ABSENT, RECHECK_PIANO, RECHECK_VIOLIN, FakeDB, commit, world


@pytest.fixture(autouse=True)
def _pages_in_call_order(monkeypatch):
    import app.librarian.part_cut as pc
    monkeypatch.setattr(pc, "PREREAD_PAGES", False)


@pytest.mark.asyncio
async def test_a_cut_says_cut():
    client, _ = fake_client([tool("read_header", {}), HEADER, tool("read_page", {"page": 1}), LABEL, commit(1, [4, 5]), RECHECK_PIANO, tool("finish", {})])
    job, ctx, db = world(1)
    out = await part_cut(job, ctx, client=client)
    assert out["systems_cut"] == 1
    assert out["outcome"] == "cut" and out["outcome_reason"] == "1 system cut"
    assert out["agent"]["scratch"]["log"][-1] == "Ended: cut: 1 system cut"


@pytest.mark.asyncio
async def test_a_question_says_question():
    script = [tool("read_header", {}), HEADER, tool("read_page", {"page": 1}), LABEL]
    for _ in range(3):                                   # three refused commits park the run on the admin
        script += [commit(1, [6]), RECHECK_VIOLIN]
    client, _ = fake_client(script)
    job, ctx, db = world(1)
    out = await part_cut(job, ctx, client=client)
    assert out["question"].startswith("Which staves are the Piano's on page 1, line 1")
    assert out["outcome"] == "question" and out["outcome_reason"] == out["question"]


@pytest.mark.asyncio
async def test_a_pause_is_parked_with_its_reason_not_a_finished_split():
    client, t = fake_client([])
    job, ctx, db = world(1, {"max_cost_usd": 0})          # the allowance is spent before the first turn
    out = await part_cut(job, ctx, client=client)
    assert not t.calls and out["paused"]
    assert out["outcome"] == "paused" and "0 systems cut so far" in out["outcome_reason"]
    assert not [r for r in db.rows["sources"] if r["kind"] == "part_images"]
    assert worker.paused_state(out)["state"] == "paused"   # the worker marks it paused (Continue), not done-and-empty


@pytest.mark.asyncio
async def test_all_absent_fails_with_the_reason():
    client, _ = fake_client([tool("read_header", {}), HEADER, tool("read_page", {"page": 1}), LABEL_ABSENT, commit(1, "absent"),
                             tool("read_page", {"page": 2}), LABEL_ABSENT, commit(2, "absent"), tool("finish", {})])
    job, ctx, db = world(2)
    with pytest.raises(JobFailure) as e:
        await part_cut(job, ctx, client=client)
    assert str(e.value).startswith("Nothing was cut: no staves of the Piano were found on pages 1-2 (2 lines without them)")
    assert ctx.result["outcome"] == "failed" and ctx.result["outcome_reason"] == str(e.value)
    assert not [r for r in db.rows["sources"] if r["kind"] == "part_images"]
    assert not db.rows.get("parts")                       # no part row named for a split that made nothing


@pytest.mark.asyncio
async def test_an_agent_that_stops_fails_with_its_reason_once():
    client, t = fake_client([text("I will look at the page first.")] * 6)
    job, ctx, db = world(1)
    with pytest.raises(JobFailure, match="The split of the Piano stopped: the model kept answering in prose"):
        await part_cut(job, ctx, client=client)
    interp = [r for r in db.rows["interpretations"] if r.get("engine") == "part-cut-agent"][0]
    assert interp["status"] == "failed" and interp["summary"]["log"][-1].startswith("Ended: failed: The split of the Piano stopped")


class _Db(FakeDB):
    pass


@pytest.mark.asyncio
async def test_the_worker_fails_a_job_failure_with_its_words_no_retry_and_leaves_the_book(monkeypatch):
    db = _Db()
    db.rows["jobs"] = [{"id": "j1", "kind": "part_cut", "status": "running", "result": {}}]
    db.rows["scores"] = [{"id": "s1", "status": "ready"}]
    monkeypatch.setattr(worker, "db", lambda: db)
    monkeypatch.setattr("app.librarian.JobContext.db", property(lambda self: db))

    async def nothing_cut(job, ctx):
        ctx.result["note"] = "Page 1 of 1, 0 systems cut"
        raise JobFailure("Nothing was cut: no staves of the Piano were found on page 1.")

    monkeypatch.setitem(HANDLERS, "part_cut", nothing_cut)
    await worker.run_one({"id": "j1", "kind": "part_cut", "payload": {"score_id": "s1"}, "score_id": "s1", "created_by": None,
                          "attempts": 1, "max_attempts": 3})
    job = db.rows["jobs"][0]
    assert job["status"] == "failed" and job["error"] == "Nothing was cut: no staves of the Piano were found on page 1."
    assert job["result"]["outcome"] == "failed" and job["result"]["note"] == "Page 1 of 1, 0 systems cut"
    assert db.rows["scores"][0] == {"id": "s1", "status": "ready"}            # the book stays as it was
    assert not [op for op in db.ops if op[0] == "jobs" and op[2] and op[2].get("status") == "queued"]   # no retry


@pytest.mark.asyncio
async def test_a_split_that_crashes_never_fails_the_book(monkeypatch):
    db = _Db()
    db.rows["jobs"] = [{"id": "j2", "kind": "part_cut", "status": "running", "result": {}}]
    db.rows["scores"] = [{"id": "s1", "status": "ready"}]
    monkeypatch.setattr(worker, "db", lambda: db)
    monkeypatch.setattr("app.librarian.JobContext.db", property(lambda self: db))

    async def crash(job, ctx):
        raise RuntimeError("boom")

    monkeypatch.setitem(HANDLERS, "part_cut", crash)
    await worker.run_one({"id": "j2", "kind": "part_cut", "payload": {"score_id": "s1"}, "score_id": "s1", "created_by": None,
                          "attempts": 3, "max_attempts": 3})
    assert db.rows["jobs"][0]["status"] == "failed" and db.rows["scores"][0]["status"] == "ready"
    json.dumps(db.rows)                                      # rows stay plain JSON
