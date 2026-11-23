# Manual GUI Check (hand-clicked)

This is the one check that hasn't been done yet: generating the report by **clicking through the real GUI by hand**. The reference report, `deliverables/Report_After.pdf` (75 pages, 2026-11-23), was produced by driving the same GUI classes from code with dialogs bypassed.

* **Expect small page shifts.** Page numbers below are from that reference. Table 4.1 lists load cases in the order the analysis returns them, which can change between design runs (values are the same), so later pages can shift by about one page.
* **The date will differ.** The running-head date is the day you generate the report.

| # | Do | Look for |
|---|---|---|
| 1 | In PowerShell, in the repo folder: `conda activate osdagbridge-env`, then `python -c "import osdagbridge.core.reports.report_data as r; print(r.__file__)"` | The printed path is inside this repo (`...\Desktop\OsdagBridge\src\...`). If it isn't, stop: the env runs another copy. |
| 2 | `python -m osdagbridge.desktop` | The main window opens. **If it crashes or closes immediately,** copy the console text and stop (no report can be produced). |
| 3 | Input Dock: **City in India**: Maharashtra → Mumbai(Bombay) (Santa Cruz); **Span (m)** 30; **Carriageway Width (Each way) (m)** 7.5; **Skew Angle (deg)** 0. Leave everything else at its default. | These are the demonstration inputs of `scripts/report_harness/sample_case.json`. |
| 4 | Click **Design**; wait for it to finish (about 1–2 minutes). | The Output Dock fills with results. (Not observed by hand before: note any dialog that appears. The demo design does fail two checks, so a warning about them would not be a fault.) **On an error dialog,** note its text and stop. |
| 5 | Click **Generate Report** (Output Dock). In the options dialog: Project Name `OsdagBridge Demonstration Case (30 m span)`, Job Number `DEMO-30`, Report Version `Rev 0`; keep all sections ticked. Click **Save PDF** and choose a file name. | A PDF is written. A `UnboundLocalError … braking_force_2` line in the console is expected (upstream defect D-18, logged on purpose). |
| 6 | Open the PDF. Check the page count and the footers. | About 75 pages. Page 1 (title) has no page number; every other page reads "Page i of N", with i equal to the PDF page number. |
| 7 | **p. 3** Executive Summary; **p. 6** Key Design Outcomes | "Overall Design Status **FAIL**", naming Fatigue Normal Stress (UR 1.58) and an intermediate-stiffener check (UR 1.48). Deck PASS 0.94, Cross Bracing PASS 0.74, End Diaphragms NOT AVAILABLE. |
| 8 | **p. 12** Table 2.7 | Girder dimensions in mm (1670 / 10 / 510 / 22), not "1.67 mm". |
| 9 | **pp. 16–17** Table 3.3; **p. 17** Table 3.4 | The vehicles listed are exactly those ticked in Additional Inputs → Loading (defaults). Braking row: "Not available — … returns no value for 2 design lanes (known upstream defect D-18)." Centrifugal row: "Not applicable (straight bridge) …". Table 3.4 says no footpath. No Python text anywhere. |
| 10 | **pp. 21–25** Tables 4.1–4.3 (Table 4.2 on p. 25 in the reference; in another run it may split across pp. 24–25); **p. 40** Table 5.6 (continued), G4 group | Each continuation page starts with "Table X (continued)" and the column heading. No table text in or under the footer line. The G4 rows stay together on one page. On p. 57, the last line of the "End Diaphragm" row in Table 5.28 does not touch the rule below it. |
| 11 | **pp. 56–59** Table 5.28 and Figures 5.1–5.4 | Red dashed line at UR = 1.0 in every chart; two red hatched bars in Figure 5.1 (1.58, 1.48). Figure 5.4 is a framed panel stating "No design results available" with the reason (no end-diaphragm member forces). |
| 12 | **pp. 67–70** Table 7.1 and Figures 7.1–7.3 | Girders 36.46 MT, cross bracing 0.47 MT, end diaphragms "not available" (one-line note under Figure 7.1; N.A. in Table 7.1). Concrete 63.00 m³ deck and 18.14 m³ crash barriers. Reinforcement 7.56 MT. |

**Optional automated check** on your PDF, from the handover's `evidence/logs` folder:

```powershell
python footer_clearance.py <your.pdf>
python head_order.py <your.pdf>
```

Expected: `overlapping_pages=0` and `misplaced continued headings: 0`.

**Report back:**
* **If it works:** the PDF page count and any difference from the reference.
* **If it fails:** the console text and the step number.
