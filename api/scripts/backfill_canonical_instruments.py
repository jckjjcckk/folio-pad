"""Backfill the canonical instrument names a seat and a part are matched on (010, CK 2026-11-02; migration
20261102130000 adds `parts.canonical` and `members.part_canonical`), for the rows written before the import, the cut
and the seat scripts wrote them.

    cd api && uv run python scripts/backfill_canonical_instruments.py                 # dry run, the hosted project
    cd api && uv run python scripts/backfill_canonical_instruments.py --apply
    cd api && uv run python scripts/backfill_canonical_instruments.py --local --apply # the local stack

Every name goes through the one normaliser (`app.librarian.instruments.canonical_instrument`). Dry run by default: says
what it would write, writes nothing. Idempotent: a row whose canonical name is already right is skipped. A database
without the migration is reported and left alone. Acts through the service role; prints no key, no URL; never deletes.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.librarian.instruments import canonical_instrument  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true", help="write (default: dry run)")
    ap.add_argument("--local", action="store_true", help="the local Supabase stack instead of api/.env's project")
    a = ap.parse_args()
    if a.local:
        from app.librarian.run import point_at_local_stack
        point_at_local_stack(allow_remote=False)
    from app.db import db
    d = db()

    parts = d.table("parts").select("*").execute().data or []
    members = d.table("members").select("*").execute().data or []
    if (parts and "canonical" not in parts[0]) or (members and "part_canonical" not in members[0]):
        sys.exit("this database has no canonical columns yet (migration 20261102130000 not applied); nothing written")

    part_todo = [(r, canonical_instrument(r["name"])) for r in parts if r.get("name") and r.get("canonical") != canonical_instrument(r["name"])]
    seat_todo = [(r, canonical_instrument(r["part"]) if r.get("part") else None) for r in members
                 if r.get("part_canonical") != (canonical_instrument(r["part"]) if r.get("part") else None)]
    print(f"parts: {len(parts)} rows, {len(part_todo)} to write; seats: {len(members)} rows, {len(seat_todo)} to write")
    for r, c in part_todo:
        print(f"  part  {r['name']!r:40} -> {c!r}")
    for r, c in seat_todo:
        print(f"  seat  {r.get('part')!r:40} -> {c!r}")
    if not a.apply:
        print("dry run: nothing written (--apply writes)")
        return
    for r, c in part_todo:
        d.table("parts").update({"canonical": c}).eq("id", r["id"]).execute()
    for r, c in seat_todo:
        d.table("members").update({"part_canonical": c}).eq("id", r["id"]).execute()
    print(f"written: {len(part_todo)} parts, {len(seat_todo)} seats")


if __name__ == "__main__":
    main()
