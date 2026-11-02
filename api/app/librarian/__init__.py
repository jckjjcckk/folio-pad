"""Job handlers: the librarian's work. One function per job kind, registered with @handler.

The worker (app/worker.py) claims jobs and calls these. See docs/librarian-contract.md for what a handler
may touch and what it must write. Handlers for the intelligence thread live beside this file.
"""
from __future__ import annotations

import base64
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from ..db import db as _db
from ..llm import Completion, complete as _complete
from ..auth import User, load_user
from ..spend import Charge, charge as _charge
from ..tiers import DEFAULT_TIER, TIERS, model_name, tier_of

log = logging.getLogger("folio.librarian")


@dataclass(frozen=True)
class Job:
    id: str
    kind: str
    payload: dict[str, Any]
    score_id: str | None
    created_by: str | None
    attempts: int
    max_attempts: int

    @staticmethod
    def from_row(r: dict[str, Any]) -> "Job":
        return Job(r["id"], r["kind"], r.get("payload") or {}, r.get("score_id"), r.get("created_by"), r.get("attempts", 1), r.get("max_attempts", 3))

    @property
    def owns_score(self) -> bool:
        """The job's book takes its status and meter from this job: a failure marks the book failed and progress moves
        its meter. A job that works beside a ready book (`SIDE_KINDS`) carries `score_id` only so everyone who can read
        the book sees it (RLS `jobs_select`, the shelf's Realtime), never to move the book's own state."""
        return bool(self.score_id) and self.kind not in SIDE_KINDS


# Jobs that work beside a ready book and never move its status or meter (2026-11-02, CK: a convert job is visible to
# every member, so `jobs.score_id` is set on it now; before, it stayed null so the worker could not fail the PDF book).
# A split (008) makes strips or a notation file from a ready book: its failure is the split's, never the book's.
SIDE_KINDS = frozenset({"omr_convert", "part_cut", "part_split"})


@dataclass
class JobContext:
    job: Job
    result: dict[str, Any] = field(default_factory=dict)
    _model_tier: str | None = field(default=None, repr=False, compare=False)

    @property
    def db(self):
        return _db()

    @property
    def user(self) -> User | None:
        return load_user(self.job.created_by) if self.job.created_by else None

    @property
    def model_tier(self) -> str:
        """The tier this job's model calls run on, settled once per job and kept on the row (`result.model_tier`).

        A job that resumes another (`payload.resume_from`: an answered question, a paused run continued) runs on the
        tier the first job of the chain started on, even when the profile changed meanwhile (CK 2026-11-02: a parked job
        resumes on the tier it started on; a transcript is not replayed across models). In order: the tier pinned in
        the payload (`payload.model_tier`, the answer and resume routes copy it), the tier the resumed job recorded,
        then the creator's `profiles.model_tier`. Standard (non-training) when the job has no user, the column is not
        there yet (migration not applied) or a read fails."""
        if self._model_tier is None:
            tier = self._pinned_tier()
            if tier is None:
                tier = DEFAULT_TIER
                if self.job.created_by:
                    try:
                        rows = self.db.table("profiles").select("*").eq("id", self.job.created_by).limit(1).execute().data or []
                        tier = tier_of(rows[0].get("model_tier")) if rows else DEFAULT_TIER
                    except Exception as e:  # noqa: BLE001  (the privacy-preserving tier is the fallback)
                        log.warning("job %s: model tier not read, standard: %s", self.job.id, e)
            self._model_tier = tier
            self.result["model_tier"] = tier          # on the row with the next progress write and the job's end
        return self._model_tier

    def _pinned_tier(self) -> str | None:
        p = self.job.payload or {}
        if p.get("model_tier") in TIERS:
            return p["model_tier"]
        if p.get("resume_from"):
            try:
                rows = self.db.table("jobs").select("payload,result").eq("id", p["resume_from"]).limit(1).execute().data or []
            except Exception as e:  # noqa: BLE001
                log.warning("job %s: the resumed job's tier not read: %s", self.job.id, e)
                return None
            if rows:
                prev = rows[0]
                for t in ((prev.get("result") or {}).get("model_tier"), (prev.get("payload") or {}).get("model_tier")):
                    if t in TIERS:
                        return t
        return None

    @property
    def model(self) -> str:
        """The Spark model every call of this job uses: the user's tier (`tiers.model_name`)."""
        return model_name(self.model_tier)

    async def progress(self, fraction: float, note: str | None = None) -> None:
        if note:
            self.result["note"] = note
        self.db.table("jobs").update({"progress": max(0.0, min(1.0, fraction)), "result": self.result}).eq("id", self.job.id).execute()
        if self.job.owns_score:
            self.db.table("scores").update({"progress": max(0.0, min(1.0, fraction))}).eq("id", self.job.score_id).execute()

    def charge(self, c: Charge) -> dict:
        u = self.user
        return _charge(u, c, job_id=self.job.id) if u else {}

    async def complete(self, user_text: str, **kw) -> Completion:
        kw.setdefault("model", self.model)
        c = await _complete(user_text, **kw)
        self.charge(c.charge)
        return c

    def storage_download(self, path: str) -> bytes:
        return self.db.storage.from_("scores").download(path)

    def storage_upload(self, path: str, data: bytes, content_type: str) -> None:
        self.db.storage.from_("scores").upload(path, data, {"content-type": content_type, "upsert": "true"})

    def needs_review(self, question: str, payload: dict[str, Any] | None = None, interpretation_id: str | None = None) -> dict:
        """Park the run on a question for the admin. The job finishes; the answer queues a follow-up job."""
        self.result["question"] = question
        self.result["question_payload"] = payload or {}
        if interpretation_id:
            self.db.table("interpretations").update({"status": "needs_review"}).eq("id", interpretation_id).execute()
        return self.result

    @staticmethod
    def png_b64(data: bytes) -> str:
        return base64.b64encode(data).decode()

    @staticmethod
    def now() -> str:
        return datetime.now(timezone.utc).isoformat()


PAUSE_WORDS = {"turn_limit": "Paused after its turn allowance", "cost_limit": "Paused at its spending allowance"}


def paused_state(result: dict[str, Any]) -> dict[str, Any]:
    """A run that stopped at its turn or cost allowance (the agent loop's `paused`, 006) ends its job `done` like any
    other, but it made nothing and asked nothing: it is marked `result.state = "paused"` with `result.pause =
    {reason, message, turns, cost_usd, resumable}` so the iPad shows it paused, not failed, and offers Continue
    (`POST /jobs/{id}/resume`). A run that asked a question stays a question. Anything else comes back unchanged."""
    if not result.get("paused") or result.get("question"):
        return result
    agent = result.get("agent") or {}
    reason = agent.get("pause_reason")
    if reason not in PAUSE_WORDS:
        text = str(result.get("paused") or "")
        reason = "cost_limit" if "cost" in text else "turn_limit"
    return {**result, "state": "paused",
            "pause": {"reason": reason, "message": PAUSE_WORDS[reason], "turns": agent.get("turn"),
                      "cost_usd": agent.get("cost_usd"), "resumable": True}}


class ScoreFailure(Exception):
    """A failure a musician can read: the message goes to `scores.failure_reason` as it is, and the worker does not
    retry (the file will not change between attempts). Anything else is a fault: retried, then reported in
    general words while `jobs.error` keeps the technical text."""


class JobFailure(Exception):
    """This job could not do what it was asked, for a reason a musician can read (the message, as it is, goes to
    `jobs.error`); the worker does not retry it and the book is left as it was. A split that ends with nothing cut
    (008, CK 2026-11-02) is one: the book is still readable, only the split did not happen."""


Handler = Callable[[Job, JobContext], Awaitable[dict[str, Any] | None]]
HANDLERS: dict[str, Handler] = {}


def handler(kind: str) -> Callable[[Handler], Handler]:
    def wrap(fn: Handler) -> Handler:
        HANDLERS[kind] = fn
        return fn
    return wrap


def load_handlers() -> None:
    """Import every handler module so it registers. Add new modules here."""
    from . import engrave, import_musicxml, import_pdf, part_cut, part_split, transcribe_voice  # noqa: F401
    try:
        from . import process_pages, transcribe_voice, brief  # noqa: F401  (intelligence thread)
    except ImportError:
        pass
