-- Links the encrypted ACO_Num used through PY 2017 to the unencrypted ACO_ID used from PY 2018.
-- CMS mentions an ACO ID crosswalk, but none is listed in the data.cms.gov catalog, so this
-- model builds a conservative one: an exact match on the normalized ACO name AND the initial
-- agreement start date between the PY 2017 and PY 2018 files, kept only when the match is
-- one to one in both directions. Unmatched legacy ACOs keep a LEGACY- key downstream.

with legacy as (
    select
        aco_source_id as legacy_aco_num,
        aco_name as legacy_aco_name,
        upper(regexp_replace(aco_name, '[^A-Za-z0-9]', '', 'g')) as name_key,
        initial_start_date
    from {{ ref('stg_puf__py2017') }}
),

current_ids as (
    select
        aco_source_id as aco_id,
        aco_name as current_aco_name,
        upper(regexp_replace(aco_name, '[^A-Za-z0-9]', '', 'g')) as name_key,
        initial_start_date
    from {{ ref('stg_puf__py2018') }}
),

candidates as (
    select
        l.legacy_aco_num,
        c.aco_id,
        l.legacy_aco_name,
        c.current_aco_name,
        l.initial_start_date
    from legacy as l
    inner join current_ids as c
        on l.name_key = c.name_key
        and l.initial_start_date = c.initial_start_date
)

select
    legacy_aco_num,
    aco_id,
    legacy_aco_name,
    current_aco_name,
    initial_start_date,
    'exact normalized name and initial start date, PY 2017 to PY 2018, one to one' as match_rule
from candidates
qualify count(*) over (partition by legacy_aco_num) = 1
    and count(*) over (partition by aco_id) = 1
