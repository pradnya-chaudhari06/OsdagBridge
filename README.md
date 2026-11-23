# OsdagBridge

OsdagBridge is a modular, shared-core software plugin for the analysis and design of steel bridges within the Osdag ecosystem.  
It supports desktop (PySide6), web (Django + React), and CLI interfaces through a unified Python core.

The system currently supports:
- Plate Girder Bridges  
 

Additional bridge types can be added through the plugin architecture.

---

## Key Features

### Shared Core Architecture
All numerical logic and I/O are implemented once in `osdagbridge.core`.  
The desktop GUI, web app, and CLI all reuse the same core for consistent behavior.

### Modular Bridge-Type System
Each bridge type includes:
- DTO (input model schema)
- Initial sizing routines
- Structural analysis configuration
- Design and code-check modules
- CAD geometry generation
- Report generation utilities

### Reusable Bridge Components
Common structural elements are defined in `bridge_components/`:
- Girders  
- Decks  
- Crash barriers  
- Pedestals  
- Piers  
- Foundations  
- Piles and pile caps  

Components are shared across multiple bridge types.

### Multi-Solver Analysis Support
Multiple analysis backends are supported:
- Native lightweight FEM solver  
- OpenSeesPy  
- OspGrillage  

Solvers are switchable at runtime via adapters.

### Integrated Indian Standards
Included under `core/utils/codes/`:
- IRC:6–2017  
- IRC:22–2015  
- IRC:24–2010  

These modules provide load models, combinations, material factors, and code checks.

---

## Project Structure

```
OsdagBridge/
├── docs/
├── examples/
├── tests/
└── src/
    └── osdagbridge/
        ├── core/              # Analysis, design, IO, solvers, codes
        ├── bridge_types/      # Plate girder, box girder, truss
        ├── bridge_components/ # Reusable components
        ├── cli/               # Command-line interface
        ├── desktop/           # PySide6 GUI
        └── web/               # Django + React web stack
```

---

## Installation

Clone the repository:

```bash
git clone https://github.com/osdag-admin/OsdagBridge.git
cd OsdagBridge
```

Install in editable mode:

```bash
pip install -e .
```

---

## Usage

### Command-Line Interface

Run an analysis:

```bash
osdagbridge analyze project.yaml --solver native
```

Generate a report:

```bash
osdagbridge report project.yaml report.pdf
```

### Desktop Application

```bash
python -m osdagbridge.desktop
```

### Web Application

Backend:

```bash
python src/osdagbridge/web/backend/manage.py runserver
```

Frontend:

```bash
cd src/osdagbridge/web/frontend
npm install
npm start
```

---

## Testing

Run the complete test suite:

```bash
pytest -q
```

Continuous integration runs automatically through GitHub Actions (`.github/workflows/ci.yml`).

---

## Design Report Generator: Tests and Report Generation (Windows)

The report generator lives in `src/osdagbridge/core/reports/`. A summary of the changes is in `deliverables/Technical_Changes.pdf`.

### 1. Environment

```powershell
conda env create -f environment.yml        # one time; creates "osdagbridge-env" (Python 3.12)
conda activate osdagbridge-env
pip install pytest pymupdf                 # test tools (pymupdf reads the generated PDFs)
```

`pdflatex` ships inside the env (`osdag_latex_env`), so no MiKTeX/TeX Live install is needed. Always activate the env: starting its `python.exe` without activation can make numpy/matplotlib fail to load their DLLs.

**Check which source tree Python imports.** The env's editable install may point to a different checkout:

```powershell
python -c "import osdagbridge, sys; print(osdagbridge.__path__)"
```

If the first path is not this folder's `src\osdagbridge`, run every command below with this folder's sources first on the path:

```powershell
$env:PYTHONPATH = "$PWD\src"
```

### 2. Run the tests

```powershell
python -m pytest tests -q
```

Expected: `163 passed` (2026-11-23). The PDF-level tests compile real LaTeX; they are skipped if `pdflatex` or `pymupdf` is missing.

### 3. Generate the design report

* **In the application:** start it with `python -m osdagbridge.desktop`, fill in the Input Dock, press **Design**, then **Generate Report** → **Save PDF**.
* **Scripted, same GUI code path.** The harness opens the real window off-screen, runs the design and generates the report. Dialogs are bypassed by code:

```powershell
$env:HARNESS_PLATFORM = "windows"
$env:OSDAGBRIDGE_REPORT_KEEP_LOG = "1"            # keep the LaTeX .log next to the PDF
$env:HARNESS_DUMP = "out\payload.pkl"             # optional: save data for fast rebuilds
python scripts/report_harness/generate_report_offscreen.py scripts/report_harness/sample_case.json out\Report_After.pdf
```

* **Rebuild from a saved payload** (no new design run):

```powershell
python scripts/report_harness/rebuild_report.py out\payload.pkl out\Report_rebuilt.pdf
```

`sample_case.json` is a **demonstration case** (GUI defaults, 30 m span), not a real project.

### 4. Known environment restrictions and GUI limitations

* The harness process crashes during Qt/OpenCASCADE teardown *after* the PDF is written (exit code `-1073741819` / 139). The PDF is complete.
* A `UnboundLocalError ... braking_force_2` traceback in the console is expected. It is an upstream IRC 6 braking-function defect for ≤ 2 lanes (D-18). It is logged, and the PDF shows "Not available" instead.
* On machines where Windows Smart App Control blocks Shiboken/PySide6 or scipy, the GUI and the harness cannot run. Do not disable security features: use the existing PDFs in `deliverables/`, and run only the tests that do not need the blocked component.
* The GUI was exercised only through the harness (programmatically), not by hand clicking.
* `requirements.txt` pins `PySide6<=6.9.3`, while `environment.yml` takes PySide6 from `osdag::osdag` (6.12.0 installed); the app ran with 6.12.0.

---

## Development Guidelines

### Key Code Locations
- Core logic: `src/osdagbridge/core/`
- Codes & standards: `src/osdagbridge/core/utils/codes/`
- Bridge types: `src/osdagbridge/bridge_types/`
- Components: `src/osdagbridge/bridge_components/`
- CLI: `src/osdagbridge/cli/`
- Desktop GUI: `src/osdagbridge/desktop/`
- Web backend/frontend: `src/osdagbridge/web/`

### Contribution Workflow
1. Fork the repository  
2. Create a feature branch  
3. Ensure all tests pass (`pytest`)  
4. Submit a pull request

---

## Acknowledgements

OsdagBridge is part of the Osdag project, promoting open-source tools for steel design education, research, and practice.

---

## License

This project is licensed under the MIT License.  
See the `LICENSE` file for full details.
