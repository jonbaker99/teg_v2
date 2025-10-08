# streamlit/pages/SI_vs_GrossVP.py
import pandas as pd
import numpy as np
import altair as alt
import streamlit as st
from utils import load_all_data

st.set_page_config(page_title="SI vs GrossVP", layout="wide")
st.title("SI vs GrossVP")

# --- Altair setup ---
alt.data_transformers.disable_max_rows()

# --- Load + tidy ---
@st.cache_data(show_spinner=False)
def get_data():
    df = load_all_data()
    # keep only needed cols, drop nulls
    needed = {"SI", "GrossVP", "Pl"}
    missing = needed - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {missing}")
    df = df[list(needed)].dropna(subset=["SI", "GrossVP", "Pl"]).copy()

    # ensure SI is integer 1..18 and also provide numeric copy for fitting
    df["SI"] = pd.to_numeric(df["SI"], errors="coerce").astype("Int64")
    df = df[df["SI"].between(1, 18)]
    df["SI_num"] = df["SI"].astype(int)
    return df

df = get_data()
si_sort = list(range(1, 19))
players = sorted(df["Pl"].dropna().unique().tolist())

# =========================
# Chart 1: mean(GrossVP) by SI, coloured by Pl,
#          with an overall "line of best fit" (Total)
# =========================

st.subheader("Mean GrossVP by SI (coloured by Player) + Overall Trend")

# player means (line for each player)
player_means = (
    alt.Chart(df)
    .mark_line(point=True)
    .encode(
        x=alt.X("SI:O", sort=si_sort, title="SI"),
        y=alt.Y("mean(GrossVP):Q", title="Mean GrossVP"),
        color=alt.Color("Pl:N", title="Player"),
        tooltip=[
            alt.Tooltip("Pl:N", title="Player"),
            alt.Tooltip("SI:O", title="SI"),
            alt.Tooltip("mean(GrossVP):Q", title="Mean GrossVP", format=".2f"),
        ],
    )
)

# overall line of best fit (Total) — compute simple linear regression y = a*SI + b
@st.cache_data(show_spinner=False)
def compute_overall_trend(_df: pd.DataFrame) -> pd.DataFrame:
    x = _df["SI_num"].astype(float).values
    y = _df["GrossVP"].astype(float).values
    if len(x) < 2:
        # fallback: flat line at overall mean if not enough points
        a, b = 0.0, float(np.nanmean(y) if len(y) else 0.0)
    else:
        a, b = np.polyfit(x, y, 1)
    xs = np.arange(1, 19, dtype=float)
    yhat = a * xs + b
    return pd.DataFrame({"SI": xs.astype(int), "yhat": yhat})

trend_df = compute_overall_trend(df)

trend_line = (
    alt.Chart(trend_df)
    .mark_line(size=3, strokeDash=[6, 4])
    .encode(
        x=alt.X("SI:O", sort=si_sort, title="SI"),
        y=alt.Y("yhat:Q", title="Mean GrossVP"),
        color=alt.value("black"),
        tooltip=[
            alt.Tooltip("SI:O", title="SI"),
            alt.Tooltip("yhat:Q", title="Trend (Total)", format=".2f"),
        ],
    )
)

legend_note = alt.Chart(
    pd.DataFrame({"label": ["Trend (Total)"]})
).mark_point(filled=True, size=100, shape="line").encode(
    color=alt.value("black"),
    tooltip=alt.Tooltip("label:N", title="")
).properties(height=0)

st.altair_chart((player_means + trend_line).resolve_scale(y="shared"), use_container_width=False)
st.caption("Dashed black line is the overall line of best fit (all players combined).")

# =========================
# Chart 2: Box plot of GrossVP by SI with Pl filter (or All)
# =========================
st.subheader("Box Plot of GrossVP by SI")

pl_choice = st.selectbox("Filter by Player", options=["All"] + players, index=0)

if pl_choice != "All":
    df_box = df[df["Pl"] == pl_choice].copy()
else:
    df_box = df.copy()

box = (
    alt.Chart(df_box)
    .mark_boxplot(outliers=True)
    .encode(
        x=alt.X("SI:O", sort=si_sort, title="SI"),
        y=alt.Y("GrossVP:Q", title="GrossVP"),
        tooltip=[
            alt.Tooltip("SI:O", title="SI"),
            alt.Tooltip("GrossVP:Q", title="GrossVP", format=".2f"),
            alt.Tooltip("Pl:N", title="Player"),
        ],
    )
)

# Jittered points layer (Altair 5.x)
# Adds a tiny random offset per point so dots don't stack on each other at each SI
pts = (
    alt.Chart(df_box)
    .transform_calculate(
        # small symmetric jitter; tweak 0.35 to spread more/less
        jitter="(random()-0.5) * 0.7"
    )
    .mark_circle(size=45, opacity=0.28)
    .encode(
        x=alt.X("SI:O", sort=si_sort, title="SI"),
        # apply horizontal jitter at each SI bucket
        xOffset=alt.XOffset("jitter:Q"),
        y=alt.Y("GrossVP:Q", title="GrossVP"),
        tooltip=[
            alt.Tooltip("Pl:N", title="Player"),
            alt.Tooltip("SI:O", title="SI"),
            alt.Tooltip("GrossVP:Q", title="GrossVP", format=".2f"),
        ],
    )
)


st.altair_chart((box + pts), use_container_width=False)

# Info footer
if pl_choice == "All":
    st.caption("Showing all players. Use the selector above to focus on a single player.")
else:
    st.caption(f"Filtered to **{pl_choice}**.")
