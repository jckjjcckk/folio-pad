# 017 Demo plan and hackathon submission

Status: script of 2026-11-01 written; nothing recorded; web app and stable API live | Meta models: Muse Spark 1.3 (librarian labels, part cut, voice proposals) and Muse Voice Transcribe (spoken notes) on screen; SAM 3.1 named only as tried first (it lost the tap test to OpenCV geometry, 003) and is not in the product.

## What the judges see

Rubric: Impact 30, Use of Meta AI tooling 25, Technical depth 20, Demo 25. Stage one is pass or fail on
using Meta models. Three-minute video, public repo, new work only; stage three: the top 5 per track, judges
watch the videos live. Bonus prizes: Best Agentic ($5K, autonomy, effectiveness, practical usefulness), Best
Creative with Muse Image or Wonder ($5K), Best Open-Weight ($10K), Most Viral (post on X). Submission due
2026-11-04, 9 PM ET.

The claim (000 positioning): a mid-size model made trustworthy on a hard visual task by designing the loop;
same accuracy at a tenth of the cost; both numbers published, Claude through the same harness.

## Script (2026-11-01, supersedes the 2026-10-26 table below)

Three minutes, shot by shot, against the organisers' rules (Discord, verified the week of 2026-11-01): at most 3:00,
open with one line on what existed before Oct 26, live Meta model calls visible on screen, say where each model is
used, no code walkthrough, no slides, a human presenter. CK presents: on camera in shots 1, 9 and 13, his voice over
the iPads elsewhere. Only what the product does today (progress.md, 2026-10-31): import, labels, the librarian asks,
parts on stands, Convert to Digital, marks live, voice notes, Play the parts with loop and pace. Devices, books, props
and fallbacks: `docs/demo-shot-list.md`.

How a live call is shown: while a model runs, a lower-third names it ("Muse Spark", "Muse Voice Transcribe") and a
small inset shows the hosted `usage_events` rows arriving (model, kind, cost, time; Supabase table view, newest
first, refreshed after the call). That is the call's own ledger row, not code. A caption says so when a result was
made before filming (Convert, a parked question).

Two framing lines CK wants said: shot 10 ("Folio doesn't listen to you play; it listens to the conductor") and
shot 13 ("the model proposes and a deterministic check decides"). SAM 3.1 appears once, in shot 4, as tried first.

| # | Time | On screen | Said (exact) | Meta model on screen |
|---|---|---|---|---|
| 1 | 0:00-0:08 | CK on camera beside four music stands, iPad A in hand. Lower-third: "Built Oct 26 to Nov 4, 2026" | "Nothing in Folio existed before this hackathon. The repo started on October twenty-sixth, and its commit history is the build log." | None |
| 2 | 0:08-0:18 | Paper parts on the four stands; a cut pencilled on three parts and not the fourth; a fumbled page turn | "In rehearsal, the parts never quite agree: the cut is on three stands and not the fourth. Folio is a librarian for the whole ensemble, on iPads." | None |
| 3 | 0:18-0:32 | iPad A, the Shelf: import a 5-page Goldberg PDF from Files; the card's blue rope runs while the pages are read. Inset: `muse-spark-1.3` rows arrive | "I drop in a public-domain scan. Geometry finds every staff and barline; Muse Spark reads what is printed: the first bar number, the parts, the title, the key." | **Muse Spark** (live: page labels, key and meter) |
| 4 | 0:32-0:44 | iPad A: the book sheet (key, meter, length); Open PDF; tap a bar and it is selected with its number | "Spark never places a bar. We tried SAM 3.1 for that first, and plain OpenCV geometry beat it. Spark proposes the labels; the geometry's count decides the numbers." | Muse Spark (labels from shot 3) |
| 5 | 0:44-1:02 | iPad A, the concerto: Split by instrument, Piano; the rope turns yellow; the question with numbered staves and "Why am I asked?"; CK taps the staves; "Resuming". Inset: the recheck's `muse-spark-1.3` rows | "Splitting out the piano, Spark proposes which staves are its. A check it cannot skip, the header's staff count and a yes-or-no recheck of each cut, refuses it, so the librarian stops and asks me. The answer is kept for the rest of the book." | **Muse Spark** (live: part cut agent and recheck; caption "parked before filming" if the fallback is used) |
| 6 | 1:02-1:10 | iPad B (Noor, Violin II) opens Op. 18/1 on her part; iPad A shows the viola part beside it | "Each player opens their own part, cut from the same pages. Bar one-twelve is bar one-twelve on every stand." | None (a Digital book is split by music21) |
| 7 | 1:10-1:20 | iPad A: the Goldberg copy, Open PDF beside Open Digital, the engraved pages. Caption: "Converted before filming" | "Convert to Digital: Audiveris reads the notes, Spark adds words only where a printed glyph confirms them, and MuseScore engraves the page." | Muse Spark (text reread and render check, ran before filming) |
| 8 | 1:20-1:30 | **Both iPads**, Op. 18/1, presence faces: CK highlights bars on iPad A and the mark appears on iPad B | "Marks are live. One made on my stand reaches every stand in about half a second." | None (Supabase Realtime) |
| 9 | 1:30-1:38 | CK on camera as the leader, holding iPad A's voice button; the strands gather into one string while he speaks. Lower-third: "Muse Voice Transcribe" | "Second violins, from forty-two to forty-eight we're cutting that." (live, into the iPad microphone) | **Muse Voice Transcribe** (live) |
| 10 | 1:38-1:58 | iPad A: the proposal card and the blue ghost over bars 42 to 48 for Violin II; CK taps Accept. Inset: a `muse-voice-transcribe-1.0` row, then a `muse-spark-1.3` row | "Folio doesn't listen to you play; it listens to the conductor. Voice Transcribe writes down what I said, Spark proposes the mark, and a check decides whether it may stand: the quote word for word in the transcript, the bars in the book, the part in the group. Then I accept it." | **Muse Voice Transcribe**, then **Muse Spark** (live) |
| 11 | 1:58-2:05 | iPad B: the cut lands on Violin II; then the cello part on iPad A, unchanged | "It lands only on the stands it was meant for." | None |
| 12 | 2:05-2:28 | iPad B, sound on: the Stand's "…" menu, Play the parts; Violin II silenced, pace 80 %, a bar of count-in, a loop over bars 42 to 48; the bar highlight moves | "Then practise. Play the parts: leave your own part out, slow it to eighty percent, loop the passage. The parts and the bar map come from music21 when the book is imported; no model guesses a note." | None (music21 and Tone.js) |
| 13 | 2:28-2:50 | CK on camera, iPad A on the stand behind CK showing the accepted cut | "Everywhere in Folio, the model proposes and a deterministic check decides: the bar map, music21, a word-for-word check against the transcript, or a question to a person. Voice Transcribe can hear the same take differently from one run to the next. That is why nothing lands on a stand on the model's word alone." | Muse Spark and Muse Voice Transcribe named in a lower-third |
| 14 | 2:50-3:00 | End card on iPad A's screen recording: the forte f, "Folio", folio.jckjjcckk.com, the repo, "Muse Spark · Muse Voice Transcribe" | "Folio. One score for the whole ensemble." | Both named on the card |

Total 3:00; about 360 spoken words, near 120 a minute, so the iPad waits can breathe. Shot 13's "confidence
threshold" means the key and meter read (a guess below high confidence is shown, never filled in) and the page read's
fall-back on a doubted page; push-to-talk voice has no threshold today: every proposal that passes the check waits for
the leader's Accept.

The tables below are kept for the record.

## Demo script (revised 2026-10-26, supersedes the first version)

| Time | Scene | Proves |
|---|---|---|
| 0:00 to 0:20 | A rehearsal goes wrong because parts disagree | Real problem |
| 0:20 to 0:55 | Folio imports and prepares the score (Path B photos → pages, parts, difficulty) | Intelligent automation (OpenCV geometry + Spark) |
| 0:55 to 1:25 | The agent detects an ambiguous staff, asks the admin, resolves it, continues | Distinctive Meta AI use, honest |
| 1:25 to 2:15 | Admin makes a cut and speaks an instruction; confirms the proposal; players' stands update | The wow moment (Realtime + Voice Transcribe + Spark) |
| 2:15 to 2:40 | Pianist practises the corrected passage: loop, tempo, other parts | Continuing usefulness |
| 2:40 to 3:00 | The agent's log, the finished score, the product promise, the name | Credibility and impact |

Demo fixture: Beethoven Op. 18/1 (MusicXML, Path A) for the ensemble, plus one or two scanned Goldberg pages
for the Path B and failure moments. Orchestral scores are not in the video. The one deliberate realistic
failure (ambiguous staff assignment, the agent asks, continues) is more credible than an infallible model.
First version (for the record): 0:00 the problem; 0:30 admin drops a PDF; 1:15 invite, assign parts, four
iPads light up; 1:40 rehearsal session with a cut and a spoken note; 2:20 pianist practice with the Casio;
2:50 name. Admin carries the video; pianist gets the last 30 s. Needs 2+ iPads, the Casio, ideally a small
real ensemble or UofT Faculty of Music contacts.

## Deployment (week one, not urgent)

- Web at `https://folio.jckjjcckk.com`: Cloudflare Pages, root `web`, build `npm run build`, output `dist`,
  env `VITE_*`, custom domain on CK's zone (subdomain, not a path: PWA scope, Vite base, Pages domains and
  Supabase redirects all favour a clean origin).
- API at `https://folio-api-dev.jckjjcckk.com` through CK's named Cloudflare tunnel (`macbook_pro_m4`, inactive
  today; `zephyr server` healthy) to the Mac (Casio and OMR live there); Railway later if wanted. Set
  `CORS_ORIGINS` to the web origin, `VITE_API_URL` to the API origin, add `https://folio.jckjjcckk.com/**` to
  the Supabase redirect URLs.
- Quick tunnel for phone access meanwhile: `cloudflared tunnel --url http://localhost:5173` (random
  trycloudflare URL, allowed by `web/vite.config.ts`).
- Modal credits only if CPU OMR turns out too slow.

## Submission checklist

- README: the repo started on Oct 26 with nothing pre-existing (the eight setup-only commits of that day: layout,
  scaffold, install script, exploration scaffold and mock data), which Meta model does what and which check decides
  (from the handler docstrings), how to run with a judge's own Meta key, the model tier. The video says the same
  (shot 1). Done 2026-11-01, with a LICENSE (all rights reserved, readable and runnable for judging).
- Rename the GitHub repo to Folio before the submission form (GitHub redirects the old URL; then
  `git remote set-url origin ...`).
- Build queue: Nov 2 integration, iPad testing, demo rehearsal (full run-through recorded); Nov 3 reliability,
  recording, README, submission draft (final video cut); Nov 4 final verification, submit before 9 PM ET,
  post on X.
- Public repo from day 0; push only when CK says.

## Next steps

1. Complete usable demo by Nov 1, then refine.
2. Deploy, PWA install on the iPads, record.
