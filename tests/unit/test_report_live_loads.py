"""Requirement 3 - separate Vehicle and Footway live-load tables (Chapter 3).

Unit tests use synthetic selections of the real GUI keys; the vehicle loads
themselves come from the application's IRC 6 module.
"""
import pytest

from osdagbridge.core.reports.chap3 import (
    ch3_loads, footway_live_load_table, vehicle_live_load_table,
)
from osdagbridge.core.reports.report_data import (
    braking_info, footway_info, selected_vehicles,
)
from osdagbridge.core.utils.codes.irc6_2017 import IRC6_2017
from osdagbridge.core.utils.common import (
    KEY_BL_IRC_CLASS_SV, KEY_CARRIAGEWAY_WIDTH, KEY_FOOTPATH, KEY_LL_CUSTOM_VEHICLES,
    KEY_LL_ECCENTRICITY, KEY_LL_FOOTPATH_PRESSURE_MODE, KEY_LL_FOOTPATH_PRESSURE_VALUE,
    KEY_LL_IRC_70R_BOGIE, KEY_LL_IRC_70R_TRACKED, KEY_LL_IRC_70R_WHEELED,
    KEY_LL_IRC_AA_TRACKED, KEY_LL_IRC_AA_WHEELED, KEY_LL_IRC_CLASS_A,
    KEY_LL_IRC_CLASS_FATIGUE, KEY_LL_IRC_CLASS_SV, KEY_SPAN, KEY_TS_FOOTPATH_WIDTH,
    KEY_TS_NO_OF_FOOTPATHS, KEY_WC_LD_LANE_TABLE_COUNT,
)
from report_test_utils import load_demo_case

ALL_KEYS = [KEY_LL_IRC_CLASS_A, KEY_LL_IRC_70R_WHEELED, KEY_LL_IRC_70R_TRACKED,
            KEY_LL_IRC_70R_BOGIE, KEY_LL_IRC_AA_WHEELED, KEY_LL_IRC_AA_TRACKED,
            KEY_LL_IRC_CLASS_SV, KEY_LL_IRC_CLASS_FATIGUE]


def _inputs(selected, **extra):
    d = {k: (k in selected) for k in ALL_KEYS}
    d.update({KEY_SPAN: 30, KEY_LL_ECCENTRICITY: "1.2"})
    d.update(extra)
    return d


def test_only_selected_vehicles_are_listed_in_gui_order():
    rows = selected_vehicles(_inputs({KEY_LL_IRC_CLASS_SV, KEY_LL_IRC_CLASS_A}))
    assert [r.name for r in rows] == ["IRC Class A", "IRC Class SV"]


@pytest.mark.parametrize("combo", [
    {KEY_LL_IRC_CLASS_A},
    {KEY_LL_IRC_70R_WHEELED, KEY_LL_IRC_70R_TRACKED},
    {KEY_LL_IRC_AA_WHEELED, KEY_LL_IRC_CLASS_FATIGUE},
    set(ALL_KEYS),
])
def test_vehicle_table_contains_exactly_the_selected_classes(combo):
    tex = vehicle_live_load_table(_inputs(combo))
    names = {r.name for r in selected_vehicles(_inputs(set(ALL_KEYS)))}
    chosen = {r.name for r in selected_vehicles(_inputs(combo))}
    for n in names:
        # match the table cell ("IRC Class A &"), not a substring of "IRC Class AA"
        assert (f"{n} &" in tex) == (n in chosen), n


def test_gui_string_booleans_are_interpreted():
    d = _inputs(set())
    d[KEY_LL_IRC_CLASS_A] = "True"
    d[KEY_LL_IRC_70R_WHEELED] = "False"
    assert [r.name for r in selected_vehicles(d)] == ["IRC Class A"]


def test_empty_selection_is_reported_not_invented():
    d = _inputs(set())
    assert selected_vehicles(d) == []
    tex = vehicle_live_load_table(d)
    assert "No vehicle class selected" in tex
    assert "IRC Class A" not in tex


def test_total_loads_come_from_irc6_vehicle_definitions():
    rows = {r.name: r for r in selected_vehicles(_inputs(set(ALL_KEYS)))}
    class_a = sum(IRC6_2017.cl_204_1_ClassA_vehicle()["wheel_loads"]) / 1000.0
    assert rows["IRC Class A"].total_load_kN == pytest.approx(class_a)
    assert rows["IRC Class A"].total_load_kN == pytest.approx(55.4 * 9.81)     # 55.4 t train
    assert rows["IRC Class 70R (Wheeled)"].total_load_kN == pytest.approx(100 * 9.81)
    assert rows["IRC Class 70R (Tracked)"].total_load_kN == pytest.approx(70 * 9.81, rel=1e-3)
    assert rows["IRC Class SV"].total_load_kN == pytest.approx(
        IRC6_2017.cl_204_5_1_special_vehicle()["total_load_kN"])


def test_vehicles_without_library_definition_show_missing_value():
    rows = {r.name: r for r in selected_vehicles(_inputs({KEY_LL_IRC_AA_WHEELED}))}
    assert rows["IRC Class AA (Wheeled)"].total_load_kN is None
    assert r"\dag" in vehicle_live_load_table(_inputs({KEY_LL_IRC_AA_WHEELED}))


def test_impact_factor_uses_existing_irc6_clauses():
    rows = {r.name: r for r in selected_vehicles(_inputs({KEY_LL_IRC_CLASS_A, KEY_LL_IRC_70R_WHEELED}))}
    assert rows["IRC Class A"].impact_factor == pytest.approx(1 + IRC6_2017.cl_208_2_impact_factor(30))
    assert rows["IRC Class 70R (Wheeled)"].impact_factor == pytest.approx(
        1 + IRC6_2017.cl_208_3_impact_factor(30))


def test_braking_flags_follow_gui_keys():
    d = _inputs({KEY_LL_IRC_CLASS_SV, KEY_LL_IRC_CLASS_A}, **{KEY_BL_IRC_CLASS_SV: False})
    rows = {r.name: r for r in selected_vehicles(d)}
    assert rows["IRC Class SV"].braking_considered is False
    assert rows["IRC Class A"].braking_considered is None        # governed by IRC 6 Cl. 211.2
    assert "As per IRC 6 Cl. 211.2" in vehicle_live_load_table(d)


def test_braking_eccentricity_and_lane_source():
    b = braking_info(_inputs(set(), **{KEY_CARRIAGEWAY_WIDTH: 7.5}))
    assert b.eccentricity_m == pytest.approx(1.2)
    assert b.lanes == IRC6_2017.table_6(7.5) and "Table 6" in b.lanes_source
    b2 = braking_info(_inputs(set(), **{KEY_WC_LD_LANE_TABLE_COUNT: "3"}))
    assert b2.lanes == 3 and b2.lanes_source == "lane table"
    if b2.force_t is not None:
        assert b2.force_kN == pytest.approx(b2.force_t * 9.81)


def test_custom_vehicle_without_load_is_not_given_a_value():
    d = _inputs(set(), **{KEY_LL_CUSTOM_VEHICLES: [{"name": "Crane 40t"}, "Truck X"]})
    rows = selected_vehicles(d)
    assert [r.name for r in rows] == ["Crane 40t", "Truck X"]
    assert all(r.total_load_kN is None for r in rows)


# ---------------------------------------------------------------- footway
def test_footway_not_applicable_without_footpath():
    fw = footway_info({KEY_FOOTPATH: "None"})
    assert not fw.applicable
    assert "Not applicable" in footway_live_load_table({KEY_FOOTPATH: "None"})


def test_footway_irc6_default_pressure():
    d = {KEY_FOOTPATH: "Both Sides", KEY_TS_NO_OF_FOOTPATHS: 2, KEY_TS_FOOTPATH_WIDTH: 1.5,
         KEY_LL_FOOTPATH_PRESSURE_MODE: "As per IRC 6", KEY_LL_FOOTPATH_PRESSURE_VALUE: ""}
    fw = footway_info(d)
    assert fw.applicable and fw.n_footpaths == 2 and fw.width_m == 1.5
    assert fw.pressure_kN_m2 == pytest.approx(IRC6_2017.cl_206_1_footway_load())
    tex = footway_live_load_table(d)
    assert r"kN/m\textsuperscript{2}" in tex and "IRC 6 Cl. 206.1" in tex


def test_footway_custom_and_missing_pressure():
    base = {KEY_FOOTPATH: "Single Side", KEY_LL_FOOTPATH_PRESSURE_MODE: "Custom"}
    assert footway_info({**base, KEY_LL_FOOTPATH_PRESSURE_VALUE: "4.2"}).pressure_kN_m2 == 4.2
    missing = footway_info({**base, KEY_LL_FOOTPATH_PRESSURE_VALUE: ""})
    assert missing.pressure_kN_m2 is None


def test_chapter3_has_two_separate_tables_and_no_merged_table():
    tex = ch3_loads(load_demo_case()["input_dict"])
    assert "Vehicle Live Load (LL)" in tex and "Footway Live Load (FPLL)" in tex
    assert tex.index("Vehicle Live Load") < tex.index("Footway Live Load")
    assert "Live Loads (LL)" not in tex                     # old merged table removed
    assert tex.count(r"\begin{longtable}") >= 8
