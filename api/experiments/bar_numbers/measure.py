"""Printed bar numbers vs the geometric count, live on a few pages per fixture (CK's decision 3, 2026-11-02).

Muse Spark through `bar_numbers.read_printed` exactly as `process_pages` calls it (effort minimal, chat completions; a page
whose readings disagree with its own count read again at low), on pages rendered at the import route's 150 dpi
(`import_pdf.render_page`) with `cut.page_measures`. Truth keyed by eye from the annotated PNGs: {page: {box: printed}}.
Writes `results/<run>.json` (every call, reading, cost and second) and prints the table.

    cd api && PYTHONPATH=. uv run python experiments/bar_numbers/measure.py run1 [fixture ...]
"""
from __future__ import annotations

import asyncio
import base64
import json
import sys
import time
from pathlib import Path

import pymupdf

from app import llm
from app.librarian import bar_numbers as bn
from app.librarian.cut import page_measures
from app.librarian.import_pdf import render_page

FIX = Path("/Users/ckjiang/Documents/muse/api/fixtures")
PREP = Path("/Users/ckjiang/Documents/muse/api/experiments/pageread_speed/results/prep")
OUT = Path(__file__).parent / "results"

# (pdf or png glob, pages, expected staves, truth per page: {box: printed number}; "multi" boxes carry several numbers)
FIXTURES: dict[str, dict] = {
    "cappi": {"pdf": FIX / "imslp/beethoven-op27-2-cappi-1802.pdf", "pages": [2, 3, 4], "staves": None, "truth": {2: {}, 3: {}, 4: {}}},
    "goldberg-bga": {"pdf": FIX / "pdf/goldberg-bga-p1-5.pdf", "pages": [1, 2, 3], "staves": None, "truth": {1: {}, 2: {}, 3: {}}},
    "beethoven9": {"png": [PREP / f"beethoven9-p{p}.png" for p in (172, 173, 174)], "pages": [1, 2, 3], "staves": 16, "truth": {1: {}, 2: {}, 3: {}}},
    "chopin-ekier": {"pdf": FIX / "pdf/chopin-polonaises-ekier-test-p4-7.pdf", "pages": [1, 2, 3, 4], "staves": None, "truth": {
        1: {5: 5, 9: 9, 13: 13, 17: 17}, 2: {1: 20, 5: 24, 9: 28, 13: 32, 16: 35}, 3: {1: 38, 5: 42, 8: 45, 11: 48, 14: 51},
        4: {1: 54, 4: 57, 7: 60, 10: 63, 13: 66}}},
    "goldberg-peters": {"pdf": FIX / "pdf/goldberg-peters-test-p4-7.pdf", "pages": [1, 2, 3, 4], "staves": None, "truth": {
        1: {5: 5, 9: 9, 13: 13}, 2: {1: [17, 20, 23, 27, 30]}, 3: {4: 4, 7: 7, 10: 10, 13: 13}, 4: {1: 17, 29: 20, 52: 23, 85: 26, 116: 29}}},
}
# systems whose count is truly wrong (by eye), for false-disagreement scoring: (page, system)
TRUE_ERRORS = {"chopin-ekier": {(2, 5), (3, 5)}, "goldberg-peters": {(2, 1), (3, 5), (4, 1), (4, 2), (4, 3), (4, 4), (4, 5), (4, 6), (4, 7),
                                                                     (4, 8), (4, 9), (4, 10), (4, 11)}}


class LiveCtx:
    """What `read_printed` needs of a JobContext: complete (charged here to a list) and png_b64."""
    def __init__(self):
        self.calls: list[dict] = []

    async def complete(self, text: str, **kw):
        t0 = time.monotonic()
        c = await llm.complete(text, **kw)
        self.calls.append({"effort": kw.get("effort"), "api": c.api, "model": c.charge.model, "in": c.charge.input_tokens,
                           "out": c.charge.output_tokens, "cost_usd": float(c.charge.cost_usd), "seconds": round(time.monotonic() - t0, 2),
                           "text": c.text[:2000]})
        return c

    @staticmethod
    def png_b64(b: bytes) -> str:
        return base64.b64encode(b).decode()


def load(name: str, f: dict) -> list[tuple[int, bytes, dict]]:
    out = []
    if "pdf" in f:
        doc = pymupdf.open(f["pdf"])
        for p in f["pages"]:
            png = render_page(doc[p - 1])[0]
            out.append((p, png, page_measures(png, expected_staves=f["staves"])))
    else:
        for p, path in zip(f["pages"], f["png"]):
            png = path.read_bytes()
            out.append((p, png, page_measures(png, expected_staves=f["staves"])))
    return out


async def read_page(ctx: LiveCtx, page: int, png: bytes, geo: dict) -> dict:
    rec = await bn.read_printed(ctx, png, geo, effort=bn.EFFORT)
    if "error" not in rec and (why := bn.page_disagrees(geo, rec["readings"], page)):
        again = await bn.read_printed(ctx, png, geo, effort=bn.FALLBACK_EFFORT)
        if "error" not in again:
            rec = {**again, "fallback": why, "first_cost_usd": rec["cost_usd"], "first_readings": rec["readings"], "first_seconds": rec["seconds"]}
    return rec


def score_page(truth: dict, readings: list[dict]) -> dict:
    """Readings against the truth: right (number on its box), wrong box, invented (no such printed number), missed."""
    want = {(b, n) for b, v in truth.items() for n in (v if isinstance(v, list) else [v])}
    printed = {n for _, n in want}
    got = [(r["box"], r["number"]) for r in readings if r["confidence"] != "low"]
    right = sum(1 for g in got if g in want)
    wrong_box = sum(1 for b, n in got if (b, n) not in want and n in printed)
    invented = sum(1 for b, n in got if n not in printed)
    missed = sum(1 for w in want if w not in got)
    return {"truth": len(want), "right": right, "wrong_box": wrong_box, "invented": invented, "missed": missed,
            "low": sum(1 for r in readings if r["confidence"] == "low")}


async def main(run: str, names: list[str]) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    report: dict = {"run": run, "model": llm.model_name(), "fixtures": {}}
    gate = asyncio.Semaphore(4)
    for name in names:
        f = FIXTURES[name]
        pages = load(name, f)
        ctx = LiveCtx()

        async def one(p, png, geo):
            async with gate:
                return await read_page(ctx, p, png, geo)
        t0 = time.monotonic()
        recs = await asyncio.gather(*(one(p, png, geo) for p, png, geo in pages))
        wall = time.monotonic() - t0
        number_of, n = {}, 1
        for p, _, geo in pages:
            for m in geo["measures"]:
                number_of[(p, m["provisional"])] = n
                n += 1
        book = bn.verify_book([(p, geo, rec) for (p, _, geo), rec in zip(pages, recs)], number_of)
        per_page = []
        for (p, _, geo), rec in zip(pages, recs):
            sc = score_page(f["truth"].get(p, {}), rec.get("readings") or [])
            per_page.append({"page": p, "bars_counted": len(geo["measures"]), "systems": len(geo["systems"]), "effort": rec.get("effort"),
                             "fallback": rec.get("fallback"), "readings": rec.get("readings"), "first_readings": rec.get("first_readings"),
                             "dropped": rec.get("dropped"), "error": rec.get("error"), **sc,
                             "cost_usd": rec.get("cost_usd", 0) + rec.get("first_cost_usd", 0), "seconds": rec.get("seconds", 0) + rec.get("first_seconds", 0)})
        truth_err = TRUE_ERRORS.get(name, set())
        doubted = {(d["page"], d["system"]) for d in book["doubts"]}
        report["fixtures"][name] = {
            "pages": per_page, "wall_s": round(wall, 1), "calls": ctx.calls,
            "book": {k: book[k] for k in ("status", "offset", "offset_confirmed", "restarts", "used", "read", "cost_usd")},
            "doubts": book["doubts"], "ignored": book["ignored"],
            "true_doubts": sorted(doubted & truth_err), "false_doubts": sorted(doubted - truth_err), "missed_errors": sorted(truth_err - doubted),
        }
        r = report["fixtures"][name]
        tot = {k: sum(pp[k] for pp in per_page) for k in ("truth", "right", "wrong_box", "invented", "missed", "low")}
        cost = sum(c["cost_usd"] for c in ctx.calls)
        print(f"{name}: {len(pages)} pages, {len(ctx.calls)} calls, ${cost:.4f} (${cost / len(pages):.4f}/page), "
              f"median call {sorted(c['seconds'] for c in ctx.calls)[len(ctx.calls) // 2]} s, wall {wall:.1f} s | "
              f"printed {tot['truth']} right {tot['right']} wrong-box {tot['wrong_box']} invented {tot['invented']} missed {tot['missed']} low {tot['low']} | "
              f"book {book['status']} offset {book['offset']} confirmed {book['offset_confirmed']} restarts {len(book['restarts'])} | "
              f"doubts true {r['true_doubts']} false {r['false_doubts']} missed {r['missed_errors']} | fallbacks {sum(1 for pp in per_page if pp['fallback'])}",
              flush=True)
    (OUT / f"{run}.json").write_text(json.dumps(report, indent=1))
    spent = sum(c["cost_usd"] for fx in report["fixtures"].values() for c in fx["calls"])
    print(f"total ${spent:.4f}")


if __name__ == "__main__":
    run = sys.argv[1]
    asyncio.run(main(run, sys.argv[2:] or list(FIXTURES)))
