"""The engine's staff fragments put back on the book's instruments (feature 005, the cut-away full score). No model.

Audiveris 5.11 links a system's physical parts to the book's "logical parts" by staff configuration first (staff
count, lines), then by the OCR'd label against the logical part's name or abbreviation, case only; a part that
matches nothing becomes a new logical part, and `-batch` has no editor to collate them. A full score drops the silent
instruments from a system (every orchestral page after the first), and its staff labels are abbreviations the OCR
reads differently each time ("Viol. I", "Viol.I", "Viol. n"), the transposition line of a two-line label ("(B)",
"(Es)") or nothing at all ("Voice 7"), so the export holds one part per fragment: Beethoven PC3 pp. 1-4 came back as
60 parts for 12 instruments and Rachmaninoff 2 pp. 1-4 as 29 for 14 (E2E night 2026-10-31; CK saw "about 40 voices"
on the iPad). Every fragment carries every bar of the book: where its staff is absent from a system the exporter
writes a whole-bar rest with no position.

`merge_parts` puts the fragments back on the instruments:
  1. systems: the bars between the export's system breaks (`<print new-system>`, in every part), or `systems` as
     `omr_book` lists them (`doc["systems"][i]["numbers"]`);
  2. presence: a fragment is on a system when one of its bars there holds a note, or a rest the engine placed
     (`style.absoluteX`, MusicXML `default-x`); a stand-in rest has none;
  3. the roster: the book's instruments in score order as the page reading read them from the header (the `parts`
     rows, position < 1000), each with a family (flute, violin, ...), numbers (Violin I / II) and transposition keys
     ("in B-flat", "(Es)"); without a roster, the families the fragments themselves name, in file order;
  4. per system, the present fragments top to bottom (the exporter lists a new logical part above or below the parts
     it was met with, so the file order is the vertical order) are matched to the roster monotonically: a cut-away
     system is a subsequence of the roster. A named fragment takes a slot of its family (and number or key when one
     was read), an unnamed one any slot between its neighbours; the clef the fragment carries (the exporter writes the
     logical part's own clef at its bar 1, present or not) breaks ties; two staves may share one slot (four horns on
     two staves, "3 Tromboni" over "e Tuba") at a cost. A fragment keeps the slot of the system where it has most bars;
  5. the merged score: one part per roster slot in use (a Part, or PartStaffs when the slot holds two staves anywhere),
     every bar: the fragment's own measures moved in, a whole-bar rest where the instrument is absent, the clef
     restated where the source changes. A fragment no slot fits keeps its own part; one that never sounds is dropped.

Measure numbers, layouts and spanners are kept, so the bar map, the flags, the playback and the engraving read the
merged file as before. A file with no more app parts than the roster has is returned unchanged (a chamber book the
engine read in one piece, a sonata). Audiveris's own disambiguating suffix ("Viola I".."Viola IV" for four fragments
labelled "Viola") is the last of two number tokens and is ignored.
"""
from __future__ import annotations

import copy
import re
import unicodedata
from dataclasses import dataclass, field
from typing import Any

from music21 import clef as m21clef, key as m21key, layout, meter, note, stream

from .omr_score import _rest_bar, staff_groups

# (family, regex on the normalised label); the first hit names the fragment, so the order matters: "violoncello" and
# "viola" before "viol", "bassoon" before "bass", "tromboni" before "trombe".
FAMILIES: list[tuple[str, str]] = [
    ("piccolo", r"\bpicc"),
    ("flute", r"\bfl+\b|\bfl[aou]|\bflute|\bflot"),
    ("english horn", r"\bengl|\bcor angl|\bcorno ingl"),
    ("oboe", r"\bob\b|\bobo|\bhob|\bhautb"),
    ("clarinet", r"\bcl\b|\bclar|\bkl\b|\bklar"),
    ("bassoon", r"\bfag|\bfg\b|\bbasso{1,2}n|\bbsn"),
    ("horn", r"\bhr\b|\bhn\b|\bhorn|\bcor\b|\bcorn[io]|\bcors\b"),
    ("trombone", r"\btrombon|\btrb|\btbn|\bpos\b|\bposaun"),
    ("trumpet", r"\btr\b|\btrp|\btpt|\btromb[ae]|\btromp|\btrumpet|\bclarin[io]"),
    ("tuba", r"\btuba|\btb\b"),
    ("timpani", r"\btimp|\btymp|\bpauk|\bpk\b"),
    ("harp", r"\bharp|\barpa|\bharfe"),
    ("organ", r"\borg"),
    ("piano", r"\bpiano|\bpf\b|\bpfte|\bklav|\bcemb"),
    ("soprano", r"\bsopr|\bs\b"),
    ("alto", r"\balt\b|\balto\b|\balti\b|\ba\b"),
    ("tenor", r"\bten\b|\btenor|\bt\b"),
    ("cello", r"\bvioloncel|\bvcl?l?\b|\bvlc\b|\bcell"),
    ("viola", r"\bviola|\bviole\b|\bvla\b|\bvle\b|\bbr\b|\bbratsch"),
    ("violin", r"\bviol|\bvl\b|\bvln|\bvn\b|\bgeige"),
    ("double bass", r"\bkontrab|\bcontrab|\bdouble|\bkb\b|\bcb\b|\bdb\b|\bk b\b"),
    ("bass", r"\bbass\b|\bbassi\b|\bbasso\b|\bbasses\b|\bb\b"),
]
COMPAT = {("bass", "double bass"), ("double bass", "bass")}     # a choir's "Bass" and the orchestra's basses
CANON = {"double bass": "Double bass", "english horn": "English horn"}
CLEF_GROUP = {"treble": {"piccolo", "flute", "english horn", "oboe", "clarinet", "horn", "trumpet", "violin", "soprano", "alto", "tenor"},
              "alto": {"viola"},
              "bass": {"bassoon", "trombone", "tuba", "timpani", "cello", "double bass", "bass"}}
KEYS = {"b": "b", "bb": "b", "bflat": "b", "b-flat": "b", "es": "es", "eb": "es", "eflat": "es", "e-flat": "es",
        "as": "as", "ab": "as", "aflat": "as", "a-flat": "as", "des": "des", "dflat": "des", "d-flat": "des",
        "f": "f", "c": "c", "d": "d", "e": "e", "g": "g", "a": "a", "h": "h", "fis": "fis", "cis": "cis"}
ROMAN = {"i": 1, "ii": 2, "iii": 3, "iv": 4, "v": 5, "vi": 6}
STROKE1 = set("il1!|[]})'ı")
STROKE2 = set("unh")
UNNAMED = re.compile(r"^voice\b|^staff\b|^part\b|^archi\b|^tutti\b|^strings\b|^p\d+$")
OCR = str.maketrans({"0": "o", "1": "l", "!": "l", "|": "l", "5": "s", "6": "o", "8": "b", "]": "l", "[": "l", "}": "l", "{": "("})
SCORE_NAMED, SCORE_UNNAMED, SCORE_CLEF, COST_SHARE, COST_UNASSIGNED = 3, 1, 1, 2, 3


# ---------------------------------------------------------------------------------------------------- labels

def normalise(label: str) -> tuple[str, list[str]]:
    """A label as the OCR left it -> (the words, the parenthesised key tokens). Accents are folded, confusables
    inside a word read as letters ("0b." -> "ob", "f!!!" -> "flll", "(E5)" -> "(es)", "K.-B" -> "k b")."""
    s = unicodedata.normalize("NFKD", label or "")
    s = "".join(c for c in s if not unicodedata.combining(c)).replace("ß", "ss").lower()
    s = s.replace("—", "-").replace("–", "-").replace("{", "(")
    keys: list[str] = []
    s = re.sub(r"\(([^()]*)\)", lambda m: keys.append(m.group(1)) or " ", s)
    m = re.search(r"\(([^()]*)$", s)             # an unclosed "(C'" at the end of a line
    if m:
        keys.append(m.group(1))
        s = s[: m.start()]
    words = []
    for tok in re.split(r"[\s.,:;/]+", s):
        if not tok:
            continue
        if any(c.isalpha() for c in tok):
            tok = tok.translate(OCR)
        tok = tok.strip("-_'\"`*#+()")
        if tok:
            words.append(tok)
    key_tokens = []
    for k in keys:
        for tok in re.split(r"[\s.,;/_]+", k.translate(OCR)):
            tok = tok.strip("-'\"`")
            if tok in KEYS:
                key_tokens.append(KEYS[tok])
    return " ".join(words), key_tokens


def _number(tok: str) -> int | None:
    """A number token: "ii", "2", "1!" (strokes), "u"/"n"/"h" (two strokes); else None."""
    if tok.isdigit():
        return int(tok)
    if tok in ROMAN:
        return ROMAN[tok]
    if tok and all(c in STROKE1 or c in STROKE2 for c in tok):
        return sum(2 if c in STROKE2 else 1 for c in tok)
    return None


@dataclass
class Identity:
    family: str | None = None
    numbers: list[int] = field(default_factory=list)     # as printed; a fragment's second token is Audiveris's own
    keys: list[str] = field(default_factory=list)
    families: set[str] = field(default_factory=set)      # a roster entry may name two ("Violoncello and Double Bass")

    @property
    def number(self) -> int | None:
        return self.numbers[0] if self.numbers else None


def identify(label: str, roster_entry: bool = False) -> Identity:
    """What a label names. A fragment takes its first family hit and the numbers after it; a roster entry takes every
    family it names and every number anywhere ("Flute I, II", "Trombones and Tuba"). "Voice 7" and friends are unnamed."""
    text, keys = normalise(label)
    ident = Identity(keys=keys)
    if not text or (UNNAMED.match(text) and not roster_entry):
        return ident
    for m in re.finditer(r"\bin\s+([a-h](?:-?flat|-?sharp|b|s|is)?)\b", text):
        if m.group(1) in KEYS:
            ident.keys.append(KEYS[m.group(1)])
    hits = []
    for order, (fam, rx) in enumerate(FAMILIES):
        m = re.search(rx, text)
        # A lone letter ("S", "A", "B") names a choir line only beside other words, never as a whole OCR'd label.
        if m and (roster_entry or len(text.split()) > 1 or len(m.group(0)) > 1):
            hits.append((m.start(), order, fam))
    hits.sort()
    if not hits:
        return ident
    ident.family = hits[0][2]
    ident.families = {f for _, _, f in hits} if roster_entry else {hits[0][2]}
    if roster_entry:
        ident.numbers = [n for n in (_number(t) for t in text.split()) if n]
    else:
        after = text[hits[0][0]:].split()[1:]
        for tok in after:
            n = _number(tok)
            if n is None:
                break
            ident.numbers.append(n)
    return ident


def compatible(fragment: Identity, slot: Identity) -> bool:
    if fragment.family is None:
        return False
    return any(f == fragment.family or (fragment.family, f) in COMPAT for f in slot.families)


def _clef_group(c: m21clef.Clef | None) -> str | None:
    if c is None or not getattr(c, "sign", None):
        return None
    if c.sign == "G":
        return "treble"
    if c.sign == "F":
        return "bass"
    if c.sign == "C":
        return "bass" if (c.line or 3) >= 4 else "alto"
    return None


# ---------------------------------------------------------------------------------------------------- fragments

@dataclass
class Fragment:
    index: int                      # file order (vertical order among the parts met together)
    label: str
    staves: list[stream.Part]       # one, or the two PartStaffs of a grand staff
    ident: Identity
    measures: list[dict[int, stream.Measure]]
    present: set[int] = field(default_factory=set)      # bar numbers where a staff of it holds engine-placed music
    sounds: bool = False
    clef: str | None = None
    slot: int | None = None


def _present(m: stream.Measure) -> bool:
    for el in m.recurse().notesAndRests:
        if not isinstance(el, note.Rest) or el.style.absoluteX is not None:
            return True
    return False


def fragments_of(sc: stream.Score) -> list[Fragment]:
    parts = list(sc.parts)
    groups = staff_groups(sc)
    out: list[Fragment] = []
    for g in sorted(set(groups)):
        staves = [p for p, gi in zip(parts, groups) if gi == g]
        ms = [{m.number: m for m in p.getElementsByClass(stream.Measure)} for p in staves]
        label = next((p.partName for p in staves if p.partName), "") or ""
        f = Fragment(len(out), label, staves, identify(label), ms)
        for mm in ms:
            for n, m in mm.items():
                if _present(m):
                    f.present.add(n)
                    if any(not isinstance(el, note.Rest) for el in m.recurse().notesAndRests):
                        f.sounds = True
        first = min(f.present) if f.present else None
        m0 = ms[0].get(first) if first is not None else None
        c = (m0.clef or m0.getContextByClass(m21clef.Clef)) if m0 is not None else None
        if c is None and ms[0]:
            c = next(iter(ms[0][min(ms[0])].getElementsByClass(m21clef.Clef)), None)
        f.clef = _clef_group(c)
        out.append(f)
    return out


def systems_of(sc: stream.Score, numbers: list[int]) -> list[list[int]]:
    """Bar numbers per system, from the layout marks any part carries (the first bar starts the first system)."""
    starts = {numbers[0]} if numbers else set()
    for p in sc.parts:
        for m in p.getElementsByClass(stream.Measure):
            if any(getattr(e, "isNew", False) for e in m.getElementsByClass((layout.SystemLayout, layout.PageLayout))):
                starts.add(m.number)
    out: list[list[int]] = []
    for n in numbers:
        if n in starts or not out:
            out.append([])
        out[-1].append(n)
    return out


# ---------------------------------------------------------------------------------------------------- the roster

def roster_of(names: list[str] | None, fragments: list[Fragment]) -> list[tuple[str, Identity]]:
    """The slots: the book's instruments as given, else the families the fragments name, in file order."""
    if names:
        return [(n, identify(n, roster_entry=True)) for n in names]
    out: list[tuple[str, Identity]] = []
    seen: set[tuple[str, int | None]] = set()
    for f in fragments:
        fam = f.ident.family
        if fam is None or (fam, f.ident.number) in seen:
            continue
        seen.add((fam, f.ident.number))
        name = CANON.get(fam, fam.capitalize())
        if f.ident.number:
            name += " " + "I" * f.ident.number if f.ident.number <= 3 else f" {f.ident.number}"
        out.append((name, Identity(family=fam, numbers=[f.ident.number] if f.ident.number else [], families={fam})))
    return out


def candidates(f: Fragment, roster: list[tuple[str, Identity]]) -> list[int] | None:
    """The slots a fragment may take: its family's (and number's, when a slot has it), else its key's, else any (None).
    A named fragment the roster lacks gets none."""
    ident = f.ident
    if ident.family is not None:
        fam = [i for i, (_, r) in enumerate(roster) if compatible(ident, r)]
        if ident.number is not None:
            numbered = [i for i in fam if ident.number in roster[i][1].numbers]
            if numbered:
                return numbered
        return fam
    if ident.keys:
        hit = [i for i, (_, r) in enumerate(roster) if set(ident.keys) & set(r.keys)]
        if hit:
            return hit
    return None


def assign_system(units: list[Fragment], roster: list[tuple[str, Identity]]) -> list[int | None]:
    """The slots of one system's fragments, top to bottom, non-decreasing (a shared slot costs), the best-scoring
    assignment by dynamic programming; a fragment no slot fits is left out (None)."""
    m = len(roster)
    cands = [candidates(u, roster) for u in units]

    def score(u: Fragment, c: list[int] | None, k: int) -> float | None:
        if c is None:
            base = SCORE_UNNAMED
        elif k in c:
            base = SCORE_NAMED
        else:
            return None
        fams = roster[k][1].families
        groups = {g for g, fs in CLEF_GROUP.items() if fs & fams}
        if u.clef and groups:
            base += SCORE_CLEF if u.clef in groups else -SCORE_CLEF
        return base

    NEG = float("-inf")
    # dp[j]: best score with the last assigned slot j - 1 (j = 0: none yet); back[i][j] = (prev j, slot or None)
    dp = [0.0] + [NEG] * m
    back: list[list[tuple[int, int | None] | None]] = []
    for i, u in enumerate(units):
        nxt = [NEG] * (m + 1)
        bk: list[tuple[int, int | None] | None] = [None] * (m + 1)
        for j in range(m + 1):
            if dp[j] == NEG:
                continue
            if dp[j] - COST_UNASSIGNED > nxt[j]:
                nxt[j], bk[j] = dp[j] - COST_UNASSIGNED, (j, None)
            for k in range(max(j - 1, 0), m):
                s = score(u, cands[i], k)
                if s is None:
                    continue
                v = dp[j] + s - (COST_SHARE if k == j - 1 else 0)
                if v > nxt[k + 1]:
                    nxt[k + 1], bk[k + 1] = v, (j, k)
        dp, back = nxt, back + [bk]
    j = max(range(m + 1), key=lambda x: dp[x])
    out: list[int | None] = [None] * len(units)
    for i in range(len(units) - 1, -1, -1):
        prev, k = back[i][j]
        out[i] = k
        j = prev
    return out


# ---------------------------------------------------------------------------------------------------- the merge

def merge_parts(sc: stream.Score, roster_names: list[str] | None = None, systems: list[list[int]] | None = None) -> tuple[stream.Score, dict[str, Any]]:
    """The score with its fragments merged on the instruments, and a report:
    `{changed, before, after, systems, slots: {name: [labels]}, unassigned, dropped, shared}`."""
    frags = fragments_of(sc)
    before = [f.label for f in frags]
    numbers = sorted({n for f in frags for mm in f.measures for n in mm})
    report: dict[str, Any] = {"changed": False, "before": before, "after": before, "systems": 0, "slots": {}, "unassigned": [], "dropped": [], "shared": []}
    if not frags or not numbers:
        return sc, report
    if roster_names and len(frags) <= len(roster_names):
        return sc, report
    if not roster_names and len(frags) <= 2:
        return sc, report
    roster = roster_of(roster_names, frags)
    if not roster:
        return sc, report
    sys_bars = [list(s) for s in systems if s] if systems else systems_of(sc, numbers)
    covered = {n for s in sys_bars for n in s}
    if covered != set(numbers):                 # a system list that does not cover the file: back to the layout marks
        sys_bars = systems_of(sc, numbers)
    report["systems"] = len(sys_bars)

    votes: dict[int, dict[int, int]] = {}
    for bars in sys_bars:
        units = [f for f in frags if f.present & set(bars)]
        for f, k in zip(units, assign_system(units, roster)):
            if k is not None:
                votes.setdefault(f.index, {})[k] = votes.get(f.index, {}).get(k, 0) + len(f.present & set(bars))
    for f in frags:
        v = votes.get(f.index)
        f.slot = max(v, key=lambda k: (v[k], -k)) if v else None

    system_of = {n: i for i, bars in enumerate(sys_bars) for n in bars}
    out = stream.Score()
    if sc.metadata is not None:
        out.metadata = sc.metadata
    measures_of = {id(p): f.measures[j] for f in frags for j, p in enumerate(f.staves)}   # by staff, as read once
    placed: dict[int, stream.Part] = {}            # a fragment staff -> the merged staff its first bar went to
    ref = frags[0].staves[0]
    slots_used = sorted({f.slot for f in frags if f.slot is not None})
    for k in slots_used:
        name = roster[k][0]
        members = [f for f in frags if f.slot == k]
        report["slots"][name] = [f.label for f in members]
        # per system, the staves (music21 parts) the slot shows there, top to bottom
        per_system: list[list[stream.Part]] = []
        for bars in sys_bars:
            here = [f for f in members if f.present & set(bars)]
            per_system.append([p for f in here for p in f.staves])
            if len(here) > 1:
                report["shared"].append({"part": name, "bars": [bars[0], bars[-1]], "labels": [f.label for f in here]})
        width = max([len(s) for s in per_system] + [max(len(f.staves) for f in members)])
        new = [stream.PartStaff(id=f"M{k + 1}-Staff{j + 1}") if width > 1 else stream.Part(id=f"M{k + 1}") for j in range(width)]
        for p in new:
            p.partName = name
        current_clef: list[str | None] = [None] * width
        for n in numbers:
            srcs = per_system[system_of[n]] if n in system_of else []
            for j, target in enumerate(new):
                src = srcs[j] if j < len(srcs) else None
                m = measures_of[id(src)].get(n) if src is not None else None
                if m is None:
                    m = _rest_bar(target, src if src is not None else ref)
                    m.number = n
                else:
                    c = m.clef or m.getContextByClass(m21clef.Clef)
                    sig = _clef_sig(c)
                    if sig and current_clef[j] not in (None, sig) and m.clef is None:
                        m.insert(0, copy.deepcopy(c))
                    if sig:
                        current_clef[j] = sig
                    placed.setdefault(id(src), target)
                if not target.getElementsByClass(stream.Measure):
                    _first_bar_attributes(m, members, j, measures_of[id(ref)], numbers[0])
                    if m.clef is not None:
                        current_clef[j] = _clef_sig(m.clef)
                target.append(m)
        for f in members:
            for p in f.staves:
                home = placed.get(id(p), new[0])
                for sp in p.spanners:
                    home.insert(0, sp)
        for p in new:
            out.insert(0, p)
        if width > 1:
            out.insert(0, layout.StaffGroup(new, name=name, symbol="brace", barTogether=True))
    for f in frags:
        if f.slot is not None:
            continue
        if not f.sounds:
            report["dropped"].append(f.label)
            continue
        report["unassigned"].append(f.label)
        for p in f.staves:
            out.insert(0, p)
        if len(f.staves) > 1:
            out.insert(0, layout.StaffGroup(f.staves, name=f.label, symbol="brace", barTogether=True))
    report["changed"] = True
    report["after"] = [roster[k][0] for k in slots_used] + report["unassigned"]
    return out, report


def _clef_sig(c: m21clef.Clef | None) -> str | None:
    return f"{c.sign}{c.line}{c.octaveChange or 0}" if c is not None and getattr(c, "sign", None) else None


def _first_bar_attributes(m: stream.Measure, members: list[Fragment], j: int, ref: dict[int, stream.Measure], first: int) -> None:
    """A merged staff's first bar states a clef, key and time: the fragment's own clef (the exporter writes it at the
    logical part's bar 1), the book's key and time from the first part's first bar."""
    if m.clef is None:
        c = None
        for f in members:
            if j < len(f.staves):
                m0 = f.measures[j].get(min(f.measures[j])) if f.measures[j] else None
                c = next(iter(m0.getElementsByClass(m21clef.Clef)), None) if m0 is not None else None
                if c is not None:
                    break
        if c is not None:
            m.insert(0, copy.deepcopy(c))
    m0 = ref.get(first)
    if m0 is not None:
        if m.keySignature is None:
            ks = m0.keySignature or m0.getContextByClass(m21key.KeySignature)
            if ks is not None:
                m.insert(0, copy.deepcopy(ks))
        if m.timeSignature is None:
            ts = m0.timeSignature or m0.getContextByClass(meter.TimeSignature)
            if ts is not None:
                m.insert(0, copy.deepcopy(ts))
