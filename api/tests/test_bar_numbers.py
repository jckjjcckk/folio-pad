"""Printed bar numbers as a check on the geometric count (CK's decision 3, 2026-11-02): the comparison (agreement, a
confirmed offset that re-bases, a disagreement that doubts a system, a restart that is not a doubt, a misread that is
ignored, low confidence left out), the answer's parsing, and `process_pages` with the check on: the offset applied, the
admin's first bar holding, a doubt downgrading the system's bars, the in-page fallback to low. Synthetic pages, scripted
model, fake database; no network."""
from __future__ import annotations

import json
from decimal import Decimal

import pytest

from app.agent.fake import fake_client
from app.librarian import bar_numbers as bn
from app.librarian import process_pages as pp
from app.librarian.process_pages import process_pages
from app.llm import Completion
from app.spend import Charge
from tests.test_part_cut import HEADER
from tests.test_signature import LABELS, SCORE, PagesCtx, job, pages_world, sig


def book(*systems_per_page: list[int]) -> list[dict]:
    """Bars in book order, counted from 1: each page a list of bars per system."""
    out, n = [], 1
    for p, systems in enumerate(systems_per_page, start=1):
        box = 1
        for s, bars in enumerate(systems, start=1):
            for _ in range(bars):
                out.append({"page": p, "box": box, "system": s, "number": n})
                box += 1
                n += 1
    return out


def rd(page: int, box: int, number: int, confidence: str = "high") -> dict:
    return {"page": page, "box": box, "number": number, "confidence": confidence}


# ---------------------------------------------------------------- the comparison

def test_numbers_at_each_system_start_that_fit_the_count_confirm_it():
    boxes = book([4, 4, 4], [4, 4])
    res = bn.compare(boxes, [rd(1, 5, 5), rd(1, 9, 9), rd(2, 1, 13), rd(2, 5, 17)])
    assert res["status"] == "agrees" and res["offset"] == 0 and res["offset_confirmed"] and not res["doubts"] and res["used"] == 4


def test_a_scan_that_starts_at_bar_24_is_a_confirmed_offset():
    boxes = book([4, 4], [4, 4])
    res = bn.compare(boxes, [rd(1, 1, 24), rd(1, 5, 28), rd(2, 1, 32)])
    assert res["status"] == "offset" and res["offset"] == 23 and res["offset_confirmed"] and not res["doubts"]


def test_one_reading_alone_confirms_nothing():
    res = bn.compare(book([4, 4]), [rd(1, 5, 30)])
    assert res["status"] == "unconfirmed" and res["offset"] == 25 and not res["offset_confirmed"]
    # two readings on one system do not confirm either
    res = bn.compare(book([4, 4]), [rd(1, 1, 30), rd(1, 3, 32)])
    assert not res["offset_confirmed"]


def test_an_extra_barline_doubts_the_system_it_is_in_and_no_other():
    """System 2 of page 1 has a stem counted as a barline: 5 boxes for 4 bars. The printed numbers jump by 4 where the
    count found 5; the systems before and after agree."""
    boxes = book([4, 5, 4], [4])
    res = bn.compare(boxes, [rd(1, 1, 1), rd(1, 5, 5), rd(1, 10, 9), rd(2, 1, 13)])
    assert res["status"] == "doubted"
    assert [(d["page"], d["system"]) for d in res["doubts"]] == [(1, 2)]
    assert "printed bar 5" in res["doubts"][0]["why"] and "is 4 bars; the count found 5" in res["doubts"][0]["why"]
    assert res["offset"] == 0 and res["offset_confirmed"]


def test_a_missed_barline_across_a_page_turn_doubts_the_last_system_of_the_page():
    """Ekier p. 15: the last system is one box for three bars; the next page's first number shows it."""
    boxes = book([4, 4], [3])
    res = bn.compare(boxes, [rd(1, 1, 1), rd(1, 5, 5), rd(2, 1, 11)])
    assert [(d["page"], d["system"]) for d in res["doubts"]] == [(1, 2)]
    assert "the count found 4" in res["doubts"][0]["why"] and "page 2" in res["doubts"][0]["why"]


def test_a_box_with_two_printed_numbers_holds_more_than_one_bar():
    boxes = book([1], [4])
    res = bn.compare(boxes, [rd(1, 1, 17), rd(1, 1, 20), rd(1, 1, 23)])
    assert [(d["page"], d["system"]) for d in res["doubts"]] == [(1, 1)]
    assert "carries printed bars 17, 20, 23" in res["doubts"][0]["why"]


def test_a_numbering_that_starts_again_is_a_new_run_not_a_doubt():
    """Peters Goldberg: the Aria ends at bar 32, Variation 1 is numbered from 1 again; geometry numbers the book through."""
    boxes = book([4, 4], [4, 4])
    res = bn.compare(boxes, [rd(1, 1, 1), rd(1, 5, 5), rd(2, 1, 1), rd(2, 5, 5)])
    assert res["status"] == "agrees" and not res["doubts"] and res["runs"] == 2
    assert res["restarts"] == [{"page": 2, "box": 1, "printed": 1}]
    # inside the second run a miscount is still found
    boxes = book([4, 4], [4, 5, 4])
    res = bn.compare(boxes, [rd(1, 1, 1), rd(1, 5, 5), rd(2, 1, 1), rd(2, 5, 5), rd(2, 10, 9)])
    assert [(d["page"], d["system"]) for d in res["doubts"]] == [(2, 2)]


def test_one_misread_digit_between_two_agreeing_neighbours_is_ignored():
    boxes = book([4, 4, 4, 4])
    res = bn.compare(boxes, [rd(1, 1, 1), rd(1, 5, 5), rd(1, 9, 19), rd(1, 13, 13)])
    assert res["status"] == "agrees" and not res["doubts"]
    assert [i["number"] for i in res["ignored"]] == [19] and "misread" in res["ignored"][0]["why"]


def test_low_confidence_and_unknown_boxes_are_left_out():
    boxes = book([4, 4])
    res = bn.compare(boxes, [rd(1, 1, 1), rd(1, 5, 7, "low"), rd(3, 1, 9)])
    assert res["used"] == 1 and {i["why"] for i in res["ignored"]} == {"low confidence", "box not found"}
    assert not res["doubts"]


def test_no_printed_numbers_is_status_none():
    res = bn.compare(book([4, 4]), [])
    assert res["status"] == "none" and res["offset"] is None and not res["offset_confirmed"]


def test_page_disagrees_reads_one_page_against_its_own_boxes():
    geo = {"measures": [{"provisional": k, "system": 1 if k <= 4 else 2} for k in range(1, 10)]}
    assert bn.page_disagrees(geo, [{"box": 1, "number": 30, "confidence": "high"}, {"box": 5, "number": 34, "confidence": "high"}]) == []
    why = bn.page_disagrees(geo, [{"box": 1, "number": 30, "confidence": "high"}, {"box": 5, "number": 33, "confidence": "high"}])
    assert len(why) == 1 and why[0].startswith("system 1:")


def test_parse_readings_keeps_numbers_on_drawn_boxes_only():
    kept, dropped = bn.parse_readings({"bar_numbers": [
        {"number": 5, "box": 5, "confidence": "high"}, {"number": "9", "box": "9", "confidence": "Medium"},
        {"number": 5, "box": 5, "confidence": "high"}, {"number": 13, "box": 40}, {"number": "IV", "box": 2},
        {"number": 0, "box": 1}, {"number": 17, "box": None}, "junk"]}, 20)
    assert kept == [{"number": 5, "box": 5, "confidence": "high"}, {"number": 9, "box": 9, "confidence": "medium"}]
    assert [d["why"] for d in dropped] == ["box not on the page", "not a bar number", "not a bar number", "no box"]
    assert bn.parse_readings({}, 4) == ([], [])


# ---------------------------------------------------------------- process_pages with the check on

@pytest.fixture
def printed_on(monkeypatch):
    monkeypatch.setattr(pp, "READ_PRINTED", True)
    monkeypatch.setattr(pp, "PAGE_EFFORT", "low")       # one label answer per page; the label guard is tested elsewhere


class PrintedCtx(PagesCtx):
    """Labels from `labels`, printed-number reads from `printed` (one answer per call, in call order); each printed read's
    effort is kept."""
    def __init__(self, *a, printed: list[dict], **k):
        super().__init__(*a, **k)
        self.printed = list(printed)
        self.printed_efforts: list[str] = []

    async def complete(self, user_text: str, **kw) -> Completion:
        if kw.get("system") == bn.SYSTEM:
            self.printed_efforts.append(kw.get("effort"))
            c = Completion(json.dumps(self.printed.pop(0)), Charge("meta", "muse-spark-1.3", "spark", Decimal("0.004"), 900, 60), "chat")
            self.charge(c.charge)
            return c
        return await super().complete(user_text, **kw)


def answer(*pairs: tuple[int, int]) -> dict:
    return {"bar_numbers": [{"number": n, "box": b, "confidence": "high"} for b, n in pairs], "none_printed": not pairs}


async def run(printed: list[dict], n_pages: int = 2, first_bar: int | None = None) -> tuple[dict, PrintedCtx, dict]:
    db, pages = pages_world(n_pages)
    if first_bar is not None:
        db.rows["scores"][0]["first_bar"] = first_bar
    ctx = PrintedCtx(job({"score_id": SCORE, "source_id": "src1"}), db, pages, labels=[LABELS] * n_pages, printed=printed)
    c, _ = fake_client([sig(), HEADER])
    out = await process_pages(job({"score_id": SCORE, "source_id": "src1"}), ctx, client=c, model="muse-spark-1.3")
    return out, ctx, db


def numbers(db) -> list[int]:
    by_id = {r["id"]: r["number"] for r in db.rows["measures"]}
    return [by_id[p["measure_id"]] for p in db.rows["measure_placements"]]


async def test_a_confirmed_offset_renumbers_the_book_from_the_printed_bar(printed_on):
    """Two pages of four bars; the edition prints 25 over page 1's first bar and 29 over page 2's."""
    out, ctx, db = await run([answer((1, 25)), answer((1, 29))])
    assert numbers(db) == list(range(25, 33)) and db.rows["scores"][0]["bars"] == 8
    s = db.rows["interpretations"][0]["summary"]
    assert s["first_measure"] == 25 and s["bar_numbers"]["status"] == "offset" and s["bar_numbers"]["offset_applied"]
    assert s["bar_numbers"]["counted"] == "page"
    assert "The printed bar numbers run +24 from the count at the start of the book; numbered from bar 25 as printed" in s["log"]
    assert ctx.printed_efforts == ["minimal", "minimal"]
    assert out["cost_usd"] == pytest.approx(float(sum(ch.cost_usd for ch in ctx.charges)))


async def test_the_admins_first_bar_holds_against_a_printed_offset(printed_on):
    out, ctx, db = await run([answer((1, 25)), answer((1, 29))], first_bar=1)
    assert numbers(db) == list(range(1, 9))
    s = db.rows["interpretations"][0]["summary"]
    assert s["bar_numbers"]["offset"] == 24 and not s["bar_numbers"]["offset_applied"]
    assert any("the first bar set in Details holds" in line for line in s["log"])


async def test_a_disagreement_doubts_the_system_and_keeps_the_count(printed_on):
    """Page 2 prints bar 6 where the count says 5: page 1's system holds a bar too many by the printed numbers."""
    out, ctx, db = await run([answer((1, 1), (3, 3)), answer((1, 6))])
    assert numbers(db) == list(range(1, 9))                                  # the count stays
    pl = db.rows["measure_placements"]
    assert all(p["confidence"] != "high" and "printed bar numbers disagree" in p["flag"] for p in pl if p["page"] == 1)
    assert not any("printed bar numbers" in (p["flag"] or "") for p in pl if p["page"] == 2)
    s = db.rows["interpretations"][0]["summary"]
    assert s["bar_numbers"]["status"] == "doubted" and [(d["page"], d["system"]) for d in s["bar_numbers"]["doubted"]] == [(1, 1)]
    assert any(line.startswith("Page 1 system 1: the printed bar numbers disagree with the count") for line in s["log"])
    assert s["flagged"]["bars_doubtful"] >= 4


async def test_a_page_that_disagrees_with_itself_is_read_again_at_low(printed_on):
    """Minimal reads page 1's second number as 5 (the count says 3); low reads 3: nothing is doubted."""
    out, ctx, db = await run([answer((1, 1), (3, 5)), answer((1, 1), (3, 3)), answer((1, 5))])   # page 1 at minimal, again at low; page 2
    assert sorted(ctx.printed_efforts) == ["low", "minimal", "minimal"]
    state = db.rows["interpretations"][0]["params"]["state"]
    rec = state["pages"]["1"]["numbers"]
    assert rec["effort"] == "low" and rec["fallback"] and rec["first_readings"][1]["number"] == 5
    assert any("read again at low" in line for line in state["log"])
    s = db.rows["interpretations"][0]["summary"]
    assert s["bar_numbers"]["status"] == "agrees" and not s["bar_numbers"]["doubted"]
    assert s["bar_numbers"]["cost_usd"] == pytest.approx(0.012)


async def test_no_printed_numbers_says_the_bars_are_counted_from_the_page(printed_on):
    out, ctx, db = await run([answer(), answer()])
    s = db.rows["interpretations"][0]["summary"]
    assert s["bar_numbers"]["status"] == "none" and numbers(db) == list(range(1, 9))
    assert "No printed bar numbers read on 2 pages; the bars are counted from the page" in s["log"]


async def test_a_failed_printed_read_never_fails_the_page(printed_on):
    out, ctx, db = await run([{"nothing": "here"}, "not json at all"])
    assert db.rows["scores"][0]["status"] == "ready" and numbers(db) == list(range(1, 9))
    assert db.rows["interpretations"][0]["summary"]["bar_numbers"]["status"] == "none"


async def test_the_check_off_leaves_the_summary_unchecked():
    out, ctx, db = await run([])
    assert db.rows["interpretations"][0]["summary"]["bar_numbers"] == {"counted": "page", "status": "unchecked"}
