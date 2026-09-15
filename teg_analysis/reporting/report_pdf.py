"""Pre-render each TEG newspaper report (`newspaper_edition`) to a single-page,
A4-width PDF.

WHY A SEPARATE PIPELINE STEP, NOT "screenshot the preview page": the webapp
preview page is meant to be looked at on screen, and a PDF made by literally
capturing it would either be the wrong width (native desktop layout is ~312mm
wide) or paginate awkwardly (a naive `page.pdf()` at A4 size breaks the paper
across as many pages as it takes). What this module does instead is compose
the SAME desktop HTML/CSS the preview page uses, but tell Chromium to lay it
out at its native desktop viewport width and then print that single page at
A4 width by scaling the whole render down — so the PDF is a faithful, single-
page A4 print of the desktop edition, not a browser screenshot glued into a
page.

THE TWO WIDTHS, AND WHY THEY MUST STAY DIFFERENT (verified against
`newspaper_preview.css`, which gates its desktop layout behind
`min-width:701px` media queries — evaluated against the Chromium *viewport*,
never against the PDF page size Playwright is asked to emit):

  LAYOUT_WIDTH = 1180   CSS px. The page viewport. This is what makes the
                        desktop (as opposed to mobile) layout apply at all.
  PAPER_WIDTH  = 794    CSS px = 210mm = A4 width. The PDF page Playwright
                        emits. `page.pdf(scale=...)` shrinks the 1180px
                        render down to fit this page — it does not change
                        the viewport, so the media queries stay satisfied.
  SCALE = PAPER_WIDTH / LAYOUT_WIDTH  (~0.6728)

Render a viewport 794px wide directly and the desktop rail collapses to the
mobile layout; the fix is not "make the paper wider", it is "keep the
viewport at 1180 and print smaller".

ORDER OF OPERATIONS (each step depends on the one before it — verified by a
throwaway spike before this module existed; do not reorder):

    1. page.set_content(html, wait_until="networkidle")
    2. page.wait_for_function("document.fonts.ready.then(() => true)")
    3. page.emulate_media(media="screen")
    4. measure .np-paper's height
    5. page.pdf(...)

`emulate_media("screen")` (step 3) has to run AFTER `set_content` (Chromium
defaults new pages to no forced media type, but `page.pdf()` forces `print`
unless told otherwise) and BEFORE the measurement in step 4: measure first
and Chromium switches to `print` media between the measurement and the PDF
call, so the height used to size the PDF page no longer matches what actually
gets printed, producing an unwanted second, near-empty page. Step 4 measures
`.np-paper`'s `getBoundingClientRect().height`, not `scrollHeight` —
`scrollHeight` rounds down and undercounts border/shadow-adjacent layout in a
way that clips the last few pixels of content.

Playwright itself (`sync_playwright`) is imported lazily, inside the
functions that need it — never at module import time. `teg_analysis/` must
import cleanly with no UI package (and, by the same test guard, no browser
automation package) installed; see the "No frontend imports" invariant in
CLAUDE.md. `paper_html` below is the exception: it is pure string assembly,
needs no browser, and is unit-testable on its own.
"""

from __future__ import annotations

import base64
import functools
import hashlib
import json
import math
import pathlib
import re
import time
from typing import Any, Callable, Iterable

#: CSS px the desktop layout is composed at. Must match the viewport a
#: browser opens the report at for `newspaper_preview.css`'s desktop media
#: queries (`min-width:701px`) to apply. See module docstring.
LAYOUT_WIDTH = 1180

#: CSS px = 210mm, A4 width. The PDF page Playwright is asked to emit.
PAPER_WIDTH = 794

#: How far the 1180px render is shrunk to print at `PAPER_WIDTH`. Passed to
#: `page.pdf(scale=...)`; the viewport itself stays at `LAYOUT_WIDTH`.
SCALE = PAPER_WIDTH / LAYOUT_WIDTH

#: Where rendered PDFs live by default. `scripts/build_report_pdfs.py`'s
#: `--out` default and the manifest's home.
PDF_DIR = "data/commentary/pdfs"

#: Same four font families (Fraunces / Source Serif 4 / IBM Plex Mono /
#: Libre Franklin) the live preview page loads via
#: `webapp/templates/teg_reports.html`'s `fonts.googleapis.com` `<link>`.
#: THAT link is right for a browser tab — it has a live network. Chromium in
#: the PDF-build container does not: all external requests it makes fail
#: (the container's `HTTPS_PROXY` is honoured by `curl`, never by Chromium),
#: so linking the same URL here used to make the render silently fall back
#: to system serif/sans/mono and still exit 0. Fixed by self-hosting: the
#: woff2 files this exact CSS spec resolves to are downloaded once into
#: `webapp/static/fonts/` (see that folder's `faces.json`) and
#: `embedded_font_css()` below inlines them as `data:` URIs, so the build
#: needs no network at all and can't silently degrade.
_REQUIRED_FONT_FAMILIES = ("Fraunces", "Source Serif 4", "IBM Plex Mono", "Libre Franklin")

#: (family, style) pairs that must each have their OWN loaded face — not just
#: the family name. `newspaper_preview.css`'s `.sf-contrast` standfirst rules
#: set `font-style:italic` on Libre Franklin text; if `faces.json` only had
#: the upright face bundled, `document.fonts` would still report the family
#: "loaded" (from the upright face) while Chromium silently synthesises a
#: fake oblique for the italic request — exactly the failure mode this guard
#: exists to catch. Checked in addition to, not instead of,
#: `_REQUIRED_FONT_FAMILIES`.
_REQUIRED_FONT_STYLES = (("Libre Franklin", "italic"),)

#: Where the self-hosted woff2 files (and their `faces.json` metadata) live.
#: A filesystem path, not a Python import — reading static font bytes from
#: here does not violate "no frontend imports in `teg_analysis/`", which is
#: about not importing `webapp`'s Python code.
_FONTS_DIR = pathlib.Path(__file__).resolve().parent.parent.parent / "webapp" / "static" / "fonts"


def _load_font_faces(fonts_dir: pathlib.Path) -> list[dict[str, Any]]:
    """Parsed `faces.json` from `fonts_dir` — one dict per `@font-face` to
    emit, each naming the woff2 file (relative to `fonts_dir`) that holds it.
    """
    faces_path = fonts_dir / "faces.json"
    return json.loads(faces_path.read_text())


@functools.lru_cache(maxsize=4)
def _embedded_font_css_cached(fonts_dir_str: str) -> str:
    fonts_dir = pathlib.Path(fonts_dir_str)
    faces = _load_font_faces(fonts_dir)
    families = {face["font_family"] for face in faces}
    missing = [fam for fam in _REQUIRED_FONT_FAMILIES if fam not in families]
    if missing:
        raise RuntimeError(
            f"report_pdf: {fonts_dir}/faces.json is missing font(s) {missing} — "
            "expected Fraunces, Source Serif 4, IBM Plex Mono and Libre Franklin."
        )

    rules = []
    for face in faces:
        woff2_path = fonts_dir / face["file"]
        data = base64.b64encode(woff2_path.read_bytes()).decode("ascii")
        descriptors = [
            f"font-family: '{face['font_family']}'",
            f"font-style: {face['font_style']}",
            f"font-weight: {face['font_weight']}",
        ]
        if face.get("font_stretch"):
            descriptors.append(f"font-stretch: {face['font_stretch']}")
        if face.get("font_optical_sizing"):
            descriptors.append(f"font-optical-sizing: {face['font_optical_sizing']}")
        descriptors.append("font-display: swap")
        descriptors.append(f"src: url(data:font/woff2;base64,{data}) format('woff2')")
        if face.get("unicode_range"):
            descriptors.append(f"unicode-range: {face['unicode_range']}")
        rules.append("@font-face{" + ";".join(descriptors) + ";}")
    return "".join(rules)


def embedded_font_css(fonts_dir: pathlib.Path | str = _FONTS_DIR) -> str:
    """`@font-face` CSS for Fraunces / Source Serif 4 / IBM Plex Mono /
    Libre Franklin, each `src` a `data:font/woff2;base64,...` URI — no
    network fetch, ever.

    Built from `fonts_dir`'s `faces.json` (family, style, weight — including
    variable-font weight ranges like `"400 900"` — stretch, optical-sizing
    and unicode-range, one entry per downloaded woff2). Memoized per
    `fonts_dir` so rendering ~84 reports in one `render_pdfs` call reads and
    base64-encodes the ~18 files once, not once per report.
    """
    return _embedded_font_css_cached(str(fonts_dir))

#: PDF-only overrides layered on top of the site's own CSS: kill the preview
#: page's outer padding, the paper's card shadow/border and its max-width, so
#: the paper IS the printed page, edge to edge, rather than a card floating
#: on a background the PDF has no use for.
_PDF_OVERRIDES = f"""
html, body {{ margin:0; padding:0; background:#F6F3EA; }}
.np-desktop {{ padding:0 !important; }}
.np-paper {{
  width:{LAYOUT_WIDTH}px !important; max-width:none !important;
  margin:0 !important; box-shadow:none !important; border:none !important;
}}
"""


def paper_html(body_html: str, css: str, font_css: str | None = None) -> str:
    """Assemble the standalone document Chromium renders and prints.

    No browser; the only I/O is `font_css`'s default (reading and
    base64-encoding the self-hosted woff2 files, memoized — see
    `embedded_font_css`). `body_html` is
    `newspaper_edition.render_desktop_html(edition, rail="s2")`'s output;
    `css` is the caller-supplied stylesheet text (`report_pdf` takes no
    dependency on where that comes from — see "No frontend imports" above;
    `scripts/build_report_pdfs.py` is the one that knows it lives at
    `webapp/static/newspaper_preview.css`). `font_css` defaults to
    `embedded_font_css()` (Fraunces / Source Serif 4 / IBM Plex Mono /
    Libre Franklin, inlined as `data:` URIs — no `fonts.googleapis.com`
    fetch, which Chromium in this container cannot reach); pass it
    explicitly only to override for a test.
    """
    if font_css is None:
        font_css = embedded_font_css()
    return (
        "<!doctype html><html><head><meta charset=\"utf-8\">"
        f"<style>{font_css}</style>"
        f"<style>{css}</style><style>{_PDF_OVERRIDES}</style>"
        "</head><body>"
        '<div class="np-page pal-a sf-contrast"><div class="np-desktop">'
        f'<main class="np-paper rail-s2">{body_html}</main>'
        "</div></div></body></html>"
    )


def pdf_filename(teg: int, round_num: int | None) -> str:
    """`"teg_18.pdf"` (tournament) or `"teg_18_round_3.pdf"` (round)."""
    if round_num is None:
        return f"teg_{teg}.pdf"
    return f"teg_{teg}_round_{round_num}.pdf"


def content_sha(body_html: str, css: str) -> str:
    """Deterministic fingerprint of what a PDF was built from.

    sha256 of the rendered desktop body HTML concatenated with the CSS text
    — the two inputs that, together, determine everything Chromium prints
    (fonts and the fixed PDF overrides never change). Lets
    `scripts/build_report_pdfs.py --check` detect "the report, or the
    stylesheet, changed since this PDF was built" without re-rendering:
    recompute this and compare against the manifest.
    """
    return hashlib.sha256((body_html + css).encode("utf-8")).hexdigest()


def _find_bundled_chromium() -> str | None:
    """First `chrome` binary under a versioned `/opt/pw-browsers/chromium-*`
    install, or `None`. Discovered by glob rather than hardcoding the version
    number in it (`chromium-1194` today), so a Playwright browser upgrade on
    this container doesn't silently break the fallback path."""
    matches = sorted(pathlib.Path("/opt/pw-browsers").glob("chromium-*/chrome-linux/chrome"))
    return str(matches[0]) if matches else None


def _launch_chromium(playwright_instance: Any):
    """Playwright's own bundled Chromium first; if launching that raises,
    fall back to an explicit `executable_path` found by `_find_bundled_chromium`.
    Both paths pass `--no-sandbox` (required in this container)."""
    try:
        return playwright_instance.chromium.launch(args=["--no-sandbox"])
    except Exception:  # noqa: BLE001 - bundled browser missing/unlaunchable; try the fallback
        executable_path = _find_bundled_chromium()
        if executable_path is None:
            raise
        return playwright_instance.chromium.launch(executable_path=executable_path, args=["--no-sandbox"])


def _assert_required_fonts_loaded(page: Any, teg: int, round_num: int | None) -> None:
    """Guard against the exact failure this module used to have silently:
    the fonts requested by `paper_html` not actually loading in Chromium,
    and the render falling back to a system serif/sans/mono font while still
    reporting success. Call AFTER `document.fonts.ready` resolves and BEFORE
    `page.pdf()` — never let a fallback-font PDF get written to disk.

    Checks family names (`_REQUIRED_FONT_FAMILIES`) AND specific
    (family, style) pairs (`_REQUIRED_FONT_STYLES`). The family check alone
    is not enough for italic: if only an upright face for a family is
    bundled, `document.fonts` still reports that family as "loaded" (from
    the upright face), while Chromium silently synthesises a fake oblique
    for any `font-style:italic` text — no failure, no missing family, just a
    slanted-upright fake in place of the real italic. Distinguishing that
    requires inspecting each loaded `FontFace`'s own `style`, not just
    collecting family names.
    """
    loaded_faces = page.evaluate(
        "() => [...document.fonts].filter(f => f.status === 'loaded')"
        ".map(f => ({family: f.family.replace(/^[\"']|[\"']$/g, ''), style: f.style}))"
    )
    loaded_families = {face["family"] for face in loaded_faces}
    missing = [fam for fam in _REQUIRED_FONT_FAMILIES if fam not in loaded_families]

    missing_styles = [
        f"{fam} ({style})"
        for fam, style in _REQUIRED_FONT_STYLES
        if not any(
            face["family"] == fam and style in face["style"]
            for face in loaded_faces
        )
    ]

    if missing or missing_styles:
        target = pdf_filename(teg, round_num)
        problems = missing + missing_styles
        raise RuntimeError(
            f"report_pdf: required font(s) failed to load for {target}: {problems}. "
            f"document.fonts reported loaded faces: {sorted((f['family'], f['style']) for f in loaded_faces)}. "
            "Refusing to render a fallback-font PDF (a missing italic face is silently "
            "synthesised by Chromium as a fake oblique, not reported as an error) — check "
            "webapp/static/fonts/ (faces.json + woff2 files) and embedded_font_css()."
        )


#: Fixed stand-in for Chromium's `/CreationDate` and `/ModDate` — same
#: length (23 bytes: `D:` + 14 digits + `+00'00'`) as every value Chromium
#: has been observed to emit, so swapping it in never changes the file size.
_FIXED_PDF_DATE = b"D:20260101000000+00'00'"


def _normalize_pdf_determinism(pdf_bytes: bytes) -> bytes:
    """Replace Chromium's per-render `/CreationDate`, `/ModDate` and `/ID`
    with fixed, content-derived values so re-rendering an UNCHANGED report
    produces byte-identical PDF output.

    WHY THIS EXISTS: Chromium stamps a fresh wall-clock timestamp (and,
    depending on version, a random `/ID`) into every PDF it produces, even
    when nothing about the page content changed. Left alone, that turns
    every `--all` rebuild into an ~84-file, ~24MB diff, which drowns real
    content changes in noise and makes `git blame`/review useless for this
    directory.

    CRITICAL CONSTRAINT — every replacement below is byte-length-preserving,
    NEVER length-changing. A PDF's cross-reference table (`xref`) records
    absolute byte OFFSETS into the file for every indirect object; shrinking
    or growing anything before an object shifts every offset after it and
    corrupts the file (Chromium's `page.pdf()` output here isn't rewritten
    through a PDF library that would recompute the xref table for us — see
    the module docstring's explanation for why not). So each substitution
    below only ever swaps bytes for other bytes of the exact same count:
    `/CreationDate`/`/ModDate` values are always the same 23-byte
    `D:YYYYMMDDHHMMSS+00'00'` shape (verified against this pipeline's own
    output), and any `/ID` hex strings are replaced by a same-length slice
    of a sha256 digest of the (already date-normalized) bytes — deterministic
    because it depends only on content, not wall-clock time. Any match whose
    captured value isn't the expected length is left untouched rather than
    forced to fit, since a wrong-length swap is exactly the corruption this
    function must never cause.
    """
    def _replace_date(match: re.Match) -> bytes:
        prefix, value, suffix = match.group(1), match.group(2), match.group(3)
        if len(value) != len(_FIXED_PDF_DATE):
            return match.group(0)
        return prefix + _FIXED_PDF_DATE + suffix

    result = re.sub(rb"(/CreationDate\s*\()([^)]*)(\))", _replace_date, pdf_bytes)
    result = re.sub(rb"(/ModDate\s*\()([^)]*)(\))", _replace_date, result)

    # /ID [<hex...> <hex...>] — not observed in this pipeline's current
    # Chromium output, but handled defensively in case a future Chromium
    # version adds one. The replacement hex is derived from a hash of the
    # (date-normalized) content, so it stays fixed across identical renders
    # while varying with the actual content, same spirit as `content_sha`.
    digest_hex = hashlib.sha256(result).hexdigest()

    def _replace_id(match: re.Match) -> bytes:
        prefix, hex1, mid, hex2, suffix = match.groups()

        def _fixed_hex(length: int) -> bytes:
            repeated = (digest_hex * (length // len(digest_hex) + 1))[:length]
            return repeated.encode("ascii")

        return prefix + _fixed_hex(len(hex1)) + mid + _fixed_hex(len(hex2)) + suffix

    result = re.sub(
        rb"(/ID\s*\[\s*<)([0-9A-Fa-f]*)(>\s*<)([0-9A-Fa-f]*)(>\s*\])",
        _replace_id, result,
    )
    return result


def _render_target(page: Any, teg: int, round_num: int | None, css: str, out_dir: pathlib.Path
                   ) -> dict[str, Any]:
    from teg_analysis.reporting.newspaper_edition import build_edition, render_desktop_html

    edition = build_edition(teg, round_num=round_num)
    body = render_desktop_html(edition, rail="s2")
    html_doc = paper_html(body, css)

    # Order matters — see module docstring.
    page.set_content(html_doc, wait_until="networkidle")
    page.wait_for_function("document.fonts.ready.then(() => true)")
    _assert_required_fonts_loaded(page, teg, round_num)
    page.emulate_media(media="screen")
    height = page.evaluate("document.querySelector('.np-paper').getBoundingClientRect().height")
    paper_height = math.ceil(height * SCALE) + 2
    pdf_bytes = page.pdf(
        width=f"{PAPER_WIDTH}px", height=f"{paper_height}px", scale=SCALE,
        margin={"top": "0", "bottom": "0", "left": "0", "right": "0"},
        print_background=True, page_ranges="1",
    )
    pdf_bytes = _normalize_pdf_determinism(pdf_bytes)

    filename = pdf_filename(teg, round_num)
    (out_dir / filename).write_bytes(pdf_bytes)
    return {
        "teg": teg, "round": round_num, "filename": filename,
        "bytes": len(pdf_bytes), "content_height": height,
        "sha": content_sha(body, css),
    }


def render_pdfs(
    targets: Iterable[tuple[int, int | None]], css: str, out_dir: str,
    progress: Callable[[dict[str, Any]], None] | None = None,
) -> list[dict[str, Any]]:
    """Render one PDF per `(teg, round_num)` in `targets` (`round_num=None`
    for the tournament edition) into `out_dir`.

    Opens ONE browser and ONE page and reuses them for every target — for
    ~84 reports, launching a fresh Chromium per report dominates the run
    time; `page.set_content` on a page that already exists does not.

    Each entry in the returned list carries `teg`, `round`, `filename`,
    `bytes`, `content_height`, `sha` and `elapsed_s` on success, or `teg`,
    `round`, `error` and `elapsed_s` on failure — one bad edition (a
    malformed artefact, a parser mismatch) does not lose the PDFs already
    rendered before it, same resilience pattern as
    `storyline_full_report_experiment.py`'s per-TEG loop. `progress`, if
    given, is called once per target with that target's result dict, in
    order, as soon as it is known.
    """
    from playwright.sync_api import sync_playwright

    out_path = pathlib.Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    results: list[dict[str, Any]] = []
    with sync_playwright() as p:
        browser = _launch_chromium(p)
        try:
            page = browser.new_page(viewport={"width": LAYOUT_WIDTH, "height": 1000})
            for teg, round_num in targets:
                started = time.monotonic()
                try:
                    result = _render_target(page, teg, round_num, css, out_path)
                except Exception as e:  # noqa: BLE001 - keep going; report at the end
                    result = {"teg": teg, "round": round_num,
                              "error": f"{type(e).__name__}: {e}"}
                result["elapsed_s"] = time.monotonic() - started
                results.append(result)
                if progress is not None:
                    progress(result)
        finally:
            browser.close()
    return results


def render_pdf(
    teg: int, round_num: int | None = None, *, css: str, out_dir: str = PDF_DIR,
) -> dict[str, Any]:
    """Convenience wrapper around `render_pdfs` for a single report. Still
    launches its own browser for the one target, so prefer `render_pdfs`
    directly when rendering more than one report."""
    return render_pdfs([(teg, round_num)], css, out_dir)[0]
