"""Spark 1.2 vs 1.3 on the render proofreading question (005 omr_verify, VERIFY_RENDER_EFFORT minimal): the 29 Goldberg
p1-5 pair images the speed pass dumped (scan system above our engraving), the app's prompt and system through
`ask.ask_model` (minimal -> chat completions), 2 runs per model. Reference: the speed pass's 1.3 replay (2 low + 2
minimal runs, copied to runs/verify_pairs_a_replay.json). No hand GT: agreement with the 1.3 majority is reported.

    cd api && uv run python -m experiments.spark12.verify call
    cd api && uv run python -m experiments.spark12.verify score
"""
from __future__ import annotations

import asyncio
import base64
import json
import random
import statistics as st
import sys
import time
from decimal import Decimal
from pathlib import Path

from app.librarian.ask import ask_model
from app.librarian.omr_verify import VERIFY_RENDER_PROMPT, VERIFY_RENDER_SYSTEM, _same
from app.llm import PRICES, _client

HERE = Path(__file__).resolve().parent
DUMP = HERE / "runs" / "verify_pairs_a"
OUT = HERE / "runs" / "verify_spark12.json"
REF = HERE / "runs" / "verify_pairs_a_replay.json"
LEDGER = HERE / "spend-verify.jsonl"
CAP = 0.6
MODELS = ("muse-spark-1.2", "muse-spark-1.3")
RUNS = 2
PRICES.setdefault("muse-spark-1.2", (Decimal("1.25"), Decimal("4.25")))


class Ctx:
    def __init__(self, key: str):
        self.key, self.usd, self.tok = key, 0.0, []

    def charge(self, c):
        self.usd += float(c.cost_usd)
        self.tok.append((c.input_tokens, c.output_tokens, c.model))
        with LEDGER.open("a") as f:
            f.write(json.dumps({"id": self.key, "model": c.model, "usd": float(c.cost_usd), "input_tokens": c.input_tokens,
                                "output_tokens": c.output_tokens}) + "\n")

    png_b64 = staticmethod(lambda b: base64.b64encode(b).decode())


def spent() -> float:
    return sum(json.loads(l)["usd"] for l in LEDGER.read_text().splitlines() if l.strip()) if LEDGER.exists() else 0.0


async def call() -> None:
    done = json.loads(OUT.read_text()) if OUT.exists() else {}
    items = sorted(DUMP.glob("*.json"))
    client = _client("meta")
    sem = asyncio.Semaphore(8)
    jobs = [(f, m, r) for f in items for m in MODELS for r in range(1, RUNS + 1) if f"{f.stem}|{m}|{r}" not in done]
    random.Random(5).shuffle(jobs)

    async def one(f, m, r):
        key = f"{f.stem}|{m}|{r}"
        if spent() + 0.02 > CAP:
            print("cap"); return
        meta = json.loads(f.read_text())
        png = f.with_suffix(".png").read_bytes()
        prompt = VERIFY_RENDER_PROMPT.format(first=meta["first"], last=meta["last"])
        ctx = Ctx(key)
        async with sem:
            t0 = time.monotonic()
            try:
                ans = await ask_model(ctx, client, m, prompt, png, max_tokens=8000, effort="minimal", retries=1, system=VERIFY_RENDER_SYSTEM)
            except Exception as e:  # noqa: BLE001
                done[key] = {"error": f"{type(e).__name__}: {str(e)[:200]}", "usd": ctx.usd}
                return
            secs = time.monotonic() - t0
        same, reason, named = _same(ans, meta["numbers"])
        done[key] = {"same": same, "named": named, "reason": reason, "secs": round(secs, 2), "usd": ctx.usd, "api": ans.get("_api"),
                     "input_tokens": sum(t[0] for t in ctx.tok), "output_tokens": sum(t[1] for t in ctx.tok),
                     "model_returned": ctx.tok[-1][2] if ctx.tok else None, "attempts": len(ctx.tok)}
    await asyncio.gather(*(one(*j) for j in jobs))
    OUT.write_text(json.dumps(done, indent=1))
    print(f"{len(done)} records; ledger ${spent():.4f}")


def score() -> None:
    done = json.loads(OUT.read_text())
    ref = json.loads(REF.read_text())
    systems = sorted({k.split("|")[0] for k in done}, key=lambda s: (int(s.split("-")[0][1:]), int(s.split("sys")[1])))
    # reference verdict: majority of the speed pass's four 1.3 runs (2 low, 2 minimal); ties = None
    refv = {}
    for s in systems:
        vs = [ref[k]["same"] for k in ref if k.split("|")[0] == s]
        yes = sum(v is True for v in vs)
        refv[s] = True if yes * 2 > len(vs) else (False if yes * 2 < len(vs) else None)
    print("reference (speed-pass 1.3 majority): 'no' on", [s for s in systems if refv[s] is False], "ties", [s for s in systems if refv[s] is None])
    for m in MODELS:
        recs = [done[k] for k in done if k.split("|")[1] == m and "error" in done[k]]
        ok = {k: v for k, v in done.items() if k.split("|")[1] == m and "error" not in v}
        secs = [v["secs"] for v in ok.values()]
        outs = [v["output_tokens"] for v in ok.values()]
        ins = [v["input_tokens"] for v in ok.values()]
        usd = [v["usd"] for v in ok.values()]
        agree = sum(1 for k, v in ok.items() if refv[k.split("|")[0]] is not None and v["same"] == refv[k.split("|")[0]])
        n_ref = sum(1 for k in ok if refv[k.split("|")[0]] is not None)
        stable = sum(1 for s in systems if len({done.get(f"{s}|{m}|{r}", {}).get("same") for r in range(1, RUNS + 1)}) == 1)
        nos = [(k.split("|")[0], k.split("|")[2], v["named"], v["reason"][:90]) for k, v in ok.items() if v["same"] is False]
        unparsed = sum(1 for v in ok.values() if v["same"] is None)
        print(f"## {m}: {len(ok)} calls, {len(recs)} errors, {unparsed} without a yes/no")
        print(f"agree with 1.3 reference {agree}/{n_ref}; runs agree with each other on {stable}/{len(systems)} systems; 'no' answers {len(nos)}")
        print(f"median {st.median(secs):.2f} s, p95 {sorted(secs)[round(0.95 * (len(secs) - 1))]:.2f} s; median in {st.median(ins):.0f} "
              f"out {st.median(outs):.0f}; $/call {sum(usd) / len(usd):.5f}; total ${sum(usd):.4f}; models {sorted({v['model_returned'] for v in ok.values()})}")
        for n in sorted(nos):
            print("   no:", n)
        for k, v in done.items():
            if k.split("|")[1] == m and "error" in v:
                print("   error:", k, v["error"])


if __name__ == "__main__":
    asyncio.run(call()) if sys.argv[1] == "call" else score()
