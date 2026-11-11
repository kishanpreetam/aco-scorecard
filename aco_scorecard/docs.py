"""Generate docs/schema_mapping.md and docs/data_dictionary.md.

schema_mapping.md is rendered from config/schema_mapping.yml, so the documented mapping can
never drift from the one the pipeline runs. data_dictionary.md is rendered from the dbt
manifest and catalog (descriptions and warehouse column types) plus the CMS definitions of the
source columns, read from the PY 2024 data dictionary downloaded from data.cms.gov.
"""

from __future__ import annotations

import json
import re
import sys

from .mapping import Field, Source, load_mapping
from .paths import DBT_DIR, DOCS_DIR, RAW_DIR

DERIVED = {
    "aco_key": "Conformed ACO key: published ACO_ID from PY 2018, the bridged ACO_ID for earlier rows, or LEGACY-<ACO_Num> when no bridge exists.",
    "aco_key_method": "How aco_key was assigned: published_aco_id, bridged_legacy_id or legacy_id_only.",
    "aco_period_key": "aco_key and performance_period_id joined with a pipe; primary key of fct_aco_financial_year.",
    "aco_year_key": "aco_key and performance_year joined with a pipe.",
    "aco_measure_key": "aco_key, performance_period_id, measure_key and collection_type joined with pipes.",
    "attribution_key": "aco_key, performance_period_id and enrollment_type_code joined with pipes.",
    "aco_county_key": "aco_key, performance_period_id and ssa_county_key joined with pipes.",
    "performance_year": "Calendar performance year (2013 to 2024). Both PY 2019 periods have performance_year 2019.",
    "performance_year_start": "January 1 of the performance year; the time dimension used by the semantic layer.",
    "period_start_date": "First day covered by the period's dollar totals.",
    "period_end_date": "Last day covered by the period's dollar totals.",
    "period_months": "Months covered by the dollar totals: 12, 6 (2019 half-year periods), or 18 or 21 (2012 starters in PY 2013).",
    "track_family": "Track grouped for reporting: Track 1, Track 1+, Track 2, Track 3, BASIC A and B (one-sided), BASIC C to E (two-sided), ENHANCED.",
    "risk_model": "One-Sided or Two-Sided; published from PY 2019, derived from the track before that.",
    "beneficiary_years_in_period": "person_years times period_months / 12; weights per capita values when periods are combined.",
    "savings_rate": "benchmark_minus_expenditures / total_benchmark_expenditures, computed the same way for every year.",
    "earned_shared_savings": "Positive part of earned_savings_losses: the shared savings payment CMS made.",
    "shared_losses_owed": "Negative part of earned_savings_losses, as a positive number: losses the ACO owed CMS.",
    "max_sharing_rate": "Maximum sharing rate for the track (published through PY 2021, from track_reference after).",
    "max_sharing_rate_source": "published or track_reference.",
    "per_capita_expenditure": "Annualized spending per assigned beneficiary person year (published from PY 2014, derived from enrollment types for PY 2013).",
    "per_capita_expenditure_source": "published or derived_from_enrollment_types.",
    "annualized_expenditure": "per_capita_expenditure times person_years.",
    "risk_adjusted_per_capita_expenditure": "Sum over enrollment types of (per capita spending / CMS-HCC risk score) times person years, divided by the person years of the types included.",
    "risk_adjusted_annualized_expenditure": "risk_adjusted_per_capita_expenditure times person_years.",
    "weighted_risk_score": "Person-year weighted mean prospective CMS-HCC risk score across enrollment types.",
    "earned_shared_savings_per_beneficiary": "earned_shared_savings / n_assigned_beneficiaries.",
    "earned_savings_flag": "True when earned_shared_savings is above zero.",
    "owed_losses_flag": "True when shared_losses_owed is above zero.",
    "savings_rate_met_msr_flag": "True when savings_rate is at least min_savings_rate.",
    "savings_rate_band": "Spent above benchmark, 0 to 2 percent, 2 to 5 percent, or 5 percent or more.",
    "aco_period_count": "Always 1; summed by the semantic layer to count reconciliations.",
    "measure_key": "Conformed quality measure key (see dim_measure).",
    "collection_type": "How the measure was collected: CAHPS survey, Claims, Web Interface, eCQM, MIPS CQM, Medicare CQM, eCQM or MIPS CQM (2021), EHR attestation.",
    "source_column": "PUF column the value came from.",
    "raw_value": "Value text exactly as published.",
    "measure_value": "Performance rate as a number (Quality ID 479 scaled from a proportion to percent).",
    "value_status": "reported, not_reported, suppressed_small_cell, not_applicable, reporting_error, cahps_waived_auto_credit or pay_for_reporting_suppressed.",
    "is_reported": "True when value_status is reported.",
    "enrollment_type_code": "esrd, disabled, aged_dual or aged_nondual.",
    "person_year_share": "Share of the ACO's person years in this enrollment type.",
    "risk_score": "Mean prospective CMS-HCC risk score for the enrollment type in the performance year.",
    "risk_score_by3": "Mean prospective CMS-HCC risk score for the enrollment type in benchmark year 3.",
    "risk_score_change_since_by3": "risk_score / risk_score_by3 minus 1.",
    "ssa_county_key": "Zero padded SSA state code (2 digits) plus SSA county code (3 digits).",
    "is_suppressed": "True when CMS suppressed the county's total assigned beneficiaries.",
}

MORE = {
    "performance_period_id": "CMS performance period id: 2013 to 2024, with PY 2019 split into 2019 and 2019A.",
    "track_code": "Decoded track: TRACK_1, TRACK_1_PLUS, TRACK_2, TRACK_3, BASIC_A to BASIC_E or ENHANCED.",
    "track_name": "Track name as CMS writes it.",
    "track_flag_count": "Number of track flags set in the source row; tests require exactly 1.",
    "program_era": "Original tracks (2012 to mid 2019) or Pathways to Success (July 2019 on).",
    "display_order": "Sort order for reports.",
    "notes": "Notes on the source or method.",
    "description": "Plain-language description.",
    "_source_file_key": "Raw file the row came from (lineage).",
    "_source_sha256": "sha256 of the raw file (lineage).",
    "_source_row_number": "Row number in the raw file (lineage).",
    "_loaded_at": "When the raw file was loaded (UTC).",
    "source_file_key": "Raw file the period was loaded from.",
    "source_sha256": "sha256 of that raw file.",
    "loaded_at": "When the raw file was loaded (UTC).",
    "period_rule": "How period length is set: full_year, start_date_2013, six_month_flag_first_half or second_half.",
    "aco_id_system": "encrypted_aco_num (PY 2013 to 2017) or aco_id (PY 2018 on).",
    "id_system": "encrypted_aco_num (PY 2013 to 2017) or aco_id (PY 2018 on).",
    "period_label": "Readable period name.",
    "nominal_start": "Nominal first day of the period.",
    "nominal_end": "Nominal last day of the period.",
    "quality_measure_set": "ACO measure set (2013 to 2020) or APM Performance Pathway (2021 to 2024).",
    "quality_score_definition": "What QualScore measured that year.",
    "comparability_group": "Quality scores are comparable only within the same group.",
    "measure_name": "Measure name.",
    "legacy_code": "ACO measure code used in PY 2016 to 2020 (for example ACO-27).",
    "app_code": "APM Performance Pathway identifier used from PY 2021 (for example Quality ID 001).",
    "domain": "Measure domain (legacy ACO domains; APP measures take their predecessor's domain).",
    "higher_is_better": "False for inverse measures such as readmissions and HbA1c poor control.",
    "unit": "Unit of the published performance rate.",
    "predecessor_measure_key": "Earlier measure this one replaced when CMS changed the method.",
    "collection_types": "Collection types seen for the measure.",
    "first_performance_year": "First year the item appears in the data.",
    "last_performance_year": "Last year the item appears in the data.",
    "published_aco_id": "Unencrypted ACO_ID, when the ACO appears in PY 2018 or later.",
    "legacy_aco_num": "Encrypted ACO_Num used in PY 2013 to 2017, when the ACO appears in those years.",
    "legacy_aco_name": "ACO name in the PY 2017 file.",
    "current_aco_name": "ACO name in the PY 2018 file.",
    "aco_id": "Unencrypted ACO_ID (PY 2018 on).",
    "match_rule": "Rule used to link the identifiers.",
    "performance_years_reconciled": "Distinct performance years the ACO was reconciled.",
    "performance_periods_reconciled": "Performance periods the ACO was reconciled (an ACO in both PY 2019 periods counts twice).",
    "latest_performance_period_id": "Most recent period the ACO appears in.",
    "latest_track_code": "Track in the most recent period.",
    "latest_agreement_type": "Agreement type in the most recent period.",
    "latest_assigned_beneficiaries": "Assigned beneficiaries in the most recent period.",
    "is_active_in_latest_year": "True when the ACO was reconciled in the latest performance year loaded.",
    "states_with_assigned_beneficiaries": "States with at least one county row for the ACO in its latest county file year.",
    "enrollment_type_name": "Readable enrollment type.",
    "person_years_by3": "Person years for the enrollment type in benchmark year 3.",
    "per_capita_expenditure_by3": "Per capita spending for the enrollment type in benchmark year 3.",
    "person_years_by_type_total": "Sum of the four enrollment type person years (suppressed cells count as zero).",
    "per_capita_expenditure_by_type": "Person-year weighted mean of the enrollment type per capita spending.",
    "state_name": "State of beneficiary residence (upper case, as published).",
    "county_name": "County of beneficiary residence (upper case, as published).",
    "ssa_state_code": "SSA state code, zero padded to 2 digits.",
    "ssa_county_code": "SSA county code, zero padded to 3 digits.",
    "total_person_years": "Assigned beneficiary person years in the county (NULL when suppressed).",
    "total_person_years_status": "reported, suppressed, none or blank_suppressed_or_missing (PY 2016 leaves suppressed cells blank).",
    "total_assigned_beneficiaries": "Assigned beneficiaries in the county (NULL when suppressed).",
    "total_assigned_beneficiaries_status": "reported, suppressed or blank_suppressed_or_missing.",
    "periods_in_year": "Performance periods combined into the row (2 for ACOs in both PY 2019 periods).",
    "beneficiary_years": "Sum of beneficiary_years_in_period over the periods combined.",
    "net_savings_to_medicare": "Benchmark minus expenditures, less shared savings payments, plus shared losses owed.",
    "earned_savings_per_beneficiary": "Earned shared savings divided by assigned beneficiaries.",
    "savings_rate_change_yoy": "Change in savings rate from the previous year (fraction points); NULL if that year is missing.",
    "per_capita_expenditure_growth_yoy": "Growth in per capita spending from the previous year.",
    "quality_score_change_yoy": "Change in quality score from the previous year (only meaningful within a scoring era).",
    "cumulative_earned_shared_savings": "Running total of earned shared savings through the year.",
    "cumulative_net_savings_to_medicare": "Running total of net savings to Medicare through the year.",
    "years_reconciled_to_date": "Number of years the ACO has been reconciled up to and including this one.",
    "savings_rate_rank": "Rank by savings rate within the year (1 is highest).",
    "savings_rate_percentile": "Percent rank of savings rate within the year (0 to 1).",
    "savings_rate_quartile": "Quartile of savings rate within the year (4 is highest).",
    "earned_savings_rank": "Rank by earned shared savings within the year.",
    "quality_score_percentile": "Percent rank of quality score within the year.",
    "risk_adjusted_spend_percentile": "Percent rank of risk-adjusted per capita spending within the year (0 is lowest).",
    "savings_rate_vs_year_median": "Savings rate minus the median ACO savings rate that year.",
    "aco_count": "Distinct ACOs.",
    "aco_reconciliations": "ACO performance periods reconciled.",
    "assigned_beneficiaries": "Assigned beneficiaries (each ACO counted once per year).",
    "reconciliations_earning_savings": "Reconciliations with a shared savings payment.",
    "reconciliations_owing_losses": "Reconciliations that owed shared losses.",
    "share_earning_savings": "Reconciliations earning shared savings divided by all reconciliations.",
    "two_sided_aco_count": "ACOs in a two-sided (savings and losses) arrangement.",
    "two_sided_share": "Share of ACOs in a two-sided arrangement.",
    "savings_rate_p25": "25th percentile of ACO savings rates that year.",
    "savings_rate_median": "Median ACO savings rate that year.",
    "savings_rate_p75": "75th percentile of ACO savings rates that year.",
    "quality_score_mean": "Mean ACO quality score.",
    "quality_score_median": "Median ACO quality score.",
    "earned_shared_savings_growth_yoy": "Growth in earned shared savings from the previous year.",
    "aco_count_change_yoy": "Change in the number of ACOs from the previous year.",
    "track_year_key": "Performance year and track family joined with a pipe.",
    "share_of_year_acos": "Share of the year's ACOs in the track family.",
    "share_of_year_earned_savings": "Share of the year's earned shared savings paid to the track family.",
    "savings_rate_rank_in_year": "Rank of the track family by savings rate within the year.",
    "measure_year_key": "Measure, collection type and year joined with pipes.",
    "aco_results": "ACO results expected for the measure that year.",
    "reported_results": "Results with a reported value.",
    "suppressed_results": "Results CMS suppressed for small cells.",
    "not_applicable_results": "Results marked N/A (no eligible patients).",
    "waived_results": "Results waived (2020 CAHPS automatic credit or pay-for-reporting suppression).",
    "mean_value": "Mean of reported rates.",
    "p10_value": "10th percentile of reported rates.",
    "median_value": "Median of reported rates.",
    "p90_value": "90th percentile of reported rates.",
    "reporting_rate": "Reported results divided by expected results.",
    "median_change_yoy": "Change in the median rate from the previous year.",
    "median_improved_yoy": "True when the median moved in the better direction (lower for inverse measures).",
    "state_year_key": "Performance year and state joined with a pipe.",
    "acos_with_beneficiaries": "ACOs with at least one county row in the state.",
    "counties_with_beneficiaries": "Counties with at least one ACO row.",
    "reported_person_years": "Sum of reported (unsuppressed) county person years.",
    "reported_person_years_esrd": "Reported ESRD person years.",
    "reported_person_years_disabled": "Reported disabled person years.",
    "reported_person_years_aged_dual": "Reported aged dual person years.",
    "reported_person_years_aged_nondual": "Reported aged non-dual person years.",
    "suppressed_aco_county_rows": "ACO by county rows with suppressed totals.",
    "aco_county_rows": "ACO by county rows.",
    "share_of_reported_person_years": "Share of the year's reported person years living in the state.",
    "state_rank_in_year": "Rank of the state by reported person years within the year.",
    "date_day": "Calendar day.",
}
DERIVED.update(MORE)

TERM_ALIASES = {"ACO_Num": None, "Sav_Rate": "Sav_rate"}


def compress(field: Field, order: list[str]) -> list[tuple[str, Source | None]]:
    """Group consecutive periods that share the same source spec."""
    out: list[tuple[list[str], Source | None]] = []
    for pid in order:
        src = field.sources.get(pid)
        if out and out[-1][1] == src:
            out[-1][0].append(pid)
        else:
            out.append(([pid], src))
    return [((p[0] if len(p) == 1 else f"{p[0]} to {p[-1]}"), s) for p, s in out]


def describe_source(src: Source | None) -> str:
    if src is None:
        return "not published"
    if src.expr:
        return "`" + src.expr.replace("{", "").replace("}", "") + "`"
    s = f"`{src.column}`"
    if src.scale == 0.01:
        s += " (percent, divided by 100)"
    elif src.scale == 100:
        s += " (fraction, times 100)"
    elif src.scale:
        s += f" (times {src.scale})"
    return s


def schema_mapping_md() -> str:
    m = load_mapping()
    order = m.period_ids
    L = [
        "# Schema mapping",
        "",
        "Generated from `config/schema_mapping.yml` by `aco_scorecard/docs.py`. Do not edit by hand.",
        "",
        "CMS publishes one Performance Year Financial and Quality Results file per performance period. Between PY 2013 and",
        "PY 2024 the files renamed columns (for example `ACO_NAME` to `ACO_Name`, `N_AB_Year` to `N_AB_Year_PY`, `Sav_rate` to",
        "`Sav_Rate` and back), changed units (rates published as fractions in some years and percents in others, with and",
        "without a `%` sign), switched identifiers (encrypted `ACO_Num` through PY 2017, unencrypted `ACO_ID` from PY 2018),",
        "recoded tracks (0/1 flags through PY 2021, a single code from PY 2022) and replaced the quality measure set in PY 2021.",
        "Every one of those decisions is recorded below, period by period. The loader refuses a file if any column named here is",
        "missing, and the dbt tests check that every rate lands on the expected scale in every period.",
        "",
        f"Mapping version: {m.version}. Periods: {', '.join(order)}.",
        "",
        "## Financial, attribution and population fields",
        "",
        "| canonical column | type | unit | source by period |",
        "|---|---|---|---|",
    ]
    for f in m.fields:
        parts = "; ".join(f"{rng}: {describe_source(s)}" for rng, s in compress(f, order))
        L.append(f"| `{f.name}` | {f.type} | {f.unit or ''} | {parts} |")
    L += ["", "## Track decoding", "", "| periods | rule |", "|---|---|"]
    for key, spec in m.raw["tracks"].items():
        if "flags" in spec:
            rule = "0/1 flags: " + ", ".join(f"`{c}` = {v}" for c, v in spec["flags"].items())
            if spec.get("default"):
                rule += f"; none set = {spec['default']}"
        else:
            rule = f"code column `{spec['code']['column']}`: " + ", ".join(f"{k} = {v}" for k, v in spec["code"]["values"].items())
        L.append(f"| {key.replace('..', ' to ')} | {rule} |")
    L += [
        "",
        "## Quality measure columns",
        "",
        "Legacy ACO measure columns (PY 2016 to 2020) map to their APM Performance Pathway names using the crosswalk printed in",
        "the CMS PY 2021 data dictionary notes. Measure level results are not published for PY 2013 to 2015.",
        "",
        "| measure key | collection | source by period |",
        "|---|---|---|",
    ]
    for q in m.raw["quality_measures"]:
        parts = "; ".join(f"{k.replace('..', ' to ')}: `{v}`" for k, v in q["sources"].items())
        if q.get("scale"):
            parts += f" (times {q['scale']})"
        L.append(f"| `{q['measure_key']}` | {q['collection']} | {parts} |")
    L += ["", "## County file columns", "", "Header spelling changed four times while the column order stayed fixed. 2017 headers end in a tab, which the loader trims.", "", "| canonical column | source by period |", "|---|---|"]
    for f in m.county_fields:
        order_c = [p for p in order if p in m.county_periods]
        parts = "; ".join(f"{rng}: {describe_source(s)}" for rng, s in compress(f, order_c))
        L.append(f"| `{f.name}` | {parts} |")
    return "\n".join(L) + "\n"


def cms_terms() -> dict[str, dict]:
    terms = {}
    for key in ("dict_puf_2023", "dict_puf_2024"):
        path = RAW_DIR / "dictionaries" / f"{key}_terms.json"
        if path.exists():
            for t in json.loads(path.read_text())["terms"]:
                terms[t["short_name"]] = t
    return terms


def first_sentence(text: str | None, limit: int = 220) -> str:
    if not text:
        return ""
    # CMS text uses em dashes in a few definitions; render them as commas to keep the docs plain
    text = re.sub(r"\s*\u2014\s*", ", ", text)
    s = re.split(r"(?<=[.])\s", text.strip(), maxsplit=1)[0]
    return s if len(s) <= limit else s[: limit - 3].rsplit(" ", 1)[0] + "..."


def data_dictionary_md() -> str:
    manifest = json.loads((DBT_DIR / "target" / "manifest.json").read_text())
    catalog_path = DBT_DIR / "target" / "catalog.json"
    catalog = json.loads(catalog_path.read_text())["nodes"] if catalog_path.exists() else {}
    mapping = load_mapping()
    field_desc = {f.name: f.description + (f" Unit: {f.unit}." if f.unit else "") for f in mapping.fields}
    L = [
        "# Data dictionary",
        "",
        "Generated by `aco_scorecard/docs.py` from the dbt manifest and catalog (warehouse column types) and the schema mapping.",
        "Metric definitions are in [metric_definitions.md](metric_definitions.md); the period by period source mapping is in",
        "[schema_mapping.md](schema_mapping.md).",
        "",
        "Layers: `raw` (CSV text as published, one table per file), `staging` (one generated view per file: typed, renamed,",
        "units converted), `intermediate` (periods stacked, ACO identifier bridge, derived values), `core` (conformed",
        "dimensions and facts), `reporting` (marts with window functions), `reference` (seeds).",
        "",
    ]
    wanted = [n for n in manifest["nodes"].values() if n["resource_type"] in ("model", "seed") and n["schema"] in ("core", "reporting", "reference", "intermediate")]
    order = {"core": 0, "reporting": 1, "intermediate": 2, "reference": 3}
    for node in sorted(wanted, key=lambda n: (order[n["schema"]], n["name"])):
        cat_cols = catalog.get(node["unique_id"], {}).get("columns", {})
        L += [f"## {node['schema']}.{node['name']}", "", (node.get("description") or "").strip() or "(no description)", ""]
        if not cat_cols:
            continue
        L += ["| column | type | description |", "|---|---|---|"]
        doc_cols = {k.lower(): v for k, v in node.get("columns", {}).items()}
        for name, info in sorted(cat_cols.items(), key=lambda kv: kv[1]["index"]):
            lname = name.lower()
            desc = (doc_cols.get(lname, {}).get("description") or "").strip() or DERIVED.get(lname) or field_desc.get(lname, "")
            desc = " ".join(desc.split())
            L.append(f"| `{lname}` | {info['type'].lower()} | {desc} |")
        L.append("")
    terms = cms_terms()
    if terms:
        L += [
            "## CMS source column definitions",
            "",
            "First sentence of the CMS definition for each source column the pipeline reads, from the PY 2024 (or PY 2023) data",
            "dictionary on data.cms.gov. Columns used only in earlier years are defined in the PY 2013 to 2020, 2021 and 2022",
            "dictionaries listed in `config/sources.yml`.",
            "",
            "| source column | CMS name | CMS definition (first sentence) |",
            "|---|---|---|",
        ]
        used = set()
        for p in mapping.period_ids:
            used |= mapping.required_columns(p)
        for col in sorted(used, key=str.lower):
            t = terms.get(TERM_ALIASES.get(col, col) or "")
            if not t:
                continue
            L.append(f"| `{col}` | {t['full_name']} | {first_sentence(t['definition']).replace('|', '/')} |")
    return "\n".join(L) + "\n"


def main() -> int:
    DOCS_DIR.mkdir(exist_ok=True)
    (DOCS_DIR / "schema_mapping.md").write_text(schema_mapping_md(), encoding="utf-8")
    (DOCS_DIR / "data_dictionary.md").write_text(data_dictionary_md(), encoding="utf-8")
    print("wrote docs/schema_mapping.md and docs/data_dictionary.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
