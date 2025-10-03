import streamlit as st
import pandas as pd
import numpy as np
import altair as alt

st.set_page_config(page_title="Altair Column")
st.title("Altair column chart")

st.markdown(
    """
    <link href="https://fonts.googleapis.com/css2?family=Roboto+Mono:wght@400;500;700&display=swap" rel="stylesheet">
    """,
    unsafe_allow_html=True
)

# ----- Data -----
rng = np.random.default_rng(7)
bar_df = pd.DataFrame({
    "Category": list("ABCDEF"),
    "Value": rng.integers(20, 120, size=6)
})

# ----- Theme helper -----
def altair_min_theme_mono():
    # A monospace font stack for cross-platform consistency
    mono = "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Courier New', monospace"
    return {
        "config": {
            # Background of the plotting area (e.g. "white", "transparent", "lightgrey")
            "background": "#F3F3F3",

            # Settings for the chart "view" (the drawing canvas)
            "view": {
                # Stroke width of the chart border (0 = no border box around chart)
                "strokeWidth": 0
            },

            # Axis formatting (applies to both x and y unless overridden)
            "axis": {
                # Show/hide the axis line
                "domain": False,
                # Show/hide grid lines
                "grid": False,
                # Show/hide tick marks
                "ticks": False,
                # Font family for axis labels
                "labelFont": mono,
                # Font family for axis title
                "titleFont": mono,
                # Colour of the tick labels
                "labelColor": "black",
                # Colour of the axis title
                "titleColor": "#3a3a3a",
                # Size of the tick labels (in pt)
                "labelFontSize": 14,
                # Size of the axis title text (in pt)
                "titleFontSize": 14,
                # Rotation of x-axis labels (0 = horizontal)
                "labelAngle": 0
            },

            # Legend formatting
            "legend": {
                # Hide legend title
                "title": None,
                # Font family for legend labels
                "labelFont": mono,
                # Font size for legend labels
                "labelFontSize": 14
            },

            # Title formatting
            "title": {
                # Font family for chart title
                "font": mono,
                # Font size for chart title
                "fontSize": 14,
                # Colour for chart title
                "color": "#333",
            }
        }
    }


mono_font = "'Roboto Mono', ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Courier New', monospace"

# ----- Base chart -----
base = alt.Chart(bar_df).encode(
    x=alt.X("Category:N", title="X axis"),
    y=alt.Y("Value:Q", title="Y Axis", scale=alt.Scale(nice=True, zero=True))
)

# BAR FORMATTING
bars = base.mark_bar(
    color="#173E72", # <── bar fill colour
    cornerRadiusTopLeft=0, # <── rounded top corners
    cornerRadiusTopRight=0
)

# BAR LABELS
labels = base.mark_text(
    dy=-20,
    font=mono_font,
    fontSize=16,
    color="#173E72"
).encode(
    text=alt.Text("Value:Q", format=",.0f")
)

# ----- Layer and set fixed width -----
chart = alt.layer(bars, labels).properties(
    width=400,   # <── fixed width
    height=340,
    padding={"left": 6, "right": 6, "top": 10, "bottom": 12},
    title = "A chart title"
).configure(**altair_min_theme_mono()["config"])


st.altair_chart(chart, use_container_width=False)
