"""Theme management for TEG webapp."""

THEMES = [
    ("clean-page", "Clean Page"),
    ("clean-layered", "Clean Layered"),
    ("clean", "Clean"),
]

THEME_IDS = {t[0] for t in THEMES}
DEFAULT_THEME = "clean-page"


def get_theme(request) -> str:
    """Read theme from cookie, falling back to default."""
    theme = request.cookies.get("theme", DEFAULT_THEME)
    return theme if theme in THEME_IDS else DEFAULT_THEME


# Title style options — controls page-title-area CSS via body class ts-X
TITLE_STYLES = [
    ("a",  "Title: A — Mono label"),
    ("b",  "Title: B — All caps"),
    ("c",  "Title: C — Breadcrumb"),
    ("d",  "Title: D — Left rule"),
    ("e",  "Title: E — Underline"),
    ("c1", "Title: C1 — Green block"),
    ("c2", "Title: C2 — White/green"),
    ("c3", "Title: C3 — Grey block"),
    ("f1", "Title: F1 — Card green"),
    ("f2", "Title: F2 — Card green text"),
    ("f3", "Title: F3 — Card grey"),
    ("f4", "Title: F4 — Card green inline"),
    ("f5", "Title: F5 — Card green inline white"),
]

TITLE_STYLE_IDS = {s[0] for s in TITLE_STYLES}
DEFAULT_TITLE_STYLE = "a"


def get_title_style(request) -> str:
    """Read title style from cookie, falling back to default."""
    ts = request.cookies.get("title_style", DEFAULT_TITLE_STYLE)
    return ts if ts in TITLE_STYLE_IDS else DEFAULT_TITLE_STYLE


# Plotly theme overrides keyed by theme id.
# Values are passed into fig.update_layout().

_LIGHT = {
    "paper_bgcolor": "#ffffff",
    "plot_bgcolor": "#ffffff",
    "font_color": "#333333",
}

PLOTLY_THEMES = {
    "clean-page": _LIGHT,
    "clean-layered": _LIGHT,
    "clean": _LIGHT,
}


def get_plotly_theme(theme: str) -> dict:
    """Return Plotly layout overrides for the given theme."""
    return PLOTLY_THEMES.get(theme, PLOTLY_THEMES[DEFAULT_THEME])
