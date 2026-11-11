-- Grain: one row per performance year and track family. Shows how results differ by risk
-- arrangement and how ACOs moved between tracks over time.

with periods as (
    select * from {{ ref('fct_aco_financial_year') }}
),

by_track as (
    select
        performance_year,
        track_family,
        min(risk_model) as risk_model,
        count(distinct aco_key) as aco_count,
        count(*) as aco_reconciliations,
        sum(n_assigned_beneficiaries) as assigned_beneficiaries,
        sum(total_benchmark_expenditures) as total_benchmark_expenditures,
        sum(benchmark_minus_expenditures) as benchmark_minus_expenditures,
        sum(earned_shared_savings) as earned_shared_savings,
        sum(shared_losses_owed) as shared_losses_owed,
        count(*) filter (where earned_savings_flag) as reconciliations_earning_savings,
        avg(quality_score) as quality_score_mean
    from periods
    group by 1, 2
)

select
    performance_year || '|' || track_family as track_year_key,
    *,
    {{ safe_divide('benchmark_minus_expenditures', 'total_benchmark_expenditures') }} as savings_rate,
    {{ safe_divide('earned_shared_savings', 'assigned_beneficiaries') }} as earned_savings_per_beneficiary,
    {{ safe_divide('reconciliations_earning_savings', 'aco_reconciliations') }} as share_earning_savings,
    {{ safe_divide('aco_count', 'sum(aco_count) over (partition by performance_year)') }} as share_of_year_acos,
    {{ safe_divide('earned_shared_savings', 'sum(earned_shared_savings) over (partition by performance_year)') }} as share_of_year_earned_savings,
    rank() over (partition by performance_year order by {{ safe_divide('benchmark_minus_expenditures', 'total_benchmark_expenditures') }} desc) as savings_rate_rank_in_year
from by_track
