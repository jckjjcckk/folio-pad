"""Seat names vs part names (E2E night item 1, CK 2026-11-02): a group with a seat "Violin II" and a book whose part is
printed "Violino II" shows that part on the seat's stand, and a mark addressed to "Violino II" reaches that seat.

    cd api && PYTHONPATH=. ENGRAVE=off uv run python -m experiments.e2e_night.seat_check --local   # the local stack
    cd api && PYTHONPATH=. ENGRAVE=off uv run python -m experiments.e2e_night.seat_check            # api/.env's project

The real chain minus the device: the service role sets up a group "Seat check" (admin, a "Violin II" seat, a "Violin I"
seat), and a group book from a two-part MusicXML printed "Violino I" / "Violino II"; the `import_musicxml` handler runs
here through `worker.run_one` (no model, $0; ENGRAVE=off skips the box); a live mark for the part "Violino II" is
written as the admin. Then each player, with a session from the service role (`generate_link` + `verify`, no
password), reads what the iPad reads under RLS (`parts *`, `members *`, the marks) and the stand's own matcher
(`web/src/app/seat.ts`, run by node) picks the seat's part. Idempotent: the group and the book are reused by name.
Prints no key, no token, no URL. Needs migration 20261102130000 on the stack; without it, it says so and stops.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import httpx

GROUP = "Seat check"
TITLE = "Seat check: Violino I, Violino II"
ROOT = Path(__file__).resolve().parents[3]


def musicxml() -> bytes:
    from music21 import instrument, note, stream
    from music21.musicxml.m21ToXml import GeneralObjectExporter
    s = stream.Score()
    for name, pitch in (("Violino I", "E5"), ("Violino II", "C5")):
        p = stream.Part()
        p.partName = name
        p.insert(0, instrument.Violin())
        p.getElementsByClass(instrument.Instrument)[0].partName = name
        for _ in range(4):
            m = stream.Measure()
            m.append(note.Note(pitch, quarterLength=4))
            p.append(m)
        s.insert(0, p)
    return GeneralObjectExporter(s).parse()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--local", action="store_true")
    a = ap.parse_args()
    if a.local:
        from app.librarian.run import point_at_local_stack
        point_at_local_stack(allow_remote=False)
        st = json.loads(subprocess.check_output(["supabase", "status", "-o", "json"], cwd=ROOT, stderr=subprocess.DEVNULL))
        sb_url, pub = st["API_URL"], st["PUBLISHABLE_KEY"]
        admin_email, seats = "admin@muse.test", {"violin2@muse.test": "Violin II", "violin1@muse.test": "Violin I"}
    else:
        env = dict(l.split("=", 1) for l in (ROOT / "web" / ".env").read_text().splitlines() if "=" in l and not l.lstrip().startswith("#"))
        sb_url, pub = env["VITE_SUPABASE_URL"].strip().strip('"'), env["VITE_SUPABASE_PUBLISHABLE_KEY"].strip().strip('"')
        admin_email, seats = "admin1@muse.test", {"test1@muse.test": "Violin II", "test2@muse.test": "Violin I"}
    os.environ.setdefault("ENGRAVE", "off")
    from app.db import db
    from app.librarian.instruments import store_seat_canonicals
    from app.librarian import load_handlers
    from app.worker import run_one
    load_handlers()
    d = db()

    probe = d.table("parts").select("*").limit(1).execute().data
    mem = d.table("members").select("*").limit(1).execute().data
    if (probe and "canonical" not in probe[0]) or (mem and "part_canonical" not in mem[0]):
        sys.exit("this stack has no canonical columns (migration 20261102130000 not applied): the seat cannot match yet")

    ids = {p["email"]: p["id"] for p in d.table("profiles").select("id,email").execute().data}
    for e in (admin_email, *seats):
        assert e in ids, f"{e} has no profile on this stack"
    ens = d.table("ensembles").select("id").eq("name", GROUP).execute().data
    eid = ens[0]["id"] if ens else d.table("ensembles").insert({"name": GROUP, "created_by": ids[admin_email]}).execute().data[0]["id"]
    for e, seat in seats.items():
        d.table("members").upsert({"ensemble_id": eid, "user_id": ids[e], "role": "player", "part": seat, "display_name": e.split("@")[0]},
                                  on_conflict="ensemble_id,user_id").execute()
    store_seat_canonicals(d, eid)

    book = d.table("scores").select("id,status").eq("ensemble_id", eid).eq("title", TITLE).execute().data
    if book and book[0]["status"] == "ready":
        sid = book[0]["id"]
    else:
        sid = book[0]["id"] if book else d.table("scores").insert({"ensemble_id": eid, "created_by": ids[admin_email], "title": TITLE,
                                                                     "status": "processing", "progress": 0}).execute().data[0]["id"]
        key = f"{sid}/source.musicxml"
        d.storage.from_("scores").upload(key, musicxml(), {"content-type": "application/vnd.recordare.musicxml+xml", "upsert": "true"})
        src = d.table("sources").insert({"score_id": sid, "kind": "musicxml", "storage_paths": [key], "created_by": ids[admin_email],
                                         "meta": {"filename": "seat-check.musicxml"}}).execute().data[0]
        now = datetime.now(timezone.utc).isoformat()
        job = d.table("jobs").insert({"kind": "import_musicxml", "status": "running", "attempts": 1, "score_id": sid, "created_by": ids[admin_email],
                                      "payload": {"score_id": sid, "source_id": src["id"]}, "locked_at": now, "started_at": now}).execute().data[0]
        asyncio.run(run_one(job))
        print("import:", d.table("jobs").select("status,error").eq("id", job["id"]).single().execute().data)
    parts = d.table("parts").select("name,canonical").eq("score_id", sid).order("position").execute().data
    print("book parts (printed -> canonical):", [(p["name"], p["canonical"]) for p in parts])

    # A live mark for the part as printed, by the admin (what a voice note or the admin's pencil writes).
    if not d.table("annotations").select("id").eq("score_id", sid).eq("audience_part", "Violino II").execute().data:
        m1 = d.table("measures").select("id").eq("score_id", sid).order("number").limit(1).execute().data[0]["id"]
        d.table("annotations").insert({"score_id": sid, "kind": "text", "measure_from": m1, "measure_to": m1, "audience": "part",
                                       "audience_part": "Violino II", "author_id": ids[admin_email], "status": "live",
                                       "body": "Seat check: bar 1, second violins only"}).execute()

    ok = True
    for e, seat in seats.items():
        link = d.auth.admin.generate_link({"type": "magiclink", "email": e})
        r = httpx.post(f"{sb_url}/auth/v1/verify", headers={"apikey": pub}, json={"type": "magiclink", "token_hash": link.properties.hashed_token}, timeout=20)
        tok = r.json()["access_token"]
        h = {"apikey": pub, "Authorization": f"Bearer {tok}"}
        rest = lambda path: httpx.get(f"{sb_url}/rest/v1/{path}", headers=h, timeout=20).json()   # noqa: E731
        my = [m for m in rest(f"members?select=*&ensemble_id=eq.{eid}") if m["user_id"] == ids[e]][0]
        seen_parts = rest(f"parts?select=*&score_id=eq.{sid}&order=position")
        marks = rest(f"annotations?select=id,audience_part,body&score_id=eq.{sid}")
        js = ("import { seatPart } from './src/app/seat.ts';"
              f"const parts = {json.dumps([{'id': p['id'], 'name': p['name'], 'canonical': p.get('canonical')} for p in seen_parts])};"
              f"console.log(JSON.stringify(seatPart(parts, {json.dumps(my['part'])}, {json.dumps(my.get('part_canonical'))}) ?? null))")
        hit = json.loads(subprocess.check_output(["node", "--input-type=module", "-e", js], cwd=ROOT / "web", text=True).strip())
        want_part = "Violino II" if seat == "Violin II" else "Violino I"
        want_marks = 1 if seat == "Violin II" else 0
        good = (hit or {}).get("name") == want_part and len(marks) == want_marks
        ok &= good
        print(f"{e.split('@')[0]:8} seat {seat!r} (canonical {my.get('part_canonical')!r}): stand opens {(hit or {}).get('name')!r}; "
              f"marks for 'Violino II' visible: {len(marks)}  {'OK' if good else 'WRONG'}")
    print("seat check:", "pass" if ok else "FAIL")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
