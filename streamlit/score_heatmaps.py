# 11_Hole_Difficulty_Heatmap.py
# Dynamic hole-by-hole difficulty heatmap (Altair) with filters and row grouping

import os
import pandas as pd
import streamlit as st
import altair as alt
from utils import load_all_data

st.set_page_config(page_title="Hole Difficulty Heatmap", layout="centered")

# --- CONFIG ---
FILTER_FIELDS = ["Area", "Course", "Player", "TEGNum", "Round"]
ROW_CHOICE_FIELDS = ["Course", "Player", "TEGNum", "Round"]
VALUE_FIELD = "GrossVP"   # average score vs par
HOLE_FIELD = "Hole"

# --- Altair setup ---
alt.data_transformers.disable_max_rows()

# --- Data loader ---
@st.cache_data(show_spinner=False)
def load_data() -> pd.DataFrame:
    df = load_all_data()

    # Ensure required fields exist
    required = set([VALUE_FIELD, HOLE_FIELD]) | set(FILTER_FIELDS)
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")

    df = df.copy()
    df[HOLE_FIELD] = pd.to_numeric(df[HOLE_FIELD], errors="coerce").astype("Int64")

    # Keep TEGNum numeric for proper ordering
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
    return df

# --- Load data ---
try:
    all_data = load_data()
except Exception as e:
    st.error(str(e))
    st.stop()

# --- UI: Main page controls in expander ---
with st.expander("🔧 Filters & Options", expanded=True):
    st.subheader("Filters")

    # TEGNum filter options (numeric sort, shown as strings)
    if "TEGNum" in all_data.columns:
        tegnum_order = sorted([int(x) for x in all_data["TEGNum"].dropna().unique().tolist()])
        tegnum_options = ["All"] + [str(x) for x in tegnum_order]
    else:
        tegnum_options = ["All"]

    # Build filter widgets with "All"
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
    st.subheader("Rows (group by)")
    row_flags = {f: st.checkbox(f, value=(f == "Course")) for f in ROW_CHOICE_FIELDS}

    st.markdown("---")
    st.subheader("Display Options")
    sort_rows = st.checkbox("Sort rows by overall difficulty (mean GrossVP)", value=False)
    show_values = st.checkbox("Show values on hover", value=True)
    show_col_totals = st.checkbox("Show column totals (mean by hole across filtered data)", value=True)
    st.caption("Tip: Use the filters above to narrow the dataset, then pick row dimensions to group by.")

# --- Apply filters ---
df = all_data.copy()
for field, selections in filter_values.items():
    # Treat "All" (or empty) as no filter
    if selections and "All" not in selections:
        if field == "TEGNum":
            df = df[df[field].isin([int(s) for s in selections])]
        else:
            df = df[df[field].isin([str(s) for s in selections])]

# If no data, stop early
if df.empty:
    st.warning("No data after applying filters. Try relaxing the filters.")
    st.stop()

# --- Build row dimensions & group ---
row_dims = [f for f, on in row_flags.items() if on]
group_dims = row_dims + [HOLE_FIELD]

# Aggregate: average GrossVP per selected rows + Hole
agg = (
    df.groupby(group_dims, dropna=False, as_index=False)[VALUE_FIELD]
      .mean()
      .rename(columns={VALUE_FIELD: "AvgGrossVP"})
)

# Row label builder (force integer display for TEGNum, clean up Course names)
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
        # Strip "PGA Catalunya - " from course names
        if d == "Course" and val.startswith("PGA Catalunya - "):
            val = val.replace("PGA Catalunya - ", "")
        parts.append(val)
    return " | ".join(parts)

if not row_dims:
    agg["RowLabel"] = "All"
else:
    agg["RowLabel"] = agg.apply(lambda r: make_row_label(r, row_dims), axis=1)

# Ensure holes are ordered 1..18 and keep only valid ones
valid_holes = list(range(1, 19))
agg = agg[agg[HOLE_FIELD].isin(valid_holes)]
agg[HOLE_FIELD] = pd.Categorical(agg[HOLE_FIELD], categories=valid_holes, ordered=True)

# Optionally add column totals (average per hole across all filtered rows)
if show_col_totals and row_dims:
    col_totals = (
        df.groupby(HOLE_FIELD, as_index=False)[VALUE_FIELD]
          .mean()
          .rename(columns={VALUE_FIELD: "AvgGrossVP"})
    )
    col_totals = col_totals[col_totals[HOLE_FIELD].isin(valid_holes)]
    col_totals["RowLabel"] = "TOTAL"
    agg = pd.concat([agg, col_totals], ignore_index=True)

# --- Determine row order ---
if sort_rows:
    # By difficulty (hardest first)
    order = (
        agg.groupby("RowLabel", as_index=False)["AvgGrossVP"]
           .mean()
           .sort_values("AvgGrossVP", ascending=False)["RowLabel"]
           .tolist()
    )
    if show_col_totals and row_dims:
        order = [x for x in order if x != "Column Avg"] + ["Column Avg"]
else:
    # Numeric-aware sort by the *actual row fields* in the order selected
    if row_dims:
        labels = agg[row_dims].drop_duplicates().copy()
        if "TEGNum" in row_dims:
            labels["TEGNum_num"] = pd.to_numeric(labels["TEGNum"], errors="coerce")
        if "Round" in row_dims:
            labels["Round_num"] = pd.to_numeric(labels["Round"], errors="coerce")

        by = []
        for d in row_dims:
            if d == "TEGNum":
                by.append("TEGNum_num")
            elif d == "Round":
                by.append("Round_num")
            else:
                by.append(d)

        labels["RowLabel"] = labels.apply(lambda r: make_row_label(r, row_dims), axis=1)
        labels = labels.sort_values(by=by, kind="mergesort")
        order = labels["RowLabel"].tolist()
        if show_col_totals and row_dims:
            order = order + ["Column Avg"]
    else:
        order = ["All"]

# --- Title/context ---
def pretty_sel(field: str, sels: list[str]) -> str:
    if (not sels) or ("All" in sels):
        return None
    return f"{field}: {', '.join(map(str, sels))}" if len(sels) <= 3 else f"{field}: {len(sels)} selected"

# Function to get just the filter values without field names
def get_filter_display() -> str:
    all_selections = []
    for field, sels in filter_values.items():
        if sels and "All" not in sels:
            # Clean up Course names
            cleaned_sels = []
            for sel in sels:
                if field == "Course" and sel.startswith("PGA Catalunya - "):
                    cleaned_sels.append(sel.replace("PGA Catalunya - ", ""))
                else:
                    cleaned_sels.append(sel)
            all_selections.extend(cleaned_sels)
    return " | ".join(all_selections) if all_selections else "All data"

title_bits = [pretty_sel(f, s) for f, s in filter_values.items()]
title_bits = [b for b in title_bits if b]
title_suffix = " • ".join(title_bits) if title_bits else "All data"

st.title("Hole Score Heatmap")
st.caption(f"Colour shows average {VALUE_FIELD} (score vs par). {title_suffix}")

# --- Heatmap chart ---
tooltip = [
    alt.Tooltip(HOLE_FIELD, type="ordinal", title="Hole"),
    alt.Tooltip("RowLabel:N", title="Group"),
    alt.Tooltip("AvgGrossVP:Q", title="Avg GrossVP", format=".2f"),
] if show_values else None

heatmap = (
    alt.Chart(agg, height=max(100, 28 * len(order)+60), width=100)
    .mark_rect()
    .encode(
        x=alt.X(f"{HOLE_FIELD}:O", title="Hole", sort=valid_holes,
                scale=alt.Scale(paddingInner=0.15, paddingOuter=0.05),
                axis=alt.Axis(labelFont='Open Sans', labelFontSize=10,labelColor='black')),
        y=alt.Y("RowLabel:N", title=None, sort=order,
                scale=alt.Scale(paddingInner=0.15, paddingOuter=0.05),
                axis=alt.Axis(labelLimit=0, labelFont='Open Sans', labelFontSize=10,labelColor='black')),
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
        .mark_text(baseline="middle", align="center", fontSize=10, font = 'Open Sans')
        .encode(
            x=alt.X(f"{HOLE_FIELD}:O", sort=valid_holes),
            y=alt.Y("RowLabel:N", sort=order),
            text=alt.Text("AvgGrossVP:Q", format=".1f"),
        )
    )
    chart = heatmap + text
else:
    chart = heatmap

st.altair_chart(chart)

