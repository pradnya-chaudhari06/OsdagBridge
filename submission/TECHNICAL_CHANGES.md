# Technical Changes: OsdagBridge LaTeX Report Generator

Branch `feature/report-generator-enhancements`, based on `dev` @ `d74f56dd7f22925fb8148cabf5740ed8d1e39ff3`. All changes are uncommitted.

This document has two parts. **Part A** (§1–§18) covers the original refactoring for requirements R1–R6, updated where the final QA round changed it. **Part B** (§19) covers the final QA round: bugs A–C, the defects found in the audit, and the disclosure of upstream issues.

## 1. Project overview
OsdagBridge designs short-span steel plate-girder bridges. After a design run, **Generate Report** turns the design `input_dict` and `output_dict` into a PDF. The PDF is assembled as LaTeX from Python string templates (one module per chapter) and compiled with `pdflatex`. This work refactors that report subsystem. No structural calculation was changed.

## 2. Original problems (verified on Report_Before.pdf)
1. Multi-page tables repeated their column headings on only 2 of about 51 tables (see e.g. Table 5.6 on PDF p. 31 and Table 5.29 on p. 46).
2. **Footer overlap**: on PDF p. 31 ("Page 30 of 58") the **G4** label of Table 5.7 is printed in the footer. Reason: longtable broke the page inside a `\multirow{6}` group, so the label was centred over rows that continued on the next page. In addition, 46 tables were wider than the text block, there were 139 LaTeX errors (longtable `\caption` without `\\`, and `≤`), and the footer note was pulled into the text area with `\vspace{-20pt}`.
3. Chapter 3 had one merged "Live Loads (LL)" table: a comma-separated vehicle list, combined impact factors, braking and footpath load.
4. No utilization charts.
5. No material-quantity charts. The BOQ produced strings only.
6. Formatting values were scattered over the preamble and every chapter.

## 3. Summary of changes
| Area | Change |
|---|---|
| Styles | New `reports/styles.py`, the single source of truth consumed by the preamble, the table builder and the charts |
| Tables | New `reports/latex_tables.py::build_longtable()` built on **PyLaTeX `LongTable`**; 50 longtables in chap 2, 3, 4, 5, 7 migrated |
| Layout | Geometry with reserved head/foot space; no negative footer `\vspace`; tables fitted to the text width; multirow groups never split; longtable/needspace conflict removed; `\cline` break fix; emergency stretch |
| Chapter 3 | Separate **Vehicle Live Load** and **Footway Live Load** tables driven by the GUI selection |
| Section 5.5 | Four UR bar charts (girders, deck, cross bracing, end diaphragms) with a red dashed UR = 1.0 line; end-diaphragm summary rows now use end-diaphragm data |
| Chapter 7 | Bill of Materials via the table builder, plus an End Diaphragms row, plus three quantity charts (steel MT, concrete m³, rebar MT) |
| Data layer | New `reports/report_data.py` (live loads, URs, quantities; no LaTeX) |
| Charts | New `reports/charts.py` (matplotlib Agg) |
| BOQ | Additive numeric outputs (`boq_numeric`) plus end-diaphragm tonnage when fully defined; **crash-barrier area unit fix** (see R5) |
| Small fixes | `_tex` maps ≤/≥; figure placeholders end their paragraph; Executive Summary girder table and Chapter 8 code tables fitted to the page |
| QA | 158 new tests (163 in the suite on 2026-11-23), a real-data fixture, a GUI-driving report harness, and PDF layout detectors |
| Final QA round | Bugs A–C fixed, D-07…D-16 and D-20 fixed, upstream issues D-04/05/06/17/18/19 disclosed in the report (Part B) |

## 4. The six requirements

### R1: Repeated table headers
* `build_longtable(colspec, header, body, caption=…, label=…, tabcolsep_pt=…)` builds a `pylatex.LongTable` (all content `NoEscape`, because cells are already escaped by `_tex`):
  `\caption{X}\\ \hline <head> \\ \hline \endfirsthead`
  `\caption[]{X (continued)}\\ \hline <head> \\ \hline \endhead` (via `LongTable.end_table_header()`)
  `\multicolumn{n}{r}{Continued on next page}\\ \endfoot \endlastfoot` (via `end_table_footer()` / `end_table_last_footer()`).
* The table number is stepped once; `\caption[]` keeps continuation captions out of the list of tables.
* The header row is shaded (`tableHeaderBg`) and made hyphenatable (`\hspace{0pt}` before bold words).
* **Migration:** a token-aware rewrite (the Python tokenizer finds `\begin{longtable}` inside raw string literals) replaced only the *head* of each standard table with a `build_longtable(…)` call. The original body expression stays byte-identical, including the `""" + expr + r"""` interpolations. Five irregular tables (no header row, existing `\endfirsthead`, two-row header in Table 4.1, the BOM) were migrated by hand. Short single-page `tabular`s (executive summary, Chapter 1/2 information blocks, Chapter 8) were deliberately left as `tabular`.
* The missing `\\` after `\caption` in longtables, the cause of 138 of the 139 LaTeX errors, disappears automatically.

### R2: Page layout, footer and spacing
Root causes and fixes:
1. **Split `\multirow` groups (the G4 overlap).** `keep_multirow_groups()` scans the body brace-aware, finds `\multirow{N}`, and turns the row ends inside the group into `\\*` (longtable's no-break row end). A `\noalign{\nobreak}` goes after each inner `\hline`. Two more TeX-level causes had to be fixed:
   * `\cline` draws its rule as a separate table line followed by `\vskip-\arrayrulewidth`, which is a legal break point. The preamble now patches `\@cline` (colortbl's version) to add `\nobreak` there.
   * longtable processes rows in chunks of 20, and chunk boundaries are always breakable. `LTchunksize` is set to 1000 from `styles.TABLE`.
2. **`\needspace` before longtable.** The original `\BeforeBeginEnvironment{longtable}{\needspace{5\baselineskip}}` issued a page break that longtable's own output routine then processed. Near a page bottom this printed an orphaned "continued" foot and placed the repeated heading *before* the first heading. It is now applied to float `table`s only. A sweep of table positions (tests) shows longtable alone handles every position correctly.
3. **Footer geometry.** The original geometry had `margin=1in` with fancyhdr defaults: `\headheight` 12 pt was too small (fancyhdr enlarged it silently), and the note was moved up with `\vspace{-20pt}`. Now `geometry` gets `headheight=15pt, headsep=14pt, footskip=42pt, includehead, includefoot`, so the space is reserved in the page layout. The note is typeset inside the footer block (`styles.latex_fancy_footer_rule()`).
4. **Over-wide tables.** `fit_colspec()` scales every cm-width column proportionally so that the sum of widths + 2·`\tabcolsep` per column + rules ≤ `\textwidth` (computed from `styles.PAGE`). Spanning cells are sized from the fitted spec, rounded down.
5. `\emergencystretch=3em` reduces overfull lines in narrow cells.

Result (same design data): LaTeX errors 139 → 0, over-wide tables 46 → 0, footer intrusions 1 → 0, minimum clearance 21.9 pt.

### R3: Live load and geometry tables
* `report_data.selected_vehicles(input_dict)` reads the eight IRC checkboxes (`KEY_LL_IRC_*`, GUI order) and the custom-vehicle list. Only selected entries are returned, and the empty list is handled.
* For each vehicle:
  * **Total load** is the sum of the axle or track loads of the IRC 6 Cl. 204 definition in `IRC6_2017`. These are the code-module functions the project already uses: Class A 543.5 kN, 70R (W) 981 kN, 70R (T) 686.8 kN, SV 3776.8 kN, Fatigue 392.4 kN. Classes without a definition in the library (AA wheeled/tracked, 70R bogie) show "—†" with a footnote.
  * **Impact factor**: the same clauses the original chapter used (Cl. 208.2 for Class A, Cl. 208.3 for AA/70R).
  * **Braking considered?**: from `KEY_BL_*` where the GUI stores it (Class SV checkbox); otherwise "As per IRC 6 Cl. 211.2", which is what the GUI describes.
  * **Braking value**: the unchanged `IRC6_2017.cl_211_2_braking_force`. If it fails, which it does for 1–2 lanes because of upstream defect D-18, the cell says "Not available — …" with a plain reason, and the exception goes to the log (Bug B). Lanes come from the lane table, or else `IRC6_2017.table_6(carriageway)`, the analyser's own rule.
  * **Eccentricity**: `KEY_LL_ECCENTRICITY`.
* `footway_info()`: footpath provision, number, width, IRC 6 Cl. 206.1 or custom intensity (kN/m²). Without a footpath the table says "Not applicable".
* "Geometry": the girder-dimension table (17.6 cm wide) and every other over-wide geometry or table spec are fitted to the page (R2.4).

### R4: Utilization-ratio charts (Section 5.5)
* `compute_ur(demand, capacity, reported)`: an existing DCR or Osdag efficiency is authoritative; otherwise UR = |D|/C. Missing, non-numeric or NaN values, or a capacity ≤ 0, give `NO_DATA`. Such a check is never counted as passing. UR = 1.0 passes, UR > 1.0 fails.
* Sources:
  * **Girders**: `design_results.per_girder[G].checks` (each of the 20 check names with its governing girder).
  * **Deck**: `deck_report_values` (sagging, hogging, overhang, punching, one-way shear, crack width).
  * **Cross bracing**: `crossbracing_design_results` with demand from `crossbracing_forces_dict`.
  * **End diaphragms**: `end_diaphragm_design_results` / `end_diaphragm_forces_dict`.
* In the demo design the analysis returns no end-diaphragm forces, so the chart and the summary row say so. The original summary instead repeated the **cross-bracing** numbers under "End Diaphragm — Moment/Shear". Those rows were corrected, which is an intended content change. Section 5.4 had the same problem and was fixed in the final round (D-08).
* `charts.utilization_chart()`: green bars pass, red hatched bars fail, grey marks no data, red dashed line at 1.0, y-axis "Utilization Ratio (Demand / Capacity)", value labels, legend.
* Embedded as LaTeX `figure[H]` in a "Utilization Ratio Charts" subsection after Table 5.28 (Overall Design Check Summary).

### R5: Material-quantity charts (Chapter 7)
* `boq_generator.calculate_material_quantities` now also returns `boq_numeric` (floats next to every printed total; the strings are unchanged). It also computes end-diaphragm tonnage for rolled/welded-beam diaphragms (mass/m × stored length × number of members). For cross-bracing diaphragms the member lengths aren't in the design output, so tonnage is **not computed** and a note says so.
* `report_data.material_quantity_groups()` builds three charts, **one unit per chart**:
  * Structural steel (MT): girders, cross bracing, end diaphragms.
  * Concrete (m³): deck slab, crash barriers.
  * Reinforcement (MT): deck. This is the BOQ estimate of 120 kg/m³, stated under the figure.
* Table 7.1 got the matching "End Diaphragms" row and a real caption.
* **Crash-barrier volume fix (an intended change to Table 7.1).** The BOQ divided `typical_section.crash_barrier.area` by 10⁶ as if it were mm². The GUI field is labelled "Area (m²)" and the stored default is 0.3023 m², which matches the 7.56 kN/m barrier load at 25 kN/m³. The original report therefore printed 0.00 m³ / 0.00 MT for the crash barriers. With the fix: 2 × 0.3023 m² × 30 m = 18.14 m³ (45.35 MT). This is a quantity take-off correction, not a structural calculation; the analysis uses the barrier *load*, which is unchanged. Covered by `test_crash_barrier_volume_uses_area_in_m2`.

### R6: Centralised styling (`reports/styles.py`)
| Block | Controls |
|---|---|
| `PAGE`, `geometry_options()`, `text_width_cm()` | paper, margins, head/foot reservation |
| `TYPOGRAPHY` | base size, class, line stretch, emergency stretch, note and continued-text fonts |
| `COLORS`, `LATEX_COLOR_NAMES`, `CHART_PALETTE`, `latex_color_definitions()` | brand / secondary / accent, table header, pass / fail / no-data, reference line, chart palette |
| `TABLE`, `latex_table_settings()`, `available_column_width_cm()` | padding, row stretch, rules, row spacing, longtable pre/post, header shading, chunk size, width safety |
| `HEADER_FOOTER`, `latex_head_rule()`, `latex_fancy_footer_rule()` | footer texts, rules, separation |
| `FIGURES`, `CHART`, `matplotlib_rc()` | figure widths, chart size, dpi, fonts, grid, reference line |

The module has no `osdagbridge` imports (no circular imports). The preamble, `latex_tables`, `charts`, `chap3`, `chap5` and `chap7` read from it, and tests prove that a value change propagates to the LaTeX. Legacy per-table settings inside untouched chapter text (e.g. `\setlength{\tabcolsep}{3.5pt}` groups) were left unchanged rather than rewritten.

## 5. Files modified
`report_generator.py` (preamble from styles, needspace and cline fixes, chart generation, log retention), `chap2.py`, `chap3.py`, `chap4.py`, `chap5.py`, `chap7.py`, `chap8.py`, `executive_summary.py`, `report_utils.py`, `core/boq/boq_generator.py`, `environment.yml`, `pyproject.toml`, `requirements.txt`.

## 6. Files created
`reports/styles.py`, `reports/latex_tables.py`, `reports/report_data.py`, `reports/charts.py`, `scripts/report_harness/{generate_report_offscreen.py, rebuild_report.py, sample_case.json}`, `tests/conftest.py`, `tests/unit/{report_test_utils.py, test_report_tables.py, test_report_styles.py, test_report_live_loads.py, test_report_utilization.py, test_report_quantities.py}`, `tests/integration/test_report_generation.py`, `tests/fixtures/demo_case_30m.json.gz`.

## 7. Architecture
```
report_generator.generate_report
 ├─ styles ──────────────► preamble (geometry, colours, table lengths, header/footer)
 ├─ boq_generator ───────► quantities (strings + boq_numeric)
 ├─ _build_report_charts
 │    ├─ report_data.collect_utilization ─► charts.utilization_chart ─► tmp/images/charts/ur_*.png
 │    └─ report_data.material_quantity_groups ─► charts.quantity_chart ─► tmp/images/charts/qty_*.png
 └─ chapters (chap3 ─ report_data live loads; chap5 ─ UR rows and figures; chap7 ─ BOM and figures)
         all multi-page tables ─► latex_tables.build_longtable (PyLaTeX LongTable)
```
The dependency direction is one way: `styles` ← `latex_tables` / `charts`; `report_data` has no LaTeX; the chapters import those modules; `report_generator` imports the chapters.

## 8. Live-load data flow
Additional Inputs → Loading → Live Load checkboxes → `input_dict[KEY_LL_IRC_*]` (bool or "True") → `report_data.selected_vehicles` (+ `IRC6_2017` cl. 204/208) → `chap3.vehicle_live_load_table`. Footpath: Input Dock footpath, Typical Section width and count, Loading footway mode/value → `footway_info` → `footway_live_load_table`.

## 9. Utilization-ratio data flow
`PlateGirderBridge.design()` → `output_dict` (`design_results`, `deck_report_values`, `crossbracing_*`, `end_diaphragm_*`) → `report_data.collect_utilization` → (a) Table 5.28 rows and the Executive Summary statuses, (b) `charts.utilization_chart` → Section 5.5 figures.

## 10. Material-quantity data flow
`input_dict` + `output_dict` → `calculate_material_quantities` → strings (Table 7.1) and `boq_numeric` → `material_quantity_groups` → `quantity_chart` → Chapter 7 figures.

## 11. Chart generation
matplotlib with the `Agg` backend (thread-safe, no display) inside `plt.rc_context(styles.matplotlib_rc())`; 200 dpi PNG files go into the report's temporary directory (`images/charts`) and are deleted with it after compilation. Chart errors are logged and never stop the report. If compilation fails, the LaTeX log is copied next to the `.tex`. `OSDAGBRIDGE_REPORT_KEEP_LOG=1` keeps it on success too.

## 12. LongTable implementation details
`parse_colspec` understands `|`, `>{}`, `<{}`, `@{}`, `!{}`, `*{n}{…}`, l/c/r/X and p/m/b/L/C/R widths. `fit_colspec` only scales specs whose columns all have cm widths, floors them to 0.01 cm, and keeps the column types. `format_row` adds the style's row padding and `\hline`.

## 13. Footer and pagination fixes
See R2. Verification: `tests/unit/test_report_tables.py` (page-position sweeps, unsplit groups) and `tests/integration/test_report_generation.py::test_no_text_in_footer_area`.

## 14. Dependencies
`pylatex>=1.4` declared in `pyproject.toml`, `requirements.txt` and `environment.yml`. It was already installed through `osdag::osdag`, so nothing new is needed at runtime. Test extra: `pymupdf` (PDF inspection; PDF tests skip without it). matplotlib was already a dependency.

**Upstream defects in the engineering code** (documented, not changed): see `KNOWN_LIMITATIONS.md` and `DEFECT_REGISTER.md` (D-04, D-05, D-06, D-17, D-18, D-19). The report now discloses each one where it matters.

## 15–18. Installation, testing, PDF generation, limitations
These moved to `SETUP_AND_EXECUTION.md`, `TEST_RESULTS.md` and `KNOWN_LIMITATIONS.md`.

# Part B: final QA round

## 19. Changes in the final QA round

Full root causes and tests for each item are in `DEFECT_REGISTER.md`.

### 19.1 Confirmed bugs
| Bug | Change | Files |
|---|---|---|
| **A**: girder dimensions in m printed as mm | `girder_dimension_source_unit()` (m after `design()`, mm before), `length_in_mm()` (explicit source unit, raises for unknown units, never converts twice), `format_mm()`; `_girder_tables(…, dim_unit)` | `report_data.py`, `chap2.py` |
| **B**: raw `UnboundLocalError` in the braking row | `braking_info()` logs the exception with its traceback and sets `unavailable_reason` (plain sentence). `design_lanes()` gives lanes and their source. The IRC 6 function is **not** patched (a missing "succeeding trains" term must not become 0). | `report_data.py`, `chap3.py` |
| **C**: hard-coded "design pass" | `component_status()` / `design_status()` (PASS / FAIL / INCOMPLETE / NOT AVAILABLE; overall PASS / FAIL / NOT FULLY VERIFIED); `girder_check_items()`, `per_girder_governing()`, `girder_ur_items()` (a failing item is never replaced by a passing one). The Executive Summary was rewritten: status, governing check, per-girder governing check and UR, Key Design Outcomes table, "UR ≤ 1.0 passes", units on spacing and thickness. | `report_data.py`, `executive_summary.py` |

### 19.2 Further defects found in the audit (fixed)
| ID | Change | Files |
|---|---|---|
| D-07 | BOQ girder area from the final designed section (`_designed_girder_area_m2`, equals `A_steel_mm2`); 32.89 → 36.46 MT | `boq_generator.py` |
| D-08 | Section 5.4 end-diaphragm tables built from end-diaphragm input and results (`end_diaphragm_members`, `end_diaphragm_tables`) instead of cross-bracing content; same for the Table 5.28 rows | `report_data.py`, `chap5.py` |
| D-09 | Removed global `\LTleft`/`\LTright`/`\tabcolsep` overrides that leaked into later chapters | `chap2.py`, `chap5.py` |
| D-10 | Title page unnumbered; since 2026-11-22 the counter continues at 2, so "Page X of Y" equals the PDF page (see §20) | `report_generator.py` |
| D-11 | Table 1 in a minipage; `\clearpage` before Sections 5.1 and 5.5 (not `\needspace`, see ARCHITECTURE §6) | `executive_summary.py`, `chap5.py` |
| D-12 | `keep_rules_with_rows()`; closing `\hline` moved into `\endlastfoot` | `latex_tables.py` |
| D-13 | Lanes shown; Vz/Pz shown; wind/seismic forces "Not available"; Table 4.2 governing reactions (max \|R\|) | `chap2.py`, `chap3.py`, `chap4.py` |
| D-14 | Table 5.7 labels "Required …"/"Provided …" by design mode | `chap5.py` |
| D-15 | Table 5.16 impact-factor label no longer claims Cl. 208.2 | `chap5.py` |
| D-16 | Rebar chart label shortened | `report_data.py` |
| D-20 | Table 4.2 ties broken by name and disclosed ("and N other load cases with the same value") | `chap4.py` |

### 19.3 Upstream issues disclosed in the report (engineering code unchanged)
`consistency_notes(input_dict, output_dict)` detects four of them from the data: `girder_count` (D-04), `cb_spacing` (D-05), `section_properties` (D-06), and `deflection` (D-17, > 5 % difference). They are printed:
* in the Executive Summary ("Data Consistency Notes");
* in a box at the start of Chapter 5;
* under Table 2.9 and Tables 4.1 / 4.3.

D-18 (braking) is shown in Table 3.3; D-19 (vehicle checkboxes) is documented only.

### 19.4 Other
* Unused imports introduced by this work were removed, and the touched files were normalized to CRLF (repository convention).
* The test suite grew from 94 to 144 tests: `test_report_regressions.py` plus three PDF-level integration tests.

### 19.5 Files changed relative to `d74f56d`
**Modified:**
* `src/osdagbridge/core/reports/`: `report_generator.py`, `executive_summary.py`, `chap2.py`, `chap3.py`, `chap4.py`, `chap5.py`, `chap7.py`, `chap8.py`, `report_utils.py`
* `src/osdagbridge/core/boq/boq_generator.py`
* `environment.yml`, `pyproject.toml`, `requirements.txt`

**New:**
* `src/osdagbridge/core/reports/`: `styles.py`, `latex_tables.py`, `report_data.py`, `charts.py`
* `scripts/report_harness/`: `generate_report_offscreen.py`, `rebuild_report.py`, `sample_case.json`
* `tests/conftest.py`, `tests/fixtures/demo_case_30m.json.gz`
* `tests/unit/`: `report_test_utils.py`, `test_report_tables.py`, `test_report_styles.py`, `test_report_live_loads.py`, `test_report_utilization.py`, `test_report_quantities.py`, `test_report_regressions.py`
* `tests/integration/test_report_generation.py`

In total, 30 files: +4422 / −779 lines (`git diff --shortstat` of the patch).

## 20. Changes on 2026-11-22/23 (final integration round, `Desktop\OsdagBridge`)

| Change | Files | Test |
|---|---|---|
| Chart failures are visible: each figure that cannot be drawn becomes a framed placeholder "Chart could not be generated; values are in Table 5.28 / 7.1" (via `\ref`, so the number is always right) and a warning is logged. Tables 5.28 and 7.1 got labels. | `report_generator.py`, `report_utils.py`, `chap5.py`, `chap7.py` | `test_report_gap_closures.py` (exception, matplotlib missing, real PDF compile) |
| Figure 5.4 without results is a framed panel: axes, UR axis label and red dashed UR = 1.0 line kept, reason in a box inside the plot area. | `charts.py` | `test_ur_no_data_panel_keeps_axes_and_limit_line` |
| Centrifugal force row in Table 3.3: "Not applicable (straight bridge)" when there is no plan-curvature input (always, today); "Not available - not computed by the design pipeline" otherwise. No value is ever computed. | `report_data.py`, `chap3.py` | three tests (straight, curved, analyser has no curve) |
| Braking failure sentence names the reason: "…returns no value for 2 design lanes (known upstream defect D-18)." | `report_data.py` | `test_table_3_3_braking_failure_is_one_plain_sentence` |
| One-line end-diaphragm tonnage note under Figure 7.1. | `report_data.py` | `test_end_diaphragm_tonnage_*` |
| Page numbering: `\setcounter{page}{2}` after the title page, so "Page X of Y" equals the PDF page and Y the page count. | `report_generator.py` | `test_footer_page_numbers_match_pdf_pages` |
| Hard-coded per-table spacing (3 pt / 3.5 pt / 1.25) moved to `styles.TABLE` (`tabcolsep_compact_pt`, `tabcolsep_dense_pt`, `arraystretch_dense`) with the same values (layout unchanged). | `styles.py`, `chap4.py`, `chap7.py`, `chap8.py` | existing layout tests |
| Table 5.28 end-diaphragm message cell ends with `\strut`, so its last line no longer touches the rule below (was −0.01 pt, now 2.54 pt). | `chap5.py` | `test_table_5_28_end_diaphragm_message_has_strut`, `test_table_5_28_end_diaphragm_message_clears_bottom_rule` |
| Brief 2-page `deliverables/Technical_Changes.pdf` (this file stays the long reference). | `deliverables/` | — |
| Environment: editable install repointed to this repo (offline reinstall). | conda env only | full suite without `PYTHONPATH` |

Not changed: engineering formulas, code factors, loads, design results, and the upstream defects D-04, D-05, D-06, D-17, D-18, D-19.
