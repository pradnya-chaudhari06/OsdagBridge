"""Requirement 6 - centralised formatting configuration (styles.py).

Synthetic/unit level: checks the configuration values and that the report
generator actually consumes them (single source of truth).
"""
import subprocess
import sys

import pytest

from osdagbridge.core.reports import styles


def test_styles_module_has_no_osdagbridge_imports():
    """styles.py must be importable on its own (no circular-import risk)."""
    src = open(styles.__file__, encoding="utf-8").read()
    assert "import osdagbridge" not in src and "from osdagbridge" not in src


@pytest.mark.parametrize("module", [
    "osdagbridge.core.reports.styles",
    "osdagbridge.core.reports.latex_tables",
    "osdagbridge.core.reports.report_data",
    "osdagbridge.core.reports.charts",
    "osdagbridge.core.reports.chap3",
    "osdagbridge.core.reports.chap5",
    "osdagbridge.core.reports.chap7",
    "osdagbridge.core.reports.report_generator",
])
def test_report_modules_import_cleanly_in_fresh_interpreter(module):
    """Each module imports first in a new interpreter -> no circular imports."""
    code = (
        "import os,sys\n"
        "if os.name=='nt':\n"
        "    [os.add_dll_directory(p) for p in [os.path.join(sys.prefix,'Library','bin')] if os.path.isdir(p)]\n"
        f"import importlib; importlib.import_module('{module}')\n"
    )
    res = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    assert res.returncode == 0, res.stderr


def test_page_geometry_values():
    assert styles.PAGE["paper"] == "a4paper"
    assert styles.text_width_cm() == pytest.approx(21.0 - 2 * 2.54)
    opts = styles.geometry_options()
    for token in ("a4paper", "includehead", "includefoot", "headheight=15.0pt",
                  "footskip=42.0pt", "left=2.54cm"):
        assert token in opts
    # fancyhdr needs >= 14.5pt head height for a 12pt document
    assert styles.PAGE["headheight_pt"] >= 14.5


def test_colour_definitions_cover_brand_and_pass_fail():
    defs = styles.latex_color_definitions()
    assert r"\definecolor{osdagGreen}{HTML}{91B014}" in defs      # original brand colour kept
    assert "tableHeaderBg" in defs and "passGreen" in defs and "failRed" in defs
    assert styles.hex_color("fail").startswith("#") and len(styles.hex_color("fail")) == 7
    assert len(styles.palette(12)) == 12


def test_table_settings_snippet_matches_config():
    snip = styles.latex_table_settings()
    assert rf"\setlength{{\tabcolsep}}{{{styles.TABLE['tabcolsep_pt']}pt}}" in snip
    assert rf"\renewcommand{{\arraystretch}}{{{styles.TABLE['arraystretch']}}}" in snip
    assert r"\setcounter{LTchunksize}" in snip


def test_footer_rule_has_no_negative_vspace():
    """The old footer pulled the note up with \\vspace{-20pt} (overlap cause)."""
    rule = styles.latex_fancy_footer_rule()
    assert "-20pt" not in rule and r"\vspace{-" not in rule
    assert "Software default value" in rule


def test_available_width_accounts_for_padding_and_rules():
    two = styles.available_column_width_cm(2)
    expected = styles.text_width_cm() - (2 * 2 * 6.0 + 3 * 0.5) / styles.PT_PER_CM - 0.05
    assert two == pytest.approx(expected)


def test_preamble_consumes_styles():
    from osdagbridge.core.reports.report_generator import preamble
    pre = preamble("Project", "J-1", "2026-01-01")
    assert styles.geometry_options() in pre
    assert styles.latex_color_definitions() in pre
    assert styles.latex_table_settings() in pre
    assert styles.HEADER_FOOTER["footer_left"] in pre
    # longtable must NOT be preceded by \needspace (breaks repeated heads)
    assert r"\BeforeBeginEnvironment{longtable}" not in pre


def test_changing_style_changes_output(monkeypatch):
    """Single source of truth: a style change propagates to generated LaTeX."""
    from osdagbridge.core.reports.report_generator import preamble
    monkeypatch.setitem(styles.COLORS, "table_header_bg", "123456")
    assert r"\definecolor{tableHeaderBg}{HTML}{123456}" in preamble("P", "J", "D")


def test_chart_rc_uses_chart_config():
    rc = styles.matplotlib_rc()
    assert rc["axes.labelsize"] == styles.CHART["label_size"]
    assert rc["savefig.dpi"] == styles.CHART["dpi"]
