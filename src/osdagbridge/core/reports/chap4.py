from typing import TYPE_CHECKING
from osdagbridge.core.utils.common import (
    KEY_SPAN,
    KEY_TS_NO_OF_GIRDERS,
    KEY_SD_DEFL_LIVE,
    KEY_SD_DEFL_TOTAL,
)
from osdagbridge.core.reports.report_utils import _tex, _fig_embed
from osdagbridge.core.reports import styles
from osdagbridge.core.reports.latex_tables import build_longtable
from osdagbridge.core.reports.report_data import consistency_notes

if TYPE_CHECKING:
    from .report_generator import ReportDataBridge

# Two-row column heading of Table "Summary of Maximum Demands" (repeated on
# every page by build_longtable).
_DEMANDS_HEADER = (
    r"\multirow{2}{*}{\makecell{\textbf{Load}\\\textbf{Case/}\\\textbf{Comb.}}}" "\n"
    r"& \multicolumn{3}{c|}{\textbf{Bending Moment}}" "\n"
    r"& \multicolumn{3}{c|}{\textbf{Shear Force}}" "\n"
    r"& \multicolumn{2}{c|}{\makecell{\textbf{Reaction at}\\\textbf{Supports}}}\\" "\n"
    r"\cline{2-9}" "\n"
    r"& \makecell{\textbf{Max}\\\textbf{(kNm)}}" "\n"
    r"& \textbf{Girder}" "\n"
    r"& \makecell{\textbf{Loc.}\\\textbf{(m)}}" "\n"
    r"& \makecell{\textbf{Max}\\\textbf{(kN)}}" "\n"
    r"& \textbf{Girder}" "\n"
    r"& \makecell{\textbf{Loc.}\\\textbf{(m)}}" "\n"
    r"& \makecell{\textbf{Left}}" "\n"
    r"& \makecell{\textbf{Right}}"
)


def _reaction_rows(rxn_summary):
    """Governing left / right support reaction over all load cases.

    Same data as the reaction columns of Table 4.1 (analysis_summary
    "reactions"); one row per support.  Governing = largest magnitude, shown
    with the solver's sign.  'Not available' if there is none.
    """
    def _best(side):
        """(load case, value, n_other_tied); ties -> alphabetically first case.

        Several load cases can give exactly the same reaction (e.g. the
        ACCIDENTAL combinations); the order of the analysis dict is not stable
        between runs, so the tie is broken by name and disclosed.
        """
        vals = []
        for lc, r in (rxn_summary or {}).items():
            try:
                v = float((r or {}).get(side))
            except (TypeError, ValueError):
                continue
            if v == v:  # not NaN
                vals.append((lc, v))
        if not vals:
            return None
        top = max(abs(v) for _, v in vals)
        tied = sorted((lc, v) for lc, v in vals if round(abs(v), 3) == round(top, 3))
        return tied[0][0], tied[0][1], len(tied) - 1

    rows = []
    for label, side in (("Left support", "left_kN"), ("Right support", "right_kN")):
        b = _best(side)
        if b is None:
            rows.append(_tex(label) + r" & \textit{Not available} & --- \\[6pt]" "\n" r"\hline")
        else:
            lc = _tex(b[0])
            if b[2]:
                lc += (r" \textit{(and " + str(b[2]) + " other load case"
                       + ("s" if b[2] > 1 else "") + " with the same value)}")
            rows.append(_tex(label) + " & " + lc + " & " + f"{b[1]:.3f}"
                        + r" \\[6pt]" "\n" r"\hline")
    return "\n".join(rows)


def _note(bridge, key):
    """Italic data-consistency note (report_data.consistency_notes) or ''."""
    text = consistency_notes(bridge.input_dict, bridge.output_dict).get(key)
    return (r"\noindent\textit{Note: " + _tex(text) + "}\n") if text else ""


def ch4_analysis(asum, fig_paths, bridge: "ReportDataBridge", span_m: float):
    lc_summary  = (asum or {}).get('load_cases', {})
    rxn_summary = (asum or {}).get('reactions',  {})

    def _is_moving(lc_name: str) -> bool:
        n = lc_name.lower()
        return "moving" in n or " pos_" in n

    lc_summary  = {k: v for k, v in lc_summary.items()  if not _is_moving(k)}
    rxn_summary = {k: v for k, v in rxn_summary.items() if not _is_moving(k)}

    def _fmt(val, nd=3):
        try:
            return f"{float(val):.{nd}f}"
        except (TypeError, ValueError):
            return r"---"

    def _merged_row(lc, bm_d, rxn_d):
        bm_d  = bm_d  or {}
        rxn_d = rxn_d or {}
        return (
            _tex(lc)                              + r" & "
            + _fmt(bm_d.get('max_bm'))           + r" & "
            + _tex(bm_d.get('bm_girder', '---')) + r" & "
            + _fmt(bm_d.get('bm_location'))      + r" & "
            + _fmt(bm_d.get('max_sf'))           + r" & "
            + _tex(bm_d.get('sf_girder', '---')) + r" & "
            + _fmt(bm_d.get('sf_location'))      + r" & "
            + _fmt(rxn_d.get('left_kN'))         + r" & "
            + _fmt(rxn_d.get('right_kN'))        + r" \\[6pt]"
        )

    all_lcs = list(lc_summary.keys()) + [k for k in rxn_summary if k not in lc_summary]

    merged_body = ("\n\\hline\n").join(
        _merged_row(lc, lc_summary.get(lc), rxn_summary.get(lc))
        for lc in all_lcs
    ) if all_lcs else r"--- & --- & --- & --- & --- & --- & --- & --- & --- \\[6pt]"

    _span_m         = float(bridge.input_dict.get(KEY_SPAN, 0) or 0)
    _allow_live_mm  = _span_m * 1000.0 / 800.0
    _allow_total_mm = _span_m * 1000.0 / 600.0

    # Find governing girder — worst (max) deflection across all girders
    try:
        n = int(bridge.input_dict.get(KEY_TS_NO_OF_GIRDERS, 1) or 1)
    except (TypeError, ValueError):
        n = 1

    _live_mm  = None
    _total_mm = None
    for _gi in range(1, n + 1):
        _l = bridge.output_dict.get(f"{KEY_SD_DEFL_LIVE}.G{_gi}")
        _t = bridge.output_dict.get(f"{KEY_SD_DEFL_TOTAL}.G{_gi}")
        if _l is not None:
            _live_mm  = max(_live_mm, float(_l))  if _live_mm  is not None else float(_l)
        if _t is not None:
            _total_mm = max(_total_mm, float(_t)) if _total_mm is not None else float(_t)

    _live_str        = f"{_live_mm:.3f} mm"  if _live_mm  is not None else "---"
    _total_str       = f"{_total_mm:.3f} mm" if _total_mm is not None else "---"
    _allow_live_str  = f"L/800 = {_allow_live_mm:.1f} mm"
    _allow_total_str = f"L/600 = {_allow_total_mm:.1f} mm"
    _live_status     = ("PASS" if _live_mm  <= _allow_live_mm  else r"\textcolor{red}{FAIL}") if _live_mm  is not None else "---"
    _total_status    = ("PASS" if _total_mm <= _allow_total_mm else r"\textcolor{red}{FAIL}") if _total_mm is not None else "---"
    return r"""
\chapter{Analysis Results}

A grillage model was used for structural analysis. The deck is idealized as a grid of elastic beam elements --- longitudinal members represent the composite steel girders with effective slab, and transverse members represent the slab or cross frames. This section summarizes the critical output from that analysis.

\vspace{1em}
\begingroup
\footnotesize
\setlength{\tabcolsep}{""" + f"{styles.TABLE['tabcolsep_dense_pt']:g}" + r"""pt}
\renewcommand{\arraystretch}{""" + f"{styles.TABLE['arraystretch_dense']:g}" + r"""}

""" + build_longtable(
    r"|>{\centering\arraybackslash}p{3.1cm}|>{\centering\arraybackslash}p{1.7cm}|>{\centering\arraybackslash}p{1.2cm}|>{\centering\arraybackslash}p{1.3cm}|>{\centering\arraybackslash}p{1.7cm}|>{\centering\arraybackslash}p{1.2cm}|>{\centering\arraybackslash}p{1.3cm}|>{\centering\arraybackslash}p{1.6cm}|>{\centering\arraybackslash}p{1.6cm}|",
    _DEMANDS_HEADER,
    merged_body + "\n" + r"\hline",
    caption=r"\textbf{Summary of Maximum Demands}",
    tabcolsep_pt=styles.TABLE["tabcolsep_dense_pt"],
) + r"""
\endgroup
""" + _note(bridge, "girder_count") + r"""

\vspace{1em}
""" + build_longtable(
    r"|>{\centering\arraybackslash}p{5.2cm}|>{\centering\arraybackslash}p{5.2cm}|>{\centering\arraybackslash}p{5.2cm}|",
    r"\textbf{Support} & \textbf{Governing Load Case} & \textbf{Governing Reaction (kN), max.\ $|R|$}",
    _reaction_rows(rxn_summary),
    caption=r"\textbf{Reactions at Supports --- Governing Values}",
) + r"""

\vspace{1em}
""" + build_longtable(
    r"|L{7cm}|p{8.5cm}|",
    r"\textbf{parameter} & \textbf{value}",
    r"""\textnormal{Deflection due to Live Load, $\delta_{LL}$} & """ + _live_str + r""" \\[6pt]
\hline
\textnormal{Allowable Live Load Deflection ($\Delta_{allow}$)} & """ + _allow_live_str + r""" \\[6pt]
\hline
\textnormal{Live Load Deflection Check Status} & """ + _live_status + r""" \\[6pt]
\hline
\textnormal{Deflection due to Total Load, $\delta_{total}$} & """ + _total_str + r""" \\[6pt]
\hline
\textnormal{Allowable Total Deflection ($\Delta_{allow}$)} & """ + _allow_total_str + r""" \\[6pt]
\hline
\textnormal{Total Load Deflection Check Status} & """ + _total_status + r""" \\[6pt]
\hline
""",
    caption=r"\textbf{Deflection Summary (Live Load \& Total Load)}",
) + r"""
""" + _note(bridge, "deflection") + r"""

\vspace{1em}
\noindent
""" + _fig_embed(fig_paths.get('bm_envelope'), 'Bending Moment Envelope (Envelope ULS): Max/min BM along span. X-axis: distance from left support (m). Y-axis: Bending Moment (kN-m).', width=r'0.75\textwidth') + r"""
""" + _fig_embed(fig_paths.get('sf_envelope'), 'Shear Force Envelope (Envelope ULS): Max/min SF along span. X-axis: distance from left support (m). Y-axis: Shear Force (kN).', width=r'0.75\textwidth') + r"""
""" + _fig_embed(fig_paths.get('defl_ll'), 'Vertical Deflection D$_y$ (1.0 LL): Maximum deflection along span. Load Case: 1.0 LL, Combination: $D_y$. Nodes shown. Isometric view.', width=r'0.75\textwidth') + r"""
"""

