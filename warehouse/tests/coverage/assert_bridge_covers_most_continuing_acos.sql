-- At least 80 percent of PY 2018 ACOs that started before 2018 (so they should appear in the
-- PY 2017 file) must be linked to their legacy identifier by the bridge.
with continuing as (
    select aco_source_id
    from {{ ref('stg_puf__py2018') }}
    where initial_start_date < date '2018-01-01'
),
linked as (
    select aco_id from {{ ref('int_aco_id_bridge') }}
)
select
    count(*) as continuing_acos,
    count(*) filter (where aco_source_id in (select aco_id from linked)) as linked_acos
from continuing
having count(*) filter (where aco_source_id in (select aco_id from linked)) < 0.8 * count(*)
