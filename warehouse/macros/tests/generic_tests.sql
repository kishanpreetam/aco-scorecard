{# Project generic tests. dbt packages are not used so the build needs nothing beyond PyPI. #}

{% test accepted_range(model, column_name, min_value=none, max_value=none, row_filter=none) %}
select *
from {{ model }}
where {{ column_name }} is not null
  and (
      {% if min_value is not none %}{{ column_name }} < {{ min_value }}{% else %}false{% endif %}
      or {% if max_value is not none %}{{ column_name }} > {{ max_value }}{% else %}false{% endif %}
  )
  {% if row_filter %}and ({{ row_filter }}){% endif %}
{% endtest %}


{# Fails rows where the expression is false. NULL results pass, so use not_null where a value is required. #}
{% test expression_is_true(model, expression, column_name=none, row_filter=none) %}
select *
from {{ model }}
where not ({{ expression }})
  {% if row_filter %}and ({{ row_filter }}){% endif %}
{% endtest %}


{% test unique_combination(model, columns) %}
select {{ columns | join(', ') }}, count(*) as n_rows
from {{ model }}
group by {{ columns | join(', ') }}
having count(*) > 1
{% endtest %}


{# Every expected value must appear at least once (used for year coverage). #}
{% test values_present(model, column_name, expected_values=none, expected_var=none) %}
{% if expected_var %}{% set expected_values = var(expected_var) %}{% endif %}
with expected as (
    select unnest([{% for v in expected_values %}'{{ v }}'{% if not loop.last %}, {% endif %}{% endfor %}]) as expected_value
),
actual as (
    select distinct cast({{ column_name }} as varchar) as actual_value
    from {{ model }}
    where {{ column_name }} is not null
)
select expected_value
from expected
where expected_value not in (select actual_value from actual)
{% endtest %}


{# Row count of the model must equal the row count of another relation, optionally filtered. #}
{% test row_count_matches(model, compare_model, model_filter=none, compare_filter=none) %}
with a as (select count(*) as n from {{ model }} {% if model_filter %}where {{ model_filter }}{% endif %}),
     b as (select count(*) as n from {{ compare_model }} {% if compare_filter %}where {{ compare_filter }}{% endif %})
select a.n as model_rows, b.n as compare_rows
from a cross join b
where a.n <> b.n
{% endtest %}
