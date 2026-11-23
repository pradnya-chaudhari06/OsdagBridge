from osdagbridge.core.reports import styles
from osdagbridge.core.reports.latex_tables import build_longtable, format_row
from osdagbridge.core.reports.report_utils import _tex, chart_figure_or_placeholder

# (row number, description, BOQ key prefix) — Table 7.1 rows, in print order.
_BOM_ROWS = [
    ("1",    r"Structural Steel (IS 2062) for Girders", "steel_girders"),
    ("2(a)", r"Cross Bracing - Top Chord",              "bracing_top"),
    ("2(b)", r"Cross Bracing - Bottom Chord",           "bracing_bot"),
    ("2(c)", r"Cross Bracing - Diagonal Chord",         "bracing_diag"),
    ("3",    r"End Diaphragms",                         "end_diaphragm"),
    ("4",    r"Concrete (M40) for Deck Slab",           "concrete_deck"),
    ("5",    r"Reinforcement Steel (Fe 500)",           "rebar_deck"),
    ("6",    r"Shear Stud Connectors",                  "shear_studs"),
    ("7",    r"Crash Barrier",                          "crash_barrier"),
]
_BOM_COLUMNS = ("vol_formula", "qty", "vol_total", "wt_single", "wt_total")


def _bom_rows(input_dict):
    rows = []
    for sn, desc, prefix in _BOM_ROWS:
        cells = [sn, desc] + [str(input_dict.get(f"{prefix}_{c}", "N.A.")) for c in _BOM_COLUMNS]
        rows.append(format_row(cells, row_pad=""))
    return "\n".join(rows)


BOM_LABEL = "tab:bill-of-materials"   # Table 7.1, cited by chart placeholders


def _chart_figure(path, caption, notes):
    """Embed one quantity chart (PNG produced by charts.quantity_chart), or a
    visible placeholder citing Table 7.1 when the chart could not be drawn."""
    note_tex = ""
    if notes:
        note_tex = (r"\par\vspace{2pt}{\footnotesize\itshape "
                    + r" ".join(_tex(n) for n in notes) + r"}")
    return chart_figure_or_placeholder(path, caption, BOM_LABEL,
                                       styles.FIGURES["chart_width_narrow"],
                                       styles.FIGURES["placement"], note_tex)


def ch7_quantities(input_dict, chart_paths=None, chart_groups=None):
    """Chapter 7 — Material Take-off & Quantity Summary.

    ``chart_paths`` / ``chart_groups`` (optional) are the quantity charts built
    by the report generator from the same BOQ numbers printed in Table 7.1.
    """
    table = build_longtable(
        r"|C{1.0cm}|L{3.8cm}|C{2.6cm}|C{1.8cm}|C{1.8cm}|C{1.8cm}|C{1.8cm}|",
        ["S.N.", "Item Description", "Volume", "Quantity", "Total Volume",
         "Weight (MT)", "Total Weight (MT)"],
        _bom_rows(input_dict),
        caption=r"\textbf{Bill of Materials (Steel, Concrete, and Reinforcement Quantities)}",
        label=BOM_LABEL,
        tabcolsep_pt=styles.TABLE["tabcolsep_compact_pt"],
    )

    charts = ""
    if chart_groups:   # also when every chart failed (paths None -> placeholders)
        parts = [
            r"\section{Material Quantity Charts}" "\n"
            r"The charts below are generated from the quantities in the Bill of Materials "
            r"above. Each material is shown in its own unit (structural and reinforcement "
            r"steel in metric tonnes, concrete in m\textsuperscript{3}); quantities that "
            r"could not be computed are marked \emph{not available}." "\n"
        ]
        paths = list(chart_paths or []) + [None] * (len(chart_groups) - len(chart_paths or []))
        for path, grp in zip(paths, chart_groups):
            parts.append(_chart_figure(path, _tex(grp.title) + " (" + _tex(grp.unit) + ")",
                                       grp.notes))
        charts = "\n".join(parts)

    return r"""
\chapter{Material Take-off \& Quantity Summary}
\label{ch:material-takeoff}

\begingroup
\setlength{\tabcolsep}{""" + f"{styles.TABLE['tabcolsep_compact_pt']:g}" + r"""pt}
""" + table + r"""
\endgroup
""" + charts
