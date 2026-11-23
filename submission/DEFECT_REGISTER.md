# Defect Register: final QA round

Scope: the report generator built in the first round, re-audited on 2026-11-21 against the source code, the real demonstration design data and a page-by-page inspection of the generated PDF.

**Severity:**
- **High**: wrong engineering information in the report.
- **Medium**: misleading or incomplete presentation.
- **Low**: layout or wording.

**Type:**
- **Fixed**: corrected in the report or BOQ code, with a regression test.
- **Disclosed**: an upstream issue in the analysis or design modules. Those modules were not changed; the report now states the issue and marks it as requiring engineering verification.

All tests named below are in `tests/unit/test_report_regressions.py` unless another file is given.

## Defects in the report and BOQ code (fixed)

### D-01 (Bug A) — High — Fixed: girder dimensions printed in metres as mm
- **Location:** `reports/chap2.py`, `_girder_tables._dim_row`.
- **Root cause:** `design()` converts the girder `section_input` dimensions from mm to metres in place (`PlateGirderBridge._convert_girder_dims_mm_to_m`). The report printed them with `_render_value(...,' mm')` without converting, giving "1.67 mm", "0.022 mm".
- **Correction:** new helpers in `report_data`:
  - `girder_dimension_source_unit()` returns "m" once design results exist, "mm" for GUI values;
  - `length_in_mm()` converts explicitly from a stated unit and never converts twice;
  - `format_mm()`.
  
  Table 2.7 now shows 1670 mm / 10 mm / 510 mm, 22 mm, matching Table 5.1 and `design_results.D_mm`. Other unit-labelled values in Chapters 2–7 were checked and are correct.
- **Tests:** `test_length_in_mm*`, `test_format_mm*`, `test_dimension_unit_follows_pipeline_stage`, `test_girder_dimension_table_shows_millimetres` (m and mm inputs), `test_chapter2_real_case_dimensions_match_designed_section`.

### D-02 (Bug B) — High — Fixed: raw "UnboundLocalError" printed in Table 3.3
- **Location:** `report_data.braking_info`, `chap3.vehicle_live_load_table`.
- **Root cause:** `IRC6_2017.cl_211_2_braking_force` raises `UnboundLocalError` for 1–2 lanes, because `braking_force_2` is only assigned for lanes > 2. The report wrote the exception name into the PDF.
- **Correction:** the exception (with traceback) goes to the diagnostic log. The report says "Not available — the design pipeline's IRC 6 Cl. 211.2 braking-force function returns no value for 2 design lanes (known upstream defect D-18)." (wording updated 2026-11-23) The engineering function is **not** patched: treating the missing term as 0 would drop the "10 % of succeeding trains" part of Cl. 211.2 and could understate the force. A missing lane count gets its own message.
- **Tests:** `test_braking_failure_reported_without_python_details`, `test_braking_success_path_unchanged`, `test_braking_missing_lanes`, `test_real_case_report_has_no_raw_exception`.

### D-03 (Bug C) — High — Fixed: Executive Summary hardcoded "… design pass" for all components
- **Location:** `reports/executive_summary.py`.
- **Root cause:** the Key Design Outcomes were literal text. In addition:
  - the overall status used girder checks only;
  - every girder column repeated the bridge-wide maximum UR;
  - spacing and thickness had no units;
  - the note said "UR < 1.0 passes" (should be ≤).
- **Correction:** `report_data.component_status` / `design_status` derive per-component and overall statuses from the same data as Section 5.5:
  - FAIL if any valid check has UR > 1.0, or the design module flags FAIL;
  - PASS only if every check has valid data and UR ≤ 1.0;
  - INCOMPLETE or NOT AVAILABLE otherwise;
  - overall: FAIL, PASS, or NOT FULLY VERIFIED.
  
  The demo design now correctly reports **FAIL** (girder fatigue UR 1.58, intermediate stiffener leg UR 1.48). Per-girder governing checks come from `per_girder_governing`.
- **Tests:** `test_component_status` (7 cases incl. UR = 1.0, missing, zero), `test_module_fail_flag_wins_over_ratio`, `test_overall_status` (4 cases), `test_real_case_executive_summary_is_derived_not_hardcoded`, `test_executive_summary_per_girder_values_differ`, `test_executive_summary_all_pass_case`.

### D-07 — Medium — Fixed: BOQ girder tonnage used stale section properties
- **Location:** `core/boq/boq_generator.py`.
- **Root cause:** the BOQ used `section_properties.area/mass` (0.03492 m², 274 kg/m). These are not updated after optimisation. The designed section is 1670×510×22×510×22, tw 10, so A = 38 700 mm².
- **Correction:** `_designed_girder_area_m2` computes A from the final section dimensions, which equals `design_results.A_steel_mm2` exactly. The stored properties are only a fallback. Girder steel: 32.89 → **36.46 MT**.
- **Tests:** `test_boq_girder_tonnage_uses_designed_section`, `test_boq_girder_falls_back_to_stored_properties_without_dimensions`.

### D-08 — High — Fixed: Section 5.4 "End Diaphragm" tables reprinted cross-bracing data
- **Location:** `chap5.py`.
- **Root cause:** the three end-diaphragm tables were filled with the `cb_*_content` variables, i.e. cross-bracing sections and forces under end-diaphragm captions.
- **Correction:** `end_diaphragm_tables()` builds a member/section table from the end-diaphragm input, plus a capacity summary from `end_diaphragm_design_results`. Without results it shows a row explaining why. The Table 5.28 end-diaphragm rows are fixed the same way.
- **Test:** `test_section_5_4_uses_end_diaphragm_data_only`.

### D-09 — Medium — Fixed: un-grouped table layout overrides leaked into later chapters
- **Location:** `chap2.py`, `chap5.py`.
- **Root cause:** `\setlength\LTleft`, `\LTright` and `\tabcolsep{4pt}` were set without a group. Every later table became left-aligned with 4 pt padding, against `styles.TABLE`.
- **Correction:** the overrides are removed; all specs are width-fitted.
- **Test:** `test_no_global_longtable_alignment_overrides_in_chapters`.

### D-10 — Low — Fixed: title page and Table of Contents both "Page 1"; total off by one
- **Root cause:** the `titlepage` environment restarts the page counter, but the title page footer still printed a number.
- **Correction:** the title page is unnumbered. Since 2026-11-22 numbering continues at 2 after it, so "Page X of Y" equals the PDF page (2…75 of 75).
- **Test:** `test_title_page_has_no_page_number_and_no_global_heading_needspace`.

### D-11 — Low — Fixed: orphaned captions and headings
- **Cases:**
  - the Table 1 title was left at a page bottom;
  - the headings of Sections 5.1 and 5.5 were left at page bottoms;
  - a section heading appeared with the following table's *continued* heading placed above it (caused by a trial global `\needspace` before headings).
- **Correction:** Table 1 is wrapped in a minipage. `\clearpage` is used before 5.1 and 5.5, whose first table rows can't be split. No `\needspace` before any longtable (documented in the code).
- **Tests:** integration tests `test_no_heading_left_at_page_bottom` and `test_continued_headings_never_precede_first_heading`.

### D-12 — Low — Fixed: stray table rule at the top of the next page
- **Root cause:** a table ended exactly at a page break (after Table 2.11), and longtable repeated its final `\hline` on the next page.
- **Correction:** the closing rule now lives in `\endlastfoot`, and every row ending is `\\*` before its rule.
- **Tests:** `test_closing_rule_moves_to_last_foot_and_rows_keep_their_rule`; integration test `test_no_stray_table_rule_at_page_top`.

### D-13 — Medium — Fixed: blank value cells
- **Cases:**
  - "No. of Traffic Lanes" was blank;
  - Vz and Pz were blank, although chap3 already computed them (IRC 6 Table 12) and never used them;
  - the wind forces and the hardcoded `'' + ' kN'` seismic forces were blank;
  - Table 4.2 had three hardcoded empty rows.
- **Correction:**
  - lanes come from the analyser's rule, `design_lanes()`;
  - Vz and Pz are shown;
  - unavailable forces say "Not available";
  - Table 4.2 shows the governing (max |R|) reaction per support from the Table 4.1 data.
- **Tests:** `test_design_lanes_shown_instead_of_blank`, `test_chapter3_missing_wind_and_seismic_forces_are_labelled`, `test_reaction_table_uses_largest_magnitude`.

### D-14 — Medium — Fixed: Table 5.7 showed required stiffener values without saying so
- **Root cause:** `store_design_results` stores *required* values in Optimized mode and *provided* values in Custom mode. The label said only "Thickness", so the required 21.1 mm could be read as the provided plate (10 mm).
- **Correction:** labels follow the design mode ("Required …" / "Provided …"), and a missing spacing says "Not available".
- **Test:** `test_stiffener_summary_says_required_or_provided`.

### D-15 — Low — Fixed: Table 5.16 impact factor labelled with the wrong clause
- **Root cause:** the value 1.100 belongs to the governing Class 70R(W) vehicle, which falls under Cl. 208.3, but the label said "Cl. 208.2".
- **Correction:** the label is now "Impact Factor of the Governing Vehicle (IRC 6 Cl. 208)".
- **Test:** `test_deck_impact_factor_label_does_not_claim_wrong_clause`.

### D-16 — Low — Fixed: rebar chart label truncated
- **Correction:** the category label "Deck slab reinforcement" was shortened to "Deck slab" (the chart title already says "Reinforcement Steel").
- **Verification:** visual inspection.

### D-20 — Low — Fixed: Table 4.2 governing load case depended on run order
- **Found by:** the reproducibility check (the same design case built twice printed "ACCIDENTAL 2" and "ACCIDENTAL 3").
- **Root cause:** four load cases (ACCIDENTAL 1–3 and Envelope ULS) give the same reaction; the first one in the analysis dict was printed, and that order differs between runs.
- **Correction:** ties are broken by load-case name and the cell says "(and N other load cases with the same value)". The value is unchanged (−1308.880 / 1042.068 kN).
- **Test:** `test_reaction_table_tie_is_deterministic_and_disclosed`.

## Upstream issues in the analysis and design modules (disclosed, not changed)

These require engineering verification and are disclosed in the Executive Summary "Data Consistency Notes" and next to the affected tables.

### D-04 — High — Disclosed: 4 girders in the input, 6 girders in the design results
- **Location:** `plategirderbridge._run_dcr_checks` creates `PlateGirderAnalysisResults` without passing `edge_dist`. The deck-edge grillage lines are therefore not named EB1/EB2, and are designed and reported as G1 and G6.
- **Effect:** design labels G1–G6 do not match the Chapter 2 girders.
- **Tests:** `test_consistency_notes_on_real_case`, `test_no_consistency_notes_for_consistent_data`.

### D-05 — High — Disclosed: cross-bracing spacing mismatch
- **Effect:** the input spacing is 15 m per pair (Table 2.9). The design and bracing-force modules read an unset key and apply a 3 m default, including the LTB unbraced length.
- **Test:** `test_consistency_notes_on_real_case`.

### D-06 — High — Disclosed: analysis section differs from the designed section
- **Effect:** the grillage uses the stored A = 349.2 cm² and Iz, while the IRC 22 checks use the designed section with A = 387.0 cm².
- **Test:** `test_consistency_notes_on_real_case`.

### D-17 — High — Disclosed: two deflection results that disagree
- **Effect:** Table 4.3 and Table 5.9 use the per-girder load-effect deflections (19.4 / 51.2 mm, total FAIL). The IRC 22 check uses 9.63 / 22.87 mm (PASS).
- **Test:** `test_deflection_inconsistency_note`.

### D-18 — Medium — Disclosed: braking-force function crashes for 1–2 lanes
- **Location:** `IRC6_2017.cl_211_2_braking_force`.
- **Effect:** see D-02. Not patched, because a fix requires engineering verification against IRC 6 Cl. 211.2.

### D-19 — Medium — Disclosed: vehicle checkboxes don't drive the analysis
- **Location:** analyser `vehicle_lane_coordinates`.
- **Effect:** it uses IRC 6 Table 6A (Class A / 70R) regardless of the vehicle checkboxes. Table 3.3 lists the user's selection, as required.
