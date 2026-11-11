-- Same guard for rates stored as fractions: a period left in percent units would show a
-- median minimum savings rate near 2 instead of 0.02, or a sharing rate above 1.
select
    performance_period_id,
    median(min_savings_rate) as median_msr,
    max(final_sharing_rate) as max_final_sharing_rate,
    max(abs(savings_rate_reported)) as max_abs_published_savings_rate
from {{ ref('fct_aco_financial_year') }}
group by 1
having median(min_savings_rate) > 0.1
    or max(final_sharing_rate) > 1
    or max(abs(savings_rate_reported)) > 1
