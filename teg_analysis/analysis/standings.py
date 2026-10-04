"""Round and TEG totals with positions, from a holes frame.

One definition shared by TEGBot's lookups and the sandbox toolkit. Net competition
is NetVP up to TEG 7 (lowest wins) and Stableford from TEG 8 (highest wins). Ranks use
``method="min"``, so ties share a position.
"""
from __future__ import annotations

from typing import Iterable

import pandas as pd


def trophy_rank(df: pd.DataFrame, keys: list[str]) -> pd.Series:
    """Rank in the net competition within ``keys``."""
    from teg_analysis.analysis.scoring import get_net_competition_measure
    by_net = df.groupby(keys)["NetVP"].rank(method="min")
    by_stab = df.groupby(keys)["Stableford"].rank(method="min", ascending=False)
    net_era = df["TEGNum"].map(lambda t: get_net_competition_measure(int(t)) == "NetVP")
    return by_net.where(net_era, by_stab)


def build_rounds(holes: pd.DataFrame) -> pd.DataFrame:
    """One row per player per round: totals, plus position in the round and after it."""
    keys = ["Player", "Pl", "TEGNum", "Year", "Round", "Course"]
    keys += [c for c in ("Area", "Date") if c in holes.columns]
    df = holes.groupby(keys, as_index=False).agg(
        Sc=("Sc", "sum"), GrossVP=("GrossVP", "sum"), NetVP=("NetVP", "sum"),
        Stableford=("Stableford", "sum"), HC=("HC", "first"), Holes=("Hole", "size"),
    )
    if "Date" in df.columns and df["Date"].map(lambda v: isinstance(v, str)).any():
        df["Date"] = pd.to_datetime(df["Date"], format="%d/%m/%Y", errors="coerce").dt.date
    df = df.sort_values(["TEGNum", "Round", "Player"]).reset_index(drop=True)
    df["RoundJacketPos"] = df.groupby(["TEGNum", "Round"])["GrossVP"].rank(method="min")
    df["RoundTrophyPos"] = trophy_rank(df, ["TEGNum", "Round"])
    cum = df.groupby(["TEGNum", "Player"])[["GrossVP", "NetVP", "Stableford"]].cumsum()
    after = df[["TEGNum", "Round"]].join(cum)
    df["JacketPosAfterRound"] = after.groupby(["TEGNum", "Round"])["GrossVP"].rank(method="min")
    df["TrophyPosAfterRound"] = trophy_rank(after, ["TEGNum", "Round"])
    for col in ("RoundJacketPos", "RoundTrophyPos", "JacketPosAfterRound", "TrophyPosAfterRound"):
        df[col] = df[col].astype("Int64")
    return df


def build_tegs(holes: pd.DataFrame, complete: Iterable[int]) -> pd.DataFrame:
    """One row per player per TEG. Final positions are blank while a TEG is in progress."""
    keys = ["Player", "Pl", "TEGNum", "Year"]
    if "Area" in holes.columns:
        keys.append("Area")
    df = holes.groupby(keys, as_index=False).agg(
        Sc=("Sc", "sum"), GrossVP=("GrossVP", "sum"), NetVP=("NetVP", "sum"),
        Stableford=("Stableford", "sum"), HC=("HC", "first"),
        Rounds=("Round", "nunique"), Holes=("Hole", "size"),
    )
    df["Complete"] = df["TEGNum"].isin(set(int(t) for t in complete))
    df["JacketPosition"] = df.groupby("TEGNum")["GrossVP"].rank(method="min")
    df["TrophyPosition"] = trophy_rank(df, ["TEGNum"])
    df["FieldSize"] = df.groupby("TEGNum")["Player"].transform("size")
    for col in ("JacketPosition", "TrophyPosition"):
        df[col] = df[col].astype("Int64").where(df["Complete"])
    return df.sort_values(["TEGNum", "TrophyPosition"]).reset_index(drop=True)
