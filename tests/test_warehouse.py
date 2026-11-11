"""Checks on the built warehouse, written independently of the dbt tests."""

import json

from aco_scorecard.paths import ROOT


def test_every_raw_row_reaches_the_fact_table(con):
    report = json.loads((ROOT / "results" / "ingest_report.json").read_text())
    raw = {f["period_id"]: f["rows"] for f in report["files"] if f["series"].startswith("Performance Year")}
    fact = dict(con.execute("select performance_period_id, count(*) from core.fct_aco_financial_year group by 1").fetchall())
    assert raw == fact
    assert sum(fact.values()) == 5476


def test_keys_are_unique(con):
    for table, key in [
        ("core.fct_aco_financial_year", "aco_period_key"),
        ("core.dim_aco", "aco_key"),
        ("core.fct_attribution", "attribution_key"),
        ("core.fct_aco_quality_measure", "aco_measure_key"),
        ("reporting.mart_aco_year_scorecard", "aco_year_key"),
    ]:
        total, distinct = con.execute(f"select count(*), count(distinct {key}) from {table}").fetchone()
        assert total == distinct, table


def test_2024_totals_match_the_raw_file(con):
    num = lambda c: f"try_cast(replace(replace(trim(\"{c}\"), ',', ''), '%', '') as double)"
    raw = con.execute(
        f"select sum({num('BnchmkMinExp')}), sum({num('ABtotBnchmk')}), sum(greatest({num('EarnSaveLoss')}, 0)), count(*) from raw.puf_py2024"
    ).fetchone()
    mart = con.execute(
        "select benchmark_minus_expenditures, total_benchmark_expenditures, earned_shared_savings, aco_count from reporting.mart_program_year_summary where performance_year = 2024"
    ).fetchone()
    assert abs(raw[0] - mart[0]) < 1
    assert abs(raw[1] - mart[1]) < 1
    assert abs(raw[2] - mart[2]) < 1
    assert raw[3] == mart[3]


def test_2019_combines_both_periods(con):
    distinct_acos = con.execute(
        "select count(distinct id) from (select trim(\"ACO_ID\") as id from raw.puf_py2019 union all select trim(\"ACO_ID\") from raw.puf_py2019a)"
    ).fetchone()[0]
    mart = con.execute("select aco_count, aco_reconciliations from reporting.mart_program_year_summary where performance_year = 2019").fetchone()
    assert mart == (distinct_acos, 475 + 205)


def test_identifier_bridge_is_one_to_one(con):
    n, legacy, current = con.execute("select count(*), count(distinct legacy_aco_num), count(distinct aco_id) from intermediate.int_aco_id_bridge").fetchone()
    assert n == legacy == current
    assert n > 0


def test_rates_are_fractions_and_scores_are_points(con):
    worst = con.execute(
        "select max(abs(savings_rate)), max(final_sharing_rate), max(quality_score), min(quality_score) from core.fct_aco_financial_year"
    ).fetchone()
    assert worst[0] < 0.5 and worst[1] <= 0.75 and worst[2] <= 100 and worst[3] >= 0
