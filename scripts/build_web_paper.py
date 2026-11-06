"""Build the web reader docs/paper/ from paper/main.tex (same text and numbers as the PDF).

pandoc renders the LaTeX source with paper/reader.html: masthead, abstract, a results strip read from results/tables,
contents, numbered sections, references and appendices. Numbers for sections, tables, figures and equations are
assigned here in document order, the way LaTeX assigns them, and every cross-reference becomes a link. paper.pdf and
the PNG versions of the figures are copied next to the page; GitHub Pages serves docs/ at
https://thanatchon36.github.io/stablerun/. Requires pandoc on PATH; the script stops on anything it cannot resolve.

Usage: python scripts/build_web_paper.py
"""
from __future__ import annotations

import csv
import html
import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAPER = ROOT / "paper"
TABLES = ROOT / "results" / "tables"
OUT = ROOT / "docs" / "paper"

REPO_URL = "https://github.com/thanatchon36/stablerun"
PAPER_URL = "https://thanatchon36.github.io/stablerun/paper/"
DATA_URL = "https://huggingface.co/datasets/thanatchon36/stablerun"
DOI = "10.5281/zenodo.23996044"
SUBTITLE = "An Agent-Based Stress Test"
WIDE_FORMULA = 30  # characters of LaTeX source above which an inline formula may not fit a phone screen


def braced(tex: str, start: int) -> tuple[str, int]:
    """The contents of the {...} group opening at tex[start], and the index just past its closing brace."""
    if tex[start] != "{":
        raise ValueError(f"expected a brace group at: {tex[start:start + 40]!r}")
    depth = 0
    for i in range(start, len(tex)):
        if tex[i] == "\\":
            continue
        if tex[i] == "{" and tex[i - 1] != "\\":
            depth += 1
        elif tex[i] == "}" and tex[i - 1] != "\\":
            depth -= 1
            if depth == 0:
                return tex[start + 1 : i], i + 1
    raise ValueError(f"unbalanced group at: {tex[start:start + 40]!r}")


def expand_inputs(tex: str) -> str:
    return re.sub(
        r"\\input\{([^}]+)\}",
        lambda m: expand_inputs((PAPER / f"{m.group(1)}.tex").read_text(encoding="utf-8")),
        tex,
    )


def unwrap_adjustbox(tex: str) -> str:
    """adjustbox only sizes a table for the page; the browser scrolls instead."""
    marker = r"\adjustbox{max width=\textwidth}"
    while marker in tex:
        i = tex.index(marker)
        inner, end = braced(tex, i + len(marker))
        tex = tex[:i] + inner + tex[end:]
    return tex


def simplify_tabulars(tex: str) -> str:
    """Reduce the print-oriented tabulars to the plain form pandoc reads correctly.

    Left alone, pandoc splits a table at a nested tabular, drops the first word of a cell in a column with a >{...}
    prefix, spills a second \\cmidrule into the next row and blanks a \\multicolumn row after \\addlinespace, so stacked
    headers are flattened, column specs cut down to their alignment letters and partial rules and spacing removed.
    """
    tex = re.sub(r"\\cmidrule(?:\([a-z]*\))?\{[^}]*\}|\\addlinespace(?:\[[^]]*\])?", "", tex)
    tex = re.sub(
        r"\\begin\{tabular\}\[b\]\{(?:[^{}]|\{[^{}]*\})*\}(.*?)\\end\{tabular\}",
        lambda m: m.group(1).replace("\\\\", " "),
        tex, flags=re.DOTALL,
    )

    def alignment(spec: str) -> str:
        spec = re.sub(r"[@>]\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}", "", spec)
        return re.sub(r"p\{[^}]*\}", "l", spec)

    out, pos = [], 0
    for m in re.finditer(r"\\begin\{tabular\}|\\multicolumn\{\d+\}", tex):
        spec, end = braced(tex, m.end())
        out += [tex[pos : m.end()], "{", alignment(spec), "}"]
        pos = end
    tex = "".join(out) + tex[pos:]
    tex = re.sub(r"\{\\itshape ([^{}]*)\}", r"{\\emph{\1}}", tex)
    return tex.replace("\\quad ", "~~")


def clean_for_pandoc(tex: str) -> str:
    """Remove page-layout commands pandoc has no use for."""
    tex = simplify_tabulars(unwrap_adjustbox(tex))
    tex = tex.replace(r"\bibliography{refs}", "\\section*{References}\\label{references}\n\nREFERENCES-GO-HERE\n")
    for pattern in (
        r"\\FloatBarrier",
        r"\\bibliographystyle\{[^}]*\}",
        r"\\titleformat\{\\section\}.*",
        r"\\begin\{small\}",
        r"\\end\{small\}",
        r"\\setlength\{\\(?:itemsep|tabcolsep)\}\{[^}]*\}",
        r"\\renewcommand\{\\arraystretch\}\{[^}]*\}",
        r"\\hangindent=\S+\\hangafter=\S+\s",
    ):
        tex = re.sub(pattern, "", tex)
    return tex


def number_document(tex: str) -> tuple[str, list[tuple[str, str]], dict[str, str]]:
    """Number floats, equations and sections in document order, then turn every \\ref into a link.

    Returns the rewritten LaTeX, the (id, number) of each display equation and the label-to-number map. pandoc cannot
    number equations or letter appendices, so finish_html() adds those to its output.
    """
    labels: dict[str, str] = {}

    # Sections and subsections: letters after \appendix, as in the PDF.
    section, subsection, in_appendix = 0, 0, False
    for m in re.finditer(r"\\appendix\b|\\(section|subsection)(\*?)\{|\\label\{([^}]+)\}|\\begin\{equation\}|"
                         r"\\begin\{(?:table|figure)\}", tex):
        if m.group(0) == r"\appendix":
            section, subsection, in_appendix = 0, 0, True
        elif m.group(1) == "section" and not m.group(2):
            section, subsection = section + 1, 0
        elif m.group(1) == "subsection" and not m.group(2):
            subsection += 1
        elif m.group(3) and m.group(3).startswith(("sec:", "app:")):
            major = chr(ord("A") + section - 1) if in_appendix else str(section)
            labels[m.group(3)] = f"{major}.{subsection}" if subsection else major

    # Floats: one counter per kind, continuing through the appendices (the preamble does not reset them).
    counts = {"table": 0, "figure": 0}

    def number_float(m: re.Match) -> str:
        kind, block = m.group(1), m.group(0)
        counts[kind] += 1
        label = re.search(r"\\label\{([^}]+)\}", block)
        if not label:
            raise ValueError(f"unlabelled {kind}: {block[:80]!r}")
        labels[label.group(1)] = str(counts[kind])
        block = block.replace(label.group(0), "")
        tag = rf"\hypertarget{{{label.group(1)}}}{{\textbf{{{kind.capitalize()} {counts[kind]}.}}}} "
        return block.replace(r"\caption{", r"\caption{" + tag, 1)

    tex = re.sub(r"\\begin\{(table|figure)\}.*?\\end\{\1\}", number_float, tex, flags=re.DOTALL)

    # Equations: unlabelled ones are numbered too.
    equations: list[tuple[str, str]] = []

    def number_equation(m: re.Match) -> str:
        number = str(len(equations) + 1)
        label = re.search(r"\\label\{([^}]+)\}", m.group(0))
        eq_id = label.group(1) if label else f"eq:{number}"
        labels[eq_id] = number
        equations.append((eq_id, number))
        return m.group(0).replace(label.group(0), "") if label else m.group(0)

    tex = re.sub(r"\\begin\{equation\}.*?\\end\{equation\}", number_equation, tex, flags=re.DOTALL)

    def link(m: re.Match) -> str:
        if m.group(1) not in labels:
            raise ValueError(f"undefined reference: {m.group(1)}")
        return rf"\href{{#{m.group(1)}}}{{{labels[m.group(1)]}}}"

    return re.sub(r"\\ref\{([^}]+)\}", link, tex), equations, labels


def pandoc(tex: str, *args: str) -> str:
    if shutil.which("pandoc") is None:
        raise RuntimeError("pandoc not found; install pandoc to build the web reader")
    return subprocess.run(
        ["pandoc", "--from=latex", "--to=html5", "--mathml", "--wrap=none", *args],
        input=tex, capture_output=True, text=True, check=True, cwd=str(PAPER),
    ).stdout


def read_csv(name: str) -> list[dict[str, str]]:
    with open(TABLES / name, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def pick(rows: list[dict[str, str]], **match: str) -> dict[str, str]:
    found = [r for r in rows if all(r[k] == v for k, v in match.items())]
    if len(found) != 1:
        raise ValueError(f"expected one row for {match}, found {len(found)}")
    return found[0]


def grid_mean(rows: list[dict[str, str]], column: str, **match: str) -> float:
    """Main effect in the E3 grid: the mean over the cells that match, excluding the redemption-basis rows."""
    found = [float(r[column]) for r in rows if r["cash_buffer"] not in ("par", "nav")
             and all(float(r[k]) == float(v) for k, v in match.items())]
    if not found:
        raise ValueError(f"no grid cells for {match}")
    return sum(found) / len(found)


def size_multiple(value: str) -> str:
    return value[:-1] + "×"


def results_strip() -> list[tuple[str, str, str, str]]:
    """(label, style, finding, detail), with every number read from results/tables. Style: ref = model result."""
    e2 = read_csv("E2_tipping_point.csv")
    crossings = read_csv("E2_crossings.csv")
    e3 = read_csv("E3_policy_grid.csv")
    e4 = read_csv("E4_contagion.csv")
    e5 = read_csv("E5_sensitivity.csv")

    def peak(scenario: str, impact: str, size: str = "1") -> float:
        return float(pick(e2, scenario=scenario, impact=impact, rails="calibrated", size=size)["peak_Y_bp_med"])

    def sold(scenario: str) -> float:
        return float(pick(e2, scenario=scenario, impact="sqrt", rails="calibrated", size="1")["bills_sold_med"])

    def cross(scenario: str, mark: str) -> str:
        return size_multiple(pick(crossings, scenario=scenario, impact="sqrt", rails="calibrated")[f"size_{mark}bp"])

    solvency = "loss10_5x_fast"
    liquidity = "scare_1x_calibrated"
    grid = [r for r in e3 if r["config"] == solvency]
    par = pick(e3, config=solvency, cash_buffer="par")
    nav = pick(e3, config=solvency, cash_buffer="nav")
    depeg_par, depeg_nav = 1 - float(par["min_price_med"]), 1 - float(nav["min_price_med"])
    rho = pick(e5, config=solvency, metric="peak_Y_bp_med", parameter="MMF reinvestment rho")
    b_solvency = pick(e4, scenario_A="loss10", beta="0.3")
    liquidity_grid = [r for r in e3 if r["config"] == liquidity]
    no_fee, top_fee = grid_mean(grid, "peak_Y_bp_med", fee="0"), grid_mean(grid, "peak_Y_bp_med", fee="0.02")

    return [
        (
            "Spillover",
            "ref",
            f"A run at today’s size moves three-month bill yields by {peak('scare', 'sqrt'):.0f}–{peak('loss10', 'sqrt'):.0f} bp",
            f"liquidity run and 10% loss on the largest issuer, square-root impact; bills sold outright: "
            f"${sold('scare'):.0f} bn and ${sold('loss10'):.0f} bn",
        ),
        (
            "Channel",
            "ref",
            "The externality is demand withdrawn at auction, not a fire sale",
            "redemptions are throttled by processing capacity and funded by maturing bills",
        ),
        (
            "Systemic size",
            "ref",
            f"25 bp is crossed at {cross('loss10', '25')}–{cross('scare', '25')} today’s size, "
            f"50 bp at {cross('loss10', '50')}–{cross('scare', '50')}",
            "square-root impact, calibrated processing rails",
        ),
        (
            "Upper bound",
            "ref",
            f"Linear impact: {peak('scare', 'linear'):.0f} bp in a liquidity run and "
            f"{peak('loss10', 'linear'):.0f} bp in a solvency run at today’s size",
            "every billion withdrawn costs the same; bounds the square-root results from above",
        ),
        (
            "Cash buffer",
            "ref",
            f"A 30% buffer cuts a solvency run’s footprint from {grid_mean(grid, 'peak_Y_bp_med', cash_buffer='0'):.0f} "
            f"to {grid_mean(grid, 'peak_Y_bp_med', cash_buffer='0.3'):.0f} bp",
            f"a 20% buffer takes a liquidity run from {grid_mean(liquidity_grid, 'peak_Y_bp_med', cash_buffer='0'):.0f} "
            f"to {grid_mean(liquidity_grid, 'peak_Y_bp_med', cash_buffer='0.2'):.0f} bp; "
            "redemptions and the price trough do not change",
        ),
        (
            "Redemption basis",
            "ref",
            f"Redeeming at net asset value lifts the trough from {float(par['min_price_med']):.2f} to "
            f"{float(nav['min_price_med']):.2f}, a depeg smaller by "
            f"{1 - depeg_nav / depeg_par:.0%}",
            f"it does not stop the run: {float(nav['R_end_med']):.1%} redeemed against {float(par['R_end_med']):.1%}; "
            f"a 2% fee moves the footprint only from {no_fee:.0f} to {top_fee:.0f} bp",
        ),
        (
            "Key unknown",
            "ref",
            f"Reinvestment through money market funds moves the footprint between {float(rho['high']):.0f} and "
            f"{float(rho['low']):.0f} bp",
            "solvency run at 5× today’s size, share of redeemed cash returning to bills from one to zero",
        ),
        (
            "Contagion",
            "ref",
            f"A solvency run spills over to take {float(b_solvency['B_R_end']):.0%} of the second issuer’s supply",
            f"belief weight 0.3; combined bill-market impact stays at {float(b_solvency['combined_persistent_Y']):.0f} bp",
        ),
        (
            "Inputs",
            "null",
            "Calibration inputs and references still to be verified",
            "compiled without access to primary sources; check them before citing the paper",
        ),
    ]


def promote_head_rows(page: str, head_rows: list[int]) -> str:
    """pandoc reads a multi-row header as body rows; move the rows above \\midrule back into <thead>."""
    remaining = iter(head_rows)

    def table(m: re.Match) -> str:
        rows = next(remaining)
        if "<thead>" in m.group(1):
            return m.group(0)
        tail = re.sub(r"^\s*<tbody>", "", m.group(1))
        head = ""
        for _ in range(rows):
            row = re.match(r"\s*<tr\b.*?</tr>", tail, re.DOTALL)
            head, tail = head + row.group(0), tail[row.end():]
        return "<table><thead>" + re.sub(r"<(/?)td\b", r"<\1th", head) + "\n</thead>\n<tbody>" + tail + "</table>"

    page, found = re.subn(r"<table>(.*?)</table>", table, page, flags=re.DOTALL)
    if found != len(head_rows):
        raise ValueError(f"{len(head_rows)} tables in the source, {found} in the page")
    return page


def finish_html(page: str, equations: list[tuple[str, str]], labels: dict[str, str], head_rows: list[int]) -> str:
    """Figures, tables, equation numbers and heading numbers: the things pandoc leaves in print form."""
    # Run-in \\paragraph headings are unnumbered in the PDF.
    page = re.sub(r'(<h4\b[^>]*?)\sdata-number="[^"]*"([^>]*>)<span class="header-section-number">[^<]*</span>\s*',
                  r"\1\2", page)
    # Appendices carry letters, in the headings and in the contents.
    for label, letter in labels.items():
        if label.startswith("app:"):
            page, headings = re.subn(
                rf'(<h1\b[^>]*id="{label}"[^>]*><span class="header-section-number">)[^<]*(</span>)',
                rf"\g<1>{letter}\2", page)
            page, entries = re.subn(
                rf'(<a href="#{label}"[^>]*><span class="toc-section-number">)[^<]*(</span>)',
                rf"\g<1>{letter}\2", page)
            if (headings, entries) != (1, 1):
                raise ValueError(f"appendix {label}: {headings} headings, {entries} contents entries")

    def image(m: re.Match) -> str:
        tag = re.sub(r'\s(?:style|width|height)="[^"]*"', "", m.group(0))
        tag = re.sub(r'src="([^"/]+)"', lambda s: f'src="figures/{s.group(1)}.png"', tag)
        return tag.replace("<img ", '<img loading="lazy" ', 1)

    page = re.sub(r"<img\b[^>]*>", image, page)
    # The caption sits above the table, outside its sideways scroll, so it wraps at the text width.
    page = re.sub(
        r"<table\b[^>]*>\s*<caption>(.*?)</caption>(.*?)</table>",
        r'<div class="tbl"><p class="tcap">\1</p><div class="tscroll"><table>\2</table></div></div>',
        page, flags=re.DOTALL,
    )
    # Column widths are sized for the PDF page; in the browser the tables size to their content and scroll.
    page = re.sub(r"<colgroup>.*?</colgroup>\s*", "", page, flags=re.DOTALL)
    page = promote_head_rows(page, head_rows)

    # MathML does not line-break, so a long inline formula scrolls on its own instead of widening the page. Scrolling
    # moves a formula's baseline, so short ones, which fit on any screen, are left as they are.
    def inline_math(m: re.Match) -> str:
        tex_source = re.search(r'<annotation encoding="application/x-tex">(.*?)</annotation>', m.group(0), re.DOTALL)
        if tex_source and len(html.unescape(tex_source.group(1))) > WIDE_FORMULA:
            return m.group(0).replace("<math ", '<math class="wide" ', 1)
        return m.group(0)

    page = re.sub(r'<math display="inline".*?</math>', inline_math, page, flags=re.DOTALL)

    remaining = iter(equations)

    def equation(m: re.Match) -> str:
        eq_id, number = next(remaining)
        return f'<span class="eq" id="{eq_id}">{m.group(0)}<span class="eqno">({number})</span></span>'

    page, found = re.subn(r'<math\b[^>]*display="block".*?</math>', equation, page, flags=re.DOTALL)
    if found != len(equations):
        raise ValueError(f"{len(equations)} equations in the source, {found} in the page")
    return page


def main() -> None:
    main_tex = (PAPER / "main.tex").read_text(encoding="utf-8")
    macros = "\n".join(re.findall(r"^\\newcommand\{\\(?:bn|bp)\}.*$", main_tex, flags=re.MULTILINE))
    abstract = re.search(r"\\textbf\{Abstract\}\\end\{center\}\s*\\noindent(.*?)\\medskip", main_tex, re.DOTALL).group(1)
    keywords = re.search(r"\\textbf\{Keywords:\}\s*(.*?)\.", main_tex).group(1).split("; ")
    jel = re.search(r"\\textbf\{JEL codes:\}\s*(.*?)\.", main_tex).group(1)
    thanks, _ = braced(main_tex, main_tex.index(r"\thanks{") + len(r"\thanks"))
    title = re.search(r"pdftitle=\{([^}]*)\}", main_tex).group(1)
    author = re.search(r"pdfauthor=\{([^}]*)\}", main_tex).group(1)
    date = re.search(r"\\date\{\\normalsize ([^}]*)\}", main_tex).group(1)
    body = main_tex[main_tex.index(r"\input{part1}") : main_tex.index(r"\end{document}")]

    tex, equations, labels = number_document(clean_for_pandoc(expand_inputs(body)))

    meta = {
        "title": title,
        "subtitle": SUBTITLE,
        "author": [author],
        "date": date,
        "keywords": keywords,
        "jel": jel,
        "pagetitle": "When Stablecoins Run",
        "description": "Working paper: an agent-based stress test of stablecoin runs and their fire-sale spillovers "
                       "to the US Treasury-bill market.",
        "link-citations": True,
    }
    with tempfile.TemporaryDirectory() as tmp:
        meta_file = Path(tmp) / "meta.json"
        meta_file.write_text(json.dumps(meta), encoding="utf-8")
        page = pandoc(
            macros + "\n" + tex,
            "--standalone", "--template=reader.html", "--number-sections", "--toc", "--toc-depth=1",
            f"--metadata-file={meta_file}", "--lua-filter=reader.lua", "--citeproc", "--bibliography=refs.bib",
        )
    if "REFERENCES-GO-HERE" in page:
        raise RuntimeError("the reference list was not placed")
    head_rows = [head.count("\\\\") for head in re.findall(r"\\toprule(.*?)\\midrule", tex, re.DOTALL)]
    page = finish_html(page, equations, labels, head_rows)

    items = "\n".join(
        f'<li class="r r-{style}"><span class="r-id">{html.escape(label)}</span>'
        f'<span class="r-text">{html.escape(finding)}<small>{html.escape(detail)}</small></span></li>'
        for label, style, finding, detail in results_strip()
    )
    actions = (
        '<li><a href="paper.pdf">Download PDF</a></li>'
        f'<li><a href="{REPO_URL}">Code and replication</a></li>'
        f'<li><a href="{DATA_URL}">Data (Hugging Face)</a></li>'
        f'<li><a href="https://doi.org/{DOI}">Zenodo archive</a></li>'
    )
    bib = (
        "@unpublished{chongmankhong2026stablerun,\n"
        "  author = {Chongmankhong, Thanatchon},\n"
        f"  title  = {{{title}. {SUBTITLE}}},\n"
        "  note   = {Working paper and code repository},\n"
        "  year   = {2026},\n"
        f"  doi    = {{{DOI}}},\n"
        f"  url    = {{{PAPER_URL}}}\n"
        "}"
    )
    colophon = pandoc(thanks) + (
        "<p>Rendered from <code>paper/main.tex</code> by <code>scripts/build_web_paper.py</code>. The headline numbers "
        "above are read from <code>results/tables/</code>. The PDF is authoritative.</p>"
    )
    for marker, value in (
        ("<!--ABSTRACT-->", pandoc(macros + "\n" + abstract)),
        ("<!--ACTIONS-->", actions),
        ("<!--RESULTS-NOTE-->", "Headline numbers, read from the result files. Amber: model results; grey: pending."),
        ("<!--RESULTS-->", items),
        ("<!--CITE-->", f"<h2>How to cite</h2><pre><code>{html.escape(bib)}</code></pre>"),
        ("<!--COLOPHON-->", colophon),
    ):
        if marker not in page:
            raise RuntimeError(f"reader.html lacks {marker}")
        page = page.replace(marker, value)

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "index.html").write_text(page, encoding="utf-8")
    shutil.copyfile(ROOT / "paper.pdf", OUT / "paper.pdf")
    (OUT / "figures").mkdir(exist_ok=True)
    for name in sorted(set(re.findall(r'src="figures/([\w.-]+)"', page))):
        shutil.copyfile(ROOT / "results" / "figures" / name, OUT / "figures" / name)
    print(f"web reader -> {OUT / 'index.html'}")


if __name__ == "__main__":
    main()
