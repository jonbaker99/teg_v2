#!/usr/bin/env python3
"""Full-page screenshots of the design_round2 variants.

Serves design_round2/ over localhost (so relative CSS resolves and
localStorage works), loads each page in the pre-installed Chromium via
the outbound proxy (CDN assets: tailwind, plotly, fonts), and captures
light + dark for each requested page.

Usage: python3 shoot.py [--only styling1,styling2] [--pages results,player,components]
"""

import argparse
import http.server
import os
import socketserver
import threading
from pathlib import Path

from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SHOTS = ROOT / "screenshots"

STYLINGS = [
    ("theme-a-plain", "ledger"),
    ("theme-a-plain", "gridline"),
    ("theme-a-plain", "manila"),
    ("theme-b-editorial", "broadsheet"),
    ("theme-b-editorial", "order-of-merit"),
    ("theme-b-editorial", "pressbox"),
    ("theme-c-striking", "scoreboard"),
    ("theme-c-striking", "almanac"),
    ("theme-c-striking", "floodlight"),
]

PORT = 8731


def serve():
    os.chdir(ROOT)
    handler = http.server.SimpleHTTPRequestHandler
    socketserver.ThreadingTCPServer.allow_reuse_address = True
    httpd = socketserver.ThreadingTCPServer(("127.0.0.1", PORT), handler)
    httpd.daemon_threads = True
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="")
    ap.add_argument("--pages", default="results,player")
    ap.add_argument("--modes", default="light,dark")
    ap.add_argument("--width", type=int, default=1280)
    args = ap.parse_args()

    only = {s for s in args.only.split(",") if s}
    pages = [p for p in args.pages.split(",") if p]
    modes = [m for m in args.modes.split(",") if m]

    SHOTS.mkdir(exist_ok=True)
    serve()

    proxy = os.environ.get("HTTPS_PROXY")
    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            executable_path="/opt/pw-browsers/chromium",
            proxy={"server": proxy, "bypass": "127.0.0.1,localhost"} if proxy else None,
            args=["--ignore-certificate-errors"],
        )
        ctx = browser.new_context(viewport={"width": args.width, "height": 1000})
        page = ctx.new_page()
        if "components" in pages:
            pages = [p for p in pages if p != "components"]
            for theme, styling in STYLINGS:
                if only and styling not in only:
                    continue
                url = f"http://127.0.0.1:{PORT}/{theme}/components.html"
                try:
                    page.goto(url, wait_until="networkidle", timeout=45000)
                except Exception:
                    pass
                try:
                    page.wait_for_function("document.fonts.status === 'loaded'", timeout=15000)
                except Exception:
                    pass
                page.evaluate(
                    "s => { const b=document.querySelector(`[data-styling='${s}']`);"
                    " if (window.dr2SetStyling) dr2SetStyling(s, b); }",
                    styling,
                )
                # tokens.css @imports Google Fonts, which blocks the whole
                # sheet — wait until the swapped tokens are actually computed.
                try:
                    page.wait_for_function(
                        "getComputedStyle(document.documentElement)"
                        ".getPropertyValue('--chart-1').trim().length > 0",
                        timeout=20000,
                    )
                    page.wait_for_function("document.fonts.status === 'loaded'", timeout=15000)
                except Exception:
                    pass
                page.wait_for_timeout(1800)
                out = SHOTS / f"{styling}--components.png"
                page.screenshot(path=str(out), full_page=True)
                print("shot", out.name)

        for theme, styling in STYLINGS:
            if only and styling not in only:
                continue
            for pg in pages:
                url = f"http://127.0.0.1:{PORT}/{theme}/{styling}/{pg}.html"
                for mode in modes:
                    try:
                        page.goto(url, wait_until="networkidle", timeout=45000)
                    except Exception:
                        pass  # networkidle can time out on long-polling; capture anyway
                    try:
                        page.wait_for_function("document.fonts.status === 'loaded'", timeout=15000)
                    except Exception:
                        pass
                    # Set the opposite mode, then let the page's own toggle flip
                    # to the target — that path also re-renders the charts.
                    page.evaluate(
                        "m => { const h = document.documentElement;"
                        " h.setAttribute('data-mode', m === 'dark' ? 'light' : 'dark');"
                        " if (window.tegToggleMode) window.tegToggleMode();"
                        " else h.setAttribute('data-mode', m); }",
                        mode,
                    )
                    page.wait_for_timeout(1400)
                    out = SHOTS / f"{styling}--{pg}--{mode}.png"
                    page.screenshot(path=str(out), full_page=True)
                    print("shot", out.name)
        browser.close()


if __name__ == "__main__":
    main()
