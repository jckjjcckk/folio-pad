# Demo video: shot list (3:00)

Built from the script of 2026-11-01 in `docs/features/017-demo-and-submission.md` (the exact lines and the model on
screen per shot are there) and build-queue items 9 to 11 (Nov 2 integration and rehearsal run-through, Nov 3
recording and final cut, Nov 4 verification and submission before 9 PM ET). The order: what existed before (nothing),
the problem, the librarian at work, the question it has to ask, parts and Convert, live marks, the conductor's spoken
note, play the parts, the rule behind it all, the close. CK presents on camera in shots 1, 9 and 13.

Markers: **[2 iPads]** needs two signed-in devices in frame or cut together; **[mic]** needs the real iPad
microphone, recorded live, not dubbed.

Devices: **iPad A** is the admin's (CK's iPad Pro 13, signed in as Ada, admin of Hart House, plays viola).
**iPad B** is a player's (signed in as Noor, Violin II). The concerto question (shot 5)
runs in Ada's library on iPad A.

Books:

- **Goldberg** (Bach-Gesellschaft, IMSLP06984): a 5-page cut starting at the first music page, from
  `api/fixtures/pdf/goldberg-bga.pdf`. Imported live in shot 3, plus a copy imported and converted beforehand.
- **Concerto** for the question: Beethoven Piano Concerto 3 test pages 1 to 4 (`beethoven-pc3-fullscore-imslp977417.pdf`)
  or Rachmaninoff Concerto 1 pages 1 to 5. Which book asks reliably must be settled in the Nov 2 rehearsal run
  (the label memory now settles labels the header names, so a question is not guaranteed).
- **Op. 18/1**: Beethoven, String Quartet Op. 18 No. 1, first movement, MusicXML
  (`web/public/fixtures/beethoven-op18no1-mv1.musicxml`, 313 bars), in Hart House with all four parts assigned.

## Shots

Every shot where a model runs live carries a lower-third naming it and an inset of the hosted `usage_events` rows
(model, kind, cost, time), refreshed after the call.

| # | Time | Dur | On screen | Said (short form; exact line in 017) | Device | Book | Fallback |
|---|---|---|---|---|---|---|---|
| 1 | 0:00 | 0:08 | CK on camera beside the stands; "Built Oct 26 to Nov 4, 2026" | "Nothing in Folio existed before this hackathon…" | Camera | None | None needed |
| 2 | 0:08 | 0:10 | Paper parts on four stands; a cut on three parts, not the fourth; a fumbled page turn | "In rehearsal, the parts never quite agree…" | Camera | Printed Op. 18/1 parts | Stills of the stands with the line as a caption |
| 3 | 0:18 | 0:14 | Import a PDF from Files; the blue rope runs; inset `muse-spark-1.3` rows | "I drop in a public-domain scan…" | iPad A | Goldberg, 5 pages | Cut the wait (23.4 s for 5 pages in testing); if it stalls, use the copy imported beforehand |
| 4 | 0:32 | 0:12 | Book sheet: key, meter, length; Open PDF; tap a bar, selected with its number | "Spark never places a bar. We tried SAM 3.1…" | iPad A | Goldberg | The copy imported beforehand |
| 5 | 0:44 | 0:18 | Split by instrument, Piano; yellow rope; the staves question and "Why am I asked?"; tap the staves; "Resuming"; inset recheck rows | "Splitting out the piano, Spark proposes…" | iPad A | Concerto | A split started before recording and left parked, captioned "parked before filming" |
| 6 | 1:02 | 0:08 | Op. 18/1 opened on Violin II on iPad B, the viola part on iPad A | "Each player opens their own part…" | iPad A and B | Op. 18/1 | One iPad, switching parts |
| 7 | 1:10 | 0:10 | Open PDF beside Open Digital; engraved pages; caption "Converted before filming" | "Convert to Digital: Audiveris reads the notes…" | iPad A | Goldberg, converted beforehand | Never run Convert live (114.7 s for 5 pages) |
| 8 | 1:20 | 0:10 | Presence faces; a highlight on iPad A appears on iPad B | "Marks are live…" | **[2 iPads]** A and B | Op. 18/1 | Retake; then the Mac browser signed in as Noor as the second stand |
| 9 | 1:30 | 0:08 | CK on camera holding the voice button; strands gather while he speaks | "Second violins, from forty-two to forty-eight we're cutting that." | **[mic]** iPad A | Op. 18/1 | Retake in a quieter room; then a take recorded before the shoot (proposals wait in the tray) |
| 10 | 1:38 | 0:20 | Proposal card, blue ghost over bars 42 to 48 for Violin II; Accept; inset transcribe row then Spark row | "Folio doesn't listen to you play; it listens to the conductor…" | **[mic]** iPad A | Op. 18/1 | As shot 9 |
| 11 | 1:58 | 0:07 | The cut on the Violin II stand; the cello part unchanged | "It lands only on the stands it was meant for." | **[2 iPads]** B, then A as cello | Op. 18/1 | Violin II stand alone, then the cello part on iPad A |
| 12 | 2:05 | 0:23 | Play the parts: Violin II silenced, pace 80 %, count-in, loop over bars 42 to 48 | "Then practise. Play the parts…" | iPad B, sound on | Op. 18/1 | Record on the web app in a Mac browser |
| 13 | 2:28 | 0:22 | CK on camera; iPad A behind CK with the accepted cut; lower-third naming both models | "Everywhere in Folio, the model proposes and a deterministic check decides…" | Camera | Op. 18/1 | None needed |
| 14 | 2:50 | 0:10 | End card: forte f, Folio, folio.jckjjcckk.com, the repo, "Muse Spark · Muse Voice Transcribe" | "Folio. One score for the whole ensemble." | Title card | None | None needed |

Total: 3:00.

## Props and setup checklist

- [ ] Accounts: Ada (admin, Viola), Lin (Violin I), Noor (Violin II), Inès (Cello) in Hart House, and the pianist's
      personal account. CK signs every device in; budgets reset and the demo group seeded on the hosted project.
- [ ] Books imported beforehand: Op. 18/1 MusicXML imported fresh into Hart House, so it has its landmarks and
      playback files (books imported before 2026-10-30 have no landmarks), all four parts assigned; the Goldberg
      copy imported and converted to Digital; the concerto split started and left parked on its question (shot 6
      fallback); one successful voice take left as a proposal (shot 9 fallback).
- [ ] The concerto book that asks confirmed in the Nov 2 rehearsal run.
- [ ] A clean 5-page Goldberg PDF in Files on iPad A for shot 3.
- [ ] yoga's stable API on main, checked with a test import before the shoot.
- [ ] Mac awake, on power, on the same network.
- [ ] Both iPads on the current build from main, charged, Do Not Disturb on, volume up, same network.
- [ ] Quiet room for shots 9 and 10; the real-iPad mic tested once before the shoot.
- [ ] Printed Op. 18/1 parts and four stands for shot 1.
- [ ] Screen recording on each iPad; a full run-through recorded on Nov 2 as the safety cut.
- [ ] The `usage_events` inset: the hosted Supabase table view (or a saved query) of model, kind, cost and time,
      newest first, recorded from the Mac beside each live call (shots 3, 5, 9, 10). It shows ledger rows, not code.
- [ ] The Op. 18/1 Violin II part has bars 42 to 48 visible on iPad B for shots 10 to 12.
