"""Theme management for TEG webapp."""

THEMES = [
    ("clean-page", "Clean Page"),
    ("clean-layered", "Clean Layered"),
]

THEME_IDS = {t[0] for t in THEMES}
DEFAULT_THEME = "clean-page"


def get_theme(request) -> str:
    """Read theme from cookie, falling back to default."""
    theme = request.cookies.get("theme", DEFAULT_THEME)
    return theme if theme in THEME_IDS else DEFAULT_THEME


# Light/dark mode — orthogonal to the named theme. A theme picks the palette
# family; the mode flips it light↔dark by overriding the CSS variables (see
# static/themes/dark.css, scoped under html[data-mode="dark"]).
# Default is LIGHT so existing/desktop users see no change unless they opt in.
MODES = {"light", "dark"}
DEFAULT_MODE = "light"


def get_mode(request) -> str:
    """Read light/dark mode from cookie, falling back to light."""
    mode = request.cookies.get("mode", DEFAULT_MODE)
    return mode if mode in MODES else DEFAULT_MODE


# Title style options — controls page-title-area CSS via body class ts-X
TITLE_STYLES = [
    ("a",  "Title: A — Mono label"),
    ("b",  "Title: B — All caps"),
    ("c",  "Title: C — Breadcrumb"),
    ("e",  "Title: E — Underline"),
    ("e2", "Title: E2 — Underline on page"),
    ("c1", "Title: C1 — Green block"),
    ("c3", "Title: C3 — Grey block"),
    ("f1", "Title: F1 — Card green"),
    ("f3", "Title: F3 — Card grey"),
    ("f4", "Title: F4 — Card inline"),
    ("f5", "Title: F5 — Card green inline white"),
    # Mobile-only options (2026-09-17): on phones "The El Golfo" (nav-brand)
    # and the page title sit close together in the same bold serif, reading as
    # near-duplicates -- desktop has enough surrounding page chrome that the
    # same pairing doesn't clash. Jon picked M2 (brand recedes); that rule now
    # ships unconditionally in mobile.css rather than gated behind ts-m2, so
    # it applies regardless of which desktop title style (a/b/c/...) is
    # chosen here -- the two concerns are independent. M1/M3 remain
    # selectable for reference against the band-style alternatives that were
    # passed over. All three are no-ops above 640px, so picking one here
    # never changes desktop/iPad output.
    ("m1", "Title: M1 — Mobile: green band (alternative, not picked)"),
    ("m2", "Title: M2 — Mobile: brand recedes (shipped default)"),
    ("m3", "Title: M3 — Mobile: grey band + brand recedes (alternative, not picked)"),
]

TITLE_STYLE_IDS = {s[0] for s in TITLE_STYLES}
DEFAULT_TITLE_STYLE = "a"


def get_title_style(request) -> str:
    """Read title style from cookie, falling back to default."""
    ts = request.cookies.get("title_style", DEFAULT_TITLE_STYLE)
    return ts if ts in TITLE_STYLE_IDS else DEFAULT_TITLE_STYLE


# Card header style options — controls .card-header CSS via body class ch-X
CARD_HEADER_STYLES = [
    ("ch0", "Card hdr: Off"),
    ("ch1", "Card hdr: CH1 — Grey bar"),
    ("ch2", "Card hdr: CH2 — Label above"),
    ("ch3", "Card hdr: CH3 — Serif above"),
]
CARD_HEADER_IDS = {s[0] for s in CARD_HEADER_STYLES}
# Serif section headers (ch3) read like the Streamlit site's Lora headings (Phase 1a).
DEFAULT_CARD_HEADER = "ch3"


def get_card_header_style(request) -> str:
    """Read card header style from cookie, falling back to default."""
    ch = request.cookies.get("card_header", DEFAULT_CARD_HEADER)
    return ch if ch in CARD_HEADER_IDS else DEFAULT_CARD_HEADER


# Nav-cue style options — controls the phone-only .section-nav "more tabs to
# scroll" affordance via body class nc-X (mobile.css, scoped inside the
# existing @media (max-width: 640px) block). Default is "arrows" (Jon's pick,
# 2026-09-17); "off" (the old mask-fade-only look) and "chevron" (the
# alternative compared against) stay selectable at /design/headers.
NAV_CUE_STYLES = [
    ("off", "Nav cue: Off (old mask fade only, alternative)"),
    ("arrows", "Nav cue: Arrows at ends (shipped default)"),
    ("chevron", "Nav cue: Faint chevron near edge (alternative, not picked)"),
]
NAV_CUE_IDS = {s[0] for s in NAV_CUE_STYLES}
DEFAULT_NAV_CUE = "arrows"  # 2026-09-17: Jon picked arrows over chevron/off
# from the mobile tab-row overflow prototyping round.


def get_nav_cue(request) -> str:
    """Read nav-cue style from cookie, falling back to default."""
    nc = request.cookies.get("nav_cue", DEFAULT_NAV_CUE)
    return nc if nc in NAV_CUE_IDS else DEFAULT_NAV_CUE


# Plotly theme overrides keyed by theme id.
# Values are passed into fig.update_layout().

_LIGHT = {
    "paper_bgcolor": "#ffffff",
    "plot_bgcolor": "#ffffff",
    "font_color": "#333333",
}

_DARK = {
    "paper_bgcolor": "#16150f",
    "plot_bgcolor": "#16150f",
    "font_color": "#ececea",
}

PLOTLY_THEMES = {
    "clean-page": _LIGHT,
    "clean-layered": _LIGHT,
}


def get_plotly_theme(theme: str, mode: str = "light") -> dict:
    """Return Plotly layout overrides for the given theme + mode.

    Mode is light by default so existing chart callers are unaffected; pass
    ``mode="dark"`` (from ``request.state.mode``) to get the dark surface.
    """
    if mode == "dark":
        return _DARK
    return PLOTLY_THEMES.get(theme, PLOTLY_THEMES[DEFAULT_THEME])
