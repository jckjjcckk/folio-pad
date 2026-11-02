"""Audio straight to Spark vs the production chain (CK, 2026-11-01): three pipelines over the 40 recorded lines.

    A  muse-spark-1.2, the take sent as an `input_audio` part             -> proposal
    B  muse-spark-1.3, the take sent as an `input_audio` part             -> proposal
    C  production: muse-voice-transcribe-1.0 (DIARIZATION, the app's keywords) -> muse-spark-1.3 on the transcript

Every Spark call is the product's: chat completions, reasoning_effort "minimal", streamed, max_completion_tokens 8192
(`transcribe_voice.VOICE_EFFORT`, `llm.chat`), system and prompt from `voice_prompt.build_prompt` with the facts the
app would pass for the eval's quartet + choir book (groups from `derive_groups`, no landmarks). A and B use the same
prompt with the transcript section swapped for the attached recording (and the quote asked for "as said", since there
is no transcript to copy from); see `audio_prompt`. Scoring is `voice_eval.score_line` against script.csv, plus the
eval's judge2 on the stand text. A's and B's quotes cannot be checked against a transcript, so for them the quote check
is the model's own words (every other check in `checked_marks` applies unchanged).

    cd api && uv run python -m experiments.voice.audio_vs_asr probe            # one clip on A, prints usage
    cd api && uv run python -m experiments.voice.audio_vs_asr run --run r1 [--pipelines A,B,C]
    cd api && uv run python -m experiments.voice.audio_vs_asr report

Raw replies go to out/audio_vs_asr/<run>/<pipeline>/ (ignored); every paid call to spend.jsonl; scores to
results/audio_vs_asr_<run>.json.
"""

from __future__ import annotations

import argparse
import asyncio
import base64
import json
import random
import statistics as st
import sys
import time
from pathlib import Path

import httpx

from app.librarian.transcribe_voice import ASR_MODEL, Score, meta_transcribe, pcm_wav
from app.librarian.voice_prompt import SCHEMA, ScoreFacts, build_prompt, checked_marks, derive_groups, parse_answer
from app.settings import settings

from . import voice_eval as VE

HERE = Path(__file__).resolve().parent
WAVS = VE.AUDIO / "wav"
OUT = HERE / "out" / "audio_vs_asr"
RESULTS = HERE / "results"
CAP_USD = 5.0                      # this experiment's own cap, on top of voice_eval's ledger budget
EFFORT = "minimal"
MAX_TOKENS = 8192
LIST = {"in": 1.25, "cached": 0.15, "out": 4.25}   # Spark Standard, every version, $/M (dev.meta.ai pricing)
ASR_USD_PER_HOUR = 0.18
PIPELINES = {"A": "muse-spark-1.2", "B": "muse-spark-1.3", "C": "muse-spark-1.3"}
RETRIES = 3

# The facts the app passes (`transcribe_voice.Score.facts`): groups always, landmarks a list (none for this book).
FACTS = ScoreFacts(parts=VE.FACTS.parts, members=VE.FACTS.members, groups=derive_groups(VE.FACTS.parts), landmarks=[])


def app_keywords() -> list[str]:
    """`Score.keywords()` for this book: the app's ASR keywords (parts, plurals, nicknames, names, letters, terms)."""
    s = Score.__new__(Score)
    s.parts, s.members, s.letters = FACTS.parts, {m: m for m in FACTS.members}, {c: 0 for c in FACTS.rehearsal_marks}
    return s.keywords()


# ---------- prompts ----------

TRANSCRIPT_BLOCK = 'Transcript of what the conductor said:\n"{t}"\n\n'
AUDIO_BLOCK = "What the conductor said is the attached audio recording (one take, as recorded in rehearsal).\n\n"
AUDIO_EDITS = [
    ("- quote: copy a contiguous span of the transcript exactly, character for character.",
     "- quote: the words of the recording the mark comes from, written out exactly as said."),
    ("- The transcript is machine speech recognition and mishears words. A word that sounds like",
     "- You are hearing a rehearsal recording and may mishear words. A word that sounds like"),
    ("<verbatim span of the transcript the mark comes from>", "<the words of the recording the mark comes from, as said>"),
]


def text_prompt(transcript: str) -> tuple[str, str]:
    return build_prompt(transcript, FACTS)


def audio_prompt() -> tuple[str, str]:
    marker = "\u0000TRANSCRIPT\u0000"
    system, user = build_prompt(marker, FACTS)
    block = TRANSCRIPT_BLOCK.format(t=marker)
    assert user.count(block) == 1
    user = user.replace(block, AUDIO_BLOCK)
    for old, new in AUDIO_EDITS:
        assert user.count(old) == 1, old
        user = user.replace(old, new)
    assert "transcript" not in user.lower().replace("transcript:", ""), "a transcript reference left in the audio prompt"
    return system, user


# ---------- ledger ----------

def my_spent() -> float:
    if not VE.LEDGER.exists():
        return 0.0
    return sum(r["usd"] for r in map(json.loads, filter(str.strip, VE.LEDGER.read_text().splitlines()))
               if str(r.get("kind", "")).startswith("ava:"))


def guard(next_usd: float) -> None:
    if my_spent() + next_usd > CAP_USD:
        sys.exit(f"STOP: this experiment's spend {my_spent():.4f} + {next_usd:.4f} would pass ${CAP_USD}")
    VE.guard(next_usd)


def list_usd(tin: int, tout: int) -> float:
    return (tin * LIST["in"] + tout * LIST["out"]) / 1e6


# ---------- calls ----------

async def spark_stream(model: str, system: str, content: str | list[dict]) -> dict:
    """One streamed chat-completions call, the request `llm.chat(stream=True)` sends (no internal retry here: the
    caller retries). Returns text, wall seconds, time to first content token, usage."""
    body = {"model": model, "messages": [{"role": "system", "content": system}, {"role": "user", "content": content}],
            "reasoning_effort": EFFORT, "max_completion_tokens": MAX_TOKENS, "stream": True,
            "stream_options": {"include_usage": True}}
    url = settings.meta_api_base_url.rstrip("/") + "/chat/completions"
    t0 = time.monotonic()
    text, usage, finish, first, got = "", {}, None, None, model
    async with httpx.AsyncClient(timeout=180) as c:
        async with c.stream("POST", url, json=body, headers={"Authorization": f"Bearer {settings.meta_api_key}"}) as r:
            if r.status_code != 200:
                raise RuntimeError(f"HTTP {r.status_code}: {(await r.aread())[:400].decode('utf-8', 'replace')}")
            async for line in r.aiter_lines():
                if not line.startswith("data:") or line.strip() == "data: [DONE]":
                    continue
                ev = json.loads(line[5:])
                got = ev.get("model") or got
                if ev.get("usage"):
                    usage = ev["usage"]
                for ch in ev.get("choices") or []:
                    d = (ch.get("delta") or {}).get("content")
                    if d:
                        if first is None:
                            first = time.monotonic() - t0
                        text += d
                    if ch.get("finish_reason"):
                        finish = ch["finish_reason"]
    return {"text": text, "seconds": time.monotonic() - t0, "first_token_s": first, "usage": usage,
            "finish_reason": finish, "model": got}


async def with_retries(label: str, fn):
    last = None
    for attempt in range(RETRIES + 1):
        try:
            return await fn(), attempt
        except Exception as e:  # noqa: BLE001
            last = e
            print(f"  {label}: attempt {attempt + 1} failed: {type(e).__name__}: {str(e)[:200]}")
            if attempt < RETRIES:
                await asyncio.sleep(2 * (attempt + 1))
    raise RuntimeError(f"{label}: {last}")


def usage_row(u: dict) -> dict:
    det = u.get("prompt_tokens_details") or {}
    return {"input_tokens": int(u.get("prompt_tokens") or 0), "output_tokens": int(u.get("completion_tokens") or 0),
            "cached_tokens": int(det.get("cached_tokens") or 0), "audio_tokens": det.get("audio_tokens"),
            "reasoning_tokens": (u.get("completion_tokens_details") or {}).get("reasoning_tokens")}


async def spark_call(run: str, pipe: str, uid: str, system: str, content) -> dict:
    model = PIPELINES[pipe]
    guard(0.03)
    rep, retries = await with_retries(f"{pipe} {uid} spark", lambda: spark_stream(model, system, content))
    u = usage_row(rep["usage"])
    usd = list_usd(u["input_tokens"], u["output_tokens"])
    VE.log_spend(kind=f"ava:{run}:{pipe}:propose", id=uid, model=rep["model"], effort=EFFORT, api="chat", stream=True,
                 usd=round(usd, 6), secs=round(rep["seconds"], 2), first_token_s=rep["first_token_s"] and round(rep["first_token_s"], 2),
                 **u)
    return {**rep, **u, "usd": usd, "retries": retries}


async def asr_call(run: str, uid: str, wav: bytes, secs: float) -> dict:
    guard(secs / 3600 * ASR_USD_PER_HOUR)
    kw = app_keywords()

    async def go():
        t0 = time.monotonic()
        body = await meta_transcribe(wav, kw)
        return body, time.monotonic() - t0
    (body, took), retries = await with_retries(f"C {uid} asr", go)
    ms = body.get("audioDurationMs") or secs * 1000
    usd = ms / 3_600_000 * ASR_USD_PER_HOUR
    VE.log_spend(kind=f"ava:{run}:C:asr", id=uid, model=ASR_MODEL, usd=round(usd, 6), secs=round(took, 2),
                 audio_ms=ms)
    transcript = (body.get("transcript") or " ".join(t.get("transcript", "") for t in body.get("turns") or [])).strip()
    return {"transcript": transcript, "seconds": took, "usd": usd, "audio_ms": ms, "retries": retries}


async def one(run: str, pipe: str, uid: str) -> dict:
    dst = OUT / run / pipe / f"{uid}.json"
    if dst.exists():
        return json.loads(dst.read_text())
    wav, secs = pcm_wav((WAVS / f"{uid}.wav").read_bytes())
    t0 = time.monotonic()
    rec: dict = {"id": uid, "pipeline": pipe, "model": PIPELINES[pipe], "audio_s": round(secs, 2)}
    if pipe == "C":
        a = await asr_call(run, uid, wav, secs)
        rec["asr"] = a
        rec["transcript"] = a["transcript"]
        if a["transcript"]:
            system, user = text_prompt(a["transcript"])
            rec["spark"] = await spark_call(run, pipe, uid, system, user)
        else:
            rec["spark"] = None
    else:
        system, user = audio_prompt()
        content = [{"type": "text", "text": user},
                   {"type": "input_audio", "input_audio": {"data": base64.b64encode(wav).decode(), "format": "wav"}}]
        rec["spark"] = await spark_call(run, pipe, uid, system, content)
    rec["wall_s"] = time.monotonic() - t0
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(json.dumps(rec, ensure_ascii=False, indent=1))
    return rec


# ---------- scoring ----------

async def score(run: str, pipe: str, rec: dict) -> dict:
    uid = rec["id"]
    r = VE.labels()[VE.base_id(uid)]
    sp = rec.get("spark")
    reply = sp["text"] if sp else '{"none": true}'
    try:
        ans = parse_answer(reply)
        if pipe == "C":
            heard = rec["transcript"]
        else:   # no transcript: the quote check is against the model's own quotes
            ms = ans if isinstance(ans, list) else (ans.get("marks") if isinstance(ans, dict) and "marks" in ans else [ans])
            heard = "\n".join(str(m.get("quote", "")) for m in ms if isinstance(m, dict))
        marks, refused = checked_marks(ans, heard, FACTS)
    except Exception as e:  # noqa: BLE001
        ans, marks, refused = None, [], [f"unparseable: {e}"]
    sc = VE.score_line(VE.base_id(uid), r, marks)
    jud = {"accept": None, "usd": 0.0}
    if not sc["negative"]:
        if marks:
            jtag = f"ava_{run}_{pipe}"
            (VE.OUT / "runs" / jtag).mkdir(parents=True, exist_ok=True)
            guard(0.03)
            jud = await VE.judge(jtag, uid, r["expect"], marks)
            sc["expect_judge"] = jud["accept"]
        else:
            sc["expect_judge"] = False
    sc["line_ok"] = sc["ok"] if sc["negative"] else sc["all_fields"]
    return {"id": uid, "transcript": rec.get("transcript"), "marks": marks, "refused": refused, "answer": ans,
            "score": sc, "wall_s": rec["wall_s"], "audio_s": rec["audio_s"],
            "asr_s": rec.get("asr", {}).get("seconds"), "spark_s": sp and sp["seconds"],
            "first_token_s": sp and sp["first_token_s"], "input_tokens": sp and sp["input_tokens"],
            "output_tokens": sp and sp["output_tokens"], "reasoning_tokens": sp and sp["reasoning_tokens"],
            "cached_tokens": sp and sp["cached_tokens"], "audio_tokens": sp and sp["audio_tokens"],
            "usd": (sp["usd"] if sp else 0.0) + rec.get("asr", {}).get("usd", 0.0), "judge_usd": jud.get("usd", 0.0),
            "judge_shown": jud.get("shown"), "finish_reason": sp and sp["finish_reason"]}


# ---------- run ----------

async def cmd_run(run: str, pipes: list[str], concurrency: int) -> None:
    uids = sorted(p.stem for p in WAVS.glob("v*.wav"))
    assert len(uids) == 40, len(uids)
    jobs = [(p, u) for u in uids for p in pipes]
    random.Random(f"{run}").shuffle(jobs)        # interleaved, so time-of-day load hits every pipeline alike
    sem = asyncio.Semaphore(concurrency)
    streak = {p: 0 for p in pipes}
    dead: set[str] = set()
    recs: dict[str, dict] = {p: {} for p in pipes}
    errors: dict[str, dict] = {p: {} for p in pipes}

    async def go(p, u):
        if p in dead:
            return
        async with sem:
            if p in dead:
                return
            try:
                recs[p][u] = await one(run, p, u)
                streak[p] = 0
                sp = recs[p][u].get("spark") or {}
                print(f"{run} {p} {u}: {recs[p][u]['wall_s']:.1f}s ttft {sp.get('first_token_s')} "
                      f"in {sp.get('input_tokens')} out {sp.get('output_tokens')} {(sp.get('text') or '')[:90]!r}")
            except Exception as e:  # noqa: BLE001
                errors[p][u] = str(e)[:400]
                streak[p] += 1
                print(f"{run} {p} {u}: ERROR {e}")
                if streak[p] > 3:
                    dead.add(p)
                    print(f"STOP pipeline {p}: more than 3 clips in a row failed")
    await asyncio.gather(*(go(p, u) for p, u in jobs))

    res_path = RESULTS / f"audio_vs_asr_{run}.json"
    res = json.loads(res_path.read_text()) if res_path.exists() else {"run": run, "pipelines": {}}
    for p in pipes:
        rows = await asyncio.gather(*(score(run, p, recs[p][u]) for u in sorted(recs[p])))
        res["pipelines"][p] = {"model": PIPELINES[p], "rows": rows, "errors": errors[p], "aborted": p in dead}
    RESULTS.mkdir(exist_ok=True)
    res_path.write_text(json.dumps(res, ensure_ascii=False, indent=1, default=str))
    print(f"this experiment ${my_spent():.4f}; ledger ${VE.spent():.4f}")
    cmd_report()


# ---------- report ----------

def pct(xs: list[float], q: float) -> float:
    xs = sorted(xs)
    k = (len(xs) - 1) * q
    lo = int(k)
    return xs[lo] + (xs[min(lo + 1, len(xs) - 1)] - xs[lo]) * (k - lo)


# Lines whose own words are one of the production prompt's eight worked examples (no hold-out in the app's prompt).
IN_EXAMPLES = {"v02", "v08", "v14", "v18", "v21", "v22", "v25", "v30"}


def summarize(rows: list[dict]) -> dict:
    base = [r for r in rows if not r["id"].endswith("c")]
    ret = [r for r in rows if r["id"].endswith("c")]
    unseen = [r for r in rows if VE.base_id(r["id"]) not in IN_EXAMPLES]
    neg = [r for r in rows if r["score"]["negative"]]
    pos = [r for r in rows if not r["score"]["negative"]]

    def ok(rs):
        return sum(bool(r["score"]["line_ok"]) for r in rs)
    med = lambda k: st.median([r[k] for r in rows if r.get(k) is not None]) if any(r.get(k) is not None for r in rows) else None  # noqa: E731
    walls = [r["wall_s"] for r in rows]
    ttft = [r["first_token_s"] + (r["asr_s"] or 0) for r in rows if r.get("first_token_s") is not None]
    return {
        "n": len(rows), "ok": ok(rows), "ok_base": ok(base), "n_base": len(base), "ok_retake": ok(ret), "n_retake": len(ret),
        "ok_unseen": ok(unseen), "n_unseen": len(unseen),
        "neg_ok": ok(neg), "n_neg": len(neg),
        "judge": sum(bool(r["score"].get("expect_judge")) for r in pos), "n_pos": len(pos),
        "all_and_judge": sum(bool(r["score"].get("all_fields") and r["score"].get("expect_judge")) for r in pos),
        "fields": {f: sum(bool(r["score"].get(f)) for r in pos) for f in ("position", "bar_from", "bar_to", "audience", "kind")},
        "wall_med": st.median(walls) if walls else None, "wall_p95": pct(walls, 0.95) if walls else None,
        "ttft_med": st.median(ttft) if ttft else None, "ttft_p95": pct(ttft, 0.95) if ttft else None,
        "asr_med": med("asr_s"), "spark_med": med("spark_s"),
        "in_med": med("input_tokens"), "out_med": med("output_tokens"), "reason_med": med("reasoning_tokens"),
        "audio_tok_med": med("audio_tokens"), "cached_med": med("cached_tokens"),
        "usd_call": sum(r["usd"] for r in rows) / len(rows) if rows else None, "usd_total": sum(r["usd"] for r in rows),
        "judge_usd": sum(r["judge_usd"] for r in rows),
    }


def failures(rows: list[dict]) -> list[str]:
    out = []
    for r in rows:
        s = r["score"]
        if s["line_ok"]:
            continue
        lab = VE.labels()[VE.base_id(r["id"])]
        if s["negative"]:
            why = "FALSE POSITIVE: " + "; ".join(f"{m['text']} ({m['position']} {m.get('bar_from')}-{m.get('bar_to')}, {m['audience']})" for m in r["marks"])
        elif not s["produced"]:
            why = "no mark" + (f" (refused: {'; '.join(r['refused'])})" if r["refused"] else "")
        else:
            bad = [f for f in ("position", "bar_from", "bar_to", "audience", "kind") if not s[f]]
            got = "; ".join(f"{m['text']} [{m['position']} {m.get('bar_from')}-{m.get('bar_to')} {','.join(m['audience']) if isinstance(m['audience'], list) else m['audience']} {m['kind']}]" for m in r["marks"])
            want = f"{lab['expect']} [{lab['position']} {lab['bar_from'] or None}-{lab['bar_to'] or None} {lab['audience']} {lab['kind']}]"
            why = f"wrong {', '.join(bad)}: got {got}; want {want}"
        heard = f" | heard: {r['transcript']!r}" if r.get("transcript") is not None else ""
        out.append(f"- {r['id']}: {why}{heard}")
    return out


def cmd_report() -> None:
    runs = sorted(RESULTS.glob("audio_vs_asr_r*.json"))
    lines = ["| run | pipeline | model | lines ok /40 | 30 lines | 10 retakes | unseen 30 | rightly refused | stand text (judge) | "
             "all 5 + judge | median s | p95 s | median TTFT s | median in tok | median out tok | median reasoning | $/call | $ total | errors |",
             "|" + "---|" * 19]
    detail = []
    for p_ in runs:
        res = json.loads(p_.read_text())
        for pipe, d in sorted(res["pipelines"].items()):
            s = summarize(d["rows"])
            if not s["n"]:
                lines.append(f"| {res['run']} | {pipe} | {d['model']} | 0 | | | | | | | | | | | | | | | {len(d['errors'])} (aborted) |")
                continue
            lines.append(
                f"| {res['run']} | {pipe} | {d['model']} | {s['ok']}/{s['n']} | {s['ok_base']}/{s['n_base']} | "
                f"{s['ok_retake']}/{s['n_retake']} | {s['ok_unseen']}/{s['n_unseen']} | {s['neg_ok']}/{s['n_neg']} | "
                f"{s['judge']}/{s['n_pos']} | {s['all_and_judge']}/{s['n_pos']} | {s['wall_med']:.2f} | {s['wall_p95']:.2f} | "
                f"{s['ttft_med']:.2f} | {s['in_med']:.0f} | {s['out_med']:.0f} | {s['reason_med'] if s['reason_med'] is not None else '-'} | "
                f"{s['usd_call']:.5f} | {s['usd_total']:.4f} | {len(d['errors'])}{' (aborted)' if d['aborted'] else ''} |")
            extra = f"fields (of {s['n_pos']} instructions): " + ", ".join(f"{k} {v}" for k, v in s["fields"].items())
            if pipe == "C":
                extra += f"; median ASR {s['asr_med']:.2f} s + Spark {s['spark_med']:.2f} s"
            if s["audio_tok_med"] is not None:
                extra += f"; median audio tokens {s['audio_tok_med']}"
            detail.append(f"### {res['run']} {pipe} ({d['model']})\n\n{extra}\n\n" + ("\n".join(failures(d["rows"])) or "- none")
                          + ("\n\nErrors: " + json.dumps(d["errors"]) if d["errors"] else ""))
    text = "\n".join(lines) + "\n\n" + "\n\n".join(detail) + f"\n\nThis experiment's spend (ava:*): ${my_spent():.4f}\n"
    (RESULTS / "audio_vs_asr_tables.md").write_text(text)
    print(text)


async def cmd_probe() -> None:
    rec = await one("probe", "A", "v01")
    print(json.dumps({k: v for k, v in (rec["spark"] or {}).items()}, indent=1, default=str)[:3000])


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("probe")
    r = sub.add_parser("run")
    r.add_argument("--run", required=True)
    r.add_argument("--pipelines", default="A,B,C")
    r.add_argument("--concurrency", type=int, default=4)
    sub.add_parser("report")
    sub.add_parser("prompt")
    a = ap.parse_args()
    if a.cmd == "probe":
        asyncio.run(cmd_probe())
    elif a.cmd == "run":
        asyncio.run(cmd_run(a.run, a.pipelines.split(","), a.concurrency))
    elif a.cmd == "prompt":
        print(audio_prompt()[1])
    else:
        cmd_report()


if __name__ == "__main__":
    main()
