# Folio: submission write-up

Folio is an AI librarian for ensembles on iPads. Meta Global AI Developer Hackathon, Oct 27 to Nov 4, 2026;
entered for the main track and Best Agentic.

Folio does not listen to you play; it listens to the conductor. And everywhere in Folio, the model proposes and a
deterministic check decides.

## The problem

A chamber group rehearses from paper. The parts disagree with the score, the cut is on three stands and not
the fourth, the agreed bowing is in someone's bag. A public-domain scan is easy to find,
but it is a picture: no bar numbers a machine can use, no parts, nowhere to keep what the group decided.

## Who we built it for

CK Jiang has played classical piano for ten years and built Folio for the rehearsal he wants: nobody holds
paper, and the leader's change reaches every stand. A cellist's feedback set two rules. A player's own marks
and the ensemble's stay separate: a fingering never appears on another stand, the leader's cut appears on all.
And repeats, bar numbering and handwriting are what AI gets wrong, so fixing a machine's mark must be as cheap
as making one. The same cellist asked to slow a passage, loop it and hear the other parts: "play the parts".

Two kinds of user:

- **A chamber group or small ensemble.** The admin (in the demo, the quartet's violist) imports the score, splits
  parts, makes cuts and speaks instructions; each player reads their own part on an iPad and receives the
  group's marks.
- **A solo player with a personal library.** A pianist imports a scanned book, converts it to digital, and
  practises with the other parts playing.

Roles live on the membership: an account can be admin of one group and a player in another.

## What it does, in the demo's order

1. **Import.** A scanned PDF reads itself: OpenCV finds every staff, system and barline; Muse Spark reads what is
   printed (first bar, parts per system, rehearsal marks, title, composer, key, meter) and the printed bar
   numbers, which check the geometry's bar count. The demo piece is Bach's Minuet in G, BWV Anh. 114, a one-page
   scan.
2. **The librarian asks.** Splitting out a part, the agent meets a staff it cannot place, parks, and asks one
   typed question in musicians' words. On Beethoven's Piano Concerto No. 3, where the margin prints "Klav."
   (Klavier), it asks "Which staves are the Piano's on page 2, line 1?". The admin taps the staves; the run
   resumes where it stopped. The answer is kept for the rest of the book.
3. **Parts on every stand.** Each player opens their part, cut from the same pages: bar 112 is bar 112 for all.
4. **Convert to Digital.** Audiveris recognises the notes, Spark adds text only where a glyph confirms it,
   MuseScore engraves the result for the iPad's page. The Minuet goes from upload to digital in about 70 s, of
   which the convert is about 35 s: 32 bars, 0 to check, about $0.05 a book.
5. **Marks, live.** A highlight or a cut made on one stand lands on every stand.
6. **The conductor speaks.** The admin holds the voice button: "Violins, from bar twelve, skip twenty to
   twenty-four." Muse Voice Transcribe writes it down, Spark proposes the marks for the violins, a card and a
   blue ghost appear; the admin taps Accept and the marks land only on the violin stands.
7. **Play the parts.** Choose the parts that sound, leave yours out, set the pace, loop.

## Meta models: what each proposes, what decides

Every model Folio runs is a Meta model: **Muse Spark 1.3** (`muse-spark-1.3`) and **Muse Voice Transcribe 1.0**
(`muse-voice-transcribe-1.0`). All calls go through the API; the iPad never calls a model. Every call is charged
to a spend ledger with a per-user and a global cap. Geometry measures; Spark reads text and answers closed
questions; Spark never places a staff or a bar and never judges or re-transcribes a note.

| Feature | Model | What it proposes | What decides |
|---|---|---|---|
| Page reading on import (004) | Muse Spark, effort minimal, low on a doubted page | Per page: the first bar number, the parts on each system, rehearsal marks and printed landmarks, title, composer, difficulty, a brief | OpenCV geometry finds every staff, system and barline and counts the bars. Spark's labels attach to boxes it never moves; a label pointing at no box is dropped |
| Printed bar numbers on import (004) | Muse Spark, effort minimal, one call per page beside the label call; low on a page that disagrees | Every printed bar number on the page, the box of the bar it numbers, and a confidence; never a count | `bar_numbers.compare`: the geometric count decides. Agreement confirms it; a consistent offset re-bases the book only when the opening readings agree over two systems and the admin has not set the first bar; a disagreement flags the bars between two readings as doubtful and keeps the count. The book sheet says "Bars counted from the page" and what the printed numbers said (`process_pages.READ_PRINTED`) |
| Key and meter (004) | Muse Spark, one closed question, low | Sharps or flats counted, the mode, the time signature, each with a confidence | Only a high-confidence read whose key name agrees with its own count fills the book's key and meter; anything less is shown as a best guess for the owner to confirm |
| Score header (003, 008) | Muse Spark, low | The instruments in score order and the staff boxes each occupies | The answer is reconciled against the geometry's staff boxes: only when it uses every box once, in order, does its box count become the staff count, which then drives the staff recovery on every later page |
| Split by instrument, scanned book (008) | Muse Spark as an agent (006): labels minimal (fallback low), recheck and agent turns low | Which staves on each system are the wanted part's; then a yes-or-no recheck of each cut block | A commit tool: the staves exist in the system, the count matches the header, the crop verifies, the recheck says yes. Three refusals park the run with a typed question for the admin. The book's label memory keeps every answer; a human answer outranks a model read and is not asked again |
| Convert to Digital (005) | Muse Spark, minimal | Text, dynamics and tempo words per system; then a yes-or-no render check | Audiveris reads the notes. Spark's text is written only where an Audiveris glyph or a fixed vocabulary confirms it, never a pitch, duration or barline. MuseScore engraves the touched bars; on a "no" from the render check, Audiveris's reading comes back and the bar is flagged |
| Voice notes (013) | Muse Voice Transcribe (DIARIZATION, keywords from the book), then one Muse Spark call, minimal | The transcript; then marks: kind, bars, audience, stand text, and the quote they come from | `checked_marks`: the quote must be a verbatim span of the transcript, the bars inside the score, the audience a known part or member; a place named by a landmark resolves through the book's landmark list. A mark that passes is a proposal, and it reaches a stand only when the admin taps Accept |
| Split a Digital book, Play the parts, landmarks (008, 014, 013) | None | n/a | music21 splits the parts and writes each part's MIDI, the bar map and the printed landmarks at import and convert |

Transcripts of the same take differ between runs (other entrants report about 11 % word drift between identical
runs). That is why no spoken mark lands on a stand on the model's word alone. Spark's confidence on voice was measured (at 0.95 or above,
every proposal was right, 013) and is held for always-on listening; it is not used in push-to-talk. Numbers in
parentheses are feature files in `docs/features/`.

**SAM 3.1** was tried first for page layout. It found systems but never a barline: SAM boxes plus Spark scored 10/28
on the tap test (2026-10-27), OpenCV geometry plus Spark labels 28/28. SAM is not in the product.

## The model tier

Each account chooses its tier in the app's account settings. The choice applies to that account's own requests.

- **Standard** (the default): `muse-spark-1.3`. Meta does not train on the content.
- **Contributor**: `muse-spark-1.3-contributor`, about a twelfth of the input price and a twentieth of the output
  price ($0.10 and $0.20 per million tokens against $1.25 and $4.25), and Meta may use the content to train future
  models. It was about 3.5 times slower on the voice call when measured (013-always-on). Voice Transcribe has no
  contributor mode, so the tier changes only the Spark calls.

Checked on the hosted project on 2026-11-02 with two test accounts: switched to contributor, the next Spark call's
ledger row says `muse-spark-1.3-contributor`; switched back, it says `muse-spark-1.3`. A user can change only their
own tier, never their budget (database row rules, feature 007).

## Best Agentic: the librarian

**A loop that carries the guarantees.** The librarian runs Spark as an agent: one tool call per turn, every result
through a commit tool whose checks the model cannot skip (staff counts, label agreement, geometry). Asked to place
every bar on a page, Spark alone got 9/28; geometry plus Spark labels got 28/28.

**Park and resume.** After three refused commits on one tool the run parks with a typed question, keeping its
history. The answer returns to the same reasoning as the next message: nothing is re-read or re-charged.

**It does not ask twice.** A handler never asks again what the book already settled. What the agent learns ("Klav."
is the Piano; which staves of a line are the piano's) is kept on the book with where it came from
(a person or the model, page, job), consulted before asking, and passed to the model for later pages. A person's
answer outranks any model read.

Measured on a piano split of the Cappi edition of Beethoven's Op. 27 No. 2, pages 8 to 12 (Pianoforte), n=1 each:

| Run | Questions | Lines cut right | Time | Cost |
|---|---|---|---|---|
| No memory | 1 | 24/26 | 237 s | $0.25 |
| With memory, first pass | 2 | 26/26 | 170 s | $0.20 |
| The same split again | 0 | 26/26 | 71 s | $0.10 |

Two caveats. An answered layout applies to any later line with no printed labels and the same staff count, which is
right for this book and could be wrong for a book that changes instruments between lines of the same size. And the
"remembered from page N" note in the question dialog has not yet been seen rendered on a device.

**A speed pass with outputs held fixed** (2026-10-30). Effort minimal where it matched low, with a fallback to low on
a doubtful page; the part cut reads ahead and skips rechecks the memory settled; Audiveris runs page by page in
parallel. Five-page import 35.3 s to 23.4 s; part cut 93.8 s to 39.5 s with the same 9 decisions; Convert 187.8 s to
114.7 s; voice call median 1.83 s to 1.08 s with the same marks.

## Architecture

```
iPad (React PWA inside a Capacitor shell; also the web app in Safari)
  |  sign-in, reads and writes rows under RLS, uploads to Storage, hears changes over Realtime
  v
Supabase: Auth, Postgres (RLS on every table), Storage, Realtime
  ^
  |  service key; claims durable jobs from the jobs table
FastAPI (api/): verifies the user's token, enforces budgets, runs the librarian's handlers
  |-- Meta Model API: Muse Spark 1.3, Muse Voice Transcribe 1.0
  |-- OpenCV page geometry, music21 (part split, MIDI, landmarks)
  '-- OMR box over ssh: Audiveris 5.11 (recognition), MuseScore 4.7.5 headless (engraving, render check)
Cloudflare: the web app as a Worker with static assets; the API behind a Cloudflare Tunnel
```

The iPad calls the API only to start work. Results arrive as row changes. The database is the truth and Realtime
is the notification: clients refetch on reconnect. Three data layers: source (PDF, images, MusicXML),
interpretation (bars, staves, parts, versioned), collaboration (marks, cuts, scribbles, presence). Marks point at
stable measure ids, so re-reading a page keeps everyone's marks.

## What we measured

From `docs/features/*` (the source column names the file); the Minuet row from the demo-piece runs. Small
samples: most rows are one run on a few pages.

| What | Result | n, date | Source |
|---|---|---|---|
| Who places bars: tap every bar on a page | OpenCV geometry + Spark labels 28/28 and 13/13; Spark alone at high effort 9/28; SAM 3.1 + Spark 10/28 | 2 pages, n=1, 2026-10-27 | 003 |
| Page reading on import, effort minimal with a guard | 5-page import 35.3 s to 23.4 s; labels 42/42 across a 13-page corpus, $0.0127 a page | import n=1 before, n=2 after; corpus one run; 2026-10-30 | 004 |
| Printed bar numbers, 17 pages in 5 books | 36/36 numbers read, 0 false disagreements, ~$0.005 a page | 2 runs, 2026-11-02 | 004 |
| Part cut, Rachmaninoff Concerto 1, pages 1 to 5 | 9/9 decisions right, 0 questions; 93.8 s to 39.5 s after the speed pass | 4 runs 2026-10-28; speed pass 2026-10-30 | 008 |
| Label memory, Beethoven Concerto 3, piano part | questions on two pages to 0; 7/7 systems cut | n=1 each, 2026-10-30 | 008, 006 |
| Label memory, Cappi Op. 27 No. 2 p8-12 | 1 question and 24/26, then 0 questions and 26/26 on a second run | n=1 each, 2026-11-02 | 008 |
| Convert, Bach Minuet in G (demo piece, one page) | 32 bars, 0 to check, convert ~35 s, ~70 s upload to digital, ~$0.05 a book | 3 runs, 2026-11-04 | `docs/fixtures/` |
| Convert, Goldberg BGA pages 1 to 5 | text F1 0.963, notes kept by MuseScore 1731/1731 (v2 run); 187.8 s to 114.7 s, $0.22 | n=1, 2026-10-28 and 2026-10-30 | 005 |
| Audiveris pitch accuracy, Goldberg Aria bars 1 to 28 | pitch F1 0.972 against the Open Goldberg ground truth | n=1, 2026-10-27 | 005 |
| Voice: CK's recorded lines | all fields right on 21/26, retakes 7/9, no mark on 23/23 non-instructions; Spark median 1.08 s, $0.0035 a line | one voice, n=1, 2026-10-30 | 013 |
| Voice: 100 messy typed instructions | 99/100 with score context (prompt v4e), 74/100 without; 0/6 false positives | n=2, 2026-10-30 | 013-v4e-eval |
| Live marks to four stands | p50 0.47 s, 0 of 20 cuts lost, missed cut recovered after a reconnect | local stack, 2026-10-28 | 012 |

## Limits

- **Scanned books.** Bar numbering and part cutting work on the tested pages; recognising the notes does not always.
  Audiveris drops notes on dense piano and orchestral pages; the librarian flags doubtful bars but does not fix
  them, and a bar can be wrong without a flag (the demo Minuet's bar 21). Convert to Digital is scoped to piano and
  chamber music, and no chamber-music PDF has been tested.
- **One voice.** The voice prompt was tuned and scored on one speaker's recordings (CK's). A second voice is the
  overfitting check and has not been recorded. A transcript sometimes drops a leading addressee ("Cello, ..."), and
  the mark then goes to the whole group. Every voice proposal waits for the admin's tap; nothing is applied
  automatically.
- **iPad only.** The native app is iPad only; the web app runs in Safari and on a Mac browser. The iPad microphone
  path has not been measured.
- **Small samples.** Most numbers are single runs on 1 to 13 pages. Realtime latency was measured on the local stack,
  not the hosted project.
- **Not built:** always-on listening (researched in 013-always-on), MIDI listening to the player's instrument, piano
  reduction, notation editing.

## What's next

- **Always-on voice.** Researched, not built: the iPad streams audio through the API to Meta's realtime
  recogniser, one Spark call per spoken turn; estimated about 2.1 s median from end of speech to card, against about
  4.2 s today.
- **More scanned editions.** The IMSLP run happened on 2026-11-04: 30 imports and converts of 1 to 3 pages from 12
  public-domain piano PDFs, with no question and no server error. Plain editions converted cleanly (the demo Minuet,
  0 bars to check in 3 of 3 runs); dense or decorated pages left 10 to 40 bars to check, and 2 of the 30 converts
  failed. Next: a flag for a book whose time signature was not read, since its rhythm then goes unchecked.
- **Metadata normalisation.** Canonical composer, work, catalogue number and movement from the header read, as an
  editable suggestion.
- **MIDI listening.** Follow the player's own instrument over MIDI while the other parts play.

## Video

About three minutes. The on-camera convert of the Minuet is a live run with real Meta
calls. The two questions in the video are staged on a demo-only branch, from the product's real question templates:
the split question on Beethoven's Piano Concerto No. 3, and a convert parked on "Does bar 13 match the page?" on
Chopin's Polonaise in C♯ minor, Op. 26 No. 1. The second is a staged state only: the product does not ask about a
doubtful bar during a convert, it flags the bar on the Check screen.

## For the judges

- **Try it on the hosted app.** The shared judge account and its shelf are in the README's [Try it](../README.md#try-it)
  section.
- **What existed before.** Nothing: the repo started on 2026-10-26. The eight commits of that day are setup (repo
  layout, scaffold, install script, design-exploration scaffold and mock data); everything after is hackathon work.
- **The commit history is the build log.** Most commits name the feature they belong to (`013`, `014`, ...), and
  each feature's file in `docs/features/` holds its numbers and decisions.
- **Run it with your own Meta key.** `docs/setup.md`: put the key in `api/.env` as `META_API_KEY`. Every call is
  charged to the local spend ledger, capped per user by `PER_USER_BUDGET_USD`.

## Licence and credits

Copyright 2026 CK Jiang. Folio is free software under the GNU Affero General Public License, version 3 or later
(`LICENSE`): use it, read it, change it, and share your changes under the same terms, including when you run it as a
service.

Folio runs alongside these tools, each under its own licence:

- [Audiveris](https://github.com/Audiveris/audiveris) (AGPL-3.0), optical music recognition, run on the OMR box.
- [MuseScore Studio](https://musescore.org) (GPL-3.0), headless engraving and the render check, run on the OMR box.
- [music21](https://web.mit.edu/music21/), [OpenSheetMusicDisplay](https://opensheetmusicdisplay.org),
  [Tone.js](https://tonejs.github.io) with samples from nbrosowsky/tonejs-instruments (MIT),
  [OpenCV](https://opencv.org), [PyMuPDF](https://pymupdf.readthedocs.io) (AGPL-3.0), [Supabase](https://supabase.com),
  [Capacitor](https://capacitorjs.com).

Test material is public domain or openly licensed: the MusicXML fixtures in `web/public/fixtures/` come from the
music21 corpus; the OMR ground truth is Open Goldberg (CC0); the scanned scores are public-domain editions from
[IMSLP](https://imslp.org). Five are committed: three in `docs/fixtures/` (with their editions, licences and
results) and two editions of Beethoven's Op. 27 No. 2 (Cappi 1802 and Moscheles) in `api/fixtures/imslp/` for the
end-to-end runs; the other scans are kept out of the repo.

## Team and links

- CK Jiang, solo: code, product, design direction, musical judgement. Coding tool: Claude Code. Claude Haiku and Sonnet were run only as benchmark comparators in `api/experiments/benchmark/`, never at runtime.
- Repo: https://github.com/jckjjcckk/folio-pad
- Product site: https://folio.jckjjcckk.com
- Web app: https://folio-app.jckjjcckk.com
- iPad: TestFlight, build 1 approved
- Support: folio@jckjjcckk.com
- Licence: GNU Affero General Public License, version 3 or later (`LICENSE`).
