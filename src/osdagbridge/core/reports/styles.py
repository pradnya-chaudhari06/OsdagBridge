"""Single source of truth for the OsdagBridge design-report look and feel.

Every colour, page dimension, table spacing, column type and header/footer
rule used by the LaTeX preamble lives here. Chapter files must import from
this module instead of hard-coding formatting values.
"""

# ---- Colours (HTML hex without '#') ---------------------------------------
COLORS = {
    "osdagGreen": "91B014",
    "osdagFail": "FF0000",   # FAIL status text (was \textcolor{red})
    "osdagPass": "000000",   # PASS status text (was \textcolor{black})
    "osdagInfo": "0000FF",   # informational lines (was \textcolor{blue})
}

# ---- Document / page ------------------------------------------------------
DOCUMENT_OPTIONS = "12pt,a4paper"
GEOMETRY_OPTIONS = "a4paper, margin=1in, headheight=18pt"
LINE_STRETCH = "1.15"

# ---- Tables ---------------------------------------------------------------
TABCOLSEP = "6pt"
ARRAYSTRETCH = "1.12"
ARRAYRULEWIDTH = "0.5pt"
EXTRAROWHEIGHT = "0.6pt"
LT_LEFT = r"\fill"
LT_RIGHT = r"\fill"
LT_PRE = "0pt"
LT_POST = "6pt"
TABLE_NEEDSPACE = r"5\baselineskip"
HEADER_ROW_SKIP = "6pt"          # value of \OsdagRowSkip, the gap after a table row

COLUMN_TYPES = (
    ("L", r">{\raggedright\arraybackslash}p{#1}"),
    ("C", r">{\centering\arraybackslash}p{#1}"),
    ("R", r">{\raggedleft\arraybackslash}p{#1}"),
)

# ---- Header / footer ------------------------------------------------------
RULE_WIDTH = "1pt"
FOOTER_LEFT = r"Osdag $|$ FOSSEE $|$ Indian Institute of Technology Bombay"
FOOTER_RIGHT = r"Page \thepage\ of \pageref{LastPage}"

_PAGESTYLE = r"""\fancypagestyle{@NAME@}{
  \fancyhf{}
  \fancyhead[L]{@HL@}
  \fancyhead[R]{@HR@}
  \fancyfoot[L]{@FL@}
  \fancyfoot[R]{@FR@}
  \renewcommand{\headrule}{\color{osdagGreen}\hrule width\headwidth height @RULE@ \vspace{2pt}}
  \renewcommand{\footrule}{%
    \ifbool{hasSDonPage}{%
      \vspace{-20pt}%
      \hbox to \headwidth{\textcolor{black}{\footnotesize\textit{* Software default value}}\hfil}%
      \vspace{4pt}%
    }{%
      \vspace{-8pt}%
    }%
    \color{osdagGreen}\hrule width\headwidth height @RULE@ \vspace{6pt}%
  }
}
"""

_FIRSTPAGE = r"""\fancypagestyle{firstpage}{
  \fancyhf{}
  \renewcommand{\headrulewidth}{0pt}
  \fancyfoot[L]{@FL@}
  \fancyfoot[R]{@FR@}
  \renewcommand{\footrule}{\vspace{-8pt}\color{osdagGreen}\hrule width\headwidth height @RULE@ \vspace{6pt}}
}
"""

_PREAMBLE = r"""
\documentclass[@DOCOPTS@]{report}

% Packages
\usepackage[@GEOM@]{geometry}
\usepackage{graphicx}
\usepackage{amsmath}
\usepackage{amssymb}
\usepackage{booktabs}
\usepackage{array}
\usepackage{tabularx}
\usepackage{float}
\usepackage{fancyhdr}
\usepackage[hidelinks]{hyperref}
\usepackage{xcolor}
\usepackage{setspace}
\usepackage{enumitem}
\usepackage{caption}

\captionsetup{
    labelfont=bf,
    justification=raggedright,
    singlelinecheck=false,
    format=plain
}
\usepackage{subcaption}
\usepackage{multirow}
\usepackage{colortbl}
\usepackage{longtable}
\setlength{\LTleft}{@LTLEFT@}
\setlength{\LTright}{@LTRIGHT@}
\usepackage{titlesec}
\usepackage{titletoc}
\usepackage{lastpage}
\usepackage{makecell}
\usepackage{etoolbox}
\usepackage{needspace}

\numberwithin{table}{chapter}
\numberwithin{figure}{chapter}
% Table layout and spacing: consistent padding, row height, and longtable pre/post skips
\setlength{\tabcolsep}{@TABCOLSEP@}
\renewcommand{\arraystretch}{@ARRAYSTRETCH@}
\setlength{\LTpre}{@LTPRE@}
\setlength{\LTpost}{@LTPOST@}
% Table rules (outline thickness) and small extra row height for clarity
\setlength{\arrayrulewidth}{@RULEW@}
\setlength{\extrarowheight}{@EXTRAROW@}

% Prevent tables from overflowing past the page bottom:
% if fewer than 5 baseline-skips remain, break to the next page first.
\BeforeBeginEnvironment{table}{\needspace{@NEEDSPACE@}}
\BeforeBeginEnvironment{longtable}{\needspace{@NEEDSPACE@}}

@COLOURS@

@PAGESTYLES@
\pagestyle{main}
\setstretch{@STRETCH@}

% Custom Commands
\newcommand{\OsdagRowSkip}{@ROWSKIP@}
\newcommand{\placeholder}[1]{\textit{\textless #1\textgreater}}
\newcommand{\todo}[1]{\colorbox{yellow}{TODO: #1}}
@COLTYPES@

% Software-default asterisk
\newcommand{\sdstar}{\textsuperscript{*}}
\newbool{hasSDonPage}
\boolfalse{hasSDonPage}
\newcommand{\markSD}{\global\booltrue{hasSDonPage}}
\renewcommand{\sdstar}{\textsuperscript{*}\markSD{}}
\AddToHook{shipout/before}{\global\boolfalse{hasSDonPage}}

\title{\Large\textbf{OsdagBridge} \\ \normalsize Open Source Software for Steel Girder Bridge Design \\ \vspace{2cm} \large Design Report}
\author{}
\date{}

\begin{document}
"""


def _fill(template, **tokens):
    for key, value in tokens.items():
        template = template.replace("@" + key + "@", value)
    return template


def build_preamble(pn, jn, rd, rv):
    """Return the full LaTeX preamble. Arguments must already be LaTeX-escaped."""
    hl = pn + r" $|$ " + jn
    hr = rd + r" $|$ " + rv
    styles = "".join(
        _fill(_PAGESTYLE, NAME=n, HL=hl, HR=hr, FL=FOOTER_LEFT, FR=FOOTER_RIGHT, RULE=RULE_WIDTH)
        for n in ("main", "plain")
    ) + _fill(_FIRSTPAGE, FL=FOOTER_LEFT, FR=FOOTER_RIGHT, RULE=RULE_WIDTH)
    return _fill(
        _PREAMBLE,
        DOCOPTS=DOCUMENT_OPTIONS, GEOM=GEOMETRY_OPTIONS, STRETCH=LINE_STRETCH,
        LTLEFT=LT_LEFT, LTRIGHT=LT_RIGHT, LTPRE=LT_PRE, LTPOST=LT_POST,
        TABCOLSEP=TABCOLSEP, ARRAYSTRETCH=ARRAYSTRETCH, RULEW=ARRAYRULEWIDTH,
        EXTRAROW=EXTRAROWHEIGHT, NEEDSPACE=TABLE_NEEDSPACE, ROWSKIP=HEADER_ROW_SKIP,
        COLOURS="\n".join(r"\definecolor{%s}{HTML}{%s}" % kv for kv in COLORS.items()),
        COLTYPES="\n".join(r"\newcolumntype{%s}[1]{%s}" % kv for kv in COLUMN_TYPES),
        PAGESTYLES=styles.rstrip("\n"),
    )

# ---------------------------------------------------------------------------
# Chart style (used by charts.py: UR bar charts and material quantity charts)
# ---------------------------------------------------------------------------
CHART_DPI = 200
CHART_FIGSIZE = (6.4, 3.4)
CHART_OK_COLOR = "#4C78A8"
CHART_FAIL_COLOR = "#D62728"
CHART_LIMIT_COLOR = "#D62728"
CHART_STEEL_COLOR = "#4C78A8"
CHART_CONCRETE_COLOR = "#8C8C8C"
CHART_REBAR_COLOR = "#F58518"
CHART_FONT_SIZE = 9
