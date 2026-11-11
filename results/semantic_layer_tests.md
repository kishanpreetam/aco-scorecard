# Semantic layer tests

Run started 2026-11-04T04:12:03+00:00. Each business question is answered by MetricFlow from the governed metric
definitions and, separately, by plain SQL over the raw text tables. Values must agree within a relative tolerance of 1e-9.

Result: 12 of 12 questions passed; 42 of 42 values matched.

## Q01: What was the program-wide savings rate (total savings over total benchmark) in each performance year from 2013 to 2024?

`mf query --metrics savings_rate --group-by metric_time__year`

| group | metric | MetricFlow | plain SQL | match |
|---|---|---|---|---|
| year=2013 | savings_rate | 0.005496 | 0.005496 | yes |
| year=2014 | savings_rate | 0.005512 | 0.005512 | yes |
| year=2015 | savings_rate | 0.005856 | 0.005856 | yes |
| year=2016 | savings_rate | 0.008011 | 0.008011 | yes |
| year=2017 | savings_rate | 0.011532 | 0.011532 | yes |
| year=2018 | savings_rate | 0.015538 | 0.015538 | yes |
| year=2019 | savings_rate | 0.022690 | 0.022690 | yes |
| year=2020 | savings_rate | 0.037354 | 0.037354 | yes |
| year=2021 | savings_rate | 0.031936 | 0.031936 | yes |
| year=2022 | savings_rate | 0.036062 | 0.036062 | yes |
| year=2023 | savings_rate | 0.040334 | 0.040334 | yes |
| year=2024 | savings_rate | 0.047331 | 0.047331 | yes |

## Q02: In PY 2024, how much did CMS pay ACOs in shared savings, how much did ACOs owe in losses, and what were net savings to Medicare?

`mf query --metrics earned_shared_savings,shared_losses_owed,net_savings_to_medicare --where "{{ Dimension('aco_period__performance_year') }} = 2024"`

| group | metric | MetricFlow | plain SQL | match |
|---|---|---|---|---|
| all | earned_shared_savings | 4,142,450,738 | 4,142,450,738 | yes |
| all | shared_losses_owed | 19,966,437 | 19,966,437 | yes |
| all | net_savings_to_medicare | 2,491,835,204 | 2,491,835,204 | yes |

## Q03: Which track family had the highest savings rate in PY 2024?

`mf query --metrics savings_rate --group-by track__track_family --where "{{ Dimension('aco_period__performance_year') }} = 2024"`

| group | metric | MetricFlow | plain SQL | match |
|---|---|---|---|---|
| track_family=ENHANCED | savings_rate | 0.056450 | 0.056450 | yes |
| track_family=BASIC C to E (two-sided) | savings_rate | 0.043483 | 0.043483 | yes |
| track_family=BASIC A and B (one-sided) | savings_rate | 0.031621 | 0.031621 | yes |

## Q04: How many distinct ACOs were reconciled in PY 2019, counting both the January and July 2019 periods?

`mf query --metrics aco_count --where "{{ Dimension('aco_period__performance_year') }} = 2019"`

| group | metric | MetricFlow | plain SQL | match |
|---|---|---|---|---|
| all | aco_count | 541 | 541 | yes |

## Q05: What share of ACO reconciliations earned a shared savings payment in each year from 2021 to 2024?

`mf query --metrics share_earning_savings --group-by metric_time__year --where "{{ Dimension('aco_period__performance_year') }} >= 2021"`

| group | metric | MetricFlow | plain SQL | match |
|---|---|---|---|---|
| year=2021 | share_earning_savings | 0.576842 | 0.576842 | yes |
| year=2022 | share_earning_savings | 0.628631 | 0.628631 | yes |
| year=2023 | share_earning_savings | 0.690949 | 0.690949 | yes |
| year=2024 | share_earning_savings | 0.756303 | 0.756303 | yes |

## Q06: In PY 2023, how did earned shared savings per assigned beneficiary compare between one-sided and two-sided ACOs?

`mf query --metrics earned_shared_savings_per_assigned_beneficiary --group-by aco_period__risk_model --where "{{ Dimension('aco_period__performance_year') }} = 2023"`

| group | metric | MetricFlow | plain SQL | match |
|---|---|---|---|---|
| risk_model=Two-Sided | earned_shared_savings_per_assigned_beneficiary | 372.62 | 372.62 | yes |
| risk_model=One-Sided | earned_shared_savings_per_assigned_beneficiary | 118.22 | 118.22 | yes |

## Q07: What was the mean ACO quality score in each year of the APM Performance Pathway era (2021 to 2024)?

`mf query --metrics mean_quality_score --group-by metric_time__year --where "{{ Dimension('aco_period__performance_year') }} >= 2021"`

| group | metric | MetricFlow | plain SQL | match |
|---|---|---|---|---|
| year=2021 | mean_quality_score | 90.667747 | 90.667747 | yes |
| year=2022 | mean_quality_score | 81.531058 | 81.531058 | yes |
| year=2023 | mean_quality_score | 82.279051 | 82.279051 | yes |
| year=2024 | mean_quality_score | 81.899307 | 81.899307 | yes |

## Q08: What was risk-adjusted per capita expenditure (spending divided by CMS-HCC risk score, by enrollment type) in PY 2023 and PY 2024?

`mf query --metrics risk_adjusted_per_capita_expenditure --group-by metric_time__year --where "{{ Dimension('aco_period__performance_year') }} in (2023, 2024)"`

| group | metric | MetricFlow | plain SQL | match |
|---|---|---|---|---|
| year=2023 | risk_adjusted_per_capita_expenditure | 12,213.04 | 12,213.04 | yes |
| year=2024 | risk_adjusted_per_capita_expenditure | 13,189.35 | 13,189.35 | yes |

## Q09: How many Medicare beneficiaries were assigned to Shared Savings Program ACOs in PY 2024?

`mf query --metrics assigned_beneficiaries --where "{{ Dimension('aco_period__performance_year') }} = 2024"`

| group | metric | MetricFlow | plain SQL | match |
|---|---|---|---|---|
| all | assigned_beneficiaries | 10,326,340 | 10,326,340 | yes |

## Q10: What was the person-year weighted mean CMS-HCC risk score for each Medicare enrollment type in PY 2024?

`mf query --metrics mean_risk_score --group-by attribution_row__enrollment_type_code --where "{{ TimeDimension('metric_time', 'year') }} = '2024-01-01'"`

| group | metric | MetricFlow | plain SQL | match |
|---|---|---|---|---|
| enrollment_type_code=esrd | mean_risk_score | 0.982942 | 0.982942 | yes |
| enrollment_type_code=disabled | mean_risk_score | 0.967862 | 0.967862 | yes |
| enrollment_type_code=aged_dual | mean_risk_score | 0.958277 | 0.958277 | yes |
| enrollment_type_code=aged_nondual | mean_risk_score | 1.002932 | 1.002932 | yes |

## Q11: For Controlling High Blood Pressure (Quality ID 236) in PY 2024, what share of ACOs reported a result through each collection type?

`mf query --metrics quality_reporting_rate --group-by measure_result__collection_type --where "{{ Entity('quality_measure') }} = 'Q236' and {{ TimeDimension('metric_time', 'year') }} = '2024-01-01'"`

| group | metric | MetricFlow | plain SQL | match |
|---|---|---|---|---|
| collection_type=Web Interface | quality_reporting_rate | 0.821429 | 0.821429 | yes |
| collection_type=eCQM | quality_reporting_rate | 0.079832 | 0.079832 | yes |
| collection_type=MIPS CQM | quality_reporting_rate | 0.031513 | 0.031513 | yes |
| collection_type=Medicare CQM | quality_reporting_rate | 0.050420 | 0.050420 | yes |

## Q12: How many ACOs saved 5 percent or more of their benchmark in PY 2024, and what was their combined savings rate?

`mf query --metrics aco_count,savings_rate --where "{{ Dimension('aco_period__performance_year') }} = 2024 and {{ Dimension('aco_period__savings_rate_band') }} = '5 percent or more'"`

| group | metric | MetricFlow | plain SQL | match |
|---|---|---|---|---|
| all | aco_count | 204 | 204 | yes |
| all | savings_rate | 0.081893 | 0.081893 | yes |

