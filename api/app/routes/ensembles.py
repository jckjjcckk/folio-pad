"""Groups through the API (feature 001, 2026-11-02): joining by code with a guess limit, and deleting a group with its
files.

Joining. An 8-digit code is all it takes to join a group, and `join_ensemble` had no limit beyond Supabase's own. Here
every wrong code (malformed or unknown) counts against two sliding windows: the caller's account, 10 in 10 minutes, and
the caller's IP, 30 in 10 minutes (a whole orchestra on one rehearsal Wi-Fi joins at once, and typos happen). At the
limit every attempt, right or wrong, gets 429 with `Retry-After` until the oldest miss leaves the window. A right code
never counts, so joining several groups is never held up. The join itself is done with the service role
and follows `join_ensemble` (migration 20261028150000) step for step, with its sentences. Migration 20261102120000
takes `join_ensemble` away from `authenticated`, so the limit cannot be stepped round by calling the RPC directly.

The limiter lives in this process's memory: right for one API process (yoga's stable API). A second process, or a
restart, starts its own count; several processes would need the count in Postgres or Redis.

Deleting. `delete_ensemble` removes the group's rows by cascade but cannot touch Storage. Here the group's own books
(`scores.ensemble_id` = the group) are found first, every object under each book's folder (`{score_id}/...`, the only
place a book's files are written) is listed, the RPC deletes the group as the caller (so its admin check decides),
and the listed objects are removed with the service role. Books shared with the group by reference belong to their
owner's library: their rows and files stay. `?dry_run=true` checks the caller is an admin and returns what would go,
deleting nothing.
"""
from __future__ import annotations

import logging
import re
import threading
import time
from collections import deque
from typing import Annotated, Any, Callable

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from ..auth import CurrentUser, _bearer
from ..db import db
from ..settings import settings

log = logging.getLogger(__name__)
router = APIRouter()

BUCKET = "scores"
JOIN_LIMIT = 10            # wrong codes per account per window
JOIN_LIMIT_IP = 30         # wrong codes per address per window
JOIN_WINDOW_S = 600.0


# ---------------------------------------------------------------- the guess limit

class AttemptLimiter:
    """At most `limit` attempts per key in any `window` seconds (a sliding window). Thread-safe; in-process only."""

    def __init__(self, limit: int = JOIN_LIMIT, window: float = JOIN_WINDOW_S, clock: Callable[[], float] = time.monotonic):
        self.limit, self.window, self.clock = limit, window, clock
        self._hits: dict[str, deque[float]] = {}
        self._lock = threading.Lock()
        self._calls = 0

    def _prune(self, key: str, now: float) -> deque[float]:
        q = self._hits.get(key)
        if q is None:
            return deque()
        while q and q[0] <= now - self.window:
            q.popleft()
        if not q:
            del self._hits[key]
        return q

    def retry_after(self, keys: list[str]) -> int:
        """Seconds until every key may try again; 0 when none is at its limit."""
        with self._lock:
            now = self.clock()
            wait = 0.0
            for k in keys:
                q = self._prune(k, now)
                if len(q) >= self.limit:
                    wait = max(wait, q[0] + self.window - now)
            return int(wait) + 1 if wait > 0 else 0

    def hit(self, keys: list[str]) -> None:
        with self._lock:
            now = self.clock()
            for k in keys:
                self._prune(k, now)
                self._hits.setdefault(k, deque()).append(now)
            self._calls += 1
            if self._calls % 1000 == 0:          # forget keys whose window has passed
                for k in list(self._hits):
                    self._prune(k, now)

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()


user_limiter = AttemptLimiter(JOIN_LIMIT)
ip_limiter = AttemptLimiter(JOIN_LIMIT_IP)


def client_ip(request: Request) -> str:
    """The caller's address as the edge saw it: Cloudflare's header behind the tunnel, else the first forwarded hop,
    else the socket. On an API reached without Cloudflare the headers can be forged; the per-account limit still holds."""
    h = request.headers
    ip = h.get("cf-connecting-ip") or (h.get("x-forwarded-for") or "").split(",")[0].strip()
    return ip or (request.client.host if request.client else "unknown")


# ---------------------------------------------------------------- join

class JoinBody(BaseModel):
    code: str


def refuse(status: int, message: str, hint: str) -> HTTPException:
    return HTTPException(status, {"message": message, "hint": hint})


@router.post("/ensembles/join")
def join(body: JoinBody, request: Request, user: CurrentUser) -> dict:
    """Join a group by its 8-digit code, as a player. Idempotent. 429 after 10 wrong codes in 10 minutes from one
    account, or 30 from one address."""
    ukey, ikey = [f"user:{user.id}"], [f"ip:{client_ip(request)}"]
    wait = max(user_limiter.retry_after(ukey), ip_limiter.retry_after(ikey))
    if wait:
        minutes = max(1, round(wait / 60))
        raise HTTPException(
            429, {"message": f"Too many join codes tried. Wait {minutes} minute{'s' if minutes != 1 else ''} and try again.",
                  "hint": "too_many_attempts"},
            headers={"Retry-After": str(wait)})

    def miss() -> None:
        user_limiter.hit(ukey)
        ip_limiter.hit(ikey)

    code = re.sub(r"[\s-]", "", body.code or "")
    if not re.fullmatch(r"[0-9]{8}", code):
        miss()
        raise refuse(400, "A join code is 8 digits.", "bad_code")
    rows = db().table("ensembles").select("id").eq("join_code", code).limit(1).execute().data
    if not rows:
        miss()
        raise refuse(400, f"No group has the code {code}. Check the digits with the group's admin.", "unknown_code")
    eid = rows[0]["id"]
    # idempotent: joining twice, or an admin typing their own code, changes nothing (the role stays)
    db().table("members").upsert({"ensemble_id": eid, "user_id": user.id, "role": "player"},
                                  on_conflict="ensemble_id,user_id", ignore_duplicates=True).execute()
    return {"ensemble_id": eid}


# ---------------------------------------------------------------- delete, with the group's files

def list_folder(storage: Any, prefix: str) -> list[str]:
    """Every object key under `prefix` (no trailing slash), depth first. A Storage listing is one level deep and at
    most `limit` entries; a folder comes back with no `id`."""
    out: list[str] = []
    offset, page = 0, 1000
    while True:
        items = storage.from_(BUCKET).list(prefix, {"limit": page, "offset": offset, "sortBy": {"column": "name", "order": "asc"}}) or []
        for it in items:
            key = f"{prefix}/{it['name']}"
            if it.get("id") is None:
                out += list_folder(storage, key)
            else:
                out.append(key)
        if len(items) < page:
            return out
        offset += page


def group_files(client: Any, ensemble_id: str) -> dict:
    """What deleting this group would take from Storage: the files of the group's own books. Books shared with it by
    reference are counted, never listed: they stay with their owner."""
    books = client.table("scores").select("id,title").eq("ensemble_id", ensemble_id).execute().data or []
    shared = client.table("score_shares").select("score_id").eq("ensemble_id", ensemble_id).execute().data or []
    paths: list[str] = []
    for b in books:
        paths += list_folder(client.storage, b["id"])
    return {"books": [{"id": b["id"], "title": b.get("title")} for b in books], "objects": paths,
            "shared_books_kept": len(shared)}


def remove_objects(storage: Any, paths: list[str], chunk: int = 100) -> tuple[int, list[str]]:
    """Remove the keys in chunks. Returns (removed, failed): a failed chunk is logged and reported, not raised, because
    the group's rows are already gone by then."""
    removed, failed = 0, []
    for i in range(0, len(paths), chunk):
        part = paths[i:i + chunk]
        try:
            storage.from_(BUCKET).remove(part)
            removed += len(part)
        except Exception as e:  # noqa: BLE001
            log.warning("group delete: %d storage objects not removed: %s", len(part), e)
            failed += part
    return removed, failed


def rpc_as_user(token: str, name: str, args: dict) -> httpx.Response:
    """Call an RPC as the signed-in user (their token decides auth.uid() and RLS; the secret key only passes the
    gateway, as tested on hosted 2026-11-02)."""
    return httpx.post(f"{settings.supabase_url.rstrip('/')}/rest/v1/rpc/{name}", json=args, timeout=30,
                      headers={"apikey": settings.supabase_secret_key, "Authorization": f"Bearer {token}"})


def _token(request: Request) -> str:
    return _bearer(request)


@router.delete("/ensembles/{ensemble_id}")
def delete_ensemble(ensemble_id: str, user: CurrentUser, token: Annotated[str, Depends(_token)], dry_run: bool = False) -> dict:
    """Delete a group (admins only) and the files of its own books. `dry_run=true` returns what would go."""
    client = db()
    if not client.table("ensembles").select("id").eq("id", ensemble_id).limit(1).execute().data:
        raise refuse(404, "This group no longer exists.", "not_found")
    me = client.table("members").select("role").eq("ensemble_id", ensemble_id).eq("user_id", user.id).limit(1).execute().data
    if not me or me[0]["role"] != "admin":
        raise refuse(403, "Only an admin can delete this group.", "not_admin")
    plan = group_files(client, ensemble_id)
    out = {"ensemble_id": ensemble_id, "dry_run": dry_run, **plan}
    if dry_run:
        return out
    r = rpc_as_user(token, "delete_ensemble", {"ensemble": ensemble_id})
    if r.status_code >= 300:
        err = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
        status = {"not_admin": 403, "not_found": 404}.get(err.get("hint"), 400 if err.get("hint") else 502)
        raise refuse(status, err.get("message") or "The group could not be deleted just now. Try again in a moment.",
                     err.get("hint") or "rpc_failed")
    removed, failed = remove_objects(client.storage, plan["objects"])
    return {**out, "removed": removed, "failed": failed}
