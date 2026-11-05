# API scripts

Every script runs from `api/` with `uv run scripts/<name>.py` and reads `api/.env` (pass `--env <path>` where a
script offers it, for example from a worktree without its own `.env`). Scripts that write use the service role and
never sign in with a password.

## Demo and seed tools

These reset fixed accounts on the hosted project to known shelves. They copy finished hosted books (rows and
storage files, every id new) and make no Meta call. The source books are only read. Both seeds are idempotent and
take `--dry-run`, which prints what would be removed and made and writes nothing.

### `seed_demo.py`: the demo video's shelf

```bash
uv run scripts/seed_demo.py --dry-run
uv run scripts/seed_demo.py
```

Wipes only demo@folio.com (its books, the jobs it made, the files under those books) and sets its display name.
It then seeds three books, newest on top:

| Book | State |
|---|---|
| Beethoven, Piano Concerto No. 3 in C minor (PDF, 4 pages) | Piano split parked on page 2, line 1, whose margin prints "Klav." |
| Chopin, Polonaise in C♯ minor, Op. 26 No. 1 (PDF, 4 pages) | Convert to Digital parked on "Does bar 13 match the page?" |
| Beethoven, String Quartet No. 1 in F major, Op. 18 No. 1, I. (Digital, 313 bars) | Finished, with playback for the four parts |

The two parked questions are staged states for the demo video, not live runs. Each parked job carries
`result.demo_resume`, the finished rows prepared from a real run of the same book. `POST /jobs/{id}/answer`
(`app/routes/jobs.py`, `_demo_resume`) writes those rows on that book only and inserts the follow-up job already
`done`, so the book finishes at once with no worker and no Meta call. Only the service role writes jobs, so no user
can set that field; every other job takes the normal resume path. Tests: `tests/test_demo_resume.py`.

- Concerto: either answer finishes the split (7 systems cut, the Piano part on the book, "Klav." remembered as the
  admin's answer).
- Polonaise: either answer makes the book PDF + Digital. "The reading is right" leaves 34 bars to check; "Keep it
  to check" leaves 35. The question renders as the bar card in `web/src/app/StaffQuestion.tsx` (the scan's crop of
  the bar beside the reading's).

A reset takes about 45 s. It removes any book uploaded to demo@folio.com since the last reset.

### `seed_judges.py`: the shared judge account

```bash
uv run scripts/seed_judges.py --dry-run
uv run scripts/seed_judges.py
```

Touches only judges@folio.jckjjcckk.com; its display name and spend are left as they are. It seeds two finished
books and parks no question:

- Beethoven, String Quartet No. 1 in F major, Op. 18 No. 1, I.: Digital, with playable parts (the same source book
  as the demo seed).
- Bach, Minuet in G, BWV Anh. 114: a one-page scan converted to Digital (PDF + Digital, 32 bars, 0 to check),
  copied from the Minuet converted on demo@folio.com's shelf.

The new copies are written before the account's old books are removed, so a rerun can copy the Minuet from the
judge account's own copy when the demo account's original is gone.

### `demo_take.py`: the live convert's record

```bash
uv run scripts/demo_take.py          # start before the upload; ends when the convert ends
uv run scripts/demo_take.py --last   # no watcher ran: the newest book that is not seeded, from its rows
```

Read only. It polls demo@folio.com's new book once a second while a scan is imported and converted, and writes one
JSON record to `api/experiments/e2e_night/demo_take/` (not committed): each note the app showed with the time it was
seen, the job rows, each Spark call with its tokens and cost, and a summary (reading and convert seconds, calls,
USD, bars, flagged bars).

## Other scripts

| Script | What it does |
|---|---|
| `seed_hosted.py` | Seeds the demo world (ensembles, members, books) on the project `api/.env` points at. Idempotent. |
| `import_omr_smoke.py` | Puts the OMR smoke-test outputs into a personal library. |
| `backfill_canonical_instruments.py`, `backfill_landmarks_playback.py`, `backfill_merge_parts.py` | One-off backfills for books made before a feature wrote those fields. |
| `me_hosted.py` | Signs in to the hosted project as a demo account (password typed in the terminal) and calls the API's `/me`. |
| `smoke_agent.py` | Live smoke of the agent loop against Muse Spark. |
| `smoke_local.py`, `smoke_import.py`, `smoke_commit_marks_local.py`, `smoke_voice_local.py` | End-to-end smokes against the local Supabase stack. |
