# Test Results

Date: 2026-11-21 · Environment: `osdagbridge-env` (Python 3.12.16, pytest 9.2.0, pdfTeX / TeX Live 2025 from `osdag_latex_env`) · Branch: `feature/report-generator-enhancements` (uncommitted working tree)

## 1. Automated test suite

Command (from the repository root, env activated):

```powershell
python -m pytest tests -v
```

**Result: 94 collected · 94 passed · 0 failed · 0 skipped** (≈ 26 s). The full log is in `evidence/pytest_output.txt`.

| Test file | Kind | Tests | Result |
|---|---|---|---|
| `tests/unit/test_report_tables.py` | Requirements 1 & 2: LongTable structure, row preservation, width fitting, multirow grouping; real `pdflatex` compiles of multi-page tables at several page positions | 18 | pass |
| `tests/unit/test_report_styles.py` | Requirement 6: config values, preamble consumes `styles`, a style change propagates, import isolation (no circular imports, each module imported first in a fresh interpreter) | 17 | pass |
| `tests/unit/test_report_live_loads.py` | Requirement 3: selected-vehicle combinations, empty selection, string booleans, IRC 6 totals, impact factors, braking flags and lanes, custom vehicles, footway none / IRC 6 / custom / missing, Chapter 3 has two tables | 17 | pass |
| `tests/unit/test_report_utilization.py` | Requirement 4: UR < 1, = 1, > 1, zero capacity, missing or NaN or text values, authoritative DCR; real-data girder, deck, bracing and end-diaphragm extraction; chart reference line (red, dashed, y = 1.0), pass/fail/no-data colours; Section 5.5 has 4 charts | 21 | pass |
| `tests/unit/test_report_quantities.py` | Requirement 5: numeric BOQ equals the printed strings, units, crash-barrier area in m², missing quantities stay missing, rolled-beam end-diaphragm tonnage, chart PNGs, Chapter 7 table plus charts | 8 | pass |
| `tests/integration/test_report_generation.py` | **Real-data integration**: full `build_report_payload` → `generate_report` → PDF on the real design fixture; LaTeX log, chapters, repeated heads, no orphaned feet, live-load tables, 7 chart figures, no text in the footer band, temporary images cleaned up | 8 | pass |
| `tests/unit/test_analyser.py`, `test_designer.py`, `test_io.py`, `tests/integration/test_api_plate_girder.py`, `test_cli_plate_girder.py` | Pre-existing placeholders (`assert True`), unchanged | 5 | pass |

`tests/integration/verification_ddcl_cases.py` is a pre-existing placeholder with no tests.

### Synthetic versus real data
* **Synthetic values** are used only in isolated unit tests: UR arithmetic, chart styling, table mechanics, BOQ for a rolled-beam end diaphragm, footway variants.
* **Real data** is `tests/fixtures/demo_case_30m.json.gz`. It holds the `input_dict` / `output_dict` captured from an OsdagBridge GUI design run (see §3), with the figure bytes removed. It is used by the extraction, Chapter 3/5/7 and integration tests. No production code contains test values.

## 2. LaTeX compilation: Before versus After (same design data)

| Metric | Original code | New code |
|---|---|---|
| LaTeX errors in log (`! …`) | **139**: 46 × "Misplaced `\noalign`", 46 × "Misplaced `\omit`", 46 × "Extra alignment tab", 1 × "Unicode character ≤" | **0** |
| Tables wider than the text block (`Overfull \hbox … in alignment`) | **46** | **0** |
| All `Overfull \hbox` warnings | 58 | 12, all ≤ 5.1 pt and inside the 6 pt cell padding (long single words such as "Diagonal", and one unbreakable BOQ formula) |
| Text in the footer band (PDF measurement) | 1 page (PDF p. 31, "Page 30 of 58": label **G4**) | 0 pages; minimum body-to-footer clearance 21.9 pt |
| Multi-page tables with repeated column headings | 2 | all longtables (continued caption plus heading on each page) |
| Pages | 59 | 73 (4 pages of new charts, a separate footway table, girder groups kept together, explicit head/foot space) |

The original-code numbers come from rebuilding the original commit's report from the same design payload with its LaTeX log kept. The original `generate_report` deletes the log. The new-code numbers come from the log of the GUI-workflow `Report_After.pdf` (`OSDAGBRIDGE_REPORT_KEEP_LOG=1`).

## 3. End-to-end runs (real application workflow)

`scripts/report_harness/generate_report_offscreen.py` drives the **real desktop window** (`CustomWindow`) on the normal Windows platform, with the window positioned off-screen so OpenCASCADE can render its 3D views. It types the Input Dock values, presses **Design** (the same worker thread as the GUI button), then calls the Output Dock's **Generate Report** handler, which does the real figure capture and builds the request with the real `ReportOptionsDialog.build_request`. Only the modal steps (options dialog `exec`, file picker, message boxes) are replaced by code.

| Run | Code | Design | Figures captured | Result |
|---|---|---|---|---|
| Report_Before | original commit `d74f56d` (pristine `git archive` copy on `PYTHONPATH`) | 75 s | 17 (incl. 3D views) | PDF 59 pages |
| Report_After | working tree | 61 s | 17 | PDF 73 pages, 0 LaTeX errors |

Every numeric value in the Report_Before LaTeX also appears in Report_After, with two intended exceptions:
* Six values that the original repeated as "End Diaphragm" rows in Table 5.29 were cross-bracing results. Those copies were removed.
* The crash-barrier row of Table 7.1 changed from 0.00 m³ (a unit bug) to 18.14 m³; see TECHNICAL_CHANGES R5.

## 4. Visual inspection (done)

Pages were rendered with PyMuPDF and inspected: the whole document as contact sheets, and the key pages at full size. Evidence images are in `evidence/`. Pages checked include the original p. 31 ("Page 30 of 58") and its counterparts (After pp. 37–38), the Chapter 3 tables (After pp. 15–16), the continued demand table (p. 21), Section 5.5 (pp. 53–57) and Chapter 7 (pp. 65–68).

## 5. Limitations of this verification

* The GUI was driven programmatically, not clicked by a person. The modal dialogs were bypassed as described above, and the window was not viewed on screen.
* The process segfaults during Qt/OpenCASCADE teardown, *after* the PDF has been written (exit code 139). This is not observed in the report code.
* Only one design case (the demonstration case) was run end to end. The other vehicle and footpath combinations are covered by unit tests.
