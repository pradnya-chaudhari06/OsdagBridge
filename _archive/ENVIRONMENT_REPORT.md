# Environment Report

Recorded on 2026-11-21 on the development machine used for this work. No credentials, user names or machine identifiers are recorded here.

## 1. Machine and tools found at the start

| Item | Found | Notes |
|---|---|---|
| Operating system | Windows 11 Home (10.0.26200) | |
| PowerShell | 5.1 | Git Bash is also available |
| Git | 2.51.1 (Windows) | `core.autocrlf=true`: CRLF in the working tree, LF in the repository |
| Python (system) | 3.10, 3.12, 3.14 (`py` launcher) | Not used for the project, which runs in the conda env below |
| Conda | Miniconda, conda 25.11.1 | Already installed, so no installation was needed |
| VS Code | installed | |
| Claude Code | installed | |
| Node.js | installed | Not needed by the project |
| LaTeX (system-wide) | **none**: no MiKTeX, TeX Live, `pdflatex` or Tectonic on PATH | Solved by the project's own LaTeX package (see §3) |
| Free disk space (C:) | ≈ 80 GB at the start, ≈ 70 GB at the end | |

## 2. Project environment (created from the repository's own definition)

The environment was created with the project's `environment.yml`. No separate environment was invented.

```powershell
conda env create -f environment.yml
```

| Package | Version | Source |
|---|---|---|
| Python | 3.12.16 | conda-forge |
| osdag (Osdag core, GUI libraries, `osdag_latex_env`) | 0.0.0 | `osdag` channel |
| PySide6 | 6.12.0 | via osdag |
| pythonocc-core | 8.0.1.2 | via osdag (OpenCASCADE 3D CAD) |
| numpy / scipy | 2.5.5 / 1.18.1 | conda-forge |
| matplotlib | 3.11.2 | conda-forge (charts) |
| PyLaTeX | 1.4.2 | conda (pulled in by `osdag`, now also declared explicitly) |
| openseespy | 3.8.0.0 | pip (from `environment.yml`) |
| xarray / pydantic | 2026.9.0 / 2.14.4 | conda-forge |
| osdagbridge | editable install of this repository (`pip -e .`) | `environment.yml` |

**Development and test tools installed into the env with pip:** `pytest` 9.2.0 (the project's `test` extra) and `pymupdf` 2.1, used to read and render PDF pages in the tests and in the visual QA. Nothing else was installed.

Location: `%USERPROFILE%\miniconda3\envs\osdagbridge-env`

## 3. LaTeX compiler

* `pdfTeX 3.141592653-2.6-1.40.28 (TeX Live 2025)`. It ships inside the conda env as part of the `osdag_latex_env` package:
  `…\envs\osdagbridge-env\Library\share\osdag_latex_env\bin\x86_64-windows\pdflatex.exe`
* The report generator already finds it through `osdag_latex_env.OsdagLatexEnv`, so **no system-wide MiKTeX or TeX Live install was needed.**

## 4. Things a teammate must know about this environment

1. **Activate the env** (`conda activate osdagbridge-env`) before running scripts or tests. If you start the env's `python.exe` directly without activating it, Windows can't find the native DLLs in `Library\bin` and numpy/matplotlib abort with `0xc06d007f`. The desktop app works around this in `osdagbridge.desktop.__main__`. The test suite does the same in `tests/conftest.py`.
2. `PySide6 6.12.0` was installed by the `osdag` package, although `requirements.txt` says `PySide6<=6.9.3`. The application, the GUI design run and the report generation all worked with 6.12.0.
3. `src/osdagbridge.egg-info/` (from the editable install) and `src/osdagbridge/core/data/project_location/weather.sqlite` (created by the app at first start) are git-ignored build artefacts.
