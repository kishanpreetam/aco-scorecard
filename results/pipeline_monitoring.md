# Pipeline monitoring report

Generated 2026-11-04T04:15:59+00:00.

## Checks

| check | result | detail |
|---|---|---|
| dbt build: every model, seed, data test and unit test passed | pass | 271 nodes, 0 not passing |
| semantic layer answers match independent SQL | pass | 12/12 questions, 42/42 values |
| every source file matches its sha256 pin | pass | 29 files |
| all 13 PUF performance periods loaded | pass | 13 loaded |
| row counts unchanged since the previous run | pass | no differences from the run at 2026-11-04T04:15:40+00:00 |
| no new or revised CMS files waiting in the catalog | pass | checked 2026-11-04T04:11:30+00:00: 0 not pinned, 0 pinned files missing |

## Sources

23 data files (62,917,675 bytes) and 6 data dictionaries (3,572,562 bytes) from data.cms.gov. Latest performance year loaded: 2024. Most recently revised file: puf_py2024 (Fri, 17 Jul 2026 10:54:25 GMT).

| file | period | bytes | CMS last modified | days since CMS update | pin |
|---|---|---|---|---|---|
| puf_py2013 | 2013 | 103,682 | Tue, 28 Nov 2023 16:36:34 GMT | 1071 | verified |
| puf_py2014 | 2014 | 206,638 | Tue, 28 Nov 2023 16:35:06 GMT | 1071 | verified |
| puf_py2015 | 2015 | 232,103 | Tue, 28 Nov 2023 17:37:15 GMT | 1071 | verified |
| puf_py2016 | 2016 | 364,522 | Mon, 04 Dec 2023 17:09:21 GMT | 1065 | verified |
| puf_py2017 | 2017 | 397,254 | Tue, 28 Nov 2023 16:26:51 GMT | 1071 | verified |
| puf_py2018 | 2018 | 471,086 | Tue, 28 Nov 2023 16:29:27 GMT | 1071 | verified |
| puf_py2019 | 2019 | 392,694 | Tue, 28 Nov 2023 16:31:22 GMT | 1071 | verified |
| puf_py2019a | 2019A | 193,199 | Tue, 06 Aug 2024 12:44:16 GMT | 819 | verified |
| puf_py2020 | 2020 | 382,676 | Tue, 31 Oct 2023 13:40:26 GMT | 1099 | verified |
| puf_py2021 | 2021 | 469,381 | Thu, 07 Sep 2023 16:45:01 GMT | 1153 | verified |
| puf_py2022 | 2022 | 397,030 | Thu, 07 Mar 2024 15:33:18 GMT | 971 | verified |
| puf_py2023 | 2023 | 381,089 | Wed, 23 Oct 2024 18:47:12 GMT | 741 | verified |
| puf_py2024 | 2024 | 437,855 | Fri, 17 Jul 2026 10:54:25 GMT | 109 | verified |
| county_py2016 | 2016 | 4,421,455 | Tue, 30 Nov 2021 18:27:52 GMT | 1799 | verified |
| county_py2017 | 2017 | 5,563,732 | Tue, 30 Nov 2021 18:26:23 GMT | 1799 | verified |
| county_py2018 | 2018 | 6,503,795 | Tue, 30 Nov 2021 18:24:49 GMT | 1799 | verified |
| county_py2019 | 2019 | 6,091,842 | Tue, 30 Nov 2021 18:18:13 GMT | 1799 | verified |
| county_py2019a | 2019A | 2,796,184 | Tue, 30 Nov 2021 18:21:13 GMT | 1799 | verified |
| county_py2020 | 2020 | 6,728,528 | Tue, 30 Nov 2021 18:15:51 GMT | 1799 | verified |
| county_py2021 | 2021 | 6,397,391 | Tue, 20 Sep 2022 15:02:05 GMT | 1505 | verified |
| county_py2022 | 2022 | 6,764,277 | Thu, 14 Sep 2023 13:39:52 GMT | 1146 | verified |
| county_py2023 | 2023 | 6,495,900 | Fri, 08 Nov 2024 15:32:28 GMT | 725 | verified |
| county_py2024 | 2024 | 6,725,362 | Wed, 05 Nov 2025 12:31:20 GMT | 363 | verified |
| dict_puf_2013_2020 |  | 669,617 | Tue, 25 Mar 2025 13:39:06 GMT | 588 | verified |
| dict_puf_2021 |  | 419,577 | Tue, 25 Mar 2025 13:39:25 GMT | 588 | verified |
| dict_puf_2022 |  | 494,270 | Tue, 25 Mar 2025 13:38:47 GMT | 588 | verified |
| dict_puf_2023 |  | 1,304,387 | Tue, 25 Mar 2025 13:36:40 GMT | 588 | verified |
| dict_puf_2024 |  | 503,365 | Wed, 26 Nov 2025 15:08:33 GMT | 342 | verified |
| dict_county_current |  | 181,346 | Mon, 17 Nov 2025 19:17:26 GMT | 351 | verified |

## dbt build

dbt 1.12.6, 271 nodes in 13.65 seconds.

| resource type | status counts |
|---|---|
| model | success: 53 |
| seed | success: 4 |
| test | pass: 212 |
| unit_test | pass: 2 |

## Semantic layer

12 of 12 business questions passed; 42 of 42 values matched plain SQL.

## Row counts

| relation | type | rows |
|---|---|---|
| core.dim_aco | table | 1,059 |
| core.dim_enrollment_type | table | 4 |
| core.dim_measure | table | 43 |
| core.dim_performance_year | table | 13 |
| core.dim_track | table | 10 |
| core.fct_aco_county_assignment | table | 1,185,051 |
| core.fct_aco_financial_year | table | 5,476 |
| core.fct_aco_quality_measure | table | 128,010 |
| core.fct_attribution | table | 21,904 |
| core.metricflow_time_spine | table | 5,479 |
| intermediate.int_aco_id_bridge | table | 405 |
| intermediate.int_aco_period__keyed | table | 5,476 |
| intermediate.int_county__unioned | table | 1,185,051 |
| intermediate.int_puf__unioned | table | 5,476 |
| intermediate.int_quality__unioned | table | 128,010 |
| raw._load_audit | table | 23 |
| raw.county_py2016 | table | 98,208 |
| raw.county_py2017 | table | 109,900 |
| raw.county_py2018 | table | 131,165 |
| raw.county_py2019 | table | 122,627 |
| raw.county_py2019a | table | 56,444 |
| raw.county_py2020 | table | 135,418 |
| raw.county_py2021 | table | 130,186 |
| raw.county_py2022 | table | 136,150 |
| raw.county_py2023 | table | 129,750 |
| raw.county_py2024 | table | 135,203 |
| raw.puf_py2013 | table | 220 |
| raw.puf_py2014 | table | 333 |
| raw.puf_py2015 | table | 392 |
| raw.puf_py2016 | table | 432 |
| raw.puf_py2017 | table | 472 |
| raw.puf_py2018 | table | 548 |
| raw.puf_py2019 | table | 475 |
| raw.puf_py2019a | table | 205 |
| raw.puf_py2020 | table | 513 |
| raw.puf_py2021 | table | 475 |
| raw.puf_py2022 | table | 482 |
| raw.puf_py2023 | table | 453 |
| raw.puf_py2024 | table | 476 |
| reference.enrollment_types | table | 4 |
| reference.measure_catalog | table | 43 |
| reference.performance_periods | table | 13 |
| reference.track_reference | table | 10 |
| reporting.mart_aco_year_scorecard | table | 5,337 |
| reporting.mart_program_year_summary | table | 12 |
| reporting.mart_quality_measure_year | table | 257 |
| reporting.mart_state_year_assignment | table | 504 |
| reporting.mart_track_year_summary | table | 46 |
| staging (33 views) | view | 1,318,537 |

## Data health

- ACO identifier bridge (PY 2017 to PY 2018): 405 of 472 PY 2017 ACOs linked (85.8%); 95.3% of the 425 PY 2018 ACOs that started before 2018.
- ACO keys by method: bridged_legacy_id 405, legacy_id_only 219, published_aco_id 435.
- County files: reported (unsuppressed) county person years as a share of PUF person years: 2016 97.9%, 2017 97.9%, 2018 97.8%, 2019 97.9%, 2019A 97.5%, 2020 97.8%, 2021 97.7%, 2022 97.7%, 2023 97.8%, 2024 97.7%.
- Quality results reported share: 2016 99.2%, 2017 99.3%, 2018 99.7%, 2019 99.2%, 2019A 99.1%, 2020 47.1%, 2021 87.1%, 2022 77.0%, 2023 74.2%, 2024 64.5%.
- ACO rows with a suppressed enrollment type cell: 2015 1, 2017 4, 2018 6, 2019 7, 2020 7, 2021 4, 2022 18, 2023 42, 2024 43.
- Quality score not published (pay for reporting): 2014 119, 2015 89.
