"""Record the on-camera Minuet for the demo video: watch demo@folio.com's new book while CK uploads and converts it on
the iPad, then write one record the video build reads, in the shape of `experiments/e2e_night/imslp_1104/<cut>.json`.

    cd api && uv run scripts/demo_take.py            # start it before the upload; it ends when the convert ends
    cd api && uv run scripts/demo_take.py --last     # no watcher ran: write the record of the latest book from its rows

Read only (no Meta call, no write to the project). It polls every second, so every note the iPad showed is in `polls`
with the time it was seen; each Spark call is in `jobs[].usage_events` with the time it returned. The record lands in
`api/experiments/e2e_night/demo_take/<utc>-<title>.json` (uncommitted, like the other run folders). The seeded books
(the quartet, the concerto, the polonaise) are ignored: only a book made after the watcher started, or with --last the
newest book that is not one of the three, is recorded.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from seed_demo import EMAIL, load_env  # noqa: E402

SEEDED = ("String Quartet No. 1 in F major", "Piano Concerto No. 3 in C minor", "Polonaise in C♯ minor")
KINDS = ("import_pdf", "process_pages", "omr_convert")
OUT = Path(__file__).resolve().parents[1] / "experiments" / "e2e_night" / "demo_take"


def utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def secs(a: str | None, b: str | None) -> float | None:
    if not a or not b:
        return None
    return round((datetime.fromisoformat(b) - datetime.fromisoformat(a)).total_seconds(), 2)


def book_jobs(d, sid: str) -> list[dict]:
    return d.table("jobs").select("*").eq("score_id", sid).order("created_at").execute().data or []


def record(d, sid: str, polls: dict, started: str) -> Path:
    score = d.table("scores").select("*").eq("id", sid).single().execute().data
    jobs = []
    for j in book_jobs(d, sid):
        ev = d.table("usage_events").select("*").eq("job_id", j["id"]).order("created_at").execute().data or []
        jobs.append({"row": j, "usage_events": ev, "queue_s": secs(j["created_at"], j.get("started_at")),
                     "run_s": secs(j.get("started_at"), j.get("finished_at")), "calls": len(ev),
                     "in_tok": sum(e["input_tokens"] for e in ev), "out_tok": sum(e["output_tokens"] for e in ev),
                     "usd": round(sum(float(e["cost_usd"]) for e in ev), 6)})
    by = {j["row"]["kind"]: j for j in jobs}
    conv, read = by.get("omr_convert"), by.get("process_pages")
    xml = next((s for s in reversed(d.table("sources").select("*").eq("score_id", sid).order("created_at").execute().data or [])
                if s["kind"] == "musicxml"), None)
    summary = {"score_id": sid, "title": score["title"], "pages": score.get("pages"),
               "reading_s": read and read["run_s"], "reading_usd": read and read["usd"], "reading_calls": read and read["calls"],
               "convert_s": conv and conv["run_s"], "convert_usd": conv and conv["usd"], "convert_calls": conv and conv["calls"],
               "status": conv and conv["row"]["status"], "note": conv and (conv["row"].get("result") or {}).get("note"),
               "bars": conv and (conv["row"].get("result") or {}).get("bars"),
               "flagged": conv and len((conv["row"].get("result") or {}).get("flagged_bars") or []),
               "musicxml_source": xml and xml["id"]}
    OUT.mkdir(parents=True, exist_ok=True)
    slug = re.sub(r"[^a-z0-9]+", "-", score["title"].lower()).strip("-")[:40]
    path = OUT / f"{started[:19].replace(':', '')}-{slug}.json"
    path.write_text(json.dumps({"title": score["title"], "account": EMAIL, "score_id": sid, "started_utc": started, "finished_utc": utc(),
                                "polls": polls, "jobs": jobs, "sources": d.table("sources").select("*").eq("score_id", sid).execute().data,
                                "score": score, "summary": summary}, indent=1, default=str))
    return path


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--last", action="store_true", help="write the record of the newest unseeded book now, without watching")
    ap.add_argument("--env", type=Path, default=Path(__file__).resolve().parents[1] / ".env")
    a = ap.parse_args()
    load_env(a.env)
    from app.db import db
    d = db()
    uid = d.table("profiles").select("id").eq("email", EMAIL).single().execute().data["id"]
    started = utc()
    mine = lambda: [s for s in (d.table("scores").select("id,title,created_at").eq("owner_user_id", uid).order("created_at").execute().data or [])
                    if s["title"] not in SEEDED]
    if a.last:
        books = mine()
        assert books, f"{EMAIL} has no book besides the seeded three"
        print(record(d, books[-1]["id"], {}, books[-1]["created_at"]))
        return
    before = {s["id"] for s in mine()}
    print(f"watching {EMAIL} from {started}; upload the Minuet on the iPad now (Ctrl-C to stop)")
    sid, polls, last = None, {k: [] for k in KINDS}, {}
    try:
        while True:
            if sid is None:
                new = [s for s in mine() if s["id"] not in before]
                if new:
                    sid = new[-1]["id"]
                    print(f"book: {new[-1]['title']} ({sid})")
            if sid:
                for j in book_jobs(d, sid):
                    r = j.get("result") or {}
                    seen = {"seen_utc": utc(), "status": j["status"], "progress": j["progress"], "note": r.get("note"),
                            "attempts": j["attempts"], "started_at": j.get("started_at")}
                    key = (j["status"], j["progress"], r.get("note"))
                    if j["kind"] in polls and last.get(j["id"]) != key:
                        last[j["id"]] = key
                        polls[j["kind"]].append(seen)
                        print(f"  {j['kind']:13} {j['status']:8} {round(100 * j['progress']):3}% {r.get('note') or ''}")
                    if j["kind"] == "omr_convert" and j["status"] in ("done", "failed"):
                        raise StopIteration
            time.sleep(1)
    except (KeyboardInterrupt, StopIteration):
        pass
    if sid:
        print(record(d, sid, polls, started))
    else:
        print("no new book seen; nothing written")


if __name__ == "__main__":
    main()
