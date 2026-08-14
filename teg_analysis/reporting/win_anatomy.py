"""Deterministic answer to "why did the champion win?".

The pipeline detects micro-events (holes, stretches, lead changes) and asks the
editor LLM to assemble a story from them. `competition_arcs` supplies the WHAT
— leader by round, lead changes, the decisive moment — but nothing supplies the
WHY. So causation was left to inference over a pile of beats, which is exactly
where "the champion was rubbish" creeps in: hand a model twenty disasters and
no causal spine, and it will narrate the disasters.

Jon's framing (2026-08-14), which this module implements literally:

    The most important thing is that we're clear WHY the champion won. Were
    they good — in a round, consistently, in all but one or two rounds? Were
    their competitors bad? Did someone blow a lead?

All of that is computable. What is NOT computable is which explanation is the
most interesting, so this module states facts in neutral language — the same
contract as `history_context.notable_milestones` — and the editor decides what
to foreground. Free, deterministic, no LLM call.
"""

from __future__ import annotations

from typing import Optional

import pandas as pd

from teg_analysis.reporting.era import trophy_metric


def _cols(metric: str) -> tuple:
    """(column, higher_is_better) for the Trophy/Spoon in this era."""
    return ("NetVP", False) if metric == "net_vs_par" else ("Stableford", True)


def _round_totals(teg_df: pd.DataFrame, col: str) -> pd.DataFrame:
    return teg_df.groupby(["Player", "Round"])[col].sum().unstack(fill_value=0)


def _label_round(value: float, field: pd.Series, higher: bool) -> str:
    """Where this round sat against the field: the writer's raw material for
    'was he good, or were they bad'."""
    best = field.max() if higher else field.min()
    median = field.median()
    if value == best:
        return "best in field"
    better_than_median = value > median if higher else value < median
    return "above field median" if better_than_median else "below field median"


def build_win_anatomy(teg_num: int, all_data: Optional[pd.DataFrame] = None) -> dict:
    """How each competition was actually won or lost.

    Returns {"trophy": {...}, "jacket": {...}, "spoon": {...}}, each carrying
    `summary_facts` — neutral phrases for the editor and writer to draw on.
    """
    from teg_analysis.core.data_loader import load_all_data

    if all_data is None:
        all_data = load_all_data(exclude_teg_50=True, exclude_incomplete_tegs=False)
    # Proper-case to match every other artefact ("Alex Baker", not "Alex BAKER").
    # Two name formats reaching the writer is how confabulated players start.
    from teg_analysis.reporting.events import _proper
    all_data = all_data.copy()
    all_data["Player"] = all_data["Player"].map(_proper)
    teg_df = all_data[all_data["TEGNum"] == teg_num]
    if teg_df.empty:
        raise ValueError(f"No data for TEG {teg_num}")

    metric = trophy_metric(teg_num)
    out = {}
    for name in ("trophy", "jacket", "spoon"):
        col, higher = ("GrossVP", False) if name == "jacket" else _cols(metric)
        out[name] = _anatomy(teg_df, col, higher, bottom=(name == "spoon"), label=name)
    return out


def _anatomy(teg_df: pd.DataFrame, col: str, higher: bool, bottom: bool,
             label: str) -> dict:
    totals = teg_df.groupby("Player")[col].sum().sort_values(ascending=not higher)
    if bottom:
        totals = totals.iloc[::-1]          # worst first — the Spoon race
    subject = totals.index[0]
    rival = totals.index[1] if len(totals) > 1 else None
    margin = abs(float(totals.iloc[0]) - float(totals.iloc[1])) if rival else 0.0

    per_round = _round_totals(teg_df, col)
    rounds = sorted(per_round.columns)

    # --- round-by-round: was the subject good, or was the field bad? ---
    breakdown, beat_rival, lost_to_rival = [], 0, 0
    for r in rounds:
        field = per_round[r]
        val = float(field.get(subject, 0))
        entry = {"round": int(r), "score": val,
                 "standing": _label_round(val, field, higher)}
        if rival is not None:
            rv = float(field.get(rival, 0))
            won = (val > rv) if higher else (val < rv)
            entry["vs_runner_up"] = round(val - rv, 1)
            beat_rival += int(won and val != rv)
            lost_to_rival += int((not won) and val != rv)
        breakdown.append(entry)

    best_rounds = sum(1 for b in breakdown if b["standing"] == "best in field")
    weak_rounds = sum(1 for b in breakdown if b["standing"] == "below field median")

    # --- built or inherited? Did the subject gain the margin, or did the rival
    # shed it? Answers "were they good or were their competitors bad". ---
    facts = []
    n = len(rounds)
    if rival is not None:
        if beat_rival >= n - 1:
            attribution = "built"
            facts.append(f"{subject} outscored {rival} in {beat_rival} of {n} rounds")
        elif beat_rival > lost_to_rival:
            attribution = "built"
            facts.append(f"{subject} outscored {rival} in {beat_rival} of {n} rounds, "
                         f"losing {lost_to_rival}")
        else:
            attribution = "inherited"
            facts.append(f"{rival} outscored {subject} in {lost_to_rival} of {n} rounds "
                         f"but still finished behind")
    else:
        attribution = "unopposed"

    if best_rounds:
        facts.append(f"{subject} posted the best round in the field {best_rounds} "
                     f"time{'s' if best_rounds != 1 else ''}")
    if weak_rounds:
        facts.append(f"{subject} was below the field median in {weak_rounds} "
                     f"round{'s' if weak_rounds != 1 else ''}")

    # --- consistency vs one big round ---
    subj_rounds = [b["score"] for b in breakdown]
    spread = max(subj_rounds) - min(subj_rounds) if subj_rounds else 0
    field_spread = float((per_round.max(axis=1) - per_round.min(axis=1)).median() or 0)
    shape = "consistent" if spread <= field_spread else "volatile"
    facts.append(f"{subject}'s round-to-round spread was {spread:.0f} "
                 f"({'narrower' if shape == 'consistent' else 'wider'} than the field median "
                 f"of {field_spread:.0f})")

    # --- could the rival have flipped it by playing their own average? ---
    flip = None
    if rival is not None:
        rv_rounds = per_round.loc[rival, rounds].astype(float)
        worst = rv_rounds.min() if higher else rv_rounds.max()
        avg = rv_rounds.mean()
        recovered = abs(avg - worst)
        flip = bool(recovered > margin)
        facts.append(
            f"had {rival} played their own average in their worst round instead, "
            f"they would {'have won' if flip else 'still have lost'} "
            f"({recovered:.0f} vs a margin of {margin:.0f})")

    return {
        "subject": subject,
        "runner_up": rival,
        "margin": round(margin, 1),
        "attribution": attribution,          # built | inherited | unopposed
        "shape": shape,                      # consistent | volatile
        "best_in_field_rounds": best_rounds,
        "below_median_rounds": weak_rounds,
        "rounds": breakdown,
        "rival_could_have_flipped_it": flip,
        "summary_facts": facts,
    }
