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

# --- ALTair setup ---
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

    # Keep TEGNum numeric (integer) for sorting
    if "TEGNum" in df.columns:
        df["TEGNum"] = pd.to_numeric(df["TEGNum"], errors="coerce").astype("Int64")

    # Round should be string (for display)
    if "Round" in df.columns:
        df["Round"] = df["Round"].astype(str)

    # Course / Area / Player as strings
    for col in ["Course", "Area", "Player"]:
        if col in df.columns:
            df[col] = df[col].astype(str)

    # Ensure numeric value field
    df[VALUE_FIELD] = pd.to_numeric(df[VALUE_FIELD], errors="coerce")

    return df


# --- UI: Sidebar controls ---
st.sidebar.header("Filters")

try:
    all_data = load_data()
except Exception as e:
    st.error(str(e))
    st.stop()

# --- Build TEGNum filter options (sorted numerically) ---
if "TEGNum" in all_data.columns:
    tegnum_order = sorted([x for x in all_data["TEGNum"].dropna().unique() if pd.notna(x)])
    tegnum_options = ["All"] + [str(int(x)) for x in tegnum_order]

# --- Build filter widgets ---
filter_values = {}
for field in FILTER_FIELDS:
    if field == "TEGNum":
        options = tegnum_options
    else:
        unique_vals = sorted(all_data[field].dropna().astype(str).unique().tolist(), key=str)
        options = ["All"] + unique_vals
    selected = st.sidebar.multiselect(f"{field} filter", options, default=["All"])
    filter_values[field] = selected

st.sidebar.markdown("---")
st.sidebar.header("Rows (group by)")
row_flags = {}
for field in ROW_CHOICE_FIELDS:
    row_flags[field] = st.sidebar.checkbox(field, value=(field == "Player"))  # default: Player on

st.sidebar.markdown("---")
sort_rows = st.sidebar.checkbox("Sort rows by overall difficulty (mean GrossVP)", value=True)
show_values = st.sidebar.checkbox("Show values on hover", value=True)
st.sidebar.caption("Tip: Use the filters above to narrow the dataset, then pick row dimensions to group by.")

# --- Apply filters ---
df = all_data.copy()
for field, selections in filter_values.items():
    if selections and "All" not in selections:
        if field == "TEGNum":
            df = df[df[field].isin([int(s) for s in selections])]
        else:
            df = df[df[field].isin([str(s) for s in selections])]

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

# --- Row label builder ---
def make_row_label(row: pd.Series, dims: list[str]) -> str:
    if not dims:
        return "All"
    parts = []
    for d in dims:
        val = row[d]
        if d == "TEGNum" and pd.notna(val):
            val = str(int(val))  # remove .0
        parts.append(f"{d}={val}")
    return " | ".join(parts)

if not row_dims:
    agg["RowLabel"] = "All"
else:
    agg["RowLabel"] = agg.apply(lambda r: make_row_label(r, row_dims), axis=1)

# --- Ensure holes ordered 1–18 ---
valid_holes = list(range(1, 19))
agg = agg[agg[HOLE_FIELD].isin(valid_holes)]
agg[HOLE_FIELD] = pd.Categorical(agg[HOLE_FIELD], categories=valid_holes, ordered=True)

# --- Optional row sorting ---
if sort_rows:
    order = (
        agg.groupby("RowLabel", as_index=False)["AvgGrossVP"]
           .mean()
           .sort_values("AvgGrossVP", ascending=False)["RowLabel"]
           .tolist()
    )
else:
    order = sorted(agg["RowLabel"].unique().tolist(), key=str)

# --- Title/context ---
def pretty_sel(field: str, sels: list[str]) -> str:
    if (not sels) or ("All" in sels):
        return None
    if len(sels) <= 3:
        return f"{field}: {', '.join(map(str, sels))}"
    return f"{field}: {len(sels)} selected"

title_bits = [pretty_sel(f, s) for f, s in filter_values.items()]
title_bits = [b for b in title_bits if b]
title_suffix = " • ".join(title_bits) if title_bits else "All data"

st.title("Hole-by-Hole Difficulty Heatmap")
st.caption(f"Colour shows average {VALUE_FIELD} (score vs par). {title_suffix}")

# --- Heatmap chart ---
tooltip = [
    alt.Tooltip(HOLE_FIELD, type="ordinal", title="Hole"),
    alt.Tooltip("RowLabel:N", title="Group"),
    alt.Tooltip("AvgGrossVP:Q", title="Avg GrossVP", format=".2f")
] if show_values else None

heatmap = (
    alt.Chart(agg, height=max(100, 30 * len(order)+60), width=100)
    .mark_rect()
    .encode(
        x=alt.X(f"{HOLE_FIELD}:O", title="Hole", sort=valid_holes,
                scale=alt.Scale(paddingInner=0.15, paddingOuter=0.05)),
        y=alt.Y("RowLabel:N", title="Rows", sort=order,
                scale=alt.Scale(paddingInner=0.15, paddingOuter=0.05)),
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
        .mark_text(baseline="middle", align="center")
        .encode(
            x=alt.X(f"{HOLE_FIELD}:O", sort=valid_holes),
            y=alt.Y("RowLabel:N", sort=order),
            text=alt.Text("AvgGrossVP:Q", format=".1f"),
        )
    )
    chart = heatmap + text
else:
    chart = heatmap

st.altair_chart(chart, use_container_width=True)

# --- Data preview & download ---
with st.expander("Show aggregated data"):
    st.dataframe(agg[[*row_dims, HOLE_FIELD, "AvgGrossVP"]] if row_dims else agg[[HOLE_FIELD, "AvgGrossVP"]])
    csv = agg.to_csv(index=False)
    st.download_button("Download aggregated CSV", data=csv,
                       file_name="hole_difficulty_aggregated.csv", mime="text/csv")
