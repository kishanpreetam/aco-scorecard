-- Grain: one row per ACO, performance period and Medicare enrollment type.
-- Person years, spending and CMS-HCC risk scores in the performance year and in benchmark
-- year 3 (the last year of the historical benchmark period).

with periods as (
    select * from {{ ref('int_aco_period__keyed') }}
),

long_format as (
    {% set types = ['esrd', 'disabled', 'aged_dual', 'aged_nondual'] %}
    {% for t in types %}
    select
        aco_key,
        performance_period_id,
        performance_year,
        '{{ t }}' as enrollment_type_code,
        person_years_{{ t }} as person_years,
        per_capita_exp_{{ t }} as per_capita_expenditure,
        risk_score_{{ t }} as risk_score,
        person_years_{{ t }}_by3 as person_years_by3,
        per_capita_exp_{{ t }}_by3 as per_capita_expenditure_by3,
        risk_score_{{ t }}_by3 as risk_score_by3
    from periods
    {% if not loop.last %}union all{% endif %}
    {% endfor %}
)

select
    aco_key || '|' || performance_period_id || '|' || enrollment_type_code as attribution_key,
    aco_key || '|' || performance_period_id as aco_period_key,
    aco_key,
    performance_period_id,
    performance_year,
    make_date(performance_year, 1, 1) as performance_year_start,
    enrollment_type_code,
    person_years,
    {{ safe_divide('person_years', 'sum(person_years) over (partition by aco_key, performance_period_id)') }} as person_year_share,
    per_capita_expenditure,
    risk_score,
    {{ safe_divide('per_capita_expenditure', 'risk_score') }} as risk_adjusted_per_capita_expenditure,
    person_years_by3,
    per_capita_expenditure_by3,
    risk_score_by3,
    {{ safe_divide('risk_score', 'risk_score_by3') }} - 1 as risk_score_change_since_by3
from long_format
