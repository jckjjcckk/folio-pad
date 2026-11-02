# Backlog: known limits we are not fixing during the hackathon

Honest list, kept so the submission can say what Folio does not do yet.

- **Done 2026-11-02: join codes have a guess limit.** `POST /ensembles/join` allows 10 wrong codes per account and 30
  per address in 10 minutes, then 429 with `Retry-After`. The count is in the API process's memory (one process on
  yoga; a restart forgets it). Migration `20261102120000` closes the direct `join_ensemble` RPC; it is not on hosted
  yet (after yoga serves the route). Codes still never expire. Feature 001.
- **Done 2026-11-02: deleting a group removes its files.** `DELETE /ensembles/{id}` removes the files of the group's
  own books after the rows go; books shared by reference stay with their owner; `?dry_run=true` lists what would go.
  Deleting through the RPC directly, or deleting one book, still leaves its files. Feature 001.
- **C-clef misreads when splitting a single choir voice.** Cutting one voice alone (Soprano without Alto) makes
  the recheck ask about alto/tenor C clefs about three times in five pages; pairs of voices cut cleanly. Fix later:
  trust by-order labels on a full system, or a glyph-level clef reader (feature 008).
- **PyMuPDF is AGPL-3.** It rasterizes PDFs for the page reader. Fine while the repo is public and the source is
  available to users; a closed or commercial build would need pypdfium2 (BSD/Apache) instead.
- **Fine-tuning a transcription by hand.** Doubtful bars are listed and the music is shown as read; no bar editor.
- **Per-page rescan** of an unreadable page: button only, not wired, unless the UI branch found it cheap.
- **Voice (feature 013)**: rehearsal speech to actions with Muse Voice Transcribe; script written, no audio, no handler.
