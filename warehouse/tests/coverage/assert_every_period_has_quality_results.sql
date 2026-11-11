-- Measure level quality results are published from PY 2016. Each of those periods must have
-- reported results for most ACOs (PY 2020 CAHPS results were waived, so the check uses any measure).
with expected as (
    select unnest(['2016', '2017', '2018', '2019', '2019A', '2020', '2021', '2022', '2023', '2024']) as performance_period_id
),
reported as (
    select performance_period_id, count(distinct aco_key) filter (where is_reported) as acos_with_results
    from {{ ref('fct_aco_quality_measure') }}
    group by 1
),
acos as (
    select performance_period_id, count(*) as aco_count from {{ ref('fct_aco_financial_year') }} group by 1
)
select e.performance_period_id, r.acos_with_results, a.aco_count
from expected as e
left join reported as r using (performance_period_id)
left join acos as a using (performance_period_id)
where coalesce(r.acos_with_results, 0) < 0.9 * a.aco_count
