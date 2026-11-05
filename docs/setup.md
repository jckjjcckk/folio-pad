# Setup

How to run Folio on your own machine, with your own Meta key. Checked against `install.sh`, `api/.env.example`,
`web/.env.example`, `api/app/settings.py` and `supabase/`.

## Repo layout

- `web/`: Vite + React + TypeScript app (Tailwind v4, OpenSheetMusicDisplay, Tone.js, supabase-js). The same build
  runs in Safari and inside the iPad app; `web/ios/` is the Capacitor shell.
- `api/`: FastAPI on Python 3.12 via uv. Owns every model call and every secret. `app/agent/` the agent loop,
  `app/librarian/` the handlers (page reading, part cut, convert, engrave, voice, playback), `scripts/` smoke tests
  and seeds, `tests/`, `experiments/` the measured experiments (`api/experiments/README.md`).
- `supabase/`: `config.toml` for the local stack and `migrations/` (schema, RLS policies, RPCs).
- `deploy/`: Cloudflare Tunnel config and the stable API's service files; `deploy/README.md` is the hosting runbook.
- `docs/`: design and feature notes (`docs/README.md`). `PRODUCT.md` and `DESIGN.md`: product and visual rules.

## Requirements

- Node 20 or newer, npm, git, [uv](https://docs.astral.sh/uv/) (it installs Python 3.12 from `api/.python-version`).
- Docker and the [Supabase CLI](https://supabase.com/docs/guides/cli) for the local database.
- A Meta Model API key with access to `muse-spark-1.3` and `muse-voice-transcribe-1.0`.
- For Convert to Digital and engraving only: an OMR box reachable over ssh (below). Import, bar numbering, part
  cutting, marks, voice notes and playback of digital books work without it.

`./install.sh --check` checks the tools and both env files without changing anything.

## 1. Database

```bash
supabase start          # local Supabase in Docker; applies supabase/migrations
supabase status         # prints the API URL, the publishable key and the secret key
```

The local stack serves the API on `http://127.0.0.1:54321` and Studio on `http://127.0.0.1:54323`. For a hosted
project: `supabase link --project-ref <ref>` once, then `supabase db push`.

## 2. Environment

```bash
cp api/.env.example api/.env
cp web/.env.example web/.env
```

`api/.env` holds the server's secrets and is never shipped to a browser:

| Name | Required | Meaning |
|---|---|---|
| `SUPABASE_URL` | yes | The project URL (`http://127.0.0.1:54321` locally) |
| `SUPABASE_SECRET_KEY` | yes | The secret key (`sb_secret_...`); bypasses RLS, server only |
| `META_API_KEY` | yes | Your Meta Model API key |
| `META_API_BASE_URL` | no | Default `https://api.meta.ai/v1`, written with its `/v1` |
| `META_MODEL` | no | The standard-tier Spark model, default `muse-spark-1.3`; the contributor tier uses the same name plus `-contributor` |
| `PER_USER_BUDGET_USD` | no | Seeds each new account's budget, default 10; the live cap is `profiles.budget_usd` |
| `CORS_ORIGINS` | no | Comma-separated origins allowed to call the API, default `http://localhost:5173` (the example also lists the hosted app and the iPad app's `capacitor://localhost`) |
| `LLM_PROVIDER` | for `install.sh` | `install.sh` refuses to start without it; set `LLM_PROVIDER=meta`. The API itself uses Meta only |
| `PDF_MAX_PAGES` | no | Longest PDF an import reads, default 40 |
| `WORKER` | no | `0` turns the job loop off in this process (default on) |
| `WORKER_CONCURRENCY` | no | Jobs run at once, default 2 |
| `WORKER_WAKE` | no | `0` turns off the Realtime listener that claims new jobs at once (the 2 s poll remains) |
| `OMR_HOST`, `OMR_ROOT` | no | The OMR box's ssh host (default `omr`) and working folder under its home (default `omr/folio`) |
| `OMR_PARALLEL_PAGES` | no | Audiveris processes per convert, one page each, default 5 |
| `MUSESCORE_BIN` | no | MuseScore on the box, default `omr/musescore/squashfs-root/AppRun` under its home |

`web/.env` holds public values only: `VITE_SUPABASE_URL`, `VITE_SUPABASE_PUBLISHABLE_KEY` (`sb_publishable_...`)
and `VITE_API_URL` (default `http://localhost:8000`). To point the dev server at the local stack while `web/.env`
keeps the hosted values, put the same three names in `web/.env.local`; the hosted and iPad builds never read it.

## 3. Install and start

```bash
./install.sh            # checks tools and env, installs deps, starts web on :5173 and the API on :8000
./install.sh --stop     # stops both
```

Or by hand:

```bash
cd web && npm install && npm run dev                                      # LAN-exposed on :5173
cd api && uv sync && uv run uvicorn app.main:app --reload --port 8000     # docs at http://localhost:8000/docs
```

An iPad on the same wifi opens `http://<your Mac's LAN address>:5173`; `install.sh` prints it.

## 4. Accounts

There is no sign-up: accounts are created by hand. Once, against the local stack only:

```bash
cd api && uv run scripts/smoke_local.py
```

It creates the five demo accounts (`admin`, `piano`, `violin1`, `violin2`, `cello` at `muse.test`) with one group and
one score, then checks what RLS lets each of them see and do, and the API's 401, 403 and 402 paths. It sets a random
password for its own checks; to sign in to the local web app, set a password for one of these users in Studio
(Authentication). Never run it against a hosted project.

Every model call is charged to the spend ledger (`usage_events`) against the account's budget and a global cap; a
spent budget answers 402. Each account picks its model tier in the app's account settings (`docs/submission.md`).

## 5. The OMR box (Convert to Digital)

Convert to Digital and engraving run on a separate Linux machine over ssh, so that Audiveris (AGPL) and MuseScore
(GPL) stay separate processes. The API connects with `ssh -o BatchMode=yes <OMR_HOST>`, so the host needs an entry
in `~/.ssh/config` and key authentication. On the box:

- Audiveris 5.11 at `~/.local/bin/audiveris` (or `AUDIVERIS`), with Tesseract language data in `~/omr/tessdata`
  (or `TESSDATA_PREFIX`).
- MuseScore 4.7.5, the AppImage extracted under `~/omr/musescore/` (or `MUSESCORE_BIN`), run headless.
- `python3` and poppler's `pdfinfo`, `pdftoppm`, `pdfseparate` and `pdfunite`. The API copies its box script
  (`api/app/librarian/omr_box.py`, standard library only) on each run.

Notes on the box used for the measurements: `api/experiments/grounding/OMR-BOX.md`.

## 6. Tests

```bash
cd api && uv run pytest        # offline; the model is faked at the transport
cd web && npm test
```

Some API tests (`*_local.py`) need the local stack running and skip otherwise.

## Beyond this machine

- iPad app (Capacitor, TestFlight): `docs/ios.md`.
- Hosting (the web app as a Cloudflare Worker, the API behind a Cloudflare Tunnel, the stable API service):
  `deploy/README.md`; `./install.sh --serve` installs the API and the tunnel as launchd agents on a Mac,
  `--unserve` removes them.
- Test scores to import: `docs/fixtures/`.
