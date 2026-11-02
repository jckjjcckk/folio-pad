"""Spark 1.2 vs 1.3 on the page read (004, `labels.label_page`): the 004 speed eval's variant B (chat completions,
reasoning_effort minimal, full prompt; the product's first read, PAGE_EFFORT) on the same 13 prepared pages, one model
per process. Each book is read in order like `process_pages`. Results in experiments/spark12/runs/pageread/<model>/.

    cd api && uv run python -m experiments.spark12.pageread muse-spark-1.2
    cd api && uv run python -m experiments.spark12.pageread score
"""
from __future__ import annotations

import asyncio
import json
import statistics as st
import sys
from pathlib import Path

from decimal import Decimal

from app.llm import PRICES

from ..pageread_speed import common, run as R, score as S

HERE = Path(__file__).resolve().parent
OUT = HERE / "runs" / "pageread"
PRICES.setdefault("muse-spark-1.2", (Decimal("1.25"), Decimal("4.25")))  # one Standard price for every Spark version
MODELS = ("muse-spark-1.2", "muse-spark-1.3")


async def go(model: str, run: int = 1) -> None:
    common.MODEL = model
    common.LEDGER = HERE / "spend-pageread.jsonl"
    common.CAP_USD = 1.0
    R.RUNS = OUT / model
    sem = asyncio.Semaphore(4)

    async def one(book):
        async with sem:
            await R.chain("B", run, book)
    await asyncio.gather(*(one(b) for b in common.BOOKS))
    print(f"ledger ${common.spent():.4f}")


def pct(xs, q):
    return S.pct(xs, q)


def score() -> None:
    from app.librarian.labels import PageLabels  # noqa: F401 (labels dicts are plain here)
    for model in MODELS:
        S.RUNS = OUT / model
        recs = S.load()
        lab_ok = lab_n = park = dbt = lm_f = lm_h = lm_i = 0
        fb1, fba, secs, outs, rea, usd, ins = [], [], [], [], [], [], []
        bad = []
        for r in recs:
            secs.append(r["seconds"]); outs.append(r["output_tokens"]); usd.append(r["usd"]); ins.append(r["input_tokens"])
            if r.get("reasoning_tokens") is not None:
                rea.append(r["reasoning_tokens"])
            tag = f"r{r['run']} {r['page']}"
            if not r.get("labels"):
                bad.append(f"{tag} parse fail"); continue
            ok, n, why = S.score_labels(r["page"], r["labels"])
            lab_ok += ok; lab_n += n
            if why:
                bad.append(f"{tag}: " + "; ".join(why))
            park += bool(r.get("question"))
            if r.get("question"):
                bad.append(f"{tag} would park: {r['question'][:140]}")
            fm = S.FIRST.get(r["page"])
            if fm is not None:
                fba.append(r["labels"]["first_measure_number"] == fm)
                if r["first_page"]:
                    fb1.append(r["labels"]["first_measure_number"] == fm)
            dbt += len(r["labels"]["doubtful"])
            if r["page"] in S.LM_TRUTH:
                lm = S.score_landmarks(r["page"], r["labels"]["landmarks"])
                lm_f += lm["found"]; lm_h += lm["half"]; lm_i += len(lm["invented"])
                if lm["invented"]:
                    bad.append(f"{tag} invented {lm['invented']}")
        nruns = len({r["run"] for r in recs})
        print(f"## {model}: {len(recs)} page reads, {nruns} run(s)")
        print(f"labels {lab_ok}/{lab_n}, park {park}, first bar (book's first page) {sum(fb1)}/{len(fb1)}, all {sum(fba)}/{len(fba)}, "
              f"doubted boxes {dbt}, landmarks found {lm_f} (+{lm_h} half) of {20 * nruns}, invented {lm_i}")
        print(f"median {st.median(secs):.1f} s, p95 {pct(secs, .95):.1f} s, median in {st.median(ins):.0f} out {st.median(outs):.0f} "
              f"reasoning {st.median(rea) if rea else '-'}, $/page {sum(usd) / len(usd):.4f}, total ${sum(usd):.4f}")
        for b in bad:
            print("  -", b)


if __name__ == "__main__":
    arg = sys.argv[1]
    if arg == "score":
        score()
    else:
        asyncio.run(go(arg, int(sys.argv[2]) if len(sys.argv) > 2 else 1))
