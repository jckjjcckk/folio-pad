"""Spark 1.2 vs 1.3 on the voice-note proposal (013, `transcribe_voice`): the transcript -> marks call, text only (the
audio goes to Muse Voice Transcribe, never to Spark). The app's prompt (`voice_prompt.build_prompt`, via spark_lat's
"app" version), chat completions, reasoning_effort minimal, streamed, 8192 budget: the product's call. The 130-line
text set of 013-text-eval, scored by `voice_text.run.score_case` (code, no judge). Both models interleaved.

    cd api && uv run python -m experiments.spark12.voice call
    cd api && uv run python -m experiments.spark12.voice score
"""
from __future__ import annotations

import asyncio
import json
import random
import statistics as st
import sys
from pathlib import Path

from ..voice_stream import common
from ..voice_stream.spark_lat import build
from ..voice_text import run as VT
from ..voice_text.cases import CASES

HERE = Path(__file__).resolve().parent
OUT = HERE / "runs" / "voice"
MODELS = ("muse-spark-1.2", "muse-spark-1.3")
common.PRICE.setdefault("muse-spark-1.2", (1.25, 0.15, 4.25))  # Meta: one Standard price for every Spark version
common.LEDGER = HERE / "spend-voice.jsonl"
common.BUDGET_USD = 1.5


async def call() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    done = {m: (json.loads((OUT / f"raw_{m}.json").read_text()) if (OUT / f"raw_{m}.json").exists() else {}) for m in MODELS}
    jobs = [(m, c) for c in CASES for m in MODELS if c["id"] not in done[m]]
    random.Random(11).shuffle(jobs)
    sem = asyncio.Semaphore(6)

    async def one(m, c):
        system, user = build("app", c["text"], c["id"])
        async with sem:
            try:
                r = await common.spark_chat(system, user, tag=f"spark12:{m}", uid=c["id"], effort="minimal", model=m)
            except RuntimeError as e:
                print(m, c["id"], "ERROR", e)
                return
        done[m][c["id"]] = {k: r[k] for k in ("text", "seconds", "first_object", "usd", "input_tokens", "cached_tokens",
                                              "output_tokens", "reasoning_tokens")}
    await asyncio.gather(*(one(m, c) for m, c in jobs))
    for m in MODELS:
        (OUT / f"raw_{m}.json").write_text(json.dumps(done[m], ensure_ascii=False, indent=1))
        print(m, len(done[m]), "/", len(CASES))
    print(f"ledger ${common.spent():.4f}")


def score() -> None:
    for m in MODELS:
        raw = json.loads((OUT / f"raw_{m}.json").read_text())
        rows = [VT.score_case(c, raw.get(c["id"])) for c in CASES]
        ins = [r for r in rows if r["instruction"] and not r.get("missing")]
        neg = [r for r in rows if not r["instruction"] and not r.get("missing")]
        fh = [f for r in ins for f in r["field_hits"]]
        secs = [raw[c]["seconds"] for c in raw]
        outs = [raw[c]["output_tokens"] for c in raw]
        rea = [raw[c]["reasoning_tokens"] for c in raw if raw[c].get("reasoning_tokens") is not None]
        ins_t = [raw[c]["input_tokens"] for c in raw]
        usd = [raw[c]["usd"] for c in raw]
        list_usd = [(raw[c]["input_tokens"] * 1.25 + raw[c]["output_tokens"] * 4.25) / 1e6 for c in raw]
        print(f"## {m}: {len(raw)} calls")
        print(f"instructions fully right {sum(r['ok'] for r in ins)}/{len(ins)} (with stand text {sum(r['text_all'] for r in ins)}); "
              f"non-instructions right (no mark) {sum(r['ok'] for r in neg)}/{len(neg)}")
        print("  fields: " + ", ".join(f"{k} {sum(f[k] for f in fh)}/{len(fh)}" for k in ("position", "bars", "audience", "kind", "text", "core")))
        print(f"  false negatives {[r['id'] for r in ins if not r['produced']]}; false positives {[r['id'] for r in neg if not r['ok']]}")
        print(f"  unparseable {[r['id'] for r in rows if any('unparseable' in x for x in (r.get('refused') or []))]}")
        print(f"  median {st.median(secs):.2f} s, p95 {VT.p90(secs) if False else sorted(secs)[round(0.95 * (len(secs) - 1))]:.2f} s; "
              f"median in {st.median(ins_t):.0f} out {st.median(outs):.0f} reasoning {st.median(rea) if rea else '-'}; "
              f"$/call billed-est (cache) {sum(usd) / len(usd):.5f}, at list no cache {sum(list_usd) / len(list_usd):.5f}; total ${sum(usd):.4f}")
        (OUT / f"score_{m}.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1, default=str))
    a = {r["id"]: r for r in json.loads((OUT / f"score_{MODELS[0]}.json").read_text())}
    b = {r["id"]: r for r in json.loads((OUT / f"score_{MODELS[1]}.json").read_text())}
    print("right on 1.2 only:", [k for k in a if a[k].get("ok") and not b[k].get("ok")])
    print("right on 1.3 only:", [k for k in a if b[k].get("ok") and not a[k].get("ok")])


if __name__ == "__main__":
    asyncio.run(call()) if sys.argv[1] == "call" else score()
