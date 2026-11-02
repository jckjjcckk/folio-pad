"""Jobs: answering a parked question (feature 011). A handler that cannot decide parks its job `done` with
`result.question` and a typed `result.question_payload`; the admin's answer queues a follow-up job of the same
kind with the same payload plus `answer` and `resume_from`, which the handler resumes from the saved state. The
answered split's interpretation goes back to `running` at once (the reading's own stays `needs_review` until the
resumed `process_pages` picks it up by that status).

A run paused at its turn or cost allowance (`result.state = "paused"`, 2026-11-02) is continued the same way without an
answer: `POST /jobs/{id}/resume` queues the follow-up with `resume_from` and no `answer`; the agent loop gives the run a
fresh allowance from where it stopped (006). Both routes pin the follow-up to the tier the chain started on
(`payload.model_tier`), so a profile changed meanwhile never moves a parked transcript to another model."""
from typing import Any

from fastapi import APIRouter, HTTPException

from ..db import db
from ..spend import BudgetedUser
from ..tiers import TIERS
from .live_jobs import insert_job, parts_key
from .scores import assert_can_edit

router = APIRouter()


@router.post("/jobs/{job_id}/answer")
def answer_job(job_id: str, body: dict[str, Any], user: BudgetedUser) -> dict:
    """Answer a parked job. The body is the answer in the shape `result.question_payload.answer_format` gives
    (`{"staves": [11, 12]}`, `{"blocks": [[11], [13]]}`, `{"staves": "absent"}`). Returns the new job row."""
    rows = db().table("jobs").select("id,kind,status,score_id,payload,result").eq("id", job_id).limit(1).execute().data
    if not rows:
        raise HTTPException(404, "No such job")
    job = rows[0]
    if not job.get("score_id"):
        raise HTTPException(400, "This job has no score")
    assert_can_edit(user, job["score_id"])
    result = job.get("result") or {}
    if job["status"] != "done" or not result.get("question"):
        raise HTTPException(409, "This job is not waiting for an answer")
    if not isinstance(body, dict) or not body or not ("staves" in body or "blocks" in body or "answer" in body):
        raise HTTPException(400, "The answer must be an object with staves, blocks or answer")
    already = db().table("jobs").select("id").eq("payload->>resume_from", job_id).limit(1).execute().data
    if already:
        raise HTTPException(409, "This question was already answered")
    payload = {k: v for k, v in (job.get("payload") or {}).items() if k not in ("answer", "resume_from")}
    q = result.get("question_payload") or {}
    if q.get("interpretation_id") and not payload.get("interpretation_id"):
        payload["interpretation_id"] = q["interpretation_id"]
    payload.update({"answer": body["answer"] if set(body) == {"answer"} else body, "resume_from": job_id})
    row = _follow_up(job, payload, user.id)
    if job["kind"] == "part_cut" and q.get("interpretation_id"):
        # The split's own run stops asking the moment it is answered: its interpretation said `needs_review` until the
        # resumed run wrote it again at its very end, minutes later, and the book showed a question nobody could answer.
        db().table("interpretations").update({"status": "running"}).eq("id", q["interpretation_id"]).eq("status", "needs_review").execute()
    return row


def _follow_up(job: dict, payload: dict, user_id: str) -> dict:
    """Queue the job that picks `job` up: same kind and book, the parked run's tier pinned, the split's parts key kept."""
    tier = (job.get("result") or {}).get("model_tier") or (job.get("payload") or {}).get("model_tier")
    if tier in TIERS:
        payload["model_tier"] = tier
    key = payload.get("parts_key") if job["kind"] == "part_cut" else None
    if job["kind"] == "part_cut" and key is None:
        key = payload["parts_key"] = parts_key(payload.get("instruments") or ([payload["instrument"]] if payload.get("instrument") else []))
    return insert_job({"kind": job["kind"], "status": "queued", "score_id": job["score_id"], "created_by": user_id, "payload": payload}, key)


@router.post("/jobs/{job_id}/resume")
def resume_job(job_id: str, user: BudgetedUser) -> dict:
    """Continue a run that paused at its turn or cost allowance (`result.state == "paused"`). Owner or admin of the book
    (403), budget left (402), 404 no such job, 409 when the job is not paused or was continued already. Returns the new
    job row (same kind, same payload, `resume_from` set, no answer)."""
    rows = db().table("jobs").select("id,kind,status,score_id,payload,result").eq("id", job_id).limit(1).execute().data
    if not rows:
        raise HTTPException(404, "No such job")
    job = rows[0]
    if not job.get("score_id"):
        raise HTTPException(400, "This job has no score")
    assert_can_edit(user, job["score_id"])
    result = job.get("result") or {}
    if job["status"] != "done" or result.get("state") != "paused" or result.get("question"):
        raise HTTPException(409, "This job is not paused")
    already = db().table("jobs").select("id").eq("payload->>resume_from", job_id).limit(1).execute().data
    if already:
        raise HTTPException(409, "This run was already continued")
    payload = {k: v for k, v in (job.get("payload") or {}).items() if k not in ("answer", "resume_from")}
    payload["resume_from"] = job_id
    return _follow_up(job, payload, user.id)
