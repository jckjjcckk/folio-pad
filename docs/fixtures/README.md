# Test scores

Three public-domain scans, cut to their first pages, that Folio reads and converts well. Upload one in the app
(Import, then Convert to Digital) to see the same result. The results are from one overnight run through the
real chain (hosted test project, stable API, the OMR box) on 2026-11-04; "to check" is the number of bars the
librarian flags for a musician to look at after Convert to Digital.

The source PDFs were downloaded from [IMSLP](https://imslp.org) and renamed before the run, so the IMSLP file
numbers (`IMSLPnnnnn`) were not kept and are not recoverable from the files: their metadata carries no source.
Each is an IMSLP scan without a recoverable number. No page carries a Creative Commons or contributor notice.

| File | Pages | Composer, work | Edition | Licence | Folio's result (2026-11-04) |
|---|---|---|---|---|---|
| `bach-minuet-g-bwv-anh114-p1.pdf` | 1 | J. S. Bach (attr.; now given to Christian Petzold), Minuet in G, BWV Anh. 114 | Headed "Die Menuett. I. Joh. Seb. Bach", for piano, page 47 of a collection with the footer "B. B. II."; publisher and year are not printed | Public domain as a pre-1930 edition is likely but not confirmed: the collection and its date could not be identified | 32 bars, 0 to check, in 3 of 3 runs; convert 32.5 to 34.4 s, reading 25 to 33 s. Checked by hand: bar 21 is wrong and not flagged, and four ornaments are dropped. This is the demo piece |
| `schumann-album-fur-die-jugend-op68-p1-4.pdf` | 4 | Robert Schumann, Album für die Jugend, Op. 68: title, blank, No. 1 Melodie, No. 2 Soldatenmarsch | Robert Schumann's Werke für Pianoforte solo, Band I, revised by Alfred Dörffel, fingering by Richard Schmidt, C. F. Peters, Leipzig ("Edition Peters", plate 7000); year not printed | Public domain in Canada and the US: a 19th-century Leipzig edition (the pre-1901 spelling "Abtheilung", "revidirt" dates the printing) | Melodie (p. 3): 20 bars, 3 to check, convert 67.3 s. Soldatenmarsch (p. 4): 32 bars, 4 to check, convert 60.4 s, with about 10 wrong bars the flags miss (a left-hand clef change and dotted rhythms) |
| `clementi-sonatinas-op36-p1-4.pdf` | 4 | Muzio Clementi, Six Sonatinas, Op. 36: title, then Sonatina No. 1 (Spiritoso, Andante, Vivace) | Schirmer's Library of Musical Classics vol. 811, revised and fingered by Louis Köhler, G. Schirmer, New York, copyright 1904 | Public domain in Canada and the US (published 1904; Köhler died 1886) | Sonatina No. 1, first movement (p. 2): 38 bars, 11 to check, convert 57.4 s. Pages 3 to 5 as one book: 143 bars, 110 to check, convert 95.1 s |

Readings (import, bar numbering, labels) took 25 to 34 s a page; no run asked a question.

Two more scans are in `api/fixtures/imslp/`: Beethoven's Sonata Op. 27 No. 2 in the first edition (Cappi, Vienna
1802) and Moscheles' edition, used for the end-to-end and label-memory runs.
