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
    cd api && uv run python -m experiments.voice.set2 report

Every paid call goes to spend.jsonl with a kind starting "s2:"; this experiment stops at $12 of its own spend.
Raw replies go to out/set2/ (ignored); scores to results/set2_<run>.json.
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


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("align")
    a = ap.parse_args()
    if a.cmd == "align":
        asyncio.run(cmd_align())


if __name__ == "__main__":
    main()
