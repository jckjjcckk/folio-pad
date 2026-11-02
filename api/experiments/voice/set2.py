"""Set 2 (CK, 2026-11-02): a harder, fair test of three ways to turn rehearsal speech into marks, with shipped errors
as the headline. Read `results/set2_2026-11-02.md` for the write-up.

    P1   push-to-talk, production chain: one clip per line -> Voice Transcribe (batch, DIARIZATION, the app's keywords)
         -> muse-spark-1.3 on the text (v4f, `voice_prompt.build_prompt`, chat, effort minimal, streamed)
         -> `checked_marks` (the app's check, imported: it needs no DB).
    P2   always-on: the whole file streamed at real-time pace to Voice Transcribe realtime (ENDPOINTING, the app's
         keywords), each `speechComplete` turn -> Spark 1.3 text (same prompt) -> `checked_marks`. Two readings of
         the turns: "alone" (each turn on its own) and "group" (013-always-on's rolling group: a turn within 1 s of the
         last joins its group, at most 3 turns, the group re-read at each turn, a mark owned by the turn its quote
         sits in). Spark is called the moment the turn completes, so end of speech -> proposal is measured live.
    P3a  muse-spark-1.2 on the push-to-talk clip as `input_audio` (audio_vs_asr's request and audio prompt).
    P3b  muse-spark-1.3, the same request. No transcript: no verbatim check, every proposal ships.

Conditions: set 2 (27 lines from the messy set, `fixtures/voice/script2.csv`) recorded quiet (h-quiet.wav) and with
music in the room (h-music.wav); the old 40 clips augmented (far, music, noise; see `augment`). P2 runs on set 2 only.

    cd api && uv run python -m experiments.voice.set2 align          # VAD + one batch ASR per long file (alignment only)
    cd api && uv run python -m experiments.voice.set2 clips          # writes fixtures/voice/audio2/clips/ + clips.json
    cd api && uv run python -m experiments.voice.set2 augment        # writes fixtures/voice/audio/aug/{far,music,noise}/
    cd api && uv run python -m experiments.voice.set2 overlap        # the worked-example overlap list
    cd api && uv run python -m experiments.voice.set2 run --run r1 [--cells ...]
    cd api && uv run python -m experiments.voice.set2 stream --run r1
    cd api && uv run python -m experiments.voice.set2 score          # no calls: results/set2_<run>.json + set2_tables.md
    cd api && uv run python -m experiments.voice.set2 report         # no calls: the tables again

Every paid call goes to spend.jsonl with a kind starting "s2:"; this experiment stops at $12 of its own spend.
Raw replies go to out/set2/ (ignored); scores to results/set2_<run>.json; tables to results/set2_tables.md.
The clean condition is audio_vs_asr's r1/r2 calls on the unaltered 40, rescored here at no cost.
"""

from __future__ import annotations

import argparse
import asyncio
import base64
import csv
import difflib
import io
import json
import random
import re
import statistics as st
import sys
import time
import wave
from pathlib import Path

import numpy as np

from app.librarian.transcribe_voice import ASR_MODEL, meta_transcribe, pcm_wav
from app.librarian.voice_prompt import EXAMPLES, checked_marks, parse_answer
from app.settings import settings

from . import audio_vs_asr as AVA
from . import voice_eval as VE
from ..voice_text import run as TR          # the text sets' field matcher (`fields`, `match`)
from ..voice_text.messy import run as MR    # patches TR.fields for the messy set's ANY fields
from ..voice_text.messy.cases import CASES as MESSY

HERE = Path(__file__).resolve().parent
API = HERE.parent.parent
A2 = API / "fixtures" / "voice" / "audio2"
CLIPS = A2 / "clips"
AUG = VE.AUDIO / "aug"
OUT = HERE / "out" / "set2"
RESULTS = HERE / "results"
SR = 16000
CAP_USD = 12.0
LIST = AVA.LIST
ASR_USD_PER_HOUR = 0.18
AUDIO_TOK_PER_S = 12.5
GATE = 0.9
MODELS = {"P1": "muse-spark-1.3", "P2": "muse-spark-1.3", "P3a": "muse-spark-1.2", "P3b": "muse-spark-1.3"}
FACTS = AVA.FACTS
CLIPPED = {"v11", "v16", "v28"}             # the recording clips the words the key depends on (audio_vs_asr r1/r2)
KEY_FIX = {"v04c": {"audience": "part:Soprano"}}   # the take ends "No, sorry, I mean sopranos"


# ---------- ledger ----------

def my_spent() -> float:
    if not VE.LEDGER.exists():
        return 0.0
    return sum(r["usd"] for r in map(json.loads, filter(str.strip, VE.LEDGER.read_text().splitlines()))
               if str(r.get("kind", "")).startswith("s2:"))


def guard(next_usd: float) -> None:
    if my_spent() + next_usd > CAP_USD:
        sys.exit(f"STOP: set 2 spend {my_spent():.4f} + {next_usd:.4f} would pass ${CAP_USD}")
    VE.guard(next_usd)


def list_usd(tin: int, tout: int) -> float:
    return (tin * LIST["in"] + tout * LIST["out"]) / 1e6


# ---------- audio io ----------

def read_wav(p: Path) -> np.ndarray:
    with wave.open(str(p)) as w:
        assert w.getnchannels() == 1 and w.getsampwidth() == 2 and w.getframerate() == SR, p
        return np.frombuffer(w.readframes(w.getnframes()), np.int16).copy()


def wav_bytes(x: np.ndarray) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(np.clip(np.round(x), -32768, 32767).astype(np.int16).tobytes())
    return buf.getvalue()


def write_wav(p: Path, x: np.ndarray) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(wav_bytes(x))


def frame_db(x: np.ndarray, fr: int = 320) -> np.ndarray:
    """dBFS per 20 ms frame."""
    f = x[: len(x) // fr * fr].astype(np.float64).reshape(-1, fr)
    return 20 * np.log10(np.sqrt((f ** 2).mean(axis=1)) + 1e-9) - 20 * np.log10(32768)


def vad(x: np.ndarray, on: float = -45.0, off: float = -55.0, min_sil: float = 1.5, min_sp: float = 0.3) -> list[tuple[float, float]]:
    """Energy VAD with hysteresis on 20 ms frames: speech starts at `on` dBFS, ends after `min_sil` s under `off`."""
    db = frame_db(x)
    out, start, last = [], None, None
    for i, v in enumerate(db):
        t = i * 0.02
        if start is None:
            if v >= on:
                start = last = t
        else:
            if v >= off:
                last = t
            elif t - last >= min_sil:
                if last + 0.02 - start >= min_sp:
                    out.append((round(start, 2), round(last + 0.02, 2)))
                start = None
    if start is not None:
        out.append((round(start, 2), round(len(db) * 0.02, 2)))
    return out


# ---------- labels ----------

def script2() -> list[dict]:
    with (API / "fixtures" / "voice" / "script2.csv").open() as f:
        return list(csv.DictReader(f))


CASE = {c["id"]: c for c in MESSY}
H2CASE = {r["id"]: r["case"] for r in script2()}


def norm_words(s: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", s.lower())


def sim(a: str, b: str) -> float:
    return difflib.SequenceMatcher(None, norm_words(a), norm_words(b)).ratio()


# ---------- Voice Transcribe (batch) ----------

async def asr_batch(kind: str, uid: str, x: np.ndarray, cache: Path) -> dict:
    """The production call (`meta_transcribe`: DIARIZATION, the app's keywords), cached per file."""
    if cache.exists():
        return json.loads(cache.read_text())
    secs = len(x) / SR
    guard(secs / 3600 * ASR_USD_PER_HOUR + 0.001)

    async def go():
        t0 = time.monotonic()
        body = await meta_transcribe(wav_bytes(x), AVA.app_keywords())
        return body, time.monotonic() - t0
    (body, took), retries = await AVA.with_retries(f"{kind} {uid} asr", go)
    ms = body.get("audioDurationMs") or secs * 1000
    usd = ms / 3_600_000 * ASR_USD_PER_HOUR
    VE.log_spend(kind=kind, id=uid, model=ASR_MODEL, usd=round(usd, 6), secs=round(took, 2), audio_ms=ms)
    transcript = (body.get("transcript") or " ".join(t.get("transcript", "") for t in body.get("turns") or [])).strip()
    rec = {"body": body, "transcript": transcript, "seconds": took, "usd": usd, "audio_ms": ms, "retries": retries}
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(rec, ensure_ascii=False, indent=1))
    return rec


async def cmd_align() -> None:
    """Alignment material only (not scored): the energy VAD segments of h-quiet and one batch ASR of each long file."""
    for name in ("h-quiet", "h-music"):
        x = read_wav(A2 / f"{name}.wav")
        rec = await asr_batch("s2:align:asr", name, x, OUT / "align" / f"{name}.batch.json")
        body = rec["body"]
        print(name, {k: v for k, v in body.items() if k not in ("turns", "transcript")})
        for t in body.get("turns") or []:
            print(" ", {k: v for k, v in t.items() if k != "transcript"}, t.get("transcript"))
        if not body.get("turns"):
            print(rec["transcript"])
        segs = vad(x)
        print(name, "VAD segments", len(segs))
    print(f"set 2 spend ${my_spent():.4f}")



# ---------- splitting the long files into push-to-talk clips ----------

PAD = 0.3


def raw_segments(name: str) -> list[tuple[float, float]]:
    """The VAD segments of a long file. Quiet: floor about -70 dBFS, so -45/-55 dBFS hysteresis with 1.5 s of silence.
    Music: the music bed sits at -60 to -40 dBFS between lines, so the gate is raised to -30/-36 dBFS with 0.7 s of
    silence, and segments less than 1.7 s apart are joined (every within-line pause in this file is under 1.6 s,
    every between-line gap over 1.9 s)."""
    x = read_wav(A2 / f"{name}.wav")
    if name == "h-quiet":
        return vad(x, -45, -55, 1.5)
    segs = vad(x, -30, -36, 0.7)
    out = [list(segs[0])]
    for a, b in segs[1:]:
        if a - out[-1][1] < 1.7:
            out[-1][1] = b
        else:
            out.append([a, b])
    return [tuple(s) for s in out]


async def cmd_segments() -> None:
    """Transcribe every raw VAD segment once (alignment check only, kind s2:align:seg) and print it."""
    for name in ("h-quiet", "h-music"):
        x = read_wav(A2 / f"{name}.wav")
        segs = raw_segments(name)
        async def one(i, a, b):
            y = x[int(max(0, a - PAD) * SR): int(min(len(x) / SR, b + PAD) * SR)]
            return await asr_batch("s2:align:seg", f"{name}:{i}", y, OUT / "align" / f"{name}.seg{i:02d}.json")
        recs = await asyncio.gather(*(one(i, a, b) for i, (a, b) in enumerate(segs)))
        for i, ((a, b), r) in enumerate(zip(segs, recs)):
            print(f"{name} {i:2d} {a:7.2f}-{b:7.2f} ({b - a:5.2f}s) {r['transcript']!r}")
    print(f"set 2 spend ${my_spent():.4f}")



def clip_plan() -> dict[str, list[dict]]:
    """Each long file's 27 clips: line id, the speech span (s, file time), the clip span (padded) and the raw segments.
    h-quiet has two segments that are not lines: #0 ("Yeah.", before the first line) is dropped, and #19
    ("diminuendo", 1.8 s after h18 ends with "make it a diminuendo") is h18 said again and stays in h18's clip."""
    plan = {}
    for name, suffix in (("h-quiet", ""), ("h-music", "m")):
        segs = list(raw_segments(name))
        dur = len(read_wav(A2 / f"{name}.wav")) / SR
        groups: list[list[int]] = []
        notes: dict[int, str] = {}
        for k in range(len(segs)):
            if name == "h-quiet" and k == 0:
                notes[k] = "dropped: 'Yeah.' before the first line"
                continue
            if name == "h-quiet" and k == 19:
                groups[-1].append(k)
                notes[k] = "joined to h18: the word 'diminuendo' said again"
                continue
            groups.append([k])
        assert len(groups) == 27, (name, len(groups))
        rows = []
        for n, g in enumerate(groups):
            a, b = segs[g[0]][0], segs[g[-1]][1]
            prev_end = segs[groups[n - 1][-1]][1] if n else 0.0
            next_start = segs[groups[n + 1][0]][0] if n + 1 < len(groups) else dur
            ca = max(a - PAD, (prev_end + a) / 2, 0.0)
            cb = min(b + PAD, (b + next_start) / 2, dur)
            rows.append({"line": f"h{n + 1:02d}", "clip": f"h{n + 1:02d}{suffix}", "speech_start": a, "speech_end": b,
                         "clip_start": round(ca, 2), "clip_end": round(cb, 2), "segments": g,
                         "notes": [notes[k] for k in g if k in notes]})
        plan[name] = rows
        plan[name + ":dropped"] = [{"segment": k, "span": segs[k], "note": v} for k, v in notes.items() if "dropped" in v]
    return plan


def cmd_clips() -> None:
    plan = clip_plan()
    CLIPS.mkdir(parents=True, exist_ok=True)
    lines = {r["id"]: r["text"] for r in script2()}
    out = {"made_by": "experiments/voice/set2.py clips", "pad_s": PAD, "files": {}}
    for name in ("h-quiet", "h-music"):
        x = read_wav(A2 / f"{name}.wav")
        for r in plan[name]:
            y = x[int(r["clip_start"] * SR): int(r["clip_end"] * SR)]
            write_wav(CLIPS / f"{r['clip']}.wav", y)
            seg_text = " / ".join(json.loads((OUT / "align" / f"{name}.seg{k:02d}.json").read_text())["transcript"]
                                  for k in r["segments"])
            r["align_asr"] = seg_text
            r["similarity"] = round(sim(seg_text, lines[r["line"]]), 2)
        # script order: each clip's alignment transcript is closest to its own line
        for r in plan[name]:
            best = max(lines, key=lambda h: sim(r["align_asr"], lines[h]))
            assert best == r["line"], (name, r["clip"], best, r["align_asr"])
        out["files"][name] = {"clips": plan[name], "dropped": plan[name + ":dropped"]}
        print(name, len(plan[name]), "clips, all closest to their own script line")
    (CLIPS / "clips.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))


# ---------- augmenting the old 40 (numpy, seeded: ffmpeg is not installed on this machine) ----------

AUG_CONDS = ("far", "musicbed", "noise")


def speech_rms(x: np.ndarray) -> float:
    """RMS over the frames within 25 dB of the loudest 20 ms frame (the speech, not the pauses)."""
    fr = 320
    f = x[: len(x) // fr * fr].astype(np.float64).reshape(-1, fr)
    p = (f ** 2).mean(axis=1)
    db = 10 * np.log10(p + 1e-9)
    return float(np.sqrt(p[db >= db.max() - 25].mean()))


def room_ir(seed: int, rt60: float = 0.6, drr_db: float = 0.0) -> np.ndarray:
    """A synthetic room: the direct path, then exponentially decaying noise from 3 ms (reverberant energy equal to the
    direct path's at drr 0 dB, about what a stand 2-3 m from the speaker hears)."""
    rng = np.random.default_rng(seed)
    n = int(rt60 * 1.2 * SR)
    t = np.arange(n) / SR
    tail = rng.standard_normal(n) * np.exp(-6.9 * t / rt60)
    tail[: int(0.003 * SR)] = 0
    tail *= np.sqrt(10 ** (-drr_db / 10) / (tail ** 2).sum())
    h = tail
    h[0] = 1.0
    return h


def fftconv(x: np.ndarray, h: np.ndarray) -> np.ndarray:
    n = len(x) + len(h) - 1
    m = 1 << (n - 1).bit_length()
    return np.fft.irfft(np.fft.rfft(x, m) * np.fft.rfft(h, m), m)[: len(x)]


def pink(n: int, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    spec = np.fft.rfft(rng.standard_normal(n))
    f = np.fft.rfftfreq(n, 1 / SR)
    f[0] = f[1]
    y = np.fft.irfft(spec / np.sqrt(f), n)
    return y / np.sqrt((y ** 2).mean())


def music_pool() -> np.ndarray:
    """Music only: h-music.wav between its clips' speech spans, 0.4 s in from each side (Dvorak's 9th, in the room)."""
    x = read_wav(A2 / "h-music.wav").astype(np.float64)
    rows = clip_plan()["h-music"]
    parts = []
    for r0, r1 in zip(rows, rows[1:]):
        a, b = r0["speech_end"] + 0.4, r1["speech_start"] - 0.4
        if b - a >= 0.8:
            parts.append(x[int(a * SR): int(b * SR)])
    return np.concatenate(parts)


def cmd_augment() -> None:
    pool = music_pool()
    meta = {"music_pool_s": round(len(pool) / SR, 2), "clips": {}}
    for k, p in enumerate(sorted((VE.AUDIO / "wav").glob("v*.wav"))):
        uid = p.stem
        x = read_wav(p).astype(np.float64)
        srms = speech_rms(x)
        seed = 2026_11_02 + k
        # (a) far field: room reverb, level back to the dry clip's, then -12 dB
        y = fftconv(x, room_ir(seed))
        y *= srms / speech_rms(y) * 10 ** (-12 / 20)
        far = y
        # (b) music bed at -20 dB relative to the speech
        off = np.random.default_rng(seed).integers(0, len(pool))
        m = np.resize(np.roll(pool, -off), len(x))
        m *= srms * 10 ** (-20 / 20) / np.sqrt((m ** 2).mean())
        mus = x + m
        # (c) pink noise at -25 dB relative to the speech
        noi = x + pink(len(x), seed) * srms * 10 ** (-25 / 20)
        info = {}
        for cond, y in (("far", far), ("musicbed", mus), ("noise", noi)):
            peak = np.abs(y).max()
            if peak > 32000:
                y = y * 32000 / peak
            write_wav(AUG / cond / f"{uid}.wav", y)
            info[cond] = {"peak_scaled": bool(peak > 32000)}
        meta["clips"][uid] = {"seed": seed, "music_offset_s": round(off / SR, 2), **info}
    (AUG / "augment.json").write_text(json.dumps(meta, indent=1))
    print(f"40 clips x {AUG_CONDS} -> {AUG}; music pool {meta['music_pool_s']} s")


# ---------- the worked examples (hold-out check) ----------

def example_items() -> list[dict]:
    out, tr = [], None
    for line in EXAMPLES.splitlines():
        if line.startswith("Transcript: "):
            tr = json.loads(line[len("Transcript: "):])
        elif line.startswith("Answer: "):
            ans = json.loads(line[len("Answer: "):])
            out.append({"transcript": tr, "marks": ans if isinstance(ans, list) else []})
    return out


EX = example_items()


def wsim(a: str, b: str) -> float:
    from .textnorm import words
    return difflib.SequenceMatcher(None, words(a), words(b)).ratio()


def overlap_rows() -> list[dict]:
    rows = []
    lab = VE.labels()
    for uid in sorted(p.stem for p in (VE.AUDIO / "wav").glob("v*.wav")):
        text = lab[VE.base_id(uid)]["text"]
        said = text
        if uid.endswith("c"):               # a retake: its words are its own; use yesterday's production transcript
            t = HERE / "out" / "audio_vs_asr" / "r1" / "C" / f"{uid}.json"
            said = json.loads(t.read_text())["transcript"] if t.exists() else text
        best = max(EX, key=lambda e: wsim(said, e["transcript"]))
        rows.append({"id": uid, "said": said, "example": best["transcript"], "sim": round(wsim(said, best["transcript"]), 2)})
    for r in script2():
        best = max(EX, key=lambda e: wsim(r["text"], e["transcript"]))
        rows.append({"id": r["id"], "said": r["text"], "example": best["transcript"],
                     "sim": round(wsim(r["text"], best["transcript"]), 2)})
    return rows


OVERLAP_MIN = 0.6
IN_EXAMPLES = AVA.IN_EXAMPLES | {"v02c", "v08c"}


def copied_example(uid: str, m: dict) -> str | None:
    """A mark on a line that is not itself a worked example, whose text and bars are a worked example's answer."""
    if uid in IN_EXAMPLES or VE.base_id(uid) in AVA.IN_EXAMPLES:
        return None
    from .textnorm import annotation_key
    for e in EX:
        for em in e["marks"]:
            same_text = annotation_key(str(m.get("text", ""))) == annotation_key(em["text"])
            same_bars = (m.get("bar_from"), m.get("bar_to")) == (em["bar_from"], em["bar_to"]) and em["bar_from"] is not None
            if same_text or (same_bars and sim(str(m.get("text", "")), em["text"]) >= 0.5):
                return em["text"]
    return None


def cmd_overlap() -> None:
    for r in overlap_rows():
        if r["sim"] >= OVERLAP_MIN:
            print(f"{r['id']:5} {r['sim']:.2f} {r['said']!r} ~ {r['example']!r}")
    top = max((r for r in overlap_rows() if r["id"].startswith("h")), key=lambda r: r["sim"])
    print("set 2 closest:", top)


# ---------- scoring ----------
#
# A line is right when the marks that reach the admin are the ground truth's (old 40: `voice_eval.score_line`, all 5
# fields, v04c relabelled Soprano; set 2: the messy set's matcher with its alternatives and ANY fields). v4f has no
# confidence field and production writes every surviving mark as `proposed`, so every mark reaches the admin and none
# reaches the stand: a "flag" line is right when its mark has the right core fields (or no mark where `also` is "none"),
# and a "none" line whose `also` is "flag" accepts a mark. A shipped error is a line where a wrong mark reached the
# admin (a missed mark alone is not shipped). Dangerous: a shipped mark with the wrong part or audience, the wrong
# bars, or the opposite instruction (`INVERTED`). A phantom is a mark where nothing should be written.

OLD = VE.labels()
NEGATION = r"\b(no|not|don'?t|do not|never|without|senza|non|carry|keep)\b"


def _has(t: str, pat: str) -> bool:
    return re.search(pat, (t or "").lower()) is not None


# The opposite card: the text says the reverse of what was said (keyed by messy case id or old base id).
INVERTED = {
    "pc08": lambda t: _has(t, r"rush") and not _has(t, NEGATION),
    "pc09": lambda t: _has(t, r"breath") and not _has(t, NEGATION),
    "pc11": lambda t: _has(t, r"\b(f|forte|ff)\b") and not _has(t, r"\b(pp|p|pianissimo|piano|softer|soft)\b"),
    "pc17": lambda t: _has(t, r"\b(rit|ritard|ritardando)\b") and not _has(t, r"\b(no|not|tempo)\b"),
    "pc18": lambda t: _has(t, r"cresc") and not _has(t, r"\b(dim|diminuendo|decresc)"),
    "v10": lambda t: _has(t, r"\b(louder|cresc\w*|f|forte)\b") and not _has(t, r"\b(not|no|hold|back|less|softer|p)\b"),
    "v16": lambda t: _has(t, r"vib") and not _has(t, r"\b(no|senza|non|without)\b"),
    "v24": lambda t: _has(t, r"rush") and not _has(t, NEGATION),
}
INVERTED_AUD = {"v15": lambda aud: "part:Cello" in aud}      # "everyone except the cello"


def auds(m: dict) -> list[str]:
    a = m.get("audience")
    return a if isinstance(a, list) else [a]


def clean_marks(ms: list) -> list[dict]:
    out = []
    for m in ms:
        if isinstance(m, dict):
            m = dict(m)
            m.setdefault("audience", [])
            m["text"] = m.get("text") if isinstance(m.get("text"), str) else ""
            out.append(m)
    return out


def all_marks(ans: object) -> list[dict]:
    """Every mark object in an answer, unchecked (what ships when there is no check)."""
    if isinstance(ans, dict) and ans.get("none") is True:
        return []
    if isinstance(ans, dict) and isinstance(ans.get("marks"), list):
        ans = ans["marks"]
    return clean_marks(ans if isinstance(ans, list) else [ans])


def old_label(uid: str) -> dict:
    r = dict(OLD[VE.base_id(uid)])
    r.update(KEY_FIX.get(uid, {}))
    return r


def inverted(key: str, marks: list[dict]) -> bool:
    f, g = INVERTED.get(key), INVERTED_AUD.get(key)
    return any((f and f(m.get("text", ""))) or (g and g(auds(m))) for m in marks)


def score_marks(uid: str, marks: list[dict]) -> dict:
    marks = clean_marks(marks)
    cats: set[str] = set()
    if uid.startswith("h"):
        c = CASE[H2CASE[uid]]
        key, negative = c["id"], c["gt"] == "none"
        if negative:
            ok = not marks or c["also"] == "flag"
            if marks and not ok:
                cats.add("phantom")
        else:
            answers = [c["answers"][0]] if c["gt"] == "flag" else c["answers"]
            best = None
            for ai, answer in enumerate(answers):
                pairs, extras = TR.match(answer, marks)
                right = bool(marks) and not extras and all(f["core"] for *_, f in pairs)
                k = (right, sum(f["core"] for *_, f in pairs), sum(sum(f.values()) for *_, f in pairs), -ai)
                if best is None or k > best[0]:
                    best = (k, pairs, extras)
            _, pairs, extras = best
            ok = best[0][0] or (not marks and c["gt"] == "flag" and c["also"] == "none")
            for g, p, f in pairs:
                if p is not None and not f["core"]:
                    cats |= {n for n, k_ in (("audience", "audience"), ("bars", "bars"), ("kind", "kind"),
                                             ("position", "position")) if not f[k_]}
            if extras:
                cats.add("extra")
    else:
        key = VE.base_id(uid)
        r = old_label(uid)
        sc = VE.score_line(key, r, marks)
        negative = sc["negative"]
        ok = sc["ok"] if negative else sc["all_fields"]
        if marks and not ok:
            if negative:
                cats.add("phantom")
            else:
                for f, n in (("audience", "audience"), ("bar_from", "bars"), ("bar_to", "bars"), ("kind", "kind"),
                             ("position", "position")):
                    if not sc[f]:
                        cats.add(n)
    if marks and inverted(key, marks):       # the opposite card is wrong whatever its fields
        ok = False
        cats.add("inverted")
    shipped_error = bool(marks) and not ok
    return {"ok": bool(ok), "negative": negative, "n_marks": len(marks), "shipped_error": shipped_error,
            "cats": sorted(cats), "dangerous": shipped_error and bool(cats & {"audience", "bars", "inverted"}),
            "phantom": "phantom" in cats,
            "copied": [x for m in marks if (x := copied_example(uid, m))]}


# ---------- calls ----------

KW = AVA.app_keywords()
SET2_IDS = [r["id"] for r in script2()]
OLD_IDS = sorted(p.stem for p in (VE.AUDIO / "wav").glob("v*.wav"))
CONDS = ("quiet", "music", "far", "musicbed", "noise")
BATCH_PIPES = ("P1", "P3a", "P3b")
STREAK: dict[str, int] = {}
DEAD: set[str] = set()
ERRORS: list[dict] = []


def ids_of(cond: str) -> list[str]:
    return SET2_IDS if cond in ("quiet", "music") else OLD_IDS


def wav_of(cond: str, uid: str) -> Path:
    if cond == "quiet":
        return CLIPS / f"{uid}.wav"
    if cond == "music":
        return CLIPS / f"{uid}m.wav"
    return AUG / cond / f"{uid}.wav"


async def tried(pipe: str, label: str, fn, tries: int = 3):
    """Up to `tries` attempts; a pipeline that fails 3 attempts in a row (any calls) is stopped."""
    last = None
    for k in range(tries):
        if pipe in DEAD:
            raise RuntimeError(f"{pipe} stopped")
        try:
            out = await fn()
            STREAK[pipe] = 0
            return out, k
        except Exception as e:  # noqa: BLE001
            last = e
            STREAK[pipe] = STREAK.get(pipe, 0) + 1
            ERRORS.append({"pipe": pipe, "label": label, "error": f"{type(e).__name__}: {str(e)[:300]}"})
            print(f"  {label}: attempt {k + 1} failed: {type(e).__name__}: {str(e)[:200]}")
            if STREAK[pipe] >= 3:
                DEAD.add(pipe)
                print(f"STOP pipeline {pipe}: 3 errors in a row")
                raise RuntimeError(f"{pipe} stopped after 3 errors in a row: {e}") from e
            await asyncio.sleep(2 * (k + 1))
    raise RuntimeError(f"{label}: {last}")


async def spark(run: str, pipe: str, cond: str, uid: str, system: str, content) -> dict:
    model = MODELS[pipe]
    guard(0.03)
    rep, retries = await tried(pipe, f"{run} {pipe} {cond} {uid} spark", lambda: AVA.spark_stream(model, system, content))
    u = AVA.usage_row(rep["usage"])
    usd = list_usd(u["input_tokens"], u["output_tokens"])
    VE.log_spend(kind=f"s2:{run}:{pipe}:{cond}:propose", id=uid, model=rep["model"], effort="minimal", api="chat",
                 stream=True, usd=round(usd, 6), secs=round(rep["seconds"], 2),
                 first_token_s=rep["first_token_s"] and round(rep["first_token_s"], 2), **u)
    return {**rep, **u, "usd": usd, "retries": retries}


async def asr(run: str, pipe: str, cond: str, uid: str, wav: bytes, secs: float) -> dict:
    guard(secs / 3600 * ASR_USD_PER_HOUR + 0.001)

    async def go():
        t0 = time.monotonic()
        body = await meta_transcribe(wav, KW)
        return body, time.monotonic() - t0
    (body, took), retries = await tried(pipe, f"{run} {pipe} {cond} {uid} asr", go)
    ms = body.get("audioDurationMs") or secs * 1000
    usd = ms / 3_600_000 * ASR_USD_PER_HOUR
    VE.log_spend(kind=f"s2:{run}:{pipe}:{cond}:asr", id=uid, model=ASR_MODEL, usd=round(usd, 6), secs=round(took, 2),
                 audio_ms=ms)
    transcript = (body.get("transcript") or " ".join(t.get("transcript", "") for t in body.get("turns") or [])).strip()
    return {"transcript": transcript, "seconds": took, "usd": usd, "audio_ms": ms, "retries": retries}


async def one(run: str, pipe: str, cond: str, uid: str) -> dict:
    dst = OUT / run / pipe / cond / f"{uid}.json"
    if dst.exists():
        return json.loads(dst.read_text())
    wav, secs = pcm_wav(wav_of(cond, uid).read_bytes())
    t0 = time.monotonic()
    rec: dict = {"id": uid, "pipeline": pipe, "cond": cond, "model": MODELS[pipe], "audio_s": round(secs, 2)}
    if pipe == "P1":
        a = await asr(run, pipe, cond, uid, wav, secs)
        rec["asr"], rec["transcript"] = a, a["transcript"]
        rec["spark"] = (await spark(run, pipe, cond, uid, *AVA.text_prompt(a["transcript"]))) if a["transcript"] else None
    else:
        system, user = AVA.audio_prompt()
        content = [{"type": "text", "text": user},
                   {"type": "input_audio", "input_audio": {"data": base64.b64encode(wav).decode(), "format": "wav"}}]
        rec["spark"] = await spark(run, pipe, cond, uid, system, content)
    rec["wall_s"] = time.monotonic() - t0
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(json.dumps(rec, ensure_ascii=False, indent=1))
    return rec


async def cmd_run(run: str, pipes: list[str], conds: list[str], concurrency: int) -> None:
    jobs = [(p, c, u) for c in conds for u in ids_of(c) for p in pipes]
    random.Random(f"set2:{run}").shuffle(jobs)
    sem = asyncio.Semaphore(concurrency)
    done = 0

    async def go(p, c, u):
        nonlocal done
        if p in DEAD:
            return
        async with sem:
            if p in DEAD:
                return
            try:
                rec = await one(run, p, c, u)
                done += 1
                sp = rec.get("spark") or {}
                print(f"{done:4}/{len(jobs)} {run} {p} {c} {u}: {rec['wall_s']:.1f}s {(sp.get('text') or '')[:80]!r}")
            except Exception as e:  # noqa: BLE001
                print(f"{run} {p} {c} {u}: ERROR {e}")
    await asyncio.gather(*(go(p, c, u) for p, c, u in jobs))
    if ERRORS:
        (OUT / run).mkdir(parents=True, exist_ok=True)
        with (OUT / run / "errors.jsonl").open("a") as f:
            f.writelines(json.dumps(e) + "\n" for e in ERRORS)
    print(f"stopped: {sorted(DEAD) or 'none'}; errors {len(ERRORS)}; set 2 spend ${my_spent():.4f}; ledger ${VE.spent():.4f}")


# ---------- P2: always-on, the whole file streamed ----------

WS_URL = "wss://api.meta.ai/v1/asr/realtime"
FRAME = SR * 80 // 1000
GROUP_GAP_S, GROUP_MAX = 1.0, 3


async def stream_file(run: str, name: str) -> dict:
    """Stream one long file at real-time pace to Voice Transcribe realtime (ENDPOINTING, the app's keywords) as the mic
    would (no lead-in: the mic is already open; 3 s of silence after). On each `speechComplete` Spark is called at once
    on the turn alone and, when the turn joined a rolling group, on the group. Times are on the stream clock (s from
    the first frame), which is the file's clock at real-time pace."""
    import websockets
    dst = OUT / run / "P2" / f"{name}.json"
    if dst.exists():
        return json.loads(dst.read_text())
    x = read_wav(A2 / f"{name}.wav")
    post = 3.0
    sig = np.concatenate([x, np.zeros(int(post * SR), np.int16)])
    secs = len(sig) / SR
    guard(secs / 3600 * ASR_USD_PER_HOUR + 0.3)
    hs = {"authorization": {"accessToken": f"Bearer {settings.meta_api_key}"}, "audioEncoding": "PCM_16KHZ",
          "model": ASR_MODEL, "mode": "ENDPOINTING", "partialMode": "CUMULATIVE", "emitAudioProgress": False,
          "keywords": KW}
    events: list[dict] = []
    turns: list[dict] = []
    groups: list[dict] = []
    calls: list[dict] = []
    tasks: list[asyncio.Task] = []
    starts: dict = {}
    ends: dict = {}
    clock = {"t0": None}

    def now() -> float:
        return time.monotonic() - clock["t0"]

    async def call(mode: str, key: str, text: str, tids: list, t_trigger: float) -> None:
        system, user = AVA.text_prompt(text)
        try:
            sp = await spark(run, "P2", name, f"{mode}:{key}", system, user)
            calls.append({"mode": mode, "key": key, "turns": tids, "text": text, "t_trigger": t_trigger,
                          "t_done": now(), "spark": sp})
        except Exception as e:  # noqa: BLE001
            calls.append({"mode": mode, "key": key, "turns": tids, "text": text, "t_trigger": t_trigger,
                          "t_done": None, "spark": None, "error": str(e)[:300]})

    def on_event(ev: dict) -> None:
        typ, tid = ev.get("type"), ev.get("turnId")
        if typ == "speechStart":
            starts[tid] = ev.get("audioProcessedMs", 0) / 1000
        elif typ == "speechEnd":
            ends[tid] = ev.get("audioProcessedMs", 0) / 1000
        elif typ == "speechComplete":
            text = (ev.get("transcript") or "").strip()
            s, e = starts.get(tid), ends.get(tid, ev.get("audioProcessedMs", 0) / 1000)
            turn = {"turn": tid, "start": s, "end": e, "text": text, "t_complete": ev["t"], "group": None}
            turns.append(turn)
            if not text:
                return
            g = groups[-1] if groups else None
            if g and len(g["turns"]) < GROUP_MAX and s is not None and s - g["end"] <= GROUP_GAP_S:
                g["turns"].append(tid)
                g["texts"].append(text)
                g["end"] = e
            else:
                g = {"id": len(groups), "turns": [tid], "texts": [text], "start": s, "end": e}
                groups.append(g)
            turn["group"] = g["id"]
            tasks.append(asyncio.create_task(call("alone", str(tid), text, [tid], ev["t"])))
            if len(g["turns"]) > 1:
                tasks.append(asyncio.create_task(call("group", f"g{g['id']}x{len(g['turns'])}", " ".join(g["texts"]),
                                                      list(g["turns"]), ev["t"])))

    async def go():
        events.clear(); turns.clear(); groups.clear(); calls.clear(); starts.clear(); ends.clear()
        t_conn = time.monotonic()
        async with websockets.connect(WS_URL, max_size=2 ** 22) as ws:
            await ws.send(json.dumps(hs))
            ack = json.loads(await ws.recv())
            handshake = time.monotonic() - t_conn
            clock["t0"] = time.monotonic()

            async def sender():
                for k, i in enumerate(range(0, len(sig), FRAME)):
                    d = clock["t0"] + k * FRAME / SR - time.monotonic()
                    if d > 0:
                        await asyncio.sleep(d)
                    await ws.send(sig[i:i + FRAME].tobytes())
                events.append({"type": "_endStream_sent", "t": now()})
                await ws.send(json.dumps({"type": "endStream"}))

            async def receiver():
                try:
                    async for m in ws:
                        if isinstance(m, bytes):
                            continue
                        ev = json.loads(m)
                        ev["t"] = now()
                        if ev.get("type") != "transcript":
                            events.append(ev)
                        if ev.get("type") == "error":
                            print(f"  P2 {run} {name}: server error {str(ev)[:200]}")
                        on_event(ev)
                except websockets.ConnectionClosed:
                    pass
            rx = asyncio.create_task(receiver())
            await sender()
            try:
                await asyncio.wait_for(rx, timeout=30)
            except asyncio.TimeoutError:
                events.append({"type": "_timeout", "t": now()})
            close = ws.close_code
        if close not in (1000, None):
            raise RuntimeError(f"stream closed {close}")
        return ack, handshake, close

    (ack, handshake, close), retries = await tried("P2", f"{run} P2 {name} stream", go)
    usd = int(secs) / 3600 * ASR_USD_PER_HOUR
    VE.log_spend(kind=f"s2:{run}:P2:{name}:asr_rt", id=name, model=ASR_MODEL, usd=round(usd, 6), secs=round(secs, 2),
                 audio_ms=int(secs * 1000))
    await asyncio.gather(*tasks)
    rec = {"name": name, "run": run, "audio_s": secs, "asr_usd": usd, "handshake_s": round(handshake, 3),
           "close": close, "retries": retries, "ack_keys": sorted(ack), "events": events, "turns": turns,
           "groups": groups, "calls": calls}
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(json.dumps(rec, ensure_ascii=False, indent=1))
    print(f"P2 {run} {name}: {len(turns)} turns, {len(groups)} groups, {len(calls)} Spark calls")
    return rec


async def cmd_stream(run: str) -> None:
    await asyncio.gather(*(stream_file(run, n) for n in ("h-quiet", "h-music")))
    print(f"set 2 spend ${my_spent():.4f}")


# ---------- turning records into scored rows ----------

def plan_rows(name: str) -> list[dict]:
    return json.loads((CLIPS / "clips.json").read_text())["files"][name]["clips"]


def script_text() -> dict[str, str]:
    return {r["id"]: r["text"] for r in script2()}


def edge_lost(script: str, heard: str) -> tuple[int, int]:
    """Script words before the first and after the last word the transcript matches (lost at the edges)."""
    from .textnorm import words
    a, b = words(script), words(heard)
    blocks = [bl for bl in difflib.SequenceMatcher(None, a, b, autojunk=False).get_matching_blocks() if bl.size]
    if not blocks:
        return len(a), 0
    return blocks[0].a, len(a) - (blocks[-1].a + blocks[-1].size)


def reply_of(sp: dict | None) -> str:
    return sp["text"] if sp else '{"none": true}'


def parsed(sp: dict | None) -> object | None:
    try:
        return parse_answer(reply_of(sp))
    except Exception:  # noqa: BLE001
        return None


def batch_row(run: str, pipe: str, cond: str, rec: dict) -> dict:
    uid, sp = rec["id"], rec.get("spark")
    ans = parsed(sp)
    unchecked = all_marks(ans) if ans is not None else []
    if pipe == "P1":
        shipped, refused = checked_marks(ans, rec["transcript"], FACTS) if ans is not None else ([], ["unparseable"])
        alt = unchecked                        # what would ship without the check
    else:
        shipped, refused = unchecked, ([] if ans is not None else ["unparseable"])
        quotes = "\n".join(str(m.get("quote", "")) for m in unchecked)
        alt, _ = checked_marks(ans, quotes, FACTS) if ans is not None else ([], [])   # every check but the quote's
    return {"run": run, "pipe": pipe, "cond": cond, "id": uid, "transcript": rec.get("transcript"),
            "reply": reply_of(sp), "marks": clean_marks(shipped), "refused": refused, "score": score_marks(uid, shipped),
            "score_alt": score_marks(uid, alt), "latency_s": rec["wall_s"],
            "asr_s": (rec.get("asr") or {}).get("seconds"), "spark_s": sp and sp["seconds"],
            "input_tokens": sp and sp["input_tokens"], "output_tokens": sp and sp["output_tokens"],
            "reasoning_tokens": sp and sp.get("reasoning_tokens"),
            "usd": (sp["usd"] if sp else 0.0) + (rec.get("asr") or {}).get("usd", 0.0),
            "finish_reason": sp and sp.get("finish_reason")}


def p2_rows(run: str, rec: dict, mode: str) -> tuple[list[dict], dict]:
    """Per-line rows for one streamed file. mode "alone": each turn's own reading; "group": each rolling group's last
    reading. A mark goes to the line its quote came from: the turn holding the quote (else the reading's span), then
    among the lines that span overlaps, the one whose script text the quote is closest to."""
    from app.librarian.voice_prompt import quote_ok
    name = rec["name"]
    cond = "quiet" if name == "h-quiet" else "music"
    lines = plan_rows(name)
    text_of = script_text()
    turns = {t["turn"]: t for t in rec["turns"] if t["text"]}
    for t in turns.values():
        if t["start"] is None:
            t["start"] = t["end"] - 1.0

    def ov(a0, a1, b0, b1):
        return max(0.0, min(a1, b1) - max(a0, b0))

    alone = {c["turns"][0]: c for c in rec["calls"] if c["mode"] == "alone"}
    if mode == "alone":
        readings = [alone[t] for t in sorted(alone)]
    else:
        readings = []
        for g in rec["groups"]:
            gc = [c for c in rec["calls"] if c["mode"] == "group" and c["turns"][0] == g["turns"][0]]
            readings.append(max(gc, key=lambda c: len(c["turns"])) if gc else alone.get(g["turns"][0]))
        readings = [r for r in readings if r]
    reading_of_turn = {t: r for r in readings for t in r["turns"]}

    per_line = {L["line"]: {"marks": [], "unchecked": []} for L in lines}
    offline: list[dict] = []
    for r in readings:
        ans = parsed(r["spark"])
        if ans is None:
            continue
        shipped, _ = checked_marks(ans, r["text"], FACTS)
        for bucket, ms in (("marks", shipped), ("unchecked", all_marks(ans))):
            for m in clean_marks(ms):
                q = str(m.get("quote", ""))
                owner = next((turns[t] for t in r["turns"] if t in turns and quote_ok(q, turns[t]["text"])), None)
                ts = [turns[t] for t in r["turns"] if t in turns]
                a0, a1 = (owner["start"], owner["end"]) if owner else (min(t["start"] for t in ts), max(t["end"] for t in ts))
                cands = [L for L in lines if ov(a0 - 0.5, a1 + 0.5, L["speech_start"], L["speech_end"]) > 0]
                if not cands:
                    if bucket == "marks":
                        offline.append({"mark": m, "span": [a0, a1]})
                    continue
                L = max(cands, key=lambda L: (sim(q, text_of[L["line"]]), ov(a0, a1, L["speech_start"], L["speech_end"])))
                per_line[L["line"]][bucket].append(m)

    # boundaries: which turns overlap which lines
    t_lines = {tid: [L["line"] for L in lines if ov(t["start"], t["end"], L["speech_start"], L["speech_end"]) > 0.1]
               for tid, t in turns.items()}
    rows = []
    for L in lines:
        lid = L["line"]
        lt = [turns[t] for t in turns if lid in t_lines[t]]
        last = max(lt, key=lambda t: t["end"]) if lt else None
        rd = reading_of_turn.get(last["turn"]) if last else None
        lat = (rd["t_done"] - L["speech_end"]) if rd and rd.get("t_done") is not None else None
        heard = " ".join(t["text"] for t in sorted(lt, key=lambda t: t["start"]))
        sp = rd["spark"] if rd else None
        rows.append({"run": run, "pipe": "P2" if mode == "alone" else "P2g", "cond": cond, "id": lid,
                     "transcript": heard, "reply": reply_of(sp) if rd else None, "marks": per_line[lid]["marks"],
                     "refused": [], "score": score_marks(lid, per_line[lid]["marks"]),
                     "score_alt": score_marks(lid, per_line[lid]["unchecked"]), "latency_s": lat,
                     "endpoint_s": (last["t_complete"] - L["speech_end"]) if last else None,
                     "n_turns": len(lt), "edge_lost": list(edge_lost(text_of[lid], heard)) if heard else None,
                     "input_tokens": sp and sp["input_tokens"], "output_tokens": sp and sp["output_tokens"],
                     "reasoning_tokens": sp and sp.get("reasoning_tokens"), "usd": None})
    used = [r for r in readings] if mode == "group" else list(alone.values())
    if mode == "group":   # the live system makes one call per turn: alone for a group's first turn, then the group's
        used = [alone[g["turns"][0]] for g in rec["groups"] if g["turns"][0] in alone] + \
               [c for c in rec["calls"] if c["mode"] == "group"]
    spark_usd = sum(c["spark"]["usd"] for c in used if c.get("spark"))
    for r in rows:
        r["usd"] = (rec["asr_usd"] + spark_usd) / len(rows)
    bound = {"turns": len(turns), "empty_turns": sum(1 for t in rec["turns"] if not t["text"]),
             "turns_on_no_line": [turns[t]["text"] for t in turns if not t_lines[t]],
             "merged_turns": [(t, t_lines[t]) for t in turns if len(t_lines[t]) > 1],
             "split_lines": {r["id"]: r["n_turns"] for r in rows if r["n_turns"] > 1},
             "lost_lines": [r["id"] for r in rows if r["n_turns"] == 0],
             "edge_lost_words": [sum(r["edge_lost"][0] for r in rows if r["edge_lost"]),
                                 sum(r["edge_lost"][1] for r in rows if r["edge_lost"])],
             "offline_marks": offline, "calls": len(used), "spark_usd": spark_usd, "asr_usd": rec["asr_usd"],
             "spark_errors": sum(1 for c in rec["calls"] if c.get("error"))}
    return rows, bound


def clean_rows(run: str) -> list[dict]:
    """Last night's calls on the clean 40 (audio_vs_asr A, B, C), rescored here at no cost: condition "clean"."""
    rows = []
    for old, pipe in (("C", "P1"), ("A", "P3a"), ("B", "P3b")):
        d = HERE / "out" / "audio_vs_asr" / run / old
        for p in sorted(d.glob("v*.json")):
            rec = json.loads(p.read_text())
            rows.append(batch_row(run, pipe, "clean", rec))
    return rows


def cmd_score() -> None:
    for run in ("r1", "r2"):
        rows: list[dict] = []
        bounds: dict = {}
        for pipe in BATCH_PIPES:
            for cond in CONDS:
                for uid in ids_of(cond):
                    p = OUT / run / pipe / cond / f"{uid}.json"
                    if p.exists():
                        rows.append(batch_row(run, pipe, cond, json.loads(p.read_text())))
        for name in ("h-quiet", "h-music"):
            p = OUT / run / "P2" / f"{name}.json"
            if p.exists():
                rec = json.loads(p.read_text())
                for mode in ("alone", "group"):
                    rs, b = p2_rows(run, rec, mode)
                    rows += rs
                    bounds[f"{name}:{mode}"] = b
        rows += clean_rows(run)
        RESULTS.mkdir(exist_ok=True)
        (RESULTS / f"set2_{run}.json").write_text(json.dumps({"run": run, "rows": rows, "p2": bounds},
                                                             ensure_ascii=False, indent=1, default=str))
        print(run, len(rows), "rows")
    cmd_report()


# ---------- report ----------

def pct(xs: list[float], q: float) -> float | None:
    xs = sorted(x for x in xs if x is not None)
    if not xs:
        return None
    k = (len(xs) - 1) * q
    lo = int(k)
    return xs[lo] + (xs[min(lo + 1, len(xs) - 1)] - xs[lo]) * (k - lo)


def summarize(rows: list[dict]) -> dict:
    n = len(rows)
    neg = [r for r in rows if r["score"]["negative"]]
    kept = [r for r in rows if VE.base_id(r["id"]) not in CLIPPED]
    lat = [r["latency_s"] for r in rows if r["latency_s"] is not None]
    med = lambda k: st.median([r[k] for r in rows if r.get(k) is not None]) if any(r.get(k) is not None for r in rows) else None  # noqa: E731
    return {
        "n": n, "ok": sum(r["score"]["ok"] for r in rows), "ship": sum(r["score"]["shipped_error"] for r in rows),
        "danger": sum(r["score"]["dangerous"] for r in rows), "phantom": sum(r["score"]["phantom"] for r in rows),
        "inverted": sum("inverted" in r["score"]["cats"] for r in rows),
        "aud": sum("audience" in r["score"]["cats"] for r in rows), "bars": sum("bars" in r["score"]["cats"] for r in rows),
        "neg_ok": sum(r["score"]["ok"] for r in neg), "n_neg": len(neg),
        "missed": sum((not r["score"]["ok"]) and not r["score"]["shipped_error"] for r in rows),
        "ok_kept": sum(r["score"]["ok"] for r in kept), "n_kept": len(kept),
        "ship_kept": sum(r["score"]["shipped_error"] for r in kept), "danger_kept": sum(r["score"]["dangerous"] for r in kept),
        "alt_ok": sum(r["score_alt"]["ok"] for r in rows), "alt_ship": sum(r["score_alt"]["shipped_error"] for r in rows),
        "copied": sum(bool(r["score"]["copied"]) for r in rows),
        "lat_med": st.median(lat) if lat else None, "lat_p95": pct(lat, 0.95),
        "in_med": med("input_tokens"), "out_med": med("output_tokens"),
        "usd_line": sum(r["usd"] or 0 for r in rows) / n if n else None,
    }


PIPE_NAMES = {"P1": "P1 push-to-talk, production", "P2": "P2 always-on, turn alone", "P2g": "P2 always-on, rolling group",
              "P3a": "P3a Spark 1.2 on audio", "P3b": "P3b Spark 1.3 on audio"}
COND_ORDER = ("quiet", "music", "clean", "far", "musicbed", "noise")


def f2(x, d=2):
    return "-" if x is None else f"{x:.{d}f}"


def table(groups: dict, with_kept: bool) -> list[str]:
    head = ("| pipeline | condition | runs | lines ok | shipped errors | dangerous (aud / bars / inverted) | phantom | "
            "rightly no mark | missed | " + ("w/o clipped: ok / shipped / dangerous | " if with_kept else "")
            + "alt: ok / shipped | latency median / p95 s | in / out tok | $/line |")
    out = [head, "|" + "---|" * (head.count("|") - 1)]
    for (pipe, cond, runs), rows in groups.items():
        s = summarize(rows)
        n = s["n"]
        out.append(
            f"| {PIPE_NAMES[pipe]} | {cond} | {runs} | {s['ok']}/{n} ({s['ok'] / n:.0%}) | **{s['ship']}/{n} ({s['ship'] / n:.0%})** | "
            f"{s['danger']} ({s['aud']} / {s['bars']} / {s['inverted']}) | {s['phantom']} | {s['neg_ok']}/{s['n_neg']} | "
            f"{s['missed']} | " + (f"{s['ok_kept']}/{s['n_kept']} / {s['ship_kept']} / {s['danger_kept']} | " if with_kept else "")
            + f"{s['alt_ok']} / {s['alt_ship']} | {f2(s['lat_med'])} / {f2(s['lat_p95'])} | "
            f"{f2(s['in_med'], 0)} / {f2(s['out_med'], 0)} | {f2(s['usd_line'], 5)} |")
    return out


def load_rows() -> tuple[list[dict], dict]:
    rows, bounds = [], {}
    for run in ("r1", "r2"):
        p = RESULTS / f"set2_{run}.json"
        if p.exists():
            d = json.loads(p.read_text())
            rows += d["rows"]
            bounds[run] = d["p2"]
    return rows, bounds


def fmt_marks(ms: list[dict]) -> str:
    return "; ".join(f"{m.get('text')} [{m.get('position')} {m.get('bar_from')}-{m.get('bar_to')} "
                     f"{','.join(map(str, auds(m)))} {m.get('kind')}]" for m in ms) or "no mark"


def want_of(uid: str) -> str:
    if uid.startswith("h"):
        c = CASE[H2CASE[uid]]
        return f"gt {c['gt']}" if c["gt"] else c["note"]
    r = old_label(uid)
    return f"{r['expect']} [{r['position']} {r['bar_from'] or None}-{r['bar_to'] or None} {r['audience']} {r['kind']}]"


def cmd_report() -> None:
    rows, bounds = load_rows()
    by: dict = {}
    for r in rows:
        by.setdefault((r["pipe"], r["cond"]), []).append(r)
    pipes = ("P1", "P2", "P2g", "P3a", "P3b")
    out = ["## Pooled over both runs", "",
           "Set 2 (27 lines per run; 5 'none' lines, 2 'flag' lines):", ""]
    g = {(p, c, "r1+r2"): by[(p, c)] for p in pipes for c in ("quiet", "music") if (p, c) in by}
    out += table(g, False)
    out += ["", "Old 40 (v04c relabelled Soprano; 'ok w/o clipped' leaves out v11, v16, v28; 'clean' is last night's "
            "calls rescored):", ""]
    g = {(p, c, "r1+r2"): by[(p, c)] for p in pipes for c in ("clean", "far", "musicbed", "noise") if (p, c) in by}
    out += table(g, True)
    out += ["", "## Per run", ""]
    g = {}
    for p in pipes:
        for c in COND_ORDER:
            for run in ("r1", "r2"):
                rs = [r for r in by.get((p, c), []) if r["run"] == run]
                if rs:
                    g[(p, c, run)] = rs
    out += table(g, True)
    # P2 boundaries and latency
    out += ["", "## P2 boundaries (endpointer turns against the 27 lines)", "",
            "| run | file | turns | empty | turns on no line | lines split (turns) | turns merging lines | lines with no turn | "
            "script words lost at start / end (P2) | same for P1 batch clip transcript | endpoint lag median / p95 s | "
            "Spark calls | Spark errors |", "|" + "---|" * 13]
    for run, bd in sorted(bounds.items()):
        for key, b in sorted(bd.items()):
            if not key.endswith(":alone"):
                continue
            name = key.split(":")[0]
            cond = "quiet" if name == "h-quiet" else "music"
            p1 = [r for r in by.get(("P1", cond), []) if r["run"] == run]
            el = [edge_lost(script_text()[r["id"]], r["transcript"] or "") for r in p1]
            ep = [r["endpoint_s"] for r in by.get(("P2", cond), []) if r["run"] == run and r["endpoint_s"] is not None]
            out.append(f"| {run} | {name} | {b['turns']} | {b['empty_turns']} | {len(b['turns_on_no_line'])} "
                       f"{b['turns_on_no_line'][:4]} | {len(b['split_lines'])} {b['split_lines']} | "
                       f"{len(b['merged_turns'])} {b['merged_turns']} | {b['lost_lines']} | "
                       f"{b['edge_lost_words'][0]} / {b['edge_lost_words'][1]} | "
                       f"{sum(e[0] for e in el)} / {sum(e[1] for e in el)} | {f2(st.median(ep) if ep else None)} / "
                       f"{f2(pct(ep, 0.95))} | {b['calls']} alone, {bd[name + ':group']['calls']} group | {b['spark_errors']} |")
        for key, b in sorted(bd.items()):
            if b["offline_marks"]:
                out.append(f"\n{run} {key}: marks from turns on no line: " + fmt_marks([o["mark"] for o in b["offline_marks"]]))
    # failures
    out += ["", "## Per-line failures (both runs; shipped errors marked SHIPPED, dangerous ones DANGER)", ""]
    for p in pipes:
        for c in COND_ORDER:
            rs = sorted(by.get((p, c), []), key=lambda r: (r["id"], r["run"]))
            bad = [r for r in rs if not r["score"]["ok"]]
            if not rs:
                continue
            out.append(f"### {PIPE_NAMES[p]}, {c}: {len(bad)} failures of {len(rs)}\n")
            for r in bad:
                s = r["score"]
                tag = ("DANGER " if s["dangerous"] else "") + ("SHIPPED " if s["shipped_error"] else "missed ")
                cats = f" ({', '.join(s['cats'])})" if s["cats"] else ""
                cp = f" COPIED EXAMPLE: {s['copied']}" if s["copied"] else ""
                heard = f" | heard: {r['transcript']!r}" if r.get("transcript") is not None else ""
                out.append(f"- {r['run']} {r['id']}: {tag}{cats} got {fmt_marks(r['marks'])}; want {want_of(r['id'])}{cp}{heard}")
            out.append("")
    copied = [(r["pipe"], r["cond"], r["run"], r["id"], r["score"]["copied"]) for r in rows if r["score"]["copied"]]
    out += ["## Answers that copy a worked example (lines that are not themselves examples)", ""]
    out += [f"- {p} {c} {run} {i}: {x}" for p, c, run, i, x in copied] or ["- none"]
    out += ["", f"Set 2 spend (s2:* in spend.jsonl): ${my_spent():.4f}; ledger total ${VE.spent():.4f}", ""]
    text = "\n".join(out)
    (RESULTS / "set2_tables.md").write_text(text)
    print(text[:12000])


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    for c in ("align", "segments", "clips", "augment", "overlap", "score", "report"):
        sub.add_parser(c)
    r = sub.add_parser("run")
    r.add_argument("--run", required=True)
    r.add_argument("--pipes", default=",".join(BATCH_PIPES))
    r.add_argument("--conds", default=",".join(CONDS))
    r.add_argument("--concurrency", type=int, default=6)
    s = sub.add_parser("stream")
    s.add_argument("--run", required=True)
    a = ap.parse_args()
    if a.cmd == "align":
        asyncio.run(cmd_align())
    elif a.cmd == "segments":
        asyncio.run(cmd_segments())
    elif a.cmd == "clips":
        cmd_clips()
    elif a.cmd == "augment":
        cmd_augment()
    elif a.cmd == "overlap":
        cmd_overlap()
    elif a.cmd == "run":
        asyncio.run(cmd_run(a.run, a.pipes.split(","), a.conds.split(","), a.concurrency))
    elif a.cmd == "stream":
        asyncio.run(cmd_stream(a.run))
    elif a.cmd == "score":
        cmd_score()
    else:
        cmd_report()


if __name__ == "__main__":
    main()
