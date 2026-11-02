"""The one normaliser a seat and a part are matched on (CK 2026-11-02): printed names in Italian, German, French,
English, abbreviated, numbered by ordinal or plural, all to one English name."""
from __future__ import annotations

import pytest

from app.librarian.instruments import canonical_instrument, seat_reads, store_part_canonicals, store_seat_canonicals
from tests.test_part_cut import FakeDB

CASES = [
    # the brief's cases
    ("Violino II", "Violin II"), ("Vln. 2", "Violin II"), ("2. Violine", "Violin II"), ("Seconds", "Violin II"),
    ("Vc.", "Cello"), ("Kb.", "Double Bass"), ("Sopran", "Soprano"), ("Pianoforte", "Piano"),
    # the seats themselves are fixed points
    ("Violin I", "Violin I"), ("Violin II", "Violin II"), ("Viola", "Viola"), ("Cello", "Cello"), ("Double Bass", "Double Bass"),
    ("Flute", "Flute"), ("Oboe", "Oboe"), ("Clarinet", "Clarinet"), ("Bassoon", "Bassoon"), ("Horn", "Horn"), ("Trumpet", "Trumpet"),
    ("Trombone", "Trombone"), ("Timpani", "Timpani"), ("Piano", "Piano"), ("Soprano", "Soprano"), ("Alto", "Alto"), ("Tenor", "Tenor"),
    ("Bass", "Bass"),
    # numbers: Roman, Arabic, ordinals before and after, in four languages
    ("Vn 2", "Violin II"), ("Violin 2", "Violin II"), ("2nd Violins", "Violin II"), ("Second Violin", "Violin II"),
    ("Violino secondo", "Violin II"), ("1. Violine", "Violin I"), ("Violine I", "Violin I"), ("Violini I", "Violin I"), ("Vl. I", "Violin I"),
    ("Viol. II", "Violin II"), ("Firsts", "Violin I"), ("Corno I in F", "Horn I"), ("Horn 3", "Horn III"), ("Clarinetto in B 2", "Clarinet II"),
    ("Piano 2", "Piano II"),
    # abbreviations and other languages
    ("Vla.", "Viola"), ("Bratsche", "Viola"), ("Violas", "Viola"), ("Violoncello", "Cello"), ("Celli", "Cello"), ("Cb.", "Double Bass"),
    ("Contrabbasso", "Double Bass"), ("Kontrabaß", "Double Bass"), ("Double Basses", "Double Bass"), ("Pf.", "Piano"), ("Klav.", "Piano"),
    ("Klavier", "Piano"), ("Piano (solo)", "Piano"), ("Flöte", "Flute"), ("Hörner", "Horn"), ("Fagotti", "Bassoon"), ("Trombe in C", "Trumpet"),
    ("Tromboni", "Trombone"), ("Pauken", "Timpani"), ("Cor anglais", "English Horn"), ("Tenore", "Tenor"), ("Basso", "Bass"),
    ("Mezzo-soprano", "Mezzo-soprano"), ("Bass Clarinet", "Bass Clarinet"), ("Bass Trombone", "Bass Trombone"),
    ("Contrafagotto", "Contrabassoon"), ("S.", "Soprano"), ("T", "Tenor"),
    # counts are not numbers; shared staves name every player
    ("2 Flauti", "Flute"), ("Flauti a 2", "Flute"), ("Klavier zu 4 Händen", "Piano"), ("Violini", "Violin"),
    ("Flauti I. II.", "Flute I & Flute II"), ("Violoncello e Contrabasso", "Cello & Double Bass"),
    ("Violoncello and Double Bass", "Cello & Double Bass"),
    # what the tables do not know keeps its own words
    # names printed on the hosted test books (2026-11-02)
    ("Horn in B basso", "Horn"), ("Horn in E-flat I, II", "Horn I & Horn II"), ("Corni in Es I II", "Horn I & Horn II"),
    ("Clarinet in B-flat I, II", "Clarinet I & Clarinet II"), ("2 Clarinetti (B)", "Clarinet"), ("Timpani (G, As, C)", "Timpani"),
    ("Vcllo. e C-B", "Cello & Double Bass"), ("Violoni + Violoncello", "Double Bass & Cello"), ("Violini I + Violoncelli", "Violin I & Cello"),
    ("Klavier oben + Klavier unten", "Piano"), ("3 Tromboni e Tuba", "Trombone & Tuba"), ("Violins II", "Violin II"),
    ("Erhu", "Erhu"), ("Part 1", "Part 1"), ("  Theremin. ", "Theremin"), ("", ""),
]


@pytest.mark.parametrize("printed,canonical", CASES)
def test_printed_to_canonical(printed, canonical):
    assert canonical_instrument(printed) == canonical


def test_canonical_is_a_fixed_point():
    for _, c in CASES:
        assert canonical_instrument(c) == c


def test_a_seat_reads_its_part_or_a_shared_staff_naming_it():
    assert seat_reads("Violin II", canonical_instrument("Violino II"))
    assert seat_reads("Cello", canonical_instrument("Violoncello e Contrabasso"))
    assert seat_reads("Flute I", canonical_instrument("Flauti I. II."))
    assert not seat_reads("Violin I", canonical_instrument("Violino II"))
    assert not seat_reads("Viola", canonical_instrument("Violin"))
    assert not seat_reads("", "Violin II") and not seat_reads("Violin II", "")


def test_store_part_canonicals_writes_once_and_skips_a_database_without_the_column():
    db = FakeDB()
    db.rows["parts"] = [{"id": "p1", "score_id": "s", "name": "Violino II", "canonical": None},
                        {"id": "p2", "score_id": "s", "name": "Violoncello", "canonical": "Cello"}]
    assert store_part_canonicals(db, "s") == 1
    upserts = [op for op in db.ops if op[1] == "upsert"]
    assert upserts == [("parts", "upsert", [{"score_id": "s", "name": "Violino II", "canonical": "Violin II"}], {})]
    old = FakeDB()
    old.rows["parts"] = [{"id": "p1", "score_id": "s", "name": "Violino II"}]      # migration not applied
    assert store_part_canonicals(old, "s") is None and not [op for op in old.ops if op[1] != "select"]


def test_store_seat_canonicals():
    db = FakeDB()
    db.rows["members"] = [{"id": "m1", "ensemble_id": "e", "part": "2nd Violins", "part_canonical": None},
                          {"id": "m2", "ensemble_id": "e", "part": None, "part_canonical": None},
                          {"id": "m3", "ensemble_id": "e", "part": "Cello", "part_canonical": "Cello"}]
    assert store_seat_canonicals(db, "e") == 1
    assert db.rows["members"][0]["part_canonical"] == "Violin II"
    old = FakeDB()
    old.rows["members"] = [{"id": "m1", "ensemble_id": "e", "part": "Violin II"}]
    assert store_seat_canonicals(old, "e") is None
