# =============================================================================
# OsdagBridge Report — reusable multi-page table builder (PyLaTeX LongTable)
# =============================================================================
# Every multi-page table in the report is built here so that all of them get
# the same behaviour:
#
#   * caption + column headings on the first page   (\endfirsthead)
#   * "<caption> (continued)" + the same column headings repeated on every
#     following page                                (\endhead)
#   * a "Continued on next page" line at a page break (\endfoot)
#   * nothing extra after the last row              (\endlastfoot)
#   * column widths that never exceed \textwidth (p{}/L{}/C{}/R{} widths in
#     cm are scaled down proportionally when a spec is wider than the page)
#
# The chapter generators already produce fully escaped LaTeX for every cell,
# so all content is passed to PyLaTeX wrapped in ``NoEscape``.
# =============================================================================

from __future__ import annotations

import re
from typing import Iterable, Sequence

from pylatex import LongTable, NoEscape

from osdagbridge.core.reports import styles

__all__ = [
    "build_longtable",
    "parse_colspec",
    "fit_colspec",
    "format_row",
    "keep_multirow_groups",
    "keep_rules_with_rows",
]

# Column letters that create a column (array/tabularx/our own L C R types).
_COLUMN_LETTERS = set("lcrpmbXLCR")
# Column letters that take a width argument.
_WIDTH_LETTERS = set("pmbLCR")
_WIDTH_RE = re.compile(r"^\s*([0-9]*\.?[0-9]+)\s*cm\s*$")


def _read_group(spec: str, i: int) -> tuple[str, int]:
    """Return the text inside the brace group starting at spec[i] == '{'."""
    if i >= len(spec) or spec[i] != "{":
        raise ValueError(f"Expected '{{' at position {i} in column spec {spec!r}")
    depth = 0
    for j in range(i, len(spec)):
        if spec[j] == "{":
            depth += 1
        elif spec[j] == "}":
            depth -= 1
            if depth == 0:
                return spec[i + 1:j], j + 1
    raise ValueError(f"Unbalanced braces in column spec {spec!r}")


def parse_colspec(spec: str) -> dict:
    """Parse a LaTeX column spec.

    Returns ``{"tokens": [...], "n_cols": int, "n_vrules": int,
    "widths_cm": [float | None, ...]}`` where ``tokens`` is a list of
    ``(kind, text)`` pairs that can be re-joined to rebuild the spec, and
    ``widths_cm`` holds one entry per column (None when the column has no
    width in cm, e.g. ``c`` or a width given as ``0.3\\textwidth``).
    """
    tokens: list[tuple[str, str]] = []
    widths: list[float | None] = []
    n_vrules = 0
    i = 0
    while i < len(spec):
        ch = spec[i]
        if ch.isspace():
            i += 1
            continue
        if ch == "|":
            tokens.append(("rule", "|"))
            n_vrules += 1
            i += 1
        elif ch in "><@!":
            arg, j = _read_group(spec, i + 1)
            tokens.append(("decl", ch + "{" + arg + "}"))
            i = j
        elif ch == "*":
            # *{n}{cols} — expand so widths/columns are counted correctly
            count, j = _read_group(spec, i + 1)
            body, k = _read_group(spec, j)
            expanded = parse_colspec(body * int(count))
            tokens.extend(expanded["tokens"])
            widths.extend(expanded["widths_cm"])
            n_vrules += expanded["n_vrules"]
            i = k
        elif ch in _WIDTH_LETTERS:
            arg, j = _read_group(spec, i + 1)
            m = _WIDTH_RE.match(arg)
            widths.append(float(m.group(1)) if m else None)
            tokens.append(("col", ch + "{" + arg + "}"))
            i = j
        elif ch in _COLUMN_LETTERS:
            widths.append(None)
            tokens.append(("col", ch))
            i += 1
        else:
            raise ValueError(f"Unsupported character {ch!r} in column spec {spec!r}")
    return {"tokens": tokens, "n_cols": len(widths), "n_vrules": n_vrules,
            "widths_cm": widths}


def fit_colspec(spec: str, max_width_cm: float | None = None,
                tabcolsep_pt: float | None = None) -> str:
    """Scale cm column widths down so the table fits the text width.

    Only specs in which *every* column has a width in cm are adjusted (for
    anything else the real width cannot be known in Python).  Proportions
    between the columns are preserved.  Specs that already fit are returned
    unchanged.
    """
    info = parse_colspec(spec)
    widths = info["widths_cm"]
    if not widths or any(w is None for w in widths):
        return spec
    if max_width_cm is None:
        max_width_cm = styles.available_column_width_cm(
            info["n_cols"], info["n_vrules"], tabcolsep_pt=tabcolsep_pt)
    total = sum(widths)
    if total <= max_width_cm + 1e-9:
        return spec
    factor = max_width_cm / total
    out = []
    w_iter = iter(widths)
    for kind, text in info["tokens"]:
        if kind == "col":
            w = next(w_iter)
            new_w = int(w * factor * 100) / 100.0      # floor to 0.01 cm
            letter = text[0]
            out.append(f"{letter}{{{new_w:.2f}cm}}")
        else:
            out.append(text)
    return "".join(out)


_TRAILING_ROW_END = re.compile(r"(\\\\(\[[^\]]*\])?\s*)$")


def _strip_row_end(row: str) -> str:
    """Remove a trailing ``\\\\`` / ``\\\\[6pt]`` and surrounding whitespace."""
    return _TRAILING_ROW_END.sub("", row.strip()).strip()


def _split_rows(body: str) -> list[list[str]]:
    """Split table body text into ``[text, terminator]`` pairs.

    A terminator is a top-level ``\\\\`` with an optional ``*`` and optional
    ``[len]``; ``\\\\`` inside braces (e.g. ``\\makecell{a\\\\b}``) is ignored.
    The final element may have an empty terminator (trailing ``\\hline``).
    """
    rows, depth, start, i, n = [], 0, 0, 0, len(body)
    while i < n:
        ch = body[i]
        if ch == "\\" and i + 1 < n and body[i + 1] == "\\" and depth == 0:
            j = i + 2
            if j < n and body[j] == "*":
                j += 1
            k = j
            while k < n and body[k] in " \t":
                k += 1
            if k < n and body[k] == "[":
                close = body.find("]", k)
                if close > 0:
                    j = close + 1
            rows.append([body[start:i], body[i:j]])
            start = i = j
            continue
        if ch == "\\" and i + 1 < n:
            i += 2                      # skip escaped char such as \{ or \%
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth = max(depth - 1, 0)
        i += 1
    rows.append([body[start:], ""])
    return rows


_MULTIROW_RE = re.compile(r"\\multirow\s*\{\s*(\d+)\s*\}")


def keep_multirow_groups(body: str) -> str:
    """Forbid page breaks inside ``\\multirow`` row groups.

    longtable may break the page after any row.  When it breaks inside a
    group whose first row carries ``\\multirow{N}{..}{label}``, the label is
    vertically centred over rows that continue on the next page and is
    printed *below* the last row — i.e. on top of the page footer (the "G4"
    overlap seen in the original report).  Turning the row ends inside each
    group into ``\\\\*`` (longtable's "no page break here") keeps every group
    on one page; breaks are still allowed between groups.
    """
    if r"\multirow" not in body:
        return body
    rows = _split_rows(body)
    protect_until = -1
    for idx, (text, term) in enumerate(rows):
        m = _MULTIROW_RE.search(text)
        if m:
            span = int(m.group(1))
            protect_until = max(protect_until, idx + span - 1)
        if idx < protect_until and term.startswith("\\\\"):
            if not term.startswith("\\\\*"):
                rows[idx][1] = "\\\\*" + term[2:]
            # A \cline / \hline between two rows of the group is set as its
            # own line, and the space after it is a legal page-break point
            # even after \\*.  Glue it to the next row as well.
            if idx + 1 < len(rows):
                rows[idx + 1][0] = _RULE_RE.sub(
                    lambda mm: mm.group(1) + r"\noalign{\nobreak}", rows[idx + 1][0], count=1)
    return "".join(t + term for t, term in rows)


def keep_rules_with_rows(body: str) -> str:
    r"""Never break a page between a row and the ``\hline`` directly after it.

    Otherwise the closing rule of a row can be pushed to the top of the next
    page (seen below Table 2.11).  The row end becomes ``\\*``; the page can
    still break after the rule.
    """
    rows = _split_rows(body)
    for idx in range(len(rows) - 1):
        term = rows[idx][1]
        if (term.startswith("\\\\") and not term.startswith("\\\\*")
                and rows[idx + 1][0].lstrip().startswith(r"\hline")):
            rows[idx][1] = "\\\\*" + term[2:]
    return "".join(t + term for t, term in rows)


# leading rule commands of a row segment: "\n\cline{2-3}" or "\n\hline"
_RULE_RE = re.compile(r"^(\s*(?:\\cline\{[^}]*\}|\\hline)(?:\s*(?:\\cline\{[^}]*\}|\\hline))*)")


def format_row(cells: Sequence[str], row_pad: str | None = None) -> str:
    """Join already-escaped cells into one body row followed by ``\\hline``."""
    pad = styles.TABLE["row_pad"] if row_pad is None else row_pad
    end = rf" \\[{pad}]" if pad else r" \\"
    return " & ".join(str(c) for c in cells) + end + "\n" + r"\hline"


def _header_row(header: str | Sequence[str]) -> str:
    if isinstance(header, str):
        row = _strip_row_end(header)
    else:
        bold = styles.TABLE["header_bold"]
        row = " & ".join((rf"\textbf{{{h}}}" if bold else str(h)) for h in header)
    return row


def _hyphenatable(row: str) -> str:
    r"""Allow long heading words to hyphenate in narrow columns.

    TeX never hyphenates the first word of a paragraph, so a single long
    heading such as "Controlling" stuck out of a 1.6 cm column.  A zero-width
    \hspace before each bold heading makes that word hyphenatable.
    """
    return row.replace(r"\textbf{", r"\hspace{0pt}\textbf{")


def _shade(row: str) -> str:
    """Prefix a header row with the shared header background colour."""
    if not styles.TABLE["header_bg"]:
        return row
    # Multi-line headers (with their own \\ or \cline) are left unshaded to
    # avoid colour bleeding across \multirow cells.
    if "\\\\" in row or r"\cline" in row or r"\multirow" in row:
        return row
    return r"\rowcolor{tableHeaderBg}" + row


def build_longtable(
    colspec: str,
    header: str | Sequence[str] | None,
    body: str | Iterable[Sequence[str]],
    *,
    caption: str | None = None,
    label: str | None = None,
    continued: bool = True,
    fit_width: bool = True,
    row_pad: str | None = None,
    tabcolsep_pt: float | None = None,
) -> str:
    """Return the LaTeX for a page-breakable table with repeated headings.

    Parameters
    ----------
    colspec : str
        LaTeX column specification, e.g. ``"|L{5.5cm}|p{10cm}|"``.
    header : str | list[str] | None
        Column headings (None for a parameter/value table without a heading
        row; the caption is then the only thing repeated).  Either a raw LaTeX row (``"\\textbf{a} & \\textbf{b}"``,
        a trailing ``\\\\`` is optional) or a list of plain heading texts that
        will be set in bold.
    body : str | iterable of cell lists
        Raw LaTeX rows (each ending in ``\\\\ ... \\hline``, exactly as the
        chapter templates produce them) or an iterable of cell lists which are
        formatted with :func:`format_row`.
    caption : str, optional
        Caption text (already escaped).  Numbered once; repeated on following
        pages with the "(continued)" suffix.
    label : str, optional
        ``\\label`` attached to the first caption.
    continued : bool
        Add the "Continued on next page" footer at page breaks.
    fit_width : bool
        Scale cm column widths down so the table never exceeds ``\\textwidth``.
    """
    spec = fit_colspec(colspec, tabcolsep_pt=tabcolsep_pt) if fit_width else colspec
    n_cols = parse_colspec(spec)["n_cols"]
    head = _shade(_hyphenatable(_header_row(header))) if header else None

    if isinstance(body, str):
        body_tex = body.strip("\n")
    else:
        body_tex = "\n".join(format_row(r, row_pad) for r in body)
    body_tex = keep_rules_with_rows(keep_multirow_groups(body_tex))

    # The table's closing rule goes into \endlastfoot instead of the body:
    # longtable repeats an \hline that falls exactly at a page break at the
    # top of the next page (a stray rule above the following text was seen
    # after Table 2.11).  The last foot is set together with the last row.
    closing_rule = False
    stripped = body_tex.rstrip()
    if stripped.endswith(r"\hline"):
        body_tex = stripped[: -len(r"\hline")].rstrip()
        closing_rule = True

    table = LongTable(NoEscape(spec), width=n_cols)

    # ---- first-page head -----------------------------------------------------
    if caption:
        lab = rf"\label{{{label}}}" if label else ""
        table.append(NoEscape(rf"\caption{{{caption}}}{lab}\\"))
    table.append(NoEscape(r"\hline"))
    if head:
        table.append(NoEscape(head + r" \\"))
        table.append(NoEscape(r"\hline"))
    table.append(NoEscape(r"\endfirsthead"))

    # ---- head repeated on every following page --------------------------------
    if caption:
        suffix = styles.TABLE["continued_caption_suffix"]
        table.append(NoEscape(rf"\caption[]{{{caption}{suffix}}}\\"))
    table.append(NoEscape(r"\hline"))
    if head:
        table.append(NoEscape(head + r" \\"))
        table.append(NoEscape(r"\hline"))
    table.end_table_header()                     # -> \endhead

    # ---- foot at a page break / after the last row ----------------------------
    if continued:
        note = styles.TABLE["continued_footer_text"]
        font = styles.TYPOGRAPHY["continued_note_font"]
        table.append(NoEscape(
            rf"\multicolumn{{{n_cols}}}{{r}}{{{{{font} {note}}}}} \\"))
    table.end_table_footer()                     # -> \endfoot
    if closing_rule:
        table.append(NoEscape(r"\hline"))
    table.end_table_last_footer()                # -> \endlastfoot

    # ---- body -------------------------------------------------------------------
    if body_tex:
        table.append(NoEscape(body_tex))

    return table.dumps()
