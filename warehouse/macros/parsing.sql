{#
  Parsing helpers used by the generated staging models.
  CMS files mix plain numbers, numbers with thousands separators, dollar signs and percent
  signs, and sentinel codes ("*", "-", "N/A", "/", "^", "~", "P4R", "."). Anything that is not
  a number after removing "$", "," and "%" becomes NULL; the sentinel itself is kept where it
  carries meaning (see measure_status and county_status).
#}

{% macro parse_number(column) -%}
try_cast(nullif(regexp_replace(trim({{ column }}), '[$,%[:space:]]', '', 'g'), '') as double)
{%- endmacro %}

{% macro parse_flag(column) -%}
case
    when try_cast(trim({{ column }}) as double) = 1 then true
    when try_cast(trim({{ column }}) as double) = 0 then false
end
{%- endmacro %}

{% macro parse_date(column) -%}
cast(try_strptime(split_part(trim({{ column }}), ' ', 1), '%m/%d/%Y') as date)
{%- endmacro %}

{% macro clean_text(column) -%}
nullif(regexp_replace(trim({{ column }}), '[[:space:]]+', ' ', 'g'), '')
{%- endmacro %}

{% macro measure_status(column) -%}
case
    when {{ column }} is null or trim({{ column }}) = '' then 'not_reported'
    when {{ parse_number(column) }} is not null then 'reported'
    when trim({{ column }}) = '*' then 'suppressed_small_cell'
    when trim({{ column }}) = '-' then 'not_reported'
    when upper(trim({{ column }})) = 'N/A' then 'not_applicable'
    when trim({{ column }}) = '/' then 'reporting_error'
    when trim({{ column }}) = '^' then 'cahps_waived_auto_credit'
    when trim({{ column }}) = '~' then 'pay_for_reporting_suppressed'
    else 'unrecognized'
end
{%- endmacro %}

{# County counts: "." means no beneficiaries of that type (zero), "*" means suppressed (1 to 10
   or complementary suppression). The PY 2016 county file leaves both cases blank. #}
{% macro parse_county_count(column) -%}
case
    when trim({{ column }}) = '.' then 0.0
    else {{ parse_number(column) }}
end
{%- endmacro %}

{% macro county_status(column) -%}
case
    when {{ column }} is null or trim({{ column }}) = '' then 'blank_suppressed_or_missing'
    when trim({{ column }}) = '.' then 'none'
    when trim({{ column }}) = '*' then 'suppressed'
    when {{ parse_number(column) }} is not null then 'reported'
    else 'unrecognized'
end
{%- endmacro %}

{% macro safe_divide(numerator, denominator) -%}
case when ({{ denominator }}) is null or ({{ denominator }}) = 0 then null else ({{ numerator }}) / ({{ denominator }}) end
{%- endmacro %}
