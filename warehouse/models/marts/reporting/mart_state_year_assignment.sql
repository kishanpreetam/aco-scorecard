-- Grain: one row per state and performance year (both PY 2019 periods pooled).
-- Reported (unsuppressed) assigned beneficiary person years by state of residence. Because
-- CMS suppresses small counties these are lower bounds; coverage_of_program shows how much of
-- the program total the reported counties account for.

with counties as (
    select * from {{ ref('fct_aco_county_assignment') }}
),

program as (
    select performance_year, sum(person_years) as program_person_years
    from {{ ref('fct_aco_financial_year') }}
    group by 1
),

by_state as (
    select
        performance_year,
        state_name,
        count(distinct aco_key) as acos_with_beneficiaries,
        count(distinct ssa_county_key) as counties_with_beneficiaries,
        sum(total_person_years) as reported_person_years,
        sum(person_years_esrd) as reported_person_years_esrd,
        sum(person_years_disabled) as reported_person_years_disabled,
        sum(person_years_aged_dual) as reported_person_years_aged_dual,
        sum(person_years_aged_nondual) as reported_person_years_aged_nondual,
        count(*) filter (where is_suppressed) as suppressed_aco_county_rows,
        count(*) as aco_county_rows
    from counties
    group by 1, 2
)

select
    s.performance_year || '|' || s.state_name as state_year_key,
    s.*,
    {{ safe_divide('s.reported_person_years', 'sum(s.reported_person_years) over (partition by s.performance_year)') }} as share_of_reported_person_years,
    {{ safe_divide('sum(s.reported_person_years) over (partition by s.performance_year)', 'p.program_person_years') }} as coverage_of_program,
    rank() over (partition by s.performance_year order by s.reported_person_years desc nulls last) as state_rank_in_year
from by_state as s
left join program as p using (performance_year)
