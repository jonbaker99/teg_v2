"""TEGBot's lookups, and the data it gives the code sandbox.

Two ways to an answer, lookups first:

- **Lookups** (this module) answer well-defined questions with the site's own
  definitions: honours, records, streaks, bounce-back. Each returns its full
  result, ties included, never a cut-off list, plus ``definition`` /
  ``notes`` and the ``page`` that shows the same data.
- **Code** for everything else. The bot writes pandas in Anthropic's sandbox
  against the CSVs ``ChatData.datasets()`` builds (documented in
  ``prompt.DATA_GUIDE``). That code runs on Anthropic's servers, never here.

Bad input never raises out of ``run_tool``: it comes back as ``{"error": ...}``
so the model can correct itself and retry.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Optional

import pandas as pd

from teg_analysis.analysis.standings import build_rounds, build_tegs

from teg_analysis.analysis.bounceback import (
    BASIS_COLUMNS, GROUPINGS, TRIGGER_THRESHOLDS, bounce_back_stats,
)



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


def _default_ranked(scope: str) -> pd.DataFrame:
    from teg_analysis.analysis import rankings
    return {
        "teg": rankings.get_ranked_teg_data,
        "round": rankings.get_ranked_round_data,
        "frontback": rankings.get_ranked_frontback_data,
    }[scope]()


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
    #: The site's simulation of the next TEG (TEG Predictatron 3100), as plain data.
    predictions: Optional[Callable[[], dict]] = None
    #: Win chances now for the TEG in progress, entered holes included. Raises
    #: ValueError when no TEG is in progress.
    live_predictions: Optional[Callable[[], dict]] = None
    #: (player full name or None, competition, rivals) -> what it takes to win from here.
    what_it_takes: Optional[Callable[..., Any]] = None
    #: scope ("teg" | "round" | "frontback") -> ranked frame, as /records uses.
    ranked: Callable[[str], pd.DataFrame] = None  # type: ignore[assignment]
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

    def ranked_df(self, scope: str) -> pd.DataFrame:
        return self._get(f"ranked_{scope}", lambda: (self.ranked or _default_ranked)(scope))

    def complete(self) -> set[int]:
        return self._get("complete", lambda: {int(t) for t in self.completed_tegs()})

    def rounds(self) -> pd.DataFrame:
        return self._get("rounds", self._build_rounds)

    def tegs(self) -> pd.DataFrame:
        return self._get("tegs", self._build_tegs)

    def _build_rounds(self) -> pd.DataFrame:
        return build_rounds(self.holes())

    def _build_tegs(self) -> pd.DataFrame:
        return build_tegs(self.holes(), self.complete())

    def datasets(self) -> dict[str, pd.DataFrame]:
        """The CSVs uploaded to the code sandbox. Columns: see prompt.DATA_GUIDE."""
        hole_cols = ["Player", "Pl", "TEGNum", "Year", "Area", "Course", "Date", "Round",
                     "Hole", "FrontBack", "PAR", "SI", "HC", "HCStrokes", "Sc", "GrossVP",
                     "NetVP", "Stableford"]
        holes = self.holes()[[c for c in hole_cols if c in self.holes().columns]].copy()
        if "Date" in holes.columns:
            holes["Date"] = pd.to_datetime(holes["Date"], format="%d/%m/%Y", errors="coerce").dt.date
        winners = self.winners_df().copy()
        return {
            "holes.csv": holes.sort_values(["TEGNum", "Round", "Player", "Hole"]),
            "rounds.csv": self.rounds(),
            "tegs.csv": self.tegs(),
            "winners.csv": winners,
        }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
class ToolInputError(ValueError):
    """Bad tool input — reported back to the model, never to the user as a crash."""


def _as_int(value: Any, name: str) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        raise ToolInputError(f"{name} must be a whole number, not {value!r}.") from None


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


def _records(df: pd.DataFrame) -> list[dict]:
    """Every row, JSON-safe. Lookups never truncate: small data, and a cut-off
    list can hide a tie."""
    out = df.copy()
    for col in out.columns:
        if pd.api.types.is_float_dtype(out[col]):
            out[col] = out[col].round(2)
            if (out[col].dropna() % 1 == 0).all():
                out[col] = out[col].astype("Int64")
    rows = [
        {k: (None if pd.isna(v) else (v.item() if hasattr(v, "item") else v)) for k, v in r.items()}
        for r in out.to_dict(orient="records")
    ]
    return rows


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
    result: dict[str, Any] = {"winners_by_teg": _records(winners), "counts": {}}
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
        "longest_streak_per_player": _records(prepare_streaks_data(holes, direction)),
        "all_time_records": _records(prepare_record_streaks_data(holes, direction)),
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
        teg = _as_int(teg, "teg")
        holes = holes[holes["TEGNum"] == teg]
        if holes.empty:
            raise ToolInputError(f"No data for TEG {teg}.")
    try:
        df = bounce_back_stats(holes, basis=basis, trigger=trigger, group_by=group_by)
    except ValueError as exc:
        raise ToolInputError(str(exc)) from exc
    if player:
        df = df[df["Player"] == resolve_player(player, data.players())]
    trig_text = "bogey or worse" if trigger == "bogey_or_worse" else "double bogey or worse"
    return {
        "result": _records(df),
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
# Tool: records — the /records page's own holders, every tie included
# ---------------------------------------------------------------------------
RECORD_SCOPES = {"teg": "teg", "round": "round", "nine": "frontback"}


def get_records(data: ChatData, scope: str = "round") -> dict:
    from teg_analysis.display.formatters import (
        prepare_records_table, prepare_worst_records_table, score_count_record_holders,
    )
    if scope == "score_counts":
        holders = score_count_record_holders(data.holes())
        players = data.players()
        for h in holders:
            h["player"] = players.get(h["player"], h["player"])
        return {
            "scope": scope, "records": holders,
            "notes": ["Eagles, birdies and pars counts include better scores."],
            "page": "/records?tab=score_counts",
        }
    if scope not in RECORD_SCOPES:
        raise ToolInputError(f"scope must be one of {[*RECORD_SCOPES, 'score_counts']}")
    level = RECORD_SCOPES[scope]
    ranked = data.ranked_df(level)
    if level == "teg":
        worst_src = ranked[ranked["TEGNum"] != 2]  # TEG 2 had 3 rounds
    else:
        worst_src = ranked
    best = prepare_records_table(ranked, level)
    worst = prepare_worst_records_table(worst_src, level)

    def rows(df: pd.DataFrame) -> list[dict]:
        return [{"record": str(r.iloc[0]), "value": str(r.iloc[1]),
                 "player": str(r.iloc[2]), "when": str(r.iloc[3])} for _, r in df.iterrows()]
    tab = {"teg": "teg", "round": "round", "nine": "9hole"}[scope]
    return {
        "scope": scope,
        "best": rows(best),
        "worst": rows(worst),
        "notes": [
            "Every record holder is listed; several rows for one record means a tie.",
            "TEG records count completed TEGs only; worst TEGs exclude TEG 2 (3 rounds).",
        ],
        "page": f"/records?tab={tab}",
    }


# ---------------------------------------------------------------------------
# Tool: predictions — the site's simulator (TEG Predictatron 3100)
# ---------------------------------------------------------------------------
def get_predictions(data: ChatData) -> dict:
    from teg_analysis.analysis.win_probability import NoTegInProgress

    if data.predictions is None:
        raise ToolInputError("Predictions aren't available here.")
    if data.live_predictions is not None:
        try:
            live = data.live_predictions()
        except NoTegInProgress:
            live = None  # no TEG in progress: pre-tournament odds are right
        except Exception as exc:  # any fault: never fall back to pre-tournament odds mid-TEG
            raise ToolInputError("Win chances can't be worked out right now.") from exc
        if live:
            raise ToolInputError(
                f"TEG {live['teg_num']} is in progress; use get_live_win_chances for current chances.")
    try:
        pred = data.predictions()
    except ValueError as exc:
        raise ToolInputError(f"The simulator can't run yet: {exc}") from exc
    return {
        **pred,
        "definition": (
            f"Monte Carlo simulation of TEG {pred['teg_num']} ({pred['simulations']:,} runs). "
            "Each player's hole scores are drawn from their recent history by par and stroke "
            "index, using this TEG's courses and handicaps. Trophy = most Stableford points, "
            "Green Jacket = lowest gross, Wooden Spoon = fewest Stableford points. Chances are "
            "the share of simulations each player won; odds are the fair fractional equivalent."
        ),
        "notes": [*pred.get("notes", []),
                  "A prediction from past form, not a certainty.",
                  "The Predictatron page reruns the simulation, so its figures can differ by a "
                  "point or two, and lets you change the settings."],
        "page": "/simulation",
    }


# ---------------------------------------------------------------------------
# Tools: live win chances and "what does X need" (a TEG in progress)
# ---------------------------------------------------------------------------
def get_live_win_chances(data: ChatData) -> dict:
    if data.live_predictions is None:
        raise ToolInputError("Live win chances aren't available here.")
    try:
        pred = data.live_predictions()
    except ValueError as exc:
        raise ToolInputError(str(exc)) from exc
    return {
        **pred,
        "definition": (
            "Win chances now for the TEG in progress. Completed rounds and the holes entered so "
            "far in the round being played are banked at their actual scores; the rest is "
            "simulated hole by hole from each player's form, blended with how they are playing "
            "this TEG. Trophy = most Stableford points (net vs par before TEG 8), Green Jacket = "
            "lowest gross, Wooden Spoon = fewest Stableford points. Change is in percentage "
            "points since the last finalised round. Thru = holes entered in the live round."),
        "notes": ["A prediction, not a certainty.",
                  "Mid-round figures move as scores come in. When live_round is set they include "
                  "scores entered but not yet finalised; otherwise they are as at the last "
                  "finalised round.",
                  "Positions share ties (2=)."],
        "page": "/simulation?tab=live",
    }


def get_what_it_takes(data: ChatData, player: Optional[str] = None,
                      competition: str = "trophy", rivals: str = "same_pace") -> Any:
    if data.what_it_takes is None:
        raise ToolInputError("This isn't available here.")
    if competition not in ("trophy", "jacket"):
        raise ToolInputError("competition must be 'trophy' or 'jacket'.")
    if rivals not in ("same_pace", "expected"):
        raise ToolInputError("rivals must be 'same_pace' or 'expected'.")
    name = resolve_player(player, data.players()) if player and str(player).strip() else None
    try:
        res = data.what_it_takes(name, competition, rivals)
    except ValueError as exc:
        raise ToolInputError(str(exc)) from exc
    key = "players" if name is None else "result"
    return {
        key: res, "competition": competition, "rivals": rivals,
        "definition": (
            "What the player needs over the holes still to play to win outright, or to tie. "
            "same_pace: every rival keeps scoring at the per-hole rate they have so far. "
            "expected: rivals score as the simulator expects. Gross targets are converted from "
            "Stableford/net targets using the player's handicap and the remaining scorecards, so "
            "say 'about'. Holes entered in a round in progress are counted as played."),
        "notes": ["Check out_of_reach and reality before saying it is realistic.",
                  "A projection from form, not a certainty."],
        "page": "/simulation?tab=live",
    }


# ---------------------------------------------------------------------------
# Tool schemas (Anthropic tool-use format) and dispatch
# ---------------------------------------------------------------------------
TOOL_SCHEMAS = [
    {
        "name": "get_predictions",
        "description": (
            "Predictions for the next TEG from the site's simulator, the TEG Predictatron 3100: "
            "each player's chance and fair odds of winning the TEG Trophy, the Green Jacket and "
            "the Wooden Spoon, plus expected Stableford and gross. Use for any question about "
            "who will win, favourites, odds or forecasts for the upcoming TEG."
        ),
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "get_live_win_chances",
        "description": (
            "Win chances right now while a TEG is in progress, from the site's live simulator: "
            "each player's chance of the TEG Trophy, Green Jacket and Wooden Spoon, change since "
            "the last finalised round, positions, and totals so far, including holes entered in "
            "the round being played. Use for who will win, chances, odds, favourite or who is "
            "winning now during a TEG. Errors if no TEG is in progress."),
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "get_what_it_takes",
        "description": (
            "What a player needs to win the TEG Trophy or Green Jacket from here, while a TEG is "
            "in progress: target gross (per round and total, about) and Stableford points, to "
            "win outright or tie, with a reality check against their own scoring. Omit player "
            "for everyone. rivals same_pace (default): rivals keep scoring as they have so far; "
            "expected: rivals score as the simulator expects. Never work targets out by hand."),
        "input_schema": {
            "type": "object",
            "properties": {
                "player": {"type": "string"},
                "competition": {"type": "string", "enum": ["trophy", "jacket"]},
                "rivals": {"type": "string", "enum": ["same_pace", "expected"]},
            },
            "required": [],
        },
    },
    {
        "name": "get_honours",
        "description": (
            "Official winners of each completed TEG (TEG Trophy, Green Jacket, Wooden Spoon) "
            "and win counts per player, including manual overrides."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"competition": {"type": "string", "enum": ["all", *COMPETITIONS]}},
            "required": [],
        },
    },
    {
        "name": "get_records",
        "description": (
            "All-time records exactly as the site's Records page shows them, with every "
            "tied holder: best and worst gross, score, net and Stableford for a whole TEG, a "
            "round, or a 9 (scope teg/round/nine); or most/fewest eagles, birdies, pars etc. "
            "in a round or TEG (scope score_counts)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"scope": {"type": "string", "enum": [*RECORD_SCOPES, "score_counts"]}},
            "required": ["scope"],
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
]

_DISPATCH = {
    "get_predictions": get_predictions,
    "get_live_win_chances": get_live_win_chances,
    "get_what_it_takes": get_what_it_takes,
    "get_honours": get_honours,
    "get_records": get_records,
    "get_streak_records": get_streak_records,
    "get_bounce_back": get_bounce_back,
}


def run_tool(name: str, tool_input: dict, data: ChatData) -> dict:
    """Run one lookup. Input errors come back as {"error": ...} for the model to fix."""
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
    except (ValueError, KeyError, IndexError) as exc:
        return {"error": f"Bad input: {exc}"}
