"""Reset the shared judge account's shelf to two finished books. Idempotent.

    cd api && uv run scripts/seed_judges.py --dry-run    # what it would remove and make
    cd api && uv run scripts/seed_judges.py              # seed the new copies, then remove the account's old books

Touches only judges@folio.jckjjcckk.com: its own books (rows cascade), the jobs it made, and the files under those
books' folders. Its display name and spend are left as they are. It copies two finished hosted books through the
service role (no Meta call, no worker), with the code `seed_demo.py` uses:

1. Beethoven, String Quartet No. 1 in F major, Op. 18 No. 1, I.: a digital book with engraved pages and playback for
   Violin I, Violin II, Viola and Cello (the same source book as the demo seed).
2. Bach, Minuet in G, BWV Anh. 114: a one-page scan converted to Digital (PDF + Digital, 32 bars, 0 to check), copied
   from the Minuet converted on demo@folio.com's shelf ("minute in G 3"), retitled.

No question is parked. The new copies are written before the old books are removed, so a rerun can take the Minuet
from the judge account's own copy when demo@folio.com's original is gone (for example after a demo reset). The source
books are only read.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from seed_demo import BUCKET, EMAIL as DEMO_EMAIL, Book, all_rows, clone, files_under, load_env, seed_quartet  # noqa: E402

EMAIL = "judges@folio.jckjjcckk.com"
MINUET = "1f7a4f7c-84b1-4bd6-ab81-5743115672b0"      # demo@folio.com: "minute in G 3", converted live on 2026-11-04
MINUET_FROM = "minute in G 3"
MINUET_TITLE = "Minuet in G, BWV Anh. 114"


def uid_of(d, email: str) -> str | None:
    rows = d.table("profiles").select("id").eq("email", email).execute().data
    return rows[0]["id"] if rows else None


def minuet_source(d, judges: str) -> str:
    """The Minuet to copy: demo@folio.com's converted book (by id, else by title), else the judge account's own copy."""
    if d.table("scores").select("id").eq("id", MINUET).execute().data:
        return MINUET
    demo = uid_of(d, DEMO_EMAIL)
    for owner, title in ((demo, MINUET_FROM), (judges, MINUET_TITLE)):
        if owner:
            rows = d.table("scores").select("id").eq("owner_user_id", owner).eq("title", title) \
                .order("created_at", desc=True).limit(1).execute().data
            if rows:
                return rows[0]["id"]
    raise SystemExit(f"no Minuet to copy: neither {DEMO_EMAIL}'s {MINUET_FROM!r} nor {EMAIL}'s {MINUET_TITLE!r} exists")


def seed_minuet(d, uid: str, source: str, dry: bool) -> None:
    b = Book(d, source)
    clone(d, b, uid, dry=dry, fields={"title": MINUET_TITLE},
          keep_sources=lambda s: True, keep_itps={i["id"] for i in b.itps})


def remove(d, uid: str, books: list[dict], dry: bool) -> None:
    """The account's old books (their rows cascade), the jobs it made, and the files under those books' folders."""
    jobs = all_rows(d.table("jobs").select("id").eq("created_by", uid))
    files = [f for s in books for f in files_under(d, s["id"])]
    print(f"remove from {EMAIL}: {len(books)} books, {len(jobs)} jobs it made, {len(files)} files")
    for s in books:
        print(f"  - {s['title']}")
    if dry:
        return
    for j in range(0, len(files), 100):
        d.storage.from_(BUCKET).remove(files[j:j + 100])
    for j in range(0, len(jobs), 200):
        d.table("jobs").delete().in_("id", [r["id"] for r in jobs[j:j + 200]]).execute()
    for s in books:
        d.table("scores").delete().eq("id", s["id"]).eq("owner_user_id", uid).execute()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--dry-run", action="store_true", help="print what it would remove and make; write nothing")
    ap.add_argument("--env", type=Path, default=Path(__file__).resolve().parents[1] / ".env", help="the api/.env to read (default: this checkout's)")
    a = ap.parse_args()
    load_env(a.env)
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from app.db import db        # after the env: settings read SUPABASE_URL and SUPABASE_SECRET_KEY at import
    d = db()
    uid = uid_of(d, EMAIL)
    assert uid, f"{EMAIL} has no profile on {os.environ.get('SUPABASE_URL', '?')}"
    print(("DRY RUN: " if a.dry_run else "") + f"{EMAIL} ({uid})")
    old = all_rows(d.table("scores").select("id,title").eq("owner_user_id", uid))
    source = minuet_source(d, uid)
    print("seed:")
    # Oldest first: the shelf lists the newest on top, so the Minuet leads.
    seed_quartet(d, uid, a.dry_run)
    seed_minuet(d, uid, source, a.dry_run)
    remove(d, uid, old, a.dry_run)
    print("done" if not a.dry_run else "nothing written")


if __name__ == "__main__":
    main()
