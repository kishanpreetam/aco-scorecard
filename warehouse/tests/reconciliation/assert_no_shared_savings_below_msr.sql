-- An ACO whose savings rate is below its minimum savings rate earns no shared savings, except
-- under the PY 2024 reduced shared savings policy for low revenue ACOs (ReducedSS = 1).
select
    aco_period_key,
    savings_rate,
    min_savings_rate,
    earned_shared_savings,
    reduced_shared_savings_flag
from {{ ref('fct_aco_financial_year') }}
where savings_rate < min_savings_rate - 0.0001
  and earned_shared_savings > 0
  and not coalesce(reduced_shared_savings_flag, false)
