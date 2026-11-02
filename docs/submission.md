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

## What it does, in the demo's order

1. **Import.** A scanned PDF reads itself: OpenCV finds every staff, system and barline; Muse Spark reads what is
   printed (first bar, parts per system, rehearsal marks, title, composer, key, meter).
2. **The librarian asks.** Splitting out a part, the agent meets a staff it cannot place, parks, and asks one
   typed question in musicians' words ("Which staves are the Piano's on page 2, line 2?"). The admin taps the
   staves; the run resumes where it stopped. The answer is kept for the rest of the book.
3. **Parts on every stand.** Each player opens their part, cut from the same pages: bar 112 is bar 112 for all.
4. **Convert to Digital.** Audiveris recognises the notes, Spark adds text only where a glyph confirms it,
   MuseScore engraves the result for the iPad's page.
5. **Marks, live.** A highlight or a cut made on one stand lands on every stand.
6. **The conductor speaks.** The admin holds the voice button: "Second violins, from forty-two to forty-eight
   we're cutting that." Muse Voice Transcribe writes it down, Spark proposes a cut on bars 42 to 48 for
   Violin II, a card and a blue ghost appear; the admin taps Accept and the cut is on the Violin II stand.
7. **Play the parts.** Choose the parts that sound, leave yours out, set the pace, loop.

## Meta models: what each proposes, what decides

Every model Folio runs is a Meta model: **Muse Spark 1.3** (`muse-spark-1.3`) and **Muse Voice Transcribe 1.0**
(`muse-voice-transcribe-1.0`). All calls go through the API; the iPad never calls a model. Every call is charged
to a spend ledger with a per-user and a global cap. Geometry measures; Spark reads text and answers closed
questions; Spark never places a staff or a bar and never judges or re-transcribes a note.

| Feature | Model | What it proposes | What decides |
|---|---|---|---|
| Page reading on import | Muse Spark, effort minimal, low on a doubted page | Per page: the first bar number, the parts on each system, rehearsal marks, title, composer, a brief | OpenCV geometry finds every staff, system and barline and counts the bars. Spark's labels attach to boxes it never moves; a label pointing at no box is dropped |
| Key and meter | Muse Spark, one closed question, low | Sharps or flats, the mode, the time signature, each with a confidence | Only a high-confidence read whose key name agrees with its own count fills the book; anything less is shown as a guess for the owner to confirm |
| Score header | Muse Spark, low | The instruments in score order and the staff boxes each occupies | Reconciled against the geometry's staff boxes: only an answer that uses every box once, in order, sets the staff count for later pages |
| Split by instrument, scanned book | Muse Spark as an agent: labels minimal (fallback low), recheck and agent turns low | Which staves on each system are the wanted part's; then a yes-or-no recheck of each cut | A commit tool: the staves exist, the count matches the header, the crop verifies, the recheck says yes. Three refusals park the run with a typed question. The book's label memory keeps every answer; a human answer outranks a model read |
| Convert to Digital | Muse Spark, minimal | Text, dynamics and tempo words per system; then a yes-or-no render check | Audiveris reads the notes. Spark's text is written only where an Audiveris glyph or a fixed vocabulary confirms it, never a pitch, duration or barline. On a "no" from the render check, Audiveris's reading comes back and the bar is flagged |
| Voice notes | Muse Voice Transcribe (DIARIZATION, keywords from the book), then one Muse Spark call, minimal | The transcript; then marks: kind, bars, audience, stand text, and the quote they come from | The quote must be a verbatim span of the transcript, the bars inside the score, the audience a known part or member. A mark that passes is a proposal; it reaches a stand only when the admin taps Accept |
| Split a Digital book, Play the parts, landmarks | None | n/a | music21 splits the parts and writes each part's MIDI, the bar map and the printed landmarks |

Transcripts of the same take differ between runs (other entrants report about 11 % word drift between identical
runs). That is why no spoken mark lands on a stand on the model's word alone.

**SAM 3.1** was tried first for page layout. It found systems but never a barline: SAM boxes plus Spark scored 10/28
on the tap test (2026-10-27), OpenCV geometry plus Spark labels 28/28. SAM is not in the product.

## The model tier

Each account chooses its tier in the app's account settings. The choice applies to that account's own requests.

- **Standard** (the default): `muse-spark-1.3`. Meta does not train on the content.
- **Contributor**: `muse-spark-1.3-contributor`, about a twelfth of the input price and a twentieth of the output
  price, and Meta may use the content to train future models. Voice Transcribe has no contributor mode, so the tier
  changes only the Spark calls.

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

## What we measured

From `docs/features/*`. Small samples: most rows are one run.

| What | Result | n, date |
|---|---|---|
| Place every bar (tap test) | geometry + Spark 28/28 and 13/13; Spark alone 9/28; SAM 3.1 + Spark 10/28 | 2 pages, n=1, 2026-10-27 |
| Page reading on import | labels 42/42 across 13 pages, $0.0127 a page; 5-page import 23.4 s | 2026-10-30 |
| Part cut, Rachmaninoff Concerto 1 p1-5 | 9/9 right, 0 questions; 39.5 s | 4 runs 2026-10-28; 2026-10-30 |
| Label memory, Cappi Op. 27 No. 2 p8-12 | 1 question and 24/26, then 0 questions and 26/26 on a second run | n=1 each, 2026-11-02 |
| Convert, Goldberg p1-5 | text F1 0.963, $0.22, 114.7 s | n=1, 2026-10-30 |
| Audiveris notes, Goldberg Aria b1-28 | pitch F1 0.972 | n=1, 2026-10-27 |
| Voice, CK's recorded lines | 21/26 all fields right, 7/9 retakes, 23/23 non-instructions silent | one voice, n=1, 2026-10-30 |
| Voice, 100 messy typed lines | 99/100 with score context, 74/100 without | n=2, 2026-10-30 |
| Live marks, four stands | p50 0.47 s, 0 of 20 cuts lost | local stack, 2026-10-28 |

## Limits

- **Scanned books.** Bar numbering and part cutting work on the tested pages; recognising the notes does not always.
  Audiveris drops notes on dense piano and orchestral pages; the librarian flags doubtful bars but does not fix them.
- **One voice.** The voice prompt was tuned on one speaker's recordings. Every voice proposal waits for the admin's
  tap; nothing is applied automatically.
- **Small samples.** Most numbers are single runs on 1 to 13 pages. Realtime latency was measured on the local stack.
- **Not built:** always-on listening, MIDI listening to the player's instrument, piano reduction, notation editing.

## What's next

- **Always-on voice.** Researched, not built: the iPad streams audio through the API to Meta's realtime
  recogniser, one Spark call per spoken turn; estimated about 2.1 s median from end of speech to card, against about
  4.2 s today.
- **The IMSLP dataset run.** Dozens of public-domain PDFs to test import, part cut, Convert and metadata.
- **Metadata normalisation.** Canonical composer, work, catalogue number and movement from the header read, as an
  editable suggestion.
- **MIDI listening.** Follow the player's own instrument over MIDI while the other parts play.

## Video

Three minutes, not yet recorded. The script is in `docs/features/017-demo-and-submission.md`; devices, books and
fallbacks in `docs/demo-shot-list.md`.

## Team and links

- CK Jiang: product, design direction, musical judgement.
- Repo: https://github.com/jckjjcckk/folio-pad
- Product site: https://folio.jckjjcckk.com
- Web app: https://folio-app.jckjjcckk.com
- iPad: TestFlight, build 1 approved
- Support: folio@jckjjcckk.com
- Licence: GNU Affero General Public License, version 3 or later (`LICENSE`).
