"""`omr_box.py --parallel`: each page its own Audiveris book, stitched into the whole-book layout that
`omr_book.load_run` reads. Audiveris and pdfseparate are stood in for; the stitching is the code under test."""
import json
import zipfile
from pathlib import Path

from app.librarian import omr_box


def book_xml(pages: list[tuple[int, bool, str | None]]) -> str:
    """One sheet with these Audiveris pages: (measures, movement-start, movement name)."""
    pgs = "".join(f'<page id="{i}" {"movement-start=\"true\" " if start else ""}delta-measure-id="{n}"/>' for i, (n, start, _) in enumerate(pages, 1))
    scores = "".join(f'<score id="{i}"><page sheet-number="1" sheet-page-id="{i}"/><logical-part name="{name}"/></score>'
                     for i, (_, start, name) in enumerate(pages, 1) if start and name)
    return f'<book><sheet number="1">{pgs}</sheet>{scores}</book>'


def test_pages_are_stitched_in_order_each_a_movement(tmp_path, monkeypatch):
    # page 1: one Audiveris page (the Aria starts); page 2: the Aria's end, then Var. 1 starts mid-page (two pages)
    layout = {1: [(28, True, "Aria")], 2: [(4, False, None), (16, True, "Var. 1.")]}
    calls = []

    def fake_run(cmd, **kw):
        assert cmd[0] == "pdfseparate"
        Path(cmd[-1]).write_bytes(b"%PDF one page")
        return None

    def fake_audiveris(pdf: Path, out: Path):
        page = int(out.name)
        calls.append(page)
        with zipfile.ZipFile(out / f"{pdf.stem}.omr", "w") as z:
            z.writestr("book.xml", book_xml(layout[page]))
            z.writestr("sheet#1/sheet#1.xml", f"<sheet page='{page}'/>")
            z.writestr("sheet#1/BINARY.png", b"png")
        k = len(layout[page])
        names = [f"{pdf.stem}.mxl"] if k == 1 else [f"{pdf.stem}.mvt{j}.mxl" for j in range(1, k + 1)]
        for j, n in enumerate(names, 1):
            (out / n).write_text(f"page {page} part {j}")
        (out / "audiveris.log").write_text("ok")
        return 0, 1.0

    monkeypatch.setattr(omr_box.subprocess, "run", fake_run)
    monkeypatch.setattr(omr_box, "run_audiveris", fake_audiveris)
    rc, secs, movements, tail, report = omr_box.parallel_pages(tmp_path / "book.pdf", 2, tmp_path, "book", [7, 8], workers=2)
    assert rc == 0 and sorted(calls) == [1, 2] and report == {"skipped": [], "recovered": []}
    assert [(m["sheet"], m["pdf_page"], m["page"], m["movement"], m["measures"]) for m in movements] == [
        (1, 7, 1, 1, 28), (2, 8, 1, 2, 4), (2, 8, 2, 3, 16)]
    assert [m["name"] for m in movements] == ["Aria", None, "Var. 1."]
    assert [(tmp_path / f"book.mvt{k}.mxl").read_text() for k in (1, 2, 3)] == ["page 1 part 1", "page 2 part 1", "page 2 part 2"]
    assert (tmp_path / "book" / "sheet#2" / "sheet#2.xml").read_text() == "<sheet page='2'/>"
    assert not list((tmp_path / "book").glob("sheet#*/BINARY.png")) and not (tmp_path / "pp").exists()
    # the stitched book.xml is what detected_movements and omr_book read: sheets 1 and 2 in order
    again = omr_box.detected_movements((tmp_path / "book" / "book.xml").read_bytes(), [7, 8])
    assert json.dumps(again) == json.dumps(movements)


NPE = "INFO start\nERROR java.lang.NullPointerException: staff is null\nlast line"
TOO_LARGE = ("INFO  [book]  SheetStub 1278 | Loaded image #1 6250x7999\n"
             "WARN  [book]                 SheetStub 411  | Too large image: 49,993,750 pixels (vs 20,000,000 max)\n"
             "WARN  [book]                      Book 2044 | Error processing stub org.audiveris.omr.step.StepException: Sheet ignored\n")


def fake_tools(tmp_path, monkeypatch, fails, log: str = NPE):
    """pdfseparate and pdftoppm stood in for; Audiveris writes a one-page book unless `fails(page, input)` says no
    (then it exits 1 with an exception in its log). Returns the list of (page, input name) it was run on."""
    runs = []

    def fake_run(cmd, **kw):
        if cmd[0] == "pdftoppm":
            Path(cmd[-1] + ".png").write_bytes(f"png {cmd[2]}".encode())
        else:
            Path(cmd[-1]).write_bytes(b"%PDF")
        return type("P", (), {"returncode": 0})()

    def fake_audiveris(src: Path, out: Path):
        page = int(out.name)
        runs.append((page, src.name))
        if fails(page, src.name, len([r for r in runs if r[0] == page])):
            (out / "audiveris.log").write_text(log)
            return 1, 2.0
        with zipfile.ZipFile(out / f"{src.stem}.omr", "w") as z:
            z.writestr("book.xml", book_xml([(3, True, None)]))
            z.writestr("sheet#1/sheet#1.xml", f"<sheet page='{page}'/>")
        (out / f"{src.stem}.mxl").write_text(f"page {page}")
        (out / "audiveris.log").write_text("ok")
        return 0, 2.0

    monkeypatch.setattr(omr_box.subprocess, "run", fake_run)
    monkeypatch.setattr(omr_box, "run_audiveris", fake_audiveris)
    (tmp_path / "scan").mkdir(exist_ok=True)
    return runs


def test_a_page_audiveris_fails_on_is_tried_twice_more_then_left_out(tmp_path, monkeypatch):
    # PC5 p. 4 (E2E night): Audiveris's NullPointerException on one page failed the whole convert. Now the page is read
    # again alone, then from its 300 dpi image, then at 400 dpi, and left out with what was tried; the others still stitch.
    runs = fake_tools(tmp_path, monkeypatch, lambda page, src, n: page == 2)
    rc, _, movements, tail, report = omr_box.parallel_pages(tmp_path / "book.pdf", 3, tmp_path, "book", [4, 5, 6], workers=3)
    assert rc == 0 and tail == []
    assert [r for r in runs if r[0] == 2] == [(2, "book.pdf"), (2, "book.pdf"), (2, "book.png"), (2, "book.png")]
    [skip] = report["skipped"]
    assert skip["pdf_page"] == 5 and skip["index"] == 2 and skip["reason"] == "ERROR java.lang.NullPointerException: staff is null"
    assert [t["step"] for t in skip["tried"]] == ["audiveris", "again alone", "300 dpi image", "400 dpi image"]
    assert [(m["sheet"], m["pdf_page"], m["movement"]) for m in movements] == [(1, 4, 1), (3, 6, 2)]
    assert sorted(f.name for f in tmp_path.glob("book.mvt*.mxl")) == ["book.mvt1.mxl", "book.mvt2.mxl"]
    assert (tmp_path / "book.mvt2.mxl").read_text() == "page 3" and not (tmp_path / "book" / "sheet#2").exists()
    log = (tmp_path / "audiveris.log").read_text()
    assert "=== retry again alone: rc 1" in log and "=== retry 300 dpi image: rc 1" in log and "=== retry 400 dpi image: rc 1" in log


def test_a_page_too_large_for_audiveris_is_read_from_its_300_dpi_scan(tmp_path, monkeypatch):
    # Sym 9, the 1826 scan (E2E night): every page failed, "Too large image: 49,993,750 pixels (vs 20,000,000 max)": the
    # PDF embeds a 6250 x 7999 scan and Audiveris reads it at that size. The 300 dpi image the box renders reads.
    fake_tools(tmp_path, monkeypatch, lambda page, src, n: page == 1 and src.endswith(".pdf"), log=TOO_LARGE)
    (tmp_path / "scan" / "p1.png").write_bytes(b"png 300")
    rc, _, movements, _, report = omr_box.parallel_pages(tmp_path / "book.pdf", 2, tmp_path, "book", [1, 2], workers=2)
    assert rc == 0 and report["skipped"] == [] and len(movements) == 2
    [rec] = report["recovered"]
    # a second try cannot shrink the image: straight to the 300 dpi image
    assert rec["pdf_page"] == 1 and rec["scan_dpi"] == 300 and [t["step"] for t in rec["tried"]] == ["audiveris", "300 dpi image"]
    assert rec["tried"][0]["why"] == "Too large image: 49,993,750 pixels (vs 20,000,000 max)"
    assert (tmp_path / "scan" / "p1.png").read_bytes() == b"png 300"       # read from the scan itself: the frame is unchanged


def test_a_page_still_too_large_at_300_dpi_is_read_at_the_resolution_that_fits(tmp_path, monkeypatch):
    # The Sym 9 pages print at 21 x 27 inches: 50.8 M pixels at 300 dpi. 300 x sqrt(18 M / 50.8 M) = 178 dpi fits.
    fake_tools(tmp_path, monkeypatch, lambda page, src, n: page == 1 and n <= 2,
               log=TOO_LARGE.replace("49,993,750", "50,768,000"))
    (tmp_path / "scan" / "p1.png").write_bytes(b"png 300")
    rc, _, _, _, report = omr_box.parallel_pages(tmp_path / "book.pdf", 2, tmp_path, "book", [1, 2], workers=2)
    [rec] = report["recovered"]
    assert rc == 0 and rec["scan_dpi"] == 178 and [t["step"] for t in rec["tried"]] == ["audiveris", "300 dpi image", "178 dpi image"]
    assert (tmp_path / "scan" / "p1.png").read_bytes() == b"png 178"       # that render is the page's scan now
    assert omr_box._fit_dpi("no", 300) is None and omr_box._fit_dpi("Too large image: 72,000,000 pixels", 300) == 150


def test_a_page_read_on_the_second_try_needs_no_image(tmp_path, monkeypatch):
    fake_tools(tmp_path, monkeypatch, lambda page, src, n: page == 2 and n == 1)
    rc, _, movements, _, report = omr_box.parallel_pages(tmp_path / "book.pdf", 2, tmp_path, "book", [1, 2], workers=2)
    assert rc == 0 and len(movements) == 2 and report["recovered"][0]["tried"][-1] == {"step": "again alone", "rc": 0, "s": 2.0, "why": None}


def test_every_page_failing_fails_the_run_with_each_reason(tmp_path, monkeypatch):
    fake_tools(tmp_path, monkeypatch, lambda page, src, n: True)
    rc, _, movements, tail, report = omr_box.parallel_pages(tmp_path / "book.pdf", 2, tmp_path, "book", [1, 2], workers=2)
    assert rc == 3 and movements == [] and len(report["skipped"]) == 2
    assert tail == ["page 1: ERROR java.lang.NullPointerException: staff is null", "page 2: ERROR java.lang.NullPointerException: staff is null"]


def test_a_failed_whole_book_is_read_page_by_page(tmp_path, monkeypatch, capsys):
    """Without --parallel, a whole-book run that fails is read page by page, so one bad page no longer fails the book;
    with --whole-only (the convert's own fallback) it fails as before."""
    import sys
    calls = []
    monkeypatch.setattr(omr_box, "pdf_page_count", lambda pdf: 2)
    monkeypatch.setattr(omr_box, "render_scans", lambda pdf, n, d: d.mkdir(parents=True, exist_ok=True))
    monkeypatch.setattr(omr_box, "cut_pdf", lambda pdf, pages, dest: None)

    def per_page(book_pdf, n, out, stem, pages, workers):
        calls.append(workers)
        (out / f"{stem}.mvt1.mxl").write_text("page 1")       # a stitched book names its exports mvtK, even one
        mv = [{"sheet": 1, "pdf_page": 1, "page": 1, "movement_start": True, "movement": 1, "name": None, "measures": 3}]
        return 0, 5.0, mv, [], {"skipped": [{"pdf_page": 2}], "recovered": []}
    monkeypatch.setattr(omr_box, "parallel_pages", per_page)

    def whole(pdf, out):
        (out / "audiveris.log").write_text("SEVERE java.lang.NullPointerException")
        return 1, 9.0
    monkeypatch.setattr(omr_box, "run_audiveris", whole)
    pdf = tmp_path / "book.pdf"
    pdf.write_bytes(b"%PDF")
    out = tmp_path / "out"

    def run(*extra):
        monkeypatch.setattr(sys, "argv", ["omr_box.py", str(pdf), str(out), *extra])
        try:
            omr_box.main()
        except SystemExit as e:
            return e.code
        return 0
    (tmp_path / "out").mkdir()
    assert run() == 0 and calls == [2]
    rec = json.loads((out / "book_run.json").read_text())
    assert rec["whole_failed"] == {"rc": 1, "reason": "SEVERE java.lang.NullPointerException", "audiveris_s": 9.0}
    assert rec["skipped"] == [{"pdf_page": 2}] and rec["audiveris_s"] == 14.0 and rec["exports"] == ["book.mvt1.mxl"]
    calls.clear()
    assert run("--whole-only") == 3 and calls == []


def test_a_page_java_refuses_to_sort_is_read_again_with_the_legacy_sort(tmp_path, monkeypatch):
    # Moscheles p. 13 (E2E night): Audiveris exits 1 on TimSort's contract check; the legacy merge sort reads the page.
    (tmp_path / "book.omr").write_text("half a book")
    runs = []

    def fake_run(cmd, stdout=None, stderr=None, env=None):
        runs.append(env.get("JAVA_TOOL_OPTIONS"))
        if len(runs) == 1:
            stdout.write("java.lang.IllegalArgumentException: Comparison method violates its general contract!\n")
            return type("P", (), {"returncode": 1})()
        assert not (tmp_path / "book.omr").exists()      # the failed run's book is not read again
        (tmp_path / "book.omr").write_text("whole")
        return type("P", (), {"returncode": 0})()

    monkeypatch.setattr(omr_box.subprocess, "run", fake_run)
    monkeypatch.delenv("JAVA_TOOL_OPTIONS", raising=False)
    rc, _ = omr_box.run_audiveris(tmp_path / "input" / "book.pdf", tmp_path)
    assert rc == 0 and runs == [None, omr_box.LEGACY_SORT]
    assert "again with" in (tmp_path / "audiveris.log").read_text()


def test_any_other_failure_is_not_retried(tmp_path, monkeypatch):
    runs = []

    def fake_run(cmd, stdout=None, stderr=None, env=None):
        runs.append(1)
        stdout.write("StepException: No regularly spaced lines found\n")
        return type("P", (), {"returncode": 1})()

    monkeypatch.setattr(omr_box.subprocess, "run", fake_run)
    rc, _ = omr_box.run_audiveris(tmp_path / "book.pdf", tmp_path)
    assert rc == 1 and runs == [1]
