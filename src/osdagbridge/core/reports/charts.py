r"""Matplotlib chart helpers for the report (UR bars and material quantities).

Uses the object-oriented Agg API (no pyplot), so it is safe in the GUI's
worker thread. Every function returns the saved path, or None when there is
no numeric data to plot (the caller then skips the figure).
"""
import re
import textwrap

from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure

from . import styles


def to_float(v):
    """Number from a value or a string such as '12.5 kN' or '1,250'; None if absent or 'N.A.'."""
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v) if v == v else None
    m = re.search(r"-?\d+(?:\.\d+)?", str(v).replace(",", ""))
    return float(m.group()) if m else None


def _new_fig(ncols=1):
    fig = Figure(figsize=styles.CHART_FIGSIZE)
    FigureCanvasAgg(fig)
    axes = fig.subplots(1, ncols) if ncols > 1 else [fig.add_subplot(111)]
    for ax in axes:
        ax.tick_params(labelsize=styles.CHART_FONT_SIZE)
        ax.grid(axis="y", linestyle=":", alpha=0.5)
        ax.set_axisbelow(True)
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
    return fig, axes


def _save(fig, path):
    fig.savefig(path, dpi=styles.CHART_DPI, bbox_inches="tight")
    return path


def _wrap(label, width=14):
    return textwrap.fill(str(label), width)


def ur_bar_chart(items, out_path, title=None):
    """items: [(label, UR)]. Red dashed line at UR = 1.0; bars above 1.0 are red."""
    pts = [(l, to_float(u)) for l, u in items]
    pts = [(l, u) for l, u in pts if u is not None]
    if not pts:
        return None
    fig, (ax,) = _new_fig()
    labels = [_wrap(l) for l, _ in pts]
    urs = [u for _, u in pts]
    colors = [styles.CHART_FAIL_COLOR if u > 1.0 else styles.CHART_OK_COLOR for u in urs]
    bars = ax.bar(labels, urs, color=colors, width=0.55)
    ax.axhline(1.0, color=styles.CHART_LIMIT_COLOR, linestyle="--", linewidth=1.4,
               label="UR = 1.0")
    for b, u in zip(bars, urs):
        ax.text(b.get_x() + b.get_width() / 2, u, f"{u:.2f}", ha="center",
                va="bottom", fontsize=styles.CHART_FONT_SIZE)
    ax.set_ylim(0, max(1.2, max(urs) * 1.15))
    ax.set_ylabel("Utilization ratio (demand / capacity)", fontsize=styles.CHART_FONT_SIZE)
    ax.legend(loc="upper right", fontsize=styles.CHART_FONT_SIZE - 1)
    if title:
        ax.set_title(title, fontsize=styles.CHART_FONT_SIZE + 1)
    return _save(fig, out_path)


def quantity_bar_chart(items, ylabel, out_path, title=None, color=None):
    """items: [(label, value)] in one unit. Entries without a number are skipped."""
    pts = [(l, to_float(v)) for l, v in items]
    pts = [(l, v) for l, v in pts if v is not None]
    if not pts:
        return None
    fig, (ax,) = _new_fig()
    bars = ax.bar([_wrap(l, 16) for l, _ in pts], [v for _, v in pts],
                  color=color or styles.CHART_STEEL_COLOR, width=0.5)
    top = max(v for _, v in pts)
    for b, (_, v) in zip(bars, pts):
        ax.text(b.get_x() + b.get_width() / 2, v, f"{v:,.2f}", ha="center",
                va="bottom", fontsize=styles.CHART_FONT_SIZE)
    ax.set_ylim(0, top * 1.15 if top > 0 else 1)
    ax.set_ylabel(ylabel, fontsize=styles.CHART_FONT_SIZE)
    if title:
        ax.set_title(title, fontsize=styles.CHART_FONT_SIZE + 1)
    return _save(fig, out_path)


def concrete_rebar_chart(vol, vol_unit, wt, wt_unit, out_path, title=None):
    """Concrete volume and reinforcement weight in two panels (different units)."""
    v, w = to_float(vol), to_float(wt)
    if v is None and w is None:
        return None
    fig, axes = _new_fig(2)
    for ax, label, val, unit, col in (
        (axes[0], "Concrete (deck slab)", v, vol_unit, styles.CHART_CONCRETE_COLOR),
        (axes[1], "Reinforcement steel", w, wt_unit, styles.CHART_REBAR_COLOR),
    ):
        if val is None:
            ax.text(0.5, 0.5, "N.A.", ha="center", va="center", transform=ax.transAxes)
            ax.set_xticks([])
            ax.set_yticks([])
            continue
        ax.bar([_wrap(label, 16)], [val], color=col, width=0.4)
        ax.text(0, val, f"{val:,.2f}", ha="center", va="bottom", fontsize=styles.CHART_FONT_SIZE)
        ax.set_ylim(0, val * 1.15 if val > 0 else 1)
        ax.set_ylabel(unit, fontsize=styles.CHART_FONT_SIZE)
    if title:
        fig.suptitle(title, fontsize=styles.CHART_FONT_SIZE + 1)
    fig.tight_layout()
    return _save(fig, out_path)


import logging as _logging
import os as _os

_log = _logging.getLogger(__name__)


def _figure_tex(path, caption):
    return ("\n\\begin{figure}[htbp]\n\\centering\n"
            "\\includegraphics[width=0.9\\textwidth]{" + str(path).replace("\\", "/") + "}\n"
            "\\caption{" + caption + "}\n\\end{figure}\n")


def ur_summary_figure(ur_log, chart_dir):
    """LaTeX for the Section 5.5 UR chart, built from (row label, UR cell) pairs. '' if no data."""
    if not chart_dir:
        return ""
    try:
        groups = {"Steel Plate Girders": [], "Concrete Deck Slab": [], "Cross Bracing": [], "End Diaphragms": []}
        for label, cell in ur_log:
            m = re.search(r"\d+\.\d+", str(cell))
            if not m:
                continue
            v, l = float(m.group()), str(label)
            if l.startswith("Girder"):
                groups["Steel Plate Girders"].append(v)
            elif l.startswith("Deck") or l.startswith("Transverse Shear (slab)") or l.startswith("Crack Width (slab)"):
                groups["Concrete Deck Slab"].append(v)
            elif l.startswith("Cross Bracing") and ("Compression" in l or "Tension" in l):
                groups["Cross Bracing"].append(v)
            elif l.startswith("End Diaphragm"):
                groups["End Diaphragms"].append(v)
        items = [(k, max(v)) for k, v in groups.items() if v]
        _os.makedirs(chart_dir, exist_ok=True)
        path = ur_bar_chart(items, _os.path.join(chart_dir, "ur_summary.png"))
        if not path:
            return ""
        return _figure_tex(path, "Governing utilization ratio (UR = demand / capacity) by component; "
                                 "the red dashed line marks UR = 1.0. End diaphragms are shown for Cross Bracing type only.")
    except Exception:
        _log.exception("UR summary chart skipped")
        return ""


def material_figures_latex(input_dict, chart_dir):
    """LaTeX for the Chapter 7 quantity charts. '' if there is no numeric data."""
    if not chart_dir:
        return ""
    out = ""
    try:
        _os.makedirs(chart_dir, exist_ok=True)
        g = input_dict.get
        steel = [("Girders", to_float(g("steel_girders_wt_total")))]
        cb = [to_float(g(k)) for k in ("bracing_top_wt_total", "bracing_bot_wt_total", "bracing_diag_wt_total")]
        cb = [v for v in cb if v is not None]
        if cb:
            steel.append(("Cross bracing", sum(cb)))
        p = quantity_bar_chart(steel, "Structural steel (MT)", _os.path.join(chart_dir, "qty_steel.png"))
        if p:
            out += _figure_tex(p, "Structural steel quantities (MT) from Table 7.1. End diaphragm steel "
                                  "is not part of the bill of materials and is not shown.")
        p = concrete_rebar_chart(g("concrete_deck_vol_total"), "Volume (m$^3$)",
                                 g("rebar_deck_wt_total"), "Weight (MT)",
                                 _os.path.join(chart_dir, "qty_concrete_rebar.png"))
        if p:
            out += _figure_tex(p, "Deck slab concrete volume and reinforcement steel weight from Table 7.1.")
    except Exception:
        _log.exception("Material quantity charts skipped")
    return out
