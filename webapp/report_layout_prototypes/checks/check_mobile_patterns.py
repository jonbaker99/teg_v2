"""Behavioural checks on mobile.html patterns A and B.

Not part of the pytest suite — the prototypes are not app code, and this needs
a browser and a served copy of the folder. Run it by hand after touching
mobile.html:

    python -m http.server 8899 --bind 127.0.0.1 \
        --directory webapp/report_layout_prototypes &
    python webapp/report_layout_prototypes/checks/check_mobile_patterns.py

Checks routing and the browser Back gesture, scroll restore, focus movement,
tab/keyboard control of the card track, touch-target sizes and horizontal
overflow. Run it at 390x844 (a real phone, where the document scrolls) and
again at 1280x900 (the desktop preview frame, where .scroller scrolls) — the
two take different code paths and only the first matters to a reader.
"""
from playwright.sync_api import sync_playwright


def install_font_routes(page):
    """No-op hook: the page pulls its webfonts from Google Fonts directly.
    Kept so a caller behind a blocked network can substitute a local cache."""
    return None


def ready(page, timeout=20000, settle=600):
    page.wait_for_selector("body[data-ready='1']", timeout=timeout)
    page.evaluate("() => document.fonts.ready")
    page.wait_for_timeout(settle)

errs, fails = [], []
def check(name, cond, got=""):
    (print if cond else fails.append)(f"{'PASS' if cond else 'FAIL'}  {name}" + (f"  ({got})" if got and not cond else ""))
    if cond is False:
        print(f"FAIL  {name}  ({got})")

with sync_playwright() as p:
    b = p.chromium.launch(executable_path="/opt/pw-browsers/chromium")
    pg = b.new_page(viewport={"width": 390, "height": 844}, device_scale_factor=2, has_touch=True)
    pg.on("pageerror", lambda e: errs.append(str(e)))
    install_font_routes(pg)
    pg.goto("http://127.0.0.1:8899/mobile.html", wait_until="networkidle")
    ready(pg)

    # --- A: navigation, back button, scroll restore ---
    check("A: hash initialised", pg.evaluate("location.hash") == "#a/14", pg.evaluate("location.hash"))
    check("A: lead appears once in the index",
          pg.eval_on_selector_all("#phone .idx-lead", "e => e.length") == 1)
    n_items = pg.eval_on_selector_all("#phone .idx-item", "e => e.length")
    check("A: list holds the sub-articles only (4 on TEG 14)", n_items == 4, n_items)

    # below 700px the document scrolls, not .scroller — drive whichever it is
    pg.evaluate("""() => {
        const s = document.getElementById('scroller');
        const host = (s && s.scrollHeight > s.clientHeight + 1) ? s : document.scrollingElement;
        host.scrollTop = 300;
    }""")
    pg.wait_for_timeout(200)
    # a short frame clamps 300 to its own maximum; compare against that
    before = pg.evaluate("""() => {
        const s = document.getElementById('scroller');
        const host = (s && s.scrollHeight > s.clientHeight + 1) ? s : document.scrollingElement;
        return Math.round(host.scrollTop);
    }""")
    pg.click('#phone .idx-item[data-open="2"]')
    pg.wait_for_timeout(200)
    check("A: article pushes a history entry", pg.evaluate("location.hash") == "#a/14/story/2",
          pg.evaluate("location.hash"))
    check("A: article heading takes focus",
          pg.evaluate("document.activeElement && document.activeElement.id") == "screen-title",
          pg.evaluate("document.activeElement && document.activeElement.id"))
    pg.go_back()
    pg.wait_for_timeout(250)
    check("A: browser Back returns to the index", pg.eval_on_selector_all("#phone .idx-item", "e => e.length") == 4)
    pos = pg.evaluate("""() => {
        const s = document.getElementById('scroller');
        const host = (s && s.scrollHeight > s.clientHeight + 1) ? s : document.scrollingElement;
        return Math.round(host.scrollTop);
    }""")
    check("A: index scroll position restored", before > 0 and abs(pos - before) < 40,
          f"left at {before}, returned to {pos}")

    # deep link cold
    pg.goto("http://127.0.0.1:8899/mobile.html#a/16/story/1", wait_until="networkidle")
    ready(pg)
    check("A: deep link opens the right article on TEG 16",
          "TEG 16" in pg.inner_text("#phone .tb-title"), pg.inner_text("#phone .tb-title"))

    # --- B: tabs, swipe sync, keyboard ---
    pg.goto("http://127.0.0.1:8899/mobile.html#b/14", wait_until="networkidle")
    ready(pg)
    check("B: panels = articles + appendix",
          pg.eval_on_selector_all("#phone .panel", "e => e.length") == 6,
          pg.eval_on_selector_all("#phone .panel", "e => e.length"))
    check("B: appendix panel has no stray disclosure button",
          pg.eval_on_selector_all("#phone .panel .m-apx-btn", "e => e.length") == 0)
    pg.click('#phone .tab[data-panel="3"]')
    pg.wait_for_timeout(700)
    check("B: tab click moves the track",
          pg.eval_on_selector('#phone .tab[aria-selected="true"]', "e => e.dataset.panel") == "3",
          pg.eval_on_selector('#phone .tab[aria-selected="true"]', "e => e.dataset.panel"))
    pg.keyboard.press("ArrowLeft")
    pg.wait_for_timeout(700)
    check("B: arrow key moves back a panel",
          pg.eval_on_selector('#phone .tab[aria-selected="true"]', "e => e.dataset.panel") == "2",
          pg.eval_on_selector('#phone .tab[aria-selected="true"]', "e => e.dataset.panel"))
    check("B: swipe state stays in the hash", "panel/2" in pg.evaluate("location.hash"),
          pg.evaluate("location.hash"))

    # --- both: touch target sizes and overflow ---
    small = pg.evaluate("""() => [...document.querySelectorAll('#phone button')]
        .filter(b => b.getBoundingClientRect().height > 0 && b.getBoundingClientRect().height < 44).length""")
    check("Touch targets all >= 44px", small == 0, f"{small} too small")
    ov = pg.evaluate("() => document.documentElement.scrollWidth - document.documentElement.clientWidth")
    check("No horizontal page scroll", ov == 0, f"{ov}px")
    b.close()

print("\nJS errors:", errs or "none")
print("FAILURES:", len(fails))
for f in fails:
    print(" ", f)
