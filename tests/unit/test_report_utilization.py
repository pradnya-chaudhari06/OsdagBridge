"""Requirement 4 - Utilization Ratio extraction and charts (Section 5.5).

`compute_ur` / chart tests use synthetic numbers; the extraction tests run on
real design results captured from a GUI design run (tests/fixtures).
"""
import os

import pytest

from osdagbridge.core.reports import styles
from osdagbridge.core.reports.charts import build_utilization_figure, utilization_chart
from osdagbridge.core.reports.report_data import (
    FAIL, NO_DATA, PASS, URItem, collect_utilization, compute_ur, cross_bracing_ur_items,
    deck_ur_items, end_diaphragm_ur_items, girder_ur_items,
)
from report_test_utils import load_demo_case


# ---------------------------------------------------------------- compute_ur
@pytest.mark.parametrize("demand,capacity,expected,status", [
    (50, 100, 0.5, PASS),
    (100, 100, 1.0, PASS),          # exactly at the limit passes
    (150, 100, 1.5, FAIL),
    (-80, 100, 0.8, PASS),          # sign of the demand does not matter
])
def test_ur_from_demand_and_capacity(demand, capacity, expected, status):
    ur, st, _ = compute_ur(demand, capacity)
    assert ur == pytest.approx(expected) and st == status


@pytest.mark.parametrize("demand,capacity,reason", [
    (10, 0, "zero"),
    (10, None, "capacity"),
    (None, 10, "demand"),
    ("abc", 10, "demand"),
    (float("nan"), 10, "demand"),
    (None, None, "demand and capacity"),
])
def test_invalid_data_is_no_data_never_pass(demand, capacity, reason):
    ur, st, why = compute_ur(demand, capacity)
    assert ur is None and st == NO_DATA and reason in why


def test_reported_ratio_is_authoritative():
    ur, st, _ = compute_ur(10, 100, reported=1.2)
    assert ur == 1.2 and st == FAIL


# ---------------------------------------------------------------- real data
@pytest.fixture(scope="module")
def case():
    return load_demo_case()


def test_girder_items_use_governing_girder_dcr(case):
    od = case["output_dict"]
    items = girder_ur_items(od)
    assert items, "girder checks expected in the design results"
    per_girder = od["design_results"]["per_girder"]
    for it in items:
        dcrs = [c["dcr"] for g, gd in per_girder.items() for c in gd["checks"]
                if c["name"] == it.check and c.get("dcr") is not None]
        assert it.ur == pytest.approx(max(dcrs))
        assert it.member in per_girder
    # failures present in the real design are reported as failures
    assert any(i.status == FAIL for i in items)


def test_deck_items_are_demand_over_capacity(case):
    items = {i.check: i for i in deck_ur_items(case["output_dict"])}
    dr = case["output_dict"]["deck_report_values"]
    sag = items["Flexure (sagging)"]
    assert sag.ur == pytest.approx(dr["deck.report.m_uls_sag"] / dr["deck.report.mu_bot"])
    assert "Crack width" in items and "Punching shear" in items


def test_cross_bracing_items_use_osdag_efficiency(case):
    items = cross_bracing_ur_items(case["output_dict"])
    assert len(items) == 12                     # 3 pairs x (diagonal, chord) x (C, T)
    assert all(i.status in (PASS, FAIL) for i in items)
    assert max(i.ur for i in items) == pytest.approx(0.74)


def test_end_diaphragm_without_results_is_explained_not_filled(case):
    od = case["output_dict"]
    assert end_diaphragm_ur_items(od) == []
    s = collect_utilization(case["input_dict"], od)
    assert "no end-diaphragm member forces" in s.end_diaphragm_reason
    # never borrowed from cross bracing
    assert all("end diaphragm" not in i.source for i in s.cross_bracing)


def test_all_four_categories_present(case):
    keys = [k for k, _, _ in collect_utilization(case["input_dict"], case["output_dict"]).categories()]
    assert keys == ["girders", "deck", "cross_bracing", "end_diaphragms"]


def test_end_diaphragm_rolled_beam_reason():
    s = collect_utilization({"member_properties.end_diaphragm_details.type.G1G2.E1M1": "Rolled Beam"}, {})
    assert "Rolled Beam" in s.end_diaphragm_reason


# ---------------------------------------------------------------- charts
def _items():
    return [
        URItem("A", "m", "A", 5, 10, 0.5, PASS),
        URItem("B", "m", "B", 10, 10, 1.0, PASS),
        URItem("C", "m", "C", 15, 10, 1.5, FAIL),
        URItem("D", "m", "D", None, 10, None, NO_DATA, reason="demand not available"),
    ]


def test_chart_has_red_dashed_reference_line_at_one():
    import matplotlib.colors as mcolors
    fig = build_utilization_figure(_items(), "Test")
    ax = fig.axes[0]
    refs = [l for l in ax.lines if list(l.get_ydata()) == [1.0, 1.0]]
    assert refs, "UR = 1.0 reference line missing"
    line = refs[0]
    assert line.get_linestyle() == "--"
    assert mcolors.to_hex(line.get_color()).lower() == styles.CHART["ref_line_color"].lower()
    assert ax.get_ylabel().startswith("Utilization Ratio")


def test_chart_colours_pass_fail_and_no_data_differently():
    import matplotlib.colors as mcolors
    fig = build_utilization_figure(_items(), "Test")
    bars = fig.axes[0].patches[:4]
    cols = [mcolors.to_hex(b.get_facecolor()).lower() for b in bars]
    assert cols[0] == cols[1] == styles.hex_color("pass").lower()        # UR 0.5 and 1.0 pass
    assert cols[2] == styles.hex_color("fail").lower()                   # UR 1.5 fails
    assert cols[3] == styles.hex_color("no_data").lower()                # missing data
    assert bars[3].get_height() == 0                                      # never drawn as a pass bar


def test_chart_png_written(tmp_path):
    p = utilization_chart(_items(), "Test", str(tmp_path / "ur.png"))
    assert os.path.getsize(p) > 5000
    p2 = utilization_chart([], "Empty", str(tmp_path / "none.png"), no_data_message="nothing")
    assert os.path.exists(p2)


def test_section_5_5_has_four_charts_and_real_end_diaphragm_row(case, tmp_path):
    from osdagbridge.core.reports.chap5 import ch5_design_checks
    from osdagbridge.core.reports.report_generator import ReportDataBridge
    bridge = ReportDataBridge(case["output_dict"], case["input_dict"], None)
    figs = [(str(tmp_path / f"{k}.png").replace("\\", "/"), f"UR {k}", "")
            for k in ("girders", "deck", "cross_bracing", "end_diaphragms")]
    tex = ch5_design_checks([], bridge, ur_figures=figs)
    after = tex[tex.index("Overall Design Check Summary"):]
    assert after.count(r"\includegraphics") == 4
    assert "Utilization Ratio Charts" in after
    # the end-diaphragm summary no longer repeats the cross-bracing values
    assert "End Diaphragm --- Moment" not in tex
    assert "no end-diaphragm member forces" in tex
