"""Pool the two 016 benchmark runs of the Spark 1.2 vs 1.3 grid: per task and model, accuracy (the tool's metric),
latency median / p95, tokens, $ per call at list price.   cd api && uv run python -m experiments.spark12.bench_summary"""
from __future__ import annotations

import json
import statistics as st
from collections import defaultdict
from pathlib import Path

from ..benchmark import metrics as M
from ..benchmark.runner import fmt_acc

RUNS = Path(__file__).resolve().parent.parent / "benchmark" / "runs"
NAMES = ("spark12-vs-13-2026-11-01", "spark12-vs-13-r2")


def p95(xs):
    xs = sorted(xs)
    k = (len(xs) - 1) * 0.95
    lo = int(k)
    return xs[lo] + (xs[min(lo + 1, len(xs) - 1)] - xs[lo]) * (k - lo)


def main():
    by = defaultdict(list)
    for n in NAMES:
        for r in json.loads((RUNS / n / "results.json").read_text())["records"].values():
            r["_run"] = n
            by[(r["task"], r["model"], r["effort"])].append(r)
    print("| task | effort | model | calls | accuracy (pooled) | median s | p95 s | median in tok | median out tok | median reasoning tok | $/call | $ total |")
    print("|---|---|---|---|---|---|---|---|---|---|---|---|")
    for key in sorted(by):
        recs = by[key]
        acc = M.aggregate(recs)["accuracy"]
        lat = [r["latency_s"] for r in recs if r.get("latency_s")]
        ins = [sum(a["input_tokens"] for a in r["attempts"]) for r in recs]
        outs = [sum(a["output_tokens"] for a in r["attempts"]) for r in recs]
        rea = [a.get("reasoning_tokens") for r in recs for a in r["attempts"] if a.get("reasoning_tokens") is not None]
        usd = [r["cost_usd"] for r in recs]
        print(f"| {key[0]} | {key[2]} | {key[1]} | {len(recs)} | {fmt_acc(key[0], acc)} | {st.median(lat):.1f} | {p95(lat):.1f} | "
              f"{st.median(ins):.0f} | {st.median(outs):.0f} | {st.median(rea) if rea else '-'} | {sum(usd) / len(usd):.4f} | {sum(usd):.4f} |")
    print()
    for key in sorted(by):
        for r in by[key]:
            s = r.get("score") or {}
            if key[0] == "labels" and s.get("page_ok") == 0:
                print("labels miss:", key[1], r["_run"], r["item"], json.dumps(s)[:300])
            if key[0] == "closed" and s.get("right") == 0:
                print("closed miss:", key[1], r["_run"], r["item"], json.dumps(r.get("answer"))[:160])
            if r.get("status") != "ok":
                print("status", r["status"], key, r["item"])
    models = {r.get("attempts", [{}])[-1].get("model_returned") for v in by.values() for r in v}
    print("models returned:", models)


if __name__ == "__main__":
    main()
