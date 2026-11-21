r"""Longtable helper: make every multi-page table repeat its caption and header.

Conservative by design: a table is rewritten only when it has the standard
shape  \begin{longtable}{spec} [\caption{..}[\label{..}][\\]] \hline <header row> \hline.
Tables with merged header cells, or with their own \endhead/\endfoot
commands, are returned unchanged.
"""
import re

_BEGIN = r"\begin{longtable}"
_END = r"\end{longtable}"
_ENDS = re.compile(r"\\end(?:firsthead|head|foot|lastfoot)\b")


def _group_end(s, i):
    """s[i] == '{'. Return the index just after the matching '}', or -1."""
    depth, j = 0, i
    while j < len(s):
        c = s[j]
        if c == "\\":
            j += 2
            continue
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return j + 1
        j += 1
    return -1


def _row_end(s, i):
    """Index just after the row terminator (a top-level '\\\\' plus optional [..])."""
    depth, j = 0, i
    while j < len(s):
        c = s[j]
        if c == "\\":
            if s[j + 1:j + 2] == "\\" and depth == 0:
                k = j + 2
                if s[k:k + 1] == "[":
                    k = s.index("]", k) + 1
                return k
            j += 2
            continue
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
        j += 1
    return -1


def _ncols(row):
    depth, n, j = 0, 1, 0
    while j < len(row):
        c = row[j]
        if c == "\\":
            j += 2
            continue
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
        elif c == "&" and depth == 0:
            n += 1
        j += 1
    return n


def _skip_ws(s, i):
    while i < len(s) and s[i].isspace():
        i += 1
    return i


def _convert(block):
    i = len(_BEGIN)
    if block[i:i + 1] == "[":
        i = block.index("]", i) + 1
    if block[i:i + 1] != "{":
        return block
    pos = _group_end(block, i)
    if pos < 0:
        return block
    head = block[:pos]
    pos = _skip_ws(block, pos)

    caption = label = ""
    if block.startswith(r"\caption", pos):
        j = pos + len(r"\caption")
        if block[j:j + 1] == "*":
            return block
        if block[j:j + 1] == "[":
            j = block.index("]", j) + 1
        if block[j:j + 1] != "{":
            return block
        end = _group_end(block, j)
        if end < 0:
            return block
        caption = block[pos:end]
        pos = _skip_ws(block, end)
        if block.startswith(r"\label{", pos):
            end = _group_end(block, pos + len(r"\label"))
            if end < 0:
                return block
            label = block[pos:end]
            pos = _skip_ws(block, end)
        if block.startswith("\\\\", pos):
            pos += 2
            if block[pos:pos + 1] == "[":
                pos = block.index("]", pos) + 1
            pos = _skip_ws(block, pos)

    if not block.startswith(r"\hline", pos):
        return block
    pos = _skip_ws(block, pos + len(r"\hline"))
    row_end = _row_end(block, pos)
    if row_end < 0:
        return block
    header = block[pos:row_end].strip()
    if r"\multicolumn" in header or r"\multirow" in header:
        return block
    pos = _skip_ws(block, row_end)
    if not block.startswith(r"\hline", pos):
        return block
    pos += len(r"\hline")
    body = block[pos:]

    m = re.match(r"\s*\\endfirsthead\s*\\endhead", body)   # empty, useless pair
    if m:
        body = body[m.end():]
    if _ENDS.search(body):
        return block                                       # already handled by hand

    n = _ncols(header)
    out = [head]
    if caption:
        out.append(caption + label + "\\\\")
    out += ["\\hline", header, "\\hline", "\\endfirsthead"]
    if caption:
        out.append("\\multicolumn{%d}{l}{\\small\\textit{Table \\thetable\\ (continued)}}\\\\" % n)
    out += ["\\hline", header, "\\hline", "\\endhead"]
    return "\n".join(out) + body


def apply_longtable_headers(tex):
    """Return (new_tex, tables_changed, tables_total)."""
    out, pos, changed, total = [], 0, 0, 0
    while True:
        s = tex.find(_BEGIN, pos)
        if s < 0:
            break
        e = tex.find(_END, s)
        if e < 0:
            break
        e += len(_END)
        block = tex[s:e]
        new = _convert(block)
        total += 1
        changed += new != block
        out += [tex[pos:s], new]
        pos = e
    out.append(tex[pos:])
    return "".join(out), changed, total
