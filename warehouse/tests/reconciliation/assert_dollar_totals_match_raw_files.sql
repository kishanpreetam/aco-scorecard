-- Independent check against the raw text tables: total benchmark minus expenditures per period
-- in the fact table must equal the same column summed straight from each raw file, parsed here
-- with its own logic (the column name BnchmkMinExp is the same in every year).
with raw_totals as (
    {% for pid in var('expected_periods') %}
    select '{{ pid }}' as performance_period_id,
           sum(try_cast(replace(replace(trim("BnchmkMinExp"), ',', ''), '$', '') as double)) as raw_total,
           count(*) as raw_rows
    from {{ source('cms_raw', 'puf_py' ~ (pid | lower)) }}
    {% if not loop.last %}union all{% endif %}
    {% endfor %}
),
fact_totals as (
    select performance_period_id, sum(benchmark_minus_expenditures) as fact_total, count(*) as fact_rows
    from {{ ref('fct_aco_financial_year') }}
    group by 1
)
select *
from raw_totals
full outer join fact_totals using (performance_period_id)
where raw_rows is distinct from fact_rows
   or abs(coalesce(raw_total, 0) - coalesce(fact_total, 0)) > 1
