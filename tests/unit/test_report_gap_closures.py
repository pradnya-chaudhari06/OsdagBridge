"""Report gaps closed without faking data (final integration round).

* end-diaphragm UR chart: framed "no results" panel keeps axes + UR = 1.0 line;
  real bars render when Osdag member results are supplied;
* Table 3.3: centrifugal force is stated as not computed (no IRC 6 function);
* Chapter 7: end-diaphragm tonnage is explained, never estimated;
* chart failures (matplotlib missing / exception) give a visible placeholder
  that cites the table holding the values, plus a logged warning;
* footer "Page X of Y" equals the PDF page number / count.
"""
import copy
import logging
import os
import sys
import types

import pytest

sys.path.insert(0, os.path.dirname(__file__))
from report_test_utils import have_pdf_tools, load_demo_case  # noqa: E402


@pytest.fixture(scope="module")
def case():
    return load_demo_case()


# ── 4A: end-diaphragm UR chart ───────────────────────────────────────────────
def test_ur_no_data_panel_keeps_axes_and_limit_line():
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    from osdagbridge.core.reports import styles
    from osdagbridge.core.reports.charts import build_ur_no_data_figure

    fig = build_ur_no_data_figure("Utilization Ratio — End Diaphragms", "Reason text.")
    ax = fig.axes[0]
    try:
        assert ax.get_ylabel() == styles.CHART["ur_axis_label"]
        lo, hi = ax.get_ylim()
        assert lo == 0 and hi > 1.0
        ref = [l for l in ax.get_lines() if list(l.get_ydata()) == [1.0, 1.0]]
        assert ref and ref[0].get_linestyle() == "--"
        assert ref[0].get_color() == styles.CHART["ref_line_color"]
        # no bars: nothing that could be read as a value
        assert not [p for p in ax.patches if isinstance(p, Rectangle) and p.get_height() > 0]
        texts = " ".join(t.get_text() for t in ax.texts)
        assert "No design results available" in texts and "Reason text." in texts
        # the message box stays inside the plot area (does not cover the axis label)
        long_fig = build_ur_no_data_figure("T", "The analysis returned no end-diaphragm member "
                                           "forces, so no end-diaphragm Demand/Capacity checks "
                                           "were performed.")
        long_fig.canvas.draw()
        r = long_fig.canvas.get_renderer()
        box = long_fig.axes[0].texts[0].get_bbox_patch().get_window_extent(r)
        area = long_fig.axes[0].get_window_extent(r)
        plt.close(long_fig)
        assert area.x0 <= box.x0 and box.x1 <= area.x1
    finally:
        plt.close(fig)


def test_end_diaphragm_bars_render_from_real_osdag_member_results(case):
    """Rendering test with REAL Osdag member-design results.

    The pipeline only produces end-diaphragm URs for cross-bracing-type end
    diaphragms, through the same Osdag tension/compression modules and the
    same result structure as the cross bracing.  The demo run has none, so this
    test feeds the demo's real Osdag cross-bracing results (same angle section
    IS 100 x 100 x 10) through the end-diaphragm path.  It proves that real
    member results become bars; it is NOT an end-diaphragm design result and
    is never presented as one.
    """
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    from osdagbridge.core.reports.charts import build_utilization_figure
    from osdagbridge.core.reports.report_data import PASS, end_diaphragm_ur_items

    od = case["output_dict"]
    ed_out = {"end_diaphragm_design_results": copy.deepcopy(od["crossbracing_design_results"]),
              "end_diaphragm_forces_dict": copy.deepcopy(od["crossbracing_forces_dict"])}
    items = end_diaphragm_ur_items(ed_out)
    valid = [i for i in items if i.ur is not None]
    assert len(valid) >= 4 and all(i.status == PASS for i in valid)
    fig = build_utilization_figure(items, "End Diaphragms (rendering test)")
    try:
        heights = sorted(round(p.get_height(), 6) for p in fig.axes[0].patches
                         if isinstance(p, Rectangle) and p.get_height() > 0)
        assert heights == sorted(round(i.ur, 6) for i in valid)
    finally:
        plt.close(fig)


def test_rolled_beam_end_diaphragm_never_gets_fabricated_bars():
    from osdagbridge.core.reports.report_data import collect_utilization
    s = collect_utilization({"member_properties.end_diaphragm_details.type.G1G2.E1M1": "Rolled Beam"}, {})
    assert s.end_diaphragms == []
    assert "does not yet perform a Demand/Capacity design check" in s.end_diaphragm_reason


# ── 4B: centrifugal force ────────────────────────────────────────────────────
def test_no_centrifugal_function_exists_in_irc6_module():
    """If someone adds an IRC 6 Cl. 212 function, Table 3.3 must be updated to use it."""
    from osdagbridge.core.utils.codes.irc6_2017 import IRC6_2017
    assert not [n for n in dir(IRC6_2017) if "centrifugal" in n.lower()]


def test_grillage_model_has_no_plan_curvature():
    """Basis of the 'straight bridge' decision: the analyser builds the grillage
    from span, width and skew only (no horizontal curve).  If a curve argument
    is ever added, the centrifugal row logic must be revisited."""
    import inspect
    from osdagbridge.core.bridge_types.plate_girder import analyser
    src = inspect.getsource(analyser)
    call = src[src.index("og.create_grillage("):]
    call = call[:call.index(")") + 1]
    for word in ("radius", "curve", "curvature"):
        assert word not in call.lower()


def test_table_3_3_centrifugal_straight_bridge_is_not_applicable(case):
    from osdagbridge.core.reports.chap3 import CENTRIFUGAL_NOT_APPLICABLE, vehicle_live_load_table
    tex = vehicle_live_load_table(case["input_dict"])
    assert "Centrifugal force (IRC 6 Cl. 212)" in tex
    assert CENTRIFUGAL_NOT_APPLICABLE.startswith("Not applicable (straight bridge)")
    assert CENTRIFUGAL_NOT_APPLICABLE in tex
    assert "kN" not in CENTRIFUGAL_NOT_APPLICABLE                  # never a value
    for bad in ("Error", "Traceback", "Exception", "raised"):
        assert bad not in tex


def test_table_3_3_centrifugal_curved_input_stays_not_available(case):
    from osdagbridge.core.reports.chap3 import CENTRIFUGAL_NOT_COMPUTED, vehicle_live_load_table
    from osdagbridge.core.reports.report_data import centrifugal_text
    curved = dict(case["input_dict"], **{"geometry.horizontal_curve_radius": 250})
    assert centrifugal_text(curved) == "Not available - not computed by the design pipeline"
    assert CENTRIFUGAL_NOT_COMPUTED in vehicle_live_load_table(curved)
    zero = dict(case["input_dict"], **{"geometry.horizontal_curve_radius": 0})
    assert centrifugal_text(zero).startswith("Not applicable (straight bridge)")


def test_table_3_3_braking_failure_is_one_plain_sentence(case):
    from osdagbridge.core.reports.chap3 import vehicle_live_load_table
    tex = vehicle_live_load_table(case["input_dict"])
    row = tex[tex.index("Braking load (IRC 6 Cl. 211.2)"):]
    row = row[:row.index(r"\\")]
    assert "Not available --- the design pipeline's IRC 6 Cl. 211.2 braking-force function " \
           "returns no value for 2 design lanes (known upstream defect D-18)." in row
    assert row.count(".") >= 1 and "UnboundLocalError" not in row and "braking_force_2" not in row


# ── 4C: end-diaphragm tonnage ────────────────────────────────────────────────
def test_end_diaphragm_tonnage_explained_not_estimated(case):
    from osdagbridge.core.boq.boq_generator import calculate_material_quantities
    from osdagbridge.core.reports.report_data import material_quantity_groups
    q = calculate_material_quantities(case["input_dict"], case["output_dict"])
    steel = material_quantity_groups(q)[0]
    assert steel.values[2] is None                       # no estimated value
    assert steel.notes == ["End-diaphragm tonnage not available (N.A. in Table 7.1): the member "
                           "lengths of the cross-bracing end-diaphragm frames are not in the "
                           "design output."]
    assert q["end_diaphragm_wt_total"] == "N.A."


@pytest.mark.parametrize("boq_note, expected_end", [
    ("No end diaphragms defined in the input.", "no end diaphragms defined in the input."),
    ("", "the BOQ module did not compute it."),
    (None, "the BOQ module did not compute it."),
])
def test_end_diaphragm_tonnage_note_other_reasons(boq_note, expected_end):
    from osdagbridge.core.reports.report_data import end_diaphragm_tonnage_note
    text = end_diaphragm_tonnage_note(boq_note)
    assert text.startswith("End-diaphragm tonnage not available (N.A. in Table 7.1): ")
    assert text.endswith(expected_end)
    assert text.replace("N.A.", "NA").count(". ") == 0            # one sentence


def test_figure_5_4_note_is_one_sentence(case):
    from osdagbridge.core.reports.report_data import collect_utilization
    reason = collect_utilization(case["input_dict"], case["output_dict"]).end_diaphragm_reason
    assert reason.endswith(".") and reason.count(". ") == 0 and "\n" not in reason


# ── 4D: chart failure visibility ─────────────────────────────────────────────
class _Payload(types.SimpleNamespace):
    pass


def _charts(case, tmp_path):
    from osdagbridge.core.boq.boq_generator import calculate_material_quantities
    from osdagbridge.core.reports.report_generator import _build_report_charts
    payload = _Payload(inputs=case["input_dict"], output_dict=case["output_dict"])
    q = calculate_material_quantities(case["input_dict"], case["output_dict"])
    return _build_report_charts(payload, q, str(tmp_path / "charts"))


def _assert_placeholders(ur, qp, qg, caplog):
    from osdagbridge.core.reports.chap5 import ur_charts_section
    from osdagbridge.core.reports.chap7 import ch7_quantities
    assert len(ur) == 4 and all(p is None for p, _, _ in ur)
    assert len(qg) == 3 and qp == [None, None, None]
    assert any(r.levelno == logging.WARNING and "could not be generated" in r.getMessage()
               for r in caplog.records)
    s5 = ur_charts_section(ur)
    assert s5.count(r"Chart could not be generated; values are in Table~\ref{tab:design-check-summary}") == 4
    assert r"\includegraphics" not in s5
    s7 = ch7_quantities({}, chart_paths=qp, chart_groups=qg)
    assert s7.count(r"Chart could not be generated; values are in Table~\ref{tab:bill-of-materials}") == 3
    assert r"\label{tab:bill-of-materials}" in s7


def test_chart_exception_gives_visible_placeholder_and_warning(case, tmp_path, monkeypatch, caplog):
    import osdagbridge.core.reports.charts as charts

    def boom(*a, **k):
        raise RuntimeError("simulated matplotlib failure")
    monkeypatch.setattr(charts, "utilization_chart", boom)
    monkeypatch.setattr(charts, "quantity_chart", boom)
    with caplog.at_level(logging.WARNING):
        ur, qp, qg = _charts(case, tmp_path)
    _assert_placeholders(ur, qp, qg, caplog)


def test_matplotlib_missing_gives_visible_placeholder_and_warning(case, tmp_path, monkeypatch, caplog):
    monkeypatch.setitem(sys.modules, "osdagbridge.core.reports.charts", None)   # import -> ImportError
    with caplog.at_level(logging.WARNING):
        ur, qp, qg = _charts(case, tmp_path)
    _assert_placeholders(ur, qp, qg, caplog)
    assert any("cannot be generated" in r.getMessage() for r in caplog.records)


@pytest.mark.skipif(not have_pdf_tools(), reason="pdflatex or pymupdf not available")
def test_pdf_shows_chart_placeholders_with_real_table_numbers(case, tmp_path, monkeypatch):
    """End to end: with chart generation failing, the PDF says where the values are."""
    import pymupdf
    import osdagbridge.core.reports.charts as charts
    from osdagbridge.core.reports.report_generator import (
        ReportMetadata, ReportOptions, ReportRequest, build_report_payload, generate_report,
    )

    def boom(*a, **k):
        raise RuntimeError("simulated matplotlib failure")
    monkeypatch.setattr(charts, "utilization_chart", boom)
    monkeypatch.setattr(charts, "quantity_chart", boom)
    meta = ReportMetadata(project_name="Chart failure test", project_location="", designer="QA",
                          client="", company="", group_name="", subtitle="Rev 0",
                          job_number="CF-1", additional_comments="", logo_path=None,
                          report_date="2026-01-01")
    req = ReportRequest(metadata=meta,
                        options=ReportOptions(sections=case["sections"], include_figures=True,
                                              include_toc=True, include_pdf=True),
                        output_dir=str(tmp_path), file_stem="cf")
    payload = build_report_payload(req, dict(case["input_dict"]), dict(case["output_dict"]))
    res = generate_report(payload, req)
    text = " ".join(" ".join(p.get_text().split()) for p in pymupdf.open(res.pdf_path))
    assert text.count("Chart could not be generated; values are in Table 5.28.") == 4
    assert text.count("Chart could not be generated; values are in Table 7.1.") == 3
    assert "Table 5.28: Overall Design Check Summary" in text
    assert "Table 7.1: Bill of Materials" in text
