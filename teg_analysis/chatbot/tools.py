"""Deterministic tools TEGBot calls. The model picks a tool; this code does the maths.

Every tool returns a plain JSON-able dict with:

- the numbers (never computed by the model),
- ``definition`` / ``assumptions`` where a choice was made, so the answer can
  state them,
- ``page`` — the site page that already shows this data, when one exists.

Bad input never raises out of ``run_tool``: it comes back as ``{"error": ...}``
so the model can correct itself and retry.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Optional

import pandas as pd

from teg_analysis.analysis.bounceback import (
    BASIS_COLUMNS, GROUPINGS, TRIGGER_THRESHOLDS, bounce_back_stats,
)

MAX_ROWS = 40


# ---------------------------------------------------------------------------
# Data access
# ---------------------------------------------------------------------------
def _default_all_data() -> pd.DataFrame:
    from teg_analysis.core.data_loader import load_all_data
    return load_all_data(exclude_teg_50=True, exclude_incomplete_tegs=False)


def _default_winners(all_data: pd.DataFrame) -> pd.DataFrame:
    from teg_analysis.analysis.history import get_teg_winners
    return get_teg_winners(all_data)


def _default_completed() -> set[int]:
    from teg_analysis.io.file_operations import read_file
    return set(read_file("data/completed_tegs.csv")["TEGNum"].astype(int))


def _default_players() -> dict[str, str]:
    from teg_analysis.core.players import get_player_dict
    return get_player_dict()


@dataclass
class ChatData:
    """Lazy data handles. The webapp passes its process-wide cached accessors."""

    all_data: Callable[[], pd.DataFrame] = _default_all_data
    winners: Optional[Callable[[], pd.DataFrame]] = None
    completed_tegs: Callable[[], set[int]] = _default_completed
    players: Callable[[], dict[str, str]] = _default_players
    _memo: dict = field(default_factory=dict, repr=False)

    def _get(self, key: str, fn: Callable[[], Any]) -> Any:
        if key not in self._memo:
            self._memo[key] = fn()
        return self._memo[key]

    def holes(self) -> pd.DataFrame:
        return self._get("holes", self.all_data)

    def winners_df(self) -> pd.DataFrame:
        if self.winners is not None:
            return self._get("winners", self.winners)
        return self._get("winners", lambda: _default_winners(self.holes()))

    def complete(self) -> set[int]:
        return self._get("complete", lambda: {int(t) for t in self.completed_tegs()})

    def rounds(self) -> pd.DataFrame:
        return self._get("rounds", self._build_rounds)

    def tegs(self) -> pd.DataFrame:
        return self._get("tegs", self._build_tegs)

    def _build_rounds(self) -> pd.DataFrame:
        keys = ["Player", "Pl", "TEGNum", "Year", "Round", "Course"]
        if "Area" in self.holes().columns:
            keys.append("Area")
        df = self.holes().groupby(keys, as_index=False).agg(
            Sc=("Sc", "sum"), GrossVP=("GrossVP", "sum"), NetVP=("NetVP", "sum"),
            Stableford=("Stableford", "sum"), HC=("HC", "first"), Holes=("Hole", "size"),
        )
        return df.sort_values(["TEGNum", "Round", "Player"]).reset_index(drop=True)

    def _build_tegs(self) -> pd.DataFrame:
        from teg_analysis.analysis.scoring import get_net_competition_measure
        keys = ["Player", "Pl", "TEGNum", "Year"]
        if "Area" in self.holes().columns:
            keys.append("Area")
        df = self.holes().groupby(keys, as_index=False).agg(
            Sc=("Sc", "sum"), GrossVP=("GrossVP", "sum"), NetVP=("NetVP", "sum"),
            Stableford=("Stableford", "sum"), HC=("HC", "first"),
            Rounds=("Round", "nunique"), Holes=("Hole", "size"),
        )
        df["Complete"] = df["TEGNum"].isin(self.complete())
        df["JacketPosition"] = df.groupby("TEGNum")["GrossVP"].rank(method="min").astype(int)
        net_pos = []
        for teg_num, grp in df.groupby("TEGNum"):
            if get_net_competition_measure(int(teg_num)) == "NetVP":
                net_pos.append(grp["NetVP"].rank(method="min"))
            else:
                net_pos.append(grp["Stableford"].rank(method="min", ascending=False))
        df["TrophyPosition"] = pd.concat(net_pos).astype(int)
        df["FieldSize"] = df.groupby("TEGNum")["Player"].transform("size")
        return df.sort_values(["TEGNum", "TrophyPosition"]).reset_index(drop=True)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
class ToolInputError(ValueError):
    """Bad tool input — reported back to the model, never to the user as a crash."""


def resolve_player(value: str, players: dict[str, str]) -> str:
    """Code, full name, or a unique first/last name → full name ("Jon BAKER")."""
    text = str(value).strip()
    if not text:
        raise ToolInputError("Empty player name.")
    if text.upper() in players:
        return players[text.upper()]
    names = list(players.values())
    for name in names:
        if name.lower() == text.lower():
            return name
    matches = [n for n in names if text.lower() in [p.lower() for p in n.split()]]
    if len(matches) == 1:
        return matches[0]
    if not matches:
        matches = [n for n in names if text.lower() in n.lower()]
        if len(matches) == 1:
            return matches[0]
    if matches:
        raise ToolInputError(f"'{text}' is ambiguous: {', '.join(matches)}.")
    raise ToolInputError(f"No player called '{text}'. Players: {', '.join(names)}.")


def _records(df: pd.DataFrame, limit: int = MAX_ROWS) -> tuple[list[dict], bool]:
    out = df.head(limit).copy()
    for col in out.columns:
        if pd.api.types.is_float_dtype(out[col]):
            out[col] = out[col].round(2)
            if (out[col].dropna() % 1 == 0).all():
                out[col] = out[col].astype("Int64")
    rows = [
        {k: (None if pd.isna(v) else (v.item() if hasattr(v, "item") else v)) for k, v in r.items()}
        for r in out.to_dict(orient="records")
    ]
    return rows, len(df) > limit


# ---------------------------------------------------------------------------
# Tool: honours
# ---------------------------------------------------------------------------
COMPETITIONS = {
    "trophy": ("TEG Trophy", "/honours?tab=trophy"),
    "jacket": ("Green Jacket", "/honours?tab=jacket"),
    "spoon": ("HMM Wooden Spoon", "/honours?tab=spoon"),
}


def get_honours(data: ChatData, competition: str = "all") -> dict:
    comps = list(COMPETITIONS) if competition == "all" else [competition]
    if any(c not in COMPETITIONS for c in comps):
        raise ToolInputError(f"competition must be one of {['all', *COMPETITIONS]}")
    winners = data.winners_df()
    complete = data.complete()
    winners = winners[winners["TEG"].map(lambda t: int(str(t).split()[-1]) in complete)]
    result: dict[str, Any] = {"winners_by_teg": _records(winners)[0], "counts": {}}
    for comp in comps:
        col, _ = COMPETITIONS[comp]
        # "Stuart NEUMANN*" marks the TEG 5 jacket footnote; count it as his win.
        counts = winners[col].astype(str).str.rstrip("*").value_counts()
        result["counts"][col] = {k: int(v) for k, v in counts.items()}
    if competition == "all":
        both = result["counts"]["TEG Trophy"], result["counts"]["Green Jacket"]
        result["counts"]["Trophy + Jacket combined"] = dict(sorted(
            {p: both[0].get(p, 0) + both[1].get(p, 0) for p in {*both[0], *both[1]}}.items(),
            key=lambda kv: -kv[1]))
    result["page"] = COMPETITIONS[comps[0]][1] if len(comps) == 1 else "/honours"
    result["notes"] = [
        "Only completed TEGs are counted.",
        "TEG Trophy = net competition (net vs par up to TEG 7, Stableford points from TEG 8).",
        "Green Jacket = best gross. Wooden Spoon = last in the net competition.",
        "TEG 5 Green Jacket was awarded for best Stableford round; David MULLIN had the best gross score.",
    ]
    return result


# ---------------------------------------------------------------------------
# Tool: streaks
# ---------------------------------------------------------------------------
def get_streak_records(data: ChatData, direction: str = "good") -> dict:
    from teg_analysis.analysis.streaks import prepare_record_streaks_data, prepare_streaks_data
    if direction not in ("good", "bad"):
        raise ToolInputError("direction must be 'good' or 'bad'")
    holes = data.holes()
    return {
        "direction": direction,
        "longest_streak_per_player": _records(prepare_streaks_data(holes, direction))[0],
        "all_time_records": _records(prepare_record_streaks_data(holes, direction))[0],
        "definition": (
            "Streaks run across consecutive holes played, including across rounds and TEGs. "
            "Good: consecutive birdies, pars or better, holes without a double bogey or worse (+2s), "
            "holes without a triple bogey or worse (TBPs). "
            "Bad: holes without eagles/birdies, consecutive holes over par, +2s, TBPs."
        ),
        "page": "/scoring/streaks",
    }


# ---------------------------------------------------------------------------
# Tool: bounce-back
# ---------------------------------------------------------------------------
def get_bounce_back(data: ChatData, basis: str = "gross", trigger: str = "bogey_or_worse",
                    group_by: str = "player", player: Optional[str] = None,
                    teg: Optional[int] = None) -> dict:
    holes = data.holes()
    if teg is not None:
        holes = holes[holes["TEGNum"] == int(teg)]
        if holes.empty:
            raise ToolInputError(f"No data for TEG {teg}.")
    try:
        df = bounce_back_stats(holes, basis=basis, trigger=trigger, group_by=group_by)
    except ValueError as exc:
        raise ToolInputError(str(exc)) from exc
    if player:
        df = df[df["Player"] == resolve_player(player, data.players())]
    rows, truncated = _records(df)
    trig_text = "bogey or worse" if trigger == "bogey_or_worse" else "double bogey or worse"
    return {
        "result": rows,
        "truncated": truncated,
        "definition": (
            f"Trigger: a hole at {trig_text} ({basis} vs par). Bounce-back: the next hole in the "
            f"same round at par or better ({basis}). Rate = bounce-backs / triggers, as a %. "
            "Baseline = the player's par-or-better rate on all holes 2-18, for comparison; "
            "Difference = rate minus baseline in percentage points."
        ),
        "assumptions": [
            "Hole 18 is never a trigger, because the next hole is in a different round.",
            "Holes are taken in numbered order (1-18) within a round.",
            "Includes any TEG currently in progress.",
            "Small samples (under ~50 triggers) are noisy.",
        ],
        "page": None,
    }


# ---------------------------------------------------------------------------
# Tool: query_scores — a constrained, validated query language
# ---------------------------------------------------------------------------
DIMENSIONS = {
    "hole": ["Player", "Pl", "TEGNum", "Year", "Round", "Hole", "PAR", "SI", "Course", "Area", "FrontBack"],
    "round": ["Player", "Pl", "TEGNum", "Year", "Round", "Course", "Area"],
    "teg": ["Player", "Pl", "TEGNum", "Year", "Area", "Complete"],
}
MEASURES = {
    "hole": ["Sc", "GrossVP", "NetVP", "Stableford", "HC", "HCStrokes"],
    "round": ["Sc", "GrossVP", "NetVP", "Stableford", "HC", "Holes"],
    "teg": ["Sc", "GrossVP", "NetVP", "Stableford", "HC", "Rounds", "Holes",
            "TrophyPosition", "JacketPosition", "FieldSize"],
}
OPS = {
    "==": lambda s, v: s == v, "!=": lambda s, v: s != v,
    "<": lambda s, v: s < v, "<=": lambda s, v: s <= v,
    ">": lambda s, v: s > v, ">=": lambda s, v: s >= v,
    "in": lambda s, v: s.isin(v), "not_in": lambda s, v: ~s.isin(v),
}
AGG_FUNCS = ("count", "share", "sum", "mean", "median", "min", "max", "nunique")


def _level_frame(data: ChatData, level: str) -> pd.DataFrame:
    if level == "hole":
        return data.holes()
    if level == "round":
        return data.rounds()
    if level == "teg":
        return data.tegs()
    raise ToolInputError("level must be 'hole', 'round' or 'teg'")


def _normalise_value(field_name: str, value: Any, data: ChatData) -> Any:
    if field_name == "Player":
        if isinstance(value, list):
            return [resolve_player(v, data.players()) for v in value]
        return resolve_player(value, data.players())
    if field_name == "Pl":
        return [str(v).upper() for v in value] if isinstance(value, list) else str(value).upper()
    return value


def _mask(df: pd.DataFrame, cond: dict, allowed: list[str], data: ChatData) -> pd.Series:
    if not isinstance(cond, dict):
        raise ToolInputError("Each filter must be an object with field, op, value.")
    fld, op, val = cond.get("field"), cond.get("op"), cond.get("value")
    if fld not in allowed or fld not in df.columns:
        raise ToolInputError(f"Unknown field '{fld}'. Allowed here: {allowed}")
    if op not in OPS:
        raise ToolInputError(f"Unknown op '{op}'. Allowed: {list(OPS)}")
    if op in ("in", "not_in") and not isinstance(val, list):
        raise ToolInputError(f"op '{op}' needs a list value.")
    return OPS[op](df[fld], _normalise_value(fld, val, data))


def _describe_cond(cond: dict) -> str:
    return f"{cond.get('field')} {cond.get('op')} {cond.get('value')}"


def query_scores(data: ChatData, level: str, filters: Optional[list] = None,
                 group_by: Optional[list] = None, aggregations: Optional[list] = None,
                 columns: Optional[list] = None, sort_by: Optional[str] = None,
                 descending: bool = False, limit: int = 20,
                 min_count: Optional[int] = None) -> dict:
    df = _level_frame(data, level)
    dims = [c for c in DIMENSIONS[level] if c in df.columns]
    allowed = dims + [c for c in MEASURES[level] if c in df.columns]
    filters = filters or []
    group_by = group_by or []
    aggregations = aggregations or []
    limit = max(1, min(int(limit or 20), MAX_ROWS))

    mask = pd.Series(True, index=df.index)
    for cond in filters:
        mask &= _mask(df, cond, allowed, data)
    work = df[mask]
    steps = [f"Level: {level} ({len(df)} rows total)."]
    if filters:
        steps.append("Filters: " + "; ".join(_describe_cond(c) for c in filters) + f" → {len(work)} rows.")

    if aggregations or group_by:
        bad = [g for g in group_by if g not in dims]
        if bad:
            raise ToolInputError(f"Cannot group by {bad}. Allowed: {dims}")
        if not aggregations:
            aggregations = [{"func": "count", "label": "n"}]
        keys = group_by or None
        grouped = work.groupby(keys) if keys else None
        out = (work[group_by].drop_duplicates().set_index(group_by) if keys
               else pd.DataFrame(index=[0]))
        out["n"] = grouped.size() if keys else len(work)
        for agg in aggregations:
            if not isinstance(agg, dict):
                raise ToolInputError("Each aggregation must be an object.")
            func = agg.get("func")
            fld = agg.get("field")
            where = agg.get("where")
            label = agg.get("label") or f"{func}_{fld or 'rows'}"
            if func not in AGG_FUNCS:
                raise ToolInputError(f"Unknown func '{func}'. Allowed: {list(AGG_FUNCS)}")
            if func in ("count", "share"):
                if func == "share" and not where:
                    raise ToolInputError("'share' needs a 'where' condition.")
                hit = _mask(work, where, allowed, data) if where else pd.Series(True, index=work.index)
                if keys:
                    series = hit.groupby([work[k] for k in group_by]).sum() if func == "count" \
                        else 100 * hit.groupby([work[k] for k in group_by]).mean()
                    out[label] = series
                else:
                    out[label] = hit.sum() if func == "count" else (100 * hit.mean() if len(hit) else None)
                desc = f"{label} = {'count' if func == 'count' else '% of rows'}"
                steps.append(desc + (f" where {_describe_cond(where)}" if where else "") + ".")
            else:
                if fld not in allowed or fld not in work.columns:
                    raise ToolInputError(f"Unknown field '{fld}'. Allowed: {allowed}")
                if where:
                    sub = work[_mask(work, where, allowed, data)]
                else:
                    sub = work
                if keys:
                    out[label] = sub.groupby(group_by)[fld].agg(func)
                else:
                    out[label] = sub[fld].agg(func)
                steps.append(f"{label} = {func} of {fld}"
                             + (f" where {_describe_cond(where)}" if where else "") + ".")
        out = out.reset_index() if keys else out
        if min_count:
            out = out[out["n"] >= int(min_count)]
            steps.append(f"Groups with fewer than {min_count} rows dropped.")
        if group_by:
            steps.append("Grouped by " + ", ".join(group_by) + "; n = rows per group.")
    else:
        cols = columns or [c for c in dims + MEASURES[level] if c in work.columns and c != "Pl"]
        bad = [c for c in cols if c not in allowed]
        if bad:
            raise ToolInputError(f"Unknown columns {bad}. Allowed: {allowed}")
        out = work[cols]

    if sort_by:
        if sort_by not in out.columns:
            raise ToolInputError(f"sort_by '{sort_by}' is not an output column: {list(out.columns)}")
        out = out.sort_values(sort_by, ascending=not descending, kind="stable")
        steps.append(f"Sorted by {sort_by} ({'high→low' if descending else 'low→high'}).")
    rows, truncated = _records(out, limit)
    return {
        "level": level,
        "rows_matched": int(len(work)),
        "result": rows,
        "truncated": truncated,
        "calculation": steps,
    }


# ---------------------------------------------------------------------------
# Tool schemas (Anthropic tool-use format) and dispatch
# ---------------------------------------------------------------------------
_COND_SCHEMA = {
    "type": "object",
    "properties": {
        "field": {"type": "string"},
        "op": {"type": "string", "enum": list(OPS)},
        "value": {"description": "Number, string, boolean, or a list for in/not_in."},
    },
    "required": ["field", "op", "value"],
}

TOOL_SCHEMAS = [
    {
        "name": "get_honours",
        "description": (
            "Winners of each completed TEG (TEG Trophy, Green Jacket, Wooden Spoon) and how many "
            "times each player has won each. Use for 'who has won most', 'who won TEG 12', etc. "
            "This is the official record, including manual overrides."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"competition": {"type": "string", "enum": ["all", *COMPETITIONS]}},
            "required": [],
        },
    },
    {
        "name": "get_streak_records",
        "description": (
            "Longest streaks per player and all-time streak records (birdies, pars or better, "
            "holes without +2 or triple bogey; or the bad equivalents)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"direction": {"type": "string", "enum": ["good", "bad"]}},
            "required": [],
        },
    },
    {
        "name": "get_bounce_back",
        "description": (
            "Bounce-back rate: after a bad hole, how often the player makes par or better on the "
            "next hole. Returns rate, sample size and the player's normal par-or-better baseline."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "basis": {"type": "string", "enum": list(BASIS_COLUMNS)},
                "trigger": {"type": "string", "enum": list(TRIGGER_THRESHOLDS)},
                "group_by": {"type": "string", "enum": list(GROUPINGS)},
                "player": {"type": "string"},
                "teg": {"type": "integer"},
            },
            "required": [],
        },
    },
    {
        "name": "query_scores",
        "description": (
            "Flexible, validated query over the score data for anything the other tools don't "
            "cover. Pick a level: 'hole' (one row per player per hole), 'round' (per player per "
            "round) or 'teg' (per player per TEG, with TrophyPosition, JacketPosition, FieldSize "
            "and Complete). Filter, then either list rows (columns + sort_by) or group_by and "
            "aggregate. Aggregation funcs: count, share (% of rows meeting 'where'), sum, mean, "
            "median, min, max, nunique. Each aggregation may have its own 'where' filter. "
            "Every grouped output includes n (rows per group); use min_count to drop tiny samples. "
            "Measures: Sc (strokes), GrossVP (gross vs par), NetVP (net vs par), Stableford, HC "
            "(handicap). Hole-level also has PAR, SI, Hole, FrontBack. Birdie or better is "
            "GrossVP <= -1; par or better GrossVP <= 0; bogey GrossVP == 1; double bogey or "
            "worse GrossVP >= 2."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "level": {"type": "string", "enum": ["hole", "round", "teg"]},
                "filters": {"type": "array", "items": _COND_SCHEMA},
                "group_by": {"type": "array", "items": {"type": "string"}},
                "aggregations": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "func": {"type": "string", "enum": list(AGG_FUNCS)},
                            "field": {"type": "string"},
                            "where": _COND_SCHEMA,
                            "label": {"type": "string"},
                        },
                        "required": ["func"],
                    },
                },
                "columns": {"type": "array", "items": {"type": "string"}},
                "sort_by": {"type": "string"},
                "descending": {"type": "boolean"},
                "limit": {"type": "integer"},
                "min_count": {"type": "integer"},
            },
            "required": ["level"],
        },
    },
]

_DISPATCH = {
    "get_honours": get_honours,
    "get_streak_records": get_streak_records,
    "get_bounce_back": get_bounce_back,
    "query_scores": query_scores,
}


def run_tool(name: str, tool_input: dict, data: ChatData) -> dict:
    """Run one tool. Input errors come back as {"error": ...} for the model to fix."""
    fn = _DISPATCH.get(name)
    if fn is None:
        return {"error": f"Unknown tool '{name}'."}
    if not isinstance(tool_input, dict):
        return {"error": "Tool input must be an object."}
    try:
        return fn(data, **tool_input)
    except ToolInputError as exc:
        return {"error": str(exc)}
    except TypeError as exc:
        return {"error": f"Bad arguments: {exc}"}
