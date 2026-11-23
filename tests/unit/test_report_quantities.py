"""Requirement 5 - material quantity extraction and charts (Chapter 7)."""
import os

import pytest

from osdagbridge.core.boq.boq_generator import calculate_material_quantities
from osdagbridge.core.reports.chap7 import ch7_quantities
from osdagbridge.core.reports.charts import quantity_chart
from osdagbridge.core.reports.report_data import material_quantity_groups
from report_test_utils import load_demo_case


@pytest.fixture(scope="module")
def case_quantities():
    case = load_demo_case()
    return case, calculate_material_quantities(case["input_dict"], case["output_dict"])


def test_numeric_values_match_printed_table_strings(case_quantities):
    _, q = case_quantities
    num = q["boq_numeric"]
    assert float(q["steel_girders_wt_total"]) == pytest.approx(num["steel_girders_wt_total_t"], abs=0.006)
    assert float(q["concrete_deck_vol_total"]) == pytest.approx(num["concrete_deck_vol_total_m3"], abs=0.006)
    assert float(q["rebar_deck_wt_total"]) == pytest.approx(num["rebar_deck_wt_total_t"], abs=0.006)
    for part in ("top", "bot", "diag"):
        assert float(q[f"bracing_{part}_wt_total"]) == pytest.approx(num[f"bracing_{part}_wt_total_t"], abs=0.006)


def test_crash_barrier_volume_uses_area_in_m2(case_quantities):
    case, q = case_quantities
    area = float(case["input_dict"]["typical_section.crash_barrier.area"])     # GUI: "Area (m²)"
    span = float(case["input_dict"]["geometry.span"])
    assert q["boq_numeric"]["crash_barrier_vol_total_m3"] == pytest.approx(2 * area * span)
    # consistency with the barrier load used in the analysis (area x 25 kN/m³)
    assert area * 25.0 == pytest.approx(float(case["input_dict"]["typical_section.crash_barrier.load"]), rel=0.01)


def test_existing_string_outputs_are_unchanged_in_form(case_quantities):
    _, q = case_quantities
    for key in ("steel_girders_qty", "concrete_deck_qty", "bracing_diag_qty"):
        assert isinstance(q[key], str)


def test_groups_units_and_categories(case_quantities):
    _, q = case_quantities
    steel, concrete, rebar = material_quantity_groups(q)
    assert steel.unit == "MT" and concrete.unit == "m³" and rebar.unit == "MT"
    assert steel.labels == ["Steel plate girders", "Cross bracing", "End diaphragms"]
    num = q["boq_numeric"]
    assert steel.values[0] == pytest.approx(num["steel_girders_wt_total_t"])
    assert steel.values[1] == pytest.approx(num["bracing_top_wt_total_t"] + num["bracing_bot_wt_total_t"]
                                            + num["bracing_diag_wt_total_t"])
    # cross-bracing type end diaphragms: member lengths unknown -> not invented
    assert steel.values[2] is None and "tonnage not available" in steel.notes[0]
    assert concrete.values[0] == pytest.approx(num["concrete_deck_vol_total_m3"])
    assert rebar.notes and "120 kg" in rebar.notes[0]


def test_missing_quantities_stay_missing():
    q = calculate_material_quantities({}, {})
    steel, concrete, rebar = material_quantity_groups(q)
    assert steel.values == [None, None, None]
    assert concrete.values == [None, None] and rebar.values == [None]


def test_rolled_beam_end_diaphragm_tonnage_from_section_data():
    inputs = {
        "geometry.span": 20, "typical_section.no_of_girders": 3,
        "member_properties.end_diaphragm_details.type.G1G2.E1M1": "Rolled Beam",
        "member_properties.end_diaphragm_details.type.G1G2.E1M2": "Rolled Beam",
        "member_properties.end_diaphragm_details.type.G2G3.E2M1": "Rolled Beam",
        "member_properties.end_diaphragm_details.type.G2G3.E2M2": "Rolled Beam",
    }
    p = "transverse_member_design.ed.section_properties.end_diaphragm"
    outputs = {f"{p}.G1G2.L": 2.5, f"{p}.G1G2.M": 40.0, f"{p}.G2G3.L": 2.5, f"{p}.G2G3.M": 40.0}
    q = calculate_material_quantities(inputs, outputs)
    # 4 members x 40 kg/m x 2.5 m = 400 kg = 0.4 t
    assert q["boq_numeric"]["end_diaphragm_wt_total_t"] == pytest.approx(0.4)
    assert q["end_diaphragm_qty"] == "4"


def test_quantity_chart_png_and_unavailable_values(tmp_path):
    p = quantity_chart(["A", "B"], [1.5, None], "MT", "Steel", str(tmp_path / "q.png"))
    assert os.path.getsize(p) > 3000
    p2 = quantity_chart(["A"], [None], "MT", "Steel", str(tmp_path / "q2.png"))
    assert os.path.exists(p2)


def test_chapter7_table_and_charts(case_quantities, tmp_path):
    case, q = case_quantities
    inputs = dict(case["input_dict"]); inputs.update(q)
    groups = material_quantity_groups(q)
    paths = [str(tmp_path / f"q{i}.png").replace("\\", "/") for i in range(3)]
    tex = ch7_quantities(inputs, chart_paths=paths, chart_groups=groups)
    assert "End Diaphragms" in tex and "Bill of Materials" in tex
    assert tex.count(r"\includegraphics") == 3
    assert "Structural Steel Tonnage (MT)" in tex
    assert ch7_quantities(inputs).count(r"\includegraphics") == 0     # old call still works
