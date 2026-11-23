# =============================================================================
# OsdagBridge Report — chart generation (matplotlib, headless "Agg" backend)
# =============================================================================
# Turns the numbers prepared by ``report_data`` into PNG files.  This module
# knows nothing about LaTeX; the report generator decides where the images go
# and embeds them as figures.
#
#   * utilization_chart() — bar chart of Utilization Ratio (UR) per check with
#     a red dashed reference line at UR = 1.0; passing bars (UR <= 1.0) and
#     failing bars (UR > 1.0) use different colours and hatching, and checks
#     without valid data are listed as "no data" (never drawn as passing).
#   * quantity_chart()    — bar chart of one material quantity (single unit
#     per chart, so different units are never compared on one axis).
# =============================================================================

from __future__ import annotations

import os
import textwrap
from typing import Optional, Sequence

import matplotlib

matplotlib.use("Agg")  # no display needed; safe inside the report worker thread
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Patch  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402

from osdagbridge.core.reports import styles  # noqa: E402
from osdagbridge.core.reports.report_data import FAIL, NO_DATA  # noqa: E402

__all__ = ["utilization_chart", "build_utilization_figure", "build_ur_no_data_figure", "quantity_chart"]


def _short(label: str, n: int | None = None) -> str:
    n = n or styles.CHART["max_label_chars"]
    return label if len(label) <= n else label[: n - 1] + "…"


def _save(fig, path: str) -> str:
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    fig.savefig(path, dpi=styles.CHART["dpi"], bbox_inches="tight",
                pad_inches=styles.CHART["tight_pad"], facecolor="white")
    plt.close(fig)
    return path


def _no_data_figure(title: str, message: str, path: str) -> str:
    """Placeholder chart that states clearly why there are no bars."""
    with plt.rc_context(styles.matplotlib_rc()):
        fig, ax = plt.subplots(figsize=(styles.CHART["figsize_in"][0], 1.6))
        ax.axis("off")
        ax.set_title(title, loc="left", fontweight="bold")
        ax.text(0.5, 0.45, message, ha="center", va="center", wrap=True,
                fontsize=styles.CHART["label_size"], color=styles.hex_color("muted"),
                transform=ax.transAxes)
        return _save(fig, path)


def build_ur_no_data_figure(title: str, message: str):
    """UR chart panel for an element WITHOUT design results.

    A deliberate, framed panel instead of an empty space: it keeps the UR axis,
    the axis label and the red dashed UR = 1.0 limit line, draws no bars, and
    states in a box why there are no results.  Nothing is plotted that could be
    read as a value.
    """
    c = styles.CHART
    with plt.rc_context(styles.matplotlib_rc()):
        fig, ax = plt.subplots(figsize=(c["figsize_in"][0], c["figsize_in"][1]))
        ax.set_xlim(0, 1)
        ax.set_ylim(0, c["ref_line_value"] * 1.25)
        ax.set_xticks([])
        ax.set_ylabel(c["ur_axis_label"])
        ax.set_title(title, loc="left", fontweight="bold")
        for side in ("top", "right", "bottom", "left"):
            ax.spines[side].set_visible(True)
            ax.spines[side].set_color(styles.hex_color("muted"))
        if c["grid"]:
            ax.grid(axis="y", color=c["grid_color"], linestyle=c["grid_linestyle"],
                    linewidth=c["grid_linewidth"], zorder=0)
        ax.axhline(c["ref_line_value"], color=c["ref_line_color"],
                   linestyle=c["ref_line_style"], linewidth=c["ref_line_width"], zorder=4)
        # explicit wrapping: matplotlib's wrap=True wraps to the figure width,
        # which let the box run over the axis label
        body = textwrap.fill(message, width=c.get("no_data_wrap_chars", 58))
        ax.text(0.5, 0.45, "No design results available\n\n" + body,
                ha="center", va="center", transform=ax.transAxes,
                fontsize=c["label_size"], color=styles.hex_color("muted"), zorder=5,
                bbox=dict(boxstyle="round,pad=0.6", facecolor="white",
                          edgecolor=styles.hex_color("muted"), linewidth=0.8))
        handles = [Line2D([0], [0], color=c["ref_line_color"], linestyle=c["ref_line_style"],
                          linewidth=c["ref_line_width"], label=c["ref_line_label"])]
        ax.legend(handles=handles, loc="upper left", bbox_to_anchor=(1.0, 1.0), frameon=False)
        return fig


def utilization_chart(items: Sequence, title: str, path: str,
                      no_data_message: Optional[str] = None) -> str:
    """Draw a Utilization Ratio bar chart and save it as PNG at *path*.

    Parameters
    ----------
    items : sequence of report_data.URItem
        One bar per item (``item.label``, ``item.ur``, ``item.status``).
    title : str
        Chart title (structural element).
    path : str
        Output PNG path.
    no_data_message : str, optional
        Text shown when *items* is empty.
    """
    if not items:
        fig = build_ur_no_data_figure(title, no_data_message or "No design check results available.")
        with plt.rc_context(styles.matplotlib_rc()):
            return _save(fig, path)
    with plt.rc_context(styles.matplotlib_rc()):
        return _save(build_utilization_figure(items, title), path)


def build_utilization_figure(items: Sequence, title: str):
    """Return the matplotlib Figure of a UR bar chart (not saved, not closed)."""
    c = styles.CHART
    labels = [_short(it.label) for it in items]
    values, colors, hatches = [], [], []
    for it in items:
        if it.status == NO_DATA or it.ur is None:
            values.append(0.0)
            colors.append(styles.hex_color("no_data"))
            hatches.append("")
        elif it.status == FAIL:
            values.append(it.ur)
            colors.append(styles.hex_color("fail"))
            hatches.append("///")
        else:
            values.append(it.ur)
            colors.append(styles.hex_color("pass"))
            hatches.append("")

    n = len(items)
    # Keep the drawing at (about) the printed width so fonts stay readable
    # after LaTeX scales the image to \textwidth; many bars -> taller figure
    # with steeper labels instead of a wider one.
    many = n > 10
    width = c["figsize_in"][0] + (1.2 if many else 0.0)
    height = c["figsize_tall_in"][1] + (0.8 if n > 16 else 0.0) if many else c["figsize_in"][1]
    valid = [v for v, it in zip(values, items) if it.status != NO_DATA and it.ur is not None]
    ymax = max([c["ref_line_value"]] + valid) * 1.18

    with plt.rc_context(styles.matplotlib_rc()):
        fig, ax = plt.subplots(figsize=(width, height))
        x = list(range(n))
        bars = ax.bar(x, values, width=c["bar_width"], color=colors,
                      edgecolor=c["bar_edge_color"], linewidth=c["bar_edge_width"],
                      zorder=3)
        for bar, h in zip(bars, hatches):
            if h:
                bar.set_hatch(h)
        ax.axhline(c["ref_line_value"], color=c["ref_line_color"],
                   linestyle=c["ref_line_style"], linewidth=c["ref_line_width"], zorder=4)

        for xi, it, v in zip(x, items, values):
            if it.status == NO_DATA or it.ur is None:
                ax.text(xi, ymax * 0.02, "no data", rotation=90, ha="center", va="bottom",
                        fontsize=c["annotation_size"], color=styles.hex_color("muted"), zorder=5)
            else:
                ax.text(xi, v + ymax * 0.012, f"{it.ur:.2f}", ha="center", va="bottom",
                        fontsize=c["annotation_size"], zorder=5)

        ax.set_xticks(x)
        rot = (c["tick_rotation_dense"] if many else c["tick_rotation"]) if n > 4 else 0
        ax.set_xticklabels(labels, rotation=rot, ha="right" if rot else "center")
        ax.set_ylim(0, ymax)
        ax.set_ylabel(c["ur_axis_label"])
        ax.set_title(title, loc="left", fontweight="bold")
        if c["grid"]:
            ax.grid(axis=c["grid_axis"], color=c["grid_color"],
                    linestyle=c["grid_linestyle"], linewidth=c["grid_linewidth"], zorder=0)

        handles = [
            Patch(facecolor=styles.hex_color("pass"), edgecolor=c["bar_edge_color"], label="Pass (UR ≤ 1.0)"),
            Patch(facecolor=styles.hex_color("fail"), edgecolor=c["bar_edge_color"], hatch="///", label="Fail (UR > 1.0)"),
            Line2D([0], [0], color=c["ref_line_color"], linestyle=c["ref_line_style"],
                   linewidth=c["ref_line_width"], label=c["ref_line_label"]),
        ]
        if any(it.status == NO_DATA or it.ur is None for it in items):
            handles.append(Patch(facecolor=styles.hex_color("no_data"), label="No valid data"))
        ax.legend(handles=handles, loc="upper left", bbox_to_anchor=(1.0, 1.0),
                  frameon=False)
        return fig


def quantity_chart(labels: Sequence[str], values: Sequence[Optional[float]],
                   unit: str, title: str, path: str,
                   axis_label: Optional[str] = None,
                   no_data_message: Optional[str] = None) -> str:
    """Draw a bar chart for one material quantity measured in *unit*.

    Categories whose value is None are drawn as "not available" (no bar).
    """
    c = styles.CHART
    if not labels or all(v is None for v in values):
        return _no_data_figure(title, no_data_message or "Quantity not available for this design.", path)

    n = len(labels)
    cols = styles.palette(n)
    plotted = [v if v is not None else 0.0 for v in values]
    vmax = max([v for v in values if v is not None] + [0.0])
    ymax = vmax * 1.2 if vmax > 0 else 1.0

    with plt.rc_context(styles.matplotlib_rc()):
        fig, ax = plt.subplots(figsize=(min(c["figsize_in"][0], 2.2 + 1.5 * n), c["figsize_in"][1] * 0.9))
        x = list(range(n))
        ax.bar(x, plotted, width=min(c["bar_width"], 0.55), color=cols,
               edgecolor=c["bar_edge_color"], linewidth=c["bar_edge_width"], zorder=3)
        for xi, v in zip(x, values):
            if v is None:
                ax.text(xi, ymax * 0.02, "not available", rotation=90, ha="center", va="bottom",
                        fontsize=c["annotation_size"], color=styles.hex_color("muted"))
            else:
                ax.text(xi, v + ymax * 0.015, f"{v:,.2f} {unit}", ha="center", va="bottom",
                        fontsize=c["annotation_size"])
        ax.set_xticks(x)
        ax.set_xticklabels([_short(l, 22) for l in labels],
                           rotation=c["tick_rotation"] if n > 3 else 0,
                           ha="right" if n > 3 else "center")
        ax.set_ylim(0, ymax)
        ax.set_ylabel(axis_label or unit)
        ax.set_title(title, loc="left", fontweight="bold")
        if c["grid"]:
            ax.grid(axis=c["grid_axis"], color=c["grid_color"],
                    linestyle=c["grid_linestyle"], linewidth=c["grid_linewidth"], zorder=0)
        return _save(fig, path)
