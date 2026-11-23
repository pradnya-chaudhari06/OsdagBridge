# ═══════════════════════════════════════════════════════════════════════════════
# EXECUTIVE SUMMARY
# ═══════════════════════════════════════════════════════════════════════════════
# Every status shown here is derived from the design results through
# report_data (the same data as Section 5.5 and its charts):
#   * per check      : UR = Demand / Capacity (or the module's DCR), PASS <= 1.0
#   * per component  : report_data.component_status
#   * overall bridge : report_data.design_status
# Nothing is hard-coded; missing data is reported as such, never as a pass.

from osdagbridge.core.reports.report_utils import _fig_or_placeholder, _render_value, _tex, get_girder_entries
from osdagbridge.core.reports.latex_tables import fit_colspec
from osdagbridge.core.reports.report_data import (
    STATUS_FAIL,
    STATUS_PASS,
    collect_utilization,
    consistency_notes,
    design_status,
    per_girder_governing,
)
from osdagbridge.core.utils.common import (
    KEY_CARRIAGEWAY_WIDTH,
    KEY_SD_SECTION_DESIGNATION,
    KEY_SPAN,
    KEY_STRUCTURE_TYPE,
    KEY_TS_DECK_THICKNESS,
    KEY_TS_GIRDER_SPACING,
    KEY_TS_NO_OF_GIRDERS
)


def _status_tex(status):
    """Status word, failures in red."""
    s = _tex(status)
    return r"\textcolor{red}{\textbf{" + s + "}}" if status == STATUS_FAIL else r"\textbf{" + s + "}"


def _ur_tex(ur):
    if ur is None:
        return "---"
    s = f"{ur:.2f}"
    return r"\textcolor{red}{" + s + "}" if ur > 1.0 else s


def _overall_text(comps, overall):
    """One-line overall status with the failing checks (if any)."""
    failing = [f for c in comps for f in c.failing]
    if overall == STATUS_FAIL:
        failing.sort(key=lambda i: -(i.ur or 0))
        parts = [f"{f.label}, UR {f.ur:.2f}" for f in failing[:4]]
        more = f" and {len(failing) - 4} more" if len(failing) > 4 else ""
        return _status_tex(overall) + r" --- " + _tex("; ".join(parts) + more)
    if overall == STATUS_PASS:
        return _status_tex(overall) + r" --- all checks of all components have UR $\leq$ 1.0"
    missing = [c.title for c in comps if c.status != STATUS_PASS]
    return (_status_tex(overall) + r" --- no failing check, but results are missing for: "
            + _tex(", ".join(missing)))


def _outcomes_table(comps):
    rows = []
    for c in comps:
        gov = c.governing
        check = _tex(gov.label) if gov else (_tex(c.reason) if c.reason else "No results available")
        rows.append(_tex(c.title) + " & " + _status_tex(c.status) + " & " + check + " & "
                    + _ur_tex(gov.ur if gov else None) + " & "
                    + f"{c.n_valid} of {c.n_checks}" + r" \\" + "\n" + r"\hline")
    spec = fit_colspec(r"|L{3.4cm}|C{2.4cm}|L{6.0cm}|C{1.4cm}|C{2.2cm}|")
    return (r"\noindent\begin{tabular}{" + spec + "}\n" + r"\hline" + "\n"
            r"\rowcolor{tableHeaderBg}\textbf{Component} & \textbf{Status} & "
            r"\textbf{Governing check} & \textbf{Max UR} & \textbf{Checks with data} \\" + "\n"
            + r"\hline" + "\n" + "\n".join(rows) + "\n" + r"\end{tabular}")


def executive_summary(input_dict, output_dict, fig_paths) -> str:
    plan_fig = _fig_or_placeholder(fig_paths.get('girder_top'), 'Figure 1 -- Overall Bridge Plan')
    cs_fig = _fig_or_placeholder(fig_paths.get('cross_section'),
                                  'Figure 2 -- Typical Cross-Section (with girder, deck, barriers, footpath)')
    geom_fig = _fig_or_placeholder(fig_paths.get('final_geometry'),
                                    'Figure 3 -- 3D View of Bridge Superstructure')

    # The section designation is produced by the designer pipeline, so it lives
    # in output_dict (not input_dict).
    sec = _render_value(output_dict, KEY_SD_SECTION_DESIGNATION)

    # ── Design status: one source for every component ────────────────────────
    summary = collect_utilization(input_dict, output_dict)
    comps, overall = design_status(summary)
    valid = [c.governing for c in comps if c.governing is not None]
    gov = max(valid, key=lambda i: i.ur) if valid else None
    gov_comp = next((c.title for c in comps if c.governing is gov), "") if gov else ""
    overall_status = _overall_text(comps, overall) if comps else "---"
    gov_check = (_tex(gov.label) + " --- " + _tex(gov_comp)) if gov else "---"
    overall_ur = (_ur_tex(gov.ur) + " (" + _tex(gov_comp) + ")") if gov else "---"

    notes = consistency_notes(input_dict, output_dict)
    notes_tex = ""
    if notes:
        notes_tex = (r"\section*{Data Consistency Notes}" "\n"
                     r"\addcontentsline{toc}{section}{Data Consistency Notes}" "\n"
                     r"The following inconsistencies were found in the analysis / design output. "
                     r"They are reported here as found; the report does not change engineering results." "\n"
                     r"\begin{itemize}" "\n"
                     + "\n".join(r"\item " + _tex(t) for t in notes.values()) + "\n"
                     r"\end{itemize}" "\n")

    # --- Table 1: one column per girder of the input (Chapter 2 numbering) ---
    labels = get_girder_entries(input_dict)
    if not labels:
        labels = [("", "")]
    n_cols = len(labels)

    # Column widths: row-label column fixed at 2.8cm; girder columns share remainder
    label_col_cm = 2.8
    girder_col_cm = round(max(1.5, (15.0 - label_col_cm) / n_cols), 1)
    col_spec = '|C{' + str(label_col_cm) + 'cm}|' + '|'.join(['C{' + str(girder_col_cm) + 'cm}'] * n_cols) + '|'
    # The share above ignores cell padding and rules (the table was ~1 cm
    # wider than the page for 4 girders); scale it to the real text width.
    col_spec = fit_colspec(col_spec)

    per_girder = per_girder_governing(output_dict)

    def _gcell(lbl, what):
        it = per_girder.get(lbl)
        if it is None:
            return "---"
        if what == "check":
            return _tex(it.check)
        return _ur_tex(it.ur) + (r" (\textcolor{red}{FAIL})" if it.status == "fail" else "")

    hdr_cells = ' &\n  '.join([r'\textbf{' + _tex(lbl) + '}' for lbl, _ in labels])
    header_row = r'  \textbf{} &' + '\n  ' + hdr_cells + r' \\' + '\n'
    member_id_row = 'Member ID & ' + ' & '.join([_tex(mid) for _, mid in labels]) + r' \\' + '\n'
    sections = "Section Designation & " + ' & '.join([sec or "---"] * n_cols) + r" \\"
    gov_checks = "Governing Check & " + ' & '.join(_gcell(l, "check") for l, _ in labels) + r" \\"
    urs = "Utilization Ratio (max) & " + ' & '.join(_gcell(l, "ur") for l, _ in labels) + r" \\"

    # The minipage keeps the table title on the same page as the table (the
    # title was left alone at a page bottom before).
    table1 = (r'\par\noindent\begin{minipage}{\textwidth}' + '\n'
              r'\noindent\textbf{Table 1 -- Final Bridge Geometry (after optimization)}' + '\n\n'
              r'\vspace{0.4em}' + '\n'
              r'\noindent' + '\n'
              r'\begin{tabular}{' + col_spec + '}\n'
              r'\hline' + '\n'
              + header_row +
              r'\hline' + '\n'
              + member_id_row +
              r'\hline' + '\n'
              + sections + '\n'
              r'\hline' + '\n'
              + gov_checks + '\n'
              r'\hline' + '\n'
              + urs + '\n'
              r'\hline' + '\n'
              r'\end{tabular}' + '\n'
              r'\end{minipage}')

    return r"""
\newpage
{\centering\Large\bfseries Executive Summary\par}
\addcontentsline{toc}{chapter}{Executive Summary}
\vspace{0.8em}

This section provides a concise summary of the bridge design, key inputs, governing loads, and final design outcomes.

\section*{Project Overview}
\addcontentsline{toc}{section}{Project Overview}
\label{sec:project-overview}


\begin{tabular}{|L{5.5cm}|L{8.5cm}|}
\hline
\textbf{Bridge Type} & """ + (_render_value(input_dict, KEY_STRUCTURE_TYPE)) + r""" \\
\hline
\textbf{Design Standard} & IRC 5, IRC 6, IRC 22, IRC 24, IS 800 \\
\hline
\textbf{Span} & """ + (_render_value(input_dict, KEY_SPAN, ' m')) + r""" \\
\hline
\textbf{Carriageway Width} & """ + (_render_value(input_dict, KEY_CARRIAGEWAY_WIDTH, ' m')) + r""" \\
\hline
\textbf{No. of Girders} & """ + (_render_value(input_dict, KEY_TS_NO_OF_GIRDERS)) + r""" \\
\hline
\textbf{Girder Spacing} & """ + (_render_value(input_dict, KEY_TS_GIRDER_SPACING, ' m')) + r""" \\
\hline
\textbf{Deck Thickness} & """ + (_render_value(input_dict, KEY_TS_DECK_THICKNESS, ' mm')) + r""" \\
\hline
\textbf{Overall Design Status} & """ + overall_status + r""" \\
\hline
\textbf{Governing Check} & """ + gov_check + r""" \\
\hline
\textbf{Overall Utilization Ratio (max)} & """ + overall_ur + r""" \\
\hline
\end{tabular}


""" + plan_fig + r"""

\newpage

""" + cs_fig + '\n\n' + geom_fig + '\n\n' + table1 + r"""

\vspace{0.4em}
\noindent\textit{Note: Utilization ratio (UR) = demand / capacity. UR $\leq 1.0$ passes, UR $> 1.0$ fails. Girder columns show each girder's governing check as labelled by the design module.}

\vspace{1em}

\section*{Key Design Outcomes Summary}
\addcontentsline{toc}{section}{Key Design Outcomes Summary}
\label{sec:key-outcomes}

""" + _outcomes_table(comps) + r"""

\vspace{0.4em}
\noindent\textit{Note: A component passes only when every one of its checks has valid Demand / Capacity data and UR $\leq 1.0$; a component without results is ``NOT AVAILABLE'' and is never counted as passing. Details: Section 5.5.}

""" + notes_tex + r"""
\section*{Design Assumptions and Limitations}
\addcontentsline{toc}{section}{Design Assumptions and Limitations}
\label{sec:assumptions}

\begin{itemize}
\item Additional inputs not provided by the user were assumed by software per IRC/IS code defaults or practical consideration.
\item Grillage analysis was performed using OSPGrillage assuming simply supported I-girders.
\item Substructure and foundation design are not included in this report.
\item Splice connections and bearings are not designed in this version.
\end{itemize}

% Restore numbered chapter format
\titleformat{\chapter}[block]{\normalfont\Large\bfseries\centering}{\thechapter}{1em}{}
\titlespacing*{\chapter}{0pt}{-30pt}{10pt}
"""
