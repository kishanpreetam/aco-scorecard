-- One row per CMS performance period. PY 2019 has two periods (2019 and 2019A).

with periods as (
    select * from {{ ref('performance_periods') }}
),

loaded as (
    select
        performance_period_id,
        count(*) as aco_count,
        min(_source_file_key) as source_file_key,
        min(_source_sha256) as source_sha256,
        min(_loaded_at) as loaded_at
    from {{ ref('int_aco_period__keyed') }}
    group by 1
)

select
    p.performance_period_id,
    p.performance_year,
    make_date(p.performance_year, 1, 1) as performance_year_start,
    p.period_label,
    p.nominal_start,
    p.nominal_end,
    p.id_system,
    p.quality_measure_set,
    p.quality_score_definition,
    p.comparability_group,
    p.notes,
    l.aco_count,
    l.source_file_key,
    l.source_sha256,
    l.loaded_at
from periods as p
left join loaded as l using (performance_period_id)
