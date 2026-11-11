-- Person years by enrollment type must add up to total person years whenever all four types are
-- published (CMS suppresses small cells, and then suppresses a second cell so the first cannot
-- be derived, so rows with a suppressed type are skipped).
select
    aco_key,
    performance_period_id,
    person_years,
    person_years_by_type_total
from {{ ref('int_aco_period__keyed') }}
where person_years_esrd is not null
  and person_years_disabled is not null
  and person_years_aged_dual is not null
  and person_years_aged_nondual is not null
  and abs(person_years_by_type_total - person_years) > greatest(2, 0.001 * person_years)
