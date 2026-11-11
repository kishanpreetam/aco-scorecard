-- Earned shared savings can never exceed generated savings times the final sharing rate.
-- CMS rounds the published PY 2019 sharing rate to the nearest percent, so half a point of
-- rounding is allowed. PY 2013 publishes no generated savings; benchmark minus expenditures
-- is used instead.
select
    aco_period_key,
    earned_shared_savings,
    coalesce(generated_savings_losses, benchmark_minus_expenditures) as generated,
    final_sharing_rate
from {{ ref('fct_aco_financial_year') }}
where earned_shared_savings > greatest(coalesce(generated_savings_losses, benchmark_minus_expenditures), 0) * (final_sharing_rate + 0.005) + 1
