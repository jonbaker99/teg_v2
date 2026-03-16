"""Theme management for TEG webapp."""

THEMES = [
    # Minimalist variations
    ("terminal", "Terminal"),
    ("ink", "Ink"),
    ("warm-terminal", "Warm Terminal"),
    ("tight", "Tight"),
    # Claude-inspired
    ("claude", "Claude"),
    ("claude-dark", "Claude Dark"),
    # App-inspired
    ("linear", "Linear"),
    ("stripe", "Stripe"),
    ("vercel", "Vercel"),
    ("github", "GitHub"),
    # Data journalism
    ("datawrapper", "Datawrapper"),
    # Provocative
    ("scorecard", "Scorecard"),
]

THEME_IDS = {t[0] for t in THEMES}
DEFAULT_THEME = "terminal"


def get_theme(request) -> str:
    """Read theme from cookie, falling back to default."""
    theme = request.cookies.get("theme", DEFAULT_THEME)
    return theme if theme in THEME_IDS else DEFAULT_THEME


# Plotly theme overrides keyed by theme id.
# Values are passed into fig.update_layout().

_LIGHT = {
    "paper_bgcolor": "#ffffff",
    "plot_bgcolor": "#ffffff",
    "font_color": "#333333",
}

_DARK_GRID = dict(gridcolor="#333")

PLOTLY_THEMES = {
    # Minimalist
    "terminal": _LIGHT,
    "ink": {
        "paper_bgcolor": "#242424",
        "plot_bgcolor": "#242424",
        "font_color": "#e0e0e0",
        "xaxis": _DARK_GRID,
        "yaxis": _DARK_GRID,
    },
    "warm-terminal": {
        "paper_bgcolor": "#faf6f0",
        "plot_bgcolor": "#faf6f0",
        "font_color": "#3d3225",
    },
    "tight": _LIGHT,
    # Claude
    "claude": {
        "paper_bgcolor": "#ffffff",
        "plot_bgcolor": "#ffffff",
        "font_color": "#2d2118",
    },
    "claude-dark": {
        "paper_bgcolor": "#342e28",
        "plot_bgcolor": "#342e28",
        "font_color": "#e8ddd0",
        "xaxis": dict(gridcolor="#524a40"),
        "yaxis": dict(gridcolor="#524a40"),
    },
    # App-inspired
    "linear": {
        "paper_bgcolor": "#12131f",
        "plot_bgcolor": "#12131f",
        "font_color": "#e2e4ea",
        "xaxis": dict(gridcolor="#2a2b3d"),
        "yaxis": dict(gridcolor="#2a2b3d"),
    },
    "stripe": {
        "paper_bgcolor": "#ffffff",
        "plot_bgcolor": "#ffffff",
        "font_color": "#1a1f36",
    },
    "vercel": {
        "paper_bgcolor": "#fafafa",
        "plot_bgcolor": "#fafafa",
        "font_color": "#171717",
    },
    "github": {
        "paper_bgcolor": "#ffffff",
        "plot_bgcolor": "#ffffff",
        "font_color": "#1f2328",
    },
    # Data journalism
    "datawrapper": {
        "paper_bgcolor": "#ffffff",
        "plot_bgcolor": "#ffffff",
        "font_color": "#1d1d1d",
    },
    # Provocative
    "scorecard": {
        "paper_bgcolor": "#f7f4ec",
        "plot_bgcolor": "#f7f4ec",
        "font_color": "#2c2c1e",
    },
}


def get_plotly_theme(theme: str) -> dict:
    """Return Plotly layout overrides for the given theme."""
    return PLOTLY_THEMES.get(theme, PLOTLY_THEMES[DEFAULT_THEME])
