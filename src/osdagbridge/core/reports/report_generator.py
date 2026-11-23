# =============================================================================
# OsdagBridge — Report Generator  
# Matches OsdagBridge expected report format:
#   • Full title page with logo
#   • Numbered TOC (Executive Summary + Chapters 1-9)
#   • Executive Summary with Project Overview table, Key Design Outcomes,
#     Figure 1/2/3, and Design Assumptions
#   • Chapter 1  Project Information
#   • Chapter 2  Input Parameters (Tables 1-7: section, bracing, shear
#                connectors, partial safety factors)
#   • Chapter 3  Loads & Load Combinations (Tables 8-14)
#   • Chapter 4  Analysis Results (Tables 15-17 + figure placeholders)
#   • Chapter 5  Design Checks (Tables 18-39, all IRC 22 / IS 800 checks)
#   • Chapter 6  Drawings & Visualizations (6 sub-sections, 8 figures)
#   • Chapter 7  Material Take-off & Quantity Summary (Table 40)
#   • Chapter 8  Design Standards & References (Table 41 + reference list)
#   • Chapter 9  References (13 entries)
# =============================================================================

# =============================================================================
# GAPS REPORT — keys used in templates with no canonical KEY_ in common.py
# =============================================================================
# GAP | Template location         | Literal key used             | Notes
# ─────────────────────────────────────────────────────────────────────────────
# 1   | Table 2.1                 | 'latitude'                   | injected from weather_data; no KEY_ yet
# 2   | Table 2.1                 | 'longitude'                  | injected from weather_data; no KEY_ yet
# 3   | Table 2.4 / Exec Summary  | 'num_lanes'                  | design lane count; NOT the UI counter
#     |                           |                              | KEY_WC_LD_LANE_TABLE_COUNT; stays GAP
# 4   | Exec Summary (Proj Ovw)   | 'overall_design_status'      | output_dict value; no KEY_ needed
# 5   | Exec Summary (Proj Ovw)   | 'governing_check'            | output_dict value; no KEY_ needed
# 6   | Exec Summary (Proj Ovw)   | 'overall_utilization_ratio'  | output_dict value; no KEY_ needed
# 7   | Exec Summary (Table 1)    | 'section_designation'        | output_dict value; no KEY_ needed
# 8   | Table 2.7 / 2.8           | ''              | no. of bracing panels; no KEY_ yet
# 9   | Table 2.8                 | ''              | ED spacing; no KEY_ yet
# 10  | Table 4.1, 4.2            | ''             | Load Cases (DL only, Seismic (EL)); ADD_BACKEND_KEY
# 11  | Table 4.1, 5.22           | ''             | Load Combinations (LC-ULS-1, LC-SLS-1); ADD_BACKEND_KEY
# 12  | Table 5.12                | ''                | tau_fn (67 MPa); PLACEHOLDER
# 13  | Table 5.20b, 5.22         | ''                 | Slenderness limits (250, 400); PLACEHOLDER
# 14  | Table 3.4, 3.5, 3.6       | 'wind_speed', 'seismic_zone' | Weather inputs; no KEY_ yet
# 15  | Table 4.1 - 4.3           | ''             | Analysis solver demands (Max BM, SF, Defl)
# 16  | Table 5.7 - 5.9           | 'stiffener_by_member'        | Stiffener capacities; no KEY_ yet
# 17  | Table 5.14 - 5.17         | ''             | Deck slab / shear connector forces
# 18  | Table 5.20 - 5.21         | ''             | Cross-bracing / Diaphragm forces
# 19  | Table 7.1                 | 'steel_girders_mt' (etc)     | All BOM quantities; no KEY_ yet
# 20  | Chapter 8                 | ''             | Standards & References; no structural KEY_
# =============================================================================

# =============================================================================
# #  | KEY_ constant used                        | Template   | Backend action needed
# ─────────────────────────────────────────────────────────────────────────────
# (All missing data cases for Chapters 1-9 resolved or moved to GAPS)
# =============================================================================

#==============================================================================
#   FLOW OF REPORT GENERATION
# ─────────────────────────────────────────────────────────────────────────────
# USER CLICKS "Generate Report" button
#        │
#        ▼
#[output_dock.py] OutputDock._on_report_clicked()
#        │  traverses UI tree to locate `cad_generator` widget
#        └──► [template_page.py] CustomWindow.open_report_dialog(cad_generator)
#                    │
#                    ├── ReportOptionsDialog(parent=self).exec()
#                    │         [report_options.py — user fills form]
#                    │         └── returns request (ReportRequest dataclass)
#                    │
#                    ├── Spawns background thread: _ReportWorker(backend, request, cad_generator)
#                    │
#                    └──► [template_page.py] _ReportWorker.run()
#                                │
#                                └──► [plategirderbridge.py] PlateGirderBridge.generate_design_report(request, cad_generator)
#                                            │
#                                            ├── self.input_dict.copy() → report_inputs
#                                            ├── dict(self.output_dict) → output_dict
#                                            │
#                                            ├──► [report_generator.py] build_report_payload(request, report_inputs, output_dict)
#                                            │           └── returns ReportPayload dataclass
#                                            │
#                                            ├── self._export_cad_figures(cad_generator)
#                                            │    └── exports 4 headless views to ResourceFiles/Images
#                                            │    └── wires paths onto payload.figures (girder_3d, etc.)
#                                            │
#                                            ├── self.build_figure_grillage() → grillage_fig (matplotlib)
#                                            ├── self.figure_to_bytes(grillage_fig) → grillage_bytes
#                                            ├──► [report_generator.py] export_grillage_figure(grillage_bytes, output_dir, file_stem)
#                                            │           └── writes grillage.png → payload.figures.grillage = path
#                                            │
#                                            └──► [report_generator.py] generate_report(payload, request)
#                                                        │
#                                                        ├── OsdagLatexEnv() → discovers pdflatex binary
#                                                        ├── Creates output_dir/assets/
#                                                        ├── Copies logos & payload figures → assets/
#                                                        ├── Calls 10 chapter functions → full_tex string
#                                                        ├── Writes full_tex to tempdir/stem.tex
#                                                        ├── subprocess.run(pdflatex) × 2 passes
#                                                        ├── shutil.copy2(tmp_pdf → output_dir/stem.pdf)
#                                                        └── returns ReportResult(pdf_path, tex_path)
#                                                                  │
#                                                                  ▼
#                                                      [template_page.py] _on_report_finished()
#                                                          if dialog.is_preview → os.startfile(pdf_path)
#                                                          else → CustomMessageBox("Report Saved")
#==============================================================================

import os, shutil, logging, datetime, tempfile, subprocess
from dataclasses import dataclass, field
from typing import Optional, List, Literal

from osdagbridge.core.utils.common import (
    KEY_DESIGN_MODE,
    KEY_SPAN,
    KEY_TL_BRIDGE_TEMP_MAX,
    KEY_TL_BRIDGE_TEMP_MIN,
    KEY_TL_HIGHEST_MAX_TEMP,
    KEY_TL_LOWEST_MIN_TEMP,
    KEY_TL_TEMP_FALL,
    KEY_TL_TEMP_RISE
)

from osdagbridge.core.reports.report_utils import _tex
from osdagbridge.core.reports import styles
from .executive_summary import executive_summary
from .chap1 import ch1_project_info
from .chap2 import ch2_input_parameters
from .chap3 import ch3_loads
from .chap4 import ch4_analysis
from .chap5 import ch5_design_checks
from .chap6 import ch6_drawings
from .chap7 import ch7_quantities
from .chap8 import ch8_design_log
from .chap9 import references

logger = logging.getLogger(__name__)

# --- TEMPLATES START ---


# =============================================================================
# LaTeX template sections for OsdagBridge Design Report
# Matches the LaTeX template used in the OsdagBridge desktop application.
# Color: osdagGreen = #91B014
# =============================================================================



# ═══════════════════════════════════════════════════════════════════════════════
# PREAMBLE
# ═══════════════════════════════════════════════════════════════════════════════

def preamble(project_name, job_number, report_date, report_version='Rev 0'):
    pn = _tex(project_name)
    jn = _tex(job_number)
    rd = _tex(report_date)
    rv = _tex(report_version)
    return r"""
\documentclass[""" + styles.TYPOGRAPHY['base_font_size'] + "," + styles.PAGE['paper'] + r"""]{""" + styles.TYPOGRAPHY['document_class'] + r"""}

% Packages
% Page geometry comes from styles.PAGE: header and footer heights are reserved
% explicitly (includehead/includefoot), so running heads/feet never overlap
% the text block.
\usepackage[""" + styles.geometry_options() + r"""]{geometry}
\usepackage{graphicx}
\usepackage{amsmath}
\usepackage{amssymb}
\usepackage{booktabs}
\usepackage{array}
\usepackage{tabularx}
\usepackage{float}
\usepackage{fancyhdr}
\usepackage[hidelinks]{hyperref}
\usepackage{xcolor}
\usepackage{setspace}
\usepackage{enumitem}
\usepackage{caption}

\captionsetup{
    labelfont=bf,
    justification=raggedright,
    singlelinecheck=false,
    format=plain
}
\usepackage{subcaption}
\usepackage{multirow}
\usepackage{colortbl}
\usepackage{longtable}
\setlength{\LTleft}{\fill}
\setlength{\LTright}{\fill}
\usepackage{titlesec}
\usepackage{titletoc}
\usepackage{lastpage}
\usepackage{makecell}
\usepackage{etoolbox}
\usepackage{needspace}

\numberwithin{table}{chapter}
\numberwithin{figure}{chapter}
% Table layout and spacing: consistent padding, row height, and longtable pre/post skips
% (values from styles.TABLE -- single source of truth)
""" + styles.latex_table_settings() + r"""

% A partial rule (\cline) is set as its own table line followed by
% \vskip-\arrayrulewidth; that glue is a legal page break, so a page could
% break right after a \cline -- in the middle of a \multirow girder group,
% pushing the group label into the footer.  Forbid a break at that point.
\makeatletter
\patchcmd{\@cline}{\noalign{\vskip-\arrayrulewidth}}{\noalign{\nobreak\vskip-\arrayrulewidth}}{}{\typeout{OsdagBridge: cline patch not applied}}
\makeatother

% Prevent (float) tables from starting at the very bottom of a page:
% if fewer than N baseline-skips remain, break to the next page first.
% NOTE: deliberately NOT applied to longtable.  A \needspace break issued
% right before a longtable is processed by longtable's own output routine,
% which then prints the "continued" foot alone on the old page and both the
% continued and the first heading on the new page.  longtable already moves
% its heading + first row to the next page when they do not fit.
\BeforeBeginEnvironment{table}{\needspace{""" + str(styles.TABLE['min_space_before_table_lines']) + r"""\baselineskip}}

% Report colours (styles.COLORS / styles.LATEX_COLOR_NAMES)
""" + styles.latex_color_definitions() + r"""

% Header / footer (styles.HEADER_FOOTER).  The optional "* Software default
% value" note is part of the footer block, inside the space reserved by
% \footskip, instead of being pulled up into the text area with a negative
% \vspace (which made it overlap the last table row of the page).
\fancypagestyle{main}{
  \fancyhf{}
  \fancyhead[L]{""" + pn + r""" $|$ """ + jn + r"""}
  \fancyhead[R]{""" + rd + r""" $|$ """ + rv + r"""}
  \fancyfoot[L]{""" + styles.HEADER_FOOTER['footer_left'] + r"""}
  \fancyfoot[R]{""" + styles.HEADER_FOOTER['footer_right'] + r"""}
  """ + styles.latex_head_rule() + r"""
  """ + styles.latex_fancy_footer_rule() + r"""
}
\fancypagestyle{plain}{
  \fancyhf{}
  \fancyhead[L]{""" + pn + r""" $|$ """ + jn + r"""}
  \fancyhead[R]{""" + rd + r""" $|$ """ + rv + r"""}
  \fancyfoot[L]{""" + styles.HEADER_FOOTER['footer_left'] + r"""}
  \fancyfoot[R]{""" + styles.HEADER_FOOTER['footer_right'] + r"""}
  """ + styles.latex_head_rule() + r"""
  """ + styles.latex_fancy_footer_rule() + r"""
}
\fancypagestyle{firstpage}{
  \fancyhf{}
  \renewcommand{\headrulewidth}{0pt}
  \fancyfoot[L]{""" + styles.HEADER_FOOTER['footer_left'] + r"""}
  % No page number printed on the title page (it is page 1; numbering
  % continues at 2 after the titlepage environment, see title_page()).
  \fancyfoot[R]{}
  \renewcommand{\footrule}{{\color{""" + styles.HEADER_FOOTER['rule_color'] + r"""}\hrule width\headwidth height """ + str(styles.HEADER_FOOTER['foot_rule_pt']) + r"""pt}\vskip """ + str(styles.HEADER_FOOTER['rule_to_text_pt']) + r"""pt}
}
\pagestyle{main}
\setstretch{""" + str(styles.TYPOGRAPHY['line_stretch']) + r"""}
\setlength{\emergencystretch}{""" + styles.TYPOGRAPHY['emergency_stretch'] + r"""}

% Custom Commands
\newcommand{\placeholder}[1]{\textit{\textless #1\textgreater}}
\newcommand{\todo}[1]{\colorbox{yellow}{TODO: #1}}
\newcolumntype{L}[1]{>{\raggedright\arraybackslash}p{#1}}
\newcolumntype{C}[1]{>{\centering\arraybackslash}p{#1}}
\newcolumntype{R}[1]{>{\raggedleft\arraybackslash}p{#1}}

% Software-default asterisk
\newcommand{\sdstar}{\textsuperscript{*}}
\newbool{hasSDonPage}
\boolfalse{hasSDonPage}
\newcommand{\markSD}{\global\booltrue{hasSDonPage}}
\renewcommand{\sdstar}{\textsuperscript{*}\markSD{}}
\AddToHook{shipout/before}{\global\boolfalse{hasSDonPage}}

\title{\Large\textbf{OsdagBridge} \\ \normalsize Open Source Software for Steel Girder Bridge Design \\ \vspace{2cm} \large Design Report}
\author{}
\date{}

\begin{document}
"""


# ═══════════════════════════════════════════════════════════════════════════════
# TITLE PAGE
# ═══════════════════════════════════════════════════════════════════════════════

def title_page(m, osdag_logo, org_logo):
    if osdag_logo:
        lhs = r'\includegraphics[width=\linewidth,keepaspectratio]{' + osdag_logo.replace('\\', '/') + r'}'
    else:
        lhs = r'\textit{(Osdag Logo)}'

    if org_logo:
        rhs = r'\includegraphics[width=\linewidth,height=2.2cm,keepaspectratio]{' + org_logo.replace('\\', '/') + r'}'
    else:
        rhs = r''

    logos_tex = r"""\noindent
\begin{minipage}[c]{0.6\textwidth}
\raggedright
""" + lhs + r"""
\end{minipage}%
\hfill
\begin{minipage}[c]{0.35\textwidth}
\raggedleft
""" + rhs + r"""
\end{minipage}
\\[1cm]
"""

    return r"""
\begin{titlepage}
\thispagestyle{firstpage}
\centering
\vspace*{1.5cm}
""" + logos_tex + r"""
{\Huge \textbf{OsdagBridge}}\\[0.3cm]
{\large Open Source Software for Steel Girder Bridge Design}\\[1.5cm]
{\Large Design Report}\\[1.5cm]
\begin{tabular}{|L{4cm}|L{10cm}|}
\hline
\textbf{Project Name} & """ + _tex(m.project_name) + r""" \\
\hline
\textbf{Project Location} & """ + _tex(m.project_location) + r""" \\
\hline
\textbf{Author / Designer} & """ + _tex(m.designer) + r""" \\
\hline
\textbf{Reviewer} & """ + _tex(m.reviewer) + r""" \\
\hline
\textbf{Organization} & """ + _tex(m.company) + r""" \\
\hline
\textbf{Client Name and Organization} & """ + _tex(m.client) + r""" \\
\hline
\textbf{Job Number} & """ + _tex(m.job_number) + r""" \\
\hline
\textbf{Date} & """ + _tex(m.report_date) + r""" \\
\hline
\textbf{Report Version} & """ + (_tex(m.subtitle) if m.subtitle else '') + r""" \\
\hline
\end{tabular}
\end{titlepage}
% The report class resets the page counter to 1 after titlepage; continue at
% 2 so that "Page X of Y" equals the PDF page number (title page = page 1,
% printed without a number) and Y equals the PDF page count.
\setcounter{page}{2}
"""


# ═══════════════════════════════════════════════════════════════════════════════
# TOC
# ═══════════════════════════════════════════════════════════════════════════════

def toc_section():
    return r"""
% Chapter / TOC Formatting
\titleformat{\chapter}[block]
  {\normalfont\Large\bfseries\centering}{\thechapter}{1em}{}
\titlespacing*{\chapter}{0pt}{0pt}{10pt}
\setcounter{tocdepth}{2}

% TOC styling using titletoc
\titlecontents{chapter}[1.5em]
  {\normalfont\vspace{2pt}}
  {\contentslabel{1.5em}}
  {\hspace*{-1.5em}}
  {\hfill\contentspage}

\titlecontents{section}[3.8em]
  {\normalfont}
  {\contentslabel{2.3em}}
  {\hspace*{-2.3em}}
  {\hfill\contentspage}

\titlecontents{subsection}[7.0em]
  {\normalfont}
  {\contentslabel{3.2em}}
  {\hspace*{-3.2em}}
  {\hfill\contentspage}

\newpage
\renewcommand{\contentsname}{\centering\Large\bfseries Table of Contents}
\tableofcontents
"""


# =============================================================================
# Chapter modules are now imported from the dedicated report submodules.
# report_generator.py remains the orchestration entry point.
# =============================================================================

# ---------------------------------------------------------------------------
# Public data-classes 
# ---------------------------------------------------------------------------

@dataclass
class ReportMetadata:
    project_name: str
    project_location: str
    designer: str
    client: str
    company: str
    group_name: str = ''
    subtitle: str = ''
    job_number: str = ''
    additional_comments: str = ''
    logo_path: Optional[str] = None
    report_date: str = ''
    reviewer: str = ''

@dataclass
class ReportOptions:
    sections: List[str]
    include_figures: bool
    include_toc: bool
    include_pdf: bool

@dataclass
class ReportRequest:
    metadata: ReportMetadata
    options: ReportOptions
    output_dir: str
    file_stem: str

@dataclass
class ReportFigures:
    plan:            Optional[str] = None
    cross_section:   Optional[str] = None
    final_geometry:  Optional[str] = None
    longitudinal_elevation: Optional[str] = None
    girder_3d:       Optional[str] = None
    girder_front:    Optional[str] = None
    girder_top:      Optional[str] = None
    girder_end:      Optional[str] = None
    bm_envelope:     Optional[str] = None
    sf_envelope:     Optional[str] = None
    defl_ll:         Optional[str] = None
    shear_connector: Optional[str] = None
    cross_bracing:   Optional[str] = None

@dataclass
class ReportPayload:
    metadata:         ReportMetadata
    options:          ReportOptions
    inputs:           dict
    analysis_summary: dict
    design_checks:    list
    figures:          ReportFigures
    log_entries:      List[str] = field(default_factory=list)
    output_dict:      dict = field(default_factory=dict)
    figure_data:      dict = field(default_factory=dict)  # {attr: bytes} — cleared after writing to tmpdir


@dataclass
class ReportResult:
    pdf_path: Optional[str]
    tex_path: Optional[str]


class ReportDataBridge:
    """Centralized data extraction for the OsdagBridge report."""



    def __init__(self, output_dict: dict, input_dict: dict, payload: "ReportPayload"):
        self.output_dict = output_dict
        self.input_dict = input_dict
        self.payload = payload


    # =====================================================================
    # CHAPTER 5: CROSS BRACING
    # =====================================================================

    def _cb_forces_dict(self) -> dict:
        """Internal: return crossbracing_forces_dict from output_dict."""
        return self.output_dict.get("crossbracing_forces_dict", {})

    def _cb_pair_designs(self) -> dict:
        """Internal: return crossbracing_design_results from output_dict."""
        return self.output_dict.get("crossbracing_design_results", {})

    def _cb_osdag(self, pair: str, member: str, force_type: str) -> dict:
        """
        Extract the _extract_osdag_summary dict for one member.
        pair      e.g. "G1-G2"
        member    "diagonal" or "chord"
        force_type "tension" or "compression"
        """
        from osdagbridge.core.bridge_types.plate_girder.results_data import _extract_osdag_summary
        try:
            raw = self._cb_pair_designs()[pair][member][force_type]
            return _extract_osdag_summary(raw or {})
        except (KeyError, TypeError):
            return {}

    def get_cb_pairs(self) -> list:
        """Return sorted list of girder pair keys e.g. ['G1-G2', 'G2-G3']."""
        try:
            return sorted(self._cb_forces_dict().get("pairs", {}).keys())
        except Exception:
            return []

    def get_cb_geometry(self) -> dict:
        """Return the geometry sub-dict from forces_dict."""
        return self._cb_forces_dict().get("geometry", {})

    def get_cb_brace_type(self) -> str:
        try:
            return self._cb_forces_dict().get("brace_type", "X")
        except Exception:
            return "X"

    # --- Table 5.20(a): Member Forces ---

    def get_cb_force(self, pair: str, member: str, force_type: str) -> str:
        """
        Return demand force string for table 5.20(a).
        member: "diagonal" or "chord"
        force_type: "tension" or "compression"
        """
        try:
            pairs = self._cb_forces_dict()["pairs"][pair]
            key = f"diag_{force_type}_kN" if member == "diagonal" else f"chord_{force_type}_kN"
            val = pairs.get(key)
            if val is not None:
                return f"{val:.3f}"
        except (KeyError, TypeError):
            pass
        return ""

    def get_cb_nature(self, pair: str, member: str) -> str:
        """Return 'T', 'C', or 'T/C' depending on what forces exist for this member."""
        try:
            pairs = self._cb_forces_dict()["pairs"][pair]
            t_key = "diag_tension_kN"     if member == "diagonal" else "chord_tension_kN"
            c_key = "diag_compression_kN" if member == "diagonal" else "chord_compression_kN"
            has_t = pairs.get(t_key) is not None
            has_c = pairs.get(c_key) is not None
            if has_t and has_c:
                return "T / C"
            if has_t:
                return "T"
            if has_c:
                return "C"
        except (KeyError, TypeError):
            pass
        return ""

    def get_cb_governing_force(self, pair: str, member: str) -> tuple:
        """
        Return (force_kN_str, force_type) for the governing (max absolute) force.
        Used as the single demand value for capacity tables.
        """
        try:
            pairs = self._cb_forces_dict()["pairs"][pair]
            t_key = "diag_tension_kN"     if member == "diagonal" else "chord_tension_kN"
            c_key = "diag_compression_kN" if member == "diagonal" else "chord_compression_kN"
            t_val = pairs.get(t_key)
            c_val = pairs.get(c_key)
            if t_val is not None and c_val is not None:
                if abs(c_val) >= abs(t_val):
                    return (f"{c_val:.3f}", "compression")
                return (f"{t_val:.3f}", "tension")
            if c_val is not None:
                return (f"{c_val:.3f}", "compression")
            if t_val is not None:
                return (f"{t_val:.3f}", "tension")
        except (KeyError, TypeError):
            pass
        return ("", "compression")

    def get_cb_section(self, pair: str, member: str, force_type: str) -> str:
        """Section designation for a member e.g. '75 x 75 x 8'."""
        val = self._cb_osdag(pair, member, force_type).get("section")
        return _tex(val) if val else ""

    def get_cb_capacity(self, pair: str, member: str, force_type: str) -> str:
        """Capacity in kN."""
        val = self._cb_osdag(pair, member, force_type).get("capacity_kN")
        return f"{float(val):.3f}" if val is not None else ""

    def get_cb_efficiency(self, pair: str, member: str, force_type: str) -> str:
        """Utilization ratio (efficiency)."""
        val = self._cb_osdag(pair, member, force_type).get("efficiency")
        return f"{float(val):.3f}" if val is not None else ""

    def get_cb_slenderness(self, pair: str, member: str) -> str:
        """KL/r — same for tension and compression (geometry-based)."""
        # Prefer compression result (slenderness is more meaningful there)
        for ft in ("compression", "tension"):
            val = self._cb_osdag(pair, member, ft).get("slenderness")
            if val is not None:
                return f"{float(val):.1f}"
        return ""

    def get_cb_status(self, pair: str, member: str, force_type: str) -> str:
        """PASS / FAIL based on UR <= 1.0."""
        try:
            val = self._cb_osdag(pair, member, force_type).get("efficiency")
            if val is not None:
                ur = float(val)
                if ur <= 1.0:
                    return r"\textcolor{black}{PASS}"
                return r"\textcolor{red}{FAIL}"
        except (TypeError, ValueError):
            pass
        return ""

    def get_cb_gov_lc(self, pair: str, member: str, force_type: str) -> str:
        """Governing load case label for member (tension or compression)."""
        try:
            pfx = "diag" if member == "diagonal" else "chord"
            key = f"{pfx}_{force_type}_gov_lc"
            val = self._cb_forces_dict()["pairs"][pair].get(key)
            return _tex(val) if val else ""
        except (KeyError, TypeError):
            return ""

    def get_cb_connection(self, pair: str, member: str, force_type: str) -> str:
        """Return 'Welded' or 'Bolted'."""
        val = self._cb_osdag(pair, member, force_type).get("connection")
        return str(val) if val else ""

    def get_cb_effective_length(self, member: str) -> str:
        """Effective length KL in mm from geometry."""
        try:
            geom = self.get_cb_geometry()
            if member == "diagonal":
                L_m = geom.get("diagonal_length_m", 0)
            else:
                L_m = geom.get("horiz_proj_m", 0)
            return f"{L_m * 1000:.0f}"   # convert m → mm
        except (TypeError, ValueError):
            return ""

    def get_cb_alpha_deg(self) -> str:
        """Diagonal angle in degrees."""
        try:
            return f"{self.get_cb_geometry().get('alpha_deg', 0):.2f}"
        except Exception:
            return ""

def _format_project_location(pl_data):
    if not pl_data:
        return ''
    if isinstance(pl_data, str):
        try:
            import ast
            pl_dict = ast.literal_eval(pl_data)
        except Exception:
            return pl_data
    elif isinstance(pl_data, dict):
        pl_dict = pl_data
    else:
        return str(pl_data)
    
    method = pl_dict.get('method')
    data = pl_dict.get('data', {})
    
    if method == 'location_name':
        dist = data.get('district', '')
        state = data.get('state', '')
        if dist and state:
            return f"{dist}, {state}"
        return dist or state or r''
    elif method == 'map':
        lat = data.get('latitude', '')
        lon = data.get('longitude', '')
        if lat and lon:
            try:
                from osdagbridge.core.bridge_types.plate_girder.ui_fields_project_location import DB_PATH
                from osdagbridge.core.data.project_location.database import Database
                db = Database(DB_PATH)
                db.connect()
                nearest = db.get_nearest_station_temperature(float(lat), float(lon))
                db.close()
                if nearest:
                    return f"{nearest['station']}, {nearest['state']}"
            except Exception as e:
                logger.warning(f"Reverse geocode error: {e}")
            return f"Lat: {lat}°, Lon: {lon}°"
        return 'Map Location'
    elif method == 'custom_data':
        return 'Custom Location Data'
    
    return str(pl_data)

# ---------------------------------------------------------------------------
# Public builder helper (unchanged signature)
# ---------------------------------------------------------------------------

def build_report_payload(request, input_dict, output_dict):
    try:
        rd  = request.metadata.report_date or datetime.date.today().isoformat()
        lp  = request.metadata.logo_path
        raw_pl = request.metadata.project_location or input_dict.get('project.location') or ''
        pl = _format_project_location(raw_pl)

        md = ReportMetadata(
            project_name  = request.metadata.project_name,
            project_location = pl,
            designer      = request.metadata.designer,
            client        = request.metadata.client,
            company       = request.metadata.company,
            group_name    = request.metadata.group_name,
            subtitle      = request.metadata.subtitle,
            job_number    = request.metadata.job_number,
            additional_comments = request.metadata.additional_comments,
            logo_path     = lp,
            report_date   = rd,
            reviewer      = getattr(request.metadata, 'reviewer', ''))

        # Inject detailed project location and weather data into input_dict dict
        try:
            import ast
            if isinstance(raw_pl, str) and '{' in raw_pl:
                pl_dict = ast.literal_eval(raw_pl)
            elif isinstance(raw_pl, dict):
                pl_dict = raw_pl
            else:
                pl_dict = {}
                
            if pl_dict and isinstance(pl_dict, dict):
                data = pl_dict.get('data', {})
                weather = pl_dict.get('weather_data', {})
                
                # We prioritize manual inputs if they exist, else we use the DB/map coordinates
                lat_val = data.get('latitude') or weather.get('latitude')
                lon_val = data.get('longitude') or weather.get('longitude')
                
                if 'latitude' not in input_dict and lat_val:
                    input_dict['latitude'] = lat_val
                if 'longitude' not in input_dict and lon_val:
                    input_dict['longitude'] = lon_val
                    
                if 'seismic_zone' not in input_dict and weather.get('zone'):
                    input_dict['seismic_zone'] = weather.get('zone')
                if 'wind_speed' not in input_dict and weather.get('wind_speed'):
                    input_dict['wind_speed'] = weather.get('wind_speed')
                if 'shade_temp_max' not in input_dict and weather.get('max_temp'):
                    input_dict['shade_temp_max'] = weather.get('max_temp')
                if 'shade_temp_min' not in input_dict and weather.get('min_temp'):
                    input_dict['shade_temp_min'] = weather.get('min_temp')
        except Exception as e:
            logger.warning(f"Failed to parse project location data: {e}")

        # ── Table 3.6 rows 3 & 4: effective bridge temp range and rise/fall ────
        # The computed keys live in output_dict (which is a snapshot of input_dict
        # at design time). Merge them into input_dict if not already present.
        for _tkey in (KEY_TL_BRIDGE_TEMP_MIN, KEY_TL_BRIDGE_TEMP_MAX,
                      KEY_TL_TEMP_RISE, KEY_TL_TEMP_FALL):
            if not input_dict.get(_tkey) and output_dict.get(_tkey):
                input_dict[_tkey] = output_dict[_tkey]

        # If still missing, compute from whatever temperature inputs are available.
        if not input_dict.get(KEY_TL_BRIDGE_TEMP_MIN):
            try:
                max_str = input_dict.get(KEY_TL_HIGHEST_MAX_TEMP) or input_dict.get('shade_temp_max')
                min_str = input_dict.get(KEY_TL_LOWEST_MIN_TEMP)  or input_dict.get('shade_temp_min')
                if max_str and min_str:
                    from osdagbridge.core.utils.codes.irc6_2017 import IRC6_2017
                    res   = IRC6_2017.cl_215_2_effective_bridge_temperature(
                                float(max_str), float(min_str), 'metallic', False)
                    t_min = res.get('T_min', 0)
                    t_max = res.get('T_max', 0)
                    mean  = (t_max + t_min) / 2.0
                    input_dict[KEY_TL_BRIDGE_TEMP_MIN] = f"{t_min:.2f}"
                    input_dict[KEY_TL_BRIDGE_TEMP_MAX] = f"{t_max:.2f}"
                    input_dict[KEY_TL_TEMP_RISE]       = f"{t_max - mean:.2f}"
                    input_dict[KEY_TL_TEMP_FALL]       = f"{mean - t_min:.2f}"
            except Exception as _te:
                logger.warning(f"Could not compute temperature values for report: {_te}")

        asum = {}
        if output_dict:
            asum = output_dict.get('analysis_summary', {})
   

        # 4) Grab Design Checks and Log
        dc = []
        le = []
        if output_dict:
            if 'design_checks' in output_dict:
                dc = output_dict['design_checks']
            if 'design_log' in output_dict:
                le = output_dict['design_log']

        # Design Log chapter content: the green (success) stage-completion lines
        # captured by the singleton logger during the most recent run.
        if not le:
            try:
                from osdagbridge.core.utils.logger import bridge_logger
                le = bridge_logger.get_success_log()
            except Exception as _le:
                logger.warning("Could not read design log from logger: %s", _le)

        return ReportPayload(metadata=md, options=request.options, inputs=input_dict,
                             analysis_summary=asum, design_checks=dc,
                             figures=ReportFigures(), log_entries=le,
                             output_dict=output_dict or {})

    except Exception as exc:
        logger.warning("build_report_payload error: %s", exc)
        return ReportPayload(
            metadata=request.metadata, options=request.options,
            inputs={}, analysis_summary={}, design_checks=[],
            figures=ReportFigures(), log_entries=[],
            output_dict={})


# ---------------------------------------------------------------------------



from osdagbridge.core.boq.boq_generator import calculate_material_quantities

# ===========================================================================
# Public entry point
# ===========================================================================

_FIGURE_MAP = [
    ('plan',                  'plan.png'),
    ('cross_section',         'cross_section.png'),
    ('final_geometry',        'final_geometry.png'),
    ('longitudinal_elevation','longitudinal_elevation.png'),
    ('girder_3d',             'girder_3d.png'),
    ('girder_top',            'girder_top.png'),
    ('section_preview',       'section_preview.png'),
    ('stiffener_preview',     'stiffener_preview.png'),
    ('cb_diagram',            'cb_diagram.png'),
    ('cb_bracing',            'cb_bracing.png'),
    ('cb_top_chord',          'cb_top_chord.png'),
    ('cb_bottom_chord',       'cb_bottom_chord.png'),
    ('ed_diagram',            'ed_diagram.png'),
    ('ed_bracing',            'ed_bracing.png'),
    ('ed_top_chord',          'ed_top_chord.png'),
    ('ed_bottom_chord',       'ed_bottom_chord.png'),
    ('bm_envelope',           'bm_envelope.png'),
    ('sf_envelope',           'sf_envelope.png'),
    ('defl_ll',               'defl_ll.png'),
]

def _build_report_charts(payload, quantities, chart_dir):
    """Create the Section 5.5 UR charts and the Chapter 7 quantity charts.

    Returns ``(ur_figures, qty_paths, qty_groups)`` where ``ur_figures`` is a
    list of ``(path, caption, note)``.  Chart problems never stop the report
    and are never silent: a chart that cannot be drawn (matplotlib missing or
    an exception while drawing) keeps its place with ``path = None``, a warning
    is logged, and the chapter prints a visible placeholder that points to the
    table holding the same values (Table 5.28 / Table 7.1).
    """
    from osdagbridge.core.reports.report_data import (
        collect_utilization, material_quantity_groups,
    )
    ur_figures, qty_paths, qty_groups = [], [], []
    try:
        from osdagbridge.core.reports.charts import quantity_chart, utilization_chart
    except Exception as exc:
        logger.warning("Report charts cannot be generated (matplotlib / chart module "
                       "unavailable: %s); placeholders are printed instead.", exc)
        quantity_chart = utilization_chart = None

    os.makedirs(chart_dir, exist_ok=True)

    try:
        summary = collect_utilization(payload.inputs, payload.output_dict)
        categories = summary.categories()
        ed_reason = summary.end_diaphragm_reason
    except Exception as exc:
        logger.warning("Utilization data could not be collected for the charts: %s", exc, exc_info=True)
        categories, ed_reason = [], ""
    for key, title, items in categories:
        note = ed_reason if (key == "end_diaphragms" and not items) else ""
        caption = r"Utilization Ratio --- " + _tex(title)
        path = os.path.join(chart_dir, f"ur_{key}.png")
        try:
            if utilization_chart is None:
                raise RuntimeError("chart module unavailable")
            utilization_chart(items, f"Utilization Ratio --- {title}".replace("---", "—"),
                              path, no_data_message=note or None)
            ur_figures.append((path.replace('\\', '/'), caption, note))
        except Exception as exc:
            logger.warning("UR chart '%s' could not be generated: %s", title, exc,
                           exc_info=utilization_chart is not None)
            ur_figures.append((None, caption, note))

    try:
        groups = material_quantity_groups(quantities)
    except Exception as exc:
        logger.warning("Material quantities could not be collected for the charts: %s", exc, exc_info=True)
        groups = []
    for i, grp in enumerate(groups):
        path = os.path.join(chart_dir, f"qty_{i + 1}.png")
        try:
            if quantity_chart is None:
                raise RuntimeError("chart module unavailable")
            quantity_chart(grp.labels, grp.values, grp.unit, grp.title, path,
                           axis_label=grp.axis_label)
            qty_paths.append(path.replace('\\', '/'))
        except Exception as exc:
            logger.warning("Quantity chart '%s' could not be generated: %s", grp.title, exc,
                           exc_info=quantity_chart is not None)
            qty_paths.append(None)
        qty_groups.append(grp)

    return ur_figures, qty_paths, qty_groups


def generate_report(payload, request):
    # type: (ReportPayload, ReportRequest) -> ReportResult
    """Compile the full OsdagBridge Design Report to PDF (+ .tex source)."""
    tex_path = None
    try:
        # Use OsdagLatexEnv to discover the bundled pdflatex path
        compiler = 'pdflatex'
        try:
            import importlib
            module = importlib.import_module('osdag_latex_env.__main__')
            latex_env = getattr(module, 'OsdagLatexEnv')()
            if latex_env.pdflatex:
                compiler = str(latex_env.pdflatex)
                # Ensure the bin directory is in PATH so subprocess can find DLLs if needed
                if latex_env.bin_dir:
                    os.environ['PATH'] = str(latex_env.bin_dir) + os.pathsep + os.environ.get('PATH', '')
        except Exception as e:
            logger.info("osdag_latex_env not found or failed to load. (%s)", e)
            
        logger.info("Compiler: %s", compiler)

        os.makedirs(request.output_dir, exist_ok=True)

        # fig_paths is built inside TemporaryDirectory (see below) after bytes are written

        pdf_path = os.path.join(request.output_dir, request.file_stem + '.pdf')
        tex_path = os.path.join(request.output_dir, request.file_stem + '.tex')

        # Write to temp dir first, compile there, then copy back
        with tempfile.TemporaryDirectory() as tmp_dir:

            # ── Write figure bytes into tmp_dir/images/ then free RAM immediately ──
            tmp_images = os.path.join(tmp_dir, 'images')
            os.makedirs(tmp_images, exist_ok=True)
            fig_paths = {}
            for attr, img_bytes in list(payload.figure_data.items()):
                if img_bytes:
                    p = os.path.join(tmp_images, attr + '.png')
                    with open(p, 'wb') as fh:
                        fh.write(img_bytes)
                    fig_paths[attr] = p.replace('\\', '/')
            payload.figure_data.clear()  # bytes no longer needed — free RAM now

            # ── Write title-page logos into tmp_dir/assets (auto-deleted) ──
            # Nothing is left next to the PDF. Latex paths are relative to tmp_dir.
            tmp_assets = os.path.join(tmp_dir, 'assets')
            os.makedirs(tmp_assets, exist_ok=True)

            osdag_logo_src = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'ResourceFiles', 'vectors', 'Osdag Logo.png')
            iit_logo_src   = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets', 'IIT Bombay Logo.png')

            osdag_logo_latex = None
            if os.path.exists(osdag_logo_src):
                shutil.copy2(osdag_logo_src, os.path.join(tmp_assets, 'osdag_logo.png'))
                osdag_logo_latex = 'assets/osdag_logo.png'

            org_logo_latex = None
            org_logo_src = payload.metadata.logo_path if (payload.metadata.logo_path and os.path.exists(payload.metadata.logo_path)) else (iit_logo_src if os.path.exists(iit_logo_src) else None)
            if org_logo_src:
                shutil.copy2(org_logo_src, os.path.join(tmp_assets, 'org_logo.png'))
                org_logo_latex = 'assets/org_logo.png'

            # Compute and inject quantities for Chapter 7
            quantities = calculate_material_quantities(payload.inputs, payload.output_dict)
            payload.inputs.update(quantities)

            # ── Charts (Section 5.5 UR charts, Chapter 7 quantity charts) ──
            # Generated from the design results into tmp_dir/images/charts, so
            # they are removed together with the temporary directory.
            ur_figures, qty_paths, qty_groups = _build_report_charts(
                payload, quantities, os.path.join(tmp_images, 'charts'))

            # ── Assemble LaTeX document (fig_paths now has tmp_dir paths) ──
            bridge = ReportDataBridge(payload.output_dict, payload.inputs, payload)
            span_m = float(payload.inputs.get(KEY_SPAN, 0) or 0)

            doc_parts = []
            doc_parts.append(preamble(payload.metadata.project_name, payload.metadata.job_number, payload.metadata.report_date, payload.metadata.subtitle or 'Rev 0'))
            doc_parts.append(title_page(payload.metadata, osdag_logo_latex, org_logo_latex))

            if payload.options.include_toc:
                doc_parts.append(toc_section())

            # Chapter inclusion is driven by the canonical section keys
            # selected in the report-options dialog (TOC). The first three
            # chapters are locked in the UI, so they are always present.
            secs = payload.options.sections

            doc_parts.append(executive_summary(payload.inputs, payload.output_dict, fig_paths))
            doc_parts.append(ch1_project_info(payload.metadata))
            doc_parts.append(ch2_input_parameters(payload.metadata, payload.inputs, payload.output_dict))

            if 'loads' in secs:
                doc_parts.append(ch3_loads(payload.inputs))
            if 'analysis' in secs:
                doc_parts.append(ch4_analysis(payload.analysis_summary, fig_paths, bridge, span_m))
            if 'design_checks' in secs:
                doc_parts.append(ch5_design_checks(payload.design_checks, bridge, ur_figures=ur_figures))
            if 'drawings' in secs and payload.options.include_figures:
                doc_parts.append(ch6_drawings(fig_paths))

            doc_parts.append(ch7_quantities(payload.inputs, chart_paths=qty_paths, chart_groups=qty_groups))

            mode = str(payload.inputs.get(KEY_DESIGN_MODE, "Optimized")).strip().lower()
            is_custom = mode in {"custom", "customized"}
        

            doc_parts.append(ch8_design_log(payload.log_entries, payload.inputs))

            doc_parts.append(references())
            doc_parts.append(r"\end{document}")

            full_tex = "\n".join(doc_parts)


            # NOTE: longtable header repetition is handled per-table in each
            # chapter file (e.g. \endfirsthead / \endhead).  No automatic
            # post-processing is applied here to avoid mis-ordering captions
            # and column headings.

            tmp_tex = os.path.join(tmp_dir, request.file_stem + '.tex')
            tmp_pdf = os.path.join(tmp_dir, request.file_stem + '.pdf')

            with open(tmp_tex, 'w', encoding='utf-8') as f:
                f.write(full_tex)

            # Compile twice for TOC and references
            for _ in range(2):
                try:
                    kwargs = {
                        'cwd': tmp_dir,
                        'stdout': subprocess.PIPE,
                        'stderr': subprocess.PIPE,
                        'check': False,
                        'env': os.environ.copy()
                    }
                    if os.name == 'nt':
                        kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW
                    
                    res = subprocess.run(
                        [compiler, '-interaction=nonstopmode', request.file_stem + '.tex'],
                        **kwargs
                    )
                except Exception as exc:
                    logger.warning(f"pdflatex run failed: {exc}")

            if os.path.exists(tmp_tex):
                shutil.copy2(tmp_tex, tex_path)
            if os.path.exists(tmp_pdf):
                shutil.copy2(tmp_pdf, pdf_path)
                # Opt-in diagnostics: OSDAGBRIDGE_REPORT_KEEP_LOG=1 keeps the
                # LaTeX log next to the PDF (used by the QA scripts/tests).
                if os.environ.get('OSDAGBRIDGE_REPORT_KEEP_LOG') == '1':
                    tmp_log = os.path.join(tmp_dir, request.file_stem + '.log')
                    if os.path.exists(tmp_log):
                        shutil.copy2(tmp_log, os.path.join(request.output_dir, request.file_stem + '.log'))
            else:
                # Keep the evidence needed for debugging next to the .tex:
                # the LaTeX log (the temporary directory is deleted on exit).
                tmp_log = os.path.join(tmp_dir, request.file_stem + '.log')
                if os.path.exists(tmp_log):
                    shutil.copy2(tmp_log, os.path.join(request.output_dir, request.file_stem + '.log'))

        if os.path.exists(pdf_path):
            logger.info("Report generated: %s", pdf_path)
            return ReportResult(pdf_path=pdf_path, tex_path=tex_path)

        logger.error("pdflatex ran but no PDF was produced.")
        if 'res' in locals():
            logger.error("pdflatex STDOUT:\n%s", res.stdout.decode('utf-8', 'ignore'))
            logger.error("pdflatex STDERR:\n%s", res.stderr.decode('utf-8', 'ignore'))
        return ReportResult(pdf_path=None, tex_path=tex_path)

    except Exception as exc:
        logger.error("generate_report failed: %s", exc, exc_info=True)
        if tex_path and os.path.exists(tex_path):
            return ReportResult(pdf_path=None, tex_path=tex_path)
        return ReportResult(pdf_path=None, tex_path=None)
