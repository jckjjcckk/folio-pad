"""Reset demo@folio.com to the demo video's shelf (demo-video branch only, never main). Idempotent.

    cd api && uv run scripts/seed_demo.py --dry-run      # what it would wipe and make
    cd api && uv run scripts/seed_demo.py                # wipe demo@folio.com's books, jobs and files, then seed
    (from a worktree with no api/.env: add --env ~/Documents/muse/api/.env)

Wipes only demo@folio.com: its own books (rows cascade), the jobs it made, and the files under those books' folders;
sets its display name to "CK Jiang".
Then copies three finished books from the hosted project through the service role (no Meta call, no worker):

1. Beethoven, String Quartet Op. 18 No. 1, I.: a digital book with playback (Violin I, Violin II, Viola, Cello).
2. Beethoven, Piano Concerto No. 3, pp. 1-4 (demo1's PDF): a PDF book whose Piano split is parked on the real
   `choose_staves` question for page 2, line 1, the line printed "Klav.". Its answer writes demo1's finished split.
3. Chopin, Polonaise Op. 26 No. 1, pp. 1-4 (demo1's PDF): a PDF book whose Convert to Digital is parked on a
   `match_bar` question (bar 13: the scan prints "sotto voce", the reading has none). Its answer writes demo1's
   finished conversion; "The reading is right" also takes bar 13 off the bars to check.

Both answers go through `POST /jobs/{id}/answer` on this branch's API (`routes/jobs.py` `_demo_resume`): the rows in
the parked job's `result.demo_resume` are written and the follow-up job lands `done`. On main's API the same answer
would queue a real resume on the worker: run this branch's API for the take. The Minuet is not seeded: CK uploads it
live from the iPad. Every id copied is new; the source books are only read.
"""
from __future__ import annotations

import argparse
import copy
import json
import os
import re
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

EMAIL = "demo@folio.com"
NAME = "CK Jiang"                                     # the account's display name on camera
QUARTET = "98732848-702d-44dd-bd9c-7e7f155cdb4e"      # Hart House's String Quartet No. 1 in F major (MusicXML, engraved)
PC3 = "37caf6c8-a2d2-4ee2-850d-7f80d4e8a834"          # demo1: beethoven-pc3-test-p1-4
PC3_READ = "9f673f89-0211-4c4e-9fcf-ebc050049934"     # its reading (process_pages)
PC3_SPLIT_ITP = "e9863a60-59b0-4f39-aa34-5b766f69667c"  # its finished Piano split ...
PC3_SPLIT_SRC = "10d16435-b025-484d-ab20-cce8a3df41b1"  # ... the strips it made
PC3_SPLIT_JOB = "3f7434c2-f1de-4b5c-8839-b4f4c35ff83c"  # ... and its job
CHOPIN = "e3283a97-33d2-4b10-9b6e-30a83dd313e2"       # demo1: chopin-polonaises-ekier-test-p4-7
CHOPIN_READ = "9dc56310-11c7-45d1-a6be-5e5052721db6"
ASK_PAGE, ASK_LINE = 2, 1                             # PC3: the first line that prints "Klav." (page 1 prints "Klavier")
ASK_BAR = 13                                          # Chopin: "sotto voce" on the scan, nothing in the reading

UUID = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")
BUCKET = "scores"


def load_env(path: Path) -> None:
    for line in path.read_text().splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def all_rows(q, page: int = 1000) -> list[dict]:
    """Every row of a query (PostgREST answers at most 1000 at a time)."""
    out, i = [], 0
    while True:
        rows = q.range(i, i + page - 1).execute().data or []
        out += rows
        if len(rows) < page:
            return out
        i += page


def files_under(d, prefix: str) -> list[str]:
    """Every file in the bucket under `prefix/`, recursively."""
    out = []
    for e in d.storage.from_(BUCKET).list(prefix, {"limit": 1000}):
        p = f"{prefix}/{e['name']}"
        out += [p] if e.get("id") else files_under(d, p)
    return out


class Book:
    """One source book read whole, with a new id for every row it has; `remap` rewrites any of its old ids (in paths,
    meta, params) to the new ones in a single pass."""

    def __init__(self, d, score_id: str):
        self.d = d
        self.score = d.table("scores").select("*").eq("id", score_id).single().execute().data
        self.sources = all_rows(d.table("sources").select("*").eq("score_id", score_id).order("created_at"))
        self.itps = all_rows(d.table("interpretations").select("*").eq("score_id", score_id).order("version"))
        self.parts = all_rows(d.table("parts").select("*").eq("score_id", score_id).order("position"))
        self.measures = all_rows(d.table("measures").select("*").eq("score_id", score_id).order("number"))
        self.ids = {score_id: str(uuid.uuid4())}
        for r in self.sources + self.itps + self.parts + self.measures:
            self.ids[r["id"]] = str(uuid.uuid4())
        self.new_id = self.ids[score_id]

    def remap(self, x):
        return json.loads(UUID.sub(lambda m: self.ids.get(m.group(0), m.group(0)), json.dumps(x)))

    def placements(self, itp_ids: list[str]) -> list[dict]:
        rows = []
        for i in itp_ids:
            rows += all_rows(self.d.table("measure_placements").select("*").eq("interpretation_id", i))
        return rows


def clone(d, b: Book, uid: str, *, fields: dict, keep_sources, keep_itps, itp_status: dict | None = None,
          part_paths: bool = True, dry: bool) -> dict:
    """Copy book `b` into demo@folio.com's library: its files, the kept sources and interpretations (with their
    placements), its parts and measures. Returns the new rows by old id (sources not kept are returned remapped, for
    the parked job's resume)."""
    files = files_under(d, b.score["id"])
    srcs = [b.remap(s) for s in b.sources]
    itps = [b.remap(i) for i in b.itps if i["id"] in keep_itps]
    for s in srcs:
        s["created_by"] = uid
    for i in itps:
        i["status"] = (itp_status or {}).get(i["id"], i["status"])
    kept = [s for s in srcs if s["id"] in {b.ids[x["id"]] for x in b.sources if keep_sources(x)}]
    score = {k: v for k, v in b.remap(b.score).items() if k not in ("created_at", "updated_at")}
    score.update(owner_user_id=uid, ensemble_id=None, created_by=uid, **fields)
    current, score["current_interpretation_id"] = score.get("current_interpretation_id"), None
    parts = [{**{k: v for k, v in b.remap(p).items() if k != "created_at"}, **({} if part_paths else {"storage_path": None})} for p in b.parts]
    measures = [{k: v for k, v in b.remap(m).items() if k != "created_at"} for m in b.measures]
    places = [b.remap(p) for p in b.placements(list(keep_itps))]
    print(f"  {score['title']}: {len(files)} files, {len(kept)}/{len(srcs)} sources, {len(itps)} interpretations, "
          f"{len(parts)} parts, {len(measures)} measures, {len(places)} placements")
    if not dry:
        st = d.storage.from_(BUCKET)
        for f in files:
            st.copy(f, b.remap(f))
        d.table("scores").insert(score).execute()
        for table, rows in (("sources", kept), ("interpretations", [{k: v for k, v in i.items() if k != "created_at"} for i in itps]),
                            ("parts", parts), ("measures", measures), ("measure_placements", places)):
            for j in range(0, len(rows), 500):
                d.table(table).insert(rows[j:j + 500]).execute()
        if current in {i["id"] for i in itps}:
            d.table("scores").update({"current_interpretation_id": current}).eq("id", b.new_id).execute()
    return {old: s for old, s in zip((x["id"] for x in b.sources), srcs)}


def wipe(d, uid: str, dry: bool) -> None:
    books = all_rows(d.table("scores").select("id,title").eq("owner_user_id", uid))
    jobs = all_rows(d.table("jobs").select("id").eq("created_by", uid))
    files = [f for s in books for f in files_under(d, s["id"])]
    print(f"wipe {EMAIL}: {len(books)} books, {len(jobs)} jobs it made, {len(files)} files")
    for s in books:
        print(f"  - {s['title']}")
    if dry:
        return
    for j in range(0, len(files), 100):
        d.storage.from_(BUCKET).remove(files[j:j + 100])
    for j in range(0, len(jobs), 200):
        d.table("jobs").delete().in_("id", [r["id"] for r in jobs[j:j + 200]]).execute()
    for s in books:
        d.table("scores").delete().eq("id", s["id"]).eq("owner_user_id", uid).execute()   # sources, parts, measures... cascade


def seed_quartet(d, uid: str, dry: bool) -> None:
    b = Book(d, QUARTET)
    clone(d, b, uid, dry=dry, fields={"title": "String Quartet No. 1 in F major", "composer": "Ludwig van Beethoven",
                                      "work": "Op. 18 No. 1, I. Allegro con brio", "folder": "Quartet"},
          keep_sources=lambda s: True, keep_itps={i["id"] for i in b.itps})


def seed_concerto(d, uid: str, dry: bool) -> None:
    """The PDF book with its Piano split parked on page 2, line 1 ("Klav.")."""
    b = Book(d, PC3)
    split_itp = next(i for i in b.itps if i["id"] == PC3_SPLIT_ITP)
    state = split_itp["params"]["state"]
    mem = copy.deepcopy(b.score["label_memory"])
    klav = mem["entries"].pop("klav")                  # the line asks because "Klav." is not known yet
    mem["entries"].pop("pfte", None)
    srcs = clone(d, b, uid, dry=dry, keep_sources=lambda s: s["kind"] == "pdf", keep_itps={PC3_READ, PC3_SPLIT_ITP},
                 itp_status={b.ids[PC3_SPLIT_ITP]: "needs_review"}, part_paths=False,
                 fields={"title": "Piano Concerto No. 3 in C minor", "composer": "Ludwig van Beethoven",
                         "work": "Op. 37, I. Allegro con brio", "folder": "Concertos", "playback": None, "label_memory": mem})
    sid, itp = b.new_id, b.ids[PC3_SPLIT_ITP]
    page = state["pages"][str(ASK_PAGE)]
    geom = page["geometry"]
    line = next(s for s in geom["systems"] if s["index"] == ASK_LINE)
    prop = next(p for p in page["proposal"] if p["system"] == ASK_LINE)
    question = f"Which staves are the Piano's on page {ASK_PAGE}, line {ASK_LINE}?"     # part_cut.py's own template
    payload = {
        "kind": "choose_staves", "page": ASK_PAGE, "system": ASK_LINE, "instrument": "Piano", "instruments": ["Piano"], "interpretation_id": itp,
        "proposal": prop["staves"], "blocks": [{"staves": prop["staves"], "instruments": ["Piano"]}], "staves_per_instrument": {"Piano": 2},
        "last_attempt": prop["staves"],
        "feedback": ("commit_system was refused 3 times. Last feedback: the margin of this line prints \"Klav.\", which is not a name "
                     "the header gave (\"Klavier\") and not in the book's memory; the staves [8, 9] fit a keyboard, but the label "
                     "does not settle it."),
        "staff_boxes": [{k: s[k] for k in ("index", "y_top", "y_bottom", "x0", "x1")} for s in geom["staves"] if s["index"] in line["staff_indices"]],
        "image_key": b.remap(page.get("overlay_key")), "page_key": f"{sid}/pages/{ASK_PAGE}.png", "image_px": geom.get("image_px"),
        "allowed": {"staves": "list of staff numbers from staff_boxes (a skipped staff splits the cut into stacked blocks)",
                    "blocks": "lists of staff numbers, one per block", "absent": True},
        "answer_format": '{"staves": [11, 12]} or {"blocks": [[11], [13]]} or {"staves": "absent"}',
        "known_labels": [{"label": "Klavier", "part": "Piano", "source": "model", "origin": "header", "page": 1}],
        "margin_labels": prop.get("margin_labels") or [], "remembered": [],
    }
    log = [*state["log"][:3], state["log"][3],
           f"Page {ASK_PAGE} system {ASK_LINE}: the margin prints \"Klav.\", not in the header or the book's memory; staves {prop['staves']} proposed, the check refused",
           f"Ended: question: {question}"]
    done = d.table("jobs").select("result").eq("id", PC3_SPLIT_JOB).single().execute().data["result"]
    done = {k: v for k, v in b.remap(done).items() if k != "agent"}
    done.update(questions=1, agent={"log": [*state["log"], f"Page {ASK_PAGE} system {ASK_LINE}: \"Klav.\" is the Piano (the admin's answer), remembered for this book",
                                            "Ended: cut: 7 systems cut"]})
    mem_after = copy.deepcopy(mem)
    mem_after["entries"]["klav"] = {**klav, "source": "human", "origin": "answer", "page": ASK_PAGE, "staves": prop["staves"], "at": now()}
    resume = {"insert": {"sources": [srcs[PC3_SPLIT_SRC]]},
              "update": [{"table": "interpretations", "match": {"id": itp}, "set": {"status": "done", "finished_at": now()}},
                         {"table": "scores", "set": {"label_memory": mem_after}}],
              "result": done}
    job = {"kind": "part_cut", "status": "done", "progress": 0.3, "score_id": sid, "created_by": uid,
           "payload": {"score_id": sid, "parts_key": "piano", "instruments": ["Piano"], "pages": [1, 2, 3, 4], "interpretation_id": itp},
           "result": {"question": question, "question_payload": payload, "outcome": "question", "outcome_reason": question,
                      "note": f"Page {ASK_PAGE} of 4, 1 system cut", "phase": {"page": ASK_PAGE, "pages": 4, "systems_cut": 1},
                      "model_tier": "standard", "interpretation_id": itp, "agent": {"scratch": {"log": log}, "log": []}, "demo_resume": resume},
           "started_at": now(), "finished_at": now()}
    print(f"  parked split: {question!r} (margin \"Klav.\")")
    if not dry:
        d.table("jobs").insert(job).execute()


def seed_polonaise(d, uid: str, dry: bool) -> None:
    """The PDF book with its Convert to Digital parked on bar 13 (the scan prints "sotto voce", the reading none)."""
    b = Book(d, CHOPIN)
    srcs = clone(d, b, uid, dry=dry, keep_sources=lambda s: s["kind"] == "pdf", keep_itps={CHOPIN_READ}, part_paths=False,
                 fields={"title": "Polonaise in C♯ minor", "composer": "Frédéric Chopin", "work": "Op. 26 No. 1", "folder": "Chopin",
                         "playback": None})
    sid = b.new_id
    pdf = next(s for s in b.sources if s["kind"] == "pdf")
    xml = next(s for s in b.sources if s["kind"] == "musicxml")
    eng = {s["meta"]["layout"]: s for s in b.sources if s["kind"] == "engraving"}
    flag = next(f for f in xml["meta"]["flagged_bars"] if f["number"] == ASK_BAR)
    ebar = next(x for x in eng["display"]["meta"]["bars"] if x[0] == ASK_BAR)          # [bar, page, x, y, w, h], fractions
    box = flag["box"]
    question = f"Does bar {ASK_BAR} match the page?"
    payload = {
        "kind": "match_bar", "bar": ASK_BAR, "page": flag["page"], "source_id": b.ids[pdf["id"]],
        "scan": {"key": f"{sid}/pages/{flag['page']}.png", "px": pdf["meta"]["render"]["px"][flag["page"] - 1],
                 # the bar's box, with the marking printed just above the staff
                 "box": {"x0": box["x0"], "x1": box["x1"], "y0": max(0.0, box["y0"] - 0.035), "y1": min(1.0, box["y1"] + 0.012)}},
        "reading": {"key": b.remap(eng["display"]["storage_paths"][ebar[1] - 1]), "page_mm": eng["display"]["meta"]["page_mm"],
                    "box": {"x0": ebar[2], "y0": max(0.0, ebar[3] - 0.03), "x1": ebar[2] + ebar[4], "y1": min(1.0, ebar[3] + ebar[5] + 0.01)}},
        "printed": "sotto voce", "read": None,
        "detail": "The page prints “sotto voce” over this bar. The reading has no marking there.",
        "reasons": flag["reasons"],
        "answer_format": '{"answer": "reading"} (the reading is right) or {"answer": "check"} (keep the bar on the list to check)',
    }
    xml_row = srcs[xml["id"]]
    engs = [srcs[s["id"]] for s in eng.values()]
    done = d.table("jobs").select("result").eq("kind", "omr_convert").eq("score_id", CHOPIN).eq("status", "done") \
        .order("created_at", desc=True).limit(1).execute().data[0]["result"]
    done = b.remap(done)
    after = b.remap(b.score)

    def spec(drop: bool) -> dict:
        x = copy.deepcopy(xml_row)
        if drop:
            x["meta"]["flagged_bars"] = [f for f in x["meta"]["flagged_bars"] if f["number"] != ASK_BAR]
        n = len(x["meta"]["flagged_bars"])
        x["meta"]["flags"]["bars_doubtful"] = n
        r = {**done, "flagged_bars": [f["number"] for f in x["meta"]["flagged_bars"]], "note": f"Digital: {done.get('bars')} bars, {n} to check",
             "answered": {"bar": ASK_BAR, "answer": "reading" if drop else "check"}}
        return {"insert": {"sources": [x, *engs]},
                "update": [{"table": "parts", "set": {"storage_path": x["storage_paths"][0]}},
                           {"table": "scores", "set": {"playback": after["playback"], "landmarks": after["landmarks"]}}],
                "result": r}

    resume = {**spec(False), "answers": {"reading": spec(True)}}
    job = {"kind": "omr_convert", "status": "done", "progress": 0.6, "score_id": sid, "created_by": uid, "max_attempts": 1,
           "payload": {"score_id": sid, "source_id": b.ids[pdf["id"]]},
           "result": {"question": question, "question_payload": payload, "note": f"Bar {ASK_BAR} needs you", "model_tier": "standard",
                      "demo_resume": resume},
           "started_at": now(), "finished_at": now()}
    print(f"  parked convert: {question!r}")
    if not dry:
        d.table("jobs").insert(job).execute()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--dry-run", action="store_true", help="print what it would wipe and make; write nothing")
    ap.add_argument("--env", type=Path, default=Path(__file__).resolve().parents[1] / ".env", help="the api/.env to read (default: this checkout's)")
    a = ap.parse_args()
    load_env(a.env)
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from app.db import db        # after the env: settings read SUPABASE_URL and SUPABASE_SECRET_KEY at import
    d = db()
    prof = d.table("profiles").select("id").eq("email", EMAIL).execute().data
    assert prof, f"{EMAIL} has no profile on {os.environ.get('SUPABASE_URL', '?')}"
    uid = prof[0]["id"]
    print(("DRY RUN: " if a.dry_run else "") + f"{EMAIL} ({uid})")
    wipe(d, uid, a.dry_run)
    print(f"display name: {NAME}")
    if not a.dry_run:
        d.table("profiles").update({"display_name": NAME}).eq("id", uid).execute()
    print("seed:")
    # Oldest first: the shelf lists the newest on top, so the concerto leads, then the polonaise, then the quartet.
    seed_quartet(d, uid, a.dry_run)
    seed_polonaise(d, uid, a.dry_run)
    seed_concerto(d, uid, a.dry_run)
    print("done" if not a.dry_run else "nothing written")


if __name__ == "__main__":
    main()
