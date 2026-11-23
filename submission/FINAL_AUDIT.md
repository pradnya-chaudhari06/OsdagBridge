# Final Audit

**Date:** 2026-11-21, updated 2026-11-23 (final integration round in `Desktop\OsdagBridge`).
**Subject:** report generator on `feature/report-generator-enhancements` (uncommitted, base `d74f56d`).
**Inputs used:** the demonstration case (`scripts/report_harness/sample_case.json`), run through the GUI workflow. `deliverables/Report_After.pdf` was regenerated on 2026-11-23 through the GUI harness (GUI classes driven from code, dialogs bypassed).

**Status classes:**
* **PASS**: implemented and verified in the final PDF and by tests.
* **PARTIAL**: implemented, but part of it could not be verified end to end.
* **BLOCKED**: cannot be done without data or upstream changes.
* **FAIL**: not achieved.

## 1. Requirements

| # | Requirement | Status | Evidence (final `Report_After.pdf` page) | Notes |
|---|---|---|---|---|
| R1 | Repeated LongTable headers | **PASS** | Table 4.1 pp. 21–24; Tables 5.1–5.9 pp. 29–44 | Every longtable has a first head, a repeated "(continued)" head and a continuation foot. 0 misplaced heads (detector + integration test). |
| R2 | Page layout, footer overlap | **PASS** | p. 40 (former "G4 in footer" table) | Detectors report 0 footer intrusions (min clearance 21.9 pt), 0 stray rules, 0 orphaned headings, 0 over-wide tables. 11 hbox ≤ 5.1 pt and 2 vbox 5.4 pt remain (accepted). |
| R3 | Vehicle vs footway live-load tables from the GUI selection | **PASS** | Table 3.3 p. 16–17, Table 3.4 p. 17 | Lists only the ticked vehicles. The braking **value** is "Not available" with a plain one-sentence reason, because the IRC 6 function fails for 2 lanes (upstream D-18); that value is **BLOCKED** upstream. Centrifugal force: "Not applicable (straight bridge)" — decided from the code (no plan-curvature input; the grillage is built straight in plan). |
| R4 | UR charts with red dashed UR = 1.0 line | **PARTIAL** | Figs 5.1–5.4 pp. 58–59 | Girders, deck and cross bracing are verified with real data. Figure 5.4 is a framed panel with the axes, the red dashed UR = 1.0 line and the reason (the demo has no end-diaphragm results). Bars from real Osdag member results are unit-tested only. |
| R5 | Quantity charts (steel MT, concrete m³, rebar MT) | **PARTIAL** | Table 7.1 p. 67, Figs 7.1–7.3 pp. 68–70 | All three charts are verified. End-diaphragm tonnage is "not available" for cross-bracing-type diaphragms (member lengths not in the output); a one-line note under Figure 7.1 says so. Rolled-beam tonnage is unit-tested only. |
| R6 | Central `styles.py` | **PASS** | — | The preamble, tables and charts read it, and tests prove that a change propagates. Some legacy per-table spacing in untouched chapter text remains. |

## 2. Confirmed bugs

| Bug | Status | Before | After |
|---|---|---|---|
| A: Table 2.7 dimensions | **FIXED** | "1.67 mm", "0.022 mm" | 1670 mm, 22 mm (p. 12), equal to Table 5.1 |
| B: braking row | **FIXED** | "N/A … raised UnboundLocalError" | "Not available — the design pipeline's IRC 6 Cl. 211.2 braking-force function returns no value for 2 design lanes (known upstream defect D-18)." (p. 17); traceback in the log |
| C: Executive Summary | **FIXED** | every component "design pass"; overall from girders only; same UR in every girder column | Overall **FAIL** (girder fatigue UR 1.58; intermediate stiffener leg UR 1.48). Deck PASS 0.94, cross bracing PASS 0.74, end diaphragms NOT AVAILABLE. Per-girder governing checks (pp. 3, 6). |

## 3. Before/after comparison (same inputs, same workflow)

| Aspect | Report_Before.pdf | Report_After.pdf |
|---|---|---|
| Pages | 59 | 75 |
| LaTeX errors / over-wide tables | 139 / 46 | 0 / 0 |
| Footer intrusion | "G4" in the footer (p. 31) | none |
| Repeated table heads | 2 tables | all multi-page tables |
| Executive Summary status | hard-coded pass | derived: FAIL with the failing checks named |
| Girder dimensions | metres labelled mm | mm |
| Braking row | Python exception name | plain "Not available" sentence |
| Live loads | one merged table | Vehicle (Table 3.3) and Footway (Table 3.4) tables |
| Blank cells (lanes, Vz, Pz, wind/seismic forces, Table 4.2) | blank | values, or "Not available" |
| Section 5.4 end diaphragms | cross-bracing data under end-diaphragm captions | end-diaphragm members, plus "no results" with the reason |
| UR charts | none | 4 (Section 5.5) |
| Quantity charts | none | 3 (Chapter 7) |
| Girder steel (BOQ) | 32.89 MT (stale section) | 36.46 MT (designed section) |
| Crash-barrier concrete | 0.00 m³ (unit bug) | 18.14 m³ |
| Upstream inconsistencies | silent | disclosed in 3 places |

**Content changes that are corrections, not regressions:**
* the end-diaphragm rows and tables no longer show cross-bracing values;
* girder tonnage now follows the designed section;
* the crash-barrier volume is corrected;
* the overall status is now FAIL, as the design results require.

## 4. Cross-report consistency (verified in the final PDF)

| Item | Result |
|---|---|
| Girder count | Input 4 (Ch. 1, 2, Exec. Summary) vs design members G1–G6 (Ch. 4, 5): inconsistent **upstream** (D-04), disclosed on pp. 7, 24, 28 |
| Section properties | Table 2.7 = Table 5.1 = `design_results` (1670/10/510/22). The analysis section differs upstream (D-06), disclosed |
| Design outcomes | Executive Summary = Table 5.28 = Section 5.5 charts (same `collect_utilization` data) |
| Loading | Table 3.3 = GUI selection. The analysis vehicles may differ upstream (D-19), documented |
| Deflection | Table 4.3 / 5.9 vs IRC 22 check disagree upstream (D-17), disclosed under Table 4.3 |
| BOM vs charts | Chart bars equal the `boq_numeric` values that print in Table 7.1 (test `test_report_quantities`) |
| Metadata | Project name, job number, revision and date are identical on the title page, in Chapter 1 and in the running head |

## 5. Engineering integrity

* No engineering formula, code factor, load or design result was changed. The only calculation changes are in the **quantity take-off**:
  * girder area from the designed section;
  * crash-barrier area interpreted in m², as the GUI labels it.
* No value is invented:
  * missing values print "Not available" or "---";
  * missing values are never converted to 0;
  * missing checks are never counted as passing.
* Failures are shown: the demo bridge is reported as **FAIL**, and failing URs are printed in red.
* Upstream defects are disclosed, not patched, where a fix needs engineering judgement (D-04, D-05, D-06, D-17, D-18, D-19).
* The demonstration case is labelled as such and is not presented as a real bridge.

## 6. Code-quality review

| Aspect | Assessment |
|---|---|
| Structure | Data (`report_data`), formatting (`styles`), tables (`latex_tables`) and charts (`charts`) are separated, with one-way dependencies |
| Single source of truth | Statuses, URs and quantities are computed once and reused by every chapter |
| Error handling | Engineering-function failures are logged with tracebacks and never print Python text into the PDF. A chart that cannot be generated prints a framed placeholder "Chart could not be generated; values are in Table 5.28 / 7.1" (table number via `\ref`) and logs a warning. |
| Tests | 163 tests (run 2026-11-23, all pass), with real-data fixture tests and PDF-level layout tests |
| Static checks | pyflakes shows no new warnings from this work; pre-existing warnings in untouched code remain |
| Legacy code | Chapter modules are still large raw-LaTeX string templates. Only what the requirements and defects needed was rewritten. |

## 7. Reviewer readiness

| Item | Status |
|---|---|
| Patch applies to a clean `d74f56d` | **PASS for the 2026-11-21 handover patch only.** The working tree has later changes (2026-11-22/23); no new patch was produced (git is left to the owner). |
| Tests pass in the clean copy | **PASS on 2026-11-21 (144, handover patch).** The current tree (163 tests) was tested in the repo only. |
| Report reproducible in the clean copy | **Verified 2026-11-21 only** (handover patch). Not repeated for the current tree. |
| Documentation complete | **PASS** (this folder) |
| PDF visually inspected | **PARTIAL for the 2026-11-23 build:** automated layout checks on every page (0 footer intrusions, 0 stray rules, 0 orphaned headings, 0 misplaced continued heads, every "Continued on next page" followed by a repeated head, every page "Page i of 75"); pages 16–17, 56–59 and 67–70 of the final build inspected as images (pp. 24–25 on the previous build). The every-page visual pass was done on the 2026-11-21 build. |
| Engineering sign-off | **Not done**: requires an engineer (see `KNOWN_LIMITATIONS.md`) |
| Real project data | **BLOCKED**: none in the repository |

## 8. Verdict

The report generator meets R1, R2, R3 and R6 and fixes bugs A–C. R4 and R5 are complete in code but **PARTIAL** in end-to-end verification, because the demonstration design has no end-diaphragm results. The output is honest about the design: the demo bridge fails two checks, and six upstream inconsistencies are disclosed. The work is ready for code and engineering review. It is not claimed to be perfect, and it is not ready for use on a real project until the disclosed upstream issues are resolved by the responsible engineers.

## 9. Update 2026-11-23 (final integration round)

Verified in `Desktop\OsdagBridge` on 2026-11-23:
* `python -m pytest tests -q`: **163 passed** (no `PYTHONPATH`; the editable install now points at this repo).
* `Report_After.pdf` regenerated through the GUI harness: **75 pages, 0 LaTeX errors, 0 over-wide tables, 0 footer intrusions**, 0 undefined references; 11 overfull hboxes (≤ 5.1 pt) and 2 overfull vboxes (5.4 pt) unchanged.
* Footer "Page i of N" equals the PDF page on every page; the title page is unnumbered.
* Table 4.2 is on p. 25 in the final build. In an earlier build of the same day it split across pp. 24–25 (heading repeated correctly): the row order of Table 4.1 follows the analysis output order, which differs between design runs; values are the same.
* Table 5.28, end-diaphragm row: the last line of the multi-line message touched the bottom rule (gap −0.01 pt); fixed with a `\strut`, gap now 2.54 pt, covered by a PDF-level test.
* `Report_Before.pdf` is the unchanged handover file (original code `d74f56d`).
