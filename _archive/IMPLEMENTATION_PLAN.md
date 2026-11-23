# Implementation Plan: OsdagBridge Report Generator Refactoring

Written after a read-only investigation of the `dev` branch at commit `d74f56dd7f22925fb8148cabf5740ed8d1e39ff3`. Every path below was found in the actual code, not assumed from the assignment text. Section 7 records how the plan turned out.

## 1. Discovered architecture

The report is **hand-written LaTeX built from Python strings** (raw `r"""…"""` templates joined together). PyLaTeX was not used anywhere. Compilation runs `pdflatex` twice in a temporary directory.

| # | Item | Actual location |
|---|---|---|
| 1 | Entry point | `src/osdagbridge/core/reports/report_generator.py`: `build_report_payload()`, `generate_report()` |
| 2 | Report directory | `src/osdagbridge/core/reports/` |
| 3 | Chapter generators | `executive_summary.py`, `chap1.py` … `chap9.py` (each returns a LaTeX string) |
| 4 | Section generators | inside the chapter files (e.g. `chap5.py` has sections 5.1–5.5) |
| 5 | Existing PyLaTeX code | none |
| 6 | Table utilities | none; about 51 hand-written `longtable`/`tabular` blocks, only 2 with `\endhead` |
| 7 | Geometry | `preamble()`: `\usepackage[a4paper, margin=1in]{geometry}`, no head/foot sizes |
| 8 | Header/footer | `preamble()`: fancyhdr styles `main`/`plain`/`firstpage`; the footer note "* Software default value" is pulled up with `\vspace{-20pt}` |
| 9 | Charts | none in the report; matplotlib is used by `plate_girder/plot_generator.py` for GUI plots (BM/SF/deflection images are captured into the report) |
| 10 | Chapter 3 live load | `chap3.py::ch3_loads()`, a single "Live Loads (LL)" table that merged vehicles, impact, braking and footpath load |
| 11 | GUI Loading tab | `core/bridge_types/plate_girder/ui_fields_additional_input.py` (live-load schema), defaults in `defaults.py::_update_loading_tab_defaults` |
| 12 | Additional-input data | flat `input_dict` keys from `core/utils/common.py`: `KEY_LL_IRC_*` (vehicle checkboxes), `KEY_BL_IRC_CLASS_SV`, `KEY_LL_ECCENTRICITY`, `KEY_LL_FOOTPATH_PRESSURE_MODE/VALUE`, `KEY_FOOTPATH`, `KEY_TS_FOOTPATH_WIDTH`, `KEY_TS_NO_OF_FOOTPATHS` |
| 13 | Section 5.5 | `chap5.py` (end of `ch5_design_checks`, the `t522` rows) |
| 14 | Chapter 7 | `chap7.py::ch7_quantities()`, values from `core/boq/boq_generator.py::calculate_material_quantities()` |
| 15 | Demand/capacity sources | girders: `output_dict["design_results"]["per_girder"][G]["checks"]` (demand, capacity, **dcr**); deck: `output_dict["deck_report_values"]` (`KEY_DD_*`); cross bracing: `crossbracing_design_results` (Osdag efficiency and capacity) plus `crossbracing_forces_dict`; end diaphragms: `end_diaphragm_design_results` plus `end_diaphragm_forces_dict` |
| 16 | Quantity sources | `boq_generator.py` returns **formatted strings**, merged into `payload.inputs` |
| 17 | Dependency files | `environment.yml`, `pyproject.toml`, `requirements.txt`, `conda-recipe/meta.yaml` |
| 18 | Test suite | `tests/unit`, `tests/integration`: 6 placeholder tests (`assert True`) |
| 19 | Sample projects | none; `examples/plate_girder/*.yaml` are placeholders (one states `span_m: 30.0`) |
| 20 | PDF workflow | Output dock **Generate Report** → `CustomWindow.open_report_dialog` → `ReportOptionsDialog.build_request` → worker thread → `PlateGirderBridge.generate_design_report` → `build_report_payload` → `generate_report` |

## 2. Data flow

```
GUI Input Dock + Additional Inputs ──► CustomWindow.input_dict
      │ Design
      ▼
PlateGirderBridge.set_input() / design()  ──► output_dict (frozen MappingProxy)
      │ Generate Report (OutputDock captures CAD / plot PNG bytes)
      ▼
generate_design_report(): input_dict copy, output_dict copy, analysis_summary
      ▼
build_report_payload()  ──► ReportPayload(inputs, output_dict, figure_data, …)
      ▼
generate_report(): figures → tmp/images, BOQ strings → inputs,
                   chapters → .tex, pdflatex ×2, copy PDF/TEX to output dir
```

* **Vehicle selection:** each IRC class is a boolean `input_dict[KEY_LL_IRC_*]`. Custom vehicles are a list under `KEY_LL_CUSTOM_VEHICLES`. Note that the analyser places vehicles from IRC 6 Table 6A (Class A / 70R) whatever is ticked. The report has to show the user's selection.
* **Live-load parameters:** vehicle axle loads come from `IRC6_2017.cl_204_*`, impact factors from `cl_208_2/208_3`, braking from `cl_211_2` (lane count `KEY_WC_LD_LANE_TABLE_COUNT`), and footway load from `cl_206_1` or a custom value.
* **Utilization ratios:** girders already store DCR values, which are authoritative. The deck stores only demand and capacity, so UR = D/C. Bracing members store the Osdag efficiency. End diaphragms use the same structure as bracing (empty in the demo design).
* **Quantities:** the BOQ module computes from inputs/outputs; Chapter 7 prints strings via `input_dict.get(...)`.

## 3. Approach (incremental, without rewriting)

1. `styles.py`: one source of truth for geometry, typography, colours, table spacing, header/footer and chart styling. The preamble consumes it.
2. `latex_tables.py`: `build_longtable()` built on **PyLaTeX `LongTable`**. It produces `\endfirsthead` / `\endhead` / `\endfoot` / `\endlastfoot`, continued captions and width fitting. The existing tables were migrated by a token-aware source rewrite: the table bodies stay byte-identical and only the table head is generated. Irregular tables were migrated by hand.
3. Footer/layout: reserve real head/foot space in the geometry, remove the negative `\vspace`, fix tables wider than the page, and keep `\multirow` groups on one page.
4. `report_data.py`: pure data extraction (live loads, URs, quantities) with no LaTeX, shared by tables, charts and tests.
5. `charts.py`: matplotlib (Agg) charts written to the temporary image directory and embedded as LaTeX figures.
6. Additive BOQ change: numeric values next to the existing strings, plus end-diaphragm tonnage where it is fully defined.
7. Real-data harness that drives the real GUI off-screen to produce both PDFs. Tests: unit tests with synthetic values, and integration tests on a real design fixture.

## 4. Risks identified at planning time

| Risk | Mitigation |
|---|---|
| No real project file in the repository | Run the GUI with the application defaults plus a span from the repo's example (documented as a demonstration case) |
| Rewriting 51 tables by hand could drop rows | Mechanical rewrite that keeps bodies byte-identical; tests check row preservation; compare numbers Before/After |
| PyLaTeX escaping would break existing LaTeX | Everything passed as `NoEscape`; cells are already escaped by `_tex` |
| `pdflatex -interaction=nonstopmode` hides errors | Opt-in log retention (`OSDAGBRIDGE_REPORT_KEEP_LOG=1`) and tests that parse the log |
| End-diaphragm data may not exist | Show "no data" with the reason; never borrow other members' values |
| Rebar quantity is a 120 kg/m³ estimate | Chart it as the Chapter 7 value and label it as an estimate |

## 5. Test strategy

* Unit: column-spec fitting, LongTable structure, row preservation, multirow grouping, style values and consumption, import isolation, live-load selections, UR maths and edge cases, chart reference line and colours, BOQ numbers.
* LaTeX level: compile synthetic multi-page tables at several page positions and check repeated headers, unsplit groups, no orphaned feet and no overfull tables.
* Integration: full `build_report_payload` → `generate_report` on the real design fixture, then inspect the PDF text, images, the footer band and the LaTeX log.
* End-to-end: GUI harness run for Report_Before (original code) and Report_After (new code), with visual inspection of the rendered pages.

## 6. Out of scope (left unchanged on purpose)

Structural engineering calculations, the analyser, the GUI and the report content outside the six requirements. Pre-existing engineering-code defects found along the way are documented, not changed (see TECHNICAL_CHANGES §14).

## 7. Deviations from the plan, found during implementation

* The existing `\BeforeBeginEnvironment{longtable}{\needspace…}` hook turned out to be the cause of broken table starts (an orphaned "continued" foot, and the first heading printed after the repeated heading). It was removed for longtables.
* `\cline` creates a page-break opportunity that `\\*` can't block, so `\@cline` is patched to add `\nobreak`. longtable's 20-row chunks also allow breaks, so `LTchunksize` was raised.
