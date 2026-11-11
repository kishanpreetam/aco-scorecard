"""The schema mapping is internally consistent and the generated staging models are in sync."""

import pytest

from aco_scorecard import gen_staging
from aco_scorecard.mapping import expand_range, load_mapping


def test_ranges_follow_period_order_including_2019a():
    m = load_mapping()
    assert expand_range("2019..2020", m.period_ids) == ["2019", "2019A", "2020"]
    assert expand_range("2024", m.period_ids) == ["2024"]
    with pytest.raises(ValueError):
        expand_range("2020..2019", m.period_ids)
    with pytest.raises(ValueError):
        expand_range("1999", m.period_ids)


def test_every_period_has_identifier_name_and_track_rule():
    m = load_mapping()
    assert len(m.period_ids) == 13
    fields = {f.name: f for f in m.fields}
    for pid in m.period_ids:
        assert fields["aco_source_id"].sources.get(pid) is not None, pid
        assert fields["aco_name"].sources.get(pid) is not None, pid
        assert fields["total_benchmark_expenditures"].sources.get(pid) is not None, pid
        assert pid in m.tracks, pid


def test_unit_conversions_are_only_percent_or_fraction_scales():
    m = load_mapping()
    for f in m.fields:
        for pid, src in f.sources.items():
            if src is not None and src.scale is not None:
                assert src.scale in (0.01, 100), (f.name, pid, src.scale)
                if f.unit == "fraction":
                    assert src.scale == 0.01, (f.name, pid)
                if f.unit == "points_0_100":
                    assert src.scale == 100, (f.name, pid)


def test_quality_measures_start_in_2016():
    m = load_mapping()
    for pid in ("2013", "2014", "2015"):
        assert m.quality[pid] == []
    for pid in m.period_ids[3:]:
        assert len(m.quality[pid]) >= 20, pid


def test_generated_staging_models_match_the_mapping():
    assert gen_staging.main(["--check"]) == 0
