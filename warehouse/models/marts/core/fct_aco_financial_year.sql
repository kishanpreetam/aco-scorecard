-- Grain: one row per ACO per CMS performance period. Every performance year has one period
-- except PY 2019, which has two (2019 and 2019A); 139 ACOs were reconciled in both.
-- Dollar totals cover the whole period (6 months for the 2019 half-year periods, 18 or 21
-- months for 2012 starters in PY 2013); per capita values are annualized by CMS.

with periods as (
    select * from {{ ref('int_aco_period__keyed') }}
),

tracks as (
    select * from {{ ref('track_reference') }}
)

select
    p.aco_key || '|' || p.performance_period_id as aco_period_key,
    p.aco_key,
    p.aco_key_method,
    p.aco_source_id,
    p.aco_name,
    p.performance_period_id,
    p.performance_year,
    make_date(p.performance_year, 1, 1) as performance_year_start,
    p.period_start_date,
    p.period_end_date,
    p.period_months,

    -- agreement and track
    p.track_code,
    t.track_family,
    coalesce(p.risk_model_reported, t.risk_model) as risk_model,
    p.agreement_type,
    p.agreement_period_num,
    p.current_start_date,
    p.assignment_type,
    p.revenue_category,
    p.snf_waiver_flag,

    -- attribution
    p.n_assigned_beneficiaries,
    p.person_years,
    p.beneficiary_years_in_period,

    -- benchmark, spending and shared savings
    p.total_benchmark_expenditures,
    p.total_expenditures,
    p.benchmark_minus_expenditures,
    p.savings_rate,
    p.savings_rate_reported,
    p.min_savings_rate,
    p.generated_savings_losses,
    p.earned_savings_losses,
    p.earned_shared_savings,
    p.shared_losses_owed,
    coalesce(p.max_sharing_rate_reported, t.max_sharing_rate) as max_sharing_rate,
    case when p.max_sharing_rate_reported is null then 'track_reference' else 'published' end as max_sharing_rate_source,
    p.final_sharing_rate,
    p.final_loss_rate,
    p.updated_benchmark_per_capita,
    p.historical_benchmark_per_capita,
    p.per_capita_expenditure,
    p.per_capita_expenditure_source,
    p.per_capita_expenditure * p.person_years as annualized_expenditure,
    p.risk_adjusted_per_capita_expenditure,
    p.risk_adjusted_per_capita_expenditure * p.person_years as risk_adjusted_annualized_expenditure,
    p.weighted_risk_score,
    {{ safe_divide('p.earned_shared_savings', 'p.n_assigned_beneficiaries') }} as earned_shared_savings_per_beneficiary,

    -- quality
    p.quality_score,
    p.quality_score_raw,
    p.met_quality_standard_flag,
    p.reduced_shared_savings_flag,

    -- population health context
    p.pct_dual_eligible,
    p.n_beneficiaries_age_0_64,
    p.n_beneficiaries_age_65_74,
    p.n_beneficiaries_age_75_84,
    p.n_beneficiaries_age_85_plus,
    p.inpatient_discharges_per_1000,
    p.ed_visits_per_1000,
    p.primary_care_services_per_1000,
    p.pcp_services_per_1000,
    p.n_primary_care_physicians,
    p.n_specialists,

    -- flags used as semantic layer dimensions
    p.earned_shared_savings > 0 as earned_savings_flag,
    p.shared_losses_owed > 0 as owed_losses_flag,
    p.savings_rate >= p.min_savings_rate as savings_rate_met_msr_flag,
    case
        when p.savings_rate is null then 'Unknown'
        when p.savings_rate < 0 then 'Spent above benchmark'
        when p.savings_rate < 0.02 then '0 to 2 percent'
        when p.savings_rate < 0.05 then '2 to 5 percent'
        else '5 percent or more'
    end as savings_rate_band,
    1 as aco_period_count,

    -- lineage
    p._source_file_key,
    p._source_sha256,
    p._source_row_number,
    p._loaded_at
from periods as p
left join tracks as t using (track_code)
