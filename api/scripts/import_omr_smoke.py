"""Put the OMR box smoke-test outputs into a personal library on whichever project api/.env points at.

    cd api && PYTHONPATH=. uv run scripts/import_omr_smoke.py [--user ck@muse.test]

Creates the user if missing (random password written to api/.env as CK_TEST_PASSWORD), then for each engine
output: a score row owned by that user, the MusicXML in the bucket at {score_id}/source.musicxml (kern is
converted with music21 first), a source + import_musicxml job, run in-process through the worker. Idempotent
per title: an existing score with the same title in the folder is deleted first.
"""
from __future__ import annotations

import argparse
import asyncio
import io
import secrets
import sys
from pathlib import Path

from music21 import converter

from app.db import db
from app.librarian import load_handlers
from app.worker import run_one

ROOT = Path(__file__).resolve().parents[2]
SMOKE = ROOT / "api/experiments/grounding/out/omr-box-smoke"
FOLDER = "OMR smoke 2026-10-27"
FILES = [
    ("audiveris/goldberg-bga.xml", "Goldberg Aria p1 · Audiveris", "J. S. Bach"),
    ("audiveris2/rach1-two-piano-gutheil-1919.xml", "Rachmaninoff Concerto 1 (2 pf) p3 · Audiveris", "S. Rachmaninoff"),
    ("homr/goldberg-bga-p01.musicxml", "Goldberg Aria p1 · homr", "J. S. Bach"),
    ("homr/rach1-2pf-gutheil-p03.musicxml", "Rachmaninoff Concerto 1 (2 pf) p3 · homr", "S. Rachmaninoff"),
    ("goldberg-bga-p01_pred.krn", "Goldberg Aria p1 · Transcoda", "J. S. Bach"),
]


def ensure_user(email: str) -> str:
    d = db()
    for u in d.auth.admin.list_users():
        if u.email == email:
            return u.id
    password = secrets.token_urlsafe(14)
    u = d.auth.admin.create_user({"email": email, "password": password, "email_confirm": True}).user
    env = ROOT / "api/.env"
    with env.open("a") as f:
        f.write(f"\n# test account created by scripts/import_omr_smoke.py\nCK_TEST_PASSWORD={password}\n")
    print(f"created {email}; password appended to api/.env as CK_TEST_PASSWORD")
    return u.id


def musicxml_bytes(path: Path) -> bytes:
    if path.suffix in (".xml", ".musicxml", ".mxl"):
        return path.read_bytes()
    s = converter.parse(path.read_text().replace("**ekern_1.0", "**kern"), format="humdrum")
    for part in s.parts:  # humdrum measures arrive unnumbered; the importer keys measures by number
        for i, m in enumerate(part.getElementsByClass("Measure"), start=1):
            m.number = i
    out = s.write("musicxml")
    return Path(out).read_bytes()


async def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--user", default="ck@muse.test")
    a = ap.parse_args()
    d = db()
    uid = ensure_user(a.user)
    d.table("profiles").update({"display_name": "CK Jiang"}).eq("id", uid).execute()
    load_handlers()
    fails = 0
    for rel, title, composer in FILES:
        data = musicxml_bytes(SMOKE / rel)
        d.table("scores").delete().eq("owner_user_id", uid).eq("title", title).execute()
        score = d.table("scores").insert({"owner_user_id": uid, "title": title, "composer": composer, "folder": FOLDER, "created_by": uid}).execute().data[0]
        sid = score["id"]
        key = f"{sid}/source.musicxml"
        d.storage.from_("scores").upload(key, data, {"content-type": "application/vnd.recordare.musicxml+xml", "upsert": "true"})
        src = d.table("sources").insert({"score_id": sid, "kind": "musicxml", "storage_paths": [key], "meta": {"filename": Path(rel).name}, "created_by": uid}).execute().data[0]
        job = d.table("jobs").insert({"kind": "import_musicxml", "score_id": sid, "created_by": uid, "payload": {"score_id": sid, "source_id": src["id"]}, "status": "running"}).execute().data[0]
        await run_one(job)
        row = d.table("jobs").select("status,error,result").eq("id", job["id"]).single().execute().data
        s = d.table("scores").select("status,bars,key_sig,meter,tempo_bpm").eq("id", sid).single().execute().data
        parts = [p["name"] for p in d.table("parts").select("name").eq("score_id", sid).order("position").execute().data]
        ok = row["status"] == "done" and s["status"] == "ready"
        fails += 0 if ok else 1
        print(("  ok   " if ok else "  FAIL ") + f"{title}: {s['status']} {s['bars']} bars {s['key_sig']} {s['meter']} parts={parts} {row.get('error') or ''}")
    print("ALL PASS" if not fails else f"{fails} FAILED")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
