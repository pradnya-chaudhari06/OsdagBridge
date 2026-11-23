# Handover: OsdagBridge Report Generator Enhancements

This folder holds everything you need to review, test and submit the report-generator work. Nothing has been committed or pushed; you decide how to commit and where to send it.

## 1. What was implemented (short version)

| # | Requirement | Where to look |
|---|---|---|
| 1 | Repeated table headers on every page (PyLaTeX `LongTable`) | `src/osdagbridge/core/reports/latex_tables.py`; all multi-page tables in chap2/3/4/5/7 |
| 2 | Footer overlap and pagination fixed (the "G4 in the footer" bug, tables wider than the page, broken table starts) | `report_generator.py` preamble, `latex_tables.keep_multirow_groups`, `styles.PAGE` |
| 3 | Chapter 3: separate **Vehicle Live Load** and **Footway Live Load** tables from the vehicles actually ticked in the GUI | `chap3.py`, `report_data.py` |
| 4 | Section 5.5: Utilization Ratio charts for girders, deck slab, cross bracing and end diaphragms, with a red dashed UR = 1.0 line | `report_data.py`, `charts.py`, `chap5.py` |
| 5 | Chapter 7: charts for structural steel (MT), concrete (m³) and reinforcement (MT) | `boq_generator.py` (numeric output), `chap7.py`, `charts.py` |
| 6 | One central style configuration | `src/osdagbridge/core/reports/styles.py` |

Read `TECHNICAL_CHANGES.md` for the details and `FINAL_AUDIT.md` for the evidence behind each requirement.

## 2. Where things are

* **Repository:** `Desktop\OsdagBridge` (`OneDrive\Desktop\OsdagBridge` on this machine), branch `feature/report-generator-enhancements`, based on `dev` @ `d74f56dd7f22925fb8148cabf5740ed8d1e39ff3`.
* **Source:** `src/osdagbridge/core/reports/` (4 new modules, 9 modified), `src/osdagbridge/core/boq/boq_generator.py`.
* **Tests:** `tests/unit/test_report_*.py`, `tests/integration/test_report_generation.py`, `tests/conftest.py`, and the real-data fixture `tests/fixtures/demo_case_30m.json.gz`.
* **Report harness:** `scripts/report_harness/` (drives the real GUI to produce a report).
* **Deliverables:** this `submission/` folder: both PDFs, the six `.md` documents, `evidence/` (page images and the full pytest log) and `OsdagBridge_Report_Generator_Changes.patch`.

## 3. Environment

```powershell
conda env create -f environment.yml      # one time, creates "osdagbridge-env" (Python 3.12)
conda activate osdagbridge-env
pip install pytest pymupdf               # test tools (the project's "test" extra)
```

`pdflatex` comes with the env (`osdag_latex_env`, TeX Live 2025), so you don't need MiKTeX. **Always activate the env.** Running its `python.exe` without activating can crash numpy/matplotlib on Windows (DLL error `0xc06d007f`). See `ENVIRONMENT_REPORT.md`.

## 4. Run the application and make a report

```powershell
osdagbridge
```
Fill in the Input Dock (project location, span, carriageway, skew), press **Design**, then **Generate Report** in the Output Dock and **Save PDF**.

Scripted version of exactly that workflow (it opens a real window positioned off-screen, so the 3D views are captured):

```powershell
$env:HARNESS_PLATFORM = "windows"
python scripts/report_harness/generate_report_offscreen.py scripts/report_harness/sample_case.json out\Report_After.pdf
```

`sample_case.json` is a **demonstration case**: GUI defaults, 30 m span (from `examples/plate_girder/example_basic.yaml`), 7.5 m carriageway, Mumbai (Santa Cruz). The repository has no real project file. Replace these values with a real project before using the report for engineering decisions. Expect a native crash message after "report result" when the process exits; the PDF has already been written by then.

To keep the LaTeX log next to the PDF: `$env:OSDAGBRIDGE_REPORT_KEEP_LOG = "1"`.

## 5. Run the tests

```powershell
python -m pytest tests -v
```
Expected: **94 passed**. PDF-level tests skip themselves if `pdflatex` or `pymupdf` is missing.

## 6. PDFs

* `Report_Before.pdf`: original code (`d74f56d`), same workflow and inputs. Look at PDF page 31 ("Page 30 of 58"): the **G4** label sits in the footer, and the table has no repeated headings.
* `Report_After.pdf`: this branch. Compare pages 37–38 (same tables), 15–16 (live loads), 55–57 (UR charts) and 66–68 (quantity charts).

## 7. Inspect the Git changes

```powershell
git status
git diff --stat
git diff -- src/osdagbridge/core/reports/chap3.py
```
New files are untracked (`git status` lists them). `submission/` contains generated PDFs, so decide whether you want to commit it or keep it outside the commit. The patch excludes it.

## 8. What is NOT verified, or is a known limitation

* **End diaphragms:** the demo design produces no end-diaphragm forces and uses cross-bracing end diaphragms. The Section 5.5 chart and Table 5.29 therefore *say* "no data" (with the reason), and the end-diaphragm tonnage is "not available". Bars for real end-diaphragm results were not seen end to end.
* The GUI was driven programmatically through the real window code; nobody clicked through it by hand.
* **Pre-existing engineering-code defects (not changed):**
  * the IRC 6 braking-force function raises for 1–2 lanes, so the braking value shows N/A, as before;
  * the analyser ignores the vehicle checkboxes;
  * `per_girder` lists 6 girders while the input has 4.
* Intended content changes compared with the old report: the end-diaphragm summary rows no longer repeat cross-bracing values; the crash-barrier quantity was a unit bug (0.00 → 18.14 m³).
* 12 small overfull boxes (≤ 5.1 pt, inside cell padding) remain; the report grew from 59 to 73 pages.

## 9. Preparing the GitHub submission (your steps)

1. Review the diff (`git diff`, plus the untracked files).
2. Run the tests (§5) and, if you like, regenerate the PDFs (§4).
3. Commit on `feature/report-generator-enhancements`, for example:
   ```powershell
   git add src tests scripts environment.yml pyproject.toml requirements.txt
   git commit -m "Report generator: repeated headers, layout fixes, live-load tables, UR and quantity charts, central styles"
   ```
   Add `submission/` too if the reviewers want the PDFs and documents in the PR.
4. Push to your own fork and open a pull request against `Nidhikhare12/OsdagBridge` → `dev`.

Alternatively, on a clean checkout of `d74f56d`:
```powershell
git apply --check submission\OsdagBridge_Report_Generator_Changes.patch
git apply submission\OsdagBridge_Report_Generator_Changes.patch
```
