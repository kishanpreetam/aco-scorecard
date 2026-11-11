-- Adds the conformed ACO key used by every fact table.
--   PY 2018 onward: the published ACO_ID.
--   PY 2013 to 2017: the bridged ACO_ID when int_aco_id_bridge found one, otherwise LEGACY-<ACO_Num>.

with periods as (
    select * from {{ ref('int_puf__unioned') }}
),

bridge as (
    select * from {{ ref('int_aco_id_bridge') }}
)

select
    case
        when p.aco_id_system = 'aco_id' then p.aco_source_id
        when b.aco_id is not null then b.aco_id
        else 'LEGACY-' || p.aco_source_id
    end as aco_key,
    case
        when p.aco_id_system = 'aco_id' then 'published_aco_id'
        when b.aco_id is not null then 'bridged_legacy_id'
        else 'legacy_id_only'
    end as aco_key_method,
    p.*
from periods as p
left join bridge as b
    on p.aco_id_system = 'encrypted_aco_num'
    and p.aco_source_id = b.legacy_aco_num
