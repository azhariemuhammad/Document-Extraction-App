# Evaluation results

## tax_form_spt_1771__tax_form_fields.json vs tax_form.json (gold status: UNVERIFIED)

| Metric | Value |
|---|---|
| Gold items verified / pending | 31 / 1 |
| Field accuracy | 18/21 = 86% |
| Checkbox accuracy | 2/10 = 20% |
| Table-cell accuracy | n/a (no verified items) |
| Chart accuracy | n/a (no verified items) |
| Page coverage (gold) | n/a (no verified items) |
| Chart value error (mean relative) | n/a (no verified items) |
| Grounded-evidence rate | n/a |
| Page coverage | 100% |
| Arithmetic checks passed | 3/4 |
| Latency per page | 5.9 s |
| Tokens (in / out) | 1500 / 2126 |
| Retries | 0 |
| Failed pages | 0 |

Accuracy per gold kind:

| Kind | Correct | Total |
|---|---|---|
| checkbox | 2 | 10 |
| field | 18 | 21 |

Failed items:

| Id | Key | Expected | Got |
|---|---|---|---|
| T01 | TAHUN PAJAK | 2021 | not found |
| T05 | KLU | unreadable | not found |
| T08 | DIAUDIT | False | not found |
| T13 | 4a | False | not found |
| T23 | 9a | True | not found |
| T24 | 9b | False | not found |
| T27 | 11a | False | not found |
| T28 | 11b | False | not found |
| T29 | 11 | 1900100 | not found |
| T31 | 13a | False | not found |
| T32 | 13b | False | not found |

Pending owner check (excluded from scores): T14 4b (checkbox)

## research_paper_applied_ergonomics__full_document.json vs research_pdf.json (gold status: UNVERIFIED)

| Metric | Value |
|---|---|
| Gold items verified / pending | 20 / 17 |
| Field accuracy | 0/3 = 0% |
| Checkbox accuracy | n/a (no verified items) |
| Table-cell accuracy | 8/17 = 47% |
| Chart accuracy | n/a (no verified items) |
| Page coverage (gold) | n/a (no verified items) |
| Chart value error (mean relative) | n/a (no verified items) |
| Grounded-evidence rate | 97% |
| Page coverage | 100% |
| Arithmetic checks passed | n/a |
| Latency per page | 31.1 s |
| Tokens (in / out) | 61132 / 34880 |
| Retries | 7 |
| Failed pages | 0 |

Accuracy per gold kind:

| Kind | Correct | Total |
|---|---|---|
| table_cell | 8 | 16 |
| table_row | 0 | 1 |
| text | 0 | 3 |

Failed items:

| Id | Key | Expected | Got |
|---|---|---|---|
| R01 | None | A head mounted augmented reality design practice for maintenance as... | not found |
| R02 | None | Dedy Ariansyah | not found |
| R03 | None | 14% | not found |
| R05 | Table 1 | HMD types | not found |
| R06 | Table 1 | LOD | not found |
| R07 | Table 2 | ['Transitioning', 'Verbal', 'Vocal'] | not found |
| R08 | Table 3 | 11 | not found |
| R09 | Table 3 | 26.6 (4.55) | not found |
| R10 | Table 3 | 219.5 (437.05) | not found |
| R11 | Table 3 | -.739* | not found |
| R12 | Table 3 | .725* | not found |
| R22 | Table 7 | F = 1.454 (p = 0.247) | not found |

Pending owner check (excluded from scores): R21 Table 6 (table_cell), R23 Fig. 2 (chart_value), R24 Fig. 2 (chart_value), R25 Fig. 2 (chart_value), R26 Fig. 2 (chart_value), R27 Fig. 2 (chart_label), R28 Fig. 3 (chart_value), R29 Fig. 3 (chart_value), R30 Fig. 4 (chart_value), R31 Fig. 4 (chart_value), R32 Fig. 4 (chart_value), R33 Fig. 4 (chart_value), R34 Fig. 5 (chart_value), R35 Fig. 5 (chart_value), R36 Fig. 5 (chart_value), R37 Fig.* (status_all), R38 None (coverage)
