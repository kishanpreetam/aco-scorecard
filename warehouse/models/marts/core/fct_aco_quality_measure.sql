-- Grain: one row per ACO, performance period, quality measure and collection type.
-- Includes non-reported rows with their CMS status code so coverage can be measured.

select
    q.aco_key || '|' || q.performance_period_id || '|' || q.measure_key || '|' || q.collection_type as aco_measure_key,
    q.aco_key || '|' || q.performance_period_id as aco_period_key,
    q.aco_key,
    q.performance_period_id,
    q.performance_year,
    make_date(q.performance_year, 1, 1) as performance_year_start,
    q.measure_key,
    q.collection_type,
    q.source_column,
    q.raw_value,
    q.measure_value,
    q.value_status,
    q.value_status = 'reported' as is_reported
from {{ ref('int_quality__unioned') }} as q
