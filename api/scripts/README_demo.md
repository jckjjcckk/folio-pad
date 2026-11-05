# The demo video's shelf (demo-video branch only)

This branch (`claude/demo-video-178312`) is for the 3-minute video. Never merge it into main, never push it.
It resets demo@folio.com to the shelf `docs_offline/demo-script-v3.md` needs. The two librarian questions in the
script are parked states made by the seed, and each answer finishes its job at once from rows prepared in advance.
Only the on-camera Minuet makes Meta calls.

## Reset (before every iPad pass)

```bash
cd api && uv run scripts/seed_demo.py --dry-run
```

```bash
cd api && uv run scripts/seed_demo.py
```

In a worktree with no `api/.env` of its own, add `--env ~/Documents/muse/api/.env`. A reset takes about 45 s and makes
no Meta calls. It wipes only demo@folio.com: its own books (their rows cascade), the jobs it made, and the files
under those books' folders. It also sets the display name to "CK Jiang". It reads three finished hosted books and
copies them. Their originals are not changed.

| Shelf, top to bottom | What it is | In the script |
|---|---|---|
| Beethoven, Piano Concerto No. 3 in C minor (PDF, 4 pages, 56 bars) | demo1's PC3 PDF. Its Piano split is parked on page 2, line 1, the line printed "Klav." (page 1 prints "Klavier"). Yellow light, "Splitting · needs you" | the split question |
| Chopin, Polonaise in C♯ minor (PDF, 4 pages, 68 bars) | demo1's Ekier Op. 26 No. 1 PDF. Its Convert to Digital is parked on bar 13: the scan prints "sotto voce", the reading has nothing there. Yellow light, "Converting · needs you" | the bar question |
| Beethoven, String Quartet No. 1 in F major (Digital, 313 bars) | Op. 18 No. 1, I., with engraved pages and playback for Violin I, Violin II, Viola and Cello | practice mode, Violin I off |

The shelf heading reads "3 books · 2 need you". The Minuet is not on the shelf.

### The two questions, as the iPad shows them

1. Concerto: tap the book, then the "Splitting out Piano" tile ("Which staves are the Piano's on page 2, line 1?
   · Waiting for you"). The dialog:
   - Head: "Needs you · splitting by instrument · page 2 of 4, first line"
   - Title: **"Which staves are the *Piano*'s on this line?"** (part_cut's own `choose_staves` template)
   - Under the title: "Tap them. The librarian's guess is already chosen." The two Klav. staves are lit and tagged
     "Piano". A "Why am I asked?" fold explains that the margin prints "Klav.", which the header did not give.
   - Buttons: "The Piano isn't on this line" and "Use these staves".

   Either answer finishes the split: 7 systems cut, the Piano part on the book, and "Klav. → Piano" stored in the
   book's memory as the admin's answer.
2. Polonaise: tap the book, then the "Converting to Digital" tile ("Does bar 13 match the page? · Waiting for you").
   The dialog:
   - Head: "Needs you · converting to Digital · page 1 of 4, bar 13"
   - Title: **"Does bar 13 match the page?"**
   - Under the title: "The page prints "sotto voce" over this bar. The reading has no marking there."
   - Two crops of bar 13 side by side: "On the page" (the scan) and "What the librarian read" (the engraved
     reading).
   - Note: "Nothing is rewritten either way. A bar kept to check stays on the Check list, with the page beside it."
   - Buttons: "Keep it to check" and "The reading is right".

   Either answer finishes the convert: the book becomes PDF + Digital. "The reading is right" leaves 34 bars to
   check; "Keep it to check" leaves 35.

After both answers the shelf reads "3 books", with no yellow light. That is the "both finished in the background"
shot. To do another take, run the reset again.

## What must be on the iPad

- **The Minuet PDF**, ready for the live upload: `api/fixtures/demo/minuet-g-bwv-anh114-ed3-p1.pdf`. It is in the
  main checkout and is not committed. AirDrop it to the iPad and save it in Files, where the Import picker can find
  it. It has one page, converts in about 35 s, and gives 32 bars with 0 to check.
- **This branch's web build.** The bar question is a new card in `web/src/app/StaffQuestion.tsx`. Main's build would
  open it as the wrong dialog ("Which parts are on page 1?"). Build the app from this branch (`npm run build`, then
  `npx cap sync ios` and Xcode), or deploy this branch's bundle to the web app the iPad opens.
- Signed in as demo@folio.com (CK signs in; agents use a service-role magic link, never the password).

## The API: main's does not suffice for the answers

The only API change on this branch is in `api/app/routes/jobs.py`. `POST /jobs/{id}/answer` checks for a parked
job whose `result.demo_resume` holds prepared rows. Only the service role can write jobs, so only the seed can set
that field. For such a job, the route writes the rows (sources, parts, scores and interpretations, on that book
only) and inserts the follow-up job already `done`. Every other job takes main's path unchanged, the live Minuet
convert included. Tests: `tests/test_demo_resume.py`; the full suite gives 590 passed.

On main's API, the same answers would queue real resumes on the yoga worker. That means Meta calls on a fake state,
and the split resume could fail or cut again. So for the take, the API that the iPad calls must run this branch.
Deploying it is CK's job:

- **Recommended:** check out this branch in the stable checkout on yoga for the shoot, restart folio-api-stable,
  then go back to main afterwards. The worker and the convert are main's code at 960ef7f.
- Alternative: keep yoga on main and run this branch's API on the Mac with `WORKER=0`, so it serves the answers and
  claims no jobs. Point the iPad's build at that API. Yoga's worker still runs the Minuet, because jobs share the
  hosted queue. This needs the Mac reachable from the iPad (LAN or tunnel) and that origin in `CORS_ORIGINS`.

## The live convert's job log (for the video build)

Start the watcher before the upload. It ends by itself when the convert ends:

```bash
cd api && uv run scripts/demo_take.py
```

It is read-only and polls once a second. The record lands in
`api/experiments/e2e_night/demo_take/<utc>-<title>.json`, uncommitted like the other run folders. It has the same
shape as `api/experiments/e2e_night/imslp_1104/<cut>.json`:

- `polls[import_pdf|process_pages|omr_convert]`: each note the iPad showed, with `seen_utc`
- `jobs[].row`: the full job row, including `result.agent` / `result.note`
- `jobs[].usage_events`: each Spark call with the time it returned, tokens and cost
- `sources`, `score`, and a `summary` (reading_s, convert_s, calls, usd, bars, flagged)

The loop panel is paced from these. If no watcher ran, `uv run scripts/demo_take.py --last` writes the record of the
newest unseeded book from its rows, without `polls`. For the timeline format, see
`api/experiments/e2e_night/goldberg_timing/run1-timeline.md`.

## Checked on 2026-11-04 (hosted, this branch's web on :5175 and API on :8010 with WORKER=0)

Sign-in was a service-role magic link. Both yellow lights showed and both questions rendered as described above.
Both answers flipped their jobs to `done`: the concerto got its 7-strip Piano part and the Klav. memory, and the
polonaise got its Digital source and engravings. demo@folio.com logged 0 usage events. The quartet opens on the
stand, and "Play the parts" lists Violin I, Violin II, Viola and Cello, each "Sounding". The reset was run 3 times
and each run returned the same shelf.
