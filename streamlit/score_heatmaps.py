# streamlit/pages/Hole_Difficulty_Heatmap_plus_Trend.py
# Heatmap (as-is) + scatter/line chart from the same filtered data

import os
import pandas as pd
import streamlit as st
import altair as alt
from utils import load_all_data

# === PAGE LAYOUT CONFIGURATION ===
from utils import get_page_layout
layout = get_page_layout(__file__)
st.set_page_config(layout=layout)
st.title("Hole Difficulty Heatmap + Trends")

# --- CONFIG ---
FILTER_FIELDS = ["Course", "Player", "TEGNum", "Round"]
ROW_CHOICE_FIELDS = ["Course", "Player", "TEGNum", "Round"]
VALUE_FIELD = "GrossVP"   # average score vs par
X_FIELD_CHOICES = ["Hole", "SI", "PAR"]  # <— choose among these
AXIS_LABELS = alt.Axis(labelFont='Open Sans', labelFontSize=10, labelColor='black')
LEGEND_CONFIG = alt.Legend(labelFont='Open Sans', labelFontSize=10, titleFont='Open Sans', titleFontSize=11)
chart_width = 400

# --- Altair setup ---
alt.data_transformers.disable_max_rows()

# --- Data loader ---
@st.cache_data(show_spinner=False)
def load_data() -> pd.DataFrame:
    df = load_all_data()

    # Ensure required fields exist
    required = set([VALUE_FIELD]) | set(FILTER_FIELDS)
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")

    df = df.copy()

    # TEGNum numeric for ordering
    if "TEGNum" in df.columns:
        df["TEGNum"] = pd.to_numeric(df["TEGNum"], errors="coerce").astype("Int64")

    # Round as string for display
    if "Round" in df.columns:
        df["Round"] = df["Round"].astype(str)

    # Strings
    for col in ["Course", "Area", "Player"]:
        if col in df.columns:
            df[col] = df[col].astype(str)

    # Value numeric
    df[VALUE_FIELD] = pd.to_numeric(df[VALUE_FIELD], errors="coerce")

    # Potential X fields numeric
    for xf in X_FIELD_CHOICES:
        if xf in df.columns:
            df[xf] = pd.to_numeric(df[xf], errors="coerce")

    return df

# --- Load data ---
try:
    all_data = load_data()
except Exception as e:
    st.error(str(e))
    st.stop()

# --- UI: Main page controls ---

with st.expander("🔧 Filters & Display Options", expanded=True):
    st.markdown("#### Filters")

    # TEGNum filter options (numeric sort, shown as strings)
    if "TEGNum" in all_data.columns:
        tegnum_order = sorted([int(x) for x in all_data["TEGNum"].dropna().unique().tolist()])
        tegnum_options = ["All"] + [str(x) for x in tegnum_order]
    else:
        tegnum_options = ["All"]

    # Filters in 2 columns
    filter_values = {}
    cols = st.columns(2)
    for idx, field in enumerate(FILTER_FIELDS):
        if field == "TEGNum":
            options = tegnum_options
        else:
            unique_vals = sorted(all_data[field].dropna().astype(str).unique().tolist(), key=str)
            options = unique_vals
        with cols[idx % 2]:
            selected = st.multiselect(f"{field} filter", options)
            filter_values[field] = selected

    st.markdown("#### Rows to show")
    # Row checkboxes in columns
    row_cols = st.columns(len(ROW_CHOICE_FIELDS))
    row_flags = {}
    for idx, field in enumerate(ROW_CHOICE_FIELDS):
        with row_cols[idx]:
            row_flags[field] = st.checkbox(field, value=(field == "Player"))
    HOLE_FIELD = st.segmented_control("X-axis field", X_FIELD_CHOICES, default=X_FIELD_CHOICES[0])

    st.markdown("#### Display Options")
    tick_cols1, tickcols2 = st.columns(2)
    with tick_cols1: sort_rows = st.checkbox("Sort rows by score", value=True)
    # show_values = st.checkbox("Show values on hover", value=True)
    show_values = True
    with tickcols2: show_col_totals = st.checkbox(
        f"Show column totals", value=True
    )
        # --- Heatmap colour scale controls ---
    st.markdown("**Heatmap colour scale controls**")
    diverging_schemes = [
        "redyellowblue", "redblue", "spectral", "redyellowgreen",
        "pinkyellowgreen", "purplegreen", "purpleorange", "redgrey", "blueorange"
    ]
    colour_col1, colour_col2 = st.columns(2)
    with colour_col1: cmap_scheme = st.selectbox("Choose colour scheme", diverging_schemes, index=0)
    with colour_col2: cmap_reverse = st.checkbox("Reverse colours", value=False)
    c1, c2, c3 = st.columns(3)
    with c1:
        cmap_min = st.number_input("Min", value=0.5, step=0.1)
    with c2:
        cmap_mid = st.number_input("Mid", value=1.5, step=0.1)
    with c3:
        cmap_max = st.number_input("Max", value=2.5, step=0.1)


# --- Apply filters ---
df = all_data.copy()
for field, selections in filter_values.items():
    if selections and "All" not in selections:
        if field == "TEGNum":
            df = df[df[field].isin([int(s) for s in selections])]
        else:
            df = df[df[field].isin([str(s) for s in selections])]

# If the chosen X field is missing, stop
if HOLE_FIELD not in df.columns:
    st.error(f"Selected X-axis field '{HOLE_FIELD}' is not in the data.")
    st.stop()

# If no data, stop early
if df.empty:
    st.warning("No data after applying filters. Try relaxing the filters.")
    st.stop()

# --- Build row dimensions & group ---
row_dims = [f for f, on in row_flags.items() if on]
group_dims = row_dims + [HOLE_FIELD]

# Aggregate: average GrossVP per selected rows + X field
agg = (
    df.groupby(group_dims, dropna=False, as_index=False)[VALUE_FIELD]
      .mean()
      .rename(columns={VALUE_FIELD: "AvgGrossVP"})
)

# Row label builder (force integer for TEGNum, trim Course prefix)
def make_row_label(row: pd.Series, dims: list[str]) -> str:
    if not dims:
        return "All"
    parts = []
    for d in dims:
        val = row[d]
        if d == "TEGNum" and pd.notna(val):
            val = str(int(val))
        else:
            val = str(val)
        if d == "Course" and val.startswith("PGA Catalunya - "):
            val = val.replace("PGA Catalunya - ", "")
        parts.append(val)
    return " | ".join(parts)

agg["RowLabel"] = "All" if not row_dims else agg.apply(lambda r: make_row_label(r, row_dims), axis=1)

# --- X-axis categories & ordering ---
if HOLE_FIELD in ["Hole", "SI"]:
    x_categories = list(range(1, 19))
    present = set(pd.to_numeric(df[HOLE_FIELD], errors="coerce").dropna().astype(int).tolist())
    x_categories = [v for v in x_categories if v in present] or list(range(1, 19))
    agg = agg[agg[HOLE_FIELD].isin(x_categories)]
    agg[HOLE_FIELD] = pd.Categorical(agg[HOLE_FIELD], categories=x_categories, ordered=True)
    x_axis_title = HOLE_FIELD

elif HOLE_FIELD == "Par":
    present = sorted(pd.to_numeric(df[HOLE_FIELD], errors="coerce").dropna().astype(int).unique().tolist())
    x_categories = [p for p in [3, 4, 5] if p in present]
    if not x_categories:
        st.warning("No valid Par values in the filtered data.")
        st.stop()
    agg = agg[agg[HOLE_FIELD].isin(x_categories)]
    agg[HOLE_FIELD] = pd.Categorical(agg[HOLE_FIELD], categories=x_categories, ordered=True)
    x_axis_title = "Par"
else:
    x_categories = sorted(df[HOLE_FIELD].dropna().unique().tolist())
    if not x_categories:
        st.warning(f"No values found for {HOLE_FIELD} in the filtered data.")
        st.stop()
    agg = agg[agg[HOLE_FIELD].isin(x_categories)]
    agg[HOLE_FIELD] = pd.Categorical(agg[HOLE_FIELD], categories=x_categories, ordered=True)
    x_axis_title = HOLE_FIELD

# --- Optional column totals (TOTAL row) ---
if show_col_totals and row_dims:
    col_totals = (
        df.groupby(HOLE_FIELD, as_index=False)[VALUE_FIELD]
          .mean()
          .rename(columns={VALUE_FIELD: "AvgGrossVP"})
    )
    col_totals = col_totals[col_totals[HOLE_FIELD].isin(x_categories)]
    col_totals["RowLabel"] = "TOTAL"
    agg = pd.concat([agg, col_totals], ignore_index=True)
    agg[HOLE_FIELD] = pd.Categorical(agg[HOLE_FIELD], categories=x_categories, ordered=True)

# --- Row order for both charts ---
if sort_rows:
    order = (
        agg.groupby("RowLabel", as_index=False)["AvgGrossVP"]
           .mean()
           .sort_values("AvgGrossVP", ascending=False)["RowLabel"]
           .tolist()
    )
    if "TOTAL" in order:
        order = [x for x in order if x != "TOTAL"] + ["TOTAL"]
else:
    if row_dims:
        labels = agg[row_dims].drop_duplicates().copy()
        if "TEGNum" in row_dims:
            labels["TEGNum_num"] = pd.to_numeric(labels["TEGNum"], errors="coerce")
        if "Round" in row_dims:
            labels["Round_num"] = pd.to_numeric(labels["Round"], errors="coerce")

        by = []
        for d in row_dims:
            by.append({"TEGNum": "TEGNum_num", "Round": "Round_num"}.get(d, d))

        labels["RowLabel"] = labels.apply(lambda r: make_row_label(r, row_dims), axis=1)
        labels = labels.sort_values(by=by, kind="mergesort")
        order = labels["RowLabel"].tolist()
        if "TOTAL" in agg["RowLabel"].values:
            order = order + ["TOTAL"]
    else:
        order = ["All"]

# --- Descriptive title ---
def pretty_sel(field: str, sels: list[str]) -> str:
    if (not sels) or ("All" in sels):
        return None
    return f"{field}: {', '.join(map(str, sels))}" if len(sels) <= 3 else f"{field}: {len(sels)} selected"

title_bits = [pretty_sel(f, s) for f, s in filter_values.items()]
title_bits = [b for b in title_bits if b]
title_suffix = " • ".join(title_bits) if title_bits else "All data"

st.markdown(f"#### Heatmap: Average {VALUE_FIELD} by {HOLE_FIELD}")
st.caption(f"Colour shows average {VALUE_FIELD} (score vs par). {title_suffix}")

# =======================
# Chart A — Heatmap (as-is)
# =======================
tooltip = [
    alt.Tooltip(f"{HOLE_FIELD}:O", title=x_axis_title),
    alt.Tooltip("RowLabel:N", title="Group"),
    alt.Tooltip("AvgGrossVP:Q", title="Avg GrossVP", format=".2f"),
] if show_values else None

x_sort = x_categories

heatmap = (
    alt.Chart(agg, height=max(100, 28 * len(order) + 60), width=100)
    .mark_rect()
    .encode(
        x=alt.X(f"{HOLE_FIELD}:O",
                title=x_axis_title,
                sort=x_sort,
                scale=alt.Scale(paddingInner=0.15, paddingOuter=0.05),
                axis=AXIS_LABELS),
        y=alt.Y("RowLabel:N",
                title=None,
                sort=order,
                scale=alt.Scale(paddingInner=0.15, paddingOuter=0.05),
                axis=AXIS_LABELS),
                color=alt.Color(
            "AvgGrossVP:Q",
            title="Avg GrossVP",
            scale=alt.Scale(
                scheme=cmap_scheme,
                reverse=cmap_reverse,
                domainMin=cmap_min,
                domainMid=cmap_mid,
                domainMax=cmap_max,
            ),
            legend=LEGEND_CONFIG,
        ),

        tooltip=tooltip,
    )
)

show_cell_text = st.checkbox("Show values", value=True)
if show_cell_text:
    text = (
        alt.Chart(agg)
        .mark_text(baseline="middle", align="center", fontSize=10, font='Open Sans')
        .encode(
            x=alt.X(f"{HOLE_FIELD}:O", sort=x_sort),
            y=alt.Y("RowLabel:N", sort=order),
            text=alt.Text("AvgGrossVP:Q", format=".1f"),
        )
    )
    heatmap_chart = heatmap + text
else:
    heatmap_chart = heatmap

st.altair_chart(heatmap_chart, use_container_width=True)

# =======================
# Chart B — Scatter/Line using SAME filtered agg
# =======================
st.markdown(f"#### Line chart: Average {VALUE_FIELD} by {HOLE_FIELD}")

# Split data for TOTAL vs others
has_total = "TOTAL" in agg["RowLabel"].unique()
line_order = [x for x in order if x != "TOTAL"]

non_total = agg[agg["RowLabel"] != "TOTAL"] if has_total else agg.copy()
total_df = agg[agg["RowLabel"] == "TOTAL"] if has_total else pd.DataFrame(columns=agg.columns)

# Base per-group lines + points
lines = (
    alt.Chart(non_total)
    .mark_line(point=True)
    .encode(
        x=alt.X(f"{HOLE_FIELD}:O", sort=x_sort, title=x_axis_title, axis=AXIS_LABELS),
        y=alt.Y("AvgGrossVP:Q", title="Mean GrossVP", axis=AXIS_LABELS),
        color=alt.Color("RowLabel:N", title="Group", sort=line_order, scale = alt.Scale(scheme = "set1"), legend=LEGEND_CONFIG),
        tooltip=[
            alt.Tooltip("RowLabel:N", title="Group"),
            alt.Tooltip(f"{HOLE_FIELD}:O", title=x_axis_title),
            alt.Tooltip("AvgGrossVP:Q", title="Mean GrossVP", format=".2f"),
        ],
    )
    .properties(height=300, width = chart_width)
)

# Optional TOTAL in solid black
if has_total:
    total_line = (
        alt.Chart(total_df)
        .mark_line(point=True, strokeWidth=3)
        .encode(
            x=alt.X(f"{HOLE_FIELD}:O", sort=x_sort, title=x_axis_title, axis=AXIS_LABELS),
            y=alt.Y("AvgGrossVP:Q", title="Mean GrossVP", axis=AXIS_LABELS),
            color=alt.value("black"),
            tooltip=[
                alt.Tooltip("RowLabel:N", title="Group"),
                alt.Tooltip(f"{HOLE_FIELD}:O", title=x_axis_title),
                alt.Tooltip("AvgGrossVP:Q", title="Mean GrossVP", format=".2f"),
            ],
        )
    )
    trend_chart = (lines + total_line.properties(width=chart_width))
else:
    trend_chart = lines

st.altair_chart(trend_chart, use_container_width=True)
