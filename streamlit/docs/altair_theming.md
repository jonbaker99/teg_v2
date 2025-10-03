# Altair Chart Styling Guide

This guide explains how to style Altair charts in this project using the centralised `altair_theme.py` file.

---

## 1. Overview

Altair uses a **config dictionary** to control chart styling.  
We store shared settings in `altair_theme.py` so changes can be made in one place.

Structure:
- **General variables**: fonts, font sizes, colours, palettes.
- **core_theme()**: base theme for all charts.
- **bar_theme() / line_theme()**: inherit the core theme and add chart-family tweaks.
- **Chart-specific overrides**: applied directly in the chart definition with `.configure_*`.

---

## 2. Key Theme Sections

### Background
```python
"background": "#F3F3F3"   # chart background colour
````

### View (plotting area box)

```python
"view": {
  "strokeWidth": 0        # set >0 to show a border
  # "stroke": "#ccc"      # border colour (optional)
}
```

### Axis

```python
"axis": {
  "domain": False,        # hide axis line
  "grid": False,          # show/hide grid lines
  "ticks": False,         # show/hide tick marks
  "labelFont": FONT_MONO,
  "titleFont": FONT_MONO,
  "labelColor": "#333",
  "titleColor": "#333",
  "labelFontSize": 12,
  "titleFontSize": 12,
  "labelAngle": 0,        # rotate tick labels
  # "gridColor": "#e9e9e9" # custom grid colour
}
```

### Legend

```python
"legend": {
  "title": None,          # legend title text
  "labelFont": FONT_MONO,
  "labelFontSize": 12,
  # "orient": "bottom",   # move legend (top/right/left/bottom)
  # "fillColor": "#fff",  # legend background
  # "strokeColor": "#ccc" # legend border
}
```

### Title

```python
"title": {
  "font": FONT_MONO,
  "fontSize": 16,
  "color": "#222",
  "anchor": "start",      # start=left, middle=center, end=right
  # "orient": "bottom",   # move title below chart
  # "fontWeight": "bold",
  # "offset": 12          # spacing from chart
}
```

### Marks (the graphical elements)

```python
"mark": {
  "filled": True,         # fill bars/areas
  "strokeWidth": 1,       # line thickness
  # "cornerRadius": 4,    # round bar corners
  # "opacity": 0.9        # transparency
}
```

---

## 3. Palettes and Colours

Defined once in `altair_theme.py`:

```python
PALETTE = ["#3E7CB1", "#8FBF9F", "#E1B07E", "#D17A88", "#8C99AE", "#6C9A8B"]
PALETTE_SECONDARY = ["#555555", "#777777", "#999999", "#BBBBBB", "#DDDDDD", "#333333"]
HIGHLIGHT_COLOR = "#FF6600"
```

Use them in charts:

```python
color=alt.Color("Category:N", scale=alt.Scale(range=PALETTE))
```

---

## 4. How to Apply a Theme

### Bar chart

```python
import altair as alt
from streamlit.styles.altair_theme import bar_theme, PALETTE

bar_chart = (
    alt.Chart(bar_df)
      .mark_bar()
      .encode(
          x="Category:N",
          y="Value:Q",
          color=alt.Color("Category:N", scale=alt.Scale(range=PALETTE))
      )
      .properties(title="My Bar Chart")
      .configure(**bar_theme()["config"])   # Apply bar theme
)
```

### Line chart

```python
import altair as alt
from streamlit.styles.altair_theme import line_theme, PALETTE

line_chart = (
    alt.Chart(line_df)
      .mark_line(interpolate="monotone", size=2)
      .encode(
          x="x:Q",
          y="y:Q",
          color=alt.Color("Category:N", scale=alt.Scale(range=PALETTE))
      )
      .properties(title="My Line Chart")
      .configure(**line_theme()["config"])  # Apply line theme
)
```

---

## 5. Overriding Settings for One Chart

If you need a one-off tweak:

```python
bar_chart.configure_title(anchor="middle")     # centre the title
bar_chart.configure_axis(labelFontSize=14)     # bigger axis labels
bar_chart.configure_legend(orient="bottom")    # move legend below chart
```

These overrides only affect that chart, not the global theme.

---

## 6. Tips & Tricks

* Use `bar_theme()` for all bar charts and `line_theme()` for all line charts to keep consistency.
* Change fonts, sizes, colours in `altair_theme.py` — they cascade across all charts.
* Keep `PALETTE` consistent across charts so categories share the same colours.
* Use `HIGHLIGHT_COLOR` to draw attention to a single series or bar.
* Start simple: uncomment extras (grid, rounded corners, opacity) only when you need them.

---

## 7. Further Reading

* [Altair Configuration Docs](https://altair-viz.github.io/user_guide/configuration.html)
* [Vega-Lite Config Reference](https://vega.github.io/vega-lite/docs/config.html)

