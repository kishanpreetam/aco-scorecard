-- Grain: one row per ACO, performance period and county of beneficiary residence.
-- CMS suppresses counties with 1 to 10 assigned beneficiaries (and some neighbors), so sums of
-- reported person years are a lower bound on the ACO total.

select
    aco_key || '|' || performance_period_id || '|' || ssa_county_key as aco_county_key,
    aco_key || '|' || performance_period_id as aco_period_key,
    aco_key,
    performance_period_id,
    performance_year,
    make_date(performance_year, 1, 1) as performance_year_start,
    ssa_county_key,
    ssa_state_code,
    ssa_county_code,
    state_name,
    county_name,
    person_years_esrd,
    person_years_disabled,
    person_years_aged_dual,
    person_years_aged_nondual,
    total_person_years,
    total_assigned_beneficiaries,
    total_assigned_beneficiaries_status,
    is_suppressed
from {{ ref('int_county__unioned') }}
