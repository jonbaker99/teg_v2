# streamlit/pages/Hole_Difficulty_Heatmap_plus_Trend.py
# Heatmap (as-is) + scatter/line chart from the same filtered data

import os
import pandas as pd
import streamlit as st
import altair as alt
from utils import load_all_data

st.set_page_config(page_title="Hole Difficulty Heatmap + Trends", layout="centered")

# --- CONFIG ---
FILTER_FIELDS = ["Course", "Player", "TEGNum", "Round"]
ROW_CHOICE_FIELDS = ["Course", "Player", "TEGNum", "Round"]
VALUE_FIELD = "GrossVP"   # average score vs par
X_FIELD_CHOICES = ["Hole", "SI", "Par"]  # <— choose among these
AXIS_LABELS = alt.Axis(labelFont='Open Sans', labelFontSize=10, labelColor='black')


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
with st.expander("🔧 Filters & Options", expanded=True):
    st.subheader("Filters")

    # TEGNum filter options (numeric sort, shown as strings)
    if "TEGNum" in all_data.columns:
        tegnum_order = sorted([int(x) for x in all_data["TEGNum"].dropna().unique().tolist()])
        tegnum_options = ["All"] + [str(x) for x in tegnum_order]
    else:
        tegnum_options = ["All"]

    filter_values = {}
    for field in FILTER_FIELDS:
        if field == "TEGNum":
            options = tegnum_options
        else:
            unique_vals = sorted(all_data[field].dropna().astype(str).unique().tolist(), key=str)
            options = unique_vals
        selected = st.multiselect(f"{field} filter", options)
        filter_values[field] = selected

    st.markdown("---")
    st.subheader("Rows to show")
    row_flags = {f: st.checkbox(f, value=(f == "Player")) for f in ROW_CHOICE_FIELDS}

    st.markdown("---")
    st.subheader("Display Options")
    HOLE_FIELD = st.selectbox("X-axis field", X_FIELD_CHOICES, index=0)
    sort_rows = st.checkbox("Sort rows by overall difficulty (mean GrossVP)", value=False)
    show_values = st.checkbox("Show values on hover", value=True)
    show_col_totals = st.checkbox(
        f"Show column totals (mean by {HOLE_FIELD} across filtered data)", value=True
    )
    st.caption("Tip: Use the filters above to narrow the dataset, then pick row dimensions to group by.")

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

st.markdown("#### Hole Score Heatmap")
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
            scale=alt.Scale(scheme="redblue", reverse=False, domainMin=0, domainMid=1, domainMax=3),
        ),
        tooltip=tooltip,
    )
)

show_cell_text = st.checkbox("Overlay values as text (may be busy)", value=False)
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
st.markdown(f"#### Average {VALUE_FIELD} by {HOLE_FIELD}")
st.caption(
    "Each coloured line corresponds to a heatmap row. "
    "If column totals are shown above, a black line shows the TOTAL."
)

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
        color=alt.Color("RowLabel:N", title="Group", sort=line_order, scale = alt.Scale(scheme = "set1")),
        tooltip=[
            alt.Tooltip("RowLabel:N", title="Group"),
            alt.Tooltip(f"{HOLE_FIELD}:O", title=x_axis_title),
            alt.Tooltip("AvgGrossVP:Q", title="Mean GrossVP", format=".2f"),
        ],
    )
    .properties(height=280)
)

# Optional TOTAL in solid black
if has_total:
    total_line = (
        alt.Chart(total_df)
        .mark_line(point=True, strokeWidth=3)
        .encode(
            x=alt.X(f"{HOLE_FIELD}:O", sort=x_sort, title=x_axis_title),
            y=alt.Y("AvgGrossVP:Q", title="Mean GrossVP"),
            color=alt.value("black"),
            tooltip=[
                alt.Tooltip("RowLabel:N", title="Group"),
                alt.Tooltip(f"{HOLE_FIELD}:O", title=x_axis_title),
                alt.Tooltip("AvgGrossVP:Q", title="Mean GrossVP", format=".2f"),
            ],
        )
    )
    trend_chart = lines + total_line
else:
    trend_chart = lines

st.altair_chart(trend_chart, use_container_width=True)
