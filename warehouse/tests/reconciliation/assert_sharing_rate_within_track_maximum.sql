-- The final sharing rate can never exceed the maximum sharing rate of the ACO's track
-- (40, 50, 60 or 75 percent per the CMS data dictionary).
select
    f.aco_period_key,
    f.track_code,
    f.final_sharing_rate,
    t.max_sharing_rate
from {{ ref('fct_aco_financial_year') }} as f
inner join {{ ref('dim_track') }} as t using (track_code)
where f.final_sharing_rate > t.max_sharing_rate + 0.005
