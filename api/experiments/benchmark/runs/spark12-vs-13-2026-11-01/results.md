# Benchmark run `spark12-vs-13-2026-11-01`

Updated 2026-11-01 21:01. 54 calls in the ledger. Spend this run: Meta $0.4304 of $2.00, Claude $0.0000 of $0.00.

| task | model | effort | res | items | accuracy | $ total | $ / item | s / item | JSON fail (1st try) | unparsed | errors |
|---|---|---|---|---|---|---|---|---|---|---|---|
| closed | muse-spark-1.2 | low | 150dpi | 11 | right 0.727 | 0.0455 | 0.0041 | 4.9 | 0.0 | 0 | 0 |
| closed | muse-spark-1.3 | low | 150dpi | 11 | right 0.818 | 0.0529 | 0.0048 | 5.7 | 0.0 | 0 | 0 |
| header | muse-spark-1.2 | low | 150dpi | 3 | staves 3/3, instruments 3/3, boxes 1.0 | 0.0615 | 0.0205 | 16.1 | 0.0 | 0 | 0 |
| header | muse-spark-1.3 | low | 150dpi | 3 | staves 3/3, instruments 3/3, boxes 1.0 | 0.0566 | 0.0189 | 16.7 | 0.0 | 0 | 0 |
| labels | muse-spark-1.2 | minimal | 150dpi | 7 | systems 1.0, pages 7 | 0.0832 | 0.0119 | 7.6 | 0.0 | 0 | 0 |
| labels | muse-spark-1.3 | minimal | 150dpi | 7 | systems 1.0, pages 7 | 0.0649 | 0.0093 | 6.9 | 0.0 | 0 | 0 |
| text | muse-spark-1.2 | minimal | 150dpi | 6 | text F1 0.917 (P 0.917 R 0.917) | 0.0341 | 0.0057 | 5.8 | 0.0 | 0 | 0 |
| text | muse-spark-1.3 | minimal | 150dpi | 6 | text F1 0.917 (P 0.917 R 0.917) | 0.0317 | 0.0053 | 5.2 | 0.0 | 0 | 0 |

Cumulative spend (spend.json, all runs): Meta $1.8859, Claude $0.8857.
