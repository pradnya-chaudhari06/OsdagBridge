"""Integration: full report generation from real design data.

Uses tests/fixtures/demo_case_30m.json.gz (input_dict / output_dict captured
from an OsdagBridge GUI design run) and the real build_report_payload /
generate_report pipeline, then inspects the compiled PDF.  Skipped when no
pdflatex is available.
"""
import os
import re
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "unit"))
from report_test_utils import have_pdf_tools, latex_errors, load_demo_case  # noqa: E402

pytestmark = pytest.mark.skipif(not have_pdf_tools(), reason="pdflatex or pymupdf not available")


@pytest.fixture(scope="module")
def report(tmp_path_factory):
    from osdagbridge.core.reports.report_generator import (
        ReportMetadata, ReportOptions, ReportRequest, build_report_payload, generate_report,
    )
    out = tmp_path_factory.mktemp("report")
    case = load_demo_case()
    meta = ReportMetadata(project_name="Integration test", project_location="", designer="QA",
                          client="", company="", group_name="", subtitle="Rev 0",
                          job_number="IT-1", additional_comments="", logo_path=None,
                          report_date="2026-01-01")
    req = ReportRequest(metadata=meta,
                        options=ReportOptions(sections=case["sections"], include_figures=True,
                                              include_toc=True, include_pdf=True),
                        output_dir=str(out), file_stem="itest")
    payload = build_report_payload(req, dict(case["input_dict"]), dict(case["output_dict"]))
    os.environ["OSDAGBRIDGE_REPORT_KEEP_LOG"] = "1"
    try:
        res = generate_report(payload, req)
    finally:
        os.environ.pop("OSDAGBRIDGE_REPORT_KEEP_LOG", None)
    assert res.pdf_path and os.path.exists(res.pdf_path)
    import pymupdf
    doc = pymupdf.open(res.pdf_path)
    log = open(os.path.join(str(out), "itest.log"), encoding="latin-1").read()
    return {"pdf": res.pdf_path, "pages": [p.get_text() for p in doc], "doc": doc,
            "log": log, "dir": str(out)}


def test_pdf_compiles_without_latex_errors_or_overflows(report):
    from osdagbridge.core.reports import styles
    log = report["log"]
    assert latex_errors(log) == []
    assert "There were undefined references" not in log
    # no table wider than the text block
    assert "Overfull \\hbox" not in "\n".join(l for l in log.splitlines() if "in alignment" in l)
    # remaining paragraph overflows (single long words in narrow cells) must
    # stay inside the cell padding, i.e. never reach the neighbouring rule
    widths = [float(m) for m in re.findall(r"Overfull \\hbox \(([\d.]+)pt too wide\)", log)]
    assert all(w < styles.TABLE["tabcolsep_pt"] for w in widths), sorted(widths)[-5:]


def test_all_chapters_present(report):
    text = "\n".join(report["pages"])
    for heading in ("Executive Summary", "Project Information", "Input Parameters",
                    "Loads and Load Combinations", "Analysis Results", "Design Checks",
                    "Material Take-off", "References"):
        assert heading in text, heading


def test_multipage_tables_repeat_headers(report):
    pages = report["pages"]
    cont = [t for t in pages if "(continued)" in t]
    assert len(cont) >= 10
    for t in pages:
        for m in re.finditer(r"Table (\d+\.\d+): [^\n]*\(continued\)", t):
            first = t.find(f"Table {m.group(1)}: ")
            assert first == m.start(), f"Table {m.group(1)} continued-head printed after its first head"


def test_no_orphan_continuation_footers(report):
    for i, t in enumerate(report["pages"]):
        if "Continued on next page" in t:
            assert "(continued)" in report["pages"][i + 1] or "Table" in report["pages"][i + 1]


def test_live_load_tables_separate(report):
    text = "\n".join(report["pages"])
    assert "Vehicle Live Load (LL)" in text and "Footway Live Load (FPLL)" in text


def test_section_5_5_and_chapter_7_figures(report):
    text = "\n".join(report["pages"])
    for cap in ("Utilization Ratio — Steel Plate Girders", "Utilization Ratio — Concrete Deck Slab",
                "Utilization Ratio — Cross Bracing", "Utilization Ratio — End Diaphragms",
                "Structural Steel Tonnage (MT)", "Concrete Volume (m³)", "Reinforcement Steel (MT)"):
        assert cap in text, cap
    images = sum(len(p.get_images()) for p in report["doc"])
    assert images >= 7


def test_table_5_28_end_diaphragm_message_clears_bottom_rule(report):
    """The multi-line 'no end-diaphragm results' cell must not touch the rule below it."""
    doc = report["doc"]
    pno = next(i for i, t in enumerate(report["pages"])
               if "Table 5.28" in t and "were performed." in t.replace("\n", " "))
    page = doc[pno]
    last = max((w for w in page.get_text("words") if w[4] == "performed."), key=lambda w: w[3])
    rules = []
    for dr in page.get_drawings():
        for it in dr["items"]:
            if it[0] == "l" and abs(it[1].y - it[2].y) < 0.5:
                rules.append(it[1].y)
            elif it[0] == "re" and it[1].height < 1.5:
                rules.append(it[1].y0)
    below = min(y for y in rules if y > last[1])
    assert below - last[3] >= 1.0, (below, last[3])


def test_footer_page_numbers_match_pdf_pages(report):
    """'Page X of Y' must equal the PDF page index and the PDF page count."""
    pages = report["pages"]
    n = len(pages)
    assert not re.search(r"Page \d+ of \d+", pages[0])          # title page: no number
    for i, text in enumerate(pages[1:], start=2):
        found = re.findall(r"Page (\d+) of (\d+)", text)
        assert found and found[-1] == (str(i), str(n)), (i, found)


def test_no_text_in_footer_area(report):
    doc = report["doc"]
    ok = re.compile(r"^(Osdag|\||FOSSEE|Indian|Institute|of|Technology|Bombay|Page|\d+|"
                    r"Continued|on|next|page|\*|Software|default|value)$")
    for i, page in enumerate(doc):
        footer_top = min((w[1] for w in page.get_text("words") if w[4] == "FOSSEE"), default=None)
        if footer_top is None:
            continue
        for w in page.get_text("words"):
            if footer_top - 14 < w[1] < footer_top + 20:
                assert ok.match(w[4]), f"page {i + 1}: '{w[4]}' overlaps the footer"


def test_temporary_chart_images_cleaned_up(report):
    left = [f for f in os.listdir(report["dir"]) if f.endswith(".png")]
    assert left == []


def test_continued_headings_never_precede_first_heading(report):
    """A 'Table X (continued)' heading must follow 'Table X:' (captions may wrap)."""
    seen = set()
    for i, text in enumerate(report["pages"]):
        lines = [l.strip() for l in text.splitlines()]
        for k, line in enumerate(lines):
            m = re.match(r"Table (\d+\.\d+|\d+):", line)
            if not m:
                continue
            nxt = lines[k + 1] if k + 1 < len(lines) else ""
            if "(continued)" in line or nxt.startswith("(continued)"):
                assert m.group(1) in seen, f"page {i + 1}: Table {m.group(1)} continued before start"
            else:
                seen.add(m.group(1))


def test_no_stray_table_rule_at_page_top(report):
    import pymupdf
    for i, page in enumerate(report["doc"]):
        words = [w for w in page.get_text("words") if 100 < w[1] < 740]
        if not words:
            continue
        top = min(w[1] for w in words)
        for dr in page.get_drawings():
            for it in dr["items"]:
                r = pymupdf.Rect(it[1], it[2]) if it[0] == "l" else (it[1] if it[0] == "re" else None)
                if r is not None:
                    # a stray rule stands clear of the text (a box border sits ~3 pt above it)
                    assert not (r.height < 2 and r.width > 300 and 95 < r.y0 < top - 4), \
                        f"page {i + 1}: rule above the first text line"


def test_no_heading_left_at_page_bottom(report):
    for i, page in enumerate(report["doc"]):
        lines = []
        for b in page.get_text("dict")["blocks"]:
            for l in b.get("lines", []):
                spans = [s for s in l["spans"] if s["text"].strip()]
                if spans and 100 < l["bbox"][1] < 735:
                    lines.append((l["bbox"][1], max(s["size"] for s in spans)))
        if lines:
            assert max(lines)[1] < 13.5, f"page {i + 1}: last line is a heading"
