"""Helpers shared by the report-generator tests (not a test module)."""
import gzip
import json
import os
import shutil
import subprocess

FIXTURE = os.path.join(os.path.dirname(__file__), "..", "fixtures", "demo_case_30m.json.gz")


def load_demo_case():
    """Real design data (input_dict / output_dict) captured from a GUI design run."""
    with gzip.open(FIXTURE, "rb") as fh:
        return json.loads(fh.read().decode("utf-8"))


def have_pdf_tools():
    """True when pdflatex and PyMuPDF (test extra) are both available."""
    import importlib.util
    if importlib.util.find_spec("pymupdf") is None:
        return False
    return find_pdflatex() is not None


def find_pdflatex():
    """pdflatex from the bundled osdag_latex_env, else from PATH (None if absent)."""
    try:
        from osdag_latex_env.__main__ import OsdagLatexEnv
        env = OsdagLatexEnv()
        if env.pdflatex and os.path.exists(str(env.pdflatex)):
            return str(env.pdflatex)
    except Exception:
        pass
    return shutil.which("pdflatex")


def compile_tex(tex_source, workdir, name="doc", runs=1):
    """Compile *tex_source*; return (pdf_path or None, log text)."""
    exe = find_pdflatex()
    tex = os.path.join(workdir, name + ".tex")
    with open(tex, "w", encoding="utf-8") as fh:
        fh.write(tex_source)
    for _ in range(runs):
        subprocess.run([exe, "-interaction=nonstopmode", name + ".tex"], cwd=workdir,
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    pdf = os.path.join(workdir, name + ".pdf")
    log_path = os.path.join(workdir, name + ".log")
    log = open(log_path, encoding="latin-1").read() if os.path.exists(log_path) else ""
    return (pdf if os.path.exists(pdf) else None), log


def latex_errors(log):
    return [l for l in log.splitlines() if l.startswith("! ")]


def page_texts(pdf):
    import pymupdf
    return [p.get_text() for p in pymupdf.open(pdf)]
