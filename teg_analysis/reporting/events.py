"""Stage 2: notable-event detection + evidence assembly + 3-axis scoring.

Produces a ranked list of NotableEvent objects for a TEG. Each event is a single
narrative *beat* that carries its underlying hole-by-hole evidence, so the writer
can render specifics ("a double at the par-4 10th, a 10 at the short 17th") rather
than abstractions ("a back-nine meltdown").

Key differences from the legacy streamlit/commentary approach:
- Detects *maximal contiguous* stretches, not every overlapping rolling window, so
  one collapse is one beat (not 12-20 near-duplicate rows).
- Keeps the hole evidence attached to the beat.
- Scores every beat on importance / rarity / entertainment so selection happens in
  code, before any prose.

Pure Python: runnable and inspectable without any LLM/API key. Scoring heuristics
here are a first cut, intended to be tuned against real output.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Optional
import re

import pandas as pd

from teg_analysis.core.data_loader import load_all_data
from teg_analysis.analysis.commentary import (
    create_round_events,
    create_round_summary,
    create_tournament_summary,
)
from teg_analysis.reporting import scoring
from teg_analysis.reporting.era import trophy_metric

# Competition labels used in text
TROPHY_STABLEFORD = "Trophy (Stableford)"
TROPHY_NETVP = "Trophy (Net VP)"
TROPHY = TROPHY_STABLEFORD  # default; era-aware TROPHY chosen in build_notable_events
JACKET = "Green Jacket (Gross)"


def _trophy_label(metric: str) -> str:
    return TROPHY_NETVP if metric == "net_vs_par" else TROPHY_STABLEFORD


def _trophy_cols(metric: str) -> dict:
    """Era-appropriate Trophy column names used across events.py."""
    if metric == "net_vs_par":
        return {
            "round_score": "Round_Score_NetVP",
            "cum_score": "Cumulative_Tournament_Score_NetVP",
            "cum_rank": "Cumulative_Tournament_Rank_NetVP",
            "gap_after": "Gap_To_Leader_After_Round_NetVP",
            "tournament_score": "Tournament_Score_NetVP",
            "final_rank": "Final_Rank_NetVP",
            "won": "Won_NetVP",
            "rank_player_tegs": "Rank_Among_Player_TEGs_NetVP",
            "rank_all_tegs": "Rank_Among_All_TEGs_To_Date_NetVP",
            "rank_before": "Rank_NetVP_Before",
            "rank_after": "Rank_NetVP_After",
            "rank_hole": "Rank_NetVP_TEG",
            "hist_player": "Round_Rank_In_Player_History_NetVP",
            "hist_all": "Round_Rank_In_All_History_NetVP",
            "front_back": "Front_9_vs_Back_9_NetVP",
            "took_lead_event": "Took Lead (NetVP)",
            "spoon_hit_event": "Hit Bottom (Spoon NetVP)",
            # Sort direction: lower-is-better for NetVP
            "score_ascending": True,
        }
    return {
        "round_score": "Round_Score_Stableford",
        "cum_score": "Cumulative_Tournament_Score_Stableford",
        "cum_rank": "Cumulative_Tournament_Rank_Stableford",
        "gap_after": "Gap_To_Leader_After_Round_Stableford",
        "tournament_score": "Tournament_Score_Stableford",
        "final_rank": "Final_Rank_Stableford",
        "won": "Won_Stableford",
        "rank_player_tegs": "Rank_Among_Player_TEGs_Stableford",
        "rank_all_tegs": "Rank_Among_All_TEGs_To_Date_Stableford",
        "rank_before": "Rank_Stableford_Before",
        "rank_after": "Rank_Stableford_After",
        "rank_hole": "Rank_Stableford_TEG",
        "hist_player": "Round_Rank_In_Player_History_Stableford",
        "hist_all": "Round_Rank_In_All_History_Stableford",
        "front_back": "Front_9_vs_Back_9_Stableford",
        "took_lead_event": "Took Lead (Stableford)",
        "spoon_hit_event": "Hit Bottom (Spoon)",
        # Higher-is-better for Stableford
        "score_ascending": False,
    }


# ---------------------------------------------------------------------------
# Event model
# ---------------------------------------------------------------------------
@dataclass
class NotableEvent:
    teg_num: int
    scope: str                      # 'tournament' | 'round' | 'stretch' | 'hole'
    type: str                       # machine type, e.g. 'lead_change', 'cold_stretch'
    headline: str                   # short human description (for inspection / planning)
    players: list = field(default_factory=list)   # full names involved
    round: Optional[int] = None
    course: Optional[str] = None                  # course this round was played on
    holes: list = field(default_factory=list)     # evidence: [{hole,par,sc,grossvp,stableford,result}]
    importance: float = 0.0
    rarity: float = 0.0
    entertainment: float = 0.0
    total: float = 0.0
    context: dict = field(default_factory=dict)   # extra structured detail for the writer

    def to_dict(self):
        return asdict(self)


# ---------------------------------------------------------------------------
# Hole-evidence helpers
# ---------------------------------------------------------------------------
_RESULT_NAMES = {
    -3: "albatross",
    -2: "eagle",
    -1: "birdie",
    0: "par",
    1: "bogey",
    2: "double bogey",
    3: "triple bogey",
    4: "quadruple bogey",
    5: "quintuple bogey",
    6: "sextuple bogey",
    7: "septuple bogey",
}


def _ord(n: int) -> str:
    n = int(n)
    if 10 <= n % 100 <= 20:
        suf = "th"
    else:
        suf = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suf}"


def _proper(name) -> str:
    """Proper-case a player name from the all-caps-surname data format
    ('John PATTERSON' -> 'John Patterson')."""
    return " ".join(w.capitalize() for w in str(name).split())


def result_label(grossvp: int, sc: int, par: int) -> str:
    if sc == 1:
        return "hole-in-one"
    if grossvp in _RESULT_NAMES:
        return _RESULT_NAMES[grossvp]
    if grossvp < -3:
        return "albatross or better"
    return f"{int(grossvp):+d} (blow-up)"


def hole_evidence(row) -> dict:
    par = int(row["PAR"])
    sc = int(row["Sc"])
    gvp = int(row["GrossVP"])
    d = {
        "hole": int(row["Hole"]),
        "par": par,
        "sc": sc,
        "grossvp": gvp,
        "stableford": int(row["Stableford"]),
        "result": result_label(gvp, sc, par),
    }
    si_val = row.get("SI") if hasattr(row, "get") else getattr(row, "SI", None)
    if si_val is not None:
        try:
            d["si"] = int(si_val)
        except (TypeError, ValueError):
            pass
    return d


def _parse_rank(s) -> tuple:
    """Parse a 'X of N' historical-rank string into (X, N); (None, None) on failure."""
    if not isinstance(s, str):
        return (None, None)
    m = re.match(r"\s*(\d+)\s+of\s+(\d+)\s*", s)
    if not m:
        return (None, None)
    return (int(m.group(1)), int(m.group(2)))


# ---------------------------------------------------------------------------
# Standing weights (how central each player is to the result)
# ---------------------------------------------------------------------------
def _standing_weights(tsum: pd.DataFrame, metric: str = "stableford") -> dict:
    """Map Pl -> weight in [0,1] reflecting centrality to the result (top & bottom).

    Era-aware: the Trophy is Stableford for TEG 8+ and net-vs-par for TEGs 1-7,
    so the 'main winner' column shifts accordingly.
    """
    cols = _trophy_cols(metric)
    trophy_rank_col = cols["final_rank"]
    trophy_won_col = cols["won"]
    weights = {}
    for _, r in tsum.iterrows():
        w = 0.4
        rt = r[trophy_rank_col]
        rj = r["Final_Rank_Gross"]
        if r[trophy_won_col] or r["Won_Gross"]:
            w = 1.0
        elif rt == 2 or rj == 2:
            w = 0.85
        elif rt == 3 or rj == 3:
            w = 0.7
        if r["Wooden_Spoon"]:
            w = max(w, 0.7)        # bottom of the board still matters (and is good colour)
        weights[r["Pl"]] = w
    return weights


# ---------------------------------------------------------------------------
# Detectors
# ---------------------------------------------------------------------------
def _maximal_runs(rows, cond):
    """Return maximal contiguous sub-lists of rows where cond(row) is True."""
    runs, cur = [], []
    for r in rows:
        if cond(r):
            cur.append(r)
        elif cur:
            runs.append(cur)
            cur = []
    if cur:
        runs.append(cur)
    return runs


def _rank1_counts(teg_df: pd.DataFrame, rank_col: str) -> dict:
    """Map (round, hole) -> number of players sharing rank 1 — to tell an outright
    takeover (count 1) from merely drawing level at the top (count > 1)."""
    sub = teg_df[teg_df[rank_col] == 1]
    counts = sub.groupby(["Round", "Hole"]).size()
    return {(int(r), int(h)): int(n) for (r, h), n in counts.items()}


def _turning_points(events_log: pd.DataFrame, teg_df: pd.DataFrame, sw: dict,
                    metric: str = "stableford") -> list:
    """Lead changes (top) and spoon changes (bottom) as discrete turning-point beats.

    Era-aware: pre-8 TEGs use NetVP-based Trophy + Spoon events; post-8 use Stableford.
    """
    cols = _trophy_cols(metric)
    trophy_label = _trophy_label(metric)
    out = []
    lookup = {
        (int(r.Round), r.Pl, int(r.Hole)): r
        for r in teg_df.itertuples(index=False)
    }
    trophy_counts = _rank1_counts(teg_df, cols["rank_hole"])
    gr_counts = _rank1_counts(teg_df, "Rank_GrossVP_TEG")
    wanted = {
        cols["took_lead_event"]: (trophy_label, "lead_change"),
        "Took Lead (Gross)": (JACKET, "lead_change"),
        cols["spoon_hit_event"]: ("Wooden Spoon", "spoon_change"),
    }
    for _, e in events_log.iterrows():
        if e["Event"] not in wanted:
            continue
        rnd, hole = int(e["Round"]), int(e["Hole"])
        if rnd == 1 and hole == 1:
            continue  # start of tournament, not a change
        comp, etype = wanted[e["Event"]]
        pl, player = e["Pl"], e["Player"]
        key = (rnd, pl, hole)
        ev = [hole_evidence(lookup[key]._asdict())] if key in lookup else []
        late = rnd >= teg_df["Round"].max()
        w = sw.get(pl, 0.4)
        lead_type = None
        if etype == "lead_change":
            counts = trophy_counts if comp == trophy_label else gr_counts
            outright = counts.get((rnd, hole), 1) <= 1
            lead_type = "outright" if outright else "level"
            # Importance scales hard with how late/decisive the change is: opening-round
            # jockeying while the field is bunched is routine, not drama; a draw-level is
            # less than an outright take. Late, outright changes are the noteworthy ones.
            base_imp = 2.0 + 2.2 * (rnd - 1) + (1.5 if late else 0) + 1.5 * w
            base_ent = 2.0 + 1.5 * (rnd - 1)
            if not outright:
                base_imp *= 0.6
                base_ent *= 0.6
            imp = scoring.cap(base_imp)
            ent = scoring.cap(base_ent)
            rar = 2.0
            if outright:
                head = f"{player} takes the {comp} lead (R{rnd} H{hole})"
            else:
                head = f"{player} draws level for the {comp} lead (R{rnd} H{hole})"
        else:  # spoon
            imp = scoring.cap(3 + 0.8 * (rnd - 1))
            ent = scoring.cap(5 + 0.8 * (rnd - 1))
            rar = 2.0
            head = f"{player} drops to the bottom of the {comp} race (R{rnd} H{hole})"
        # Use the era-appropriate rank columns from the events_log
        ctx = {"competition": comp,
               "rank_before": _safe_int(e.get(cols["rank_before"])),
               "rank_after": _safe_int(e.get(cols["rank_after"]))}
        if lead_type:
            ctx["lead_type"] = lead_type
        out.append(NotableEvent(
            teg_num=int(e["TEGNum"]), scope="hole", type=etype, round=rnd,
            headline=head, players=[player], holes=ev,
            importance=imp, rarity=rar, entertainment=ent,
            context=ctx,
        ))
    return out


def _safe_int(x):
    try:
        if pd.isna(x):
            return None
        return int(x)
    except (TypeError, ValueError):
        return None


def _sequences(teg_df: pd.DataFrame, sw: dict, player_names: dict,
               player_par_max: Optional[dict] = None,
               par_max: Optional[dict] = None) -> list:
    """Per player-round: cold/hot stretches, recoveries, collapses, standout holes.

    `player_par_max[(player, par)]` and `par_max[par]` carry lifetime worst-gross
    lookups so big-blowup beats can be annotated as a player career-worst on this
    par class and/or an all-time TEG-record worst on this par class. The flags
    only steer appendix inclusion (see `render.build_records_block`); they do not
    change the beat's rarity / importance / mandatory status.
    """
    player_par_max = player_par_max or {}
    par_max = par_max or {}
    out = []
    teg_num = int(teg_df["TEGNum"].iloc[0])
    last_round = int(teg_df["Round"].max())

    for (rnd, pl), g in teg_df.sort_values("Hole").groupby(["Round", "Pl"]):
        rnd = int(rnd)
        rows = [r._asdict() for r in g.itertuples(index=False)]
        player = player_names.get(pl, pl)
        w = sw.get(pl, 0.4)
        late = 1.0 if rnd == last_round else 0.0

        # --- cold stretches: maximal run of double-bogey-or-worse, len >= 3 ---
        for run in _maximal_runs(rows, lambda r: r["GrossVP"] >= 2):
            if len(run) < 3:
                continue
            ev = [hole_evidence(r) for r in run]
            dropped = sum(h["grossvp"] for h in ev)
            severity = scoring.cap(dropped / 3.0)
            imp = scoring.cap((2 + 6 * w) * (0.6 + 0.04 * severity) + late)
            ent = scoring.cap(severity * (1.2 - 0.5 * w))
            rar = scoring.cap(severity * 0.6)
            h0, h1 = ev[0]["hole"], ev[-1]["hole"]
            out.append(NotableEvent(
                teg_num=teg_num, scope="stretch", type="cold_stretch", round=rnd,
                headline=f"{player} bleeds {dropped} shots, holes {h0}-{h1} (R{rnd})",
                players=[player], holes=ev,
                importance=imp, rarity=rar, entertainment=ent,
                context={"shots_dropped": dropped, "length": len(ev)},
            ))

        # --- hot stretches: maximal run of net birdie or better (Stableford >= 3), len >= 3 ---
        for run in _maximal_runs(rows, lambda r: r["Stableford"] >= 3):
            if len(run) < 3:
                continue
            ev = [hole_evidence(r) for r in run]
            gained = sum(h["stableford"] for h in ev)
            severity = scoring.cap(gained / 2.5)
            imp = scoring.cap((2 + 6 * w) * (0.6 + 0.04 * severity) + late)
            ent = scoring.cap(severity * (1.1 - 0.4 * w))
            rar = scoring.cap(severity * 0.6)
            h0, h1 = ev[0]["hole"], ev[-1]["hole"]
            out.append(NotableEvent(
                teg_num=teg_num, scope="stretch", type="hot_stretch", round=rnd,
                headline=f"{player} piles up {gained} points, holes {h0}-{h1} (R{rnd})",
                players=[player], holes=ev,
                importance=imp, rarity=rar, entertainment=ent,
                context={"points_gained": gained, "length": len(ev)},
            ))

        # --- recovery: birdie+ immediately after a run (len>=2) of bogey-or-worse ---
        for i, r in enumerate(rows):
            if r["GrossVP"] <= -1 and i > 0:
                prev = _maximal_runs(rows[:i], lambda x: x["GrossVP"] >= 1)
                if prev and prev[-1][-1]["Hole"] == rows[i - 1]["Hole"] and len(prev[-1]) >= 2:
                    run = prev[-1] + [r]
                    ev = [hole_evidence(x) for x in run]
                    out.append(NotableEvent(
                        teg_num=teg_num, scope="stretch", type="recovery", round=rnd,
                        headline=f"{player} stops the bleeding with a {ev[-1]['result']} at the {_ord(ev[-1]['hole'])} (R{rnd})",
                        players=[player], holes=ev,
                        importance=scoring.cap(2 + 3 * w), rarity=3.0,
                        entertainment=scoring.cap(4 + 2 * (1 - w)),
                        context={"streak_broken": "bogey_or_worse"},
                    ))

        # --- collapse: double+ immediately after a steady run (len>=3) of par-or-better ---
        for i, r in enumerate(rows):
            if r["GrossVP"] >= 2 and i > 0:
                prev = _maximal_runs(rows[:i], lambda x: x["GrossVP"] <= 0)
                if prev and prev[-1][-1]["Hole"] == rows[i - 1]["Hole"] and len(prev[-1]) >= 3:
                    run = prev[-1] + [r]
                    ev = [hole_evidence(x) for x in run]
                    out.append(NotableEvent(
                        teg_num=teg_num, scope="stretch", type="collapse_after_steady", round=rnd,
                        headline=f"{player}'s steady run ends with a {ev[-1]['result']} at the {_ord(ev[-1]['hole'])} (R{rnd})",
                        players=[player], holes=ev,
                        importance=scoring.cap(2 + 3 * w), rarity=2.5,
                        entertainment=scoring.cap(4 + 2 * (1 - w)),
                        context={"streak_broken": "par_or_better"},
                    ))

        # --- standout single holes: eagle, hole-in-one, big blow-up (>= quad) ---
        for r in rows:
            ev = hole_evidence(r)
            if ev["sc"] == 1:
                out.append(_hole_event(teg_num, rnd, player, ev, "hole_in_one",
                                       f"{player} aces the {_ord(ev['hole'])} (R{rnd})",
                                       imp=scoring.cap(4 + 3 * w), rar=10.0, ent=10.0))
            elif ev["grossvp"] <= -2:
                out.append(_hole_event(teg_num, rnd, player, ev, "eagle",
                                       f"{player} eagles the par-{ev['par']} {_ord(ev['hole'])} (R{rnd})",
                                       imp=scoring.cap(3 + 3 * w), rar=8.0,
                                       ent=scoring.cap(7 + 2 * (1 - w))))
            elif ev["grossvp"] >= 4 or ev["sc"] >= 10:
                # Catch quad+ AND any double-figure gross score (belt-and-braces;
                # in TEG's par-3/4/5 layouts grossvp >= 4 covers all 10s anyway).
                par = ev["par"]
                ppm = player_par_max.get((player, par))
                pm = par_max.get(par)
                e = _hole_event(teg_num, rnd, player, ev, "big_blowup",
                                f"{player} runs up a {ev['sc']} ({ev['result']}) at the {_ord(ev['hole'])} (R{rnd})",
                                imp=scoring.cap(1 + 4 * w), rar=scoring.cap(max(ev["grossvp"], 4)),
                                ent=scoring.cap(ev["grossvp"] + 3 - 2 * w))
                e.context = {
                    "is_player_par_worst": ppm is not None and ev["sc"] >= ppm,
                    "is_teg_par_worst": pm is not None and ev["sc"] >= pm,
                }
                out.append(e)
    return out


def _hole_event(teg_num, rnd, player, ev, etype, head, imp, rar, ent) -> NotableEvent:
    return NotableEvent(
        teg_num=teg_num, scope="hole", type=etype, round=rnd, headline=head,
        players=[player], holes=[ev], importance=imp, rarity=rar, entertainment=ent,
    )


def _round_beats(round_summary: pd.DataFrame, sw: dict, metric: str = "stableford") -> list:
    """One leadership beat per round, plus per-player round beats only when notable.

    Era-aware: for pre-8 TEGs the Trophy is net-vs-par (lower wins, signed format);
    for post-8 it's Stableford (higher wins, raw points).
    """
    cols = _trophy_cols(metric)
    is_netvp = metric == "net_vs_par"
    score_unit = "net VP" if is_netvp else "Stableford"

    def _fmt_score(x) -> str:
        return f"{int(x):+d}" if is_netvp else f"{int(x)} pts"

    out = []
    teg_num = int(round_summary["TEGNum"].iloc[0])
    last_round = int(round_summary["Round"].max())

    for rnd, g in round_summary.groupby("Round"):
        rnd = int(rnd)
        trophy_leader = g.loc[g[cols["cum_rank"]].idxmin()]
        jacket_leader = g.loc[g["Cumulative_Tournament_Rank_Gross"].idxmin()]
        head = (f"After R{rnd}: {trophy_leader['Player']} leads the Trophy "
                f"(gap {abs(int(trophy_leader[cols['gap_after']]))} on {score_unit}); "
                f"{jacket_leader['Player']} leads the Jacket")
        out.append(NotableEvent(
            teg_num=teg_num, scope="round", type="round_leadership", round=rnd,
            headline=head,
            players=[trophy_leader["Player"], jacket_leader["Player"]],
            importance=scoring.cap(4 + 0.6 * (rnd - 1) + (1 if rnd == last_round else 0)),
            rarity=1.0, entertainment=2.0,
            context={"trophy_leader": trophy_leader["Player"], "jacket_leader": jacket_leader["Player"]},
        ))

        for _, r in g.iterrows():
            pl, player = r["Pl"], r["Player"]
            w = sw.get(pl, 0.4)
            px, pn = _parse_rank(r.get(cols["hist_player"]))
            ax, an = _parse_rank(r.get(cols["hist_all"]))
            fb = r.get(cols["front_back"])
            note, rar, ent, imp = None, 1.0, 2.0, scoring.cap(2 + 3 * w)

            # Guard PB/worst against trivial early-career flags (a debut player's
            # every round is a "PB"). Require a meaningful history first.
            has_history = pn is not None and pn >= 8
            round_score_str = _fmt_score(r[cols["round_score"]])
            if ax is not None and ax <= 3:
                label = {1: "the best", 2: "the 2nd-best", 3: "the 3rd-best"}[ax]
                note = f"{player}'s {round_score_str} is {label} round in TEG history to date"
                rar, ent = {1: 9.0, 2: 8.0, 3: 7.0}[ax], scoring.cap(7 + 2 * (1 - w))
            elif px == 1 and has_history:
                note = f"{player} posts a personal-best round: {round_score_str}"
                rar, ent = 7.0, scoring.cap(6 + 2 * (1 - w))
            elif has_history and px == pn and pn > 3:
                note = f"{player}'s worst round to date: {round_score_str}"
                rar, ent = 5.0, scoring.cap(5 + 2 * (1 - w))
            elif fb is not None and abs(fb) >= 10:
                side = "front nine" if fb > 0 else "back nine"
                unit = "shot" if is_netvp else "pt"
                note = f"{player} far stronger on the {side} in R{rnd} ({int(abs(fb))}-{unit} split)"
                rar, ent = 3.0, 5.0

            if note:
                ctx = {"round_score": int(r[cols["round_score"]]),
                       "round_gross_vp": int(r["Round_Score_Gross"]),
                       "trophy_metric": metric}
                # Keep legacy key for any downstream consumer that read 'round_stableford';
                # for pre-8 reports it carries the net-vs-par value (still a Trophy score).
                ctx["round_stableford"] = int(r[cols["round_score"]])
                out.append(NotableEvent(
                    teg_num=teg_num, scope="round", type="round_player", round=rnd,
                    headline=note, players=[player],
                    importance=imp, rarity=rar, entertainment=ent,
                    context=ctx,
                ))

            # --- Gross-side round beat (independent of Trophy metric) ---
            # The Green Jacket is its own competition; a round can be a Trophy PB
            # AND a Gross PB simultaneously, or one without the other. Emit a
            # separate `round_player_gross` beat using the gross history columns.
            gx, gn = _parse_rank(r.get("Round_Rank_In_Player_History_Gross"))
            gax, _gan = _parse_rank(r.get("Round_Rank_In_All_History_Gross"))
            g_has_history = gn is not None and gn >= 8
            g_note, g_rar, g_ent, g_imp = None, 1.0, 2.0, scoring.cap(2 + 3 * w)
            gross_score = int(r["Round_Score_Gross"])
            gross_score_str = f"{gross_score:+d}"
            if gax is not None and gax <= 3:
                label = {1: "the best", 2: "the 2nd-best", 3: "the 3rd-best"}[gax]
                g_note = f"{player}'s {gross_score_str} (gross) is {label} Gross round in TEG history to date"
                g_rar, g_ent = {1: 9.0, 2: 8.0, 3: 7.0}[gax], scoring.cap(7 + 2 * (1 - w))
            elif gx == 1 and g_has_history:
                g_note = f"{player} posts a personal-best Gross round: {gross_score_str}"
                g_rar, g_ent = 7.0, scoring.cap(6 + 2 * (1 - w))
            elif g_has_history and gx == gn and gn > 3:
                g_note = f"{player}'s worst Gross round to date: {gross_score_str}"
                g_rar, g_ent = 5.0, scoring.cap(5 + 2 * (1 - w))

            if g_note:
                out.append(NotableEvent(
                    teg_num=teg_num, scope="round", type="round_player_gross", round=rnd,
                    headline=g_note, players=[player],
                    importance=g_imp, rarity=g_rar, entertainment=g_ent,
                    context={"round_score_gross": gross_score, "metric": "gross"},
                ))
    return out


def _arc_top(rs, rank_col, gap_col, score_col, events_log, event_name, label, leader_counts) -> dict:
    """Trajectory of a 'highest/lowest wins' competition won from the top."""
    rounds = sorted(int(r) for r in rs["Round"].unique())
    leader_by_round = []
    for rnd in rounds:
        g = rs[rs["Round"] == rnd]
        leader = g.loc[g[rank_col].idxmin()]
        behind = g[g[rank_col] > 1]
        lead = int(behind[gap_col].min()) if not behind.empty else None
        leader_by_round.append({"round": rnd, "leader": leader["Player"], "lead": lead})

    winner = leader_by_round[-1]["leader"]
    traj = []
    for rnd in rounds:
        row = rs[(rs["Round"] == rnd) & (rs["Player"] == winner)].iloc[0]
        traj.append({"round": rnd, "pos": int(row[rank_col]),
                     "gap": int(row[gap_col]), "round_score": int(row[score_col])})

    lc = events_log[(events_log["Event"] == event_name)
                    & ~((events_log["Round"] == 1) & (events_log["Hole"] == 1))]
    lead_changes = []
    for _, r in lc.iterrows():
        rr, hh = int(r["Round"]), int(r["Hole"])
        lead_changes.append({"round": rr, "hole": hh, "player": r["Player"],
                             "outright": leader_counts.get((rr, hh), 1) <= 1})
    # Decisive = the last time the eventual winner took the lead OUTRIGHT (a draw-level
    # by a rival afterwards does not count as the winner losing the lead).
    winner_outright = [c for c in lead_changes if c["player"] == winner and c["outright"]]
    winner_any = [c for c in lead_changes if c["player"] == winner]
    decisive = winner_outright[-1] if winner_outright else (winner_any[-1] if winner_any else None)
    return {"label": label, "winner": winner, "leader_by_round": leader_by_round,
            "winner_trajectory": traj, "lead_changes": lead_changes,
            "n_lead_changes": len(lead_changes),
            "decisive_takeover": decisive}


def _arc_bottom(rs, rank_col, score_col, events_log, event_name, label) -> dict:
    """Trajectory of the wooden-spoon race (won by sinking to last)."""
    rounds = sorted(int(r) for r in rs["Round"].unique())
    bottom_by_round = []
    for rnd in rounds:
        g = rs[rs["Round"] == rnd]
        loser = g.loc[g[rank_col].idxmax()]
        bottom_by_round.append({"round": rnd, "bottom": loser["Player"], "pos": int(loser[rank_col])})

    loser = bottom_by_round[-1]["bottom"]
    traj = []
    for rnd in rounds:
        row = rs[(rs["Round"] == rnd) & (rs["Player"] == loser)].iloc[0]
        traj.append({"round": rnd, "pos": int(row[rank_col]), "round_score": int(row[score_col])})

    hb = events_log[events_log["Event"] == event_name]
    hits = [{"round": int(r["Round"]), "hole": int(r["Hole"]), "player": r["Player"]}
            for _, r in hb.iterrows()]
    loser_hits = [h for h in hits if h["player"] == loser]
    return {"label": label, "loser": loser, "bottom_by_round": bottom_by_round,
            "loser_trajectory": traj, "bottom_changes": hits, "n_bottom_changes": len(hits),
            "decisive_drop": loser_hits[-1] if loser_hits else None}


def _competition_arcs(round_summary: pd.DataFrame, events_log: pd.DataFrame,
                      teg_df: pd.DataFrame, metric: str = "stableford") -> dict:
    """How each competition was won/lost: leader-by-round, winner trajectory, swings.

    Era-aware: pre-8 TEGs use NetVP for the Trophy and Spoon; post-8 use Stableford.
    """
    cols = _trophy_cols(metric)
    trophy_label = _trophy_label(metric)
    rs = round_summary
    trophy_counts = _rank1_counts(teg_df, cols["rank_hole"])
    gr_counts = _rank1_counts(teg_df, "Rank_GrossVP_TEG")
    return {
        "trophy": _arc_top(rs, cols["cum_rank"],
                           cols["gap_after"], cols["round_score"],
                           events_log, cols["took_lead_event"], trophy_label, trophy_counts),
        "jacket": _arc_top(rs, "Cumulative_Tournament_Rank_Gross",
                           "Gap_To_Leader_After_Round_Gross", "Round_Score_Gross",
                           events_log, "Took Lead (Gross)", JACKET, gr_counts),
        "spoon": _arc_bottom(rs, cols["cum_rank"],
                             cols["round_score"],
                             events_log, cols["spoon_hit_event"], "Wooden Spoon"),
    }


def _tournament_beats(tsum: pd.DataFrame, arcs: dict, metric: str = "stableford") -> list:
    """Winners, margins, spoon, and tournament-level records/PBs.

    The three competition beats carry their full arc (how won/lost) in context; they
    are the report's spine, in priority order Trophy > Green Jacket > Wooden Spoon.

    Era-aware: pre-8 TEGs report the Trophy in net-vs-par (signed, lower wins);
    post-8 in Stableford (raw points, higher wins).
    """
    cols = _trophy_cols(metric)
    is_netvp = metric == "net_vs_par"
    score_col = cols["tournament_score"]
    out = []
    teg_num = int(tsum["TEGNum"].iloc[0])

    # Winner margins are the gap to the runner-up (the per-row Margin_* is gap-to-winner,
    # which is 0 for the winner themselves).
    by_trophy = tsum.sort_values(score_col, ascending=cols["score_ascending"]).reset_index(drop=True)
    by_jacket = tsum.sort_values("Tournament_Score_Gross", ascending=True).reset_index(drop=True)
    trophy = by_trophy.iloc[0]
    jacket = by_jacket.iloc[0]
    spoon = tsum[tsum["Wooden_Spoon"]].iloc[0]
    # For NetVP (lower wins): margin = runner_up - winner; for Stableford: winner - runner_up
    if is_netvp:
        trophy_margin = int(by_trophy.iloc[1][score_col] - trophy[score_col])
        trophy_score = int(trophy[score_col])
        trophy_headline = (f"{trophy['Player']} wins the Trophy at "
                           f"{trophy_score:+d}, by {trophy_margin}")
        spoon_score = int(spoon[score_col])
        spoon_headline = (f"{spoon['Player']} collects the Wooden Spoon "
                          f"({spoon_score:+d} net VP)")
    else:
        trophy_margin = int(trophy[score_col] - by_trophy.iloc[1][score_col])
        trophy_score = int(trophy[score_col])
        trophy_headline = (f"{trophy['Player']} wins the Trophy on "
                           f"{trophy_score} pts, by {trophy_margin}")
        spoon_score = int(spoon[score_col])
        spoon_headline = (f"{spoon['Player']} collects the Wooden Spoon "
                          f"({spoon_score} pts)")
    jacket_margin = int(by_jacket.iloc[1]["Tournament_Score_Gross"] - jacket["Tournament_Score_Gross"])

    out.append(NotableEvent(
        teg_num=teg_num, scope="tournament", type="trophy_win",
        headline=trophy_headline,
        players=[trophy["Player"]], importance=10.0,
        rarity=_tournament_rarity(trophy, metric), entertainment=5.0,
        context={"score": trophy_score,
                 "margin": trophy_margin,
                 "trophy_metric": metric,
                 "runner_up": by_trophy.iloc[1]["Player"],
                 "all_time_rank": _safe_int(trophy.get(cols["rank_all_tegs"])),
                 "player_rank": _safe_int(trophy.get(cols["rank_player_tegs"])),
                 "arc": arcs["trophy"]},
    ))
    jacket_all_rank = _safe_int(jacket.get("Rank_Among_All_TEGs_To_Date_Gross"))
    jacket_player_rank = _safe_int(jacket.get("Rank_Among_Player_TEGs_Gross"))
    out.append(NotableEvent(
        teg_num=teg_num, scope="tournament", type="jacket_win",
        headline=(f"{jacket['Player']} wins the Green Jacket at {int(jacket['Tournament_Score_Gross']):+d}, "
                  f"by {jacket_margin}"),
        players=[jacket["Player"]], importance=9.0,
        rarity=_jacket_rarity(jacket), entertainment=4.0,
        context={"score": int(jacket["Tournament_Score_Gross"]),
                 "margin": jacket_margin,
                 "runner_up": by_jacket.iloc[1]["Player"],
                 "all_time_rank": jacket_all_rank,
                 "player_rank": jacket_player_rank,
                 "metric": "gross",
                 "arc": arcs["jacket"]},
    ))

    # Player-best gross tournament total for any non-winner (the Jacket winner is
    # already covered above with the same context fields). Same rarity tier as
    # Trophy PBs so the LLM-bundle's `rarity >= 7` rule auto-marks these mandatory.
    for _, prow in tsum.iterrows():
        if prow["Player"] == jacket["Player"]:
            continue
        p_rank = _safe_int(prow.get("Rank_Among_Player_TEGs_Gross"))
        if p_rank != 1:
            continue
        p_score = int(prow["Tournament_Score_Gross"])
        out.append(NotableEvent(
            teg_num=teg_num, scope="tournament", type="jacket_pb",
            headline=f"{prow['Player']} posts a personal-best Gross total: {p_score:+d}",
            players=[prow["Player"]], importance=5.0, rarity=7.0, entertainment=4.0,
            context={"score": p_score, "player_rank": 1, "metric": "gross"},
        ))
    out.append(NotableEvent(
        teg_num=teg_num, scope="tournament", type="wooden_spoon",
        headline=spoon_headline,
        players=[spoon["Player"]], importance=5.0, rarity=3.0, entertainment=7.0,
        context={"score": spoon_score,
                 "trophy_metric": metric,
                 "arc": arcs["spoon"]},
    ))

    # rare feats across the field
    total_eagles = int(tsum["Total_Eagles"].sum())
    total_hio = int(tsum["Holes_In_One"].sum())
    if total_hio:
        out.append(NotableEvent(
            teg_num=teg_num, scope="tournament", type="feat_hole_in_one",
            headline=f"{total_hio} hole-in-one(s) recorded",
            players=[], importance=4.0, rarity=10.0, entertainment=9.0,
        ))
    if total_eagles:
        out.append(NotableEvent(
            teg_num=teg_num, scope="tournament", type="feat_eagles",
            headline=f"{total_eagles} eagle(s) across the field",
            players=[], importance=3.0, rarity=7.0, entertainment=6.0,
        ))
    return out


def _tournament_rarity(row, metric: str = "stableford") -> float:
    cols = _trophy_cols(metric)
    all_rank = _safe_int(row.get(cols["rank_all_tegs"]))
    player_rank = _safe_int(row.get(cols["rank_player_tegs"]))
    if all_rank == 1:
        return 10.0
    if player_rank == 1:
        return 7.0
    if all_rank is not None and all_rank <= 3:
        return 6.0
    return 4.0


def _jacket_rarity(row) -> float:
    """Gross-side equivalent of `_tournament_rarity`. Reads gross rank columns;
    drives auto-mandatory body coverage via the `rarity >= 7` rule in
    story_plan / round_report bundle assembly."""
    all_rank = _safe_int(row.get("Rank_Among_All_TEGs_To_Date_Gross"))
    player_rank = _safe_int(row.get("Rank_Among_Player_TEGs_Gross"))
    if all_rank == 1:
        return 10.0
    if player_rank == 1:
        return 7.0
    if all_rank is not None and all_rank <= 3:
        return 6.0
    return 4.0


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------
def build_notable_events(teg_num: int, all_data: Optional[pd.DataFrame] = None,
                         mode: str = "balanced") -> list:
    """Build the ranked list of NotableEvent objects for a TEG."""
    metric = trophy_metric(teg_num)

    if all_data is None:
        all_data = load_all_data(exclude_teg_50=True, exclude_incomplete_tegs=False)

    # Proper-case player names once, at the source, so every downstream artefact
    # (beats, arcs, plan, draft, report) reads "John Patterson", not "John PATTERSON".
    all_data = all_data.copy()
    all_data["Player"] = all_data["Player"].map(_proper)

    teg_df = all_data[all_data["TEGNum"] == teg_num].copy()
    if teg_df.empty:
        raise ValueError(f"No data for TEG {teg_num}")

    player_names = teg_df[["Pl", "Player"]].drop_duplicates().set_index("Pl")["Player"].to_dict()

    events_log = create_round_events(all_data_df=all_data)
    events_log = events_log[events_log["TEGNum"] == teg_num]

    round_summary = create_round_summary(all_data_df=all_data)
    round_summary = round_summary[round_summary["TEGNum"] == teg_num]

    tsum = create_tournament_summary(all_data_df=all_data)
    tsum = tsum[tsum["TEGNum"] == teg_num]

    # The teg_df we pass downstream needs the per-hole NetVP rank for
    # `_competition_arcs._rank1_counts(teg_df, "Rank_NetVP_TEG")` to work.
    from teg_analysis.analysis.commentary import _add_rank_netvp_teg
    teg_df = _add_rank_netvp_teg(teg_df)

    sw = _standing_weights(tsum, metric)
    arcs = _competition_arcs(round_summary, events_log, teg_df, metric)

    # Lifetime hole-level worst-gross lookups (across ALL TEGs / all players),
    # used by _sequences to flag big_blowup events that match a player's career
    # worst on this par class or the TEG-wide worst-ever on this par class. Ties
    # count (any score equal to the lifetime max satisfies the flag). The
    # current TEG is included, so a score that SETS a new record also passes.
    player_par_max = all_data.groupby(["Player", "PAR"])["Sc"].max().to_dict()
    par_max = all_data.groupby("PAR")["Sc"].max().to_dict()

    events = []
    events += _tournament_beats(tsum, arcs, metric)
    events += _turning_points(events_log, teg_df, sw, metric)
    events += _sequences(teg_df, sw, player_names,
                         player_par_max=player_par_max, par_max=par_max)
    events += _round_beats(round_summary, sw, metric)

    # Tag each round-scoped beat with the course it was played on, so the same hole
    # NUMBER in different rounds is never mistaken for "the same hole" (it is almost
    # always a different hole on a different course).
    round_course = teg_df.drop_duplicates("Round").set_index("Round")["Course"].to_dict()
    for e in events:
        if e.round is not None:
            e.course = round_course.get(e.round)

    return scoring.finalise(events, mode=mode)


# ---------------------------------------------------------------------------
# Inspection renderer (artefact for eyeballing selection quality)
# ---------------------------------------------------------------------------
def _fmt_evidence(holes: list) -> str:
    return ", ".join(
        f"H{h['hole']}(par {h['par']}) {h['sc']} = {h['result']}, {h['stableford']}pt"
        for h in holes
    )


def _render_arc_lines(arc: dict) -> list:
    L = [f"- **how the {arc['label']} was won/lost:**"]
    if "leader_by_round" in arc:
        seq = ", ".join(
            f"R{x['round']} {x['leader']}" + (f" (+{x['lead']})" if x["lead"] is not None else "")
            for x in arc["leader_by_round"])
        L.append(f"    - leader by round: {seq}")
        wt = ", ".join(f"R{x['round']} pos{x['pos']}/gap{x['gap']} ({x['round_score']})"
                       for x in arc["winner_trajectory"])
        L.append(f"    - {arc['winner']}: {wt}")
        L.append(f"    - lead changes ({arc['n_lead_changes']}): "
                 + (", ".join(f"R{c['round']}H{c['hole']} {c['player']}"
                              + ("" if c.get("outright", True) else " (level)")
                              for c in arc["lead_changes"]) or "none"))
        d = arc.get("decisive_takeover")
        if d:
            L.append(f"    - decisive: {arc['winner']} led for good from R{d['round']} H{d['hole']}")
    else:
        seq = ", ".join(f"R{x['round']} {x['bottom']}" for x in arc["bottom_by_round"])
        L.append(f"    - bottom by round: {seq}")
        lt = ", ".join(f"R{x['round']} pos{x['pos']} ({x['round_score']})" for x in arc["loser_trajectory"])
        L.append(f"    - {arc['loser']}: {lt}")
        d = arc.get("decisive_drop")
        if d:
            L.append(f"    - decisive: {arc['loser']} hit bottom for good at R{d['round']} H{d['hole']}")
    return L


def render_events_markdown(events: list, teg_num: int, top: Optional[int] = None) -> str:
    """Render the ranked events to markdown for inspection."""
    lines = [f"# TEG {teg_num} - Notable events (Stage 2 output)",
             "",
             f"Total beats detected: {len(events)}. "
             f"Columns: total | importance / rarity / entertainment.",
             ""]
    shown = events[:top] if top else events
    for e in shown:
        rnd = f"R{e.round}" if e.round else "TEG"
        lines.append(f"### [{e.total:.1f}] {e.headline}")
        venue = f" @ {e.course}" if e.course else ""
        lines.append(f"`{e.scope}/{e.type}` · {rnd}{venue} · "
                     f"imp {e.importance:.1f} / rar {e.rarity:.1f} / ent {e.entertainment:.1f}")
        if e.holes:
            lines.append(f"- evidence: {_fmt_evidence(e.holes)}")
        ctx = dict(e.context)
        arc = ctx.pop("arc", None)
        if arc:
            lines += _render_arc_lines(arc)
        ctx = {k: v for k, v in ctx.items() if v is not None}
        if ctx:
            lines.append(f"- context: {ctx}")
        lines.append("")
    return "\n".join(lines)
