## Pooled over both runs

Set 2 (27 lines per run; 5 'none' lines, 2 'flag' lines):

| pipeline | condition | runs | lines ok | shipped errors | dangerous (aud / bars / inverted) | phantom | rightly no mark | missed | alt: ok / shipped | latency median / p95 s | in / out tok | $/line |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| P1 push-to-talk, production | quiet | r1+r2 | 48/54 (89%) | **6/54 (11%)** | 3 (0 / 3 / 0) | 2 | 8/10 | 0 | 48 / 6 | 3.68 / 17.23 | 2070 / 349 | 0.00449 |
| P1 push-to-talk, production | music | r1+r2 | 49/54 (91%) | **5/54 (9%)** | 3 (1 / 2 / 0) | 2 | 8/10 | 0 | 49 / 5 | 3.71 / 14.70 | 2071 / 365 | 0.00493 |
| P2 always-on, turn alone | quiet | r1+r2 | 47/54 (87%) | **7/54 (13%)** | 6 (3 / 4 / 1) | 1 | 9/10 | 0 | 47 / 7 | 3.02 / 26.64 | 2069 / 356 | 0.00471 |
| P2 always-on, turn alone | music | r1+r2 | 48/54 (89%) | **6/54 (11%)** | 4 (1 / 3 / 0) | 2 | 8/10 | 0 | 48 / 6 | 2.87 / 27.74 | 2069 / 324 | 0.00470 |
| P2 always-on, rolling group | quiet | r1+r2 | 47/54 (87%) | **7/54 (13%)** | 7 (4 / 5 / 0) | 0 | 10/10 | 0 | 47 / 7 | 3.05 / 26.64 | 2069 / 423 | 0.00500 |
| P2 always-on, rolling group | music | r1+r2 | 51/54 (94%) | **3/54 (6%)** | 2 (0 / 2 / 0) | 1 | 9/10 | 0 | 51 / 3 | 2.87 / 26.85 | 2070 / 324 | 0.00470 |
| P3a Spark 1.2 on audio | quiet | r1+r2 | 48/54 (89%) | **6/54 (11%)** | 2 (0 / 2 / 0) | 3 | 7/10 | 0 | 48 / 6 | 2.25 / 4.94 | 2145 / 512 | 0.00530 |
| P3a Spark 1.2 on audio | music | r1+r2 | 42/54 (78%) | **11/54 (20%)** | 6 (3 / 3 / 0) | 3 | 7/10 | 1 | 42 / 11 | 2.15 / 5.40 | 2135 / 481 | 0.00529 |
| P3b Spark 1.3 on audio | quiet | r1+r2 | 47/54 (87%) | **6/54 (11%)** | 4 (2 / 2 / 0) | 2 | 8/10 | 1 | 47 / 6 | 3.55 / 7.51 | 2145 / 446 | 0.00482 |
| P3b Spark 1.3 on audio | music | r1+r2 | 42/54 (78%) | **10/54 (19%)** | 8 (4 / 5 / 0) | 2 | 8/10 | 2 | 42 / 10 | 3.44 / 6.23 | 2135 / 476 | 0.00486 |

Old 40 (v04c relabelled Soprano; 'ok w/o clipped' leaves out v11, v16, v28; 'clean' is last night's calls rescored):

| pipeline | condition | runs | lines ok | shipped errors | dangerous (aud / bars / inverted) | phantom | rightly no mark | missed | w/o clipped: ok / shipped / dangerous | alt: ok / shipped | latency median / p95 s | in / out tok | $/line |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| P1 push-to-talk, production | clean | r1+r2 | 68/80 (85%) | **12/80 (15%)** | 10 (10 / 0 / 0) | 0 | 10/10 | 0 | 68/74 / 6 / 4 | 68 / 12 | 4.31 / 10.76 | 2069 / 289 | 0.00429 |
| P1 push-to-talk, production | far | r1+r2 | 64/80 (80%) | **16/80 (20%)** | 13 (13 / 0 / 2) | 0 | 10/10 | 0 | 64/74 / 10 / 7 | 64 / 16 | 3.32 / 14.77 | 2069 / 307 | 0.00436 |
| P1 push-to-talk, production | musicbed | r1+r2 | 62/80 (78%) | **18/80 (22%)** | 14 (13 / 1 / 1) | 0 | 10/10 | 0 | 62/74 / 12 / 8 | 62 / 18 | 3.14 / 6.21 | 2070 / 308 | 0.00428 |
| P1 push-to-talk, production | noise | r1+r2 | 64/80 (80%) | **16/80 (20%)** | 14 (14 / 0 / 1) | 0 | 10/10 | 0 | 64/74 / 10 / 8 | 64 / 16 | 3.31 / 19.55 | 2070 / 275 | 0.00422 |
| P3a Spark 1.2 on audio | clean | r1+r2 | 65/80 (81%) | **15/80 (19%)** | 12 (11 / 1 / 1) | 0 | 10/10 | 0 | 65/74 / 9 / 6 | 65 / 15 | 1.77 / 3.42 | 2154 / 402 | 0.00463 |
| P3a Spark 1.2 on audio | far | r1+r2 | 65/80 (81%) | **15/80 (19%)** | 13 (13 / 1 / 2) | 0 | 10/10 | 0 | 65/74 / 9 / 7 | 65 / 15 | 1.80 / 3.85 | 2154 / 412 | 0.00471 |
| P3a Spark 1.2 on audio | musicbed | r1+r2 | 65/80 (81%) | **15/80 (19%)** | 11 (11 / 0 / 2) | 1 | 9/10 | 0 | 65/74 / 9 / 5 | 65 / 15 | 1.74 / 3.60 | 2154 / 397 | 0.00455 |
| P3a Spark 1.2 on audio | noise | r1+r2 | 65/80 (81%) | **15/80 (19%)** | 13 (13 / 1 / 2) | 0 | 10/10 | 0 | 65/74 / 9 / 7 | 65 / 15 | 1.77 / 2.99 | 2154 / 418 | 0.00460 |
| P3b Spark 1.3 on audio | clean | r1+r2 | 67/80 (84%) | **10/80 (12%)** | 8 (8 / 0 / 0) | 0 | 10/10 | 3 | 67/74 / 4 / 2 | 67 / 10 | 3.56 / 5.61 | 2154 / 375 | 0.00442 |
| P3b Spark 1.3 on audio | far | r1+r2 | 62/80 (78%) | **12/80 (15%)** | 10 (10 / 1 / 1) | 0 | 10/10 | 6 | 62/74 / 6 / 4 | 62 / 12 | 2.97 / 5.59 | 2154 / 391 | 0.00453 |
| P3b Spark 1.3 on audio | musicbed | r1+r2 | 67/80 (84%) | **11/80 (14%)** | 9 (9 / 0 / 0) | 0 | 10/10 | 2 | 67/74 / 5 / 3 | 67 / 11 | 2.96 / 5.33 | 2154 / 363 | 0.00440 |
| P3b Spark 1.3 on audio | noise | r1+r2 | 64/80 (80%) | **12/80 (15%)** | 11 (10 / 3 / 0) | 0 | 10/10 | 4 | 64/74 / 6 / 5 | 64 / 12 | 3.09 / 6.82 | 2154 / 376 | 0.00439 |

## Per run

| pipeline | condition | runs | lines ok | shipped errors | dangerous (aud / bars / inverted) | phantom | rightly no mark | missed | w/o clipped: ok / shipped / dangerous | alt: ok / shipped | latency median / p95 s | in / out tok | $/line |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| P1 push-to-talk, production | quiet | r1 | 23/27 (85%) | **4/27 (15%)** | 2 (0 / 2 / 0) | 1 | 4/5 | 0 | 23/27 / 4 / 2 | 23 / 4 | 3.73 / 17.71 | 2070 / 362 | 0.00440 |
| P1 push-to-talk, production | quiet | r2 | 25/27 (93%) | **2/27 (7%)** | 1 (0 / 1 / 0) | 1 | 4/5 | 0 | 25/27 / 2 / 1 | 25 / 2 | 3.64 / 14.04 | 2071 / 349 | 0.00458 |
| P1 push-to-talk, production | music | r1 | 24/27 (89%) | **3/27 (11%)** | 2 (1 / 1 / 0) | 1 | 4/5 | 0 | 24/27 / 3 / 2 | 24 / 3 | 3.99 / 12.00 | 2071 / 380 | 0.00480 |
| P1 push-to-talk, production | music | r2 | 25/27 (93%) | **2/27 (7%)** | 1 (0 / 1 / 0) | 1 | 4/5 | 0 | 25/27 / 2 / 1 | 25 / 2 | 3.37 / 15.27 | 2071 / 358 | 0.00507 |
| P1 push-to-talk, production | clean | r1 | 34/40 (85%) | **6/40 (15%)** | 5 (5 / 0 / 0) | 0 | 5/5 | 0 | 34/37 / 3 / 2 | 34 / 6 | 4.41 / 6.69 | 2070 / 297 | 0.00429 |
| P1 push-to-talk, production | clean | r2 | 34/40 (85%) | **6/40 (15%)** | 5 (5 / 0 / 0) | 0 | 5/5 | 0 | 34/37 / 3 / 2 | 34 / 6 | 4.29 / 10.83 | 2068 / 288 | 0.00429 |
| P1 push-to-talk, production | far | r1 | 32/40 (80%) | **8/40 (20%)** | 6 (6 / 0 / 1) | 0 | 5/5 | 0 | 32/37 / 5 / 3 | 32 / 8 | 3.33 / 4.91 | 2069 / 320 | 0.00442 |
| P1 push-to-talk, production | far | r2 | 32/40 (80%) | **8/40 (20%)** | 7 (7 / 0 / 1) | 0 | 5/5 | 0 | 32/37 / 5 / 4 | 32 / 8 | 3.28 / 20.42 | 2069 / 304 | 0.00431 |
| P1 push-to-talk, production | musicbed | r1 | 30/40 (75%) | **10/40 (25%)** | 7 (6 / 1 / 1) | 0 | 5/5 | 0 | 30/37 / 7 / 4 | 30 / 10 | 3.14 / 4.92 | 2069 / 304 | 0.00428 |
| P1 push-to-talk, production | musicbed | r2 | 32/40 (80%) | **8/40 (20%)** | 7 (7 / 0 / 0) | 0 | 5/5 | 0 | 32/37 / 5 / 4 | 32 / 8 | 3.16 / 7.63 | 2070 / 311 | 0.00429 |
| P1 push-to-talk, production | noise | r1 | 32/40 (80%) | **8/40 (20%)** | 7 (7 / 0 / 0) | 0 | 5/5 | 0 | 32/37 / 5 / 4 | 32 / 8 | 3.18 / 4.76 | 2069 / 272 | 0.00422 |
| P1 push-to-talk, production | noise | r2 | 32/40 (80%) | **8/40 (20%)** | 7 (7 / 0 / 1) | 0 | 5/5 | 0 | 32/37 / 5 / 4 | 32 / 8 | 3.38 / 25.54 | 2070 / 282 | 0.00422 |
| P2 always-on, turn alone | quiet | r1 | 23/27 (85%) | **4/27 (15%)** | 4 (2 / 3 / 1) | 0 | 5/5 | 0 | 23/27 / 4 / 4 | 23 / 4 | 3.67 / 30.32 | 2069 / 354 | 0.00475 |
| P2 always-on, turn alone | quiet | r2 | 24/27 (89%) | **3/27 (11%)** | 2 (1 / 1 / 0) | 1 | 4/5 | 0 | 24/27 / 3 / 2 | 24 / 3 | 2.78 / 6.13 | 2069 / 357 | 0.00467 |
| P2 always-on, turn alone | music | r1 | 25/27 (93%) | **2/27 (7%)** | 1 (0 / 1 / 0) | 1 | 4/5 | 0 | 25/27 / 2 / 1 | 25 / 2 | 4.08 / 32.39 | 2069 / 315 | 0.00457 |
| P2 always-on, turn alone | music | r2 | 23/27 (85%) | **4/27 (15%)** | 3 (1 / 2 / 0) | 1 | 4/5 | 0 | 23/27 / 4 / 3 | 23 / 4 | 2.49 / 4.47 | 2069 / 325 | 0.00483 |
| P2 always-on, rolling group | quiet | r1 | 23/27 (85%) | **4/27 (15%)** | 4 (2 / 3 / 0) | 0 | 5/5 | 0 | 23/27 / 4 / 4 | 23 / 4 | 3.79 / 30.32 | 2069 / 418 | 0.00502 |
| P2 always-on, rolling group | quiet | r2 | 24/27 (89%) | **3/27 (11%)** | 3 (2 / 2 / 0) | 0 | 5/5 | 0 | 24/27 / 3 / 3 | 24 / 3 | 2.91 / 12.38 | 2069 / 428 | 0.00497 |
| P2 always-on, rolling group | music | r1 | 26/27 (96%) | **1/27 (4%)** | 1 (0 / 1 / 0) | 0 | 5/5 | 0 | 26/27 / 1 / 1 | 26 / 1 | 4.08 / 31.64 | 2070 / 289 | 0.00449 |
| P2 always-on, rolling group | music | r2 | 25/27 (93%) | **2/27 (7%)** | 1 (0 / 1 / 0) | 1 | 4/5 | 0 | 25/27 / 2 / 1 | 25 / 2 | 2.49 / 5.75 | 2070 / 364 | 0.00492 |
| P3a Spark 1.2 on audio | quiet | r1 | 24/27 (89%) | **3/27 (11%)** | 1 (0 / 1 / 0) | 2 | 3/5 | 0 | 24/27 / 3 / 1 | 24 / 3 | 2.19 / 5.29 | 2145 / 479 | 0.00530 |
| P3a Spark 1.2 on audio | quiet | r2 | 24/27 (89%) | **3/27 (11%)** | 1 (0 / 1 / 0) | 1 | 4/5 | 0 | 24/27 / 3 / 1 | 24 / 3 | 2.25 / 4.09 | 2145 / 532 | 0.00529 |
| P3a Spark 1.2 on audio | music | r1 | 20/27 (74%) | **6/27 (22%)** | 3 (2 / 1 / 0) | 2 | 3/5 | 1 | 20/27 / 6 / 3 | 20 / 6 | 2.06 / 5.02 | 2135 / 470 | 0.00519 |
| P3a Spark 1.2 on audio | music | r2 | 22/27 (81%) | **5/27 (19%)** | 3 (1 / 2 / 0) | 1 | 4/5 | 0 | 22/27 / 5 / 3 | 22 / 5 | 2.28 / 5.23 | 2135 / 531 | 0.00540 |
| P3a Spark 1.2 on audio | clean | r1 | 33/40 (82%) | **7/40 (18%)** | 5 (5 / 0 / 0) | 0 | 5/5 | 0 | 33/37 / 4 / 2 | 33 / 7 | 1.87 / 3.46 | 2154 / 412 | 0.00470 |
| P3a Spark 1.2 on audio | clean | r2 | 32/40 (80%) | **8/40 (20%)** | 7 (6 / 1 / 1) | 0 | 5/5 | 0 | 32/37 / 5 / 4 | 32 / 8 | 1.72 / 3.24 | 2154 / 374 | 0.00457 |
| P3a Spark 1.2 on audio | far | r1 | 33/40 (82%) | **7/40 (18%)** | 6 (6 / 1 / 1) | 0 | 5/5 | 0 | 33/37 / 4 / 3 | 33 / 7 | 1.83 / 3.88 | 2154 / 401 | 0.00469 |
| P3a Spark 1.2 on audio | far | r2 | 32/40 (80%) | **8/40 (20%)** | 7 (7 / 0 / 1) | 0 | 5/5 | 0 | 32/37 / 5 / 4 | 32 / 8 | 1.79 / 3.29 | 2154 / 416 | 0.00472 |
| P3a Spark 1.2 on audio | musicbed | r1 | 33/40 (82%) | **7/40 (18%)** | 5 (5 / 0 / 1) | 0 | 5/5 | 0 | 33/37 / 4 / 2 | 33 / 7 | 1.72 / 3.62 | 2154 / 392 | 0.00452 |
| P3a Spark 1.2 on audio | musicbed | r2 | 32/40 (80%) | **8/40 (20%)** | 6 (6 / 0 / 1) | 1 | 4/5 | 0 | 32/37 / 5 / 3 | 32 / 8 | 1.75 / 3.02 | 2154 / 397 | 0.00457 |
| P3a Spark 1.2 on audio | noise | r1 | 32/40 (80%) | **8/40 (20%)** | 7 (7 / 0 / 1) | 0 | 5/5 | 0 | 32/37 / 5 / 4 | 32 / 8 | 1.73 / 2.89 | 2154 / 416 | 0.00461 |
| P3a Spark 1.2 on audio | noise | r2 | 33/40 (82%) | **7/40 (18%)** | 6 (6 / 1 / 1) | 0 | 5/5 | 0 | 33/37 / 4 / 3 | 33 / 7 | 1.77 / 3.06 | 2154 / 420 | 0.00460 |
| P3b Spark 1.3 on audio | quiet | r1 | 25/27 (93%) | **2/27 (7%)** | 1 (0 / 1 / 0) | 1 | 4/5 | 0 | 25/27 / 2 / 1 | 25 / 2 | 3.48 / 8.78 | 2145 / 431 | 0.00481 |
| P3b Spark 1.3 on audio | quiet | r2 | 22/27 (81%) | **4/27 (15%)** | 3 (2 / 1 / 0) | 1 | 4/5 | 1 | 22/27 / 4 / 3 | 22 / 4 | 3.62 / 5.60 | 2145 / 460 | 0.00483 |
| P3b Spark 1.3 on audio | music | r1 | 19/27 (70%) | **7/27 (26%)** | 6 (4 / 3 / 0) | 1 | 4/5 | 1 | 19/27 / 7 / 6 | 19 / 7 | 3.24 / 6.34 | 2135 / 497 | 0.00493 |
| P3b Spark 1.3 on audio | music | r2 | 23/27 (85%) | **3/27 (11%)** | 2 (0 / 2 / 0) | 1 | 4/5 | 1 | 23/27 / 3 / 2 | 23 / 3 | 3.47 / 4.97 | 2135 / 442 | 0.00479 |
| P3b Spark 1.3 on audio | clean | r1 | 33/40 (82%) | **5/40 (12%)** | 4 (4 / 0 / 0) | 0 | 5/5 | 2 | 33/37 / 2 / 1 | 33 / 5 | 3.79 / 5.61 | 2154 / 392 | 0.00448 |
| P3b Spark 1.3 on audio | clean | r2 | 34/40 (85%) | **5/40 (12%)** | 4 (4 / 0 / 0) | 0 | 5/5 | 1 | 34/37 / 2 / 1 | 34 / 5 | 3.33 / 5.54 | 2154 / 334 | 0.00436 |
| P3b Spark 1.3 on audio | far | r1 | 32/40 (80%) | **7/40 (18%)** | 6 (6 / 1 / 1) | 0 | 5/5 | 1 | 32/37 / 4 / 3 | 32 / 7 | 2.97 / 5.91 | 2154 / 386 | 0.00449 |
| P3b Spark 1.3 on audio | far | r2 | 30/40 (75%) | **5/40 (12%)** | 4 (4 / 0 / 0) | 0 | 5/5 | 5 | 30/37 / 2 / 1 | 30 / 5 | 2.97 / 5.35 | 2154 / 404 | 0.00457 |
| P3b Spark 1.3 on audio | musicbed | r1 | 34/40 (85%) | **5/40 (12%)** | 4 (4 / 0 / 0) | 0 | 5/5 | 1 | 34/37 / 2 / 1 | 34 / 5 | 2.93 / 6.36 | 2154 / 374 | 0.00448 |
| P3b Spark 1.3 on audio | musicbed | r2 | 33/40 (82%) | **6/40 (15%)** | 5 (5 / 0 / 0) | 0 | 5/5 | 1 | 33/37 / 3 / 2 | 33 / 6 | 2.96 / 4.80 | 2154 / 347 | 0.00431 |
| P3b Spark 1.3 on audio | noise | r1 | 32/40 (80%) | **6/40 (15%)** | 6 (5 / 2 / 0) | 0 | 5/5 | 2 | 32/37 / 3 / 3 | 32 / 6 | 3.08 / 10.15 | 2154 / 360 | 0.00435 |
| P3b Spark 1.3 on audio | noise | r2 | 32/40 (80%) | **6/40 (15%)** | 5 (5 / 1 / 0) | 0 | 5/5 | 2 | 32/37 / 3 / 2 | 32 / 6 | 3.21 / 6.06 | 2154 / 388 | 0.00444 |

## P2 boundaries (endpointer turns against the 27 lines)

| run | file | turns | empty | turns on no line | lines split (turns) | turns merging lines | lines with no turn | script words lost at start / end (P2) | same for P1 batch clip transcript | endpoint lag median / p95 s | Spark calls | Spark errors |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| r1 | h-music | 27 | 0 | 0 [] | 0 {} | 0 [] | [] | 4 / 0 | 6 / 1 | 0.39 / 1.08 | 27 alone, 27 group | 0 |
| r1 | h-quiet | 28 | 0 | 0 [] | 2 {'h02': 2, 'h18': 4} | 3 [[17, ['h17', 'h18']], [26, ['h24', 'h25']], [27, ['h26', 'h27']]] | [] | 4 / 4 | 3 / 2 | 0.33 / 5.35 | 28 alone, 28 group | 0 |
| r2 | h-music | 29 | 0 | 0 [] | 2 {'h02': 2, 'h19': 2} | 0 [] | [] | 3 / 0 | 4 / 1 | 0.54 / 0.79 | 29 alone, 29 group | 0 |
| r2 | h-quiet | 27 | 0 | 0 [] | 1 {'h18': 3} | 2 [[16, ['h17', 'h18']], [26, ['h26', 'h27']]] | [] | 5 / 4 | 3 / 1 | 0.34 / 3.44 | 27 alone, 27 group | 0 |

## Per-line failures (both runs; shipped errors marked SHIPPED, dangerous ones DANGER)

### P1 push-to-talk, production, quiet: 6 failures of 54

- r1 h01: DANGER SHIPPED  (bars) got Bring it down from 30 [range 30-None part:Violin II dynamic]; want Vln II, bar 30: 'softer from here'. No end bar was said; a range to the end is not supported. | heard: "Okay, so um what I'm hearing is yeah the second second violins that whole passage let's say from thirty thirty-ish is just too much bring it down"
- r2 h01: DANGER SHIPPED  (bars) got Too much from 30, bring it down [range 30-None part:Violin II dynamic]; want Vln II, bar 30: 'softer from here'. No end bar was said; a range to the end is not supported. | heard: "Okay, so um what I'm hearing hearing is yeah the second violins that whole passage let's say from thirty thirty ish is just too much bring it down"
- r1 h02: DANGER SHIPPED  (bars, position) got staccato at 40, no weight 42 [range 40-42 part:Cello marking]; want Vc, stacc. at 42 (40 corrected). | heard: 'Cellos, staccato at 40, no weight 42.'
- r1 h12: SHIPPED  (kind) got More bow at bar 84 [bar 84-84 member:Lin marking]; want Lin, 'more bow' at 84. | heard: 'Lin bar 84 a bit more bow.'
- r1 h24: SHIPPED  (phantom) got At bar 60 [bar 60-60 part:Soprano text]; want gt none | heard: 'Sopranos at bar 60'
- r2 h24: SHIPPED  (phantom) got At bar 60 [bar 60-60 part:Soprano text]; want gt none | heard: 'Sopranos at bar 60'

### P1 push-to-talk, production, music: 5 failures of 54

- r1 h01: DANGER SHIPPED  (bars) got Bring it down from 30 [range 30-None part:Violin II dynamic]; want Vln II, bar 30: 'softer from here'. No end bar was said; a range to the end is not supported. | heard: "Okay, so what I'm hearing is, yeah, the second violins, that whole passage let's say from 30, 30-ish is just too much. Bring it down."
- r2 h01: DANGER SHIPPED  (bars) got Bring it down from 30 [range 30-None part:Violin II dynamic]; want Vln II, bar 30: 'softer from here'. No end bar was said; a range to the end is not supported. | heard: "Okay, so what I'm hearing is, yeah, the second violins that whole passage, let's say, from 30-ish, is just just too much. Bring it down."
- r1 h07: DANGER SHIPPED  (audience) got You're too loud at 140 [bar 140-140 member:Lin dynamic]; You're too loud at 140 [bar 140-140 part:Viola dynamic]; want Va softer at 140; clarinets are not in the book. | heard: "Where in you're too loud at 140 and violas you too"
- r1 h24: SHIPPED  (phantom) got Sopranos at bar 60 [bar 60-60 part:Soprano text]; want gt none | heard: 'Sopranos, at bar 60'
- r2 h24: SHIPPED  (phantom) got Entry at bar 60 [bar 60-60 part:Soprano text]; want gt none | heard: 'Sopranos, at bar 60'

### P1 push-to-talk, production, clean: 12 failures of 80

- r1 v07c: DANGER SHIPPED  (audience, position) got Late at 71 [bar 71-71 part:Violin I text]; Entry is on the end of 2 [global None-None part:Viola text]; want Entry on the and of 2, bar 71 [bar 71-71 part:Viola text] | heard: 'The first violin you are late at 71. What was that? Okay, violas, the entry is on the end end of two.'
- r2 v07c: DANGER SHIPPED  (audience) got You are late at 71 [bar 71-71 part:Violin I text]; Entry is on the end of 2 [bar 71-71 part:Viola text]; want Entry on the and of 2, bar 71 [bar 71-71 part:Viola text] | heard: 'The first violin you are late at 71. What was that? Okay, Okay, violas, the entry is on the end end of two.'
- r1 v10c: SHIPPED  (kind) got Hold it back at 88 [bar 88-88 ensemble text]; want Hold back at bar 88 [bar 88-88 ensemble dynamic] | heard: 'In 88, 88, the opposite hold it back'
- r2 v10c: SHIPPED  (kind) got Hold it back at 88 [bar 88-88 ensemble text]; want Hold back at bar 88 [bar 88-88 ensemble dynamic] | heard: 'In 88, the opposite, hold it back.'
- r1 v11: DANGER SHIPPED  (audience) got C# in bar 15 is flat. Listen to the viola there [bar 15-15 ensemble text]; want C♯ is flat, bar 15, tune to viola [bar 15-15 member text] | heard: 'C sharp in bar 15 is flat. Listen to the viola there.'
- r2 v11: DANGER SHIPPED  (audience) got C sharp in bar 15 is flat - listen to the viola there [bar 15-15 ensemble text]; want C♯ is flat, bar 15, tune to viola [bar 15-15 member text] | heard: 'C sharp in bar 15 is flat. Listen to the viola there.'
- r1 v16: DANGER SHIPPED  (audience) got no vibrato 96 to end [range 96-None part:Violin II marking]; want senza vib. 96 to end [range 96-None part:Violin I;part:Violin II marking] | heard: 'and second from 96 to the end no vibrato'
- r2 v16: DANGER SHIPPED  (audience) got No vibrato 96-end [range 96-None part:Violin II marking]; want senza vib. 96 to end [range 96-None part:Violin I;part:Violin II marking] | heard: 'and second from 96 to the end, no vibrato.'
- r1 v23: DANGER SHIPPED  (audience) got diminuendo to nothing, last page [global None-None part:Soprano,part:Alto,part:Tenor,part:Bass dynamic]; want dim. to niente, last page [global None-None ensemble dynamic] | heard: 'whole choir the last page diminuendo to nothing'
- r2 v27: DANGER SHIPPED  (audience) got Fermata on the last chord [global None-None member:Inès marking]; want Fermata on the last chord [global None-None ensemble marking] | heard: 'Right, Inès Fermenta on the last chord.'
- r1 v28: DANGER SHIPPED  (audience) got 4 beats, not 3 at bar 3 - count it [bar 3-3 ensemble text]; want Four beats, bar 3 [bar 3-3 part:Cello text] | heard: "Bar three, that's four beats, not three. Count it."
- r2 v28: DANGER SHIPPED  (audience) got 4 beats, not 3 at bar 3 [bar 3-3 ensemble text]; want Four beats, bar 3 [bar 3-3 part:Cello text] | heard: "Bar three, that's four beats, not three. Count it."

### P1 push-to-talk, production, far: 16 failures of 80

- r1 v07c: DANGER SHIPPED  (audience, position) got You are late at 71 [bar 71-71 part:Violin I text]; Entry is on the end of 2 [global None-None part:Viola text]; want Entry on the and of 2, bar 71 [bar 71-71 part:Viola text] | heard: 'The first violin you are late at 71. What was that? Okay, violas the entry is on the end end of two'
- r2 v07c: DANGER SHIPPED  (audience, position) got You are late at 71 [bar 71-71 part:Violin I text]; Entry is on the and of 2 [global None-None part:Viola text]; want Entry on the and of 2, bar 71 [bar 71-71 part:Viola text] | heard: 'The first violin you are late at 71. What was that? Okay, violas the entry is on the end and of two.'
- r1 v10c: SHIPPED  (kind) got The opposite hold back, bar 88 [bar 88-88 ensemble text]; want Hold back at bar 88 [bar 88-88 ensemble dynamic] | heard: 'In 88, the opposite Hodiback.'
- r2 v10c: SHIPPED  (kind) got Hold it back at 88 [bar 88-88 ensemble text]; want Hold back at bar 88 [bar 88-88 ensemble dynamic] | heard: 'In 88, 88, the opposite hold it back.'
- r1 v11: DANGER SHIPPED  (audience) got C# in bar 15 is flat, listen to the viola [bar 15-15 ensemble text]; want C♯ is flat, bar 15, tune to viola [bar 15-15 member text] | heard: 'C sharp in bar 15 is flat. Listen to the the viola there.'
- r2 v11: DANGER SHIPPED  (audience) got C# in bar 15 is flat. Listen to the viola there [bar 15-15 ensemble text]; want C♯ is flat, bar 15, tune to viola [bar 15-15 member text] | heard: 'C sharp in bar 15 is flat. Listen to the the viola there.'
- r1 v15: DANGER SHIPPED  (audience, inverted) got pizz. bar 50 [bar 50-50 part:Cello marking]; want pizz. at bar 50 [bar 50-50 part:Violin I;part:Violin II;part:Viola marking] | heard: 'start the cello bar 50 pizzicato'
- r2 v15: DANGER SHIPPED  (audience, inverted) got Start pizz. bar 50 [bar 50-50 part:Cello marking]; want pizz. at bar 50 [bar 50-50 part:Violin I;part:Violin II;part:Viola marking] | heard: 'Start the cello bar 50 pizzicato'
- r1 v16: DANGER SHIPPED  (audience) got No vibrato from 96 to the end [range 96-None part:Violin II marking]; want senza vib. 96 to end [range 96-None part:Violin I;part:Violin II marking] | heard: 'And second from 96 to the end, no vibrato,'
- r2 v16: DANGER SHIPPED  (audience) got No vibrato from 96 to the end [range 96-None part:Violin II marking]; want senza vib. 96 to end [range 96-None part:Violin I;part:Violin II marking] | heard: 'and second from 96 to the end, no vibrato.'
- r2 v23: DANGER SHIPPED  (audience) got dim. to nothing, last page [global None-None part:Soprano,part:Alto,part:Tenor,part:Bass dynamic]; want dim. to niente, last page [global None-None ensemble dynamic] | heard: 'Whole choir, the last page, diminuendo to nothing.'
- r1 v26: SHIPPED  (position) got f at 55, subito p at 56 [bar 55-56 part:Violin II dynamic]; want f at 55, subito p at 56 [range 55-56 part:Violin II dynamic] | heard: 'seconds mark it bar 55 is forte 56 is piano subito'
- r1 v27: DANGER SHIPPED  (audience, kind) got From Lin on the last chord [global None-None member:Inès text]; want Fermata on the last chord [global None-None ensemble marking] | heard: 'Right, Inès from Lin on the last chord.'
- r2 v27: DANGER SHIPPED  (audience) got Fermata on the last chord [global None-None member:Inès marking]; want Fermata on the last chord [global None-None ensemble marking] | heard: 'Right Inès Fermenta on the last chord.'
- r1 v28: DANGER SHIPPED  (audience) got 4 beats, not 3 at bar 3, count it [bar 3-3 ensemble text]; want Four beats, bar 3 [bar 3-3 part:Cello text] | heard: "Bar three, that's four beats, not three. Count it."
- r2 v28: DANGER SHIPPED  (audience) got 4 beats, not 3 at bar 3, count it [bar 3-3 ensemble text]; want Four beats, bar 3 [bar 3-3 part:Cello text] | heard: "Bar three, that's four beats, not three. Count it."

### P1 push-to-talk, production, musicbed: 18 failures of 80

- r1 v07c: DANGER SHIPPED  (audience) got Late at 71 [bar 71-71 part:Violin I text]; Entry is on the end of 2 [bar 71-71 part:Viola text]; want Entry on the and of 2, bar 71 [bar 71-71 part:Viola text] | heard: 'The first violin you are late at 71. What was that? Okay, violas. The entry is on the end end of two.'
- r2 v07c: DANGER SHIPPED  (audience, position) got Late at 71 [bar 71-71 part:Violin I text]; Entry is on the end of 2 [global None-None part:Viola text]; want Entry on the and of 2, bar 71 [bar 71-71 part:Viola text] | heard: 'The first violin you are late at 71. What was that? Okay, violas. The entry is on the end end of two.'
- r2 v10: DANGER SHIPPED  (audience) got No louder, the opposite, hold it back at 88 [bar 88-88 member:Inès dynamic]; want Hold back at bar 88 [bar 88-88 ensemble dynamic] | heard: 'no louder Inès 88 the opposite hold it back'
- r1 v10c: SHIPPED  (kind) got Hold it back at 88 [bar 88-88 ensemble text]; want Hold back at bar 88 [bar 88-88 ensemble dynamic] | heard: 'In 88, the opposite, hold it back.'
- r2 v10c: SHIPPED  (kind) got Hold it back at 88 [bar 88-88 ensemble text]; want Hold back at bar 88 [bar 88-88 ensemble dynamic] | heard: 'in 88, the 88. The opposite hold it back'
- r1 v11: DANGER SHIPPED  (audience) got D# in bar 15 is flat, listen to viola [bar 15-15 ensemble text]; want C♯ is flat, bar 15, tune to viola [bar 15-15 member text] | heard: 'D sharp in bar 15 is flat. Listen to the viola there.'
- r2 v11: DANGER SHIPPED  (audience) got D# in bar 15 is flat, listen to the viola there [bar 15-15 ensemble text]; want C♯ is flat, bar 15, tune to viola [bar 15-15 member text] | heard: 'D sharp in bar 15 is flat. Listen to the the viola there.'
- r1 v12: DANGER SHIPPED  (bars) got Pick up to 34, you come in [bar 34-34 part:Violin I text]; want Entry at the pickup to 34 [bar 33-34 part:Violin I text] | heard: "Pick up to 34, first, that's where you come in. Nobody else."
- r1 v15: DANGER SHIPPED  (audience, inverted) got pizz. at bar 50 [bar 50-50 part:Cello marking]; want pizz. at bar 50 [bar 50-50 part:Violin I;part:Violin II;part:Viola marking] | heard: 'Stop the cello. bar 50, pizzicato.'
- r1 v16: DANGER SHIPPED  (audience) got No vibrato from 96 to the end [range 96-None part:Violin II marking]; want senza vib. 96 to end [range 96-None part:Violin I;part:Violin II marking] | heard: 'And second from 96 to the end, no vibrato.'
- r2 v16: DANGER SHIPPED  (audience) got No vibrato 96 to the end [range 96-None part:Violin II marking]; want senza vib. 96 to end [range 96-None part:Violin I;part:Violin II marking] | heard: 'and second from 96 to the end, no vibrato.'
- r1 v18: DANGER SHIPPED  (audience) got Down bow at bar 7 [bar 7-7 part:Violin I bowing]; want Down bow at bar 7 [bar 7-7 part:Violin I;part:Violin II bowing] | heard: 'Firsts, bar seven, down bow. Both of you.'
- r2 v18: DANGER SHIPPED  (audience) got Down bow at bar 7 [bar 7-7 part:Violin I bowing]; want Down bow at bar 7 [bar 7-7 part:Violin I;part:Violin II bowing] | heard: 'firsts, bar seven, down bow, both of you.'
- r1 v23: SHIPPED  (position) got dim. to nothing, last page [mark None-None ensemble dynamic]; want dim. to niente, last page [global None-None ensemble dynamic] | heard: 'whole choir, the last page, diminuendo to nothing.'
- r2 v23: DANGER SHIPPED  (audience) got dim. to nothing last page [global None-None part:Soprano,part:Alto,part:Tenor,part:Bass dynamic]; want dim. to niente, last page [global None-None ensemble dynamic] | heard: 'whole choir the last page diminuendo to nothing'
- r1 v26: SHIPPED  (position) got f bar 55, subito p bar 56 [bar 55-56 part:Violin II dynamic]; want f at 55, subito p at 56 [range 55-56 part:Violin II dynamic] | heard: 'seconds mark it, bar 55 is forte, 56 is piano, subito,'
- r1 v28: DANGER SHIPPED  (audience) got 4 beats, not 3 at bar 3 [bar 3-3 ensemble text]; want Four beats, bar 3 [bar 3-3 part:Cello text] | heard: "Bar three, that's four beats, not three. Count it."
- r2 v28: DANGER SHIPPED  (audience) got That's 4 beats, not 3 - count it, bar 3 [bar 3-3 ensemble text]; want Four beats, bar 3 [bar 3-3 part:Cello text] | heard: "Bar three, that's four beats, not three. Count it."

### P1 push-to-talk, production, noise: 16 failures of 80

- r1 v07c: DANGER SHIPPED  (audience, position) got Late at 71 [bar 71-71 part:Violin I text]; Entry is on the end of 2 [global None-None part:Viola text]; want Entry on the and of 2, bar 71 [bar 71-71 part:Viola text] | heard: 'The first violin you are late at 71. What was that? Okay, violas, the entry is on the end end of two.'
- r2 v07c: DANGER SHIPPED  (audience) got Late at 71 [bar 71-71 part:Violin I text]; Entry is on the end of 2 [bar 71-71 part:Viola text]; want Entry on the and of 2, bar 71 [bar 71-71 part:Viola text] | heard: 'The first violin you are late at seventy-one. What was that? Okay, violas, the entry is on the end end of two.'
- r1 v10: DANGER SHIPPED  (audience) got Hold it back at 88 [bar 88-88 member:Inès dynamic]; want Hold back at bar 88 [bar 88-88 ensemble dynamic] | heard: 'No louder, Inès 88. The opposite. Hold it back.'
- r1 v10c: SHIPPED  (kind) got Hold it back at 88 [bar 88-88 ensemble text]; want Hold back at bar 88 [bar 88-88 ensemble dynamic] | heard: 'in 88, 88 the opposite hold it back'
- r2 v10c: SHIPPED  (kind) got Opposite, hold it back at 88 [bar 88-88 ensemble text]; want Hold back at bar 88 [bar 88-88 ensemble dynamic] | heard: 'In 88, 88, the opposite hold it back'
- r1 v11: DANGER SHIPPED  (audience) got C sharp in bar 15 is flat, listen to the viola [bar 15-15 ensemble text]; want C♯ is flat, bar 15, tune to viola [bar 15-15 member text] | heard: 'C sharp in bar bar 15 is flat. Listen to the viola there.'
- r2 v11: DANGER SHIPPED  (audience) got C sharp in bar 15 is flat, listen to the viola [bar 15-15 ensemble text]; want C♯ is flat, bar 15, tune to viola [bar 15-15 member text] | heard: 'C sharp in bar 15 is flat listen to the viola there.'
- r2 v15: DANGER SHIPPED  (audience, inverted) got pizz. at bar 50 [bar 50-50 part:Cello marking]; want pizz. at bar 50 [bar 50-50 part:Violin I;part:Violin II;part:Viola marking] | heard: 'step the cello, bar 50, pizzicato'
- r1 v16: DANGER SHIPPED  (audience) got No vibrato 96 to the end [range 96-None part:Violin II marking]; want senza vib. 96 to end [range 96-None part:Violin I;part:Violin II marking] | heard: 'and second from 96 to the end no vibrato vibrato.'
- r2 v16: DANGER SHIPPED  (audience) got No vibrato from 96 to the end [range 96-None part:Violin II marking]; want senza vib. 96 to end [range 96-None part:Violin I;part:Violin II marking] | heard: 'and second from 96 to the end, no vibrato.'
- r1 v18: DANGER SHIPPED  (audience) got Down bow at bar 7 [bar 7-7 part:Violin I bowing]; want Down bow at bar 7 [bar 7-7 part:Violin I;part:Violin II bowing] | heard: 'Firsts, bar seven, down bow, both of you.'
- r2 v23: DANGER SHIPPED  (audience) got dim. last page to nothing [global None-None part:Soprano,part:Alto,part:Tenor,part:Bass dynamic]; want dim. to niente, last page [global None-None ensemble dynamic] | heard: 'Whole choir the last page diminuendo to nothing'
- r1 v27: DANGER SHIPPED  (audience) got fermata on the last chord [global None-None member:Inès marking]; want Fermata on the last chord [global None-None ensemble marking] | heard: 'write Inès fermenta on the last chord.'
- r2 v27: DANGER SHIPPED  (audience) got Fermata on the last chord [global None-None member:Inès marking]; want Fermata on the last chord [global None-None ensemble marking] | heard: 'Right Inès Frumenta on the last chord.'
- r1 v28: DANGER SHIPPED  (audience) got That's 4 beats, not 3, bar 3 [bar 3-3 ensemble text]; want Four beats, bar 3 [bar 3-3 part:Cello text] | heard: "bar three, that's four beats, not not three. Count it."
- r2 v28: DANGER SHIPPED  (audience) got 4 beats, not 3 - count it, bar 3 [bar 3-3 ensemble text]; want Four beats, bar 3 [bar 3-3 part:Cello text] | heard: "Bar three, that's four beats, not not three. Count it."

### P2 always-on, turn alone, quiet: 7 failures of 54

- r1 h01: DANGER SHIPPED  (bars) got Bring it down from 30 [range 30-None part:Violin II dynamic]; want Vln II, bar 30: 'softer from here'. No end bar was said; a range to the end is not supported. | heard: "Okay, so um what I'm hearing is yeah the second violins that whole passage let's say from thirty thirty ish is just too much, bring it down"
- r2 h01: DANGER SHIPPED  (bars) got Bring it down from 30 [range 30-None part:Violin II dynamic]; want Vln II, bar 30: 'softer from here'. No end bar was said; a range to the end is not supported. | heard: "Okay, so what I'm hearing is yeah the second violins that whole passage let's say from thirty thirty ish is just too much bring it down"
- r1 h02: DANGER SHIPPED  (bars) got staccato at 40, no weight [bar 40-40 part:Cello marking]; want Vc, stacc. at 42 (40 corrected). | heard: 'Cellos, staccato at forty, no weight, Forty-two,'
- r1 h18: DANGER SHIPPED  (audience, extra, inverted) got cresc. at 30 [bar 30-30 ensemble dynamic]; dim. [global None-None ensemble dynamic]; dim. [global None-None ensemble dynamic]; want Va, dim. at 30 (cresc. corrected). | heard: "Right so okay the thing about bar one seventy and this is everyone is that it's not a retardando I know it looks like one it's in tempo keep going Crescendo at thirty Actually no make it a diminuendo diminuendo"
- r2 h18: DANGER SHIPPED  (audience, extra) got dim. at 30 [bar 30-30 ensemble dynamic]; dim. [global None-None ensemble dynamic]; want Va, dim. at 30 (cresc. corrected). | heard: "right so okay the thing about bar one seventy and this is everyone is that it's not a ritardando I know it looks like one it's in tempo keep going crescendo at thirty actually no make it a diminuendo diminuendo"
- r2 h24: SHIPPED  (phantom) got Entry at bar 60 [bar 60-60 part:Soprano text]; want gt none | heard: 'Sopranos at bar sixty'
- r1 h25: DANGER SHIPPED  (audience, bars, position) got Too loud 60-88 [range 60-88 part:Soprano dynamic]; want gt flag | heard: 'Sopranos at bar sixty you yes you bar eighty eight too loud'

### P2 always-on, turn alone, music: 6 failures of 54

- r1 h01: DANGER SHIPPED  (bars) got Bring it down from 30 [range 30-None part:Violin II dynamic]; want Vln II, bar 30: 'softer from here'. No end bar was said; a range to the end is not supported. | heard: "okay so um what I'm hearing is yeah the second violins that whole passage let's say from 30 30 ish is just too much bring it down"
- r2 h01: DANGER SHIPPED  (bars) got Too much from 30, bring it down [range 30-None part:Violin II dynamic]; want Vln II, bar 30: 'softer from here'. No end bar was said; a range to the end is not supported. | heard: "Okay, so what I'm hearing is yeah, the second valve is that whole passage, let's say from 30, 30-ish is just too much bring it down"
- r2 h02: DANGER SHIPPED  (bars) got staccato at 40 [bar 40-40 part:Cello marking]; want Vc, stacc. at 42 (40 corrected). | heard: 'Cellos, staccato at 40 No, wait, 42.'
- r2 h19: DANGER SHIPPED  (audience) got pizz. at 12 [bar 12-12 ensemble marking]; Breathe at 14 [bar 14-14 part:Bass breath]; want Vc pizz. 12; B (voices) breath at 14. | heard: 'cellos and basses wait basses are the singers just cellos Piss at 12 and the singers the basses I mean breathe at 14'
- r1 h24: SHIPPED  (phantom) got at bar 60 [bar 60-60 part:Soprano text]; want gt none | heard: 'Sopranos at bar 60'
- r2 h24: SHIPPED  (phantom) got at bar 60 [bar 60-60 part:Soprano text]; want gt none | heard: 'Sopranos at bar 60'

### P2 always-on, rolling group, quiet: 7 failures of 54

- r1 h01: DANGER SHIPPED  (bars) got Bring it down from 30 [range 30-None part:Violin II dynamic]; want Vln II, bar 30: 'softer from here'. No end bar was said; a range to the end is not supported. | heard: "Okay, so um what I'm hearing is yeah the second violins that whole passage let's say from thirty thirty ish is just too much, bring it down"
- r2 h01: DANGER SHIPPED  (bars) got Bring it down from 30 [range 30-None part:Violin II dynamic]; want Vln II, bar 30: 'softer from here'. No end bar was said; a range to the end is not supported. | heard: "Okay, so what I'm hearing is yeah the second violins that whole passage let's say from thirty thirty ish is just too much bring it down"
- r1 h02: DANGER SHIPPED  (bars) got staccato at 40, no weight [bar 40-40 part:Cello marking]; want Vc, stacc. at 42 (40 corrected). | heard: 'Cellos, staccato at forty, no weight, Forty-two,'
- r1 h18: DANGER SHIPPED  (audience, extra) got dim. at 30 [bar 30-30 ensemble dynamic]; dim. [global None-None ensemble dynamic]; want Va, dim. at 30 (cresc. corrected). | heard: "Right so okay the thing about bar one seventy and this is everyone is that it's not a retardando I know it looks like one it's in tempo keep going Crescendo at thirty Actually no make it a diminuendo diminuendo"
- r2 h18: DANGER SHIPPED  (audience, extra) got dim. at 30 [bar 30-30 ensemble dynamic]; dim. [global None-None ensemble dynamic]; want Va, dim. at 30 (cresc. corrected). | heard: "right so okay the thing about bar one seventy and this is everyone is that it's not a ritardando I know it looks like one it's in tempo keep going crescendo at thirty actually no make it a diminuendo diminuendo"
- r1 h25: DANGER SHIPPED  (audience, bars, position) got Too loud 60-88 [range 60-88 part:Soprano dynamic]; want gt flag | heard: 'Sopranos at bar sixty you yes you bar eighty eight too loud'
- r2 h25: DANGER SHIPPED  (audience, bars, position) got Too loud 60-88 [range 60-88 part:Soprano dynamic]; want gt flag | heard: 'you yes you bar eighty eight too loud'

### P2 always-on, rolling group, music: 3 failures of 54

- r1 h01: DANGER SHIPPED  (bars) got Bring it down from 30 [range 30-None part:Violin II dynamic]; want Vln II, bar 30: 'softer from here'. No end bar was said; a range to the end is not supported. | heard: "okay so um what I'm hearing is yeah the second violins that whole passage let's say from 30 30 ish is just too much bring it down"
- r2 h01: DANGER SHIPPED  (bars) got Too much from 30, bring it down [range 30-None part:Violin II dynamic]; want Vln II, bar 30: 'softer from here'. No end bar was said; a range to the end is not supported. | heard: "Okay, so what I'm hearing is yeah, the second valve is that whole passage, let's say from 30, 30-ish is just too much bring it down"
- r2 h23: SHIPPED  (phantom) got The thing at the end of the Sopranos at bar 60 [bar 60-60 part:Viola text]; want gt none | heard: 'violas at the can we just just the thing at the end of the'

### P3a Spark 1.2 on audio, quiet: 6 failures of 54

- r1 h01: DANGER SHIPPED  (bars) got Too much, bring it down from 30 [range 30-None part:Violin II dynamic]; want Vln II, bar 30: 'softer from here'. No end bar was said; a range to the end is not supported.
- r2 h01: DANGER SHIPPED  (bars) got Bring it down from 30 [range 30-None part:Violin II dynamic]; want Vln II, bar 30: 'softer from here'. No end bar was said; a range to the end is not supported.
- r2 h19: SHIPPED  (kind) got Pitches at 12 [bar 12-12 part:Cello text]; Breathe at 14 [bar 14-14 part:Bass breath]; want Vc pizz. 12; B (voices) breath at 14.
- r1 h24: SHIPPED  (phantom) got Entry at bar 60 [bar 60-60 part:Soprano text]; want gt none
- r2 h24: SHIPPED  (phantom) got Sopranos at bar 60 [bar 60-60 part:Soprano text]; want gt none
- r1 h27: SHIPPED  (phantom) got softer at 70 [bar 70-70 part:Viola dynamic]; want gt none

### P3a Spark 1.2 on audio, music: 12 failures of 54

- r1 h01: DANGER SHIPPED  (bars) got Bring it down from 30 [range 30-None part:Violin II dynamic]; want Vln II, bar 30: 'softer from here'. No end bar was said; a range to the end is not supported.
- r2 h01: DANGER SHIPPED  (bars) got Too much, bring it down from 30 [range 30-None part:Violin II dynamic]; want Vln II, bar 30: 'softer from here'. No end bar was said; a range to the end is not supported.
- r1 h03: missed  got no mark; want Vln II, accent on beat 1 of 77.
- r1 h05: DANGER SHIPPED  (audience) got Mute on at 100 [bar 100-100 ensemble marking]; pizz. at 104 [bar 104-104 part:Cello marking]; want Vln I mute on 100; Vc pizz. 104. The email aside is not a mark.
- r1 h06: DANGER SHIPPED  (audience) got Accent at 66 [bar 66-66 part:Soprano,part:Cello marking]; want Vc accent at 66; trumpets are not in the book (admin's card). Cello alone, ensemble with 'trumpets' kept, or both are defensible.
- r2 h06: DANGER SHIPPED  (audience) got Accent at 66 [bar 66-66 part:Bass,part:Cello marking]; want Vc accent at 66; trumpets are not in the book (admin's card). Cello alone, ensemble with 'trumpets' kept, or both are defensible.
- r2 h08: DANGER SHIPPED  (bars) got Don't rush at 16 [bar 16-16 ensemble text]; want Tutti, 'don't rush' at 60.
- r1 h19: SHIPPED  (kind) got pizz. at 12 [bar 12-12 part:Cello marking]; Bring at 14 [bar 14-14 part:Bass text]; want Vc pizz. 12; B (voices) breath at 14.
- r2 h19: SHIPPED  (kind) got pizz. at 12 [bar 12-12 part:Cello marking]; Bring at 14 [bar 14-14 part:Bass text]; want Vc pizz. 12; B (voices) breath at 14.
- r1 h24: SHIPPED  (phantom) got Entry at bar 60 [bar 60-60 part:Soprano text]; want gt none
- r2 h24: SHIPPED  (phantom) got Entry at bar 60 [bar 60-60 part:Soprano text]; want gt none
- r1 h27: SHIPPED  (phantom) got softer at 70 [bar 70-70 part:Viola dynamic]; want gt none

### P3a Spark 1.2 on audio, clean: 15 failures of 80

- r1 v07c: DANGER SHIPPED  (audience) got You're late at 71 [bar 71-71 part:Violin I text]; Entry on the and of 2, bar 71 [bar 71-71 part:Viola text]; want Entry on the and of 2, bar 71 [bar 71-71 part:Viola text]
- r2 v07c: DANGER SHIPPED  (audience) got Late at 71 [bar 71-71 part:Violin I text]; Entry on the and of 2 [bar 71-71 part:Viola text]; want Entry on the and of 2, bar 71 [bar 71-71 part:Viola text]
- r1 v10c: SHIPPED  (kind) got Hold it back at 88 [bar 88-88 ensemble text]; want Hold back at bar 88 [bar 88-88 ensemble dynamic]
- r2 v10c: SHIPPED  (kind) got Hold it back at 88 [bar 88-88 ensemble text]; want Hold back at bar 88 [bar 88-88 ensemble dynamic]
- r1 v11: DANGER SHIPPED  (audience) got C# in bar 15 is flat, listen to the viola there [bar 15-15 ensemble text]; want C♯ is flat, bar 15, tune to viola [bar 15-15 member text]
- r2 v11: DANGER SHIPPED  (audience) got C# in bar 15 is flat, listen to Viola [bar 15-15 ensemble text]; want C♯ is flat, bar 15, tune to viola [bar 15-15 member text]
- r2 v15: DANGER SHIPPED  (audience, inverted) got pizz. at bar 50 [bar 50-50 part:Cello marking]; want pizz. at bar 50 [bar 50-50 part:Violin I;part:Violin II;part:Viola marking]
- r1 v16: DANGER SHIPPED  (audience) got No vibrato from 96 to end [range 96-None part:Violin II marking]; want senza vib. 96 to end [range 96-None part:Violin I;part:Violin II marking]
- r2 v16: DANGER SHIPPED  (audience) got No vibrato from 96 to the end [range 96-None part:Violin II marking]; want senza vib. 96 to end [range 96-None part:Violin I;part:Violin II marking]
- r1 v23: DANGER SHIPPED  (audience, position) got dim. to nothing, last page [mark None-None part:Soprano,part:Alto,part:Tenor,part:Bass dynamic]; want dim. to niente, last page [global None-None ensemble dynamic]
- r1 v26: SHIPPED  (position) got f at 55 [bar 55-55 part:Violin II dynamic]; p subito at 56 [bar 56-56 part:Violin II dynamic]; want f at 55, subito p at 56 [range 55-56 part:Violin II dynamic]
- r2 v27: DANGER SHIPPED  (bars, kind, position) got cresc. 112–116 [range 112-116 ensemble dynamic]; want Fermata on the last chord [global None-None ensemble marking] COPIED EXAMPLE: ['cresc. 112–116']
- r1 v28: DANGER SHIPPED  (audience) got 4 beats, not 3 at bar 3 [bar 3-3 ensemble text]; want Four beats, bar 3 [bar 3-3 part:Cello text]
- r2 v28: DANGER SHIPPED  (audience) got 4 beats, not 3 at bar 3 [bar 3-3 ensemble text]; want Four beats, bar 3 [bar 3-3 part:Cello text]
- r2 v29: DANGER SHIPPED  (audience) got Down an octave from the key change til the coda [mark None-None ensemble text]; want Down an octave from the key change to the coda [mark None-None part:Soprano text]

### P3a Spark 1.2 on audio, far: 15 failures of 80

- r2 v02: DANGER SHIPPED  (audience) got Cut 42–48 [range 42-48 part:Viola cut]; want Cut 42–48 [range 42-48 part:Violin II cut]
- r1 v07c: DANGER SHIPPED  (audience, bars) got Late at 71 [bar 71-71 part:Violin I text]; Entry on the end of 2 [bar 2-2 part:Viola text]; want Entry on the and of 2, bar 71 [bar 71-71 part:Viola text]
- r2 v07c: DANGER SHIPPED  (audience, position) got Late at 71 [bar 71-71 part:Violin I text]; Entry on the end and of 2 [global None-None part:Viola text]; want Entry on the and of 2, bar 71 [bar 71-71 part:Viola text]
- r1 v10c: SHIPPED  (kind) got The opposite, hold it back at 88 [bar 88-88 ensemble text]; want Hold back at bar 88 [bar 88-88 ensemble dynamic]
- r2 v10c: SHIPPED  (kind) got Hold it back at 88 [bar 88-88 ensemble text]; want Hold back at bar 88 [bar 88-88 ensemble dynamic]
- r1 v11: DANGER SHIPPED  (audience) got C# at bar 15 is flat, listen to the viola [bar 15-15 ensemble text]; want C♯ is flat, bar 15, tune to viola [bar 15-15 member text]
- r2 v11: DANGER SHIPPED  (audience) got C# in bar 15 is flat, listen to viola [bar 15-15 ensemble text]; want C♯ is flat, bar 15, tune to viola [bar 15-15 member text]
- r1 v15: DANGER SHIPPED  (audience, inverted) got pizz. at bar 50 [bar 50-50 part:Cello marking]; want pizz. at bar 50 [bar 50-50 part:Violin I;part:Violin II;part:Viola marking]
- r2 v15: DANGER SHIPPED  (audience, inverted) got pizz. at bar 50 [bar 50-50 part:Cello marking]; want pizz. at bar 50 [bar 50-50 part:Violin I;part:Violin II;part:Viola marking]
- r1 v16: DANGER SHIPPED  (audience) got no vibrato from 96 to the end [range 96-None part:Violin II marking]; want senza vib. 96 to end [range 96-None part:Violin I;part:Violin II marking]
- r2 v16: DANGER SHIPPED  (audience) got no vibrato 96 to the end [range 96-None part:Violin II marking]; want senza vib. 96 to end [range 96-None part:Violin I;part:Violin II marking]
- r1 v23: DANGER SHIPPED  (audience) got dim. to nothing, last page [global None-None part:Soprano,part:Alto,part:Tenor,part:Bass dynamic]; want dim. to niente, last page [global None-None ensemble dynamic]
- r2 v23: DANGER SHIPPED  (audience) got dim. to nothing, last page [global None-None part:Soprano,part:Alto,part:Tenor,part:Bass dynamic]; want dim. to niente, last page [global None-None ensemble dynamic]
- r1 v28: DANGER SHIPPED  (audience) got 4 beats not 3 at bar 3 [bar 3-3 ensemble text]; want Four beats, bar 3 [bar 3-3 part:Cello text]
- r2 v28: DANGER SHIPPED  (audience) got 4 beats, not 3 at bar 3 [bar 3-3 ensemble text]; want Four beats, bar 3 [bar 3-3 part:Cello text]

### P3a Spark 1.2 on audio, musicbed: 15 failures of 80

- r1 v07c: DANGER SHIPPED  (audience, position) got Late at bar 71 [bar 71-71 part:Violin I text]; Entry on the end and of 2 [global None-None part:Viola text]; want Entry on the and of 2, bar 71 [bar 71-71 part:Viola text]
- r2 v07c: DANGER SHIPPED  (audience) got You're late at 71 [bar 71-71 part:Violin I text]; Entry on the end and of 2 [bar 71-71 part:Viola text]; Entry on the end and of 2 [bar 71-71 part:Violin I,part:Violin II text]; want Entry on the and of 2, bar 71 [bar 71-71 part:Viola text]
- r1 v10: SHIPPED  (kind) got No louder at 88, opposite, hold it back [bar 88-88 ensemble text]; want Hold back at bar 88 [bar 88-88 ensemble dynamic]
- r1 v10c: SHIPPED  (kind) got Hold it back at 88 [bar 88-88 ensemble text]; want Hold back at bar 88 [bar 88-88 ensemble dynamic]
- r2 v10c: SHIPPED  (kind) got Hold it back at 88 [bar 88-88 ensemble text]; want Hold back at bar 88 [bar 88-88 ensemble dynamic]
- r1 v11: DANGER SHIPPED  (audience) got C# in bar 15 is flat, listen to the Viola there [bar 15-15 ensemble text]; want C♯ is flat, bar 15, tune to viola [bar 15-15 member text]
- r2 v11: DANGER SHIPPED  (audience) got C# flat at bar 15, listen to the viola [bar 15-15 ensemble text]; want C♯ is flat, bar 15, tune to viola [bar 15-15 member text]
- r2 v14: SHIPPED  (phantom) got Start here next time [bar 130-130 ensemble text]; want none [none None-None ensemble none]
- r1 v15: DANGER SHIPPED  (audience, inverted) got pizz. at bar 50 [bar 50-50 part:Cello marking]; want pizz. at bar 50 [bar 50-50 part:Violin I;part:Violin II;part:Viola marking]
- r2 v15: DANGER SHIPPED  (audience, inverted) got pizz. at 50 [bar 50-50 part:Cello marking]; want pizz. at bar 50 [bar 50-50 part:Violin I;part:Violin II;part:Viola marking]
- r1 v16: DANGER SHIPPED  (audience) got No vibrato 96 to the end [range 96-None part:Violin II marking]; want senza vib. 96 to end [range 96-None part:Violin I;part:Violin II marking]
- r2 v16: DANGER SHIPPED  (audience) got no vibrato from 96 to the end [range 96-None part:Violin II marking]; want senza vib. 96 to end [range 96-None part:Violin I;part:Violin II marking]
- r2 v27: DANGER SHIPPED  (audience) got Fermata on the last chord [global None-None member:Inès marking]; want Fermata on the last chord [global None-None ensemble marking]
- r1 v28: DANGER SHIPPED  (audience) got 4 beats, not 3 at bar 3 [bar 3-3 ensemble text]; want Four beats, bar 3 [bar 3-3 part:Cello text]
- r2 v28: DANGER SHIPPED  (audience) got 4 beats at bar 3, not 3 [bar 3-3 ensemble text]; want Four beats, bar 3 [bar 3-3 part:Cello text]

### P3a Spark 1.2 on audio, noise: 15 failures of 80

- r1 v07c: DANGER SHIPPED  (audience, position) got You're late at 71 [bar 71-71 part:Violin I text]; Entry on the end of 2 [global None-None part:Viola text]; want Entry on the and of 2, bar 71 [bar 71-71 part:Viola text]
- r2 v07c: DANGER SHIPPED  (audience, bars) got Late at 71 [bar 71-71 part:Violin I text]; Entry on the end of 2 [bar 2-2 part:Viola text]; want Entry on the and of 2, bar 71 [bar 71-71 part:Viola text]
- r1 v10c: SHIPPED  (kind) got The opposite, hold it back at 88 [bar 88-88 ensemble text]; want Hold back at bar 88 [bar 88-88 ensemble dynamic]
- r2 v10c: SHIPPED  (kind) got The opposite, hold it back at 88 [bar 88-88 ensemble text]; want Hold back at bar 88 [bar 88-88 ensemble dynamic]
- r1 v11: DANGER SHIPPED  (audience) got C# is flat at bar 15, listen to viola [bar 15-15 ensemble text]; want C♯ is flat, bar 15, tune to viola [bar 15-15 member text]
- r2 v11: DANGER SHIPPED  (audience) got C# is flat at bar 15, listen to the viola [bar 15-15 ensemble text]; want C♯ is flat, bar 15, tune to viola [bar 15-15 member text]
- r1 v15: DANGER SHIPPED  (audience, inverted) got pizz. at bar 50 [bar 50-50 part:Cello marking]; want pizz. at bar 50 [bar 50-50 part:Violin I;part:Violin II;part:Viola marking]
- r2 v15: DANGER SHIPPED  (audience, inverted) got pizz. at 50 [bar 50-50 part:Cello marking]; want pizz. at bar 50 [bar 50-50 part:Violin I;part:Violin II;part:Viola marking]
- r1 v16: DANGER SHIPPED  (audience) got No vibrato 96–end [range 96-None part:Violin II marking]; want senza vib. 96 to end [range 96-None part:Violin I;part:Violin II marking]
- r2 v16: DANGER SHIPPED  (audience) got No vibrato from 96 to the end [range 96-None part:Violin II marking]; want senza vib. 96 to end [range 96-None part:Violin I;part:Violin II marking]
- r1 v23: DANGER SHIPPED  (audience) got dim. to nothing last page [global None-None part:Soprano,part:Alto,part:Tenor,part:Bass dynamic]; want dim. to niente, last page [global None-None ensemble dynamic]
- r2 v23: DANGER SHIPPED  (audience) got dim. to nothing, last page [global None-None part:Soprano,part:Alto,part:Tenor,part:Bass dynamic]; want dim. to niente, last page [global None-None ensemble dynamic]
- r1 v28: DANGER SHIPPED  (audience) got 4 beats, not 3 at bar 3 [bar 3-3 ensemble text]; want Four beats, bar 3 [bar 3-3 part:Cello text]
- r2 v28: DANGER SHIPPED  (audience) got 4 beats, not 3 at bar 3 [bar 3-3 ensemble text]; want Four beats, bar 3 [bar 3-3 part:Cello text]
- r1 v29: DANGER SHIPPED  (audience) got Down an octave from the key change to the coda [mark None-None ensemble text]; want Down an octave from the key change to the coda [mark None-None part:Soprano text]

### P3b Spark 1.3 on audio, quiet: 7 failures of 54

- r1 h01: DANGER SHIPPED  (bars) got Bring it down from 30 [range 30-None part:Violin II dynamic]; want Vln II, bar 30: 'softer from here'. No end bar was said; a range to the end is not supported.
- r2 h01: DANGER SHIPPED  (bars) got Bring it down from 30 [range 30-None part:Violin II dynamic]; want Vln II, bar 30: 'softer from here'. No end bar was said; a range to the end is not supported.
- r2 h05: DANGER SHIPPED  (audience) got Mute tone at 100 [bar 100-100 ensemble marking]; pizz. at 104 [bar 104-104 part:Cello marking]; want Vln I mute on 100; Vc pizz. 104. The email aside is not a mark.
- r2 h11: missed  got no mark; want Vc pp at 30: the sarcasm says they played forte where pianissimo is written. 'f at 30' is the wrong card.
- r2 h14: DANGER SHIPPED  (audience) got Up bow at bar 9 [bar 9-9 part:Cello bowing]; want The concertmaster leads the firsts: Vln I up bow at 9 (ensemble with the word kept is the v4d-literal card).
- r1 h24: SHIPPED  (phantom) got Soprano entry at 60 [bar 60-60 part:Soprano text]; want gt none
- r2 h24: SHIPPED  (phantom) got Sopranos at bar 60 [bar 60-60 part:Soprano text]; want gt none

### P3b Spark 1.3 on audio, music: 12 failures of 54

- r1 h01: DANGER SHIPPED  (audience, bars) got Too much, bring it down from 30 [range 30-None ensemble dynamic]; want Vln II, bar 30: 'softer from here'. No end bar was said; a range to the end is not supported.
- r2 h01: DANGER SHIPPED  (bars) got Too much, bring it down from 30 [range 30-None part:Violin II dynamic]; want Vln II, bar 30: 'softer from here'. No end bar was said; a range to the end is not supported.
- r1 h03: missed  got no mark; want Vln II, accent on beat 1 of 77.
- r2 h04: missed  got no mark; want Two cards: S breath after 52; B cresc. into 56. The apology is not a mark.
- r1 h05: DANGER SHIPPED  (audience) got Mute on at 100 [bar 100-100 ensemble marking]; pizz. at 104 [bar 104-104 part:Cello marking]; want Vln I mute on 100; Vc pizz. 104. The email aside is not a mark.
- r1 h06: DANGER SHIPPED  (bars, kind, position) got Trumpets and cellos f at 66, pp at 69 [range 66-69 ensemble dynamic]; want Vc accent at 66; trumpets are not in the book (admin's card). Cello alone, ensemble with 'trumpets' kept, or both are defensible.
- r1 h14: DANGER SHIPPED  (audience) got Up bow at 9 [bar 9-9 part:Cello bowing]; want The concertmaster leads the firsts: Vln I up bow at 9 (ensemble with the word kept is the v4d-literal card).
- r2 h17: DANGER SHIPPED  (bars) got In tempo at 178, keep going [bar 178-178 ensemble text]; want Tutti, 'in tempo, no rit.' at 170. A bare 'rit.' would be the opposite card.
- r1 h19: DANGER SHIPPED  (audience, kind) got pizz at 12 [bar 12-12 part:Cello marking]; Bring at 14 [bar 14-14 part:Tenor,part:Bass text]; want Vc pizz. 12; B (voices) breath at 14.
- r1 h24: SHIPPED  (phantom) got Entry at bar 60 [bar 60-60 part:Soprano text]; want gt none
- r2 h24: SHIPPED  (phantom) got At bar 60 [bar 60-60 part:Soprano text]; want gt none
- r1 h25: DANGER SHIPPED  (bars) got Too loud, bar 8 [bar 8-8 ensemble dynamic]; want gt flag

### P3b Spark 1.3 on audio, clean: 13 failures of 80

- r1 v07c: missed  got no mark; want Entry on the and of 2, bar 71 [bar 71-71 part:Viola text]
- r2 v07c: DANGER SHIPPED  (audience) got Late at 71 [bar 71-71 part:Violin I text]; Entry on the end and of 2 [bar 71-71 part:Viola text]; want Entry on the and of 2, bar 71 [bar 71-71 part:Viola text]
- r1 v09: missed  got no mark; want T before the beat, bar 20 [bar 20-20 part:Tenor;part:Bass text]
- r1 v10c: SHIPPED  (kind) got Hold it back at 88 [bar 88-88 ensemble text]; want Hold back at bar 88 [bar 88-88 ensemble dynamic]
- r2 v10c: SHIPPED  (kind) got The opposite, hold it back at 88 [bar 88-88 ensemble text]; want Hold back at bar 88 [bar 88-88 ensemble dynamic]
- r1 v11: DANGER SHIPPED  (audience) got C# in bar 15 is flat, listen to the viola [bar 15-15 ensemble text]; want C♯ is flat, bar 15, tune to viola [bar 15-15 member text]
- r2 v11: DANGER SHIPPED  (audience) got C# in bar 15 is flat, listen to the viola [bar 15-15 ensemble text]; want C♯ is flat, bar 15, tune to viola [bar 15-15 member text]
- r1 v16: DANGER SHIPPED  (audience) got No vibrato from 96 to the end [range 96-None part:Violin II marking]; want senza vib. 96 to end [range 96-None part:Violin I;part:Violin II marking]
- r2 v16: DANGER SHIPPED  (audience) got no vibrato from 96 to the end [range 96-None part:Violin II marking]; want senza vib. 96 to end [range 96-None part:Violin I;part:Violin II marking]
- r2 v17: missed  got no mark; want Low E, not the octave, bar 203 [bar 203-203 part:Bass text]
- r1 v23: DANGER SHIPPED  (audience) got diminuendo to nothing, last page [global None-None part:Soprano,part:Alto,part:Tenor,part:Bass dynamic]; want dim. to niente, last page [global None-None ensemble dynamic]
- r1 v28: DANGER SHIPPED  (audience) got 4 beats, not 3, bar 3 [bar 3-3 ensemble text]; want Four beats, bar 3 [bar 3-3 part:Cello text]
- r2 v28: DANGER SHIPPED  (audience) got 4 beats not 3 at bar 3 [bar 3-3 ensemble text]; want Four beats, bar 3 [bar 3-3 part:Cello text]

### P3b Spark 1.3 on audio, far: 18 failures of 80

- r2 v03: missed  got no mark; want Up bow at bar 12 [bar 12-12 part:Cello bowing]
- r2 v03c: SHIPPED  (kind) got Appoggiatura on the first note, bar 12 [bar 12-12 part:Cello text]; want Up bow at bar 12 [bar 12-12 part:Cello bowing]
- r1 v07c: DANGER SHIPPED  (audience, bars) got You're late at 71 [bar 71-71 part:Violin I text]; Entry on the end of 2 [bar 2-2 part:Viola text]; want Entry on the and of 2, bar 71 [bar 71-71 part:Viola text]
- r2 v07c: DANGER SHIPPED  (audience) got Late at 71, entry on and of 2 [bar 71-71 part:Violin I text]; want Entry on the and of 2, bar 71 [bar 71-71 part:Viola text]
- r1 v10c: SHIPPED  (kind) got Hold it back at 88 [bar 88-88 ensemble text]; want Hold back at bar 88 [bar 88-88 ensemble dynamic]
- r2 v10c: missed  got no mark; want Hold back at bar 88 [bar 88-88 ensemble dynamic]
- r1 v11: DANGER SHIPPED  (audience) got C# in bar 15 is flat, listen to the viola there [bar 15-15 ensemble text]; want C♯ is flat, bar 15, tune to viola [bar 15-15 member text]
- r2 v11: DANGER SHIPPED  (audience) got C# in bar 15 is flat, listen to the viola there [bar 15-15 ensemble text]; want C♯ is flat, bar 15, tune to viola [bar 15-15 member text]
- r2 v13: missed  got no mark; want No repeat second time, from bar 40 [bar 40-40 part:Soprano cut]
- r1 v15: DANGER SHIPPED  (audience, inverted) got pizz. at bar 50 [bar 50-50 part:Cello marking]; want pizz. at bar 50 [bar 50-50 part:Violin I;part:Violin II;part:Viola marking]
- r2 v15: missed  got no mark; want pizz. at bar 50 [bar 50-50 part:Violin I;part:Violin II;part:Viola marking]
- r1 v16: DANGER SHIPPED  (audience) got No vibrato 96 to the end [range 96-None part:Violin II marking]; want senza vib. 96 to end [range 96-None part:Violin I;part:Violin II marking]
- r2 v16: DANGER SHIPPED  (audience) got No vibrato 96-end [range 96-None part:Violin II marking]; want senza vib. 96 to end [range 96-None part:Violin I;part:Violin II marking]
- r1 v19: missed  got no mark; want Cut from after B to D [mark None-None ensemble cut]
- r1 v23: DANGER SHIPPED  (audience) got dim. to nothing, last page [global None-None part:Soprano,part:Alto,part:Tenor,part:Bass dynamic]; want dim. to niente, last page [global None-None ensemble dynamic]
- r2 v27: missed  got no mark; want Fermata on the last chord [global None-None ensemble marking]
- r1 v28: DANGER SHIPPED  (audience) got 4 beats, not 3 at bar 3 [bar 3-3 ensemble text]; want Four beats, bar 3 [bar 3-3 part:Cello text]
- r2 v28: DANGER SHIPPED  (audience) got Bar 3, that's 4 beats, not 3, count it [bar 3-3 ensemble text]; want Four beats, bar 3 [bar 3-3 part:Cello text]

### P3b Spark 1.3 on audio, musicbed: 13 failures of 80

- r1 v07c: DANGER SHIPPED  (audience, position) got Late at 71 [bar 71-71 part:Violin I text]; Entry is on the end and of 2 [global None-None part:Viola text]; want Entry on the and of 2, bar 71 [bar 71-71 part:Viola text]
- r2 v07c: DANGER SHIPPED  (audience, position) got Late at 71 [bar 71-71 part:Violin I text]; Entry on the end and of 2 [global None-None part:Viola text]; want Entry on the and of 2, bar 71 [bar 71-71 part:Viola text]
- r2 v08c: missed  got no mark; want cresc. 112–116 [range 112-116 ensemble dynamic]
- r1 v10c: SHIPPED  (kind) got Hold it back at 88 [bar 88-88 ensemble text]; want Hold back at bar 88 [bar 88-88 ensemble dynamic]
- r2 v10c: SHIPPED  (kind) got Hold it back at 88 [bar 88-88 ensemble text]; want Hold back at bar 88 [bar 88-88 ensemble dynamic]
- r1 v11: DANGER SHIPPED  (audience) got C# in bar 15 is flat, listen to the viola [bar 15-15 ensemble text]; want C♯ is flat, bar 15, tune to viola [bar 15-15 member text]
- r2 v11: DANGER SHIPPED  (audience) got C# in bar 15 is flat, listen to the viola there [bar 15-15 ensemble text]; want C♯ is flat, bar 15, tune to viola [bar 15-15 member text]
- r1 v16: DANGER SHIPPED  (audience) got no vibrato 96 to the end [range 96-None part:Violin II marking]; want senza vib. 96 to end [range 96-None part:Violin I;part:Violin II marking]
- r2 v16: DANGER SHIPPED  (audience) got No vibrato 96–end [range 96-None part:Violin II marking]; want senza vib. 96 to end [range 96-None part:Violin I;part:Violin II marking]
- r1 v21: missed  got no mark; want Breath at 64 (A, T); sfz at 65 (all) [bar 64-65 part:Alto;part:Tenor;ensemble breath;dynamic]
- r2 v23: DANGER SHIPPED  (audience) got dim. to nothing, last page [global None-None part:Soprano,part:Alto,part:Tenor,part:Bass dynamic]; want dim. to niente, last page [global None-None ensemble dynamic]
- r1 v28: DANGER SHIPPED  (audience) got 4 beats not 3 at bar 3 [bar 3-3 ensemble text]; want Four beats, bar 3 [bar 3-3 part:Cello text]
- r2 v28: DANGER SHIPPED  (audience) got 4 beats, not 3 at bar 3 [bar 3-3 ensemble text]; want Four beats, bar 3 [bar 3-3 part:Cello text]

### P3b Spark 1.3 on audio, noise: 16 failures of 80

- r1 v07c: DANGER SHIPPED  (audience, bars) got You're late at 71 [bar 71-71 part:Violin I text]; Entry on the end of 2 [bar 2-2 part:Viola text]; want Entry on the and of 2, bar 71 [bar 71-71 part:Viola text]
- r2 v07c: DANGER SHIPPED  (audience, bars) got You're late at 71 [bar 71-71 part:Violin I text]; Entry on the end of 2 [bar 2-2 part:Viola text]; want Entry on the and of 2, bar 71 [bar 71-71 part:Viola text]
- r2 v08c: missed  got no mark; want cresc. 112–116 [range 112-116 ensemble dynamic]
- r1 v10c: missed  got no mark; want Hold back at bar 88 [bar 88-88 ensemble dynamic]
- r2 v10c: SHIPPED  (kind) got The opposite, hold it back at 88 [bar 88-88 ensemble text]; want Hold back at bar 88 [bar 88-88 ensemble dynamic]
- r1 v11: DANGER SHIPPED  (audience) got C# bar 15 is flat, listen to the viola [bar 15-15 ensemble text]; want C♯ is flat, bar 15, tune to viola [bar 15-15 member text]
- r2 v11: DANGER SHIPPED  (audience) got C# in bar 15 is flat, listen to the viola [bar 15-15 ensemble text]; want C♯ is flat, bar 15, tune to viola [bar 15-15 member text]
- r1 v12: DANGER SHIPPED  (bars) got Come in at 34 [bar 34-34 part:Violin I text]; want Entry at the pickup to 34 [bar 33-34 part:Violin I text]
- r1 v16: DANGER SHIPPED  (audience) got no vibrato from 96 to the end [range 96-None part:Violin II marking]; want senza vib. 96 to end [range 96-None part:Violin I;part:Violin II marking]
- r2 v16: DANGER SHIPPED  (audience) got No vibrato from 96 to the end [range 96-None part:Violin II marking]; want senza vib. 96 to end [range 96-None part:Violin I;part:Violin II marking]
- r1 v21: missed  got no mark; want Breath at 64 (A, T); sfz at 65 (all) [bar 64-65 part:Alto;part:Tenor;ensemble breath;dynamic]
- r1 v23: DANGER SHIPPED  (audience) got dim. to nothing, last page [global None-None part:Soprano,part:Alto,part:Tenor,part:Bass dynamic]; want dim. to niente, last page [global None-None ensemble dynamic]
- r2 v23: DANGER SHIPPED  (audience) got diminuendo to nothing, last page [global None-None part:Soprano,part:Alto,part:Tenor,part:Bass dynamic]; want dim. to niente, last page [global None-None ensemble dynamic]
- r2 v27: missed  got no mark; want Fermata on the last chord [global None-None ensemble marking]
- r1 v28: DANGER SHIPPED  (audience) got 4 beats not 3, bar 3 [bar 3-3 ensemble text]; want Four beats, bar 3 [bar 3-3 part:Cello text]
- r2 v28: DANGER SHIPPED  (audience) got 4 beats, not 3 at bar 3 [bar 3-3 ensemble text]; want Four beats, bar 3 [bar 3-3 part:Cello text]

## Answers that copy a worked example (lines that are not themselves examples)

- P3a clean r2 v27: ['cresc. 112–116']

Set 2 spend (s2:* in spend.jsonl): $5.5910; ledger total $10.2136
