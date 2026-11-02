"""Backfill: a converted book's staff fragments merged on its instruments (feature 005, `parts_merge`), for books
converted before Convert to Digital merged them (PC3 pp. 1-4: 60 parts for 12 instruments; Rachmaninoff 2: 29 for 14).

    cd api && uv run python scripts/backfill_merge_parts.py                       # dry run, every converted book
    cd api && uv run python scripts/backfill_merge_parts.py --score ID --apply    # one book
    cd api && uv run python scripts/backfill_merge_parts.py --apply --engrave     # and redraw the pages (the box)

A book qualifies when it has a `sources` row of kind `musicxml` with `meta.transcribed_from` (the convert's file). Its
roster is the book's `parts` rows below position 1000 (the header's instruments; a cut's row sits at 1000). The
stored file is parsed, `merge_parts` runs on it with the roster, and a file the roster already fits is reported
unchanged. With `--apply` the merged file is written back over the same storage key (`write_musicxml`, as the convert
writes it), `meta.parts` on the source row is set to the merged names, the playback (MIDI and bar map,
`playback.write_step`) is rebuilt, and with `--engrave` the pages are drawn again on the box (`engrave_step`, best
effort; without it, queue an `engrave` job or open the book: the reader falls back to on-device OSMD). The `measures`
rows and the landmarks do not change (same bars). No model call, no spend. Dry run by default, never deletes.
"""
from __future__ import annotations

import argparse
import asyncio
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from music21 import converter  # noqa: E402

from app.librarian import playback  # noqa: E402
from app.librarian.engrave import engrave_step  # noqa: E402
from app.librarian.import_musicxml import part_groups  # noqa: E402
from app.librarian.omr_convert import CONTENT_TYPE, name_parts, write_musicxml  # noqa: E402
from app.librarian.parts_merge import merge_parts  # noqa: E402


class Ctx:
    """What `playback.write_step` and `engrave_step` use of a JobContext."""

    def __init__(self, db, score_id: str):
        self.db = db
        self.job = SimpleNamespace(id=f"backfill-merge-{score_id[:8]}-{int(time.time())}", created_by=None)
        self.result: dict = {}

    def storage_download(self, path: str) -> bytes:
        return self.db.storage.from_("scores").download(path)

    def storage_upload(self, path: str, data: bytes, content_type: str) -> None:
        self.db.storage.from_("scores").upload(path, data, {"content-type": content_type, "upsert": "true"})

    async def progress(self, fraction: float, note: str) -> None:
        print(f"    {note}")

    @staticmethod
    def now() -> str:
        return datetime.now(timezone.utc).isoformat()


def candidates(db, only: set[str] | None) -> list[dict]:
    srcs = db.table("sources").select("id,score_id,storage_paths,meta,created_at").eq("kind", "musicxml").order("created_at").execute().data or []
    out = []
    for s in srcs:
        meta = s.get("meta") or {}
        if not meta.get("transcribed_from") or not s.get("storage_paths"):
            continue
        if only and s["score_id"] not in only:
            continue
        out.append(s)
    return out


async def run(db, src: dict, apply: bool, engrave: bool) -> dict:
    score_id = src["score_id"]
    rows = db.table("parts").select("name,position").eq("score_id", score_id).order("position").execute().data or []
    roster = [r["name"] for r in rows if (r.get("position") or 0) < 1000]
    key = src["storage_paths"][0]
    data = db.storage.from_("scores").download(key)
    sc = await asyncio.to_thread(converter.parse, data, format="musicxml")
    before = [n for n, _ in part_groups(sc)]
    merged, report = await asyncio.to_thread(merge_parts, sc, roster)
    out: dict = {"before": len(before), "after": len(report["after"]), "changed": report["changed"],
                 "unassigned": report["unassigned"], "dropped": report["dropped"], "shared": len(report["shared"])}
    if not report["changed"] or not apply:
        return out
    name_parts(merged, roster)
    new = await asyncio.to_thread(write_musicxml, merged)
    ctx = Ctx(db, score_id)
    ctx.storage_upload(key, new, CONTENT_TYPE)
    parsed = await asyncio.to_thread(converter.parse, new, format="musicxml")
    names = [n for n, _ in part_groups(parsed)]
    db.table("sources").update({"meta": {**(src.get("meta") or {}), "parts": names, "parts_merged": {"before": before, "at": ctx.now()}}}).eq("id", src["id"]).execute()
    for name in names:
        if name in roster:
            db.table("parts").update({"storage_path": key}).eq("score_id", score_id).eq("name", name).execute()
    played = await playback.write_step(ctx, score_id, src["id"], parsed)
    out["playback"] = {k: played.get(k) for k in ("ok", "tracks", "bars", "reason") if played.get(k) is not None}
    if engrave:
        out["engraving"] = await engrave_step(ctx, score_id, src["id"])
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--apply", action="store_true", help="write (default: dry run)")
    ap.add_argument("--engrave", action="store_true", help="with --apply: draw the pages again on the box")
    ap.add_argument("--score", action="append", metavar="ID", help="only these books (repeatable)")
    a = ap.parse_args(argv)
    from app.db import db as get_db
    db = get_db()
    srcs = candidates(db, set(a.score) if a.score else None)
    print(f"{'APPLY' if a.apply else 'DRY RUN'}: {len(srcs)} converted books")
    failed = 0
    for s in srcs:
        head = f"- {s['score_id']} | {s['storage_paths'][0]}"
        try:
            r = asyncio.run(run(db, s, a.apply, a.engrave))
        except Exception as e:  # noqa: BLE001  (one book never stops the others)
            failed += 1
            print(f"{head} | FAILED {type(e).__name__}: {str(e)[:200]}")
            continue
        print(f"{head} | parts {r['before']} -> {r['after']}" + ("" if r["changed"] else " (unchanged)")
              + (f" | unassigned {r['unassigned']}" if r["unassigned"] else "") + (f" | dropped {r['dropped']}" if r["dropped"] else "")
              + (f" | shared {r['shared']}" if r["shared"] else "") + (f" | playback {r['playback']}" if "playback" in r else "")
              + (f" | engraving {r['engraving']}" if "engraving" in r else ""))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
