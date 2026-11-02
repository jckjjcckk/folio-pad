"""parts_merge (feature 005): the engine's staff fragments of a cut-away full score put back on the book's
instruments. A synthetic whole-book export the way Audiveris 5.11 writes one: every logical part carries every bar,
a stand-in whole-bar rest without `default-x` where the staff is absent from the system, system breaks in every part.
No model, no box."""
from __future__ import annotations

from music21 import clef, converter, layout, stream

from app.librarian.import_musicxml import part_groups
from app.librarian.omr_convert import write_musicxml
from app.librarian.parts_merge import assign_system, candidates, fragments_of, identify, merge_parts, normalise, roster_of, systems_of

DIV = 4


def bar(n: int, content: str, first: bool = False, new_system: bool = False, staves: int = 1, clef_sign: str = "G", clef_line: int = 2) -> str:
    attrs = ""
    if first:
        clefs = "".join(f'<clef number="{k}"><sign>{"F" if k == 2 else clef_sign}</sign><line>{4 if k == 2 else clef_line}</line></clef>'
                        for k in range(1, staves + 1)) if staves > 1 else f"<clef><sign>{clef_sign}</sign><line>{clef_line}</line></clef>"
        attrs = (f"<attributes><divisions>{DIV}</divisions><key><fifths>0</fifths></key><time><beats>4</beats><beat-type>4</beat-type></time>"
                 + (f"<staves>{staves}</staves>" if staves > 1 else "") + clefs + "</attributes>")
    pr = '<print new-system="yes"/>' if new_system else ""
    return f'<measure number="{n}">{pr}{attrs}{content}</measure>'


def absent(staves: int = 1) -> str:
    """The exporter's stand-in: a whole-bar rest with no position (one per staff, backed up)."""
    out = []
    for k in range(1, staves + 1):
        if k > 1:
            out.append(f"<backup><duration>{4 * DIV}</duration></backup>")
        out.append(f'<note><rest measure="yes"/><duration>{4 * DIV}</duration>' + (f"<voice>{k}</voice><staff>{k}</staff>" if staves > 1 else "") + "</note>")
    return "".join(out)


def rest_placed() -> str:
    return f'<note default-x="40"><rest measure="yes"/><duration>{4 * DIV}</duration></note>'


def notes(step: str, octave: int = 4, staves: int = 1) -> str:
    out = [f'<note default-x="30"><pitch><step>{step}</step><octave>{octave}</octave></pitch><duration>{4 * DIV}</duration><type>whole</type>'
           + ("<voice>1</voice><staff>1</staff>" if staves > 1 else "") + "</note>"]
    if staves > 1:
        out.append(f"<backup><duration>{4 * DIV}</duration></backup>")
        out.append(f'<note default-x="30"><pitch><step>C</step><octave>3</octave></pitch><duration>{4 * DIV}</duration><type>whole</type><voice>5</voice><staff>2</staff></note>')
    return "".join(out)


def part(pid: str, name: str, bars: list[str], staves: int = 1, clef_sign: str = "G", clef_line: int = 2) -> tuple[str, str]:
    body = "".join(bar(i + 1, c, first=i == 0, new_system=(i == 2), staves=staves, clef_sign=clef_sign, clef_line=clef_line) for i, c in enumerate(bars))
    return f'<score-part id="{pid}"><part-name>{name}</part-name></score-part>', f'<part id="{pid}">{body}</part>'


def book(parts: list[tuple[str, str]]) -> stream.Score:
    xml = ('<?xml version="1.0" encoding="UTF-8"?><score-partwise version="3.1"><part-list>' + "".join(h for h, _ in parts)
           + "</part-list>" + "".join(b for _, b in parts) + "</score-partwise>")
    return converter.parse(xml.encode(), format="musicxml")


# Two systems of two bars (bars 1-2, 3-4). System 1: Fl., [unnamed oboe], Klavier (2 staves), Violine I.
# System 2: Viol. I II (Audiveris's second "Viol. I"), [unnamed, bass clef], Vc.; the piano again. The exporter's file
# order puts a new logical part next to the parts it was met with.
ROSTER = ["Flute I, II", "Oboe", "Piano", "Violin I", "Violin II", "Cello"]


def cut_away() -> stream.Score:
    a = absent()
    return book([
        part("P1", "Fl.", [notes("C", 5), rest_placed(), a, a]),
        part("P2", "Voice I", [rest_placed(), notes("D", 5), a, a]),
        part("P3", "Klavier", [notes("E", staves=2), notes("E", staves=2), notes("F", staves=2), notes("F", staves=2)], staves=2),
        part("P4", "Violine I", [notes("G"), notes("G"), a, a]),
        part("P5", "Viol. I II", [a, a, notes("A"), notes("A")]),
        part("P6", "Voice II", [a, a, notes("B", 3), rest_placed()], clef_sign="F", clef_line=4),
        part("P7", "Vc.", [a, a, rest_placed(), notes("C", 3)], clef_sign="F", clef_line=4),
    ])


def test_labels_are_read_through_the_ocr():
    assert normalise("0b. II")[0] == "ob ii" and normalise("f!!! II")[0] == "flll ii"
    assert normalise("K.—B")[0] == "k b" and normalise("(E5) II") == ("ii", ["es"]) and normalise("{c_ c)") == ("", ["c", "c"])
    assert identify("Viol. I II").family == "violin" and identify("Viol. I II").number == 1          # the last token is Audiveris's
    assert identify("Viol. n").number == 2 and identify("Viol. u").number == 2 and identify("Violine II").number == 2
    assert identify("Viola III").family == "viola" and identify("Vcll. u").family == "cello" and identify("KontrabaB").family == "double bass"
    assert identify("Fag. 1}").family == "bassoon" and identify("H6rner in Es I").family == "horn" and identify("Pauken in C.G").family == "timpani"
    assert identify("3 Tromboni").family == "trombone" and identify("2 Trombe (B)").family == "trumpet" and identify("e Tuba").family == "tuba"
    assert identify("(B) II I").family is None and identify("(B) II I").keys == ["b"]
    for junk in ("Voice 7", "x", "'11", "In) II", "View", "Archi", "rompeten m CH"):
        assert identify(junk).family is None, junk


def test_roster_entries_name_every_family_number_and_key():
    r = identify("Violoncello and Double Bass", roster_entry=True)
    assert {"cello", "double bass"} <= r.families
    assert identify("Clarinet in B-flat I, II", roster_entry=True).keys == ["b"] and identify("Flute I, II", roster_entry=True).numbers == [1, 2]
    assert identify("Horns (F)", roster_entry=True).keys == ["f"] and identify("Clarinets (Bb)", roster_entry=True).keys == ["b"]
    assert identify("Violins II", roster_entry=True).numbers == [2]
    roster = roster_of(["Flute I, II", "Clarinet in B-flat I, II", "Horn in E-flat I, II", "Violin I", "Violin II"], [])
    assert candidates(fragments_of(book([part("P1", "(B) II", [notes("C")])]))[0], roster) == [1]
    assert candidates(fragments_of(book([part("P1", "Viol. II I", [notes("C")])]))[0], roster) == [4]
    assert candidates(fragments_of(book([part("P1", "Viol.", [notes("C")])]))[0], roster) == [3, 4]
    assert candidates(fragments_of(book([part("P1", "Voice 3", [notes("C")])]))[0], roster) is None
    assert candidates(fragments_of(book([part("P1", "Harfe", [notes("C")])]))[0], roster) == []


def test_fragments_presence_and_systems():
    sc = cut_away()
    frags = fragments_of(sc)
    assert [f.label for f in frags] == ["Fl.", "Voice I", "Klavier", "Violine I", "Viol. I II", "Voice II", "Vc."]
    assert frags[0].present == {1, 2} and frags[4].present == {3, 4} and frags[6].present == {3, 4}
    assert len(frags[2].staves) == 2 and frags[2].present == {1, 2, 3, 4}
    assert frags[5].clef == "bass" and frags[0].clef == "treble"
    assert systems_of(sc, [1, 2, 3, 4]) == [[1, 2], [3, 4]]


def test_a_system_is_a_monotone_subsequence_of_the_roster():
    frags = fragments_of(cut_away())
    roster = roster_of(ROSTER, frags)
    first = [f for f in frags if f.present & {1, 2}]
    assert assign_system(first, roster) == [0, 1, 2, 3]            # the unnamed staff between Fl. and the piano is the oboe
    second = [f for f in frags if f.present & {3, 4}]
    assert assign_system(second, roster) == [2, 3, 4, 5]           # Voice II in bass clef between Violin I and Vc.: Violin II by position


def test_two_staves_share_a_slot_when_the_roster_is_shorter():
    sc = book([part("P1", "4 Corni (F)", [notes("C")]), part("P2", "Voice I", [notes("E")]), part("P3", "2 Trombe (B)", [notes("G")]),
               part("P4", "3 Tromboni", [notes("C", 3)], clef_sign="F", clef_line=4), part("P5", "e Tuba", [notes("C", 2)], clef_sign="F", clef_line=4)])
    frags = fragments_of(sc)
    roster = roster_of(["Horns (F)", "Trumpets (Bb)", "Trombones and Tuba"], frags)
    assert assign_system(frags, roster) == [0, 0, 1, 2, 2]


def test_merge_puts_the_fragments_on_the_instruments():
    sc = cut_away()
    out, report = merge_parts(sc, ROSTER)
    assert report["changed"] and report["after"] == ["Flute I, II", "Oboe", "Piano", "Violin I", "Violin II", "Cello"]
    assert report["slots"]["Violin I"] == ["Violine I", "Viol. I II"] and report["slots"]["Violin II"] == ["Voice II"]
    assert not report["unassigned"] and not report["dropped"] and not report["shared"]
    names = [n for n, _ in part_groups(out)]
    assert names == ["Flute I, II", "Oboe", "Piano", "Violin I", "Violin II", "Cello"]
    v1 = next(p for p in out.parts if p.partName == "Violin I")
    pitched = {m.number: [n.nameWithOctave for n in m.notes] for m in v1.getElementsByClass(stream.Measure)}
    assert pitched == {1: ["G4"], 2: ["G4"], 3: ["A4"], 4: ["A4"]}            # both fragments, in one part, every bar numbered
    cello = next(p for p in out.parts if p.partName == "Cello")
    assert [m.number for m in cello.getElementsByClass(stream.Measure)] == [1, 2, 3, 4]
    assert isinstance(cello.measure(1).clef, clef.BassClef) and cello.measure(1).timeSignature is not None   # the rest bars state the staff
    assert all(isinstance(e, stream.PartStaff) for e in out.parts if e.partName == "Piano")
    assert any(g.name == "Piano" for g in out.getElementsByClass(layout.StaffGroup))


def test_the_merged_file_round_trips_through_music21():
    out, _ = merge_parts(cut_away(), ROSTER)
    data = write_musicxml(out)                                   # as the convert writes it: makeNotation off
    back = converter.parse(data, format="musicxml")
    assert [n for n, _ in part_groups(back)] == ["Flute I, II", "Oboe", "Piano", "Violin I", "Violin II", "Cello"]
    assert len([m for p in back.parts for m in p.getElementsByClass(stream.Measure)]) == 7 * 4


def test_a_file_the_roster_already_fits_is_left_alone():
    sc = book([part("P1", "Violino I", [notes("C")]), part("P2", "Violoncello", [notes("C", 3)], clef_sign="F", clef_line=4)])
    same, report = merge_parts(sc, ["Violin I", "Cello"])
    assert same is sc and not report["changed"]
    same, report = merge_parts(sc, None)
    assert same is sc and not report["changed"]


def test_without_a_roster_the_fragments_name_the_instruments():
    out, report = merge_parts(cut_away(), None)
    assert report["after"] == ["Flute", "Piano", "Violin I", "Cello"] and report["slots"]["Violin I"] == ["Violine I", "Viol. I II"]
    # the unnamed staves took free slots or shared one; nothing that sounds was lost
    assert not report["unassigned"] and sum(1 for p in out.parts) >= 4


def test_a_fragment_no_slot_fits_keeps_its_own_part_and_a_silent_one_is_dropped():
    a = absent()
    sc = book([part("P1", "Fl.", [notes("C", 5), a]), part("P2", "Harfe", [a, notes("D")]), part("P3", "Voice I", [a, rest_placed()]),
               part("P4", "Klavier", [notes("E", staves=2), notes("E", staves=2)], staves=2), part("P5", "Violine I", [notes("G"), notes("G")])])
    out, report = merge_parts(sc, ["Flute", "Piano", "Violin I"], systems=[[1], [2]])
    assert report["unassigned"] == ["Harfe"] and report["after"] == ["Flute", "Piano", "Violin I", "Harfe"]
    assert "Voice I" in report["dropped"] or report["slots"].get("Flute") == ["Fl.", "Voice I"] or report["slots"].get("Piano") == ["Klavier", "Voice I"]
    assert any(p.partName == "Harfe" for p in out.parts)
