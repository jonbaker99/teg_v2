import streamlit as st
import pandas as pd
import numpy as np
import altair as alt

st.set_page_config(page_title="Altair Step — togglable lines/points")
st.title("Step chart with optional lines/points and end labels")

# ---------------- Data ----------------
rng = np.random.default_rng(42)
x = np.arange(1, 73)  # 1..72
cats = list("ABCDEF")

data = []
for i, c in enumerate(cats):
    baseline = 40 + i * 3
    smooth = baseline + np.linspace(0, 8, 72) + rng.normal(0, 0.5, 72).cumsum()/4
    y = np.round(smooth, 1)
    data.append(pd.DataFrame({"x": x, "y": y, "Category": c}))
df = pd.concat(data, ignore_index=True)

last_points = (
    df.sort_values("x")
      .groupby("Category", as_index=False)
      .tail(1)
      .assign(label=lambda d: d["Category"] + " " + d["y"].round(1).astype(str))
)

# ---------------- Controls ----------------
plot_lines = True
plot_points = True
show_end_labels = True

PALETTE = ["#3E7CB1", "#8FBF9F", "#E1B07E", "#D17A88", "#8C99AE", "#6C9A8B"]

# ---------------- Theme ----------------
def altair_theme():
    return {
        "config": {
            "background": "#F3F3F3",
            "view": {"strokeWidth": 0},
            "axis": {
                "domain": False, "grid": False, "ticks": False,
                "labelColor": "#333", "titleColor": "#333",
                "labelFontSize": 12, "titleFontSize": 12
            },
            "legend": {"title": None, "labelFontSize": 12},
            "title": {
                "font": "roboto mono, monospace",
                "fontSize": 16,
                "color": "#222",
                "anchor":"middle",
                "offset": 25
                }
        }
    }

# ---------------- Base encodings (note the x-domain) ----------------
base = alt.Chart(df).encode(
    x=alt.X(
        "x:Q",
        title="X Axis",
        scale=alt.Scale(domain=[1, 72], nice=False),  # hard stop at 72
        axis=alt.Axis(values=list(range(0, 73, 9)), labelAngle=0)  # ticks every 9
    ),
    y=alt.Y("y:Q", title="Y Axis", scale=alt.Scale(nice=True, zero=False)),
    color=alt.Color("Category:N", scale=alt.Scale(range=PALETTE), legend=None)
)

# Line layer
#interpolate options: linear, step, step-before, step-after, basis, cardinal, monotone
line_layer = base.mark_line(size=2, interpolate="monotone")

# Optional point layer
point_layer = base.mark_point(filled=True, size=20, stroke="white", strokeWidth=1)

# End labels: use x=72 (last value), offset right with dx
end_labels = (
    alt.Chart(last_points)
    .mark_text(align="left", baseline="middle", dx=6, fontSize=12)
    .encode(
        x="x:Q",
        y="y:Q",
        color=alt.Color("Category:N", scale=alt.Scale(range=PALETTE), legend=None),
        text="label:N"
    )
)

# ---------------- Build chart ----------------
# Build the layer according to booleans
layers = []
if plot_lines:
    layers.append(line_layer)
if plot_points:
    layers.append(point_layer)
if show_end_labels:
    layers.append(end_labels)

# If nothing selected, at least show end labels (or an empty chart)
chart = alt.layer(*layers) if layers else alt.Chart(last_points)

chart = chart.properties(
    width=800, height=420, title="Placeholder Step Chart Title",
    padding={"left": 10, "right": 10, "top": 10, "bottom": 10}
).configure(**altair_theme()["config"])

# title configuratoin: commented out as already set in theme
# chart = chart.configure_title(fontSize=18, anchor="start", color="#333")

st.altair_chart(chart, use_container_width=False)
