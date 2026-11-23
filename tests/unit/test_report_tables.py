"""Requirements 1 & 2 - repeated table headers, widths, page breaking.

Unit tests use synthetic rows; the LaTeX tests compile real documents with
the report preamble (skipped automatically when pdflatex is unavailable).
"""
import re
import tempfile

import pytest

from osdagbridge.core.reports import styles
from osdagbridge.core.reports.latex_tables import (
    build_longtable, fit_colspec, format_row, keep_multirow_groups, parse_colspec,
)
from report_test_utils import compile_tex, have_pdf_tools, latex_errors, page_texts

needs_latex = pytest.mark.skipif(not have_pdf_tools(), reason="pdflatex or pymupdf not available")


# ---------------------------------------------------------------- column specs
def test_parse_colspec_counts_columns_rules_and_widths():
    info = parse_colspec(r"|C{2.5cm}|L{3cm}|>{\centering\arraybackslash}p{4.2cm}|c|")
    assert info["n_cols"] == 4
    assert info["n_vrules"] == 5
    assert info["widths_cm"] == [2.5, 3.0, 4.2, None]


def test_fit_colspec_scales_overwide_spec_proportionally():
    spec = r"|L{5.5cm}|p{10.0cm}|"                     # 16.39 cm incl. padding > 15.92
    fitted = fit_colspec(spec)
    w = parse_colspec(fitted)["widths_cm"]
    assert sum(w) <= styles.available_column_width_cm(2) + 1e-9
    assert w[0] / w[1] == pytest.approx(5.5 / 10.0, rel=0.01)
    assert fitted.startswith("|L{") and "|p{" in fitted   # column types preserved


def test_fit_colspec_keeps_specs_that_fit_or_cannot_be_measured():
    assert fit_colspec(r"|L{4cm}|p{6cm}|") == r"|L{4cm}|p{6cm}|"
    assert fit_colspec(r"|l|p{20cm}|") == r"|l|p{20cm}|"


# ---------------------------------------------------------------- structure
def _table(rows=5, **kw):
    body = [[f"r{i}", f"v{i}"] for i in range(rows)]
    return build_longtable(r"|L{5cm}|p{9cm}|", ["Parameter", "Value"], body,
                           caption=r"\textbf{Demo}", **kw)


def test_longtable_has_first_head_repeated_head_and_feet_in_order():
    tex = _table()
    order = [tex.index(m) for m in (r"\begin{longtable}", r"\endfirsthead", r"\endhead",
                                    r"\endfoot", r"\endlastfoot", r"\end{longtable}")]
    assert order == sorted(order)


def test_header_row_is_repeated_and_caption_marked_continued():
    tex = _table()
    assert tex.count(r"\textbf{Parameter} & \hspace{0pt}\textbf{Value}") == 2
    assert r"\caption{\textbf{Demo}}" in tex
    assert r"\caption[]{\textbf{Demo} (continued)}" in tex
    assert "Continued on next page" in tex


def test_all_rows_preserved_and_in_order():
    tex = _table(rows=40)
    found = re.findall(r"^r(\d+) & v\1", tex, re.M)
    assert [int(x) for x in found] == list(range(40))


def test_raw_string_body_and_header_are_passed_through():
    body = "a & b \\\\[6pt]\n\\hline\nc & d \\\\[6pt]\n\\hline"
    tex = build_longtable(r"|l|l|", r"\textbf{A} & \textbf{B} \\[6pt]", body)
    assert "a & b" in tex and "c & d" in tex
    assert r"\textbf{A} & \hspace{0pt}\textbf{B} \\" in tex   # trailing \\[6pt] normalised
    assert r"\textbf{B} \\[6pt]" not in tex


def test_header_less_table_repeats_only_caption():
    tex = build_longtable(r"|l|l|", None, [["x", "y"]], caption="Cap")
    assert tex.count(r"\caption") == 2 and r"\rowcolor" not in tex


def test_format_row_uses_style_row_padding():
    assert format_row(["a", "b"]).startswith(r"a & b \\[" + styles.TABLE["row_pad"] + "]")


def test_keep_multirow_groups_protects_rows_and_rules_inside_group():
    body = ("\\multirow{3}{*}{G1} & a \\\\[6pt]\n\\cline{2-2}\n & b \\\\[6pt]\n\\cline{2-2}\n"
            " & c \\\\[6pt]\n\\hline\nnext & d \\\\[6pt]\n\\hline")
    out = keep_multirow_groups(body)
    assert out.count("\\\\*[6pt]") == 2                       # rows 1 and 2 of the group
    assert out.count(r"\noalign{\nobreak}") == 2              # the two \cline inside
    assert "c \\\\[6pt]" in out and "d \\\\[6pt]" in out      # breaks allowed after group


def test_keep_multirow_ignores_double_backslash_inside_braces():
    body = "\\multirow{2}{*}{\\makecell{At\\\\Mid}} & a \\\\\n & b \\\\\n\\hline"
    out = keep_multirow_groups(body)
    assert "\\makecell{At\\\\Mid}" in out and out.count("\\\\*") == 1


# ---------------------------------------------------------------- LaTeX level
def _doc(body_tex, filler=0):
    from osdagbridge.core.reports.report_generator import preamble
    fill = "\n\n".join(f"Filler paragraph {i}." for i in range(filler))
    return preamble("P", "J", "D") + "\\chapter{T}\n" + fill + "\n" + body_tex + "\n\\end{document}\n"


@needs_latex
@pytest.mark.parametrize("filler", [0, 14, 25])
def test_multipage_table_repeats_header_on_every_page(filler):
    tex = build_longtable(r"|L{5cm}|p{9cm}|", ["Parameter", "Value"],
                          [[f"Row {i}", f"value {i}"] for i in range(1, 120)], caption="Big")
    with tempfile.TemporaryDirectory() as d:
        pdf, log = compile_tex(_doc(tex, filler), d)
        assert pdf and not latex_errors(log)
        pages = [t for t in page_texts(pdf) if "Row " in t]
        assert len(pages) >= 3
        assert "Table 1.1: Big" in pages[0] and "(continued)" not in pages[0]
        for t in pages[1:]:
            assert "Table 1.1: Big (continued)" in t and "Parameter" in t
        for t in pages[:-1]:
            assert "Continued on next page" in t
        assert "Continued on next page" not in pages[-1]
        rows = [int(m) for t in pages for m in re.findall(r"Row (\d+)", t)]
        assert rows == list(range(1, 120))                       # nothing dropped


@needs_latex
@pytest.mark.parametrize("filler", [0, 6, 12])
def test_multirow_groups_are_never_split_across_pages(filler):
    groups = []
    for g in range(1, 6):
        rows = []
        for k in range(13):
            lab = rf"\multirow{{13}}{{*}}{{G{g}}}" if k == 0 else ""
            end = "\\\\[6pt]\n" + (r"\cline{2-3}" if k < 12 else r"\hline")
            rows.append(f"{lab} & Prop{g}-{k} & {k} {end}")
        groups.append("\n".join(rows))
    tex = build_longtable(r"|C{2.5cm}|L{8cm}|C{5cm}|", ["Girder", "Property", "Value"],
                          "\n".join(groups), caption="Groups")
    with tempfile.TemporaryDirectory() as d:
        pdf, log = compile_tex(_doc(tex, filler), d)
        assert pdf and not latex_errors(log)
        for t in page_texts(pdf):
            for g in range(1, 6):
                n = len(re.findall(rf"Prop{g}-\d+", t))
                assert n in (0, 13), f"group G{g} split ({n} rows on one page)"


@needs_latex
def test_wide_specs_compile_without_overfull_boxes():
    tex = build_longtable(r"|L{1.8cm}|L{2.3cm}|L{1.8cm}|p{4.8cm}|p{4.8cm}|",
                          ["A", "B", "C", "D", "E"], [["x"] * 5] * 3, caption="Wide")
    with tempfile.TemporaryDirectory() as d:
        pdf, log = compile_tex(_doc(tex), d)
        assert pdf and "Overfull \\hbox" not in log
