"""Printed bar numbers as a check on the geometric count (CK's decision 3, 2026-11-02). Meta model: **Muse Spark 1.3**,
one small call per page at effort minimal (chat completions, through `ctx.complete`), on the same annotated page the
label call sees (the geometry's measure boxes drawn and provisionally numbered).

The bar count of a scanned book is geometric: OpenCV finds the barlines (`cut.page_measures`) and `process_pages`
numbers the boxes in order. Most engraved editions also print bar numbers, one at the start of each system or one
every 5 or 10 bars. Spark reads those digits and says which blue box each one numbers; it never counts bars and never
works a number out. The code then compares the printed numbers with the count:

- **Agreement** confirms the numbering (the summary says so; the book sheet can say "checked against the printed
  bar numbers").
- **A consistent offset** (the scan starts at bar 24, or a pickup the edition does not number) re-bases the book, but
  only when it is confirmed: the readings that open the book agree on it over at least two systems, and the admin has
  not set the first bar in Details.
- **A disagreement** (the count jumps between two readings: a missed barline, a repeat sign or a stem counted as a bar,
  a box that swallowed several bars) flags the systems between the two readings: their bars are doubted, the job log
  says where, and the page that showed it on its own is read again at low first (the path `page_doubts` uses for part
  names).

The printed numbers never silently override the geometry: after a disagreement the count stays as it is, and a
numbering that restarts (a new movement or variation numbered from 1) is a new run of comparisons, never a doubt.
Readings Spark gives with low confidence are left out; a single reading whose difference disagrees with both of its
neighbours (which agree with each other) is taken as a misread digit and ignored, never as a doubt.
"""
from __future__ import annotations

import time
from decimal import Decimal
from typing import Any

from . import JobContext
from .labels import annotated_png, extract_json

EFFORT = "minimal"            # chat completions; a page whose readings disagree with its own count is read again at low
FALLBACK_EFFORT = "low"
MAX_TOKENS = 8000             # the project's budget for a JSON answer (Spark's reasoning counts against it)
MAX_NUMBER = 9999

SYSTEM = "You read printed sheet music. Answer with strict JSON only, no prose."

PROMPT = """This is a scanned page of printed sheet music. Blue boxes with provisional numbers (1..{n}, left to right, top to bottom) mark the measures a geometry detector found; dashed grey boxes mark the systems. The blue numbers and boxes were drawn by the detector: they are not part of the page.

Many editions print bar numbers (measure numbers) on the page: a small number, plain or in a small box, above the top staff or between the staves at the start of a system, or above a barline every 5 or 10 bars. List every bar number printed on this page and the blue box of the bar it numbers. A number at the start of a system numbers the first bar of that system (the box that holds the clef and the first notes). A number over a barline inside a system numbers the bar that begins there (the box to the right of that barline).

A bar number stands at the left edge of a system or directly above a barline, never over the middle of a bar. These are not bar numbers: the page number and plate or catalogue numbers in the margins; the number of a piece or movement (a large number before the first system); fingering (small digits above, below or next to note heads, including two or three digits together such as 52 or 435 for a change of finger, often under a small arc); tuplet numbers (3, 6 over notes); time signatures; metronome marks; figured bass; rehearsal letters; footnote marks; dates and any text.

Report only digits you can read printed on the page. Do not count bars and do not work out a number that is not printed. If one box seems to carry two printed numbers, list both. If the page prints no bar numbers, return an empty list. Give confidence "low" when you are unsure the digits are a bar number or which box they belong to.

Return only JSON:
{{"bar_numbers": [{{"number": 24, "box": 5, "confidence": "high|medium|low"}}], "none_printed": false}}"""


# ---------------------------------------------------------------- the read: one Spark call per page

def parse_readings(data: dict[str, Any], n_boxes: int) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """(kept, dropped) from Spark's answer: a reading is kept when its number is a whole number 1..9999 and its box is
    drawn on this page (1..n_boxes); its confidence is kept as said (the comparison leaves out the low ones)."""
    kept: list[dict[str, Any]] = []
    dropped: list[dict[str, Any]] = []
    raw = data.get("bar_numbers")
    for d in raw if isinstance(raw, list) else []:
        if not isinstance(d, dict):
            continue
        num, box = _int(d.get("number")), _int(d.get("box", d.get("provisional_measure")))
        conf = str(d.get("confidence") or "low").lower()
        conf = conf if conf in ("high", "medium", "low") else "low"
        item = {"number": num, "box": box, "confidence": conf}
        if num is None or not 1 <= num <= MAX_NUMBER:
            dropped.append({**item, "number": d.get("number"), "why": "not a bar number"})
        elif box is None or not 1 <= box <= n_boxes:
            dropped.append({**item, "box": d.get("box"), "why": "no box" if d.get("box") is None else "box not on the page"})
        elif not any(k["number"] == num and k["box"] == box for k in kept):
            kept.append(item)
    return kept, dropped


async def read_printed(ctx: JobContext, page_png: bytes, geo: dict[str, Any], *, effort: str = EFFORT,
                       annotated: bytes | None = None) -> dict[str, Any]:
    """The page's printed bar numbers: {readings: [{number, box, confidence}], dropped, none_printed, effort, model,
    cost_usd, seconds}; `error` instead of readings when the answer had no JSON (the page is then simply not checked:
    a failed check never fails the page)."""
    png = annotated or annotated_png(page_png, geo)
    n = len(geo["measures"])
    t0 = time.monotonic()
    c = await ctx.complete(PROMPT.format(n=n), system=SYSTEM, effort=effort, max_tokens=MAX_TOKENS, image_png_b64=ctx.png_b64(png))
    out: dict[str, Any] = {"effort": effort, "model": c.charge.model, "cost_usd": float(c.charge.cost_usd),
                           "seconds": round(time.monotonic() - t0, 2), "readings": [], "dropped": []}
    try:
        data = extract_json(c.text)
    except ValueError as e:
        out["error"] = str(e)[:200]
        return out
    out["readings"], out["dropped"] = parse_readings(data, n)
    out["none_printed"] = not out["readings"] and bool(data.get("none_printed", True))
    return out


# ---------------------------------------------------------------- the comparison: pure, no model

def compare(boxes: list[dict[str, Any]], readings: list[dict[str, Any]]) -> dict[str, Any]:
    """Compare printed numbers with the geometric count.

    `boxes`: every bar in book order, [{page, box, system, number}] (box = the page's provisional number, number = the
    count's bar number). `readings`: [{page, box, number, confidence}].

    Returns {used, ignored, restarts, runs, offset, offset_confirmed, doubts, status}: `doubts` are [{page, system, why,
    boxes}] for the systems the count is doubted in; `offset` the printed minus the counted number at the start of the
    book's first run of readings, confirmed when the readings that open the book agree on it over two systems; `status`
    one of "none" (nothing printed to check), "agrees", "offset", "doubted", "unconfirmed" (a single reading)."""
    pos = {(b["page"], b["box"]): i for i, b in enumerate(boxes)}
    ignored: list[dict[str, Any]] = []
    doubts: list[dict[str, Any]] = []
    by_pos: dict[int, list[int]] = {}
    for r in readings:
        i = pos.get((r["page"], r["box"]))
        if r.get("confidence") == "low":
            ignored.append({**r, "why": "low confidence"})
        elif i is None:
            ignored.append({**r, "why": "box not found"})
        else:
            by_pos.setdefault(i, []).append(int(r["number"]))
    pts: list[dict[str, Any]] = []
    for i in sorted(by_pos):
        nums = sorted(set(by_pos[i]))
        b = boxes[i]
        if len(nums) > 1:
            _doubt(doubts, boxes, [i], f"box {b['box']} carries printed bars {', '.join(map(str, nums))}: it holds more than one bar")
        pts.append({"pos": i, "page": b["page"], "box": b["box"], "system": b["system"], "printed": nums[0], "counted": b["number"],
                    "delta": nums[0] - b["number"]})

    # a single misread: its difference disagrees with both neighbours, which agree with each other
    clean: list[dict[str, Any]] = []
    for k, p in enumerate(pts):
        if 0 < k < len(pts) - 1 and pts[k - 1]["delta"] == pts[k + 1]["delta"] != p["delta"]:
            ignored.append({"page": p["page"], "box": p["box"], "number": p["printed"], "why": "misread: its neighbours agree with the count"})
            continue
        clean.append(p)

    # runs: a printed number lower than the one before starts a new numbering (a movement or a variation from bar 1)
    clean_runs: list[list[dict[str, Any]]] = []
    for p in clean:
        if clean_runs and p["printed"] > clean_runs[-1][-1]["printed"]:
            clean_runs[-1].append(p)
        else:
            clean_runs.append([p])
    restarts = [{"page": r[0]["page"], "box": r[0]["box"], "printed": r[0]["printed"]} for r in clean_runs[1:]]

    for run in clean_runs:
        for a, b in zip(run, run[1:]):
            if a["delta"] == b["delta"]:
                continue
            gap_p, gap_c = b["printed"] - a["printed"], b["counted"] - a["counted"]
            where = f"bar {b['printed']} (page {b['page']}, box {b['box']})" if b["page"] != a["page"] else f"bar {b['printed']} (box {b['box']})"
            _doubt(doubts, boxes, list(range(a["pos"], b["pos"])),
                   f"printed bar {a['printed']} (page {a['page']}, box {a['box']}) to {where} is {gap_p} bars; the count found {gap_c}")

    first = clean_runs[0] if clean_runs else []
    offset = first[0]["delta"] if first else None
    # confirmed: the readings that open the book agree on one difference over at least two systems
    opening = []
    for p in first:
        if p["delta"] != offset:
            break
        opening.append(p)
    confirmed = len(opening) >= 2 and len({(p["page"], p["system"]) for p in opening}) >= 2
    used = sum(len(r) for r in clean_runs)
    if not used:
        status = "none"
    elif doubts:
        status = "doubted"
    elif not confirmed:
        status = "unconfirmed"
    else:
        status = "offset" if offset else "agrees"
    return {"used": used, "ignored": ignored, "restarts": restarts, "runs": len(clean_runs), "offset": offset,
            "offset_confirmed": confirmed, "doubts": doubts, "status": status,
            "agree": sum(1 for r in clean_runs for p in r if p["delta"] == r[0]["delta"])}


def _doubt(doubts: list[dict[str, Any]], boxes: list[dict[str, Any]], positions: list[int], why: str) -> None:
    """Doubt every system that holds one of `positions`, once per system (the first reason kept, later ones added)."""
    for i in positions:
        b = boxes[i]
        d = next((x for x in doubts if x["page"] == b["page"] and x["system"] == b["system"]), None)
        if d is None:
            doubts.append({"page": b["page"], "system": b["system"], "why": why, "boxes": [b["box"]]})
        else:
            if b["box"] not in d["boxes"]:
                d["boxes"].append(b["box"])
            if why not in d["why"]:
                d["why"] += "; " + why


def page_disagrees(geo: dict[str, Any], readings: list[dict[str, Any]], page: int = 0) -> list[str]:
    """Why one page's printed numbers do not fit its own count (the page alone, numbered by its provisional boxes): the
    read-time guard. A page with reasons is read again at FALLBACK_EFFORT before anything is doubted."""
    boxes = [{"page": page, "box": m["provisional"], "system": m["system"], "number": m["provisional"]} for m in geo["measures"]]
    res = compare(boxes, [{**r, "page": page} for r in readings])
    return [f"system {d['system']}: {d['why']}" for d in res["doubts"]]


def verify_book(pages: list[tuple[int, dict[str, Any], dict[str, Any] | None]], number_of: dict[tuple[int, int], int]) -> dict[str, Any]:
    """The whole book: `pages` [(page_no, geometry, numbers record or None)] in page order; `number_of` (page, box) -> the
    count's bar number. Returns `compare`'s result plus `read` (readings Spark gave), `pages_checked`, `cost_usd`."""
    boxes = [{"page": pno, "box": m["provisional"], "system": m["system"], "number": number_of[(pno, m["provisional"])]}
             for pno, geo, _ in pages for m in geo["measures"] if (pno, m["provisional"]) in number_of]
    readings = [{**r, "page": pno} for pno, _, rec in pages if rec for r in rec.get("readings") or []]
    res = compare(boxes, readings)
    res["read"] = len(readings)
    res["pages_checked"] = sum(1 for _, _, rec in pages if rec and "error" not in rec)
    res["cost_usd"] = float(sum(Decimal(str(rec.get("cost_usd") or 0)) + Decimal(str(rec.get("first_cost_usd") or 0)) for _, _, rec in pages if rec))
    return res


def _int(v: Any) -> int | None:
    if isinstance(v, bool):
        return None
    try:
        f = float(str(v).strip())
    except (TypeError, ValueError):
        return None
    return int(f) if f.is_integer() else None
