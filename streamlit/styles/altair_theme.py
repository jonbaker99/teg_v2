"""
altair_theme.py
---------------
Centralised Altair theming with a tiny deep-merge.

Hierarchy:
- CORE_THEME
- BAR_THEME  = CORE_THEME + BAR_SPECIFICS
- LINE_THEME = CORE_THEME + LINE_SPECIFICS
- CHART_X_THEME = (BAR_THEME or LINE_THEME) + per-chart overrides

Usage (example):
---------------
import altair as alt
from streamlit.styles.altair_theme import BAR_THEME, LINE_THEME, theme_for, PALETTE

# Bar:
bar_chart = (
    alt.Chart(bar_df)
      .mark_bar()
      .encode(x="Category:N", y="Value:Q",
              color=alt.Color("Category:N", scale=alt.Scale(range=PALETTE), legend=None))
      .properties(title="My Bar")
      .configure(**BAR_THEME["config"])
)

# Line with a tiny chart-specific override (centre title):
line_chart = (
    alt.Chart(line_df)
      .mark_line(size=2, interpolate="monotone")
      .encode(x="x:Q", y="y:Q", color=alt.Color("Category:N", scale=alt.Scale(range=PALETTE), legend=None))
      .properties(title="My Line")
      .configure(**theme_for("line", {"config": {"title": {"anchor": "middle"}}})["config"])
)
"""

from __future__ import annotations
import copy
from typing import Dict, Optional

# ======================
# General variables (edit these freely)
# ======================

# Fonts
FONT_MONO = "'Roboto Mono', ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Courier New', monospace"
FONT_SANS = "'Open Sans', Arial, sans-serif"

# Font sizes
FONT_SIZE_LABEL = 12        # axis/legend labels
FONT_SIZE_AXIS_TITLE = 12   # axis titles
FONT_SIZE_TITLE = 16        # chart titles
FONT_SIZE_LEGEND = 12       # legend labels

# Colours
BG_COLOR = "#F3F3F3"        # chart background
TITLE_COLOR = "#222"        # chart title colour
AXIS_LABEL_COLOR = "#333"   # tick label colour
AXIS_TITLE_COLOR = "#333"   # axis title colour

# Palettes
PALETTE = [
    "#3E7CB1",  # blue
    "#8FBF9F",  # green
    "#E1B07E",  # tan
    "#D17A88",  # rose
    "#8C99AE",  # grey-blue
    "#6C9A8B"   # teal
]

PALETTE_SECONDARY = [
    "#555555",  # dark grey
    "#777777",  # mid grey
    "#999999",  # light grey
    "#BBBBBB",  # pale grey
    "#DDDDDD",  # very pale
    "#333333"   # near black
]

HIGHLIGHT_COLOR = "#FF6600"  # accent colour for emphasis


# ======================
# Tiny deep merge helper (recursive dict overlay)
# ======================
def deep_merge(base: Dict, overrides: Optional[Dict]) -> Dict:
    """
    Return a deep copy of `base` with `overrides` applied (recursive on dicts).
    Non-dict values in overrides replace base.
    """
    if not overrides:
        return copy.deepcopy(base)
    out = copy.deepcopy(base)
    for k, v in overrides.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = deep_merge(out[k], v)
        else:
            out[k] = copy.deepcopy(v)
    return out


# ======================
# CORE THEME (edit here once; cascades everywhere)
# ======================
CORE_THEME: Dict = {
    "config": {
        # Background of the plotting area
        "background": BG_COLOR,

        # Plot "view" frame
        "view": {
            "strokeWidth": 0,         # 0 = no border; set >0 to show an outline
            # "stroke": "#cccccc",    # OPTIONAL: colour of the outline
        },

        # Axes (x & y). You can override per-axis in a chart if needed.
        "axis": {
            "domain": False,          # hide the main axis line
            "grid": False,            # hide grid lines (set True for grids)
            "ticks": False,           # hide tick marks
            "labelFont": FONT_MONO,
            "titleFont": FONT_MONO,
            "labelColor": AXIS_LABEL_COLOR,
            "titleColor": AXIS_TITLE_COLOR,
            "labelFontSize": FONT_SIZE_LABEL,
            "titleFontSize": FONT_SIZE_AXIS_TITLE,
            "labelAngle": 0,          # 0 = horizontal labels
            # "gridColor": "#e9e9e9", # OPTIONAL: grid line colour
            # "tickColor": "#aaaaaa", # OPTIONAL: tick line colour
        },

        # Legend
        "legend": {
            "title": None,            # no legend title by default
            "labelFont": FONT_MONO,
            "labelFontSize": FONT_SIZE_LEGEND,
            # "orient": "bottom",     # OPTIONAL: top/right/left/bottom
            # "fillColor": "#ffffff", # OPTIONAL: legend bg
            # "strokeColor": "#cccccc"# OPTIONAL: legend border
        },

        # Chart title (set via .properties(title="..."))
        "title": {
            "font": FONT_MONO,
            "fontSize": FONT_SIZE_TITLE,
            "color": TITLE_COLOR,
            "anchor": "start",        # start=left, middle=center, end=right
            # "orient": "bottom",     # OPTIONAL: move title below chart
            # "fontWeight": "bold",   # OPTIONAL: normal|bold|100–900
            # "offset": 12,           # OPTIONAL: spacing from chart
        },

        # Default mark styling (bars, lines, areas, points…)
        "mark": {
            "filled": True,           # bars/areas filled by default
            "strokeWidth": 1          # default line thickness
            # "cornerRadius": 4,      # OPTIONAL: round corners on bars
            # "opacity": 0.95,        # OPTIONAL: global mark opacity
        },
    }
}


# ======================
# FAMILY-SPECIFIC ADD-ONS
# (only small differences from CORE go here)
# ======================
BAR_SPECIFICS: Dict = {
    "config": {
        "title": {"fontSize": 18},   # slightly larger titles on bars
        # "axis": {"grid": True, "gridColor": "#ececec"},  # OPTIONAL: grid just for bars
    }
}

LINE_SPECIFICS: Dict = {
    "config": {
        "mark": {"strokeWidth": 2},  # thicker default lines
        # "axis": {"grid": True, "gridColor": "#f0f0f0"},  # OPTIONAL: grid just for lines
    }
}


# ======================
# BUILT THEMES (ready to use)
# ======================
BAR_THEME  = deep_merge(CORE_THEME, BAR_SPECIFICS)
LINE_THEME = deep_merge(CORE_THEME, LINE_SPECIFICS)


# ======================
# Convenience: pick a family + optional per-chart overrides
# ======================
def theme_for(kind: str, chart_overrides: Optional[Dict] = None) -> Dict:
    """
    kind: "bar" or "line" (anything else returns CORE_THEME)
    chart_overrides: optional dict to overlay on top of the family theme
                     e.g. {"config": {"title": {"anchor": "middle"}}}
    """
    family = {"bar": BAR_THEME, "line": LINE_THEME}.get(kind, CORE_THEME)
    return deep_merge(family, chart_overrides)
