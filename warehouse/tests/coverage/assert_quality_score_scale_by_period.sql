-- Guards the per-year unit conversions in the schema mapping: in every period the quality
-- score must sit on the 0 to 100 scale (median above 50, maximum at most 100). A period whose
-- fraction-to-points scale was missed would show a median near 1.
select
    performance_period_id,
    median(quality_score) as median_quality_score,
    max(quality_score) as max_quality_score
from {{ ref('fct_aco_financial_year') }}
group by 1
having median(quality_score) < 50 or max(quality_score) > 100
