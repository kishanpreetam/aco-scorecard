# ACO Scorecard

Medicare Shared Savings Program analytics on public CMS data: a tested dbt warehouse on DuckDB, a
governed MetricFlow semantic layer checked against real business questions, pipeline monitoring and a
static dashboard. It covers every published performance year, PY 2013 to PY 2024 (13 files, because
PY 2019 has two), plus nine years of county-level assignment files.

Everything in this README comes from the run saved in `results/`.

## What it does

1. **Downloads** the CMS Performance Year Financial and Quality Results files and the Number of ACO
   Assigned Beneficiaries by County files from data.cms.gov, found through the catalog
   (`data.json`). Each file's URL, size, sha256, HTTP Last-Modified date and data dictionary are
   recorded (`results/download_manifest.json`); later downloads must match the sha256 pins in
   `config/pins.json`, and the dictionary PDFs must match the md5 checksums CMS publishes.
2. **Loads** each CSV into DuckDB as text exactly as published, after checking that every column the
   schema mapping needs is present and that no quality measure column would be dropped silently.
3. **Maps** a decade of schema changes explicitly in `config/schema_mapping.yml`: renamed columns,
   rates published as fractions in some years and percents in others, an identifier switch in 2018,
   recoded tracks and a new quality measure set in 2021. A generator turns the YAML into one dbt
   staging model per file (33 models), so every year's SQL is readable.
4. **Models** a star schema in dbt: conformed dimensions (`dim_aco`, `dim_performance_year`,
   `dim_track`, `dim_measure`, `dim_enrollment_type`), facts (`fct_aco_financial_year`,
   `fct_aco_quality_measure`, `fct_attribution`, `fct_aco_county_assignment`) and reporting marts written
   with CTEs and window functions (year over year change with `LAG`, `RANK`, `PERCENT_RANK`, `NTILE`,
   rolling and running totals).
5. **Defines each metric once** in dbt semantic models and serves it through MetricFlow (savings rate,
   earned shared savings per assigned beneficiary, net savings to Medicare, risk-adjusted per capita
   spending, mean quality score and more). Twelve business questions are answered through MetricFlow
   and, separately, by plain SQL written on the raw files; all must agree.
6. **Tests and monitors**: 212 dbt data tests (including reconciliations such as benchmark minus
   expenditures equaling the published savings, totals equaling per capita values times person
   years, and earned savings never exceeding generated savings times the sharing rate), 2 dbt unit
   tests, a pytest suite, and a monitoring report with source freshness, row counts, test results and
   data health indicators.
7. **Publishes** a single-file HTML dashboard (`results/dashboard.html`) and the metrics behind it
   (`results/metrics.json`).

## Results

Program results by performance year, from `results/metrics.json` (PY 2019 combines both periods;
dollars are nominal):

| PY | ACOs | assigned beneficiaries | savings rate | total savings | shared savings paid | net to Medicare | share earning savings |
|---|---|---|---|---|---|---|---|
| 2013 | 220 | 3.68M | 0.55% | $233.6M | $315.9M | -$78.3M | 23.6% |
| 2014 | 333 | 5.33M | 0.55% | $291.5M | $341.2M | -$49.8M | 25.8% |
| 2015 | 392 | 7.27M | 0.59% | $429.3M | $645.5M | -$216.3M | 30.4% |
| 2016 | 432 | 7.88M | 0.80% | $651.9M | $700.6M | -$39.3M | 31.0% |
| 2017 | 472 | 8.99M | 1.15% | $1.09B | $799.4M | $313.7M | 33.7% |
| 2018 | 548 | 10.10M | 1.55% | $1.71B | $984.0M | $739.4M | 37.4% |
| 2019 | 541 | 11.25M | 2.27% | $2.65B | $1.47B | $1.19B | 52.2% |
| 2020 | 513 | 10.61M | 3.74% | $4.14B | $2.28B | $1.86B | 67.3% |
| 2021 | 475 | 10.12M | 3.19% | $3.62B | $1.96B | $1.66B | 57.7% |
| 2022 | 482 | 10.42M | 3.61% | $4.33B | $2.52B | $1.81B | 62.9% |
| 2023 | 453 | 10.24M | 4.03% | $5.16B | $3.09B | $2.08B | 69.1% |
| 2024 | 476 | 10.33M | 4.73% | $6.61B | $4.14B | $2.49B | 75.6% |

What stands out:

- **Savings grew almost every year.** The program-wide savings rate rose from 0.55% in PY 2013 to
  4.73% in PY 2024. Across all twelve years ACOs spent $30.92B less than their benchmarks; CMS paid
  $19.26B of that back as shared savings, and ACOs owed $100.7M in shared losses, leaving $11.76B in
  net savings to Medicare by this measure.
- **The ENHANCED track carries the program.** In PY 2024 the 205 ENHANCED ACOs saved 5.65% of their
  benchmark and received $3.11B, 75.1% of all shared savings payments, against 3.16% for the 157
  one-sided BASIC A and B ACOs. Two-sided ACOs went from 2.3% of ACOs in PY 2013 to 67.0% in PY 2024.
- **Quality and savings are only weakly related.** The correlation between an ACO's quality score and
  its savings rate ranged from -0.14 to 0.19 across the twelve years (0.16 in PY 2024).
- **Spending per beneficiary** (person-year weighted) was $13,167 in PY 2024; after dividing each
  enrollment type's spending by its CMS-HCC risk score it was $13,189.

Quality checks from the same run (`results/pipeline_monitoring.md`, `results/semantic_layer_tests.md`):

| check | result |
|---|---|
| dbt build (57 models and seeds, 212 data tests, 2 unit tests) | 271 of 271 nodes passed |
| Semantic layer business questions (MetricFlow vs plain SQL on raw files) | 12 of 12 questions, 42 of 42 values matched |
| Source files matching their sha256 pins | 29 of 29 (23 data files, 6 dictionaries, 66.5 MB) |
| Performance periods loaded | 13 of 13 (5,476 ACO performance periods, 1,190,527 raw rows) |
| ACO identifier bridge, PY 2017 to PY 2018 | 405 of 472 PY 2017 ACOs linked (95.3% of PY 2018 ACOs that started before 2018) |
| County cells reported (not suppressed), share of program person years | 97.5% to 97.9% by year |
| New or revised CMS files waiting in the catalog | none |

## Data sources

Centers for Medicare & Medicaid Services (CMS), Medicare Shared Savings Program public use files on
data.cms.gov:

- [Performance Year Financial and Quality Results](https://data.cms.gov/medicare-shared-savings-program/performance-year-financial-and-quality-results):
  one file per performance period, PY 2013 to PY 2024 (the PY 2024 file is the CMS revision of
  July 17, 2026), with data dictionaries for 2013 to 2020, 2021, 2022, 2023 and 2024.
- [Number of Accountable Care Organization Assigned Beneficiaries by County](https://data.cms.gov/medicare-shared-savings-program/number-of-accountable-care-organization-assigned-beneficiaries-by-county):
  PY 2016 to PY 2024.

Exact URLs, sizes and checksums are in `config/sources.yml` and `results/download_manifest.json`.
These are aggregate, ACO-level public use files; CMS suppresses cells with 1 to 10 beneficiaries and
no file contains beneficiary-level records. Raw files are downloaded on each machine into `data/raw`
(ignored by git) and are not redistributed here. Use of the data is subject to the terms on
data.cms.gov. This project is independent and is not affiliated with or endorsed by CMS.

## How to run

Tested on macOS with an Apple M3. Requires [uv](https://docs.astral.sh/uv/) and make. Python packages come from PyPI
and are pinned in `requirements.txt` (direct) and `requirements-lock.txt` (full set).

```bash
make setup   # uv venv --python 3.12 .venv, then install the pinned packages
make all     # download, discover, ingest, staging, dbt build, semantic tests, dashboard, docs, monitor, pytest
```

`make all` took between 1 minute 46 seconds and 5 minutes 49 seconds across three runs on an Apple M3
laptop that was running other jobs, once the files were downloaded. DuckDB runs
with a 1 GB memory limit and 2 threads. Individual steps:

```bash
make download    # fetch pinned files, verify sha256 pins and CMS md5 checksums
make discover    # re-read data.cms.gov/data.json and flag new or revised files
make ingest      # load raw CSVs into DuckDB (schema checks fail closed)
make staging     # regenerate staging models from config/schema_mapping.yml
make dbt         # dbt build: models, seeds, data tests, unit tests
make semantic    # MetricFlow answers vs plain SQL
make dashboard   # results/dashboard.html and results/metrics.json
make docs        # docs/schema_mapping.md and docs/data_dictionary.md
make monitor     # results/pipeline_monitoring.md
make test        # pytest
```

Ask the semantic layer directly (from `warehouse/`, with `DBT_PROFILES_DIR=.` and `ACO_WAREHOUSE`
pointing at the DuckDB file):

```bash
../.venv/bin/mf query --metrics savings_rate,earned_shared_savings --group-by track__track_family \
  --where "{{ Dimension('aco_period__performance_year') }} = 2024"
```

## Repository layout

| path | contents |
|---|---|
| `config/` | `sources.yml` (pinned URLs and dictionaries), `pins.json` (sha256), `schema_mapping.yml` (the mapping) |
| `aco_scorecard/` | download, ingest, staging generator, semantic tests, dashboard, docs and monitoring code |
| `warehouse/` | dbt project: generated staging models, intermediate models, core and reporting marts, seeds, semantic models, macros, tests |
| `results/` | manifest, ingest report, semantic test results, metric catalog, monitoring report, metrics.json, dashboard.html |
| `docs/` | metric definitions, data dictionary, schema mapping |
| `tests/` | pytest suite (download safety, mapping, warehouse, results, writing style) |

## Limitations

- **Quality scores are not comparable across scoring eras.** CMS changed the method in PY 2021 (APM
  Performance Pathway) and again in PY 2023 (health equity adjustment), and in PY 2019 and 2020 a COVID-19
  policy gave every ACO the higher of its own score and the national mean. The dashboard and semantic layer label each year's era.
- **The identifier bridge is a reconstruction.** CMS refers to an ACO ID crosswalk that is not in the
  data.cms.gov catalog, so ACOs are linked across the 2017 to 2018 identifier change by exact
  normalized name and initial start date, one to one only. ACOs that changed their name in that year,
  or left before 2017, keep a separate legacy key (219 ACOs).
- **Net savings to Medicare is a simple measure** (savings less payments plus losses owed). CMS's own
  published figures can differ because of adjustments not in these files.
- **Risk-adjusted spending is a normalization, not CMS's benchmark method.** It divides by the mean
  CMS-HCC risk score per enrollment type and skips suppressed cells.
- **County totals are lower bounds** because of suppression (reported cells cover about 97.7% of
  person years).
- **PY 2019** has two six-month periods for some ACOs; dollars are prorated by CMS and the marts
  combine them, while per-period metrics such as assigned beneficiaries count those ACOs in each period.
- **PY 2013** has no published savings rate, generated savings or per capita total; the pipeline derives
  them from published totals and enrollment type values. PY 2020 and 2021 spending excludes COVID-19
  episode months, as CMS calculated it.
- Measure level quality results start in PY 2016; PY 2013 to 2015 files publish only the overall score.

## License

MIT (see `LICENSE`). CMS data remains subject to the data.cms.gov terms.
