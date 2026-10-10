#!/usr/bin/env python3
"""Build a LaTeX (XeLaTeX) textbook from the wiki.

Usage:  python3 scripts/build_latex.py [--with-draft-notes] [--no-assessments] [--no-watermark] [-o book/latex]

Reads  wiki/chapters/*.md (ordered by `chapter:` frontmatter) and
       wiki/assessments/chNN-assessments.md.
Writes <out>/main.tex            student edition (chapters + quizzes, homework, assignments)
       <out>/main-instructor.tex same, plus an appendix with all answer keys
       <out>/preamble.tex, <out>/chapters/chNN.tex, <out>/keys/chNN-key.tex, <out>/Makefile
Build:  cd book/latex && latexmk -xelatex main.tex      (or: make)

Everything after `<!-- wiki-nav -->` in a wiki page is dropped; text after
`<!-- instructor-key -->` goes to the key files only.
"""
import argparse, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ap = argparse.ArgumentParser()
ap.add_argument("-o", "--output", default=os.path.join(ROOT, "book", "latex"))
ap.add_argument("--with-draft-notes", action="store_true", help="include the red *Draft notes.* boxes (omitted by default)")
ap.add_argument("--no-draft-notes", action="store_true", help=argparse.SUPPRESS)  # kept for compatibility; now the default
ap.add_argument("--chapters", help="comma-separated chapter numbers to include (e.g. 1,2,3); builds a student edition only, for publishing reviewed chapters")
ap.add_argument("--per-chapter", action="store_true", help="with --chapters: also write chapter-N.tex (one chapter plus the disclaimer page) for single-chapter PDFs")
ap.add_argument("--no-assessments", action="store_true")
ap.add_argument("--no-watermark", action="store_true", help="omit the grey DRAFT watermark (on by default)")
args = ap.parse_args()

TITLE = "No-code AI for Young Cambodian Learners"
AUTHOR = "Rina Buoy, PhD"

# ---------------------------------------------------------------- inline text
SPECIAL = {"\\": r"\textbackslash{}", "&": r"\&", "%": r"\%", "$": r"\$", "#": r"\#",
           "_": r"\_", "{": r"\{", "}": r"\}", "~": r"\textasciitilde{}", "^": r"\textasciicircum{}"}
SYMBOLS = {"→": r"\ensuremath{\rightarrow}", "↓": r"\ensuremath{\downarrow}", "↑": r"\ensuremath{\uparrow}",
           "±": r"\ensuremath{\pm}", "×": r"\ensuremath{\times}", "÷": r"\ensuremath{\div}",
           "≈": r"\ensuremath{\approx}", "≤": r"\ensuremath{\leq}", "≥": r"\ensuremath{\geq}",
           "°": r"\textdegree{}", "✓": r"\ensuremath{\checkmark}", "✗": r"\ensuremath{\times}", "⋮": r"\ensuremath{\vdots}",
           "■": r"\ensuremath{\blacksquare}", "\u00a0": "~"}
KHMER = re.compile(r"[\u1780-\u17FF\u19E0-\u19FF]+(?:[ \u1780-\u17FF\u19E0-\u19FF]*[\u1780-\u17FF\u19E0-\u19FF])?")


def esc(t):
    t = "".join(SPECIAL.get(c, c) for c in t)
    # smart quotes
    t = re.sub(r'(^|[\s(\[—–])"', lambda m: m.group(1) + "\u201c", t)
    t = t.replace('"', "\u201d")
    t = re.sub(r"(^|[\s(\[])'", lambda m: m.group(1) + "\u2018", t)
    t = t.replace("'", "\u2019")
    for k, v in SYMBOLS.items():
        t = t.replace(k, v)
    t = KHMER.sub(lambda m: "{\\khmerfont " + m.group(0) + "}", t)
    return t


INLINE = re.compile(r"`([^`]+)`|\[([^\]]+)\]\(([^)]+)\)|\*\*(.+?)\*\*|\*(.+?)\*|@fig:([\w-]+)")


FOOT = re.compile(r"\^\[([^\]]+)\]")
URL = re.compile(r"https?://\S+")


def footnote(t):
    out, pos = [], 0
    for m in URL.finditer(t):
        out.append(esc(t[pos:m.start()]))
        out.append(r"\url{" + m.group(0).replace("%", r"\%").replace("#", r"\#") + "}")
        pos = m.end()
    out.append(esc(t[pos:]))
    return r"\footnote{" + "".join(out) + "}"


def inline(s):
    if FOOT.search(s):
        parts, pos = [], 0
        for m in FOOT.finditer(s):
            parts.append(inline(s[pos:m.start()]))
            parts.append(footnote(m.group(1)))
            pos = m.end()
        parts.append(inline(s[pos:]))
        return "".join(parts)
    out, pos = [], 0
    for m in INLINE.finditer(s):
        out.append(esc(s[pos:m.start()]))
        if m.group(1) is not None:
            out.append(r"\texttt{" + esc(m.group(1)) + "}")
        elif m.group(2) is not None:
            out.append(r"\href{" + m.group(3).replace("%", r"\%").replace("#", r"\#") + "}{" + inline(m.group(2)) + "}")
        elif m.group(4) is not None:
            out.append(r"\textbf{" + inline(m.group(4)) + "}")
        elif m.group(6) is not None:
            out.append(r"\ref{fig:" + m.group(6) + "}")
        else:
            out.append(r"\emph{" + inline(m.group(5)) + "}")
        pos = m.end()
    out.append(esc(s[pos:]))
    return "".join(out)


# ---------------------------------------------------------------- block parser

FIG_SEEN = {}


def figure(caption, spec, params):
    opts = dict(kv.split("=") for kv in params.split(",") if "=" in kv)
    items = []
    for it in spec.split(";"):
        path, _, label = it.strip().partition("|")
        path = re.sub(r"^(\.\./)+", "", path.strip())
        items.append((path, label.strip()))
    base = os.path.splitext(os.path.basename(items[0][0]))[0]
    FIG_SEEN[base] = FIG_SEEN.get(base, 0) + 1
    label = base if FIG_SEEN[base] == 1 else f"{base}-{FIG_SEEN[base]}"
    src = any(p.startswith("figures/slides/") for p, _ in items)
    cap = inline(caption) + (r" \emph{Image from the course slides by Rina Buoy, PhD.}" if src else "")
    w = float(opts.get("w", 0.85))
    if len(items) == 1 and items[0][0].endswith(".tex"):
        body = r"\adjustbox{max width=\linewidth}{\input{" + items[0][0][:-4] + "}}"
    elif len(items) == 1:
        body = r"\includegraphics[width=" + str(w) + r"\linewidth]{" + items[0][0] + "}"
    else:
        cols = int(opts.get("cols", len(items)))
        rows = [items[k:k + cols] for k in range(0, len(items), cols)]
        cw = round(0.96 / cols - 0.01, 3) if "w" not in opts else w
        parts = []
        for row in rows:
            cells = []
            for pth, lab in row:
                cell = r"\begin{minipage}[t]{" + str(cw) + r"\linewidth}\centering\includegraphics[width=\linewidth]{" + pth + "}"
                if lab:
                    cell += r"\\[1pt]{\scriptsize " + inline(lab) + "}"
                cells.append(cell + r"\end{minipage}")
            parts.append(r"\hfill ".join(cells))
        body = (r"\par\medskip ").join(parts)
    return r"\begin{figure}[htbp]" + "\n" + r"\centering" + "\n" + body + "\n" + r"\caption{" + cap + r"}\label{fig:" + label + "}\n" + r"\end{figure}"

def strip_num(t):
    return re.sub(r"^[A-Z0-9]+\.\d+\s+", "", t)


def table(rows):
    cells = [[c.strip() for c in r.strip().strip("|").split("|")] for r in rows]
    header, body = cells[0], cells[2:]
    n = len(header)
    size = r"\footnotesize" if n >= 6 else (r"\small" if n >= 4 else "")
    spec = "".join([r">{\raggedright\arraybackslash}X"] * n)
    L = [r"\begin{center}", size, r"\renewcommand{\arraystretch}{1.15}",
         r"\begin{tabularx}{\linewidth}{" + spec + "}", r"\toprule",
         " & ".join(r"\textbf{" + inline(c) + "}" for c in header) + r" \\", r"\midrule"]
    for r in body:
        r = (r + [""] * n)[:n]
        L.append(" & ".join(inline(c) for c in r) + r" \\")
    L += [r"\bottomrule", r"\end{tabularx}", r"\end{center}"]
    return L


LIST_RE = re.compile(r"^(\s*)([-*]|\d+\.)\s+(.*)$")
OPT_RE = re.compile(r"^\s+[a-d]\)\s")


def convert(md, level=0, glance=True):
    """level 0: '#'=chapter ... ; level 1 (assessments): '#' dropped, '##'=subsection*"""
    lines = md.splitlines()
    out, i, first_quote = [], 0, True
    while i < len(lines):
        ln = lines[i]
        s = ln.strip()
        if not s or re.match(r"^<!--.*-->$", s):
            i += 1
            continue
        m = re.match(r"^(#{1,4})\s+(.*)$", s)
        if m:
            d, text = len(m.group(1)), m.group(2).strip()
            if level == 0:
                if d == 1:
                    text = re.sub(r"^(Chapter\s+\d+|Appendix\s+[A-Z])\.\s*", "", text)
                    out.append(r"\chapter{" + inline(text) + "}")
                elif d == 2:
                    if re.match(r"^[A-Z0-9]+\.\d+\s", text):
                        out.append(r"\section{" + inline(strip_num(text)) + "}")
                    else:
                        out.append(r"\section*{" + inline(text) + "}")
                else:
                    out.append(r"\subsection*{" + inline(text) + "}")
            else:
                if d == 1:
                    pass
                elif d == 2:
                    out.append(r"\subsection*{" + inline(text) + "}")
                else:
                    out.append(r"\subsubsection*{" + inline(text) + "}")
            i += 1
            continue
        if s == "---":
            out.append(r"\medskip\noindent\hrulefill\medskip")
            i += 1
            continue
        if s.startswith(">"):
            blk = []
            while i < len(lines) and lines[i].strip().startswith(">"):
                blk.append(lines[i].strip()[1:].strip())
                i += 1
            txt = " ".join(x for x in blk if x)
            env = "glancebox" if (glance and first_quote and txt.startswith("**Chapter at a glance")) else "notebox"
            if env == "glancebox":
                txt = re.sub(r"^\*\*Chapter at a glance\.\*\*\s*", "", txt)
            first_quote = False
            out.append(r"\begin{" + env + "}\n" + inline(txt) + "\n" + r"\end{" + env + "}")
            continue
        if s.startswith("|") and i + 1 < len(lines) and re.match(r"^\s*\|[\s:|-]+\|\s*$", lines[i + 1]):
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                rows.append(lines[i])
                i += 1
            out += table(rows)
            continue
        im = re.match(r"^!\[(.*?)\]\((.*?)\)(?:\{(.*?)\})?$", s)
        if im:
            out.append(figure(im.group(1), im.group(2), im.group(3) or ""))
            i += 1
            continue
        lm = LIST_RE.match(ln)
        if lm and not re.match(r"^\*[^*]", s.replace("**", "")) or (lm and lm.group(2) == "-"):
            ordered = lm.group(2)[0].isdigit()
            start = int(lm.group(2)[:-1]) if ordered else 1
            items = []
            while i < len(lines):
                l2 = lines[i]
                m2 = LIST_RE.match(l2)
                if m2 and len(m2.group(1)) == 0 and (m2.group(2)[0].isdigit() == ordered):
                    items.append({"t": m2.group(3), "opts": [], "sub": []})
                    i += 1
                elif l2.startswith((" ", "\t")) and items and l2.strip():
                    if OPT_RE.match(l2):
                        items[-1]["opts"] += re.split(r"\s{2,}(?=[a-d]\)\s)", l2.strip())
                    elif LIST_RE.match(l2):
                        items[-1]["sub"].append(LIST_RE.match(l2).group(3))
                    else:
                        items[-1]["t"] += " " + l2.strip()
                    i += 1
                else:
                    break
            env = "enumerate" if ordered else "itemize"
            opt = f"[start={start}]" if ordered and start != 1 else ""
            lst = [r"\begin{" + env + "}" + opt]
            for it in items:
                body = r"\item " + inline(it["t"])
                if it["opts"]:
                    body += "\n" + r"\begin{enumerate}[label=\alph*),nosep,leftmargin=1.6em]" + "\n"
                    body += "\n".join(r"\item " + inline(re.sub(r"^[a-d]\)\s*", "", o)) for o in it["opts"])
                    body += "\n" + r"\end{enumerate}"
                if it["sub"]:
                    body += "\n" + r"\begin{itemize}[nosep]" + "\n" + "\n".join(r"\item " + inline(x) for x in it["sub"]) + "\n" + r"\end{itemize}"
                lst.append(body)
            lst.append(r"\end{" + env + "}")
            out.append("\n".join(lst))
            continue
        # paragraph
        para = []
        while i < len(lines) and lines[i].strip() and not re.match(r"^(#{1,4}\s|>|\||---$|<!--|!\[)", lines[i].strip()) and not (LIST_RE.match(lines[i]) and para and False):
            para.append(lines[i].strip())
            i += 1
            if i < len(lines) and LIST_RE.match(lines[i]):
                break
        txt = " ".join(para)
        if txt.startswith("*Figure suggestion:*"):
            out.append(r"\begin{figbox}" + "\n" + inline(txt) + "\n" + r"\end{figbox}")
        elif txt.startswith("*Draft notes.*"):
            if args.with_draft_notes and not args.no_draft_notes:
                out.append(r"\begin{draftbox}" + "\n" + inline(txt) + "\n" + r"\end{draftbox}")
        else:
            out.append(inline(txt) + "\n")
    return "\n\n".join(x for x in out)


# ---------------------------------------------------------------- read wiki
def frontmatter(t):
    m = re.match(r"---\n(.*?)\n---\n", t, re.S)
    return (m.group(1), t[m.end():]) if m else ("", t)


chapters = []
cdir = os.path.join(ROOT, "wiki", "chapters")
for f in os.listdir(cdir):
    if not f.endswith(".md"):
        continue
    fm, body = frontmatter(open(os.path.join(cdir, f), encoding="utf-8").read())
    n = re.search(r"^chapter:\s*(\d+)", fm, re.M)
    if n:
        chapters.append((int(n.group(1)), body.split("<!-- wiki-nav -->")[0].strip()))
chapters.sort()

import shutil
fsrc = os.path.join(ROOT, "wiki", "figures")
if os.path.isdir(fsrc):
    shutil.copytree(fsrc, os.path.join(args.output, "figures"), dirs_exist_ok=True)
os.makedirs(os.path.join(args.output, "chapters"), exist_ok=True)
os.makedirs(os.path.join(args.output, "keys"), exist_ok=True)
SEL = {int(x) for x in args.chapters.split(",")} if args.chapters else None
for n, body in chapters:
    tex = convert(body, 0)   # always converted so figure labels stay the same
    if SEL is not None and n not in SEL:
        continue
    key_tex = ""
    if not args.no_assessments:
        ap_ = os.path.join(ROOT, "wiki", "assessments", f"ch{n:02d}-assessments.md")
        if os.path.exists(ap_):
            _, at = frontmatter(open(ap_, encoding="utf-8").read())
            at = at.split("<!-- wiki-nav -->")[0]
            student, _, key = at.partition("<!-- instructor-key -->")
            tex += "\n\n" + r"\section*{Assessments}" + "\n\n" + r"\addcontentsline{toc}{section}{Assessments}" + "\n\n" + convert(student, 1)
            key_tex = r"\section*{Chapter " + str(n) + r" answer key}" + "\n\n" + convert(key, 1)
    open(os.path.join(args.output, "chapters", f"ch{n:02d}.tex"), "w", encoding="utf-8").write(tex + "\n")
    open(os.path.join(args.output, "keys", f"ch{n:02d}-key.tex"), "w", encoding="utf-8").write(key_tex + "\n")

appendices = []
adir = os.path.join(ROOT, "wiki", "appendices")
if os.path.isdir(adir):
    for f in sorted(os.listdir(adir)):
        if f.endswith(".md"):
            fm, body = frontmatter(open(os.path.join(adir, f), encoding="utf-8").read())
            if re.search(r"^appendix:\s*[A-Z]", fm, re.M):
                appendices.append(convert(body.split("<!-- wiki-nav -->")[0].strip(), 0))
os.makedirs(os.path.join(args.output, "appendices"), exist_ok=True)
for k, tex in enumerate(appendices):
    open(os.path.join(args.output, "appendices", f"app{k+1}.tex"), "w", encoding="utf-8").write(tex + "\n")
about_tex = ""
ap = os.path.join(ROOT, "wiki", "back-matter", "about-the-author.md")
if os.path.exists(ap):
    _, ab = frontmatter(open(ap, encoding="utf-8").read())
    about_tex = (r"\chapter*{About the Author}" + "\n" + r"\addcontentsline{toc}{chapter}{About the Author}" + "\n"
                 + r"\begin{center}\includegraphics[width=0.38\linewidth]{figures/provided/author.jpg}\end{center}" + "\n\n"
                 + convert(ab.strip(), 1) + "\n")
open(os.path.join(args.output, "about.tex"), "w", encoding="utf-8").write(about_tex)
app_inc = ("\\appendix\n" + "\n".join(rf"\input{{appendices/app{k+1}}}" for k in range(len(appendices)))) if appendices else ""

PREAMBLE = r"""% Generated by scripts/build_latex.py. Compile with XeLaTeX (needed for Khmer text).
\documentclass[11pt,a4paper,openany]{book}
\usepackage{fontspec}
\usepackage[a4paper,margin=2.5cm]{geometry}
\usepackage{amssymb}
\usepackage{xcolor}
\usepackage{microtype}
\usepackage{setspace}
\usepackage{enumitem}
\usepackage{booktabs,tabularx,array}
\usepackage[most]{tcolorbox}
\usepackage{fancyhdr}
\usepackage{graphicx}
\usepackage{adjustbox}
\usepackage{tikz}
\usetikzlibrary{positioning,arrows.meta,calc}
\usepackage[font=small,labelfont=bf,labelsep=period]{caption}
\usepackage{titlesec}
\usepackage[hidelinks,unicode]{hyperref}
\setstretch{1.08}

% ---- fonts (edit to taste) ----------------------------------------------
\IfFontExistsTF{Noto Sans Khmer}{\newfontfamily\khmerfont[Script=Khmer]{Noto Sans Khmer}}{%
 \IfFontExistsTF{Khmer Sangam MN}{\newfontfamily\khmerfont[Script=Khmer]{Khmer Sangam MN}}{%
 \IfFontExistsTF{Khmer OS}{\newfontfamily\khmerfont[Script=Khmer]{Khmer OS}}{\let\khmerfont\relax}}}
\IfFontExistsTF{DejaVu Sans}{\newfontfamily\symfont{DejaVu Sans}}{%
 \IfFontExistsTF{Noto Sans Symbols 2}{\newfontfamily\symfont{Noto Sans Symbols 2}}{%
 \IfFontExistsTF{Apple Symbols}{\newfontfamily\symfont{Apple Symbols}}{\let\symfont\relax}}}

\tikzset{box/.style={draw,rounded corners=3pt,fill=white,align=center,minimum height=1cm,inner sep=5pt,font=\small},arrow/.style={-{Stealth[length=2mm]},thick}}
% ---- colours and boxes ---------------------------------------------------
\definecolor{accent}{HTML}{1F5F8B}
\definecolor{glancebg}{HTML}{EAF2F8}
\definecolor{notebg}{HTML}{FFF7E0}
\definecolor{figbg}{HTML}{F1F1F1}
\definecolor{draftbg}{HTML}{FDECEC}
\newtcolorbox{glancebox}{enhanced,breakable,colback=glancebg,colframe=accent,boxrule=0.6pt,arc=2mm,left=3mm,right=3mm,top=2mm,bottom=2mm,title={At a glance},fonttitle=\bfseries}
\newtcolorbox{notebox}{enhanced,breakable,colback=notebg,colframe=orange!70!black,boxrule=0.4pt,arc=1.5mm,left=3mm,right=3mm,top=1.5mm,bottom=1.5mm}
\newtcolorbox{figbox}{enhanced,breakable,colback=figbg,colframe=gray,boxrule=0.4pt,arc=1mm,left=3mm,right=3mm,top=1.5mm,bottom=1.5mm,title={Figure placeholder},fonttitle=\small\bfseries}
\newtcolorbox{draftbox}{enhanced,breakable,colback=draftbg,colframe=red!60!black,boxrule=0.4pt,arc=1mm,left=3mm,right=3mm,top=1.5mm,bottom=1.5mm,title={Draft note},fonttitle=\small\bfseries}

% ---- headings and page style --------------------------------------------
\titleformat{\chapter}[display]{\normalfont\bfseries\color{accent}}{\Large \chaptertitlename\ \thechapter}{0.6em}{\Huge}
\titlespacing*{\chapter}{0pt}{-10pt}{24pt}
\titleformat{\section}{\normalfont\Large\bfseries\color{accent}}{\thesection}{0.6em}{}
\titleformat{\subsection}{\normalfont\large\bfseries}{\thesubsection}{0.6em}{}
\pagestyle{fancy}
\fancyhf{}
\fancyhead[LE]{\small\nouppercase{\leftmark}}
\fancyhead[RO]{\small\nouppercase{\rightmark}}
\fancyfoot[C]{\thepage}
\setlength{\parindent}{0pt}
\setlength{\parskip}{0.6em}
\setlist{itemsep=0.25em,topsep=0.3em,parsep=0pt}
"""
WATERMARK = r"""
% ---- draft watermark (build with --no-watermark to remove) ---------------
\usepackage{draftwatermark}
\SetWatermarkText{DRAFT}
\SetWatermarkScale{1.1}
\SetWatermarkColor[gray]{0.88}
"""
open(os.path.join(args.output, "preamble.tex"), "w", encoding="utf-8").write(PREAMBLE + ("" if args.no_watermark else WATERMARK))

nums = [n for n, _ in chapters if SEL is None or n in SEL]
inc = "\n".join(rf"\include{{chapters/ch{n:02d}}}" for n in nums)
keys = "\n".join(rf"\input{{keys/ch{n:02d}-key}}" for n in nums)
COVER = r"""\begin{titlepage}
\thispagestyle{empty}
\definecolor{covernavy}{HTML}{0F2A4A}
\definecolor{coveraccent}{HTML}{F2A33A}
\begin{tikzpicture}[remember picture,overlay]
  \fill[covernavy] (current page.south west) rectangle (current page.north east);
  \node[anchor=south,inner sep=0pt] at (current page.south) {\includegraphics[width=\paperwidth]{figures/provided/cover-class-illustration.png}};
  \fill[covernavy] (current page.north west) rectangle ([yshift=-10.6cm]current page.north east);
  \fill[coveraccent] ([yshift=-1.6cm]current page.north west) rectangle ([yshift=-1.85cm]current page.north east);
  \node[anchor=north,text=white,align=center,text width=17cm] at ([yshift=-2.7cm]current page.north)
     {\centering{\fontsize{14}{18}\selectfont\textcolor{coveraccent}{\textsc{Build Your Own AI \textperiodcentered{} Grades 7--12}}\par}\vspace{7mm}
      {\fontsize{40}{46}\selectfont\bfseries\spaceskip=0.33em plus 0.1em No-code AI for Young Cambodian Learners\par}\vspace{6mm}
      {\fontsize{15}{20}\selectfont A hands-on guide to building AI with Google Teachable Machine\par}};
  \fill[covernavy,opacity=0.9] (current page.south west) rectangle ([yshift=3.2cm]current page.south east);
  \node[anchor=center,text=white,align=center] at ([yshift=1.9cm]current page.south)
     {\fontsize{22}{26}\selectfont\bfseries Rina Buoy, PhD};
  \node[anchor=south,text=white!70,align=center] at ([yshift=0.5cm]current page.south)
     {\small Draft edition};
  \node[anchor=west,inner sep=0pt] at ([xshift=1.8cm,yshift=1.7cm]current page.south west) {\includegraphics[height=1.9cm]{figures/provided/rinai-logo.png}};
  \node[anchor=east,text=white!80,align=right] at ([xshift=-1.8cm,yshift=1.7cm]current page.south east) {\small RinAI Academy\\ academy.rinabuoy.com};
\end{tikzpicture}
\end{titlepage}
\clearpage
\thispagestyle{empty}
\null\vfill
{\small\noindent\textbf{No-code AI for Young Cambodian Learners}\\ \copyright{} Rina Buoy, PhD. Draft edition.\\ Course website: \url{https://academy.rinabuoy.com}\\ Cover illustration and author photo: courtesy of the author.\\[6pt]
\textbf{Disclaimer.} This book was prepared with the assistance of Claude Code, an AI tool from Anthropic. The author provides the content and reviews and revises all of the outputs.}
\clearpage
"""
_cut = COVER.index("\\clearpage\n\\thispagestyle{empty}\n\\null")
open(os.path.join(args.output, "cover.tex"), "w", encoding="utf-8").write(COVER[:_cut] + "\\input{copyright}\n")
open(os.path.join(args.output, "copyright.tex"), "w", encoding="utf-8").write(COVER[_cut:])
FRONT = rf"""\input{{preamble}}
\title{{\Huge\bfseries {TITLE}\\[0.6em]\Large A hands-on guide to building AI with Google Teachable Machine}}
\author{{{AUTHOR}}}
\date{{}}
\begin{{document}}
\frontmatter
\input{{cover}}
\tableofcontents
\mainmatter
{inc}
{app_inc}
\input{{about}}
"""
open(os.path.join(args.output, "main.tex"), "w", encoding="utf-8").write(FRONT + "\\end{document}\n")
if args.per_chapter and SEL is not None:
    for n in nums:
        open(os.path.join(args.output, f"chapter-{n}.tex"), "w", encoding="utf-8").write(
            "\\input{preamble}\n\\begin{document}\n\\mainmatter\n\\setcounter{chapter}{" + str(n - 1) + "}\n"
            "\\input{copyright}\n\\input{chapters/ch" + f"{n:02d}" + "}\n\\end{document}\n")
if SEL is None:
    open(os.path.join(args.output, "main-instructor.tex"), "w", encoding="utf-8").write(
        FRONT + ("" if app_inc else "\\appendix\n") + "\\chapter{Instructor answer keys}\n" + keys + "\n\\end{document}\n")
MAKE_ALL = ("all:\n\t@for f in main" + "".join(f" chapter-{n}" for n in nums if args.per_chapter) + "; do if [ \"$(ENGINE)\" = latexmk ]; then latexmk -xelatex -interaction=nonstopmode $$f.tex; else tectonic -X compile $$f.tex; fi; done\n\nclean:\n\trm -f *.aux *.log *.toc *.out *.fls *.fdb_latexmk *.xdv\n") if SEL is not None else None
FULL_ALL = ("all:\n\t@if [ \"$(ENGINE)\" = latexmk ]; then latexmk -xelatex -interaction=nonstopmode main.tex && latexmk -xelatex -interaction=nonstopmode main-instructor.tex; "
            "else tectonic -X compile main.tex && tectonic -X compile main-instructor.tex; fi\n\nclean:\n\trm -f *.aux *.log *.toc *.out *.fls *.fdb_latexmk *.xdv\n")
open(os.path.join(args.output, "Makefile"), "w").write(
    "# Uses latexmk (TeX Live / MacTeX) if present, otherwise tectonic (brew install tectonic).\n"
    "ENGINE := $(shell command -v latexmk >/dev/null 2>&1 && echo latexmk || echo tectonic)\n\n" + (MAKE_ALL or FULL_ALL))

if SEL is not None:   # keep only the figure files the selected chapters, appendices and cover use
    used = set()
    for root_, _, fs_ in os.walk(args.output):
        for f_ in fs_:
            if f_.endswith(".tex"):
                txt = open(os.path.join(root_, f_), encoding="utf-8").read()
                used |= set(re.findall(r"figures/[\w./-]+", txt))
    fig_root = os.path.join(args.output, "figures")
    for root_, _, fs_ in os.walk(fig_root):
        for f_ in fs_:
            rel = os.path.relpath(os.path.join(root_, f_), args.output)
            if not any(u == rel or u + ".tex" == rel for u in used):
                os.remove(os.path.join(root_, f_))
    for root_, dirs_, fs_ in os.walk(fig_root, topdown=False):
        if not os.listdir(root_):
            os.rmdir(root_)

# ---------------------------------------------------------------- sanity check
problems = 0
for d in ("chapters", "keys"):
    for f in sorted(os.listdir(os.path.join(args.output, d))):
        t = open(os.path.join(args.output, d, f), encoding="utf-8").read()
        flat = re.sub(r"\\[\\{}%$&#_^~]", "", t)
        issues = []
        if flat.count("{") != flat.count("}"):
            issues.append("unbalanced braces")
        b, e = len(re.findall(r"\\begin\{", t)), len(re.findall(r"\\end\{", t))
        if b != e:
            issues.append(f"begin/end {b}/{e}")
        for bad in ("**", "[[", "](", "|---"):
            if bad in t:
                issues.append(f"leftover markdown {bad!r}")
        if issues:
            problems += 1
            print("CHECK", d, f, issues)
print(f"Wrote {len(nums)} chapters to {args.output}; sanity problems: {problems}")
