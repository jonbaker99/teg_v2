"""Per-player per-course history for report bundle enrichment.

`build_player_course_history(teg_num)` returns, for each player in the current
TEG and each course they played, factual history relative to their prior visits
to that course: visit count, personal best, strokes vs last visit, whether
this TEG produced a new course PB. Surfaced in the bundle as
`player_course_history[player][course] = {...}`.

`detect_course_records(teg_num)` returns NEW course gross records (good or bad)
set during this TEG, restricted to courses with >= min_prior_visits prior
appearances across all TEGs. These should be wired into the bundle's beats
list with `mandatory=True` so the writer cannot skip them.

Both functions are parametric over `teg_num`: when TEG 19 data lands, they
produce TEG 19 history automatically. No hardcoding.
"""

from __future__ import annotations

from typing import Optional

import pandas as pd


def _proper(name: str) -> str:
    """'Alex BAKER' -> 'Alex Baker'."""
    return " ".join(w.capitalize() for w in name.split())


def _round_aggregates(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate hole-level rows to per (TEG, Round, Player, Course) totals."""
    return df.groupby(["TEGNum", "Round", "Player", "Course"], dropna=False).agg(
        Gross=("Sc", "sum"),
        GrossVP=("GrossVP", "sum"),
        Stableford=("Stableford", "sum"),
    ).reset_index()


def build_player_course_history(teg_num: int, df: Optional[pd.DataFrame] = None,
                                through_round: Optional[int] = None) -> dict:
    """Per-player per-course history relative to prior TEGs.

    Returns a dict keyed by proper-case player name; each value is a dict keyed
    by course name; each entry is a fact dict suitable for the bundle.

    For each (player, course) in this TEG:
        - `visit_count_through_this_teg`: total visits to this course including
          rounds in this TEG (1 = first ever)
        - `n_prior_visits`: rounds on this course strictly before this TEG
        - `prior_best_gross` / `prior_best_teg`: PB on this course before this TEG
        - `this_teg_best_gross` / `this_teg_best_round`: best round on this course
          in this TEG (lowest gross across the player's rounds on this course)
        - `strokes_vs_last_visit`: gross delta of this TEG's best vs the player's
          most recent prior visit (negative = better)
        - `is_course_pb_this_teg`: True if this TEG's best beats prior_best_gross
        - `summary_facts`: list of factual phrases the editor/writer can use
          verbatim as anchors — neutral, factual, no flourish

    `through_round`: when given, scopes "this TEG" to rounds `<= through_round`
    of `teg_num` and "prior" to rounds strictly before `(teg_num, through_round)`
    — i.e. earlier TEGs OR earlier rounds of THIS TEG. Without it (the tournament
    default), "this TEG" is every round of `teg_num` and "prior" is only earlier
    TEGs, which is correct once the TEG is complete but a leak for a mid-
    tournament round report (a TEG-4 course best set in R4 would surface in the
    R2 report). Round callers MUST pass `through_round=round_num`.
    """
    if df is None:
        from teg_analysis.core.data_loader import load_all_data
        df = load_all_data()

    rounds = _round_aggregates(df)
    current = rounds[rounds["TEGNum"] == teg_num]
    if through_round is not None:
        current = current[current["Round"] <= through_round]
    if current.empty:
        return {}

    out: dict = {}

    # Iterate over unique (player, course) pairs in the current TEG
    for (player, course), group in current.groupby(["Player", "Course"]):
        # Player's best round on this course IN this TEG (bounded by through_round)
        best_row = group.loc[group["Gross"].idxmin()]
        this_teg_best_gross = int(best_row["Gross"])
        this_teg_best_round = int(best_row["Round"])

        # Player's prior visits to this course: earlier TEGs, plus (when
        # through_round is set) earlier rounds of THIS TEG on the same course.
        if through_round is not None:
            prior = rounds[
                (rounds["Player"] == player)
                & (rounds["Course"] == course)
                & ((rounds["TEGNum"] < teg_num)
                   | ((rounds["TEGNum"] == teg_num) & (rounds["Round"] < through_round)))
            ].sort_values(["TEGNum", "Round"])
        else:
            prior = rounds[
                (rounds["Player"] == player)
                & (rounds["Course"] == course)
                & (rounds["TEGNum"] < teg_num)
            ].sort_values(["TEGNum", "Round"])

        n_prior = len(prior)
        visit_count_through = n_prior + len(group)

        prior_best_gross: Optional[int] = None
        prior_best_teg: Optional[int] = None
        strokes_vs_last_visit: Optional[int] = None
        is_pb = False

        if n_prior > 0:
            best_prior_idx = prior["Gross"].idxmin()
            prior_best_gross = int(prior.loc[best_prior_idx, "Gross"])
            prior_best_teg = int(prior.loc[best_prior_idx, "TEGNum"])
            last_visit_gross = int(prior.iloc[-1]["Gross"])
            strokes_vs_last_visit = this_teg_best_gross - last_visit_gross
            is_pb = this_teg_best_gross < prior_best_gross

        # Best from an EARLIER round of THIS SAME TEG on this course, if any —
        # distinct from `prior_best_gross` (earlier TEGs only). Without this, a
        # "previous best" claim about `this_teg_best_round` can silently ignore
        # a better (or equal) round played earlier in the same TEG at the same
        # course (real case: TEG 18's Williams R4 84 was compared only against
        # cross-TEG history, ignoring his own 85 at the same course in R3).
        earlier_this_teg = group[group["Round"] < this_teg_best_round]
        best_earlier_this_teg: Optional[int] = None
        best_earlier_this_teg_round: Optional[int] = None
        if not earlier_this_teg.empty:
            idx = earlier_this_teg["Gross"].idxmin()
            best_earlier_this_teg = int(earlier_this_teg.loc[idx, "Gross"])
            best_earlier_this_teg_round = int(earlier_this_teg.loc[idx, "Round"])

        facts: list[str] = []
        player_proper = _proper(player)

        if n_prior == 0:
            facts.append(f"{player_proper}'s first visit to {course}")
        else:
            # Visit ordinal — only foreground when the venue is well-established
            if n_prior >= 2:
                facts.append(
                    f"{player_proper}'s {_ordinal(n_prior + 1)} visit to {course}"
                )

            if prior_best_gross is not None:
                facts.append(
                    f"{player_proper}'s prior best at {course}: {prior_best_gross} gross "
                    f"(TEG {prior_best_teg})"
                )

            if is_pb:
                facts.append(
                    f"{player_proper}'s new personal best at {course} in R{this_teg_best_round}: "
                    f"{this_teg_best_gross} gross — improved by "
                    f"{prior_best_gross - this_teg_best_gross}"
                )

            if strokes_vs_last_visit is not None and abs(strokes_vs_last_visit) >= 5:
                # Only flag meaningful deltas (>= 5 shots)
                direction = "better" if strokes_vs_last_visit < 0 else "worse"
                facts.append(
                    f"{player_proper} was {abs(strokes_vs_last_visit)} shots {direction} "
                    f"than his last visit to {course}"
                )

        entry = {
            "course": course,
            "visit_count_through_this_teg": visit_count_through,
            "n_prior_visits": n_prior,
            "prior_best_gross": prior_best_gross,
            "prior_best_teg": prior_best_teg,
            "this_teg_best_gross": this_teg_best_gross,
            "this_teg_best_round": this_teg_best_round,
            "strokes_vs_last_visit": strokes_vs_last_visit,
            "is_course_pb_this_teg": is_pb,
            "best_earlier_this_teg": best_earlier_this_teg,
            "best_earlier_this_teg_round": best_earlier_this_teg_round,
            "summary_facts": facts,
        }

        out.setdefault(player_proper, {})[course] = entry

    return out


def detect_course_records(
    teg_num: int,
    df: Optional[pd.DataFrame] = None,
    min_prior_visits: int = 3,
    through_round: Optional[int] = None,
) -> list[dict]:
    """Detect new gross course records (good or bad) set during this TEG.

    A new record only "counts" if the course has been played at least
    `min_prior_visits` times across all TEGs before this one — otherwise
    the sample is too small for a "record" to be meaningful.

    `through_round`: when given, "this TEG" is bounded to rounds `<= through_round`
    and "prior" includes earlier rounds of THIS TEG on the same course, not just
    earlier TEGs — see `build_player_course_history` for why this matters for a
    mid-tournament round report. Round callers MUST pass `through_round=round_num`.

    Returns a list of beat-shaped dicts the bundle assembler can merge
    into the events list with mandatory=True:
        {
            "type": "course_record_low" | "course_record_high"
                    | "course_record_equalled" | "course_record_high_equalled",
            "player": str (proper case),
            "course": str,
            "round": int,
            "gross": int,
            "prior_record": int,
            "n_prior_visits": int,
            "summary_fact": str,
            # equalled types only: who shot the record being equalled, in
            # play order — earlier TEGs and earlier cards of this TEG
            "record_holders": [{"player", "teg", "round"}, ...],
        }

    Walks this TEG's rounds on each course **in order**, against a running
    best that starts at the prior (cross-TEG) record. A later round is
    therefore compared with an earlier round of the SAME TEG, not just with
    history before this TEG started — and a round that exactly matches the
    running best emits an "equalled" event rather than nothing. Both were real
    gaps: TEG 18's Williams shot an 84 at the Stadium course in R4 that
    equalled Mullin's 84 there in R3 of the *same* TEG, and the strict `<`/`>`
    comparison meant neither the equalling nor the same-TEG comparison ever
    surfaced.
    """
    if df is None:
        from teg_analysis.core.data_loader import load_all_data
        df = load_all_data()

    rounds = _round_aggregates(df)
    events: list[dict] = []

    for course, group in rounds.groupby("Course"):
        if through_round is not None:
            prior = group[(group["TEGNum"] < teg_num)
                          | ((group["TEGNum"] == teg_num) & (group["Round"] < through_round))]
            current = group[(group["TEGNum"] == teg_num) & (group["Round"] <= through_round)]
        else:
            prior = group[group["TEGNum"] < teg_num]
            current = group[group["TEGNum"] == teg_num]
        if len(prior) < min_prior_visits or current.empty:
            continue

        n_prior = len(prior)
        running_min = int(prior["Gross"].min())
        running_max = int(prior["Gross"].max())

        def _holders(g: int) -> list:
            return [{"player": _proper(r["Player"]), "teg": int(r["TEGNum"]),
                     "round": int(r["Round"])}
                    for _, r in prior[prior["Gross"] == g]
                    .sort_values(["TEGNum", "Round"]).iterrows()]

        min_holders = _holders(running_min)
        max_holders = _holders(running_max)

        for _, row in current.sort_values("Round").iterrows():
            gross = int(row["Gross"])
            player = _proper(row["Player"])
            rnd = int(row["Round"])

            if gross < running_min:
                events.append({
                    "type": "course_record_low", "player": player, "course": course,
                    "round": rnd, "gross": gross, "prior_record": running_min,
                    "improvement": running_min - gross, "n_prior_visits": n_prior,
                    "summary_fact": (
                        f"new {course} course record: {gross} gross by {player} in "
                        f"R{rnd}, beating the prior record of {running_min} "
                        f"(across {n_prior} prior visits)"
                    ),
                })
                running_min = gross
                min_holders = []
            elif gross == running_min:
                events.append({
                    "type": "course_record_equalled", "player": player, "course": course,
                    "round": rnd, "gross": gross, "prior_record": running_min,
                    "n_prior_visits": n_prior, "record_holders": list(min_holders),
                    "summary_fact": (
                        f"{player} equals the {course} course record of {gross} gross "
                        f"in R{rnd} (across {n_prior} prior visits)"
                    ),
                })

            if gross > running_max:
                events.append({
                    "type": "course_record_high", "player": player, "course": course,
                    "round": rnd, "gross": gross, "prior_record": running_max,
                    "n_prior_visits": n_prior,
                    "summary_fact": (
                        f"new {course} course-worst: {gross} gross by {player} in "
                        f"R{rnd}, exceeding the prior worst of {running_max} "
                        f"(across {n_prior} prior visits)"
                    ),
                })
                running_max = gross
                max_holders = []
            elif gross == running_max:
                events.append({
                    "type": "course_record_high_equalled", "player": player, "course": course,
                    "round": rnd, "gross": gross, "prior_record": running_max,
                    "n_prior_visits": n_prior, "record_holders": list(max_holders),
                    "summary_fact": (
                        f"{player} equals the {course} course-worst of {gross} gross "
                        f"in R{rnd} (across {n_prior} prior visits)"
                    ),
                })

            card = {"player": player, "teg": teg_num, "round": rnd}
            if gross == running_min:
                min_holders.append(card)
            if gross == running_max:
                max_holders.append(card)

    return events


def _ordinal(n: int) -> str:
    if 10 <= n % 100 <= 20:
        suf = "th"
    else:
        suf = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suf}"
