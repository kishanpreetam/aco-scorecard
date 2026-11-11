-- One row per ACO (conformed key), with attributes taken from its most recent period.

with periods as (
    select * from {{ ref('int_aco_period__keyed') }}
),

latest as (
    select *
    from periods
    qualify row_number() over (partition by aco_key order by period_end_date desc, performance_period_id desc) = 1
),

history as (
    select
        aco_key,
        min(performance_year) as first_performance_year,
        max(performance_year) as last_performance_year,
        count(distinct performance_year) as performance_years_reconciled,
        count(*) as performance_periods_reconciled,
        min(initial_start_date) as initial_start_date,
        max(case when aco_id_system = 'encrypted_aco_num' then aco_source_id end) as legacy_aco_num,
        max(case when aco_id_system = 'aco_id' then aco_source_id end) as published_aco_id,
        max(case when aco_key_method = 'bridged_legacy_id' then 1 else 0 end) = 1 as has_bridged_history
    from periods
    group by 1
),

county_latest as (
    select
        aco_key,
        state_name,
        sum(total_person_years) as reported_person_years,
        row_number() over (partition by aco_key, performance_year order by sum(total_person_years) desc nulls last, state_name) as state_rank
    from {{ ref('int_county__unioned') }}
    where aco_key is not null
    group by aco_key, state_name, performance_year
    qualify dense_rank() over (partition by aco_key order by performance_year desc) = 1
),

state_summary as (
    select
        aco_key,
        max(case when state_rank = 1 then state_name end) as primary_state,
        count(*) as states_with_assigned_beneficiaries
    from county_latest
    group by 1
)

select
    l.aco_key,
    l.aco_name as aco_name,
    h.published_aco_id,
    h.legacy_aco_num,
    case
        when h.published_aco_id is not null and h.legacy_aco_num is not null then 'bridged_legacy_id'
        when h.published_aco_id is not null then 'published_aco_id'
        else 'legacy_id_only'
    end as aco_key_method,
    h.first_performance_year,
    h.last_performance_year,
    h.performance_years_reconciled,
    h.performance_periods_reconciled,
    h.initial_start_date,
    l.performance_period_id as latest_performance_period_id,
    l.track_code as latest_track_code,
    l.agreement_type as latest_agreement_type,
    l.n_assigned_beneficiaries as latest_assigned_beneficiaries,
    s.primary_state,
    s.states_with_assigned_beneficiaries,
    h.last_performance_year = (select max(performance_year) from periods) as is_active_in_latest_year
from latest as l
inner join history as h using (aco_key)
left join state_summary as s using (aco_key)
