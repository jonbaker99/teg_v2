#!/usr/bin/env python3
"""Stamp out the 9 styling variants of the Results and Player pages.

Takes the two rendered source pages (saved from the live webapp, kept in
_build/), strips the browser-injected style blob, re-points the stylesheet
links at the design_round2 css/ copies, wires in the per-theme structural
sheet + per-styling tokens + the shared retheme runtime, and writes
results.html / player.html into every styling folder.

Run from design_round2/_build:  python3 build.py
"""

import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent  # design_round2/

SOURCES = {
    "results.html": HERE / "src-results.html",
    "player.html": HERE / "src-player.html",
}

STYLINGS = [
    ("theme-a-plain", "ledger", "light"),
    ("theme-a-plain", "gridline", "light"),
    ("theme-a-plain", "manila", "light"),
    ("theme-b-editorial", "broadsheet", "light"),
    ("theme-b-editorial", "order-of-merit", "light"),
    ("theme-b-editorial", "pressbox", "light"),
    ("theme-c-striking", "scoreboard", "light"),
    ("theme-c-striking", "almanac", "light"),
    ("theme-c-striking", "floodlight", "dark"),  # dark-first styling
]


def strip_chart_innards(s: str) -> str:
    """Empty every <div class="...chart-container..."> by walking nested divs."""
    out = []
    pos = 0
    open_re = re.compile(r'<div[^>]*class="[^"]*chart-container[^"]*"[^>]*>')
    tag_re = re.compile(r"<div\b|</div>")
    while True:
        m = open_re.search(s, pos)
        if not m:
            out.append(s[pos:])
            break
        out.append(s[pos:m.end()])
        depth = 1
        scan = m.end()
        while depth:
            t = tag_re.search(s, scan)
            if not t:  # malformed; bail out unchanged
                return s
            depth += 1 if t.group(0) == "<div" else -1
            scan = t.end()
        out.append("</div>")
        pos = scan
    return "".join(out)


def clean(src_html: str) -> str:
    s = src_html

    # Drop browser-injected <style> blobs (plotly/maplibre global CSS —
    # re-injected at runtime by plotly.js itself).
    def drop_big_styles(m):
        return "" if len(m.group(1)) > 20000 or 'id="plotly.js-style-global"' in m.group(0) else m.group(0)

    s = re.sub(r"<style[^>]*>(.*?)</style>", drop_big_styles, s, flags=re.S)

    # Empty each .chart-container: the saved plot SVG has no Plotly JS state,
    # so purge() ignores it and fresh renders stack on top of it. The
    # data-figure attribute on the div is all the runtime needs.
    s = strip_chart_innards(s)

    # Swap CDN scripts for vendored copies (the pages then work offline):
    # Plotly from the plotly-5.24.1 wheel (plotly.js 2.35.2, same as the CDN
    # pin); Tailwind pre-compiled to static utilities by tailwindcss v3 CLI;
    # HTMX dropped entirely — a static prototype never issues HTMX requests.
    s = s.replace('<script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>',
                  '<script src="../../vendor/plotly.min.js"></script>')
    s = s.replace('<script src="https://cdn.tailwindcss.com"></script>',
                  '<link rel="stylesheet" href="../../vendor/tailwind.css">')
    s = re.sub(r'\s*<script src="https://unpkg\.com/htmx[^"]*"></script>', "", s)
    # flag-icons (jsdelivr) isn't used on these two pages
    s = re.sub(r'\s*<link rel="stylesheet" href="https://cdn\.jsdelivr\.net[^"]*">', "", s)

    # Remove theme/dark/debug stylesheets — replaced per styling.
    s = re.sub(r'\s*<link rel="stylesheet" href="\.\./css/(clean-page|dark|debug-structure)\.css">', "", s)

    # Re-point the structural sheets kept from the app.
    s = s.replace('href="../css/base-vars.css"', 'href="../../css/base-vars.css"')
    s = s.replace('href="../css/teg_reports.css"', 'href="../../css/teg_reports.css"')
    s = s.replace('href="../css/mobile.css"', 'href="../../css/mobile.css"')

    # Mode toggle: cookie+reload doesn't work statically; retheme.js takes over.
    s = re.sub(r'onclick="var m=document\.documentElement[^"]*location\.reload\(\)"',
               'onclick="tegToggleMode()"', s)
    return s


def build_page(cleaned: str, mode: str) -> str:
    s = re.sub(r'(<html[^>]*data-mode=")light(")', r"\g<1>" + mode + r"\g<2>", cleaned)
    inject = (
        '    <link rel="stylesheet" href="../theme.css">\n'
        '    <link rel="stylesheet" href="tokens.css">\n'
        '    <script defer src="../../shared/retheme.js"></script>\n'
        "</head>"
    )
    return s.replace("</head>", inject)


THEMES = {
    "theme-a-plain": ("Theme A — Plain", ["ledger", "gridline", "manila"], "ledger"),
    "theme-b-editorial": ("Theme B — Editorial", ["broadsheet", "order-of-merit", "pressbox"], "broadsheet"),
    "theme-c-striking": ("Theme C — Striking", ["scoreboard", "almanac", "floodlight"], "scoreboard"),
}


def build_component_sheets() -> None:
    tpl = (HERE / "components-template.html").read_text()
    for dirname, (title, stylings, default) in THEMES.items():
        btns = "\n    ".join(
            f'<button type="button" data-styling="{s}" onclick="dr2SetStyling(\'{s}\', this)"'
            ' style="background:none;border:none;color:inherit;cursor:pointer;font:inherit;'
            + ("font-weight:700;text-decoration:underline;" if s == default else "")
            + f'">{s}</button>'
            for s in stylings
        )
        out_html = (
            tpl.replace("{{THEME_TITLE}}", title)
            .replace("{{DEFAULT_STYLING}}", default)
            .replace("{{STYLING_BUTTONS}}", btns)
        )
        out = ROOT / dirname / "components.html"
        out.write_text(out_html)
        print(f"wrote {out.relative_to(ROOT)}")


def main() -> None:
    for out_name, src_path in SOURCES.items():
        cleaned = clean(src_path.read_text())
        for theme, styling, mode in STYLINGS:
            out = ROOT / theme / styling / out_name
            out.write_text(build_page(cleaned, mode))
            print(f"wrote {out.relative_to(ROOT)} ({len(cleaned)//1024} KB, default {mode})")
    build_component_sheets()


if __name__ == "__main__":
    main()
