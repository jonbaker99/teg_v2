"""Player profile routes."""

import logging
import math
from functools import lru_cache
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from fastapi import APIRouter, Request, HTTPException, Query
from fastapi.templating import Jinja2Templates
from markupsafe import escape

from teg_analysis.core.players import get_player_dict, get_name_to_code
from teg_analysis.analysis.history import (
    get_eagles_data,
    calculate_trophy_jacket_doubles,
)
from teg_analysis.analysis.aggregation import STABLEFORD_ERA_TEG
from teg_analysis.analysis.scoring import (
    calculate_par_performance_matrix,
    format_par_performance_table,
    format_vs_par,
    get_net_competition_measure,
)
from teg_analysis.analysis.streaks import (
    get_max_streaks,
    get_current_streaks,
    STREAK_CONFIGS,
    prepare_record_best_streaks_data,
    prepare_record_worst_streaks_data,
)
from teg_analysis.analysis.handicaps import (
    get_current_handicaps_formatted,
    get_next_teg_and_check_if_in_progress_fast,
)
from teg_analysis.display.formatters import (
    prepare_records_table,
    prepare_worst_records_table,
    prepare_score_count_records_table,
)
from webapp import deps
from webapp.deps import (
    cached_load_all_data,
    cached_round_data,
    cached_complete_teg_data,
    cached_ranked_teg_data,
    cached_ranked_round_data,
    cached_ranked_frontback_data,
    format_value,
)
from webapp.chart_utils import get_chart_style
from webapp.tables import df_to_html as _table_df_to_html

logger = logging.getLogger(__name__)

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))

PLAYER_TABS = [
    ("overview", "Overview"),
    ("career", "Career record"),
    ("rounds", "Rounds"),
    ("scoring", "Scoring"),
    ("records", "Records & Streaks"),
]


def _get_player_list():
    """Return sorted list of (code, name) tuples."""
    return sorted(get_player_dict().items(), key=lambda x: x[1])


def _validate_player(player_code: str) -> str:
    """Validate player code and return it uppercased, or raise 404."""
    pc = player_code.upper()
    if pc not in get_player_dict():
        raise HTTPException(status_code=404, detail=f"Unknown player code: {player_code}")
    return pc


def _ordinal(n: int) -> str:
    """Return ordinal string for an integer (1st, 2nd, 3rd, 11th, etc.)."""
    if 11 <= n % 100 <= 13:
        return f"{n}th"
    return f"{n}{['th','st','nd','rd'][n % 10] if n % 10 < 4 else 'th'}"


# ---------------------------------------------------------------------------
# Overview metrics (with cross-player rankings)
# ---------------------------------------------------------------------------

def _rank_str(series: pd.Series, name: str, ascending: bool) -> str:
    """Rank ``name`` within a per-player Series; joint ranks get an '=' suffix."""
    s = series.dropna()
    if name not in s.index:
        return "–"
    ranks = s.rank(method="min", ascending=ascending)
    r = int(ranks[name])
    tied = int((ranks == r).sum()) > 1
    return f"{r}=" if tied else str(r)


def _ordinal_rank(rank_str: str) -> str:
    """Convert a raw rank string to ordinal form: '1=' → '1st =', '3' → '3rd'."""
    if rank_str in ("–", ""):
        return rank_str
    tied = rank_str.endswith("=")
    n = int(rank_str.rstrip("="))
    return _ordinal(n) + (" =" if tied else "")


def _metric_specs(all_data, rd_data, winners):
    """Per-player Series for every overview metric.

    Returns a list of (label, series, ascending, formatter, unranked_if_zero).
    ``ascending`` controls rank direction (True = lower is better, so rank 1 is
    the lowest value); ``unranked_if_zero`` suppresses the rank for honour/count
    metrics where the player has a zero tally.
    """
    players = [n for n in get_player_dict().values() if (all_data["Player"] == n).any()]
    clean = winners.replace(r"\*", "", regex=True)

    tegs_played = all_data.groupby("Player")["TEGNum"].nunique()
    rounds_played = rd_data.groupby("Player").size()
    holes_played = all_data[all_data["Sc"].notna()].groupby("Player").size()
    avg_gvp = rd_data.groupby("Player")["GrossVP"].mean()
    avg_stab = rd_data.groupby("Player")["Stableford"].mean()
    par_avgs = {
        par: all_data[all_data["PAR"] == par].groupby("Player")["GrossVP"].mean()
        for par in (3, 4, 5)
    }

    trophy = clean["TEG Trophy"].value_counts()
    jacket = clean["Green Jacket"].value_counts()
    spoon = clean["HMM Wooden Spoon"].value_counts()
    total_trophies = trophy.add(jacket, fill_value=0)

    doubles_df, _ = calculate_trophy_jacket_doubles(winners)
    doubles = (doubles_df.set_index("Player")["Doubles"]
               if not doubles_df.empty else pd.Series(dtype=float))

    eagles = get_eagles_data(all_data)
    eagles_ct = eagles["Player"].value_counts() if not eagles.empty else pd.Series(dtype=int)
    birdies_ct = all_data[all_data["GrossVP"] == -1]["Player"].value_counts()
    pars_ct = all_data[all_data["GrossVP"] == 0]["Player"].value_counts()
    triples_ct = all_data[all_data["GrossVP"] >= 3]["Player"].value_counts()

    def fill(s):
        return s.reindex(players).fillna(0)

    int_fmt = lambda v: str(int(round(v)))
    comma_fmt = lambda v: f"{int(round(v)):,}"
    per_hole = lambda v: f"{v:+.2f}"
    return [
        ("TEGs Played",      fill(tegs_played),       False, int_fmt,                 False),
        ("Rounds Played",    fill(rounds_played),     False, int_fmt,                 False),
        ("Holes Played",     fill(holes_played),      False, comma_fmt,               False),
        ("Avg Gross vs Par", avg_gvp.reindex(players), True,  lambda v: f"{v:+.1f}",  False),
        ("Avg Stableford",   avg_stab.reindex(players), False, lambda v: f"{v:.1f}",  False),
        ("Par 3s / hole",    par_avgs[3].reindex(players), True, per_hole,            False),
        ("Par 4s / hole",    par_avgs[4].reindex(players), True, per_hole,            False),
        ("Par 5s / hole",    par_avgs[5].reindex(players), True, per_hole,            False),
        ("Total Trophies",   fill(total_trophies),    False, int_fmt,                 True),
        ("TEG Trophies",     fill(trophy),            False, int_fmt,                 True),
        ("Green Jackets",    fill(jacket),            False, int_fmt,                 True),
        ("Wooden Spoons",    fill(spoon),             False, int_fmt,                 True),
        ("Doubles",          fill(doubles),           False, int_fmt,                 True),
        ("Eagles",           fill(eagles_ct),         False, int_fmt,                 True),
        ("Birdies",          fill(birdies_ct),        False, int_fmt,                 True),
        ("Pars",             fill(pars_ct),           False, int_fmt,                 True),
        # Fewer is better: rank 1 is the player with the fewest.
        ("Triples or Worse", fill(triples_ct),        True,  int_fmt,                 False),
    ]


def _metric_cell(specs: list, name: str, label: str) -> tuple[str, str, float | None]:
    """Return (display value, ordinal rank like '1st' / '1st=' / '–', raw value)."""
    for lbl, series, ascending, fmt, unranked_if_zero in specs:
        if lbl != label:
            continue
        if name not in series.index or pd.isna(series[name]):
            return "–", "–", None
        raw = float(series[name])
        if unranked_if_zero and raw == 0:
            rank = "–"
        else:
            rank = _ordinal_rank(_rank_str(series, name, ascending)).replace(" =", "=")
        return fmt(raw), rank, raw
    return "–", "–", None


def _metric_columns(specs: list, name: str) -> tuple[list[dict], int]:
    """Honours / Averages / Counting columns for the overview, plus ranked-player count."""
    layout = [
        ("Honours", [
            ("Green Jackets", "Green Jackets", True),
            ("TEG Trophies", "TEG Trophies", True),
            ("Doubles", "Doubles", False),
            ("Total silverware", "Total Trophies", False),
            ("Wooden Spoons", "Wooden Spoons", False),
        ]),
        ("Averages", [
            ("Gross vs par / round", "Avg Gross vs Par", False),
            ("Stableford / round", "Avg Stableford", False),
            ("Par 3s / hole", "Par 3s / hole", False),
            ("Par 4s / hole", "Par 4s / hole", False),
            ("Par 5s / hole", "Par 5s / hole", False),
        ]),
        ("Counting", [
            ("TEGs played", "TEGs Played", False),
            ("Rounds played", "Rounds Played", False),
            ("Holes played", "Holes Played", False),
            ("Eagles", "Eagles", False),
            ("Birdies", "Birdies", False),
            ("Pars", "Pars", False),
            ("Triple bogey or worse", "Triples or Worse", False),
        ]),
    ]
    columns = []
    for title, rows in layout:
        out = []
        for display, label, honour in rows:
            value, rank, raw = _metric_cell(specs, name, label)
            out.append({"label": display, "value": value, "rank": rank,
                        "accent": bool(honour and raw)})
        columns.append({"title": title, "rows": out})
    n_ranked = len(specs[0][1].dropna()) if specs else 0
    return columns, n_ranked


# ---------------------------------------------------------------------------
# Career highlights / colour points
# ---------------------------------------------------------------------------

# _records_held / _worsts_held build player-INDEPENDENT global tables
# (prepare_records_table/prepare_worst_records_table over the three ranked
# datasets, plus the streaks and score-count builders) and only then filter
# rows to one player. That global computation was previously redone on every
# request for every player (~1.5s each) -- cache the six global artifacts
# here, keyed by nothing (or a level string), and registered with
# deps.register_cache_clearer so a data update still invalidates them.

@lru_cache(maxsize=None)
def _cached_records_table(level: str):
    """prepare_records_table for one level ('teg', 'round', or 'frontback')."""
    dataset = {
        'teg': cached_ranked_teg_data,
        'round': cached_ranked_round_data,
        'frontback': cached_ranked_frontback_data,
    }[level]()
    return prepare_records_table(dataset, level)


@lru_cache(maxsize=None)
def _cached_worst_records_table(level: str):
    """prepare_worst_records_table for one level ('teg', 'round', or 'frontback')."""
    dataset = {
        'teg': cached_ranked_teg_data,
        'round': cached_ranked_round_data,
        'frontback': cached_ranked_frontback_data,
    }[level]()
    return prepare_worst_records_table(dataset, level)


@lru_cache(maxsize=1)
def _cached_best_streaks():
    return prepare_record_best_streaks_data(cached_load_all_data())


@lru_cache(maxsize=1)
def _cached_worst_streaks():
    return prepare_record_worst_streaks_data(cached_load_all_data())


@lru_cache(maxsize=1)
def _cached_score_count_records():
    return prepare_score_count_records_table(cached_load_all_data())


for _clear_fn in (
    _cached_records_table,
    _cached_worst_records_table,
    _cached_best_streaks,
    _cached_worst_streaks,
    _cached_score_count_records,
):
    deps.register_cache_clearer(_clear_fn.cache_clear)
del _clear_fn


def _records_held(name: str) -> list[dict]:
    """All-time TEG records (bests) this player holds.

    Delegates to the same formatters that power the /records page:
    prepare_records_table (Gross/Net/Stableford at TEG/round/9-hole),
    prepare_record_best_streaks_data (Birdies, Pars or Better streaks),
    prepare_score_count_records_table (Most Birdies in a Round).
    """
    pl_code = get_name_to_code().get(name, "")
    records: list[dict] = []

    # Performance records — TEG / round / 9-hole
    _LEVEL_SHORT = {"TEG": "TEG", "round": "round", "9 holes": "9"}
    _MEASURE_LOWER = {"Gross": "gross", "Net": "net", "Stableford": "Stableford"}

    def perf_label(formatter_label: str, level: str) -> str:
        parts = formatter_label.split()
        if len(parts) == 2:
            action, measure = parts
            return f"{action} {_MEASURE_LOWER.get(measure, measure.lower())} {_LEVEL_SHORT[level]}"
        return f"{formatter_label} {_LEVEL_SHORT[level]}"

    seen: set[str] = set()
    for df, level in [
        (_cached_records_table('teg'), 'TEG'),
        (_cached_records_table('round'), 'round'),
        (_cached_records_table('frontback'), '9 holes'),
    ]:
        for _, row in df.iterrows():
            raw_label = str(row.iloc[0])
            if 'Score' in raw_label:
                continue
            if str(row.iloc[2]).strip() != name:
                continue
            key = perf_label(raw_label, level)
            if key in seen:
                continue
            seen.add(key)
            shared = (df.iloc[:, 0] == raw_label).sum() > 1
            records.append({
                "label": key,
                "value": str(row.iloc[1]),
                "detail": str(row.iloc[3]),
                "shared": shared,
            })

    # Best streaks — Birdies and Pars or Better only
    BEST_STREAK_LABELS = {
        "Birdies": "Longest birdies streak",
        "Pars or Better": "Longest pars or better streak",
    }
    best_streaks = _cached_best_streaks()
    for _, row in best_streaks.iterrows():
        streak_type = str(row['Streak Type'])
        if streak_type not in BEST_STREAK_LABELS:
            continue
        if str(row['Player']) != name:
            continue
        shared = (best_streaks['Streak Type'] == streak_type).sum() > 1
        records.append({
            "label": BEST_STREAK_LABELS[streak_type],
            "value": f"{row['Record']} holes",
            "detail": str(row['When']),
            "shared": shared,
        })

    # Most birdies in a round
    best_sc, _ = _cached_score_count_records()
    for _, row in best_sc.iterrows():
        if str(row.iloc[0]) != 'Most Birdies in a Round':
            continue
        player_col = str(row.iloc[2]).strip()
        detail_col = str(row.iloc[3]).strip()
        if player_col == pl_code:
            records.append({"label": "Most birdies in a round", "value": str(row.iloc[1]),
                            "detail": detail_col, "shared": False})
            break
        if player_col == '→' and pl_code in [c.strip() for c in detail_col.split('/')]:
            records.append({"label": "Most birdies in a round", "value": str(row.iloc[1]),
                            "detail": "", "shared": True})
            break

    return records


def _worsts_held(name: str) -> list[dict]:
    """All-time TEG worst records this player holds.

    Delegates to the same formatters that power the /records page:
    prepare_worst_records_table (Gross/Net/Stableford at TEG/round/9-hole),
    prepare_record_worst_streaks_data (No Birdies, Over Par, TBPs streaks),
    prepare_score_count_records_table (Most TBPs in a Round).
    """
    pl_code = get_name_to_code().get(name, "")
    worsts: list[dict] = []

    # Performance worsts — TEG / round / 9-hole
    _LEVEL_SHORT = {"TEG": "TEG", "round": "round", "9 holes": "9"}
    _MEASURE_LOWER = {"Gross": "gross", "Net": "net", "Stableford": "Stableford"}

    def perf_label(formatter_label: str, level: str) -> str:
        parts = formatter_label.split()
        if len(parts) == 2:
            action, measure = parts
            return f"{action} {_MEASURE_LOWER.get(measure, measure.lower())} {_LEVEL_SHORT[level]}"
        return f"{formatter_label} {_LEVEL_SHORT[level]}"

    seen: set[str] = set()
    for df, level in [
        (_cached_worst_records_table('teg'), 'TEG'),
        (_cached_worst_records_table('round'), 'round'),
        (_cached_worst_records_table('frontback'), '9 holes'),
    ]:
        for _, row in df.iterrows():
            raw_label = str(row.iloc[0])
            if 'Score' in raw_label:
                continue
            if str(row.iloc[2]).strip() != name:
                continue
            key = perf_label(raw_label, level)
            if key in seen:
                continue
            seen.add(key)
            shared = (df.iloc[:, 0] == raw_label).sum() > 1
            worsts.append({
                "label": key,
                "value": str(row.iloc[1]),
                "detail": str(row.iloc[3]),
                "shared": shared,
            })

    # Worst streaks — No Birdies, Over Par and TBPs only
    WORST_STREAK_LABELS = {
        "No Birdies": "Longest no-birdies streak",
        "Over Par": "Longest over par streak",
        "TBPs": "Longest TBPs streak",
    }
    worst_streaks = _cached_worst_streaks()
    for _, row in worst_streaks.iterrows():
        streak_type = str(row['Streak Type'])
        if streak_type not in WORST_STREAK_LABELS:
            continue
        if str(row['Player']) != name:
            continue
        shared = (worst_streaks['Streak Type'] == streak_type).sum() > 1
        worsts.append({
            "label": WORST_STREAK_LABELS[streak_type],
            "value": f"{row['Record']} holes",
            "detail": str(row['When']),
            "shared": shared,
        })

    # Most TBPs in a round
    _, worst_sc = _cached_score_count_records()
    for _, row in worst_sc.iterrows():
        if str(row.iloc[0]) != 'Most TBPs in a Round':
            continue
        player_col = str(row.iloc[2]).strip()
        detail_col = str(row.iloc[3]).strip()
        if player_col == pl_code:
            worsts.append({
                "label": "Most TBPs in a round",
                "value": str(row.iloc[1]),
                "detail": detail_col,
                "shared": False,
            })
            break
        if player_col == '→' and pl_code in [c.strip() for c in detail_col.split('/')]:
            worsts.append({
                "label": "Most TBPs in a round",
                "value": str(row.iloc[1]),
                "detail": "",
                "shared": True,
            })
            break

    return worsts



# ---------------------------------------------------------------------------
# Table HTML builders
# ---------------------------------------------------------------------------

_NUMERIC_COLS = {
    'Score', 'Gross', 'GrossVP', 'Gross VP', 'NetVP', 'Net VP', 'Stableford',
    'Pts', 'Points', 'Total', 'Avg', 'Average', 'Count',
    'Gross Rank', 'Net Rank', 'Trophy Rank', 'Round Rank', 'Wins', 'Losses', 'Draws',
    'Avg Diff', 'Streak', 'Value', '%', 'Career Best', 'Current',
}
_RANK_COLS = {'#', 'Rank', 'Gross Rank', 'Net Rank', 'Trophy Rank', 'Round Rank'}


def _col_class(_i: int, col: str) -> str:
    return 'col-rank' if col in _RANK_COLS else ('col-num' if col in _NUMERIC_COLS else 'col-player')


def _build_simple_table_html(df, highlight_col=None, highlight_val=None):
    """Build a simple HTML table from a DataFrame with escaped values."""
    return _table_df_to_html(
        df, col_class=_col_class,
        highlight_col=highlight_col, highlight_val=highlight_val,
    )


# ---------------------------------------------------------------------------
# Per-TEG gross/net rank computation
# ---------------------------------------------------------------------------

def _compute_teg_ranks(teg_num: int, rd_data: pd.DataFrame) -> dict[str, dict]:
    """Compute per-player gross and net finishing positions for a single TEG.

    Returns dict keyed by player name: {"gross_rank": "1st", "net_rank": "2nd"}.
    """
    teg_rd = rd_data[rd_data['TEGNum'] == teg_num]
    if teg_rd.empty:
        return {}

    net_measure = get_net_competition_measure(teg_num)
    result = {}

    # Gross ranks
    gross_totals = teg_rd.groupby('Player')['GrossVP'].sum().sort_values()
    gross_totals_rank = gross_totals.rank(method='min').astype(int)

    # Net ranks
    net_ascending = net_measure == 'NetVP'
    net_totals = teg_rd.groupby('Player')[net_measure].sum().sort_values(ascending=net_ascending)
    net_totals_rank = net_totals.rank(method='min', ascending=net_ascending).astype(int)

    for player_name in gross_totals.index:
        g_rank = int(gross_totals_rank[player_name])
        n_rank = int(net_totals_rank[player_name]) if player_name in net_totals_rank.index else None
        result[player_name] = {
            "gross_rank": _ordinal(g_rank),
            "net_rank": _ordinal(n_rank) if n_rank else "–",
        }

    return result


# ---------------------------------------------------------------------------
# Tab: Overview
# ---------------------------------------------------------------------------

# Domain note (verified against the data): the **TEG Trophy** is won on the NET
# competition (Stableford from TEG 8, NetVP before) and the **Green Jacket** on
# the GROSS competition. So the net finishing position is the "Trophy Rank" and
# the gross position is effectively the jacket rank.

def _strip_star(value) -> str:
    """Winner name without the trailing '*' that marks an asterisked result."""
    return str(value).strip().rstrip("*").strip()


def _teg_result_flags(winners: pd.DataFrame, name: str, teg_num: int) -> dict:
    """Return {trophy, jacket, spoon} booleans for ``name`` in a given TEG.

    Winner names can carry a trailing '*' (an asterisked result, for example a
    Green Jacket decided off the course); it is stripped before comparing, so
    the asterisked winner still counts as the winner.
    """
    tw = winners[winners['TEG'] == f"TEG {teg_num}"]
    if tw.empty:
        return {"trophy": False, "jacket": False, "spoon": False}
    w = tw.iloc[0]
    return {
        "trophy": _strip_star(w['TEG Trophy']) == name,
        "jacket": _strip_star(w['Green Jacket']) == name,
        "spoon": _strip_star(w['HMM Wooden Spoon']) == name,
    }


def _result_label(flags: dict) -> str:
    """Collapse win flags to a single result label for the career table."""
    if flags["spoon"]:
        return "Wooden Spoon"
    if flags["trophy"] and flags["jacket"]:
        return "Double"
    if flags["trophy"]:
        return "TEG Trophy"
    if flags["jacket"]:
        return "Green Jacket"
    return ""


_NUMBER_WORDS = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six"}


def _round_counts(rd_data: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """Rounds played per (TEG, player), plus the usual TEG length.

    Returns (counts, usual) where ``counts`` has columns TEGNum, Player, n,
    teg_rounds (most rounds anyone played in that TEG) and full (the player
    played every round of a TEG that ran the usual number of rounds). The usual
    length is the most common TEG length, so a short early TEG never competes
    in TEG-level records.
    """
    counts = rd_data.groupby(["TEGNum", "Player"]).size().rename("n").reset_index()
    if counts.empty:
        return counts.assign(teg_rounds=0, full=False), 0
    counts["teg_rounds"] = counts.groupby("TEGNum")["n"].transform("max")
    usual = int(counts.groupby("TEGNum")["n"].max().mode().iloc[0])
    counts["full"] = (counts["n"] == counts["teg_rounds"]) & (counts["teg_rounds"] >= usual)
    return counts, usual


def _build_finish_rows(name: str, rd_data: pd.DataFrame, winners: pd.DataFrame,
                       player_teg: pd.DataFrame) -> tuple[list[dict], list[str]]:
    """One dict per TEG the player played (oldest first), plus footnotes.

    Gross position = Green Jacket competition, net position = TEG Trophy
    competition. An asterisked winner (winners table value ends '*') gets '*' on
    the winning position, and on anyone else who finished first on the course in
    that competition, with a footnote explaining it.
    """
    rows: list[dict] = []
    notes: list[str] = []
    if player_teg.empty:
        return rows, notes

    hc_by_teg = rd_data[rd_data["Player"] == name].groupby("TEGNum")["HC"].first()
    for _, r in player_teg.sort_values("TEGNum").iterrows():
        teg_num = int(r["TEGNum"])
        ranks = _compute_teg_ranks(teg_num, rd_data).get(name, {})
        gross_pos = ranks.get("gross_rank", "–")
        net_pos = ranks.get("net_rank", "–")
        flags = _teg_result_flags(winners, name, teg_num)

        tw = winners[winners["TEG"] == f"TEG {teg_num}"]
        for column, label, pos_key, win_key in (
            ("Green Jacket", "Green Jacket", "gross", "jacket"),
            ("TEG Trophy", "TEG Trophy", "net", "trophy"),
        ):
            raw = str(tw.iloc[0][column]) if not tw.empty else ""
            if not raw.endswith("*"):
                continue
            pos = gross_pos if pos_key == "gross" else net_pos
            if flags[win_key] or pos == "1st":
                if pos_key == "gross":
                    gross_pos = pos + "*"
                else:
                    net_pos = pos + "*"
                notes.append(
                    f"TEG {teg_num} {label} is an asterisked result" if flags[win_key]
                    else f"TEG {teg_num} {label} awarded to {_strip_star(raw)}")

        net_measure = get_net_competition_measure(teg_num)
        if net_measure == "Stableford":
            net_total = f"{format_value(r['Stableford'], 'Stableford')} pts"
        else:
            net_total = format_value(r["NetVP"], "NetVP")

        hc = hc_by_teg.get(teg_num)
        year = int(r["Year"]) if "Year" in r.index and pd.notna(r["Year"]) else None
        rows.append({
            "teg": teg_num,
            "year": year if year is not None else "",
            "yy": f"'{str(year)[2:]}" if year is not None else "",
            "hc": str(int(round(hc))) if hc is not None and pd.notna(hc) else "–",
            "gross_total": format_value(r["GrossVP"], "GrossVP"),
            "net_total": net_total,
            "gross_pos": gross_pos,
            "net_pos": net_pos,
            "jacket": flags["jacket"],
            "trophy": flags["trophy"],
            "spoon": flags["spoon"],
            "double": flags["jacket"] and flags["trophy"],
            "result": _result_label(flags),
        })
    return rows, notes


def _chart_scale_max(top: float) -> int:
    """Chart scale: next multiple of 5 above ``top`` plus about 10% headroom."""
    return max(5, int(math.ceil(max(top, 0) * 1.1 / 5.0)) * 5)


def _build_round_chart(name: str, rd_data: pd.DataFrame, rows: list[dict],
                       jackets: set[int]) -> dict | None:
    """Server-rendered 'Gross vs par per round' columns, oldest TEG first.

    Per TEG: the average gross vs par a round (bar), and the best and worst
    round (range line). Positions are percentages of one shared scale; values
    below zero are clamped to the baseline for drawing but kept in the text.
    """
    player_rd = rd_data[rd_data["Player"] == name]
    if player_rd.empty or not rows:
        return None
    grouped = player_rd.groupby("TEGNum")["GrossVP"].agg(["sum", "count", "min", "max"])
    career = float(player_rd["GrossVP"].mean())
    scale = _chart_scale_max(float(grouped["max"].max()))

    def pct(v: float) -> float:
        return round(min(max(v, 0.0), scale) / scale * 100, 2)

    def signed(v: float, digits: int = 0) -> str:
        return f"{v:+.{digits}f}"

    cols = []
    for row in rows:
        teg = row["teg"]
        if teg not in grouped.index:
            continue
        g = grouped.loc[teg]
        avg = float(g["sum"]) / float(g["count"])
        lo, hi = float(g["min"]), float(g["max"])
        cols.append({
            "teg": teg,
            "avg_label": signed(avg, 1),
            "bar": pct(avg), "lo": pct(lo), "hi": pct(hi), "span": round(pct(hi) - pct(lo), 2),
            "jacket": teg in jackets,
            "aria": (f"TEG {teg}: {signed(avg, 1)} a round, "
                     f"best {signed(lo)}, worst {signed(hi)}"),
        })
    ticks = [{"label": "0" if t == 0 else f"+{t}", "pos": round(t / scale * 100, 2)}
             for t in range(0, scale + 1, 10)]
    return {"cols": cols, "career_label": signed(career, 1), "career": pct(career),
            "career_frac": round(pct(career) / 100, 4), "ticks": ticks}


def _join_where(places: list[str]) -> str:
    """'A', 'A; B', 'A; B; and 1 more' for tied record locations."""
    if len(places) <= 2:
        return "; ".join(places)
    return f"{places[0]}; {places[1]}; and {len(places) - 2} more"


def _extreme_cell(player_df: pd.DataFrame, col: str, *, higher_is_better: bool, best: bool,
                  value_fn, where_fn, raw_fn) -> dict | None:
    """Best or worst row(s) for one player on ``col``.

    ``raw`` is the bare figure in the same format as ``_records_held`` values,
    used to match a cell against a held record.
    """
    if player_df.empty:
        return None
    target = player_df[col].max() if best == higher_is_better else player_df[col].min()
    hits = player_df[player_df[col] == target].sort_values(
        ["TEGNum", "Round"] if "Round" in player_df.columns else ["TEGNum"])
    first = hits.iloc[0]
    return {
        "value": value_fn(first),
        "raw": raw_fn(first),
        "where": _join_where([where_fn(h) for _, h in hits.iterrows()]),
        "tag": "",
    }


def _build_records_board(name: str, rd_data: pd.DataFrame) -> tuple[list[dict], set[str]]:
    """Rows for 'Records and personal bests', plus the held-record labels tagged.

    Values are the player's own bests/worsts (full-length TEGs only; Stableford
    from the Stableford era). A cell is tagged "TEG record" / "TEG worst" only
    when ``_records_held`` / ``_worsts_held`` (the canonical records) say the
    player holds that record with the same figure. Returns (rows, tagged labels).
    """
    ranked_teg = cached_ranked_teg_data()
    ranked_rd = cached_ranked_round_data()
    ranked_fb = cached_ranked_frontback_data()

    counts, _usual = _round_counts(rd_data)
    full = {(int(t), p) for t, p in counts.loc[counts["full"], ["TEGNum", "Player"]].itertuples(index=False)}
    teg_me = ranked_teg[(ranked_teg["Player"] == name)
                        & ranked_teg["TEGNum"].map(lambda t: (int(t), name) in full).astype(bool)]
    rd_me = ranked_rd[ranked_rd["Player"] == name]

    def yr(r):
        return f"{int(r['Year'])}" if pd.notna(r.get("Year")) else ""

    teg_where = lambda r: f"TEG {int(r['TEGNum'])}, {yr(r)}"
    rd_where = lambda r: f"TEG {int(r['TEGNum'])} R{int(r['Round'])}, {r['Course']}, {yr(r)}"
    vp = lambda r: format_value(r["GrossVP"], "GrossVP")
    pts = lambda r: f"{int(round(r['Stableford']))} pts"
    pts_raw = lambda r: str(int(round(r["Stableford"])))
    rd_gross = lambda r: f"{int(r['Sc'])} ({format_value(r['GrossVP'], 'GrossVP')})"

    # (row label, dataframe, column, higher is better, value, raw, where, held-label suffix, nine)
    specs = [
        ("TEG, gross", teg_me, "GrossVP", False, vp, vp, teg_where, "gross TEG", None),
        ("TEG, Stableford", teg_me, "Stableford", True, pts, pts_raw, teg_where, "Stableford TEG", None),
        ("Round, gross", rd_me, "GrossVP", False, rd_gross, vp, rd_where, "gross round", None),
        ("Round, Stableford", rd_me, "Stableford", True, pts, pts_raw, rd_where, "Stableford round", None),
    ]
    for nine, label in (("Front", "Front 9"), ("Back", "Back 9")):
        mine = ranked_fb[(ranked_fb["FrontBack"] == nine) & (ranked_fb["Player"] == name)]
        specs.append((label, mine, "GrossVP", False, vp, vp, rd_where, "gross 9", nine))

    held = {("Best", r["label"]): r for r in _records_held(name)}
    held.update({("Worst", r["label"]): r for r in _worsts_held(name)})
    tagged: set[str] = set()
    rows = []
    for label, df, col, higher, value_fn, raw_fn, where_fn, suffix, nine in specs:
        if col == "Stableford":
            # Net was vs par before the Stableford era, so earlier points are not comparable.
            df = df[df["TEGNum"] >= STABLEFORD_ERA_TEG]
        row = {"label": label}
        for key, best in (("best", True), ("worst", False)):
            cell = _extreme_cell(df, col, higher_is_better=higher, best=best,
                                 value_fn=value_fn, where_fn=where_fn, raw_fn=raw_fn)
            held_label = f"{'Best' if best else 'Worst'} {suffix}"
            rec = held.get(("Best" if best else "Worst", held_label))
            detail = str(rec.get("detail", "")) if rec else ""
            nine_ok = nine is None or not any(w in detail for w in (" Front", " Back")) or f" {nine}" in detail
            if cell and rec and str(rec["value"]) == cell["raw"] and nine_ok:
                cell["tag"] = ("TEG record" if best else "TEG worst") + (", shared" if rec.get("shared") else "")
                tagged.add(held_label if best else f"W:{held_label}")
            row[key] = cell
        rows.append(row)

    # Course average (needs two rounds on a course to mean anything).
    player_rd = rd_data[rd_data["Player"] == name]
    course_cell = {"best": None, "worst": None}
    if not player_rd.empty:
        by_course = player_rd.groupby("Course")["GrossVP"].agg(["mean", "count"])
        by_course = by_course[by_course["count"] >= 2]
        if not by_course.empty:
            for key, course in (("best", by_course["mean"].idxmin()), ("worst", by_course["mean"].idxmax())):
                course_cell[key] = {
                    "value": f"{by_course.loc[course, 'mean']:+.1f}",
                    "where": f"{course}, {int(by_course.loc[course, 'count'])} rounds",
                    "tag": "",
                }
    rows.append({"label": "Course, avg", **course_cell})
    return rows, tagged


def _records_note(name: str, tagged: set[str]) -> str:
    """One muted line on held records and worsts no board cell is tagged with."""
    def phrase(r):
        bits = [str(r["value"])]
        if r.get("detail"):
            bits.append(str(r["detail"]))
        return f"{r['label'][0].lower()}{r['label'][1:]} ({', '.join(bits)})"

    best_all = _records_held(name)
    worst_all = _worsts_held(name)
    best = [r for r in best_all if r["label"] not in tagged]
    worst = [r for r in worst_all if f"W:{r['label']}" not in tagged]
    parts = []
    own = [phrase(r) for r in best if not r.get("shared")]
    shared = [phrase(r) for r in best if r.get("shared")]
    if own:
        parts.append("Also holds the " + "; ".join(own) + ".")
    if shared:
        parts.append("Also shares the " + "; ".join(shared) + ".")
    if worst:
        parts.append("TEG worsts also held: " + "; ".join(phrase(r) for r in worst) + ".")
    if not worst_all:
        parts.append("No TEG worsts held.")
    return " ".join(parts)


def _star_line(trophies: int, jackets: int) -> dict:
    """Header star counts and an accessible label (empty label when none)."""
    bits = []
    if trophies:
        bits.append(f"{trophies} TEG Trophy" if trophies == 1 else f"{trophies} TEG Trophies")
    if jackets:
        bits.append(f"{jackets} Green Jacket" if jackets == 1 else f"{jackets} Green Jackets")
    return {"trophies": trophies, "jackets": jackets, "label": ", ".join(bits)}


def _honour_counts(name: str) -> dict:
    """Trophy and jacket counts for the header stars (asterisks stripped)."""
    winners = deps.cached_winners()
    trophies = int((winners["TEG Trophy"].map(_strip_star) == name).sum())
    jackets = int((winners["Green Jacket"].map(_strip_star) == name).sum())
    return _star_line(trophies, jackets)


def _build_overview_context(player_code: str) -> dict:
    """Build context for the overview tab."""
    name = get_player_dict()[player_code]

    ranked_teg = cached_ranked_teg_data()
    player_teg = ranked_teg[ranked_teg['Player'] == name].copy()
    all_data = cached_load_all_data()
    winners = deps.cached_winners()
    rd_data = cached_round_data()
    specs = _metric_specs(all_data, rd_data, winners)

    columns, n_ranked = _metric_columns(specs, name)
    finish_rows, finish_notes = _build_finish_rows(name, rd_data, winners, player_teg)
    jackets = {r["teg"] for r in finish_rows if r["jacket"]}
    records_board, tagged = _build_records_board(name, rd_data)

    return {
        "metric_columns": columns,
        "n_ranked": n_ranked,
        "finish_rows": finish_rows,
        "finish_notes": finish_notes,
        "stableford_era": STABLEFORD_ERA_TEG,
        "round_chart": _build_round_chart(name, rd_data, finish_rows, jackets),
        "records_board": records_board,
        "records_note": _records_note(name, tagged),
    }


# ---------------------------------------------------------------------------
# Tab: Career record
# ---------------------------------------------------------------------------

def _build_career_context(player_code: str) -> dict:
    """Build context for the career record tab: every TEG, newest first."""
    name = get_player_dict()[player_code]
    ranked_teg = cached_ranked_teg_data()
    player_teg = ranked_teg[ranked_teg['Player'] == name].copy()
    rd_data = cached_round_data()
    rows, notes = _build_finish_rows(name, rd_data, deps.cached_winners(), player_teg)

    counts, usual = _round_counts(rd_data)
    short = sorted({int(t) for t, n in counts.groupby("TEGNum")["teg_rounds"].first().items() if n < usual})
    mine = {r["teg"] for r in rows}
    short_notes = []
    for teg in short:
        if teg not in mine:
            continue
        n = int(counts.loc[counts["TEGNum"] == teg, "teg_rounds"].iloc[0])
        short_notes.append(f"TEG {teg} was {_NUMBER_WORDS.get(n, str(n))} rounds.")
    return {
        "career_rows": list(reversed(rows)),
        "career_notes": notes,
        "career_short_notes": short_notes,
        "stableford_era": STABLEFORD_ERA_TEG,
        "has_hc": any(r["hc"] != "–" for r in rows),
    }


# ---------------------------------------------------------------------------
# Tab: Rounds
# ---------------------------------------------------------------------------

def _build_rounds_chart(player_code: str) -> str | None:
    """Bar chart of gross vs par for every round, coloured by score and grouped
    by TEG (a small gap separates TEGs; rounds within a TEG sit flush)."""
    name = get_player_dict()[player_code]
    rd_data = cached_round_data()
    player_rd = rd_data[rd_data['Player'] == name].sort_values(['TEGNum', 'Round'])
    if player_rd.empty:
        return None

    xs, ys, customdata, teg_groups = [], [], [], []
    pos = 0
    prev_teg = None
    group_start = 0
    for _, r in player_rd.iterrows():
        teg = int(r['TEGNum'])
        if prev_teg is not None and teg != prev_teg:
            teg_groups.append(((group_start + pos - 1) / 2, prev_teg))
            pos += 1  # blank slot → visual gap between TEGs
            group_start = pos
        xs.append(pos)
        ys.append(float(r['GrossVP']))
        customdata.append([f"TEG {teg}", int(r['Round']), str(r.get('Course', ''))])
        prev_teg = teg
        pos += 1
    if prev_teg is not None:
        teg_groups.append(((group_start + pos - 1) / 2, prev_teg))

    fig = go.Figure(go.Bar(
        x=xs, y=ys, customdata=customdata,
        marker=dict(color=ys, colorscale='RdYlGn', reversescale=True, cmid=0,
                    line=dict(width=0)),
        hovertemplate=("%{customdata[0]} · R%{customdata[1]}<br>"
                       "%{customdata[2]}<br>Gross vs Par: %{y:+}<extra></extra>"),
    ))
    for cx, teg in teg_groups:
        fig.add_annotation(x=cx, y=0, yref='paper', yshift=-18,
                           text=str(teg), showarrow=False,
                           font=dict(size=9, color='gray'))
    fig.update_layout(
        yaxis_title="Gross vs Par",
        margin=dict(r=20, t=10, b=46, l=50),
        font=dict(family="monospace"),
        showlegend=False, bargap=0.0,
    )
    fig.add_annotation(x=0, y=0, yref='paper', xref='paper', yshift=-32,
                       text="TEG", showarrow=False, xanchor='right',
                       font=dict(size=9, color='gray'))
    fig.update_xaxes(showticklabels=False, fixedrange=True)
    fig.update_yaxes(fixedrange=True)
    fig.update_layout(**get_chart_style('streamlit'))
    return fig.to_json()


def _build_rounds_context(player_code: str) -> dict:
    """Build context for the rounds tab."""
    name = get_player_dict()[player_code]

    chart_json = _build_rounds_chart(player_code)

    ranked_rd = cached_ranked_round_data()
    player_rd = ranked_rd[ranked_rd['Player'] == name].copy()

    if player_rd.empty:
        return {"rounds_table_html": "<p class='text-muted text-sm'>No round data.</p>",
                "rounds_chart_json": chart_json}

    # Find PB values for highlighting
    best_gross = player_rd['GrossVP'].min()
    best_stab = player_rd['Stableford'].max()

    rows = []
    for _, r in player_rd.sort_values(['TEGNum', 'Round'], ascending=[False, True]).iterrows():
        gross_vp = format_value(r['GrossVP'], 'GrossVP')
        stab = format_value(r['Stableford'], 'Stableford')
        is_pb_gross = (r['GrossVP'] == best_gross)
        is_pb_stab = (r['Stableford'] == best_stab)

        course = r.get('Course', '') if 'Course' in r.index else ''

        rows.append({
            'TEG': int(r['TEGNum']),
            'Rd': int(r['Round']),
            'Course': course,
            'Score': int(r['Sc']),
            'Gross VP': gross_vp + (' *' if is_pb_gross else ''),
            'Stableford': stab + (' *' if is_pb_stab else ''),
        })

    rd_df = pd.DataFrame(rows)
    return {"rounds_table_html": _build_simple_table_html(rd_df),
            "rounds_chart_json": chart_json}


# ---------------------------------------------------------------------------
# Tab: Scoring
# ---------------------------------------------------------------------------

def _build_scoring_context(player_code: str) -> dict:
    """Build context for the scoring tab."""
    name = get_player_dict()[player_code]
    all_data = cached_load_all_data()
    player_data = all_data[all_data['Player'] == name]

    sections = []

    # Par performance
    if not player_data.empty:
        matrix = calculate_par_performance_matrix(player_data)
        formatted = format_par_performance_table(matrix.copy())
        sections.append({
            "title": "Average Score by Par",
            "table_html": _build_simple_table_html(formatted),
        })

    # Score distribution
    if not player_data.empty:
        grossvp_counts = player_data['GrossVP'].value_counts().sort_index()

        score_labels = {
            -3: 'Albatross', -2: 'Eagle', -1: 'Birdie', 0: 'Par',
            1: 'Bogey', 2: 'Double', 3: 'Triple', 4: '+4', 5: '+5',
        }

        dist_rows = []
        total = len(player_data)
        for val in sorted(grossvp_counts.index):
            count = grossvp_counts[val]
            label = score_labels.get(int(val), format_vs_par(val))
            pct = (count / total * 100) if total > 0 else 0
            dist_rows.append({
                'Score': label,
                'Count': int(count),
                '%': f"{pct:.1f}%",
            })

        dist_df = pd.DataFrame(dist_rows)
        sections.append({
            "title": "Score Distribution",
            "table_html": _build_simple_table_html(dist_df),
        })

        # Score distribution chart
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=[r['Score'] for r in dist_rows],
            y=[int(r['Count']) for r in dist_rows],
        ))
        fig.update_layout(
            xaxis_title="Score vs Par",
            yaxis_title="Count",
            margin=dict(r=20, t=10, b=40, l=50),
            font=dict(family="monospace"),
        )
        fig.layout.xaxis.fixedrange = True
        fig.layout.yaxis.fixedrange = True

        fig.update_layout(**get_chart_style('streamlit'))
        sections.append({
            "title": "Score Distribution Chart",
            "chart_json": fig.to_json(),
        })

    return {"sections": sections}


# ---------------------------------------------------------------------------
# Tab: Records & Streaks
# ---------------------------------------------------------------------------

def _build_records_context(player_code: str) -> dict:
    """Build context for the records & streaks tab."""
    name = get_player_dict()[player_code]
    sections = []

    # Personal bests — TEG level
    ranked_teg = cached_ranked_teg_data()
    player_teg = ranked_teg[ranked_teg['Player'] == name]

    if not player_teg.empty:
        pb_rows = []
        best_gross_idx = player_teg['GrossVP'].idxmin()
        best_gross = player_teg.loc[best_gross_idx]
        pb_rows.append({
            'Record': 'Best TEG (Gross)',
            'Value': format_value(best_gross['GrossVP'], 'GrossVP'),
            'TEG': f"TEG {int(best_gross['TEGNum'])}",
        })
        best_stab_idx = player_teg['Stableford'].idxmax()
        best_stab = player_teg.loc[best_stab_idx]
        pb_rows.append({
            'Record': 'Best TEG (Stableford)',
            'Value': format_value(best_stab['Stableford'], 'Stableford'),
            'TEG': f"TEG {int(best_stab['TEGNum'])}",
        })
        sections.append({
            "title": "Personal Bests — TEG",
            "table_html": _build_simple_table_html(pd.DataFrame(pb_rows)),
        })

    # Personal bests — Round level
    ranked_rd = cached_ranked_round_data()
    player_rd = ranked_rd[ranked_rd['Player'] == name]

    if not player_rd.empty:
        rd_pb_rows = []
        best_rd_gross_idx = player_rd['GrossVP'].idxmin()
        best_rd_gross = player_rd.loc[best_rd_gross_idx]
        rd_pb_rows.append({
            'Record': 'Best Round (Gross)',
            'Value': format_value(best_rd_gross['GrossVP'], 'GrossVP'),
            'TEG': f"TEG {int(best_rd_gross['TEGNum'])} R{int(best_rd_gross['Round'])}",
        })
        best_rd_stab_idx = player_rd['Stableford'].idxmax()
        best_rd_stab = player_rd.loc[best_rd_stab_idx]
        rd_pb_rows.append({
            'Record': 'Best Round (Stableford)',
            'Value': format_value(best_rd_stab['Stableford'], 'Stableford'),
            'TEG': f"TEG {int(best_rd_stab['TEGNum'])} R{int(best_rd_stab['Round'])}",
        })
        sections.append({
            "title": "Personal Bests — Round",
            "table_html": _build_simple_table_html(pd.DataFrame(rd_pb_rows)),
        })

    # Personal worsts — TEG level
    if not player_teg.empty:
        pw_rows = []
        worst_gross_idx = player_teg['GrossVP'].idxmax()
        worst_gross = player_teg.loc[worst_gross_idx]
        pw_rows.append({
            'Record': 'Worst TEG (Gross)',
            'Value': format_value(worst_gross['GrossVP'], 'GrossVP'),
            'TEG': f"TEG {int(worst_gross['TEGNum'])}",
        })
        worst_stab_idx = player_teg['Stableford'].idxmin()
        worst_stab = player_teg.loc[worst_stab_idx]
        pw_rows.append({
            'Record': 'Worst TEG (Stableford)',
            'Value': format_value(worst_stab['Stableford'], 'Stableford'),
            'TEG': f"TEG {int(worst_stab['TEGNum'])}",
        })
        sections.append({
            "title": "Personal Worsts — TEG",
            "table_html": _build_simple_table_html(pd.DataFrame(pw_rows)),
        })

    # Streaks
    try:
        streaks_df = deps.cached_streaks_data()
        player_streaks = streaks_df[streaks_df['Pl'] == player_code]

        if not player_streaks.empty:
            max_s = get_max_streaks(player_streaks)
            current_s = get_current_streaks(player_streaks)

            good_mapping = STREAK_CONFIGS['good']['column_mapping']
            bad_mapping = STREAK_CONFIGS['bad']['column_mapping']

            streak_rows = []
            for label, col in {**good_mapping, **bad_mapping}.items():
                max_val = int(max_s[col].iloc[0]) if col in max_s.columns else 0
                cur_val = int(current_s[col].iloc[0]) if col in current_s.columns else 0
                streak_rows.append({
                    'Streak': label,
                    'Career Best': max_val,
                    'Current': cur_val,
                })

            sections.append({
                "title": "Streaks",
                "table_html": _build_simple_table_html(pd.DataFrame(streak_rows)),
            })
    except (KeyError, ValueError) as exc:
        logger.warning("Could not build streaks for %s: %s", player_code, exc)

    return {
        "sections": sections,
        "records_held": _records_held(name),
        "worsts_held": _worsts_held(name),
    }


def _current_playing_handicaps() -> dict:
    """Use the same next/in-progress TEG handicap on roster and detail pages."""
    try:
        _, next_tegnum, _ = get_next_teg_and_check_if_in_progress_fast()
        hc_df, _ = get_current_handicaps_formatted(next_tegnum - 1, next_tegnum)
        hc_col = f"TEG {next_tegnum}"
        return dict(zip(hc_df["Handicap"], hc_df[hc_col].astype(int)))
    except Exception:
        logger.exception("Could not load current handicaps for player profiles")
        return {}


# ---------------------------------------------------------------------------
# Roster (landing page cards)
# ---------------------------------------------------------------------------

def _build_roster() -> list[dict]:
    """Build roster card data for every player, ordered by honours then name.

    Each card carries identity (code/name/initials), a one-line career summary
    and three headline stats, plus trophy/jacket/spoon badges.
    """
    all_data = cached_load_all_data()
    rd_data = cached_round_data()
    winners = deps.cached_winners()

    # Current playing handicap = each player's HC for the next (or in-progress)
    # TEG. Map name → HC; players absent from the table just show "–".
    current_hc = _current_playing_handicaps()

    cards = []
    for code, name in get_player_dict().items():
        player_data = all_data[all_data['Player'] == name]
        if player_data.empty:
            continue

        teg_info = player_data[['TEGNum', 'Year']].drop_duplicates().sort_values('TEGNum')
        n_tegs = len(teg_info)
        since_year = int(teg_info.iloc[0]['Year'])

        player_rds = rd_data[rd_data['Player'] == name]
        avg_gvp = player_rds['GrossVP'].mean() if not player_rds.empty else None
        avg_stab = player_rds['Stableford'].mean() if not player_rds.empty else None

        trophy_count = int((winners['TEG Trophy'] == name).sum())
        jacket_count = int((winners['Green Jacket'] == name).sum())
        spoon_count = int((winners['HMM Wooden Spoon'] == name).sum())
        total_trophies = trophy_count + jacket_count

        badges = []
        if trophy_count:
            badges.append({"text": f"Trophy ×{trophy_count}", "style": "accent"})
        if jacket_count:
            badges.append({"text": f"Jacket ×{jacket_count}", "style": "accent"})
        if spoon_count:
            badges.append({"text": f"Spoon ×{spoon_count}", "style": "muted"})

        cards.append({
            "code": code,
            "name": name,
            "n_tegs": n_tegs,
            "since_year": since_year,
            "avg_gvp": f"{avg_gvp:+.1f}" if avg_gvp is not None else "–",
            "avg_stab": f"{avg_stab:.1f}" if avg_stab is not None else "–",
            "handicap": current_hc.get(name),
            "total_trophies": total_trophies,
            "trophy_count": trophy_count,
            "jacket_count": jacket_count,
            "badges": badges,
        })

    cards.sort(key=lambda c: (-c["total_trophies"], -c["n_tegs"], c["name"]))
    return cards


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("/player")
def player_index(request: Request):
    return templates.TemplateResponse("player_index.html", {
        "request": request,
        "active_page": "player",
        "player_list": _get_player_list(),
        "roster": _build_roster(),
    })


def _player_tab_payload(player_code: str, tab_name: str):
    if tab_name == "overview":
        return _build_overview_context(player_code), "partials/player_overview.html"
    if tab_name == "career":
        return _build_career_context(player_code), "partials/player_career.html"
    if tab_name == "rounds":
        return _build_rounds_context(player_code), "partials/player_rounds.html"
    if tab_name == "scoring":
        return _build_scoring_context(player_code), "partials/player_scoring.html"
    if tab_name == "records":
        return _build_records_context(player_code), "partials/player_records.html"
    return _build_overview_context(player_code), "partials/player_overview.html"


@router.get("/player/{player_code}")
def player_page(request: Request, player_code: str, tab: str = Query("overview")):
    pc = _validate_player(player_code)
    name = get_player_dict()[pc]
    valid_tabs = {tab_id for tab_id, _ in PLAYER_TABS}
    active_tab = tab if tab in valid_tabs else "overview"

    tab_ctx, tab_template = _player_tab_payload(pc, active_tab)

    return templates.TemplateResponse("player.html", {
        "request": request,
        "active_page": "player",
        "player_code": pc,
        "player_name": name,
        "player_list": _get_player_list(),
        "stars": _honour_counts(name),
        "tabs": PLAYER_TABS,
        "active_tab": active_tab,
        "tab_template": tab_template,
        **tab_ctx,
    })


@router.get("/player/{player_code}/tab/{tab_name}")
def player_tab(request: Request, player_code: str, tab_name: str):
    pc = _validate_player(player_code)

    valid_tabs = {tab_id for tab_id, _ in PLAYER_TABS}
    if tab_name not in valid_tabs:
        raise HTTPException(status_code=404, detail=f"Unknown tab: {tab_name}")
    ctx, template = _player_tab_payload(pc, tab_name)

    return templates.TemplateResponse(template, {
        "request": request,
        "player_code": pc,
        **ctx,
    })
