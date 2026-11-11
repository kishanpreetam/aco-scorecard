# Metric definitions

Every metric below is defined once, in `warehouse/models/semantic/semantic_models.yml`, and served
through MetricFlow. The table gives the formula in plain terms; the semantic layer tests
(`results/semantic_layer_tests.md`) check twelve business questions against plain SQL written
directly on the raw files.

## How the Shared Savings Program works (the concepts behind the metrics)

- **ACO.** An accountable care organization: a group of doctors, hospitals and other providers that
  agrees to be accountable for the cost and quality of care for a population of Medicare
  fee-for-service beneficiaries.
- **Attribution (assignment).** CMS assigns each beneficiary to the ACO whose clinicians provided most
  of their primary care. `N_AB` counts assigned beneficiaries; `person_years` counts the months they
  were eligible divided by 12. Assignment is prospective or retrospective
  (`assignment_type`, published from PY 2021).
- **Enrollment types.** CMS sets benchmarks and risk scores separately for four groups: ESRD,
  disabled, aged dual eligible (also on Medicaid) and aged non-dual.
- **Benchmark.** The spending target. CMS sets a historical benchmark from the ACO's spending in the
  three benchmark years before the agreement period (BY1 to BY3), then updates it each performance year
  for risk, trend and (for most agreements) regional spending (`UpdatedBnchmk`). Total benchmark =
  updated per capita benchmark x person years.
- **Savings or losses.** Total benchmark minus total expenditures (`BnchmkMinExp`). Positive is
  savings; negative is spending above the benchmark.
- **Minimum savings rate (MSR) and minimum loss rate (MLR).** A threshold the savings rate must reach
  before any savings are shared (or losses owed), so random variation is not rewarded. One-sided ACOs
  get an MSR on a sliding scale by size; two-sided ACOs choose a symmetric MSR and MLR.
- **Shared savings.** When the savings rate meets the MSR and the ACO meets the quality performance
  standard, the ACO earns a share of savings from the first dollar: generated savings x final sharing
  rate, reduced for sequestration and capped by the performance payment limit (`EarnSaveLoss`).
- **Tracks and sharing rates.** The maximum sharing rate depends on the track: 40 percent for BASIC
  Levels A and B, 50 percent for Track 1, Track 1+ and BASIC Levels C to E, 60 percent for Track 2 and
  75 percent for Track 3 and ENHANCED (CMS data dictionary, QualPerfShare). One-sided tracks share
  savings only; two-sided tracks also owe a share of losses beyond the MLR.
- **Quality scoring.** Through PY 2020 the quality score was the percent of quality points earned on
  the ACO measure set (first year ACOs scored on complete reporting). From PY 2021 it is the MIPS
  quality performance category score under the APM Performance Pathway (APP); PY 2023 used a health
  equity adjusted score, and PY 2024 adds population and income adjustment bonus points. In PY 2019
  and 2020 the COVID-19 extreme and uncontrollable circumstances policy gave every ACO the higher of
  its own score and the national mean, so scores are compared only within the same year or scoring
  era (`comparability_group`).
- **Risk adjustment.** Each beneficiary has a prospective CMS-HCC risk score (expected cost relative
  to an average beneficiary). The PUF publishes the mean score by enrollment type for the performance
  year and for benchmark year 3. CMS uses these to adjust the benchmark for changes in case mix, with a
  cap on positive adjustments.

## Metrics

| metric (semantic layer name) | definition | notes |
|---|---|---|
| Total benchmark (`total_benchmark`) | Sum of `total_benchmark_expenditures` | Period totals: 6-month periods in PY 2019 are prorated by CMS; 2012 starters have 18 or 21 months in PY 2013. |
| Total expenditures (`total_expenditures`) | Sum of `total_expenditures` | Parts A and B spending for assigned beneficiaries. |
| Total savings (`total_savings`) | Sum of `benchmark_minus_expenditures` | ACOs above benchmark subtract. |
| Savings rate (`savings_rate`) | Total savings / total benchmark | A ratio of sums, so larger ACOs weigh more. For one ACO it equals the published `Sav_rate` (checked by a dbt test for every year it is published). |
| Earned shared savings (`earned_shared_savings`) | Sum of positive `EarnSaveLoss` | Payments CMS made to ACOs. |
| Shared losses owed (`shared_losses_owed`) | Sum of negative `EarnSaveLoss`, as a positive number | Owed by two-sided ACOs. |
| Net savings to Medicare (`net_savings_to_medicare`) | Total savings minus earned shared savings plus shared losses owed | A simple program view. CMS's published net savings figures can include other adjustments. |
| Assigned beneficiaries (`assigned_beneficiaries`) | Sum of `N_AB` | Counted per period, so an ACO in both PY 2019 periods counts twice in this metric; the program mart counts each ACO once per year. |
| Earned shared savings per assigned beneficiary (`earned_shared_savings_per_assigned_beneficiary`) | Earned shared savings / assigned beneficiaries | Ratio of sums. |
| Per capita expenditure (`per_capita_expenditure`) | Sum of (per capita spending x person years) / sum of person years | Person-year weighted. PY 2013 per capita is derived from the four enrollment type values because the total is not published. |
| Risk-adjusted per capita expenditure (`risk_adjusted_per_capita_expenditure`) | For each ACO: sum over enrollment types of (per capita spending / mean CMS-HCC risk score x person years), divided by the person years of the types included; then person-year weighted across ACOs | A simple risk normalization for comparison, not CMS's benchmark method. Enrollment types with a suppressed cell are left out of both numerator and denominator. |
| Mean quality score (`mean_quality_score`) | Average of `quality_score` (0 to 100) | Unweighted mean over ACOs; compare only within a scoring era. PY 2014 and 2015 first-year ACOs have no score (pay for reporting). |
| Number of ACOs (`aco_count`) | Count of distinct `aco_key` | Uses the conformed key, so ACOs in both PY 2019 periods count once. |
| Share earning shared savings (`share_earning_savings`) | Reconciliations with earned shared savings above zero / all reconciliations | A reconciliation is one ACO in one performance period. |
| Mean CMS-HCC risk score (`mean_risk_score`) | Sum of (risk score x person years) / person years with a score | From `fct_attribution`, usually grouped by enrollment type. |
| Quality reporting rate (`quality_reporting_rate`) | Reported results / expected results | From `fct_aco_quality_measure`; a result is expected for every ACO, measure and collection type in the period's file. |
| Mean measure performance rate (`mean_measure_rate`) | Average of reported `measure_value` | Check `higher_is_better` before reading a change as good or bad. |

## Reporting mart measures (dbt, not the semantic layer)

| column | where | definition |
|---|---|---|
| `savings_rate_change_yoy` | `mart_aco_year_scorecard` | The ACO's savings rate minus its savings rate in the immediately preceding year (NULL after a gap year). Uses `LAG`. |
| `savings_rate_avg_last3` | `mart_aco_year_scorecard` | Average savings rate over the ACO's last three reconciled years. |
| `savings_rate_rank`, `savings_rate_percentile`, `savings_rate_quartile` | `mart_aco_year_scorecard` | `RANK`, `PERCENT_RANK` and `NTILE(4)` within the performance year. |
| `cumulative_earned_shared_savings` | `mart_aco_year_scorecard`, `mart_program_year_summary` | Running total with `SUM() OVER (ORDER BY performance_year)`. |
| `savings_rate_p25`, `savings_rate_median`, `savings_rate_p75` | `mart_program_year_summary` | Distribution of ACO savings rates within the year. |
| `share_of_year_earned_savings` | `mart_track_year_summary` | Track family's share of the year's earned shared savings. |
| `coverage_of_program` | `mart_state_year_assignment` | Reported county person years / program person years; below 1 because CMS suppresses small cells. |
