"""demo-video branch: a question parked by `scripts/seed_demo.py` (`result.demo_resume`) is answered by writing the
prepared rows and a follow-up job already `done`, never a queued job (no worker, no Meta call)."""
from __future__ import annotations

from tests.test_routes import OWNER, SCORE, as_user, world  # noqa: F401  (the route fixture)


def parked(db, resume: dict) -> None:
    db.rows["jobs"] = [{"id": "job1", "kind": "omr_convert", "status": "done", "score_id": SCORE, "created_by": "u1",
                        "payload": {"score_id": SCORE, "source_id": "pdf1"},
                        "result": {"question": "Does bar 13 match the page?", "question_payload": {"kind": "match_bar", "bar": 13},
                                   "demo_resume": resume}}]


def spec(note: str) -> dict:
    return {"insert": {"sources": [{"id": "xml1", "score_id": SCORE, "kind": "musicxml", "storage_paths": [f"{SCORE}/digital/score.musicxml"], "meta": {}}]},
            "update": [{"table": "scores", "set": {"playback": {"midi": "m"}}}],
            "result": {"note": note, "source_id": "xml1"}}


def test_the_seeded_answer_lands_done_with_the_prepared_rows(world):  # noqa: F811
    db, client = world
    parked(db, {**spec("34 to check, 13 kept"), "answers": {"reading": spec("34 to check")}})
    as_user(OWNER)
    r = client.post("/jobs/job1/answer", json={"answer": "reading"})
    assert r.status_code == 200
    row = r.json()
    assert row["status"] == "done" and row["payload"]["resume_from"] == "job1" and row["result"]["note"] == "34 to check"
    assert not [j for j in db.rows["jobs"] if j.get("status") == "queued"]
    assert [s["id"] for s in db.rows["sources"] if s.get("kind") == "musicxml"] == ["xml1"]
    assert next(s for s in db.rows["scores"] if s["id"] == SCORE)["playback"] == {"midi": "m"}
    assert client.post("/jobs/job1/answer", json={"answer": "reading"}).status_code == 409    # answered once


def test_an_answer_with_no_spec_of_its_own_takes_the_default(world):  # noqa: F811
    db, client = world
    parked(db, {**spec("35 to check"), "answers": {"reading": spec("34 to check")}})
    as_user(OWNER)
    assert client.post("/jobs/job1/answer", json={"answer": "check"}).json()["result"]["note"] == "35 to check"


def test_a_spec_never_writes_another_book(world):  # noqa: F811
    db, client = world
    bad = spec("x")
    bad["insert"]["sources"][0]["score_id"] = "another-book"
    parked(db, bad)
    as_user(OWNER)
    assert client.post("/jobs/job1/answer", json={"answer": "reading"}).status_code == 400
