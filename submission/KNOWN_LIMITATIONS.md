# Known Limitations

Each item is classified as one of:
* **Blocked by missing data**: the report code is ready, but the design pipeline does not provide the data.
* **Requires engineering verification**: an issue in the analysis/design modules. It is disclosed in the report, not changed.
* **Not verified end to end**: the feature is covered by unit tests only.
* **Accepted**: cosmetic or by design.

## Requirements engineering verification (upstream analysis and design modules)

All of these are disclosed in the Executive Summary "Data Consistency Notes" and next to the affected tables. Details: `DEFECT_REGISTER.md`.

| ID | Issue | Effect in the report |
|---|---|---|
| D-04 | `_run_dcr_checks` does not pass `edge_dist`, so the deck-edge grillage lines are designed as girders: **6 design members (G1–G6) for a 4-girder bridge** | Section 5 results are labelled G1–G6; note under Table 4.1 and in Chapter 5 |
| D-05 | Cross-bracing spacing: the input is 15 m, but the design and bracing-force modules use a 3 m default (also the LTB unbraced length) | Note under Table 2.9 and in Chapter 5 |
| D-06 | The grillage analysis uses the stored section (A = 349.2 cm²); the IRC 22 checks use the designed section (A = 387.0 cm²) | Note in Chapter 5 |
| D-17 | Two deflection calculations disagree: 19.4 / 51.2 mm (Table 4.3, total FAIL) vs 9.63 / 22.87 mm (IRC 22 check, PASS) | Note under Table 4.3 |
| D-18 | `IRC6_2017.cl_211_2_braking_force` raises `UnboundLocalError` for 1–2 lanes | Braking value "Not available" with a one-sentence reason naming D-18 (Table 3.3). Not patched: treating the missing term as 0 could understate the force |
| D-19 | The analyser uses IRC 6 Table 6A vehicles regardless of the GUI vehicle checkboxes | Table 3.3 lists the user's selection, as required; the analysis may have used other vehicles |

## Blocked by missing data

* **End-diaphragm UR chart (R4).** The demo analysis returns no end-diaphragm forces, so `end_diaphragm_design_results` is empty. Figure 5.4 is a framed panel (axes and red dashed UR = 1.0 line kept) with the reason, and Table 5.28 states it too. Bars from real Osdag member results are covered by a unit test only. Rolled/welded-beam end diaphragms never get a UR: the pipeline does not design them.
* **End-diaphragm tonnage (R5).** The demo uses cross-bracing-type end diaphragms, whose member lengths are not in the design output, so the tonnage is "not available" (one-line note under Figure 7.1; N.A. in Table 7.1). Rolled-beam end-diaphragm tonnage is unit-tested only.
* **Seismic forces (Table 3.6).** The pipeline stores no seismic force values; the report says "Not available".
* **Centrifugal force (Table 3.3).** Shown as "Not applicable (straight bridge)". This is a decision from the code, not a statement of the pipeline: OsdagBridge has no plan-curvature input and builds the grillage straight in plan, and IRC 6 Cl. 212 applies to bridges on a horizontal curve. If a curvature input is added, the row falls back to "Not available - not computed by the design pipeline".

## Not verified end to end

* Only one design case (the demonstration case) was run through the GUI workflow. Other vehicle and footway combinations, a design that passes everywhere, and Customized design mode are covered by unit tests with real fixture data plus modified inputs.
* The GUI was driven programmatically through the real window classes. The modal dialogs (report options `exec`, file picker, message boxes) were replaced by code. Nobody clicked through it by hand, and the window was not watched on screen.
* The harness process segfaults during Qt/OpenCASCADE teardown, *after* the PDF is written (exit code 139). This was not investigated further. The application itself was not changed.

## Accepted (cosmetic or by design)

* 11 overfull hboxes (≤ 5.1 pt, single long words in narrow cells, inside the cell padding) and 2 overfull vboxes (5.4 pt) on Table 4.1 pages; footer clearance is still ≥ 21.9 pt on every page.
* The report grew from 59 to 75 pages: charts, two live-load tables, girder groups kept on one page, `\clearpage` before Sections 5.1 and 5.5. Some pages end with white space.
* The row order of Table 4.1 follows the analysis output order, which can differ between design runs; the values are the same. Tie-breaking in Table 4.2 is deterministic (D-20). Because the Table 4.1 length on the last page varies, Table 4.2 may or may not split across a page (it did in one 2026-11-23 build, pp. 24–25, with a repeated heading; in the final build it is on p. 25 only). Page numbers quoted in the docs can therefore shift by about one page between runs.
* The demonstration input is not a real project; the repository contains none.
* If chart generation fails (for example, matplotlib is missing), each affected figure is replaced by a framed placeholder "Chart could not be generated; values are in Table 5.28 / 7.1" and a warning is logged (fixed 2026-11-22, tested).
* Pre-existing static-analysis warnings in untouched code (unused imports or variables in chapter modules, f-strings without placeholders) were left alone. The warnings introduced by this work were removed.
* `requirements.txt` pins `PySide6<=6.9.3`, while the conda env installs 6.12.0 (it works).

## Environment (2026-11-23)

* The conda env's editable install pointed at another copy (`D:\Int\OsdagBridge\src`). It was reinstalled offline from this repo (`pip install -e . --no-deps --no-build-isolation --no-index`); `pip show osdagbridge` now reports this repo. The `D:\Int` files were not touched, but this env no longer runs them.
* The hand-clicked GUI workflow has not been run; `submission/MANUAL_GUI_CHECK.md` lists the steps for doing it.
