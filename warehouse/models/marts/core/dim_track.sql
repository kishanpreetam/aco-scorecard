-- Tracks (risk arrangements) with the maximum sharing rate CMS documents for each, plus the
-- years each track actually appears in the data.

with reference as (
    select * from {{ ref('track_reference') }}
),

observed as (
    select
        track_code,
        min(performance_year) as first_performance_year,
        max(performance_year) as last_performance_year,
        count(*) as aco_period_count
    from {{ ref('int_aco_period__keyed') }}
    group by 1
)

select
    r.track_code,
    r.track_name,
    r.track_family,
    r.program_era,
    r.risk_model,
    r.max_sharing_rate,
    r.display_order,
    o.first_performance_year,
    o.last_performance_year,
    coalesce(o.aco_period_count, 0) as aco_period_count
from reference as r
left join observed as o using (track_code)
