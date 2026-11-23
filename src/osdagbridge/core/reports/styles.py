# =============================================================================
# OsdagBridge Report — Centralised formatting & style configuration
# =============================================================================
# Single source of truth for every *formatting* setting used by the LaTeX
# report generator and by the matplotlib charts embedded in it.
#
#   * Page geometry (paper, margins, header / footer reservation)
#   * Typography (base size, line spacing, table / caption sizes)
#   * Colour system (brand, table header, pass / fail, chart palette)
#   * Table styling (padding, row spacing, rules, usable width)
#   * Header / footer styling
#   * Chart styling (figure size, fonts, grid, UR = 1.0 reference line)
#
# Nothing in here contains engineering data.  The module has no imports from
# the rest of osdagbridge, so any report module can import it without creating
# circular imports.
# =============================================================================

from __future__ import annotations

# -----------------------------------------------------------------------------
# Units helpers
# -----------------------------------------------------------------------------
PT_PER_CM = 28.452756          # TeX points per centimetre
CM_PER_IN = 2.54

# -----------------------------------------------------------------------------
# Page geometry
# -----------------------------------------------------------------------------
# The report is A4 with 1 inch side margins (unchanged from the original
# report).  The *vertical* geometry is now explicit: header and footer sizes are
# reserved by the geometry package instead of being left to fancyhdr defaults
# (which were too small for a 12 pt document and were compensated with
# negative \vspace hacks that pushed the footer into the text block).
PAGE = {
    "paper": "a4paper",
    "paper_width_cm": 21.0,
    "paper_height_cm": 29.7,
    "left_cm": 2.54,
    "right_cm": 2.54,
    "top_cm": 2.54,             # top of page → top of header
    "bottom_cm": 2.54,          # bottom of page → bottom of footer
    "headheight_pt": 15.0,      # fancyhdr needs >= 14.5 pt for a 12 pt font
    "headsep_pt": 14.0,         # header rule → first text line
    "footskip_pt": 42.0,        # last text baseline → footer baseline
                                # (room for the "* Software default" note line
                                #  + green rule + footer text)
    "includehead": True,
    "includefoot": True,
}


def text_width_cm() -> float:
    """Usable text width (cm) = paper width − left − right margins."""
    return PAGE["paper_width_cm"] - PAGE["left_cm"] - PAGE["right_cm"]


def geometry_options() -> str:
    """Option string for ``\\usepackage[...]{geometry}``."""
    p = PAGE
    opts = [
        p["paper"],
        f"left={p['left_cm']}cm",
        f"right={p['right_cm']}cm",
        f"top={p['top_cm']}cm",
        f"bottom={p['bottom_cm']}cm",
        f"headheight={p['headheight_pt']}pt",
        f"headsep={p['headsep_pt']}pt",
        f"footskip={p['footskip_pt']}pt",
    ]
    if p["includehead"]:
        opts.append("includehead")
    if p["includefoot"]:
        opts.append("includefoot")
    return ", ".join(opts)


# -----------------------------------------------------------------------------
# Typography
# -----------------------------------------------------------------------------
TYPOGRAPHY = {
    "base_font_size": "12pt",       # \documentclass option
    "document_class": "report",
    "font_package": "",             # "" → LaTeX default (Computer Modern), unchanged
    "line_stretch": 1.15,           # \setstretch
    # extra stretch TeX may use before letting a line overflow (fewer
    # overfull lines in narrow table cells and lists)
    "emergency_stretch": "3em",
    "table_font": r"\normalsize",   # font switch used inside generated tables
    "caption_label_font": "bf",     # caption package labelfont
    "footer_note_font": r"\footnotesize\itshape",
    "header_font": r"\normalsize",
    "continued_note_font": r"\footnotesize\itshape",
}

# -----------------------------------------------------------------------------
# Colour system (hex, without '#')
# -----------------------------------------------------------------------------
COLORS = {
    "primary": "91B014",            # osdagGreen (brand colour, rules)
    "secondary": "4D5B23",          # dark olive (headings in charts)
    "accent": "1F77B4",             # accent blue
    "table_header_bg": "EEF3DC",    # very light tint of osdagGreen
    "table_rule": "000000",
    "text": "000000",
    "muted": "6B6B6B",
    "pass": "2E8B57",               # sea green → UR <= 1.0
    "fail": "C62828",               # red       → UR  > 1.0
    "no_data": "9E9E9E",            # grey      → missing / invalid data
    "reference_line": "D32F2F",     # red dashed line at UR = 1.0
}

# LaTeX colour names defined in the preamble (name → COLORS key)
LATEX_COLOR_NAMES = {
    "osdagGreen": "primary",
    "osdagSecondary": "secondary",
    "osdagAccent": "accent",
    "tableHeaderBg": "table_header_bg",
    "passGreen": "pass",
    "failRed": "fail",
    "mutedGrey": "muted",
}

# Chart palette for categories (structural steel / concrete / rebar etc.)
CHART_PALETTE = ["4E79A7", "F28E2B", "76B7B2", "59A14F", "EDC948", "B07AA1",
                 "FF9DA7", "9C755F", "BAB0AC", "E15759"]


def hex_color(key: str) -> str:
    """Return a matplotlib-ready colour ('#RRGGBB') from COLORS."""
    return "#" + COLORS[key]


def palette(n: int) -> list:
    """First *n* palette colours as '#RRGGBB' (cycled if n > palette size)."""
    return ["#" + CHART_PALETTE[i % len(CHART_PALETTE)] for i in range(max(n, 0))]


# -----------------------------------------------------------------------------
# Table styling
# -----------------------------------------------------------------------------
TABLE = {
    "tabcolsep_pt": 6.0,            # horizontal cell padding (each side)
    "arraystretch": 1.12,           # row-height multiplier
    # Local (grouped) overrides for wide tables with many columns:
    "tabcolsep_compact_pt": 3.5,    # Table 7.1 (BOM), Chapter 8 code tables
    "tabcolsep_dense_pt": 3.0,      # Table 4.1 (9 columns, footnotesize)
    "arraystretch_dense": 1.25,     # Table 4.1 row height
    "extrarowheight_pt": 0.6,
    "arrayrulewidth_pt": 0.5,       # border thickness
    "row_pad": "6pt",               # extra space after each body row (\\[6pt])
    "lt_pre_pt": 0.0,               # space above a longtable
    "lt_post_pt": 6.0,              # space below a longtable
    "header_bold": True,
    "header_bg": True,              # shade header rows with tableHeaderBg
    "continued_caption_suffix": " (continued)",
    "continued_footer_text": "Continued on next page",
    # Space that must be left on the page before a float `table` may start;
    # if less remains, it starts on the next page (needspace).  Not used for
    # longtable, which handles its own page breaks (see report_generator).
    "min_space_before_table_lines": 5,
    # longtable processes rows in chunks; the boundary between two chunks is
    # always a legal page break, which can split a \multirow group.  A large
    # chunk keeps the "no break inside a girder group" rule effective.
    "lt_chunksize": 1000,
    # Safety margin (cm) kept free when fitting column widths to \textwidth.
    "width_safety_cm": 0.05,
}


def table_overhead_cm(n_cols: int, n_vrules: int | None = None,
                      tabcolsep_pt: float | None = None) -> float:
    """Width (cm) consumed by cell padding and vertical rules for *n_cols*."""
    if n_vrules is None:
        n_vrules = n_cols + 1
    sep = TABLE["tabcolsep_pt"] if tabcolsep_pt is None else tabcolsep_pt
    pad = 2 * sep * n_cols
    rules = TABLE["arrayrulewidth_pt"] * n_vrules
    return (pad + rules) / PT_PER_CM


def available_column_width_cm(n_cols: int, n_vrules: int | None = None,
                              tabcolsep_pt: float | None = None) -> float:
    """Sum of p{} widths (cm) that fits exactly inside the text width."""
    return (text_width_cm() - table_overhead_cm(n_cols, n_vrules, tabcolsep_pt)
            - TABLE["width_safety_cm"])


# -----------------------------------------------------------------------------
# Header & footer
# -----------------------------------------------------------------------------
HEADER_FOOTER = {
    "rule_color": "osdagGreen",
    "head_rule_pt": 1.0,
    "foot_rule_pt": 1.0,
    "footer_left": r"Osdag $|$ FOSSEE $|$ Indian Institute of Technology Bombay",
    "footer_right": r"Page \thepage\ of \pageref{LastPage}",
    "software_default_note": r"* Software default value",
    # vertical gap between the note line and the green footer rule
    "note_to_rule_pt": 2.0,
    # vertical gap between the green rule and the footer text
    "rule_to_text_pt": 4.0,
}

# -----------------------------------------------------------------------------
# Figures in the PDF
# -----------------------------------------------------------------------------
FIGURES = {
    "chart_width": r"0.95\textwidth",
    "chart_width_narrow": r"0.80\textwidth",
    "placement": "H",
}

# -----------------------------------------------------------------------------
# Chart (matplotlib) styling
# -----------------------------------------------------------------------------
CHART = {
    "dpi": 200,
    "figsize_in": (7.2, 3.8),        # width, height in inches
    "figsize_tall_in": (7.2, 4.6),
    "font_family": "DejaVu Sans",
    "title_size": 11,
    "label_size": 10,
    "tick_size": 8.5,
    "legend_size": 8.5,
    "annotation_size": 7.5,
    "grid": True,
    "grid_axis": "y",
    "grid_color": "#D9D9D9",
    "grid_linestyle": "-",
    "grid_linewidth": 0.6,
    "bar_width": 0.7,
    "bar_edge_color": "#333333",
    "bar_edge_width": 0.5,
    "ref_line_value": 1.0,
    "ref_line_color": "#" + COLORS["reference_line"],
    "ref_line_style": "--",
    "ref_line_width": 1.4,
    "ref_line_label": "UR = 1.0 (limit)",
    "ur_axis_label": "Utilization Ratio (Demand / Capacity)",
    "max_label_chars": 28,
    "tick_rotation": 30,
    "tick_rotation_dense": 60,       # used when a chart has more than 10 bars
    "tight_pad": 0.4,
}


def matplotlib_rc() -> dict:
    """rcParams applied (inside a context manager) to every report chart."""
    c = CHART
    return {
        "font.family": "sans-serif",
        "font.sans-serif": [c["font_family"], "Arial", "Helvetica"],
        "font.size": c["label_size"],
        "axes.titlesize": c["title_size"],
        "axes.labelsize": c["label_size"],
        "xtick.labelsize": c["tick_size"],
        "ytick.labelsize": c["tick_size"],
        "legend.fontsize": c["legend_size"],
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.edgecolor": "#333333",
        "axes.linewidth": 0.8,
        "savefig.dpi": c["dpi"],
        "figure.dpi": 100,
    }


# -----------------------------------------------------------------------------
# LaTeX snippets generated from the settings above
# -----------------------------------------------------------------------------
def latex_color_definitions() -> str:
    """``\\definecolor`` lines for every named report colour."""
    return "\n".join(
        rf"\definecolor{{{name}}}{{HTML}}{{{COLORS[key]}}}"
        for name, key in LATEX_COLOR_NAMES.items()
    )


def latex_table_settings() -> str:
    """Global table spacing / rule lengths for the preamble."""
    t = TABLE
    return "\n".join([
        rf"\setlength{{\tabcolsep}}{{{t['tabcolsep_pt']}pt}}",
        rf"\renewcommand{{\arraystretch}}{{{t['arraystretch']}}}",
        rf"\setlength{{\LTpre}}{{{t['lt_pre_pt']}pt}}",
        rf"\setlength{{\LTpost}}{{{t['lt_post_pt']}pt}}",
        rf"\setlength{{\arrayrulewidth}}{{{t['arrayrulewidth_pt']}pt}}",
        rf"\setlength{{\extrarowheight}}{{{t['extrarowheight_pt']}pt}}",
        rf"\setcounter{{LTchunksize}}{{{t['lt_chunksize']}}}",
    ])


def latex_fancy_footer_rule() -> str:
    """Footer rule that prints the optional "* Software default value" note.

    The note is typeset *inside the space reserved by \\footskip* (above the
    green rule) instead of being pulled upwards with a negative \\vspace,
    which previously made it overlap the last line / table row of the page.
    """
    hf = HEADER_FOOTER
    return (
        r"\renewcommand{\footrule}{%" "\n"
        r"    \ifbool{hasSDonPage}{%" "\n"
        r"      \hbox to \headwidth{" + TYPOGRAPHY["footer_note_font"]
        + r"\textcolor{black}{" + hf["software_default_note"] + r"}\hfil}%" "\n"
        rf"      \vskip {hf['note_to_rule_pt']}pt%" "\n"
        r"    }{}%" "\n"
        rf"    {{\color{{{hf['rule_color']}}}\hrule width\headwidth height {hf['foot_rule_pt']}pt}}%" "\n"
        rf"    \vskip {hf['rule_to_text_pt']}pt%" "\n"
        r"  }"
    )


def latex_head_rule() -> str:
    hf = HEADER_FOOTER
    return (rf"\renewcommand{{\headrule}}{{{{\color{{{hf['rule_color']}}}"
            rf"\hrule width\headwidth height {hf['head_rule_pt']}pt}}}}")
