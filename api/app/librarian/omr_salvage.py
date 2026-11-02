"""When a page of a book will not transcribe (feature 005, CK 2026-11-02: a bad page must not fail a convert). No model.

The box tries a page Audiveris cannot read twice more and leaves it out of the stitched book (`omr_box.recover_page`).
Two failures only show on the Mac, once the pages come back:
  - a page Audiveris read with a different number of staves from the rest of the book (Cappi 1802: 3 staves on some
    pages, 2 or 4 on others), so the movements cannot be put on one set of parts;
  - a page whose bars do not match its own export, or that exported a movement with no bars on the map.
For a page-by-page read (each page its own movement(s)) such pages can be taken out of the run directory and the rest
merged: `odd_pages` finds the staff-count outliers, `pages_of_movement` names the page of a movement `merge` refused,
`drop_pages` rewrites the run (sheets, book.xml, exports, movements.json) as if Audiveris had never read those pages.

`reading_bars` is the page's geometry-only fallback: the bars the 004 page reading placed on each PDF page (its
`measure_placements` boxes), so an unreadable page keeps its bars as rests and every later bar its number.
"""
from __future__ import annotations

import json
import shutil
import xml.etree.ElementTree as ET
import zipfile
from collections import Counter
from pathlib import Path
from typing import Any

from .omr_score import movement_files


def staff_count(mxl: Path) -> int:
    """How many staves an Audiveris export holds (what music21 makes parts of): each part's `<staves>`, else 1."""
    with zipfile.ZipFile(mxl) as z:
        name = next((n for n in z.namelist() if n.endswith(".xml") and not n.startswith("META-INF")), None)
        root = ET.fromstring(z.read(name)) if name else None
    if root is None:
        return 0
    total = 0
    for part in root.findall("part"):
        st = part.find("measure/attributes/staves")
        total += int(st.text) if st is not None and (st.text or "").strip().isdigit() else 1
    return total


def _movements(run: Path) -> list[dict]:
    return json.loads((run / "movements.json").read_text())


def odd_pages(run: Path) -> dict[int, str]:
    """Pages (sheet numbers) whose export has a different number of staves from the book's: the count most of the
    book's bars are in (ties: the first page's). {sheet: reason}."""
    mvs = _movements(run)
    files = movement_files(run)
    counts: dict[int, int] = {}
    for k, f in enumerate(files, start=1):
        try:
            counts[k] = staff_count(f)
        except (zipfile.BadZipFile, ET.ParseError, KeyError, OSError):
            counts[k] = 0
    sheet_of = {m["movement"]: m["sheet"] for m in mvs}
    bars = Counter()
    for m in mvs:
        bars[counts.get(m["movement"], 0)] += m.get("measures", 0) or 0
    first = counts.get(1, 0)
    book = max(bars, key=lambda c: (bars[c], c == first)) if bars else first
    out: dict[int, str] = {}
    for k, c in counts.items():
        if c != book and k in sheet_of:
            out.setdefault(sheet_of[k], f"the transcription engine read {c} staves on this page where the rest of the book has {book}")
    return out


def pages_of_movement(run: Path, movement: int | None) -> set[int]:
    """The page (sheet) a movement number belongs to; with no movement named, the pages whose exports have no bar on the
    map at all (a movement `read_book` found no stacks for)."""
    mvs = _movements(run)
    if movement is not None:
        return {m["sheet"] for m in mvs if m["movement"] == movement}
    return set()


def unmapped_pages(run: Path, doc: dict) -> set[int]:
    """Pages whose movements exported a file but put no bar on the map (`merge`'s "the page map has movements ...")."""
    mapped = {m["movement"] for m in doc["measures"]}
    return {m["sheet"] for m in _movements(run) if m["movement"] not in mapped}


def drop_pages(run: Path, sheets: set[int]) -> None:
    """Take these sheets out of a page-by-page run: their sheet folders, their `<sheet>`/`<score>` entries in book.xml,
    their export files and their movements, the later movements renumbered (exports renamed to match), so the run reads
    as if Audiveris had only read the other pages."""
    if not sheets:
        return
    mvs = _movements(run)
    files = movement_files(run)
    keep = [m for m in mvs if m["sheet"] not in sheets]
    kept_mvts = sorted({m["movement"] for m in keep})
    renumber = {old: new for new, old in enumerate(kept_mvts, start=1)}
    stem = files[0].name.split(".mvt")[0].removesuffix(".mxl") if files else "book"
    tmp = run / "_mvt"
    tmp.mkdir(exist_ok=True)
    for k, f in enumerate(files, start=1):
        if k in renumber:
            shutil.move(str(f), str(tmp / f"{stem}.mvt{renumber[k]}.mxl"))
        else:
            f.unlink()
    for f in tmp.iterdir():
        shutil.move(str(f), str(run / f.name))
    tmp.rmdir()
    for m in keep:
        m["movement"] = renumber[m["movement"]]
    (run / "movements.json").write_text(json.dumps(keep, indent=1))
    book = run / "book"
    root = ET.parse(book / "book.xml").getroot()
    for el in list(root):
        if el.tag == "sheet" and int(el.get("number", 0)) in sheets:
            root.remove(el)
        elif el.tag == "score" and any(int(r.get("sheet-number", 0)) in sheets for r in el.findall("page")):
            root.remove(el)
    (book / "book.xml").write_bytes(ET.tostring(root))
    for n in sheets:
        shutil.rmtree(book / f"sheet#{n}", ignore_errors=True)


def reading_bars(db: Any, score_id: str, src: dict) -> dict[int, list[dict | None]]:
    """The bars the 004 page reading placed on each PDF page: {pdf_page: [box, ...]} in reading order (system, then
    left to right), from the book's current interpretation. Empty when the book has no reading (a convert never needs
    one) or it cannot be read."""
    try:
        score = (db.table("scores").select("current_interpretation_id").eq("id", score_id).limit(1).execute().data or [{}])[0]
        iid = score.get("current_interpretation_id")
        if not iid:
            return {}
        rows = db.table("measure_placements").select("page,system,box").eq("interpretation_id", iid).execute().data or []
    except Exception:  # noqa: BLE001  (no counts: the bars after the page are numbered on from the page before)
        return {}
    order = src.get("page_order") or []
    out: dict[int, list[tuple]] = {}
    for r in rows:
        if r.get("system") is None or not isinstance(r.get("page"), int):
            continue                                    # "not found in vN" rows carry no system
        idx = r["page"]
        page = order[idx - 1] if 0 < idx <= len(order) else idx
        box = r.get("box") if isinstance(r.get("box"), dict) and r["box"].get("x1") else None
        out.setdefault(page, []).append((r["system"], (box or {}).get("x0", 0), box))
    return {p: [b for _, _, b in sorted(v, key=lambda t: (t[0], t[1]))] for p, v in out.items()}
