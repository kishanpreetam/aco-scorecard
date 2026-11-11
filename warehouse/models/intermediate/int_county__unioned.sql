-- ACO by county assignment rows for every published period, with the conformed ACO key.
-- County codes are SSA state (2 digit) and county (3 digit) codes, zero padded here because
-- the files drop leading zeros.

with unioned as (
    {% for pid in var('expected_county_periods') %}
    select * from {{ ref('stg_county__py' ~ (pid | lower)) }}
    {% if not loop.last %}union all{% endif %}
    {% endfor %}
),

keys as (
    select distinct aco_key, aco_source_id, performance_period_id
    from {{ ref('int_aco_period__keyed') }}
)

select
    k.aco_key,
    u.performance_period_id,
    u.performance_year,
    u.aco_source_id,
    upper(u.state_name) as state_name,
    upper(u.county_name) as county_name,
    lpad(cast(cast(u.ssa_state_code as integer) as varchar), 2, '0') as ssa_state_code,
    lpad(cast(cast(u.ssa_county_code as integer) as varchar), 3, '0') as ssa_county_code,
    lpad(cast(cast(u.ssa_state_code as integer) as varchar), 2, '0')
        || lpad(cast(cast(u.ssa_county_code as integer) as varchar), 3, '0') as ssa_county_key,
    u.person_years_esrd,
    u.person_years_disabled,
    u.person_years_aged_dual,
    u.person_years_aged_nondual,
    u.total_person_years,
    u.total_assigned_beneficiaries,
    u.total_assigned_beneficiaries_status,
    u.total_person_years_status,
    u.total_assigned_beneficiaries_status <> 'reported' as is_suppressed,
    u._source_file_key
from unioned as u
left join keys as k
    on u.aco_source_id = k.aco_source_id
    and u.performance_period_id = k.performance_period_id
