"""Regression tests for the defects fixed in the final QA round.

Defect IDs refer to submission/DEFECT_REGISTER.md.  Synthetic dictionaries are
used to isolate each rule; the real design fixture
(tests/fixtures/demo_case_30m.json.gz) is used where real behaviour matters.
"""
import pytest

from osdagbridge.core.reports.report_data import (
    FAIL, NO_DATA, PASS, STATUS_FAIL, STATUS_INCOMPLETE, STATUS_NOT_AVAILABLE,
    STATUS_NOT_VERIFIED, STATUS_PASS, URItem, UtilizationSummary, braking_info,
    collect_utilization, component_status, consistency_notes, design_status,
    format_mm, girder_dimension_source_unit, length_in_mm, per_girder_governing,
)
from report_test_utils import load_demo_case

G = "member_properties.girder_details.section_input."


@pytest.fixture(scope="module")
def case():
    return load_demo_case()


# ===================================================================== D-01 units
@pytest.mark.parametrize("value,unit,expected", [
    (1.67, "m", 1670), (0.01, "m", 10), (0.51, "m", 510), (0.022, "m", 22),
    (1670, "mm", 1670), (22.0, "mm", 22), ("0.51", "m", 510),
])
def test_length_in_mm(value, unit, expected):
    assert length_in_mm(value, unit) == pytest.approx(expected)


def test_length_in_mm_never_converts_twice_and_rejects_unknown_units():
    once = length_in_mm(0.022, "m")
    assert length_in_mm(once, "mm") == once            # already mm -> unchanged
    assert length_in_mm(None, "m") is None and length_in_mm("All", "m") is None
    with pytest.raises(ValueError):
        length_in_mm(1.0, "cm")


def test_format_mm_strips_float_noise():
    assert format_mm(length_in_mm(0.022, "m")) == "22"
    assert format_mm(21.13) == "21.13" and format_mm(None) == "---"


def test_dimension_unit_follows_pipeline_stage():
    assert girder_dimension_source_unit({"design_results": {"x": 1}}) == "m"
    assert girder_dimension_source_unit({}) == "mm" and girder_dimension_source_unit(None) == "mm"


def _dims(depth, tw, bf, tf):
    d = {}
    for i in (1, 2):
        d.update({f"{G}depth.G{i}.M1": depth, f"{G}web_thickness.G{i}.M1": tw,
                  f"{G}top_flange_width.G{i}.M1": bf, f"{G}top_flange_thickness.G{i}.M1": tf,
                  f"{G}bottom_flange_width.G{i}.M1": bf, f"{G}bottom_flange_thickness.G{i}.M1": tf,
                  f"member_properties.girder_details.select_girder.G{i}": f"G{i}",
                  f"member_properties.girder_details.member_id.G{i}.M1": f"G{i}M1"})
    d["typical_section.no_of_girders"] = 2
    return d


@pytest.mark.parametrize("dims,output", [
    ((1.67, 0.01, 0.51, 0.022), {"design_results": {"per_girder": {}, "x": 1}}),   # after design: m
    ((1670, 10, 510, 22), {}),                                                     # GUI values: mm
])
def test_girder_dimension_table_shows_millimetres(dims, output):
    from osdagbridge.core.reports.chap2 import _girder_tables
    tex = _girder_tables(_dims(*dims), 2, girder_dimension_source_unit(output))
    assert "1670 mm" in tex and "10 mm" in tex and "510 mm, 22 mm" in tex
    for wrong in ("1.67 mm", "0.01 mm", "0.51 mm", "0.022 mm", "1670000", "1670.0 mm"):
        assert wrong not in tex


def test_chapter2_real_case_dimensions_match_designed_section(case):
    from osdagbridge.core.reports.chap2 import ch2_input_parameters
    from osdagbridge.core.reports.report_generator import ReportMetadata
    meta = ReportMetadata("P", "", "", "", "", "", "", "J", "", None, "2026-01-01")
    tex = ch2_input_parameters(meta, case["input_dict"], case["output_dict"])
    dr = case["output_dict"]["design_results"]
    assert f"{dr['D_mm']:g} mm" in tex                        # 1670 mm, consistent with Ch. 5
    assert f"{dr['bf_top_mm']:g} mm, {dr['tf_top_mm']:g} mm" in tex
    assert "1.67 mm" not in tex


# ===================================================================== D-02 braking
def test_braking_failure_reported_without_python_details(monkeypatch):
    from osdagbridge.core.reports import chap3
    from osdagbridge.core.utils.codes.irc6_2017 import IRC6_2017

    def boom(lanes):
        raise UnboundLocalError("cannot access local variable 'braking_force_2'")
    monkeypatch.setattr(IRC6_2017, "cl_211_2_braking_force", staticmethod(boom))
    d = {"geometry.carriageway_width": 7.5, "geometry.include_median": "No"}
    b = braking_info(d)
    assert b.force_kN is None and "returns no value for 2 design lanes" in b.unavailable_reason
    tex = chap3.vehicle_live_load_table(d)
    for leak in ("UnboundLocalError", "braking_force_2", "Traceback", "IRC6_2017.", "Error"):
        assert leak not in tex
    assert "Not available" in tex


def test_braking_success_path_unchanged(monkeypatch):
    from osdagbridge.core.utils.codes.irc6_2017 import IRC6_2017
    monkeypatch.setattr(IRC6_2017, "cl_211_2_braking_force", staticmethod(lambda n: 12.5))
    b = braking_info({"typical_section.lane_details.lane_table_count": 3})
    assert b.force_t == 12.5 and b.force_kN == pytest.approx(12.5 * 9.81) and b.unavailable_reason == ""


def test_braking_missing_lanes():
    b = braking_info({"geometry.include_median": "Yes"})
    assert b.lanes is None and b.force_kN is None
    assert b.unavailable_reason == "the number of design lanes is not available"


def test_real_case_report_has_no_raw_exception(case):
    from osdagbridge.core.reports.chap3 import ch3_loads
    tex = ch3_loads(case["input_dict"])
    assert "UnboundLocalError" not in tex and "Not available" in tex


# ===================================================================== D-03 status
def _it(ur, status=None):
    if ur is None:
        return URItem("x", "m", "x", None, None, None, NO_DATA, reason="missing")
    return URItem("x", "m", "x", ur, 1.0, ur, status or (FAIL if ur > 1.0 else PASS))


@pytest.mark.parametrize("urs,expected", [
    ([0.5, 0.9], STATUS_PASS),
    ([1.0], STATUS_PASS),                     # exactly 1.0 passes
    ([0.5, 1.01], STATUS_FAIL),
    ([0.5, None], STATUS_INCOMPLETE),         # missing data: never a pass
    ([None, None], STATUS_NOT_AVAILABLE),
    ([], STATUS_NOT_AVAILABLE),
    ([None, 1.5], STATUS_FAIL),
])
def test_component_status(urs, expected):
    assert component_status("k", "K", [_it(u) for u in urs]).status == expected


def test_module_fail_flag_wins_over_ratio():
    od = {"design_results": {"per_girder": {"G1": {"checks": [
        {"name": "Odd", "dcr": 0.9, "demand": 9, "capacity": 10, "status": "FAIL"}]}}}}
    assert per_girder_governing(od)["G1"].status == FAIL


@pytest.mark.parametrize("comp_urs,overall", [
    ({"girders": [0.5], "deck": [0.4], "cross_bracing": [0.3], "end_diaphragms": [0.2]}, STATUS_PASS),
    ({"girders": [1.2], "deck": [0.4], "cross_bracing": [0.3], "end_diaphragms": [0.2]}, STATUS_FAIL),
    ({"girders": [0.5], "deck": [0.4], "cross_bracing": [0.3], "end_diaphragms": []}, STATUS_NOT_VERIFIED),
    ({"girders": [0.5], "deck": [None], "cross_bracing": [1.3], "end_diaphragms": []}, STATUS_FAIL),
])
def test_overall_status(comp_urs, overall):
    s = UtilizationSummary(**{k: [_it(u) for u in v] for k, v in comp_urs.items()})
    assert design_status(s)[1] == overall


def test_real_case_executive_summary_is_derived_not_hardcoded(case):
    from osdagbridge.core.reports.executive_summary import executive_summary
    tex = executive_summary(case["input_dict"], case["output_dict"], {})
    for stale in ("Girder design pass", "Cross bracing design pass",
                  "End Diaphragm design pass", "Deck design pass"):
        assert stale not in tex
    comps, overall = design_status(collect_utilization(case["input_dict"], case["output_dict"]))
    assert overall == STATUS_FAIL                       # fatigue UR 1.58 > 1.0
    assert r"\textcolor{red}{\textbf{FAIL}} --- Fatigue Normal Stress (G3), UR 1.58" in tex
    status = {c.key: c.status for c in comps}
    assert status == {"girders": STATUS_FAIL, "deck": STATUS_PASS,
                      "cross_bracing": STATUS_PASS, "end_diaphragms": STATUS_NOT_AVAILABLE}
    assert "NOT AVAILABLE" in tex and "UR $\\leq 1.0$ passes" in tex
    assert "2.1 m" in tex and "250.0 mm" in tex          # units on overview values


def test_executive_summary_per_girder_values_differ(case):
    from osdagbridge.core.reports.executive_summary import executive_summary
    tex = executive_summary(case["input_dict"], case["output_dict"], {})
    row = next(l for l in tex.splitlines() if l.startswith("Utilization Ratio (max)"))
    pg = per_girder_governing(case["output_dict"])
    for g in ("G1", "G2", "G3", "G4"):
        assert f"{pg[g].ur:.2f}" in row
    assert "1.54" in row and "1.58" in row               # not one global value repeated


def test_executive_summary_all_pass_case():
    from osdagbridge.core.reports.executive_summary import executive_summary
    chk = lambda n, d: {"name": n, "dcr": d, "demand": d, "capacity": 1.0, "status": "PASS"}
    od = {"design_results": {"per_girder": {"G1": {"checks": [chk("Flexure", 0.6)]}}},
          "deck_report_values": {}, "crossbracing_design_results": {}}
    tex = executive_summary({"member_properties.girder_details.select_girder.G1": "G1",
                             "member_properties.girder_details.member_id.G1.M1": "G1M1"}, od, {})
    # deck / bracing / end diaphragm without data -> never an overall pass
    assert "NOT FULLY VERIFIED" in tex and r"\textbf{PASS}" in tex


# ===================================================================== D-04..06 consistency
def test_consistency_notes_on_real_case(case):
    notes = consistency_notes(case["input_dict"], case["output_dict"])
    assert set(notes) == {"girder_count", "cb_spacing", "section_properties", "deflection"}
    assert "6 longitudinal members" in notes["girder_count"] and "4 girders" in notes["girder_count"]
    assert "15 m" in notes["cb_spacing"] and "used 3 m" in notes["cb_spacing"]
    assert "349.2 cm2" in notes["section_properties"] and "387.0 cm2" in notes["section_properties"]


def test_no_consistency_notes_for_consistent_data():
    od = {"design_results": {"per_girder": {"G1": {}, "G2": {}}, "cross_bracing_spacing_m": 5.0,
                             "A_steel_mm2": 20000.0}}
    inp = {"typical_section.no_of_girders": 2,
           "member_properties.cross_bracing_details.spacing.G1G2.B1M1": 5.0,
           "member_properties.girder_details.section_properties.area.G1.M1": 0.02}
    assert consistency_notes(inp, od) == {}


# ===================================================================== D-07 BOQ girder area
def test_boq_girder_tonnage_uses_designed_section(case):
    from osdagbridge.core.boq.boq_generator import calculate_material_quantities
    q = calculate_material_quantities(case["input_dict"], case["output_dict"])
    dr = case["output_dict"]["design_results"]
    span = float(case["input_dict"]["geometry.span"])
    n = int(case["input_dict"]["typical_section.no_of_girders"])
    expected_t = n * dr["A_steel_mm2"] / 1e6 * span * 7.85
    assert q["boq_numeric"]["steel_girders_wt_total_t"] == pytest.approx(expected_t)
    assert "0.03870" in q["steel_girders_vol_formula"]


def test_boq_girder_falls_back_to_stored_properties_without_dimensions():
    from osdagbridge.core.boq.boq_generator import calculate_material_quantities
    inp = {"geometry.span": 10, "typical_section.no_of_girders": 2,
           "member_properties.girder_details.section_properties.area": 0.02,
           "member_properties.girder_details.section_properties.mass": 157.0}
    q = calculate_material_quantities(inp, {})
    assert q["boq_numeric"]["steel_girders_wt_total_t"] == pytest.approx(2 * 157.0 * 10 / 1000)


# ===================================================================== D-08 end diaphragm 5.4
def test_section_5_4_uses_end_diaphragm_data_only(case):
    from osdagbridge.core.reports.chap5 import end_diaphragm_tables
    from osdagbridge.core.reports.report_generator import ReportDataBridge
    tex = end_diaphragm_tables(ReportDataBridge(case["output_dict"], case["input_dict"], None))
    assert "IS 100 x 100 x 10" in tex                      # end-diaphragm section from input
    assert "40 x 40 x 3" not in tex                        # cross-bracing section not reused
    assert "no end-diaphragm member forces" in tex


def test_table_5_28_end_diaphragm_message_has_strut(case):
    """The multi-line message cell ends with \\strut (full last-line depth)."""
    from osdagbridge.core.reports.chap5 import ch5_design_checks
    from osdagbridge.core.reports.report_generator import ReportDataBridge
    tex = ch5_design_checks([], ReportDataBridge(case["output_dict"], case["input_dict"], None))
    i = tex.index(r"\parbox[t]{9.2cm}{\centering\small The analysis returned no end-diaphragm")
    assert r"performed.\strut}" in tex[i:i + 400]


# ===================================================================== D-09 style leak
def test_no_global_longtable_alignment_overrides_in_chapters():
    import inspect
    from osdagbridge.core.reports import chap2, chap5
    for mod in (chap2, chap5):
        src = inspect.getsource(mod)
        assert "\\setlength\\LTleft" not in src and "\\setlength{\\tabcolsep}{4pt}" not in src


# ===================================================================== visual-audit fixes
def test_closing_rule_moves_to_last_foot_and_rows_keep_their_rule():
    from osdagbridge.core.reports.latex_tables import build_longtable
    tex = build_longtable(r"|l|l|", ["A", "B"], [["a", "b"], ["c", "d"]], caption="T")
    foot = tex[tex.index(r"\endfoot"):tex.index(r"\endlastfoot")]
    assert r"\hline" in foot                                  # closing rule in last foot
    body = tex[tex.index(r"\endlastfoot"):]
    assert r"\hline" in body.split("c & d")[0]                # rule after first row kept
    assert not body.rstrip().rstrip("%").rstrip().endswith(r"\hline\end{longtable}")
    assert r"a & b \\*[6pt]" in tex                         # no break before a row's rule


def test_design_lanes_shown_instead_of_blank():
    from osdagbridge.core.reports.chap2 import _lanes_text
    assert _lanes_text({"geometry.carriageway_width": 7.5, "geometry.include_median": "No"}).startswith("2 ")
    assert "Not available" in _lanes_text({"geometry.include_median": "Yes"})


def test_chapter3_missing_wind_and_seismic_forces_are_labelled(case):
    from osdagbridge.core.reports.chap3 import ch3_loads
    tex = ch3_loads(case["input_dict"])
    seismic = tex[tex.index("Horizontal Seismic Force (longitudinal)"):][:120]
    assert "Not available" in seismic and " kN \\\\" not in seismic
    assert "Vz} & 37.07 m/s" in tex                             # IRC 6 Table 12 value now shown


def test_reaction_table_uses_largest_magnitude():
    from osdagbridge.core.reports.chap4 import _reaction_rows
    rows = _reaction_rows({"LC1": {"left_kN": 181.6, "right_kN": 10.0},
                           "LC2": {"left_kN": -1308.9, "right_kN": 1042.1}})
    assert "LC2 & -1308.900" in rows and "LC2 & 1042.100" in rows
    assert "Not available" in _reaction_rows({})


def test_reaction_table_tie_is_deterministic_and_disclosed():
    """Equal reactions in several load cases: same label whatever the dict order."""
    from osdagbridge.core.reports.chap4 import _reaction_rows
    a = {"ACC_2": {"left_kN": -1308.88, "right_kN": 1042.068},
         "ACC_1": {"left_kN": -1308.88, "right_kN": 1042.068},
         "ACC_3": {"left_kN": -1308.88, "right_kN": 1042.068},
         "DL": {"left_kN": -500.0, "right_kN": 400.0}}
    b = dict(reversed(list(a.items())))
    assert _reaction_rows(a) == _reaction_rows(b)
    rows = _reaction_rows(a)
    assert r"ACC\_\allowbreak{}1" in rows and r"\allowbreak{}2" not in rows
    assert "and 2 other load cases with the same value" in rows
    single = _reaction_rows({"LC1": {"left_kN": 1.0, "right_kN": 2.0}})
    assert "other load case" not in single


def test_stiffener_summary_says_required_or_provided(case):
    from osdagbridge.core.reports.chap5 import ch5_design_checks
    from osdagbridge.core.reports.report_generator import ReportDataBridge
    tex = ch5_design_checks([], ReportDataBridge(case["output_dict"], case["input_dict"], None))
    assert "Required Intermediate Stiffener Thickness (mm)" in tex     # Optimized mode
    custom = dict(case["input_dict"], **{"geometry.design_mode": "Customized"})
    tex2 = ch5_design_checks([], ReportDataBridge(case["output_dict"], custom, None))
    assert "Provided Intermediate Stiffener Thickness (mm)" in tex2


def test_deflection_inconsistency_note(case):
    notes = consistency_notes(case["input_dict"], case["output_dict"])
    assert "19.385 mm (live)" in notes["deflection"] and "9.631 mm" in notes["deflection"]


def test_title_page_has_no_page_number_and_no_global_heading_needspace():
    from osdagbridge.core.reports.report_generator import preamble
    pre = preamble("P", "J", "D")
    first = pre[pre.index(r"\fancypagestyle{firstpage}"):pre.index(r"\pagestyle{main}")]
    assert r"\fancyfoot[R]{}" in first
    assert r"\pretocmd{\section}{\needspace" not in pre        # caused misplaced longtable heads


def test_deck_impact_factor_label_does_not_claim_wrong_clause(case):
    """Deck impact factor 1.100 belongs to the governing 70R vehicle (Cl. 208.3), not Cl. 208.2."""
    from osdagbridge.core.reports.chap5 import ch5_design_checks
    from osdagbridge.core.reports.report_generator import ReportDataBridge
    tex = ch5_design_checks([], ReportDataBridge(case["output_dict"], case["input_dict"], None))
    assert "Impact Factor (IRC 6 Cl. 208.2)" not in tex
    assert "Impact Factor of the Governing Vehicle (IRC 6 Cl. 208)" in tex
