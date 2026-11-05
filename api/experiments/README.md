# Experiments

The measured experiments behind Folio's design decisions. Each folder holds the scripts that ran, the inputs or
ground truth they scored against, and, where one was written, a summary of the result. The numbers, sample sizes
and dates are in the feature doc named in each row (`docs/features/`). Most rows are single runs on a few pages.

Run from `api/`, for example `uv run python -m experiments.voice.voice_eval summary`. Every script that calls a
Meta model logs each call to a spend ledger in its own folder and stops at a cap.

| Folder | What it measured | Feature doc |
|---|---|---|
| `grounding/` | Who places the bars on a page: SAM 3.1 boxes plus Spark, Spark alone, and OpenCV geometry plus Spark labels, scored by tapping every ground-truth bar (the tap test); the score-header read and the piano-cut prototype the librarian was ported from. Pages in `pages/`, truth in `ground_truth.json`, `README.md` has the results and exact prompts | 003, 004, 008, 009 |
| `pageread_speed/` | Page reading at effort minimal against low, with a trimmed answer: time, cost and label agreement | 004-speed-eval |
| `speed_pass/` | The 2026-10-30 speed pass with outputs held fixed: import, part cut, Convert to Digital and the voice call, before and after | 004, 005, 007, 008, 013 |
| `bar_numbers/` | Printed bar numbers read by Spark against the geometric bar count, on 17 pages in 5 books | 004 |
| `landmarks_page/` | The per-page Spark read of printed landmarks (rehearsal marks, tempo words) on scanned pages | 004, 013-v4e-eval |
| `omr/` | Convert to Digital before it was a product step: Audiveris on the OMR box, the measure map, Spark text placement and closed questions, scored against the Open Goldberg ground truth (`goldberg_bga_text_gt.json`) | 005 |
| `engrave/` | Engraving the converted MusicXML for the iPad's page: MuseScore against OpenSheetMusicDisplay, layout and reflow, on Goldberg pages 1 to 5 and Chopin Op. 40 No. 1 p. 25 (`README.md` in each subfolder) | 005 |
| `benchmark/` | The benchmark tool: a corpus manifest with geometry and ground truth, task and model grids, and the Spark 1.2 against 1.3 comparison (`runs/*/results.md`) | 016 |
| `spark12/` | Muse Spark 1.2 against 1.3 on page reading, the convert verifier and the voice call; pools the benchmark runs | 016 |
| `voice/` | The full voice pipeline: Muse Voice Transcribe, then one Spark call, scored against `api/fixtures/voice/script.csv` and `script2.csv` (summaries in `results/*.md`) | 013 |
| `voice_text/` | The second half of the voice pipeline from text: prompt versions v4c to v4f, the messy set and the 100-line set (`set.jsonl` files are the cases) | 013-text-eval, 013-messy-eval, 013-v4e-eval |
| `voice_stream/` | Always-on listening: Meta's realtime recogniser, endpointing and the latency from end of speech to a card | 013-always-on |
| `worker_wake/` | Job pickup latency against hosted Supabase, before and after the Realtime wake | 007 |
| `e2e_night/` | The end-to-end harness: one book at a time through the real chain as the iPad drives it (hosted test project, test accounts, the API and the OMR box) | 018 |

Not in the repository, by design: the spend ledgers (`spend*.jsonl`, `spend*.json`), raw run records (`results/*.json`,
`runs/`, `out/`, `engrave/v2/`), renders and crops that the scripts rebuild, the voice recordings (one person's
voice), and copyrighted editions. A path to one of these in a feature doc names where a local run writes it.
