"""Theme management for TEG webapp."""

THEMES = [
    ("mono", "Mono"),
    ("clean-page", "Clean Page"),
    ("clean-layered", "Clean Layered"),
]

THEME_IDS = {t[0] for t in THEMES}
# Mono is the production design. The previous design lives on as the
# "clean-page" theme (untouched) — set DEFAULT_THEME back to it to revert.
# See webapp/static/themes/archive/pre-mono-backup/REVERT.md.
DEFAULT_THEME = "mono"


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

# Mono theme — charts sit inside a shaded band, so the plot surface matches the
# band colour (--band-bg) rather than the page, and the font uses the axis token.
_MONO_LIGHT = {
    "paper_bgcolor": "#f6f6f3",
    "plot_bgcolor": "#f6f6f3",
    "font_color": "#8a8d82",
}
_MONO_DARK = {
    "paper_bgcolor": "#1b1b1b",
    "plot_bgcolor": "#1b1b1b",
    "font_color": "#7d7d7d",
}

PLOTLY_THEMES = {
    "mono": _MONO_LIGHT,
    "clean-page": _LIGHT,
    "clean-layered": _LIGHT,
}


def get_plotly_theme(theme: str, mode: str = "light") -> dict:
    """Return Plotly layout overrides for the given theme + mode.

    Mode is light by default so existing chart callers are unaffected; pass
    ``mode="dark"`` (from ``request.state.mode``) to get the dark surface.
    """
    if mode == "dark":
        return _MONO_DARK if theme == "mono" else _DARK
    return PLOTLY_THEMES.get(theme, PLOTLY_THEMES[DEFAULT_THEME])
