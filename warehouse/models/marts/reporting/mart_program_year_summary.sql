-- Grain: one row per performance year. Program totals, the distribution of ACO results and
-- year over year change. Dollar totals add both PY 2019 periods.

with periods as (
    select * from {{ ref('fct_aco_financial_year') }}
),

aco_years as (
    select * from {{ ref('mart_aco_year_scorecard') }}
),

totals as (
    select
        performance_year,
        count(*) as aco_reconciliations,
        sum(total_benchmark_expenditures) as total_benchmark_expenditures,
        sum(total_expenditures) as total_expenditures,
        sum(benchmark_minus_expenditures) as benchmark_minus_expenditures,
        sum(earned_shared_savings) as earned_shared_savings,
        sum(shared_losses_owed) as shared_losses_owed,
        count(*) filter (where earned_savings_flag) as reconciliations_earning_savings,
        count(*) filter (where owed_losses_flag) as reconciliations_owing_losses,
        sum(annualized_expenditure) / nullif(sum(case when annualized_expenditure is not null then person_years end), 0) as per_capita_expenditure,
        sum(risk_adjusted_annualized_expenditure) / nullif(sum(case when risk_adjusted_annualized_expenditure is not null then person_years end), 0) as risk_adjusted_per_capita_expenditure
    from periods
    group by 1
),

distribution as (
    select
        performance_year,
        count(*) as aco_count,
        sum(n_assigned_beneficiaries) as assigned_beneficiaries,
        quantile_cont(savings_rate, 0.25) as savings_rate_p25,
        median(savings_rate) as savings_rate_median,
        quantile_cont(savings_rate, 0.75) as savings_rate_p75,
        avg(quality_score) as quality_score_mean,
        median(quality_score) as quality_score_median,
        count(*) filter (where risk_model = 'Two-Sided') as two_sided_aco_count
    from aco_years
    group by 1
),

combined as (
    select
        t.performance_year,
        d.aco_count,
        t.aco_reconciliations,
        d.assigned_beneficiaries,
        t.total_benchmark_expenditures,
        t.total_expenditures,
        t.benchmark_minus_expenditures,
        {{ safe_divide('t.benchmark_minus_expenditures', 't.total_benchmark_expenditures') }} as savings_rate,
        t.earned_shared_savings,
        t.shared_losses_owed,
        t.benchmark_minus_expenditures - t.earned_shared_savings + t.shared_losses_owed as net_savings_to_medicare,
        {{ safe_divide('t.earned_shared_savings', 'd.assigned_beneficiaries') }} as earned_savings_per_beneficiary,
        t.reconciliations_earning_savings,
        {{ safe_divide('t.reconciliations_earning_savings', 't.aco_reconciliations') }} as share_earning_savings,
        t.reconciliations_owing_losses,
        d.two_sided_aco_count,
        {{ safe_divide('d.two_sided_aco_count', 'd.aco_count') }} as two_sided_share,
        t.per_capita_expenditure,
        t.risk_adjusted_per_capita_expenditure,
        d.savings_rate_p25,
        d.savings_rate_median,
        d.savings_rate_p75,
        d.quality_score_mean,
        d.quality_score_median
    from totals as t
    inner join distribution as d using (performance_year)
)

select
    *,
    savings_rate - lag(savings_rate) over (order by performance_year) as savings_rate_change_yoy,
    {{ safe_divide('earned_shared_savings - lag(earned_shared_savings) over (order by performance_year)', 'lag(earned_shared_savings) over (order by performance_year)') }} as earned_shared_savings_growth_yoy,
    {{ safe_divide('per_capita_expenditure - lag(per_capita_expenditure) over (order by performance_year)', 'lag(per_capita_expenditure) over (order by performance_year)') }} as per_capita_expenditure_growth_yoy,
    aco_count - lag(aco_count) over (order by performance_year) as aco_count_change_yoy,
    sum(earned_shared_savings) over (order by performance_year rows between unbounded preceding and current row) as cumulative_earned_shared_savings,
    sum(net_savings_to_medicare) over (order by performance_year rows between unbounded preceding and current row) as cumulative_net_savings_to_medicare
from combined
