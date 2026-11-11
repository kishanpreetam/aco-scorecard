-- Conformed quality measures with the years and collection types in which each was published.

with catalog as (
    select * from {{ ref('measure_catalog') }}
),

observed as (
    select
        measure_key,
        min(performance_year) as first_performance_year,
        max(performance_year) as last_performance_year,
        string_agg(distinct collection_type, ', ' order by collection_type) as collection_types,
        count(*) filter (where value_status = 'reported') as reported_result_count
    from {{ ref('int_quality__unioned') }}
    group by 1
)

select
    c.measure_key,
    c.legacy_code,
    c.app_code,
    c.measure_name,
    c.domain,
    c.higher_is_better,
    c.unit,
    c.predecessor_measure_key,
    c.notes,
    o.first_performance_year,
    o.last_performance_year,
    o.collection_types,
    coalesce(o.reported_result_count, 0) as reported_result_count
from catalog as c
left join observed as o using (measure_key)
