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


def _round_position(value: float, field: pd.Series, higher: bool) -> int:
    """1-based finishing position in that round. Plainer than a median
    comparison — "no worse than 3rd in any round" is a fact a reader pictures
    instantly; "never below the field median" is a statistic they have to
    decode (Jon, 2026-08-14)."""
    ordered = field.sort_values(ascending=not higher)
    return int(list(ordered.index).index(field.index[list(field).index(value)]) + 1) \
        if value in list(field) else len(field)


def _label_round(value: float, field: pd.Series, higher: bool) -> str:
    """Where this round sat against the field, in words a reader pictures.

    Said "above/below field median" until 2026-08-14, and that phrasing reached
    published prose — "Williams was below the field median in all four rounds".
    Every string in this module is raw material the writer copies, so statistical
    vocabulary anywhere in it ends up in the report.
    """
    best = field.max() if higher else field.min()
    median = field.median()
    if value == best:
        return "best in the field"
    better_than_median = value > median if higher else value < median
    return "top half of the field" if better_than_median else "bottom half of the field"


def _ordinal(n: int) -> str:
    if 10 <= n % 100 <= 20:
        return f"{n}th"
    return f"{n}{ {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th') }"


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


def _biggest_lead_blown(teg_df: pd.DataFrame, col: str, higher: bool,
                        winner: str) -> Optional[dict]:
    """The largest lead held at any hole by someone who did not go on to win,
    and the LAST hole at which they held it.

    Reported as "led by N as late as the 12th in round 4, and lost it" — the
    lateness is what makes it a story. Round-boundary snapshots miss the common
    case of a lead surrendered mid-round.
    """
    pivot = (teg_df.sort_values(["Round", "Hole"])
             .pivot_table(index=["Round", "Hole"], columns="Player", values=col,
                          aggfunc="sum")
             .sort_index())
    if pivot.empty or pivot.shape[1] < 2:
        return None
    cume = pivot.cumsum()

    # Only leads held in the SECOND HALF of the tournament count. Someone is
    # always fractionally ahead early on, and "led by 1 at the 4th hole of 72"
    # is not a lead thrown away — it is noise that reads as a story.
    positions = list(cume.index)
    halfway = len(positions) // 2

    best = None
    for i, ((rnd, hole), row) in enumerate(cume.iterrows()):
        if i < halfway:
            continue
        ordered = row.sort_values(ascending=not higher)
        leader = ordered.index[0]
        if leader == winner:
            continue
        margin = abs(float(ordered.iloc[0]) - float(ordered.iloc[1]))
        if margin <= 0:
            continue                     # level, not a lead
        # Prefer the biggest lead; break ties on the latest hole it was held.
        if best is None or margin > best["margin"] or (
                margin == best["margin"] and (rnd, hole) > (best["round"], best["hole"])):
            best = {"player": leader, "round": int(rnd), "hole": int(hole),
                    "margin": round(margin, 1)}
    return best


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
        ranked = field.sort_values(ascending=not higher)
        pos = int(list(ranked.index).index(subject) + 1) if subject in ranked.index else len(ranked)
        entry = {"round": int(r), "score": val, "position": pos,
                 "standing": _label_round(val, field, higher)}
        if rival is not None:
            rv = float(field.get(rival, 0))
            won = (val > rv) if higher else (val < rv)
            entry["vs_runner_up"] = round(val - rv, 1)
            beat_rival += int(won and val != rv)
            lost_to_rival += int((not won) and val != rv)
        breakdown.append(entry)

    best_rounds = sum(1 for b in breakdown if b["standing"] == "best in the field")
    weak_rounds = sum(1 for b in breakdown if b["standing"] == "bottom half of the field")
    worst_pos = max(b["position"] for b in breakdown) if breakdown else 0
    field_size = len(per_round.index)

    # --- built or inherited? Did the subject gain the margin, or did the rival
    # shed it? Answers "were they good or were their competitors bad". ---
    # PLAIN ENGLISH ONLY. These strings get copied more or less verbatim into
    # the prose, so statistical phrasing ends up in the report — TEG 12 shipped
    # "a round-to-round spread of 5 against a field median of 8", which is a
    # statistic the reader has to decode rather than a picture (Jon,
    # 2026-08-14). Say "won two of the four rounds outright" and "never worse
    # than 3rd"; the raw numbers stay available in the structured fields below
    # for anyone who wants them.
    facts = []
    n = len(rounds)
    last_rounds = sum(1 for b in breakdown if b["position"] == field_size)

    if bottom:
        # The Spoon is a race to the bottom, so every phrase above inverts.
        # Left un-inverted until 2026-08-14, which produced nonsense in the
        # published plans: "Williams never finished a round worse than 5th of
        # 5", and "Meller outplayed Williams and still lost" — backwards, since
        # here `rival` is the man who ESCAPED the Spoon.
        if rival is not None:
            if lost_to_rival >= beat_rival:
                attribution = "built"
                facts.append(f"{subject} was worse than {rival} in "
                             f"{lost_to_rival} of the {n} rounds")
            else:
                attribution = "inherited"
                facts.append(f"{subject} actually outscored {rival} in "
                             f"{beat_rival} of the {n} rounds and took the Spoon anyway")
            facts.append(f"{subject} finished {margin:.0f} adrift of {rival}, "
                         f"the next worst")
        else:
            attribution = "unopposed"
        if last_rounds:
            facts.append(f"{subject} was last in the field in {last_rounds} "
                         f"of the {n} rounds")
    else:
        if rival is not None:
            if beat_rival > lost_to_rival:
                attribution = "built"
                facts.append(f"{subject} beat {rival} head-to-head in "
                             f"{beat_rival} of the {n} rounds")
            else:
                attribution = "inherited"
                facts.append(f"{rival} actually outplayed {subject} over "
                             f"{lost_to_rival} of the {n} rounds and still lost")
        else:
            attribution = "unopposed"

        if best_rounds:
            facts.append(f"{subject} won {best_rounds} of the {n} rounds outright")
        if worst_pos:
            facts.append(f"{subject} never finished a round worse than "
                         f"{_ordinal(worst_pos)} of {field_size}")

    # --- consistency vs one big round ---
    subj_rounds = [b["score"] for b in breakdown]
    spread = max(subj_rounds) - min(subj_rounds) if subj_rounds else 0
    spreads = (per_round.max(axis=1) - per_round.min(axis=1)).sort_values()
    consistency_rank = int(list(spreads.index).index(subject) + 1) \
        if subject in spreads.index else field_size
    shape = "consistent" if consistency_rank <= max(field_size // 2, 1) else "volatile"
    if consistency_rank == 1:
        facts.append(f"{subject} was the steadiest man in the field, "
                     f"round to round")
    elif shape == "consistent":
        facts.append(f"{subject} was steadier round to round than most of the field")
    else:
        facts.append(f"{subject} swung about more between rounds than most of the field")

    # --- the biggest lead anyone threw away ---
    # Jon (2026-08-14): TEG 4's missing fact was the SIZE of the lead Baker
    # blew. Computed HOLE BY HOLE, not at round boundaries: Baker led TEG 4
    # from R1 through the 12th of R4 and lost it there, which a per-round
    # snapshot misses entirely.
    # Not for the Spoon: `_biggest_lead_blown` looks for whoever was LEADING and
    # is not the subject, which in a Spoon section is the tournament leader —
    # producing "Alex Baker led by 15 and lost it" inside a paragraph about who
    # came last. A wrong fact is worse than a missing one. The mirror ("X was
    # heading for the Spoon until the 15th and escaped") would be a real
    # addition; it is not this function.
    blown = None if bottom else _biggest_lead_blown(teg_df, col, higher, subject)
    if blown:
        facts.append(
            f"{blown['player']} led by {blown['margin']:.0f} as late as the "
            f"{_ordinal(blown['hole'])} in round {blown['round']}, and lost it")

    # --- could it have gone the other way on one ordinary round? ---
    # For a competition, that question is about the RUNNER-UP: could they have
    # caught the winner. For the Spoon it is about the HOLDER: could they have
    # escaped it. Asking it of `rival` in both cases was the same inversion bug.
    flip = None
    who = subject if bottom else rival
    if who is not None:
        rr = per_round.loc[who, rounds].astype(float)
        worst = rr.min() if higher else rr.max()
        recovered = abs(rr.mean() - worst)
        flip = bool(recovered > margin)
        if bottom:
            facts.append(
                f"even with an ordinary round instead of their worst, {subject} "
                f"would {'have escaped the Spoon' if flip else 'still have taken the Spoon'}")
        else:
            facts.append(
                f"even with an ordinary round instead of their worst, {who} would "
                f"{'have won' if flip else 'still have lost'}")

    return {
        "worst_round_position": worst_pos,
        "field_size": field_size,
        "consistency_rank": consistency_rank,
        "biggest_lead_blown": blown,
        "subject": subject,
        "runner_up": rival,
        "margin": round(margin, 1),
        "attribution": attribution,          # built | inherited | unopposed
        "shape": shape,                      # consistent | volatile
        "best_in_field_rounds": best_rounds,
        "rounds_in_bottom_half": weak_rounds,
        "rounds": breakdown,
        "rival_could_have_flipped_it": flip,
        "summary_facts": facts,
    }
