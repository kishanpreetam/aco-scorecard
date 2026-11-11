-- Grain: one row per quality measure, collection type and performance year (both PY 2019
-- periods pooled). Reporting coverage and the distribution of reported performance rates.

with results as (
    select
        f.*,
        m.measure_name,
        m.domain,
        m.higher_is_better,
        m.unit
    from {{ ref('fct_aco_quality_measure') }} as f
    inner join {{ ref('dim_measure') }} as m using (measure_key)
),

by_year as (
    select
        measure_key,
        collection_type,
        performance_year,
        any_value(measure_name) as measure_name,
        any_value(domain) as domain,
        any_value(higher_is_better) as higher_is_better,
        any_value(unit) as unit,
        count(*) as aco_results,
        count(*) filter (where is_reported) as reported_results,
        count(*) filter (where value_status = 'suppressed_small_cell') as suppressed_results,
        count(*) filter (where value_status = 'not_applicable') as not_applicable_results,
        count(*) filter (where value_status in ('cahps_waived_auto_credit', 'pay_for_reporting_suppressed')) as waived_results,
        avg(measure_value) as mean_value,
        quantile_cont(measure_value, 0.10) as p10_value,
        median(measure_value) as median_value,
        quantile_cont(measure_value, 0.90) as p90_value
    from results
    group by 1, 2, 3
)

select
    measure_key || '|' || collection_type || '|' || performance_year as measure_year_key,
    *,
    {{ safe_divide('reported_results', 'aco_results') }} as reporting_rate,
    median_value - lag(median_value) over (partition by measure_key, collection_type order by performance_year) as median_change_yoy,
    case
        when lag(median_value) over (partition by measure_key, collection_type order by performance_year) is null then null
        when higher_is_better then median_value > lag(median_value) over (partition by measure_key, collection_type order by performance_year)
        else median_value < lag(median_value) over (partition by measure_key, collection_type order by performance_year)
    end as median_improved_yoy
from by_year
