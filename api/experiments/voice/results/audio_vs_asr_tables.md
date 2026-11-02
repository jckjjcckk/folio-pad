| run | pipeline | model | lines ok /40 | 30 lines | 10 retakes | unseen 30 | rightly refused | stand text (judge) | all 5 + judge | median s | p95 s | median TTFT s | median in tok | median out tok | median reasoning | $/call | $ total | errors |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| r1 | A | muse-spark-1.2 | 32/40 | 25/30 | 7/10 | 22/30 | 5/5 | 28/35 | 21/35 | 1.87 | 3.46 | 1.80 | 2154 | 412 | 340.0 | 0.00470 | 0.1880 | 0 |
| r1 | B | muse-spark-1.3 | 32/40 | 25/30 | 7/10 | 22/30 | 5/5 | 28/35 | 23/35 | 3.79 | 5.61 | 3.50 | 2154 | 392 | 311.0 | 0.00448 | 0.1790 | 0 |
| r1 | C | muse-spark-1.3 | 33/40 | 26/30 | 7/10 | 23/30 | 5/5 | 30/35 | 24/35 | 4.41 | 6.69 | 3.98 | 2070 | 297 | 204.5 | 0.00429 | 0.1716 | 0 |
| r2 | A | muse-spark-1.2 | 31/40 | 24/30 | 7/10 | 21/30 | 5/5 | 30/35 | 23/35 | 1.72 | 3.24 | 1.58 | 2154 | 374 | 333.5 | 0.00457 | 0.1827 | 0 |
| r2 | B | muse-spark-1.3 | 33/40 | 26/30 | 7/10 | 23/30 | 5/5 | 32/35 | 27/35 | 3.33 | 5.54 | 3.05 | 2154 | 334 | 281.5 | 0.00436 | 0.1743 | 0 |
| r2 | C | muse-spark-1.3 | 33/40 | 26/30 | 7/10 | 23/30 | 5/5 | 31/35 | 25/35 | 4.29 | 10.83 | 3.88 | 2068 | 288 | 199.0 | 0.00429 | 0.1717 | 0 |

### r1 A (muse-spark-1.2)

fields (of 35 instructions): position 33, bar_from 35, bar_to 35, audience 29, kind 34

- v04c: wrong audience: got Breathe after Rest, not before, bar 60 [bar 60-60 part:Soprano breath]; want Breath after 'rest', bar 60 [bar 60-60 part:Alto breath]
- v07c: wrong audience: got You're late at 71 [bar 71-71 part:Violin I text]; Entry on the and of 2, bar 71 [bar 71-71 part:Viola text]; want Entry on the and of 2, bar 71 [bar 71-71 part:Viola text]
- v10c: wrong kind: got Hold it back at 88 [bar 88-88 ensemble text]; want Hold back at bar 88 [bar 88-88 ensemble dynamic]
- v11: wrong audience: got C# in bar 15 is flat, listen to the viola there [bar 15-15 ensemble text]; want C♯ is flat, bar 15, tune to viola [bar 15-15 member text]
- v16: wrong audience: got No vibrato from 96 to end [range 96-None part:Violin II marking]; want senza vib. 96 to end [range 96-None part:Violin I;part:Violin II marking]
- v23: wrong position, audience: got dim. to nothing, last page [mark None-None part:Soprano,part:Alto,part:Tenor,part:Bass dynamic]; want dim. to niente, last page [global None-None ensemble dynamic]
- v26: wrong position: got f at 55 [bar 55-55 part:Violin II dynamic]; p subito at 56 [bar 56-56 part:Violin II dynamic]; want f at 55, subito p at 56 [range 55-56 part:Violin II dynamic]
- v28: wrong audience: got 4 beats, not 3 at bar 3 [bar 3-3 ensemble text]; want Four beats, bar 3 [bar 3-3 part:Cello text]

### r1 B (muse-spark-1.3)

fields (of 35 instructions): position 33, bar_from 33, bar_to 33, audience 28, kind 32

- v04c: wrong audience: got Breathe after Rest at bar 60, not before [bar 60-60 part:Soprano breath]; want Breath after 'rest', bar 60 [bar 60-60 part:Alto breath]
- v07c: no mark
- v09: no mark
- v10c: wrong kind: got Hold it back at 88 [bar 88-88 ensemble text]; want Hold back at bar 88 [bar 88-88 ensemble dynamic]
- v11: wrong audience: got C# in bar 15 is flat, listen to the viola [bar 15-15 ensemble text]; want C♯ is flat, bar 15, tune to viola [bar 15-15 member text]
- v16: wrong audience: got No vibrato from 96 to the end [range 96-None part:Violin II marking]; want senza vib. 96 to end [range 96-None part:Violin I;part:Violin II marking]
- v23: wrong audience: got diminuendo to nothing, last page [global None-None part:Soprano,part:Alto,part:Tenor,part:Bass dynamic]; want dim. to niente, last page [global None-None ensemble dynamic]
- v28: wrong audience: got 4 beats, not 3, bar 3 [bar 3-3 ensemble text]; want Four beats, bar 3 [bar 3-3 part:Cello text]

### r1 C (muse-spark-1.3)

fields (of 35 instructions): position 34, bar_from 35, bar_to 35, audience 29, kind 34; median ASR 1.37 s + Spark 2.95 s

- v04c: wrong audience: got Breathe after the word rest in bar 60, not before [bar 60-60 part:Soprano breath]; want Breath after 'rest', bar 60 [bar 60-60 part:Alto breath] | heard: 'Breathe after the word rest in bar 60, not before. No, sorry, I mean mean sopranos,'
- v07c: wrong position, audience: got Late at 71 [bar 71-71 part:Violin I text]; Entry is on the end of 2 [global None-None part:Viola text]; want Entry on the and of 2, bar 71 [bar 71-71 part:Viola text] | heard: 'The first violin you are late at 71. What was that? Okay, violas, the entry is on the end end of two.'
- v10c: wrong kind: got Hold it back at 88 [bar 88-88 ensemble text]; want Hold back at bar 88 [bar 88-88 ensemble dynamic] | heard: 'In 88, 88, the opposite hold it back'
- v11: wrong audience: got C# in bar 15 is flat. Listen to the viola there [bar 15-15 ensemble text]; want C♯ is flat, bar 15, tune to viola [bar 15-15 member text] | heard: 'C sharp in bar 15 is flat. Listen to the viola there.'
- v16: wrong audience: got no vibrato 96 to end [range 96-None part:Violin II marking]; want senza vib. 96 to end [range 96-None part:Violin I;part:Violin II marking] | heard: 'and second from 96 to the end no vibrato'
- v23: wrong audience: got diminuendo to nothing, last page [global None-None part:Soprano,part:Alto,part:Tenor,part:Bass dynamic]; want dim. to niente, last page [global None-None ensemble dynamic] | heard: 'whole choir the last page diminuendo to nothing'
- v28: wrong audience: got 4 beats, not 3 at bar 3 - count it [bar 3-3 ensemble text]; want Four beats, bar 3 [bar 3-3 part:Cello text] | heard: "Bar three, that's four beats, not three. Count it."

### r2 A (muse-spark-1.2)

fields (of 35 instructions): position 34, bar_from 34, bar_to 34, audience 28, kind 33

- v04c: wrong audience: got Breathe after the word rest in bar 60, not before [bar 60-60 part:Soprano breath]; want Breath after 'rest', bar 60 [bar 60-60 part:Alto breath]
- v07c: wrong audience: got Late at 71 [bar 71-71 part:Violin I text]; Entry on the and of 2 [bar 71-71 part:Viola text]; want Entry on the and of 2, bar 71 [bar 71-71 part:Viola text]
- v10c: wrong kind: got Hold it back at 88 [bar 88-88 ensemble text]; want Hold back at bar 88 [bar 88-88 ensemble dynamic]
- v11: wrong audience: got C# in bar 15 is flat, listen to Viola [bar 15-15 ensemble text]; want C♯ is flat, bar 15, tune to viola [bar 15-15 member text]
- v15: wrong audience: got pizz. at bar 50 [bar 50-50 part:Cello marking]; want pizz. at bar 50 [bar 50-50 part:Violin I;part:Violin II;part:Viola marking]
- v16: wrong audience: got No vibrato from 96 to the end [range 96-None part:Violin II marking]; want senza vib. 96 to end [range 96-None part:Violin I;part:Violin II marking]
- v27: wrong position, bar_from, bar_to, kind: got cresc. 112–116 [range 112-116 ensemble dynamic]; want Fermata on the last chord [global None-None ensemble marking]
- v28: wrong audience: got 4 beats, not 3 at bar 3 [bar 3-3 ensemble text]; want Four beats, bar 3 [bar 3-3 part:Cello text]
- v29: wrong audience: got Down an octave from the key change til the coda [mark None-None ensemble text]; want Down an octave from the key change to the coda [mark None-None part:Soprano text]

### r2 B (muse-spark-1.3)

fields (of 35 instructions): position 34, bar_from 34, bar_to 34, audience 29, kind 33

- v04c: wrong audience: got Breathe after rest, bar 60, not before [bar 60-60 part:Soprano breath]; want Breath after 'rest', bar 60 [bar 60-60 part:Alto breath]
- v07c: wrong audience: got Late at 71 [bar 71-71 part:Violin I text]; Entry on the end and of 2 [bar 71-71 part:Viola text]; want Entry on the and of 2, bar 71 [bar 71-71 part:Viola text]
- v10c: wrong kind: got The opposite, hold it back at 88 [bar 88-88 ensemble text]; want Hold back at bar 88 [bar 88-88 ensemble dynamic]
- v11: wrong audience: got C# in bar 15 is flat, listen to the viola [bar 15-15 ensemble text]; want C♯ is flat, bar 15, tune to viola [bar 15-15 member text]
- v16: wrong audience: got no vibrato from 96 to the end [range 96-None part:Violin II marking]; want senza vib. 96 to end [range 96-None part:Violin I;part:Violin II marking]
- v17: no mark
- v28: wrong audience: got 4 beats not 3 at bar 3 [bar 3-3 ensemble text]; want Four beats, bar 3 [bar 3-3 part:Cello text]

### r2 C (muse-spark-1.3)

fields (of 35 instructions): position 35, bar_from 35, bar_to 35, audience 29, kind 34; median ASR 1.32 s + Spark 2.80 s

- v04c: wrong audience: got Breathe after the word rest in bar 60, not before [bar 60-60 part:Soprano breath]; want Breath after 'rest', bar 60 [bar 60-60 part:Alto breath] | heard: 'Breathe after the word rest in bar 60, not before. No, sorry, I mean sopranos.'
- v07c: wrong audience: got You are late at 71 [bar 71-71 part:Violin I text]; Entry is on the end of 2 [bar 71-71 part:Viola text]; want Entry on the and of 2, bar 71 [bar 71-71 part:Viola text] | heard: 'The first violin you are late at 71. What was that? Okay, Okay, violas, the entry is on the end end of two.'
- v10c: wrong kind: got Hold it back at 88 [bar 88-88 ensemble text]; want Hold back at bar 88 [bar 88-88 ensemble dynamic] | heard: 'In 88, the opposite, hold it back.'
- v11: wrong audience: got C sharp in bar 15 is flat - listen to the viola there [bar 15-15 ensemble text]; want C♯ is flat, bar 15, tune to viola [bar 15-15 member text] | heard: 'C sharp in bar 15 is flat. Listen to the viola there.'
- v16: wrong audience: got No vibrato 96-end [range 96-None part:Violin II marking]; want senza vib. 96 to end [range 96-None part:Violin I;part:Violin II marking] | heard: 'and second from 96 to the end, no vibrato.'
- v27: wrong audience: got Fermata on the last chord [global None-None member:Inès marking]; want Fermata on the last chord [global None-None ensemble marking] | heard: 'Right, Inès Fermenta on the last chord.'
- v28: wrong audience: got 4 beats, not 3 at bar 3 [bar 3-3 ensemble text]; want Four beats, bar 3 [bar 3-3 part:Cello text] | heard: "Bar three, that's four beats, not three. Count it."

This experiment's spend (ava:*): $1.0711
