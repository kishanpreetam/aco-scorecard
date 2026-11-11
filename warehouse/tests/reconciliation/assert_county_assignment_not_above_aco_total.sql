-- Reported (unsuppressed) county person years for an ACO can never exceed the ACO's total
-- person years in the PUF for the same period. County values carry two decimals, so allow 1.
with county as (
    select aco_period_key, sum(total_person_years) as reported_person_years
    from {{ ref('fct_aco_county_assignment') }}
    group by 1
)
select
    f.aco_period_key,
    f.person_years,
    c.reported_person_years
from {{ ref('fct_aco_financial_year') }} as f
inner join county as c using (aco_period_key)
where c.reported_person_years > f.person_years + 1
