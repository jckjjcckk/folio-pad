"""The printed-bar-number check inside the real handlers: `import_pdf` renders, `process_pages` reads with READ_PRINTED on,
real Spark, an in-memory store (the speed pass's harness). Prints the bar numbers the book got, the check's summary and
its log lines. Pages are cut from a fixture PDF first, so a scan that starts mid-piece can be tried.

    cd api && PYTHONPATH=. uv run python experiments/bar_numbers/import_e2e.py /abs/file.pdf 2,3,4 --tag ekier-p2-4
"""
from __future__ import annotations

import argparse
import asyncio
import json
import time
import uuid
from pathlib import Path

import pymupdf

from app.librarian import Job
from app.librarian import process_pages as pp
from app.librarian.import_pdf import import_pdf
from app.llm import _client
from app.settings import settings
from tests.test_part_cut import Ctx as BaseCtx, FakeDB

OUT = Path(__file__).parent / "results"


class Ctx(BaseCtx):
    def charge(self, c):
        self.charges.append(c)
        return {}

    def storage_upload(self, path, data, content_type):
        self.pages[path] = data


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf")
    ap.add_argument("pages")
    ap.add_argument("--tag", required=True)
    a = ap.parse_args()
    src = pymupdf.open(a.pdf)
    doc = pymupdf.open()
    for p in (int(x) for x in a.pages.split(",")):
        doc.insert_pdf(src, from_page=p - 1, to_page=p - 1)
    pp.READ_PRINTED = True
    score, key = str(uuid.uuid4()), "src.pdf"
    db = FakeDB()
    db.rows["scores"] = [{"id": score, "title": a.tag, "composer": None, "work": None}]
    db.rows["sources"] = [{"id": "src1", "score_id": score, "kind": "pdf", "storage_paths": [key], "created_by": "u1"}]
    files = {key: doc.tobytes()}
    t0 = time.time()
    j1 = Job(str(uuid.uuid4()), "import_pdf", {"score_id": score, "source_id": "src1"}, score, "u1", 1, 3)
    await import_pdf(j1, Ctx(j1, db, files))
    t1 = time.time()
    j2 = Job(str(uuid.uuid4()), "process_pages", {"score_id": score, "source_id": "src1"}, score, "u1", 1, 3)
    ctx = Ctx(j2, db, files)
    out = await pp.process_pages(j2, ctx, client=_client(), model=settings.meta_model)
    t2 = time.time()
    interp = db.rows["interpretations"][-1]
    by_id = {r["id"]: r["number"] for r in db.rows["measures"]}
    per_page: dict[int, list] = {}
    for p in db.rows["measure_placements"]:
        per_page.setdefault(p["page"], []).append((by_id[p["measure_id"]], p["system"], p["confidence"], "printed" in (p["flag"] or "")))
    rec = {"tag": a.tag, "read_s": round(t2 - t1, 1), "question": out.get("question"), "bars": db.rows["scores"][0].get("bars"),
           "first_label": {k: v["labels"]["first_measure_number"] for k, v in interp["params"]["state"]["pages"].items() if v.get("labels")},
           "summary": interp["summary"].get("bar_numbers"), "first_measure": interp["summary"].get("first_measure"),
           "pages": {p: {"first": xs[0][0], "last": xs[-1][0], "doubted_systems": sorted({s for _, s, _, d in xs if d})} for p, xs in sorted(per_page.items())},
           "log": [line for line in interp["summary"]["log"] if "printed" in line.lower() or "bar numbers" in line.lower()],
           "cost_usd": round(sum(float(c.cost_usd) for c in ctx.charges), 4), "calls": len(ctx.charges)}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"e2e-{a.tag}.json").write_text(json.dumps(rec, indent=1, default=str))
    print(json.dumps(rec, indent=1, default=str))


if __name__ == "__main__":
    asyncio.run(main())
