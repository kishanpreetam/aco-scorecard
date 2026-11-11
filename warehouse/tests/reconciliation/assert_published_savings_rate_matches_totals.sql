-- The published savings rate (rounded by CMS to 4 decimal places of a fraction) must match the
-- rate recomputed from published totals. PY 2013 does not publish a savings rate.
select
    aco_period_key,
    savings_rate_reported,
    savings_rate
from {{ ref('fct_aco_financial_year') }}
where savings_rate_reported is not null
  and abs(savings_rate_reported - savings_rate) > 0.0001
