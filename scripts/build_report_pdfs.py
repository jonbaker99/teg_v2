"""Pre-render TEG newspaper reports to single-page, A4-width PDFs.

Rendering happens in `teg_analysis.reporting.report_pdf` (the library — no
knowledge of the webapp). This script is the CLI wrapper: it knows the one
thing the library deliberately doesn't (`teg_analysis/` takes no frontend
imports) — where the live stylesheet lives (`webapp/static/newspaper_preview.css`)
— reads it, and passes the text in.

Usage, from the repo root:

    # One tournament report.
    python scripts/build_report_pdfs.py --tegs 18 --tournaments-only

    # A TEG's tournament report plus every round report it has.
    python scripts/build_report_pdfs.py --tegs 18

    # A range or a mix, same syntax as backfill.py / storyline_full_report_experiment.py.
    python scripts/build_report_pdfs.py --tegs 2-18
    python scripts/build_report_pdfs.py --tegs 8,9,14

    # Every report that exists.
    python scripts/build_report_pdfs.py --all

    # Only round reports, everywhere.
    python scripts/build_report_pdfs.py --all --rounds-only

    # Is the PDF set stale? Renders nothing; exits 1 if anything needs a rebuild.
    python scripts/build_report_pdfs.py --all --check

    # Debug what Chromium is actually being handed, for one report.
    python scripts/build_report_pdfs.py --tegs 18 --tournaments-only --save-html /tmp/teg18.html

MANIFEST
--------
`<out>/manifest.json` records, per report, the sha256 of (rendered body HTML
+ CSS text) that produced its PDF (`report_pdf.content_sha`). `--check`
recomputes that hash from what's on disk right now — no rendering, no
browser — and compares it against the manifest, so it can say "TEG 18's
report changed since its PDF was last built" without spending a Chromium
launch to find out.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
import time
from datetime import datetime, timezone

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

from teg_analysis.reporting.backfill import parse_teg_spec
from teg_analysis.reporting.newspaper_edition import (
    available_report_tegs, available_rounds, has_edition, render_desktop_html, build_edition,
)
from teg_analysis.reporting.report_pdf import (
    PDF_DIR, content_sha, pdf_filename, paper_html, render_pdfs,
)

CSS_PATH = pathlib.Path(__file__).parent.parent / "webapp/static/newspaper_preview.css"
MANIFEST_NAME = "manifest.json"


def _targets_for_teg(teg: int, *, rounds_only: bool, tournaments_only: bool) -> list[tuple[int, int | None]]:
    """`(teg, round_num)` targets available for one TEG, filtered by scope."""
    targets: list[tuple[int, int | None]] = []
    if not rounds_only and has_edition(teg):
        targets.append((teg, None))
    if not tournaments_only:
        targets.extend((teg, r) for r in available_rounds(teg))
    return targets


def resolve_targets(args) -> list[tuple[int, int | None]]:
    tegs = available_report_tegs() if args.all else parse_teg_spec(args.tegs)
    targets: list[tuple[int, int | None]] = []
    for teg in tegs:
        teg_targets = _targets_for_teg(
            teg, rounds_only=args.rounds_only, tournaments_only=args.tournaments_only)
        if not teg_targets and not args.all:
            print(f"[build_report_pdfs] WARNING: TEG {teg} has no report matching this scope; skipping.")
        targets.extend(teg_targets)
    return targets


def manifest_key(teg: int, round_num: int | None) -> str:
    return pdf_filename(teg, round_num).removesuffix(".pdf")


def load_manifest(out_dir: pathlib.Path) -> dict:
    path = out_dir / MANIFEST_NAME
    if not path.exists():
        return {"entries": {}}
    return json.loads(path.read_text())


def write_manifest(out_dir: pathlib.Path, entries: dict) -> None:
    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "paper_width": 794,
        "layout_width": 1180,
        "entries": entries,
    }
    (out_dir / MANIFEST_NAME).write_text(json.dumps(manifest, indent=2))


def run_check(targets: list[tuple[int, int | None]], css: str, out_dir: pathlib.Path) -> int:
    """Render nothing; compare each target's current content against the
    manifest. Prints what's stale/missing and returns the process exit code
    (0 = up to date, 1 = something needs a rebuild)."""
    manifest = load_manifest(out_dir)
    entries = manifest.get("entries", {})
    stale: list[str] = []
    for teg, round_num in targets:
        key = manifest_key(teg, round_num)
        try:
            edition = build_edition(teg, round_num=round_num)
        except Exception as e:  # noqa: BLE001
            stale.append(f"{key}: cannot build edition ({type(e).__name__}: {e})")
            continue
        body = render_desktop_html(edition, rail="s2")
        expected_sha = content_sha(body, css)
        entry = entries.get(key)
        pdf_path = out_dir / pdf_filename(teg, round_num)
        if entry is None:
            stale.append(f"{key}: missing from manifest (never built)")
        elif not pdf_path.exists():
            stale.append(f"{key}: PDF file missing on disk ({pdf_path})")
        elif entry.get("sha") != expected_sha:
            stale.append(f"{key}: content changed since last build")

    if stale:
        print(f"[build_report_pdfs] {len(stale)} of {len(targets)} stale or missing:")
        for line in stale:
            print(f"  - {line}")
        return 1
    print(f"[build_report_pdfs] up to date: {len(targets)} report(s), manifest matches disk.")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    scope = ap.add_mutually_exclusive_group(required=True)
    scope.add_argument("--tegs",
                       help="Which TEGs: 14, 2-18, 8,9,14, or a mix. Parsed by "
                            "`backfill.parse_teg_spec`, the same syntax backfill.py and "
                            "storyline_full_report_experiment.py take.")
    scope.add_argument("--all", action="store_true",
                       help="Every available edition, tournament and round "
                            "(`newspaper_edition.available_report_tegs()`).")
    ap.add_argument("--rounds-only", action="store_true",
                    help="Render only round reports, skip tournament reports.")
    ap.add_argument("--tournaments-only", action="store_true",
                    help="Render only tournament reports, skip round reports.")
    ap.add_argument("--out", default=PDF_DIR,
                    help=f"Output directory (default: {PDF_DIR}).")
    ap.add_argument("--check", action="store_true",
                    help="Render nothing; compare against the manifest and exit 1 if "
                         "anything is stale or missing.")
    ap.add_argument("--save-html", metavar="PATH", default=None,
                    help="Dump the generated standalone HTML for the first selected "
                         "target to PATH and exit, without opening a browser.")
    args = ap.parse_args(argv)

    if args.rounds_only and args.tournaments_only:
        ap.error("--rounds-only and --tournaments-only are mutually exclusive.")

    css = CSS_PATH.read_text()
    targets = resolve_targets(args)
    if not targets:
        print("[build_report_pdfs] no targets matched this scope.")
        return 1

    out_dir = pathlib.Path(args.out)

    if args.save_html:
        teg, round_num = targets[0]
        edition = build_edition(teg, round_num=round_num)
        body = render_desktop_html(edition, rail="s2")
        html_doc = paper_html(body, css)
        save_path = pathlib.Path(args.save_html)
        save_path.parent.mkdir(parents=True, exist_ok=True)
        save_path.write_text(html_doc)
        print(f"[build_report_pdfs] wrote standalone HTML for {manifest_key(teg, round_num)} "
              f"to {save_path}")
        return 0

    if args.check:
        return run_check(targets, css, out_dir)

    out_dir.mkdir(parents=True, exist_ok=True)
    manifest = load_manifest(out_dir)
    entries = manifest.get("entries", {})

    print(f"[build_report_pdfs] rendering {len(targets)} report(s) to {out_dir}")
    started = time.monotonic()

    def progress(result: dict) -> None:
        key = manifest_key(result["teg"], result["round"])
        if "error" in result:
            print(f"  [{key}] FAILED: {result['error']} ({result['elapsed_s']:.1f}s)")
            return
        print(f"  [{key}] {result['filename']}  {result['bytes'] / 1024:.0f} KB  "
              f"content={result['content_height']:.0f}px  {result['elapsed_s']:.1f}s")

    results = render_pdfs(targets, css, str(out_dir), progress=progress)

    ok = [r for r in results if "error" not in r]
    failed = [r for r in results if "error" in r]
    for r in ok:
        key = manifest_key(r["teg"], r["round"])
        entries[key] = {"sha": r["sha"], "bytes": r["bytes"],
                        "built_at": datetime.now(timezone.utc).isoformat()}
    write_manifest(out_dir, entries)

    elapsed = time.monotonic() - started
    total_bytes = sum(r["bytes"] for r in ok)
    print(f"[build_report_pdfs] {len(ok)} rendered, {len(failed)} failed, "
          f"{total_bytes / 1024:.0f} KB total, {elapsed:.1f}s")
    if failed:
        for r in failed:
            print(f"  {manifest_key(r['teg'], r['round'])}: {r['error']}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
