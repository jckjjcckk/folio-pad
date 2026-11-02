"""One canonical English name per instrument (CK 2026-11-02, E2E night item 1): the name a seat and a part are matched on.

A group's seats say "Violin II", "Cello"; a book's parts carry what the edition prints ("Violino II", "Vn 2",
"2nd Violins", "Violoncello e Contrabasso"). Both sides go through `canonical_instrument` when they are written (the
import and the part cut for `parts.canonical`, the seat for `members.part_canonical`), the printed label stays the
part's name on screen, and the stand and the marks' policy match on the canonical names. Nothing here runs during
practice. English is assumed for the canonical side.

The rules, in order:
- Words: lower case, accents and umlauts folded ("Flöte" = "floete" = "flote", "Baß" = "bass"), punctuation is a
  space ("Vln.2" is "vln 2", "2. Violine" is "2 violine").
- Families: the header's synonym table (`header.SYNONYMS`: Italian, German, French, English and the editions'
  abbreviations) plus `EXTRA` here (contrabbasso, bass clarinet, bass trombone, contrabassoon, mezzo, baritone, ...),
  matched as the longest phrase first, left to right, so "Double Bass" is one instrument and "Bass Clarinet" is not a
  bass and a clarinet. A choir's one-letter label alone ("S.", "A", "T.", "B") is that voice.
- A transposing instrument's key is not part of its name: the words after "in" ("Horn in B basso", "Corni in Es") are
  skipped as far as they are a key, an accidental or "basso"/"alto".
- Numbers: Roman (I..VIII), Arabic (1..8), ordinals ("1st", "2nd", "first", "second", "erste", "zweite", "primo",
  "secondo", "premier", "seconde", ...) belong to the instrument after them when they come first ("2nd Violins",
  "2. Violine") and to the instrument before them otherwise ("Violino II", "Vln. 2"). "a 2" (both players) is not a
  number. A string section's nickname alone is the violins: "Firsts" is Violin I, "Seconds" is Violin II.
- Output: the family's English name ("Violin", "Cello", "Double Bass", "Piano"), plural made singular, with the number
  in Roman ("Violin II"). A shared staff names every player: "Flauti I. II." is "Flute I & Flute II", "Violoncello e
  Contrabasso" is "Cello & Double Bass"; a seat reads such a part when its own canonical name is one of them
  (`seat_reads`).
- A name the tables do not know keeps its own words, spaces collapsed and a trailing full stop dropped ("Erhu").
"""
from __future__ import annotations

import logging
import re
import unicodedata
from typing import Any

from . import header as hdr

log = logging.getLogger("folio.instruments")

# The family's name on the canonical side (header.SYNONYMS keys are lower case).
DISPLAY = {
    "double bass": "Double Bass", "english horn": "English Horn", "bass clarinet": "Bass Clarinet",
    "bass trombone": "Bass Trombone", "contrabassoon": "Contrabassoon", "mezzo": "Mezzo-soprano",
    "continuo": "Continuo", "bass drum": "Bass Drum", "snare drum": "Snare Drum",
}

# Names the header's matcher does not need (it reads one book's own labels) but a seat or a part can carry.
EXTRA = {
    "violin": ["violine", "violinen", "vni", "vns", "vlns"],
    "viola": ["violen", "vle"],
    "cello": ["violoncell", "violoncellos", "vcs", "vlc"],
    "double bass": ["violone", "violoni", "contrabbasso", "contrabbassi", "kontrabasse", "contrebasses", "string bass", "db", "d b", "cbs"],
    "piano": ["flugel", "fortepiano", "pianoforte", "klavier"],
    "oboe": ["hoboe", "hoboen"],
    "horn": ["french horn", "waldhorn", "cor", "corni", "hn", "hns"],
    "trumpet": ["trp", "tpts", "trompeta", "cornet", "cornets", "cornetto", "cornetti"],
    "bass clarinet": ["bass clarinet", "clarinetto basso", "clarinetto basso", "bassklarinette", "clarinette basse", "b cl", "bcl", "bass cl"],
    "bass trombone": ["bass trombone", "trombone basso", "bassposaune", "trombone basse", "b tbn", "btbn"],
    "contrabassoon": ["contrabassoon", "contrafagotto", "kontrafagott", "contrebasson", "cfg", "cbsn", "c fag"],
    "piccolo": ["ottavino"],
    "mezzo": ["mezzo", "mezzo soprano", "mezzosoprano", "mezzosopran", "ms"],
    "baritone": ["baritone", "bariton", "baritono", "bar"],
    "voice": ["voice", "voce", "singstimme", "gesang", "canto solo"],
    "continuo": ["continuo", "basso continuo", "b c", "bc", "cont"],
    "percussion": ["percussion", "percussione", "schlagzeug", "perc", "batterie"],
    "bass drum": ["bass drum", "gran cassa", "grosse trommel", "grosse caisse", "gr c"],
    "snare drum": ["snare drum", "tamburo militare", "kleine trommel", "caisse claire"],
    "guitar": ["guitar", "chitarra", "gitarre", "guitare", "gtr"],
    "harpsichord": ["harpsichord", "clavecin"],
    "saxophone": ["saxophone", "saxofono", "saxophon", "sax"],
    "recorder": ["recorder", "flauto dolce", "blockflote", "flute a bec"],
    "soprano": ["sopranos"],
    "tenor": ["tenors"],
}

# A one-letter choir label, the whole name and nothing else.
VOICE_LETTERS = {"s": "soprano", "a": "alto", "t": "tenor", "b": "bass"}

ROMAN_OUT = ["", "I", "II", "III", "IV", "V", "VI", "VII", "VIII"]
NUMBERS = {"i": 1, "ii": 2, "iii": 3, "iv": 4, "v": 5, "vi": 6, "vii": 7, "viii": 8,
           **{str(n): n for n in range(1, 9)}, "1st": 1, "2nd": 2, "3rd": 3, "4th": 4, "5th": 5, "6th": 6,
           "first": 1, "second": 2, "third": 3, "fourth": 4,
           "erste": 1, "erster": 1, "ersten": 1, "zweite": 2, "zweiter": 2, "zweiten": 2, "dritte": 3, "dritter": 3, "dritten": 3,
           "vierte": 4, "vierter": 4, "vierten": 4,
           "primo": 1, "prima": 1, "primi": 1, "prime": 1, "secondo": 2, "seconda": 2, "secondi": 2, "seconde": 2,
           "terzo": 3, "terza": 3, "terzi": 3, "quarto": 4,
           "premier": 1, "premiers": 1, "premiere": 1, "premieres": 1, "deuxieme": 2, "troisieme": 3}
NUMBERS.update({f"ord{n}": n for n in range(1, 9)})   # "2." before an instrument (`canonical_instrument` marks it)
# What follows "in" in a transposing instrument's name: the key, its accidental and register words.
KEY_WORDS = {*"abcdefgh", "es", "as", "is", "eb", "ab", "bb", "db", "gb", "flat", "sharp", "basso", "alto", "sib", "mib", "lab",
             "la", "re", "fa", "sol", "ut", "do", "mi", "si", "dur", "moll"}
HANDS = {"hands", "handen", "haende", "mains", "mani"}
# A string section's nickname, alone: the violins.
SECTIONS = {"firsts": ("violin", 1), "seconds": ("violin", 2)}


def fold(text: str) -> str:
    """Lower case, accents and umlauts folded (ö -> o, ß -> ss), every run of non-letters and non-digits one space."""
    t = unicodedata.normalize("NFKD", str(text or "").replace("ß", "ss").replace("ẞ", "ss"))
    t = "".join(ch for ch in t if not unicodedata.combining(ch)).lower()
    return " ".join(re.findall(r"[a-z0-9]+", t))


def _index() -> dict[tuple[str, ...], str]:
    out: dict[tuple[str, ...], str] = {}
    for fam, syns in [*hdr.SYNONYMS.items(), *EXTRA.items()]:
        for s in (fam, *syns):
            key = tuple(fold(s).split())
            if key:
                out.setdefault(key, fam)
    return out


PHRASES = _index()
LONGEST = max(len(k) for k in PHRASES)


def _singular(tok: str) -> str:
    if tok.endswith("sses"):
        return tok[:-2]
    if tok.endswith("s") and not tok.endswith("ss") and len(tok) > 3:
        return tok[:-1]
    return tok


def _family_at(toks: list[str], i: int) -> tuple[str, int] | None:
    """The family of the longest phrase starting at token i, and its length in tokens."""
    for n in range(min(LONGEST, len(toks) - i), 0, -1):
        words = tuple(toks[i:i + n])
        fam = PHRASES.get(words) or PHRASES.get(tuple(_singular(w) for w in words))
        if fam:
            return fam, n
    return None


def _name(fam: str, num: int | None) -> str:
    base = DISPLAY.get(fam) or fam.title()
    return f"{base} {ROMAN_OUT[num] if num and num < len(ROMAN_OUT) else num}" if num else base


def canonical_instrument(name: Any) -> str:
    """The one English name a seat and a part are matched on (rules in the module's docstring). '' for an empty name."""
    raw = re.sub(r"\s+", " ", str(name or "")).strip()
    # "2. Violine" is the second violin; "2 Flauti" (a header's count of players) is not: a number with a full stop is
    # an ordinal, a bare Arabic number before any instrument is a count and is dropped.
    toks = fold(re.sub(r"(?<![\d.])([1-8])\.(?!\d)", r" ord\1 ", raw)).split()
    if not toks:
        return ""
    if len(toks) == 1 and toks[0] in VOICE_LETTERS:
        return _name(VOICE_LETTERS[toks[0]], None)
    joined = " ".join(toks)
    if joined in SECTIONS:
        return _name(*SECTIONS[joined])

    # Walk the words: instruments (longest phrase first) and numbers, in the order printed.
    found: list[list[Any]] = []      # [family, [numbers]]
    pending: list[int] = []          # numbers printed before any instrument ("2nd Violins", "2. Violine")
    i = 0
    while i < len(toks):
        t = toks[i]
        if t == "in":                # "Horn in B basso", "Clarinetto in Es": the key, never an instrument or a number
            i += 1
            while i < len(toks) and toks[i] in KEY_WORDS:
                i += 1
            continue
        hit = _family_at(toks, i)
        if hit:
            fam, n = hit
            if found and found[-1][0] == fam and not found[-1][1] and not pending:
                pass                 # "Violino Violini" once only
            else:
                found.append([fam, pending])
            pending = []
            i += n
            continue
        if t in NUMBERS:
            nxt = toks[i + 1] if i + 1 < len(toks) else ""
            if (i > 0 and toks[i - 1] == "a") or (not found and t.isdigit()) or nxt in HANDS:
                i += 1               # "a 2": both players; "2 Flauti": two players; "zu 4 Händen": four hands
                continue
                continue
            if found and not pending:
                found[-1][1].append(NUMBERS[t])
            else:
                pending.append(NUMBERS[t])
            i += 1
            continue
        i += 1
    if not found:
        return raw.rstrip(".").strip()
    names: list[str] = []
    for fam, nums in found:
        nums = list(dict.fromkeys(nums))
        for x in (nums or [None]):
            nm = _name(fam, x)
            if nm not in names:
                names.append(nm)
    return " & ".join(names)


def seat_reads(seat_canonical: str, part_canonical: str) -> bool:
    """A seat reads a part when their canonical names are the same, or the part is a shared staff that names the seat
    ("Cello" reads "Cello & Double Bass", "Flute I" reads "Flute I & Flute II")."""
    if not seat_canonical or not part_canonical:
        return False
    return seat_canonical == part_canonical or seat_canonical in part_canonical.split(" & ")


# ---------------------------------------------------------------- storing them

def store_part_canonicals(db, score_id: str) -> int | None:
    """Write `parts.canonical` for every part of the score whose canonical name is missing or stale. Returns how many
    rows changed, or None when the database has no `canonical` column yet (migration 20261102130000 not applied): the
    import and the cut never fail for it, and the stand then matches by the printed name as before."""
    try:
        rows = db.table("parts").select("*").eq("score_id", score_id).execute().data or []
    except Exception as e:  # noqa: BLE001
        log.warning("parts of %s not read for canonical names: %s", score_id, e)
        return None
    if rows and "canonical" not in rows[0]:
        log.info("parts.canonical is not in this database (migration 20261102130000); canonical names not stored")
        return None
    todo = [{"score_id": score_id, "name": r["name"], "canonical": canonical_instrument(r["name"])} for r in rows
            if r.get("name") and r.get("canonical") != canonical_instrument(r["name"])]
    if todo:
        try:
            db.table("parts").upsert(todo, on_conflict="score_id,name").execute()
        except Exception as e:  # noqa: BLE001
            log.warning("canonical names of %s not stored: %s", score_id, e)
            return None
    return len(todo)


def store_seat_canonicals(db, ensemble_id: str | None = None) -> int | None:
    """Write `members.part_canonical` for every seat (of one group, or all) whose canonical name is missing or stale.
    None when the column is not in the database yet (see `store_part_canonicals`)."""
    q = db.table("members").select("*")
    if ensemble_id:
        q = q.eq("ensemble_id", ensemble_id)
    try:
        rows = q.execute().data or []
    except Exception as e:  # noqa: BLE001
        log.warning("seats not read for canonical names: %s", e)
        return None
    if rows and "part_canonical" not in rows[0]:
        log.info("members.part_canonical is not in this database (migration 20261102130000); seats not normalised")
        return None
    n = 0
    for r in rows:
        want = canonical_instrument(r["part"]) if r.get("part") else None
        if r.get("part_canonical") != want:
            db.table("members").update({"part_canonical": want}).eq("id", r["id"]).execute()
            n += 1
    return n
