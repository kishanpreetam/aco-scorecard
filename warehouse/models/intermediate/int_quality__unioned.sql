-- Quality measure results for every period that publishes them (PY 2016 onward), with the
-- conformed ACO key attached.

with unioned as (
    {% set quality_periods = ['2016', '2017', '2018', '2019', '2019A', '2020', '2021', '2022', '2023', '2024'] %}
    {% for pid in quality_periods %}
    select * from {{ ref('stg_puf_quality__py' ~ (pid | lower)) }}
    {% if not loop.last %}union all{% endif %}
    {% endfor %}
),

keys as (
    select distinct aco_key, aco_source_id, performance_period_id
    from {{ ref('int_aco_period__keyed') }}
)

select
    k.aco_key,
    u.*
from unioned as u
inner join keys as k
    on u.aco_source_id = k.aco_source_id
    and u.performance_period_id = k.performance_period_id
