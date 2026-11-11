-- All PUF periods stacked into one relation, with the period length and derived values that
-- make the years comparable. Every staging model emits the same columns in the same order
-- (they are generated from one mapping), so a positional union is safe; the staging column
-- tests guard the contract.

with unioned as (
    {% for pid in var('expected_periods') %}
    select * from {{ ref('stg_puf__py' ~ (pid | lower)) }}
    {% if not loop.last %}union all{% endif %}
    {% endfor %}
),

periods as (
    select
        *,
        case period_rule
            when 'start_date_2013' then
                case
                    when current_start_date = date '2012-04-01' then 21
                    when current_start_date = date '2012-07-01' then 18
                    else 12
                end
            when 'six_month_flag_first_half' then case when six_month_flag then 6 else 12 end
            when 'second_half' then 6
            else 12
        end as period_months,
        case period_rule
            when 'start_date_2013' then greatest(current_start_date, date '2012-04-01')
            when 'second_half' then date '2019-07-01'
            else make_date(performance_year, 1, 1)
        end as period_start_date,
        case
            when period_rule = 'six_month_flag_first_half' and six_month_flag then date '2019-06-30'
            else make_date(performance_year, 12, 31)
        end as period_end_date
    from unioned
),

derived as (
    select
        *,
        -- one definition of savings rate for every year (PY 2013 does not publish it)
        {{ safe_divide('benchmark_minus_expenditures', 'total_benchmark_expenditures') }} as savings_rate,
        person_years * period_months / 12.0 as beneficiary_years_in_period,
        greatest(earned_savings_losses, 0) as earned_shared_savings,
        greatest(-earned_savings_losses, 0) as shared_losses_owed,
        coalesce(person_years_esrd, 0) + coalesce(person_years_disabled, 0)
            + coalesce(person_years_aged_dual, 0) + coalesce(person_years_aged_nondual, 0) as person_years_by_type_total,
        -- person-year weighted mean of the enrollment type expenditures (used for PY 2013)
        {{ safe_divide(
            'coalesce(per_capita_exp_esrd * person_years_esrd, 0) + coalesce(per_capita_exp_disabled * person_years_disabled, 0)
             + coalesce(per_capita_exp_aged_dual * person_years_aged_dual, 0) + coalesce(per_capita_exp_aged_nondual * person_years_aged_nondual, 0)',
            'coalesce(person_years_esrd, 0) + coalesce(person_years_disabled, 0) + coalesce(person_years_aged_dual, 0) + coalesce(person_years_aged_nondual, 0)'
        ) }} as per_capita_expenditure_by_type,
        -- risk normalized spending: divide each enrollment type's spending by its mean CMS-HCC
        -- risk score, then weight by person years. Types without a published risk score or
        -- spending value are left out of both the numerator and the denominator.
        {{ safe_divide(
            'coalesce(case when risk_score_esrd > 0 then per_capita_exp_esrd / risk_score_esrd * person_years_esrd end, 0)
             + coalesce(case when risk_score_disabled > 0 then per_capita_exp_disabled / risk_score_disabled * person_years_disabled end, 0)
             + coalesce(case when risk_score_aged_dual > 0 then per_capita_exp_aged_dual / risk_score_aged_dual * person_years_aged_dual end, 0)
             + coalesce(case when risk_score_aged_nondual > 0 then per_capita_exp_aged_nondual / risk_score_aged_nondual * person_years_aged_nondual end, 0)',
            'coalesce(case when risk_score_esrd > 0 and per_capita_exp_esrd is not null then person_years_esrd end, 0)
             + coalesce(case when risk_score_disabled > 0 and per_capita_exp_disabled is not null then person_years_disabled end, 0)
             + coalesce(case when risk_score_aged_dual > 0 and per_capita_exp_aged_dual is not null then person_years_aged_dual end, 0)
             + coalesce(case when risk_score_aged_nondual > 0 and per_capita_exp_aged_nondual is not null then person_years_aged_nondual end, 0)'
        ) }} as risk_adjusted_per_capita_expenditure,
        {{ safe_divide(
            'coalesce(risk_score_esrd * person_years_esrd, 0) + coalesce(risk_score_disabled * person_years_disabled, 0)
             + coalesce(risk_score_aged_dual * person_years_aged_dual, 0) + coalesce(risk_score_aged_nondual * person_years_aged_nondual, 0)',
            'coalesce(case when risk_score_esrd is not null then person_years_esrd end, 0) + coalesce(case when risk_score_disabled is not null then person_years_disabled end, 0)
             + coalesce(case when risk_score_aged_dual is not null then person_years_aged_dual end, 0) + coalesce(case when risk_score_aged_nondual is not null then person_years_aged_nondual end, 0)'
        ) }} as weighted_risk_score
    from periods
)

select
    *,
    coalesce(per_capita_expenditure_reported, per_capita_expenditure_by_type) as per_capita_expenditure,
    case when per_capita_expenditure_reported is null then 'derived_from_enrollment_types' else 'published' end as per_capita_expenditure_source
from derived
