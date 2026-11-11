-- Benchmark minus expenditures (published) must equal total benchmark minus total expenditures
-- (also published) within a dollar of rounding, in every period.
select
    aco_period_key,
    benchmark_minus_expenditures,
    total_benchmark_expenditures - total_expenditures as recomputed
from {{ ref('fct_aco_financial_year') }}
where abs(benchmark_minus_expenditures - (total_benchmark_expenditures - total_expenditures)) > 2
