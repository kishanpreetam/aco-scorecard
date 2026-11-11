-- CMS defines total benchmark and total expenditures as per capita values times person years.
-- Allowing for dollar rounding of the per capita values and proration of partial-year periods,
-- the products must match the totals within 0.2 percent. PY 2013 publishes no per capita
-- benchmark, so it is excluded.
select
    aco_period_key,
    total_benchmark_expenditures,
    updated_benchmark_per_capita * person_years * period_months / 12.0 as benchmark_from_per_capita,
    total_expenditures,
    per_capita_expenditure * person_years * period_months / 12.0 as expenditures_from_per_capita
from {{ ref('fct_aco_financial_year') }}
where performance_year >= 2014
  and (
      abs(total_benchmark_expenditures - updated_benchmark_per_capita * person_years * period_months / 12.0) > 0.002 * total_benchmark_expenditures
      or abs(total_expenditures - per_capita_expenditure * person_years * period_months / 12.0) > 0.002 * total_expenditures
  )
