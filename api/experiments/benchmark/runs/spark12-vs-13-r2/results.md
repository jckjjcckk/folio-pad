# Benchmark run `spark12-vs-13-r2`

Updated 2026-11-01 21:04. 54 calls in the ledger. Spend this run: Meta $0.3988 of $2.00, Claude $0.0000 of $0.00.

| task | model | effort | res | items | accuracy | $ total | $ / item | s / item | JSON fail (1st try) | unparsed | errors |
|---|---|---|---|---|---|---|---|---|---|---|---|
| closed | muse-spark-1.2 | low | 150dpi | 11 | right 0.818 | 0.0425 | 0.0039 | 4.8 | 0.0 | 0 | 0 |
| closed | muse-spark-1.3 | low | 150dpi | 11 | right 0.727 | 0.0499 | 0.0045 | 5.5 | 0.0 | 0 | 0 |
| header | muse-spark-1.2 | low | 150dpi | 3 | staves 3/3, instruments 3/3, boxes 1.0 | 0.0495 | 0.0165 | 19.8 | 0.0 | 0 | 0 |
| header | muse-spark-1.3 | low | 150dpi | 3 | staves 3/3, instruments 3/3, boxes 1.0 | 0.0427 | 0.0142 | 14.3 | 0.0 | 0 | 0 |
| labels | muse-spark-1.2 | minimal | 150dpi | 7 | systems 0.917, pages 6 | 0.0766 | 0.0109 | 6.7 | 0.0 | 0 | 0 |
| labels | muse-spark-1.3 | minimal | 150dpi | 7 | systems 1.0, pages 7 | 0.0680 | 0.0097 | 6.3 | 0.0 | 0 | 0 |
| text | muse-spark-1.2 | minimal | 150dpi | 6 | text F1 0.917 (P 0.917 R 0.917) | 0.0391 | 0.0065 | 6.9 | 0.0 | 0 | 0 |
| text | muse-spark-1.3 | minimal | 150dpi | 6 | text F1 0.917 (P 0.917 R 0.917) | 0.0305 | 0.0051 | 5.1 | 0.0 | 0 | 0 |

Cumulative spend (spend.json, all runs): Meta $2.2847, Claude $0.8857.
