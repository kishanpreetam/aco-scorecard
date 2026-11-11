-- Grain: one row per ACO per performance year. The two PY 2019 periods are combined for ACOs
-- reconciled in both: dollars and beneficiary years are summed, rates are recomputed from the
-- sums, and the track is taken from the later period. Window functions add year over year
-- changes, within-year rankings and percentiles, and running totals.

with periods as (
    select * from {{ ref('fct_aco_financial_year') }}
),

yearly as (
    select
        aco_key,
        performance_year,
        count(*) as periods_in_year,
        arg_max(aco_name, period_end_date) as aco_name,
        arg_max(track_code, period_end_date) as track_code,
        arg_max(track_family, period_end_date) as track_family,
        arg_max(risk_model, period_end_date) as risk_model,
        max(n_assigned_beneficiaries) as n_assigned_beneficiaries,
        sum(beneficiary_years_in_period) as beneficiary_years,
        sum(total_benchmark_expenditures) as total_benchmark_expenditures,
        sum(total_expenditures) as total_expenditures,
        sum(benchmark_minus_expenditures) as benchmark_minus_expenditures,
        sum(earned_shared_savings) as earned_shared_savings,
        sum(shared_losses_owed) as shared_losses_owed,
        sum(per_capita_expenditure * beneficiary_years_in_period) / nullif(sum(case when per_capita_expenditure is not null then beneficiary_years_in_period end), 0) as per_capita_expenditure,
        sum(risk_adjusted_per_capita_expenditure * beneficiary_years_in_period) / nullif(sum(case when risk_adjusted_per_capita_expenditure is not null then beneficiary_years_in_period end), 0) as risk_adjusted_per_capita_expenditure,
        sum(weighted_risk_score * beneficiary_years_in_period) / nullif(sum(case when weighted_risk_score is not null then beneficiary_years_in_period end), 0) as weighted_risk_score,
        avg(quality_score) as quality_score,
        bool_or(earned_savings_flag) as earned_savings_flag
    from periods
    group by 1, 2
),

rates as (
    select
        *,
        {{ safe_divide('benchmark_minus_expenditures', 'total_benchmark_expenditures') }} as savings_rate,
        {{ safe_divide('earned_shared_savings', 'n_assigned_beneficiaries') }} as earned_savings_per_beneficiary,
        benchmark_minus_expenditures - earned_shared_savings + shared_losses_owed as net_savings_to_medicare
    from yearly
),

with_history as (
    select
        *,
        lag(performance_year) over aco_history as prior_performance_year,
        lag(savings_rate) over aco_history as prior_savings_rate,
        lag(per_capita_expenditure) over aco_history as prior_per_capita_expenditure,
        lag(quality_score) over aco_history as prior_quality_score,
        avg(savings_rate) over (aco_history rows between 2 preceding and current row) as savings_rate_avg_last3,
        sum(earned_shared_savings) over (aco_history rows between unbounded preceding and current row) as cumulative_earned_shared_savings,
        row_number() over aco_history as years_reconciled_to_date
    from rates
    window aco_history as (partition by aco_key order by performance_year)
)

select
    aco_key || '|' || performance_year as aco_year_key,
    aco_key,
    performance_year,
    aco_name,
    periods_in_year,
    track_code,
    track_family,
    risk_model,
    n_assigned_beneficiaries,
    beneficiary_years,
    total_benchmark_expenditures,
    total_expenditures,
    benchmark_minus_expenditures,
    savings_rate,
    earned_shared_savings,
    shared_losses_owed,
    net_savings_to_medicare,
    earned_savings_per_beneficiary,
    per_capita_expenditure,
    risk_adjusted_per_capita_expenditure,
    weighted_risk_score,
    quality_score,
    earned_savings_flag,

    -- change from the ACO's previous year, only when that year is the immediately preceding one
    case when prior_performance_year = performance_year - 1 then savings_rate - prior_savings_rate end as savings_rate_change_yoy,
    case when prior_performance_year = performance_year - 1 then {{ safe_divide('per_capita_expenditure - prior_per_capita_expenditure', 'prior_per_capita_expenditure') }} end as per_capita_expenditure_growth_yoy,
    case when prior_performance_year = performance_year - 1 then quality_score - prior_quality_score end as quality_score_change_yoy,
    savings_rate_avg_last3,
    cumulative_earned_shared_savings,
    years_reconciled_to_date,

    -- position within the year
    rank() over (partition by performance_year order by savings_rate desc) as savings_rate_rank,
    percent_rank() over (partition by performance_year order by savings_rate) as savings_rate_percentile,
    ntile(4) over (partition by performance_year order by savings_rate) as savings_rate_quartile,
    rank() over (partition by performance_year order by earned_shared_savings desc) as earned_savings_rank,
    percent_rank() over (partition by performance_year order by quality_score) as quality_score_percentile,
    percent_rank() over (partition by performance_year order by risk_adjusted_per_capita_expenditure) as risk_adjusted_spend_percentile,
    savings_rate - median(savings_rate) over (partition by performance_year) as savings_rate_vs_year_median
from with_history
