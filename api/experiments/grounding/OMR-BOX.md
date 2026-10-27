# OMR benchmark box (`ssh omr`)

Lenovo Yoga, AMD Ryzen 7 4800U (8 cores / 16 threads), 14 GB usable RAM, 468 GB NVMe, Ubuntu 24.04.5 LTS server,
Wi-Fi only, reached as `ck-yoga.local` over mDNS. Throwaway install: everything lives under `/home/ck`, no containers.
Lid switch ignored and all sleep targets masked, so it keeps running with the lid closed. No GPU is used anywhere.

Set up 2026-10-27 from the Mac with `ssh-copy-id -i ~/.ssh/id_ed25519_omr.pub ck@ck-yoga.local`; the Mac's
`~/.ssh/config` has `Host omr` with ControlMaster so repeated commands reuse one connection.

System packages (the only sudo step): git curl rsync unzip build-essential openjdk-21-jre-headless fontconfig
libfreetype6 libxext6 libxrender1 libxtst6 libxi6 libgl1 libglib2.0-0 tesseract-ocr (+eng deu fra ita) poppler-utils
linux-tools-generic. User-level: `uv` 0.13 in `~/.local/bin`.

## Layout

| Path | What |
|---|---|
| `~/muse` | clone of branch `claude/grounding-experiment-e8ae10` (from a git bundle, no GitHub remote) with `api/.env`, `api/fixtures/pdf/`, `docs_offline/` dropped in from `~/muse-data` |
| `~/muse-data` | the copied secrets and fixtures (`api.env`, `fixtures/pdf`, `docs_offline`) |
| `~/omr/audiveris` | Audiveris 5.11.0 (Ubuntu 24.04 `.deb` unpacked with `dpkg -x`, bundled JRE); launcher linked as `~/.local/bin/audiveris` |
| `~/omr/tessdata` | tesseract `eng deu fra ita` traineddata from the `tessdata` repo (legacy+LSTM); Ubuntu's own files are LSTM-only and Audiveris wants legacy mode. Use `TESSDATA_PREFIX=$HOME/omr/tessdata` |
| `~/omr/homr` | venv, Python 3.12, `homr[cpu]` 0.7.0, models downloaded with `homr --init` |
| `~/omr/oemer` | venv, Python 3.12, `oemer` 0.1.8 + onnxruntime |
| `~/omr/zeus` | venv, Python 3.10, `zeus` from GitHub; snapshots in `~/omr/zeus/models/` (`ayce-2026-08-03.model` solo staff, `zeus-grandstaff-lmx-1.0-2024-02-12.model` grand staff) |
| `~/omr/smt` | SMT repo HEAD + venv (Python 3.12, CPU torch 2.14, **transformers pinned to 4.49.0**) |
| `~/omr/smt-2024` | git worktree of SMT at `e2c1133` (2024-09-24), the last commit before the February 2025 decoder rewrite, whose module names (`cross_attention.lk`, `ffNet`) match the September 2024 Hugging Face checkpoints. Run SMT from here with `../smt/.venv`; HEAD silently re-initialises the whole decoder and emits noise |
| `~/omr/transcoda` | Transcoda repo + venv (Python 3.12, CPU torch 2.9.1, `xgrammar` group installed). `pyvips` has no libvips and is only needed for dataset generation |
| `~/omr/eval` | venv, Python 3.12: music21 10.5, musicdiff, huggingface_hub, pillow, numpy, opencv-headless, httpx |
| `~/.cache/huggingface/hub` | `antoniorv6/smt-grandstaff`, `smt-camera-grandstaff`, `smt-string-quartets`, `btrkeks/transcoda-59M-zeroshot-v1` |
| `~/omr/smoke` | smoke-test inputs (the two 150 dpi pages and per-system crops cut from `out/cv-*.json`) and each engine's output |

## Running each engine

```bash
# Audiveris: feed the PDF, not the 150 dpi PNG (interline 10 px is rejected; it wants ~300 dpi)
TESSDATA_PREFIX=$HOME/omr/tessdata audiveris -batch -transcribe -export -save -sheets 1 -output OUT ~/muse/api/fixtures/pdf/goldberg-bga.pdf

# homr: whole page PNG; writes <name>.musicxml, <name>_teaser.png and, with the flag, <name>.txt staff positions
~/omr/homr/.venv/bin/homr --write-staff-positions page.png

# Zeus: one staff or grand-staff image per file
~/omr/zeus/.venv/bin/zeus predict --quiet-tf --model-snapshot ~/omr/zeus/models/zeus-grandstaff-lmx-1.0-2024-02-12.model --output-dir OUT --lmx crop.png

# SMT: one system crop -> **kern (script in ~/omr/smt-2024/smt_run.py: <hf-ref> <image> <out.kern>)
cd ~/omr/smt-2024 && ../smt/.venv/bin/python smt_run.py antoniorv6/smt-grandstaff crop.png out.kern

# Transcoda: whole page -> **kern, writes <image>_pred.krn next to the image
cd ~/omr/transcoda && .venv/bin/python scripts/inference.py --weights ~/.cache/huggingface/hub/models--btrkeks--transcoda-59M-zeroshot-v1/snapshots/*/transcoda-59M-zeroshot-v1.ckpt --image page.png

# our geometry (from the repo)
cd ~/muse/api && uv run experiments/grounding/fallback_cv.py
```

## Smoke test, 2026-10-27 (CPU only, wall clock includes model load)

Ground truth: Goldberg p1 = 6 systems, 28 measures; Rachmaninoff 2-piano p3 = 3 systems of 4 staves, 13 measures.

| Engine | Input | Time | Peak RSS | Result |
|---|---|---|---|---|
| Audiveris 5.11.0 | PDF page 1 (Goldberg) | 47 s | 1.0 GB | `.mxl` with **28 measures**; refuses the 150 dpi PNG ("interline 10 px") |
| Audiveris 5.11.0 | PDF page 3 (Rach) | 67 s | 1.6 GB | `.mxl` with 26 `<measure>` = 2 parts × **13**; no warnings with `TESSDATA_PREFIX=~/omr/tessdata` |
| homr 0.7.0 | Goldberg PNG | 24 s | 1.1 GB | 6 staff systems found, MusicXML with **28 measures** |
| homr 0.7.0 | Rach PNG | 41 s | 1.2 GB | 10 of 12 staves found, MusicXML with 41 `<measure>` (per-staff parts, not comparable without a merge) |
| Transcoda 59M zero-shot | Goldberg PNG (resized 1050×1485) | 79 s (53 s generate) | 1.7 GB | 1864 tokens of two-spine `**kern` in G major, 23 barlines for 28 measures |
| Zeus grandstaff-2024 | Goldberg system crops 1–2 | 15 s for 2 | 0.9 GB | runs, but LMX is off-distribution (7/4, C major) and fails MusicXML decoding; expected per the research note |
| SMT grandstaff (`e2c1133`) | Goldberg system 1 crop | 19 s | 2.1 GB | two-spine `**ekern` with bass/treble clefs, 1 sharp, 7 barlines for 6 measures. From HEAD the decoder is re-initialised and the output is noise |

Takeaways for the benchmark plan: every engine except Legato runs on this box at well under 2 minutes a page, and
the box has 13 GB headroom, so two or three engines can run concurrently. Audiveris needs the PDF or a 300 dpi raster;
everything else takes the 150 dpi PNGs as they are. Measure counts from Audiveris and homr already agree with the
geometry on both pages, which is the first thing the layout tier (A) would measure.
