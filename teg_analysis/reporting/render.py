"""Stage 5a: apply CSS-class styling to a final report so it renders styled in
the streamlit UI via `streamlit/styles/teg_reports.css`.

The writer emits clean prose markdown (title H1 + per-round H2 sections + a
close). This module adds the styling hooks the existing CSS expects:
- `{.report-title}` on the H1
- a `<p class="dateline">` after the H1
- a `<section class="callout at-a-glance-box">` with Trophy / Jacket / Spoon winners
- `{.roundN .round}` on each `## Round N ...` heading

Idempotent: re-running on already-styled text is a no-op (existing hooks are detected).
"""

from __future__ import annotations

import re
from typing import Optional

from teg_analysis.reporting.venue import build_venue_context

from teg_analysis.reporting.paths import output_dir


# ---------------------------------------------------------------------------
# Per-round standings (deterministic; no LLM)
# ---------------------------------------------------------------------------
def _fmt_signed(n: int) -> str:
    """Signed integer with no sign for zero."""
    return "0" if n == 0 else f"{n:+d}"


def build_round_standings(teg_num: int) -> dict:
    """Build per-round Trophy + Green Jacket standings markdown blocks for a TEG.

    Returns {round_num: standings_markdown}. Pure data — uses cumulative totals
    from `create_round_summary`; no LLM, no fabrication risk. The final round's
    order is override-aware (`analysis.history.get_teg_placings`), so it agrees
    with the at-a-glance box and `/history` on a tiebreak decided off-course.
    """
    from teg_analysis.analysis.commentary import create_round_summary
    from teg_analysis.analysis.history import get_teg_placings
    from teg_analysis.core.data_loader import load_all_data
    from teg_analysis.reporting.era import trophy_metric
    from teg_analysis.reporting.venue import build_venue_context
    rs = create_round_summary()
    rs = rs[rs["TEGNum"] == teg_num].copy()

    metric = trophy_metric(teg_num)
    if metric == "net_vs_par":
        trophy_col = "Cumulative_Tournament_Score_NetVP"
        trophy_round_col = "Round_Score_NetVP"
        trophy_ascending = True
        trophy_fmt = lambda x: _fmt_signed(int(x))
    else:
        trophy_col = "Cumulative_Tournament_Score_Stableford"
        trophy_round_col = "Round_Score_Stableford"
        trophy_ascending = False
        trophy_fmt = lambda x: str(int(x))

    # The final round's placing is the one a tiebreak override
    # (`analysis.history.TEG_OVERRIDES`) can correct — e.g. TEG 5's Green
    # Jacket, decided off-course. Mid-tournament rounds are never overridden:
    # the ruling is about the season result, not a round in progress.
    total_rounds = len(build_venue_context(teg_num).get("rounds", []))
    placings = get_teg_placings(load_all_data(), teg_num) if total_rounds else None

    def _reorder(rdf, order: list):
        """Rows of `rdf` in `order` (a list of 'Player' names, best to worst)."""
        rank = {player: i for i, player in enumerate(order)}
        return rdf.assign(_rank=rdf["Player"].map(rank)).sort_values("_rank")

    out: dict = {}
    for rnd in sorted(int(r) for r in rs["Round"].unique()):
        rdf = rs[rs["Round"] == rnd]
        is_final = placings is not None and rnd == total_rounds
        if is_final:
            trophy = _reorder(rdf, placings["trophy"])
            jacket = _reorder(rdf, placings["jacket"])
        else:
            # Tie-break on player code so the order is deterministic. A bare
            # single-column sort_values uses quicksort, which is NOT stable, so
            # tied players came out in arbitrary order and re-running style_report
            # produced a spurious diff — despite Stage 5 being documented as
            # idempotent and free to re-run.
            trophy = rdf.sort_values([trophy_col, "Pl"],
                                     ascending=[trophy_ascending, True])
            jacket = rdf.sort_values(["Cumulative_Tournament_Score_Gross", "Pl"],
                                     ascending=[True, True])

        # Cumulative total, with the round's OWN score alongside it. The
        # standings alone answer "who is winning" but not "who had a good day",
        # and a reader reconstructing the tournament wants both. Round 1 is the
        # exception: there the cumulative total IS the round score, so the
        # bracket would repeat the number it follows.
        def _entry(r, cum_col, round_col, fmt) -> str:
            cum = fmt(r[cum_col])
            if rnd == 1:
                return f"{r['Pl']} {cum}"
            return f"{r['Pl']} {cum} (R{rnd}: {fmt(r[round_col])})"

        trophy_str = " | ".join(
            _entry(r, trophy_col, trophy_round_col, trophy_fmt)
            for _, r in trophy.iterrows()
        )
        jacket_str = " | ".join(
            _entry(r, "Cumulative_Tournament_Score_Gross", "Round_Score_Gross",
                   lambda x: _fmt_signed(int(x)))
            for _, r in jacket.iterrows()
        )
        out[rnd] = (
            f'<p class="standings"><span class="standings-header">Trophy Standings:</span>'
            f' {trophy_str}</p>\n'
            f'<p class="standings"><span class="standings-header">Green Jacket Standings:</span>'
            f' {jacket_str}</p>'
        )
    return out


def _inject_standings(text: str, standings: dict) -> str:
    """Insert per-round standings. Two modes:

    - If the report uses `## Round N` headings: inject each round's standings at
      the end of its section (immediately before the next `## ` heading, or EOF).
    - Otherwise (theme-led report with no Round-N markers): insert a single
      `## Standings by round` appendix listing every round, just before the
      player-closing section (`## The men …` / `## Players` …) or at EOF.

    Idempotent — skip if `class="standings"` is already present.
    """
    if not standings:
        return text
    if 'class="standings"' in text:
        return text  # already injected

    has_round_headings = bool(re.search(r"^## Round \d+\b", text, flags=re.MULTILINE))
    if has_round_headings:
        return _inject_standings_per_round(text, standings)
    return _inject_standings_appendix(text, standings)


def _inject_standings_per_round(text: str, standings: dict) -> str:
    lines = text.splitlines(keepends=True)
    result = []
    current_round = None
    for line in lines:
        m_round = re.match(r"^## Round (\d+)\b", line)
        m_h2 = re.match(r"^## ", line)
        if m_round:
            if current_round is not None and current_round in standings:
                result.append("\n" + standings[current_round] + "\n\n")
            current_round = int(m_round.group(1))
            result.append(line)
        elif m_h2 and current_round is not None:
            if current_round in standings:
                result.append("\n" + standings[current_round] + "\n\n")
            current_round = None
            result.append(line)
        else:
            result.append(line)
    if current_round is not None and current_round in standings:
        result.append("\n" + standings[current_round] + "\n")
    return "".join(result)


def _inject_standings_appendix(text: str, standings: dict) -> str:
    """Build a single `## Standings by round` block listing every round, and
    insert it before the player-closing section (`## The men …` / `## Players` …)
    or at EOF if no such section exists."""
    blocks = []
    for rnd in sorted(standings):
        blocks.append(f"**End of Round {rnd}**\n\n{standings[rnd]}")
    appendix = "## Standings by round\n\n" + "\n\n".join(blocks) + "\n"

    # Find the player-closing section heading (first match of common patterns).
    pattern = re.compile(r"^## (?:The men|Players?\b|The week in players)", re.MULTILINE)
    m = pattern.search(text)
    if m:
        idx = m.start()
        return text[:idx] + appendix + "\n" + text[idx:]
    # No closing section found — append at end.
    sep = "" if text.endswith("\n") else "\n"
    return text + sep + "\n" + appendix


# ---------------------------------------------------------------------------
# Heading classes
# ---------------------------------------------------------------------------
def _add_report_title_class(text: str) -> str:
    """Append `{.report-title}` to the first H1 (no-op if already tagged)."""
    def repl(m):
        line = m.group(0)
        if "{.report-title" in line:
            return line
        return f"{line.rstrip()} {{.report-title}}"
    return re.sub(r"^# [^\n]+$", repl, text, count=1, flags=re.MULTILINE)


def _add_round_classes(text: str) -> str:
    """Tag each '## Round N ...' heading with `{.roundN .round}`."""
    def repl(m):
        heading = m.group(0)
        if "{.round" in heading:
            return heading
        n = int(m.group(1))
        return f"{heading.rstrip()} {{.round{n} .round}}"
    return re.sub(r"^## Round (\d+)[^\n]*$", repl, text, flags=re.MULTILINE)


# ---------------------------------------------------------------------------
# Dateline + at-a-glance callout
# ---------------------------------------------------------------------------
def _build_dateline(venue: dict) -> str:
    teg = venue.get("teg_num")
    area = venue.get("area", "")
    year = venue.get("year", "")
    return f'<p class="dateline">TEG {teg} | {area} | {year}</p>'


def _nth_suffix(n: int) -> str:
    """'1st', '2nd', '3rd', '4th', … for win-count annotations."""
    if 10 <= n % 100 <= 20:
        suf = "th"
    else:
        suf = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suf}"


def _build_at_a_glance(teg_num: int, win_counts: Optional[dict] = None,
                       df=None) -> str:
    """Build the at-a-glance callout: winner + running win-count, nothing else.

    Computed directly from scores via `analysis.history.get_teg_placings`
    (override-aware — a tiebreak decided off-course, e.g. TEG 5's Green
    Jacket, comes out right) rather than from the LLM plan's free-text
    `winner_or_loser` field, which used to carry ad hoc score/margin prose
    that varied report to report — only 4 of 17 TEGs even carried the
    win-count annotation. Jon's call, 2026-09-12: the box says the same three
    things every time — winner, their win count, nothing about the score or
    the margin. The runner-up is not rendered here: it comes from the
    Standings appendix table via `newspaper_edition._add_runners_up`.

    `win_counts` is a dict {player_name: {"trophy_wins": N, "jacket_wins": N,
    "spoon_count": N}} covering all TEGs through the current one — keys and
    the players returned by `get_teg_placings` are both the raw
    all-caps-surname format, so no case-insensitive lookup is needed here
    unlike the old plan-text version.
    """
    from teg_analysis.analysis.history import get_teg_placings
    from teg_analysis.reporting.events import _proper

    if df is None:
        from teg_analysis.core.data_loader import load_all_data
        df = load_all_data()

    placings = get_teg_placings(df, teg_num)
    trophy, jacket = placings["trophy"], placings["jacket"]
    if not trophy or not jacket:
        return ""
    spoon_loser = trophy[-1]

    def _suffix(player: str, key: str) -> str:
        if not win_counts:
            return ""
        n = win_counts.get(player, {}).get(key, 0)
        if n == 0:
            return ""
        label = {"trophy_wins": "Trophy", "jacket_wins": "Jacket", "spoon_count": "Spoon"}[key]
        return f" ({_nth_suffix(n)} {label})"

    trophy_winner, jacket_winner = trophy[0], jacket[0]
    lines = [
        '<section class="callout at-a-glance-box">',
        '  <p class="at-a-glance-title">RESULTS</p>',
        f'  <p><strong>Trophy Winner:</strong>'
        f'<span class="trophy-winner"> {_proper(trophy_winner)}'
        f'{_suffix(trophy_winner, "trophy_wins")}</span></p>',
        f'  <p><strong>Green Jacket:</strong> {_proper(jacket_winner)}'
        f'{_suffix(jacket_winner, "jacket_wins")}</p>',
        f'  <p><strong>Wooden Spoon:</strong> {_proper(spoon_loser)}'
        f'{_suffix(spoon_loser, "spoon_count")}</p>',
        "</section>",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Public entry points
# ---------------------------------------------------------------------------
def apply_styling(text: str, teg_num: int, venue: dict,
                  standings: Optional[dict] = None,
                  win_counts: Optional[dict] = None) -> str:
    """Apply CSS-class hooks + dateline + at-a-glance callout + per-round standings.

    `win_counts` is passed to `_build_at_a_glance` to annotate wins with ordinal
    suffixes, e.g. "(2nd Jacket)".  Idempotent: existing hooks are not duplicated.
    """
    text = _add_report_title_class(text)
    text = _add_round_classes(text)

    # Insert dateline + callout right after the styled H1 (once).
    if 'class="dateline"' not in text and 'class="at-a-glance-box"' not in text:
        dateline = _build_dateline(venue)
        callout = _build_at_a_glance(teg_num, win_counts=win_counts)
        block = f"\n\n{dateline}\n\n{callout}\n"
        # The H1 has just been tagged with {.report-title}; anchor on that.
        text = re.sub(
            r"^(# [^\n]+\{\.report-title\})\s*$",
            lambda m: m.group(1) + block,
            text, count=1, flags=re.MULTILINE,
        )

    if standings:
        text = _inject_standings(text, standings)
    return text


def _append_records(text: str, records_block: str) -> str:
    """Append a PBs/Records appendix to the end of the report (idempotent)."""
    if not records_block:
        return text
    if 'class="records"' in text:
        return text
    sep = "" if text.endswith("\n") else "\n"
    return text + sep + "\n" + records_block + "\n"


_ROUND_SUFFIX_RE = re.compile(r"\s*\(R(\d+)\)\s*$")


def _dedup_entries(entries: list[str]) -> list[str]:
    """Deduplicate entries, combining round suffixes (ascending) when the base
    text is the same.

    E.g. "Baker posts a personal-best round: 44 pts (R2)" and the same for (R4)
    become "Baker posts a personal-best round: 44 pts (R2, R4)" — always in
    round order, regardless of which order the source events arrived in.
    """
    seen: dict[str, list[int]] = {}   # base_lower -> [round numbers]
    bases: dict[str, str] = {}        # base_lower -> original-cased base text
    order: list[str] = []             # insertion order of base keys
    for e in entries:
        e = e.strip()
        m = _ROUND_SUFFIX_RE.search(e)
        base, rnd = (e[: m.start()], int(m.group(1))) if m else (e, None)
        key = base.lower()
        if key not in seen:
            seen[key] = []
            bases[key] = base
            order.append(key)
        if rnd is not None and rnd not in seen[key]:
            seen[key].append(rnd)

    out = []
    for key in order:
        rounds = sorted(seen[key])
        if rounds:
            out.append(f"{bases[key]} ({', '.join(f'R{r}' for r in rounds)})")
        else:
            out.append(bases[key])
    return out


# ---------------------------------------------------------------------------
# Notable Achievements: history-depth gates (kill trivial early-TEG claims —
# a player's 2nd-ever round is not a meaningful "personal best", and "3rd-best
# in TEG history" is empty when the league only has 2 TEGs of history) and
# the tournament-total / 9-hole sections, reusing the same analysis functions
# the webapp Records page uses (`analysis.records`, `reporting.milestone_records`)
# instead of a second, hand-rolled implementation. Redesigned 2026-09-12 —
# see STATUS.md for what changed and why.
# ---------------------------------------------------------------------------
MIN_PRIOR_TEGS_FOR_LEAGUE_RANK = 4   # "the Nth-best ... in TEG history" claims
MIN_PRIOR_TEGS_FOR_TOTAL_PB = 3      # tournament-total personal best/worst
MIN_PRIOR_NINES_FOR_PB = 16          # 9-hole personal best/worst


def _a_or_an(n: int) -> str:
    """'an' before a vowel-sound number (8, 11, 18), 'a' otherwise. Hole
    scores in this appendix are always single- or double-digit."""
    return "an" if int(n) in (8, 11, 18) else "a"


def _prior_teg_count(all_data, teg_num: int, player: Optional[str] = None) -> int:
    df = all_data[all_data["TEGNum"] < teg_num]
    if player is not None:
        df = df[df["Player"] == player]
    return int(df["TEGNum"].nunique())


def _prior_nine_count(ranked9, teg_num: int, player: str) -> int:
    df = ranked9[(ranked9["TEGNum"] < teg_num) & (ranked9["Player"] == player)]
    return len(df)


def _blowup_feat(e, is_pw: bool, is_rw: bool, show_round: bool) -> str:
    """Numeric phrasing for a career/TEG-record-worst blow-up: 'runs up an 11
    (+7) at the 15th', never a word label ('sextuple bogey') — Jon's call,
    2026-09-12. Built from the raw hole evidence rather than `e.headline`,
    which carries `events.result_label`'s word form; that function stays
    untouched since it also feeds the LLM narrative prompts."""
    from teg_analysis.reporting.events import _ord

    hole = e.holes[0]
    sc, grossvp, par = int(hole["sc"]), int(hole["grossvp"]), hole["par"]
    round_tag = f" (R{e.round})" if show_round else ""
    headline = (f"{e.players[0]} runs up {_a_or_an(sc)} {sc} ({grossvp:+d}) "
               f"at the {_ord(hole['hole'])}{round_tag}")
    if is_rw and is_pw:
        tag = f"a new TEG-record and career-worst on a par-{par}"
    elif is_rw:
        tag = f"a new TEG-record worst on a par-{par}"
    else:
        tag = f"his career-worst on a par-{par}"
    return f"{headline} — {tag}"


def _totals_achievements(teg_num: int, trophy_col: str, all_data) -> tuple[list, list, list]:
    """Tournament-total (Trophy + Gross) records/PBs/worsts, from
    `analysis.records.identify_aggregate_records_and_pbs` — the same function
    the webapp Records page calls — filtered to the era-appropriate Trophy
    metric plus Gross (never raw Score, never the wrong era's metric)."""
    from teg_analysis.analysis.records import identify_aggregate_records_and_pbs
    from teg_analysis.analysis.rankings import get_ranked_teg_data
    from teg_analysis.reporting.events import _proper

    keep = {trophy_col, "GrossVP"}
    label_by_metric = {trophy_col: "Trophy", "GrossVP": "Gross"}

    def _fmt(metric: str, value) -> str:
        return str(int(value)) + " pts" if metric == "Stableford" else f"{int(value):+d}"

    res = identify_aggregate_records_and_pbs(get_ranked_teg_data(), f"TEG {teg_num}")
    league_depth = _prior_teg_count(all_data, teg_num)

    records, pbs, worsts = [], [], []
    for r in res["records"]:
        if r["metric"] not in keep or league_depth < MIN_PRIOR_TEGS_FOR_LEAGUE_RANK:
            continue
        label = label_by_metric[r["metric"]]
        records.append(f"{_proper(r['player'])}'s {_fmt(r['metric'], r['value'])} "
                       f"is the best {label} total in TEG history")
    for r in res["personal_bests"]:
        if r["metric"] not in keep:
            continue
        if _prior_teg_count(all_data, teg_num, r["player"]) < MIN_PRIOR_TEGS_FOR_TOTAL_PB:
            continue
        label = label_by_metric[r["metric"]]
        pbs.append(f"{_proper(r['player'])}'s {_fmt(r['metric'], r['value'])} is a personal {label} best")
    for r in res["personal_worsts"]:
        if r["metric"] not in keep:
            continue
        if _prior_teg_count(all_data, teg_num, r["player"]) < MIN_PRIOR_TEGS_FOR_TOTAL_PB:
            continue
        label = label_by_metric[r["metric"]]
        worsts.append(f"{_proper(r['player'])}'s {_fmt(r['metric'], r['value'])} is a personal {label} worst")
    return records, pbs, worsts


_NINE_FRIENDLY = {"Stableford": "Stableford", "NetVP": "net-vs-par", "GrossVP": "Gross"}


def _nine_hole_achievements(teg_num: int, round_num: Optional[int], trophy_col: str,
                            all_data) -> tuple[list, list, list]:
    """9-hole (front/back) records/PBs/worsts, from
    `analysis.records.identify_9hole_records_and_pbs` — the same function the
    webapp Records page calls. That function is scoped to one round, so a
    tournament report (round_num=None) loops every round of the TEG."""
    from teg_analysis.analysis.records import identify_9hole_records_and_pbs
    from teg_analysis.analysis.rankings import get_ranked_frontback_data
    from teg_analysis.reporting.events import _proper

    ranked9 = get_ranked_frontback_data()
    keep = {trophy_col, "GrossVP"}
    league_depth = _prior_teg_count(all_data, teg_num)

    def _fmt(metric: str, value) -> str:
        return str(int(value)) if metric == "Stableford" else f"{int(value):+d}"

    if round_num is not None:
        rounds = [round_num]
    else:
        rounds = sorted(int(r) for r in ranked9[ranked9["TEGNum"] == teg_num]["Round"].unique())

    records, pbs, worsts = [], [], []
    for rnd in rounds:
        res = identify_9hole_records_and_pbs(f"TEG {teg_num}", rnd, ranked9)
        suffix = f" (R{rnd})" if round_num is None else ""
        for r in res["records"]:
            if r["metric"] not in keep or league_depth < MIN_PRIOR_TEGS_FOR_LEAGUE_RANK:
                continue
            seg, fname = f"{r['segment']} nine", _NINE_FRIENDLY.get(r["metric"], r["metric"])
            records.append(f"{_proper(r['player'])} — {_fmt(r['metric'], r['value'])} {fname} "
                           f"on the {seg}{suffix} is the best {seg} {fname} in TEG history")
        for r in res["personal_bests"]:
            if r["metric"] not in keep:
                continue
            if _prior_nine_count(ranked9, teg_num, r["player"]) < MIN_PRIOR_NINES_FOR_PB:
                continue
            seg, fname = f"{r['segment']} nine", _NINE_FRIENDLY.get(r["metric"], r["metric"])
            pbs.append(f"{_proper(r['player'])} — {_fmt(r['metric'], r['value'])} {fname} "
                       f"on the {seg}{suffix} is a personal-best {seg} {fname}")
        for r in res["personal_worsts"]:
            if r["metric"] not in keep:
                continue
            if _prior_nine_count(ranked9, teg_num, r["player"]) < MIN_PRIOR_NINES_FOR_PB:
                continue
            seg, fname = f"{r['segment']} nine", _NINE_FRIENDLY.get(r["metric"], r["metric"])
            worsts.append(f"{_proper(r['player'])} — {_fmt(r['metric'], r['value'])} {fname} "
                          f"on the {seg}{suffix} is a personal-worst {seg} {fname}")
    return records, pbs, worsts


def _streak_achievements(teg_num: int, round_num: Optional[int]) -> tuple[list, list, list]:
    """All-time streak records + personal best/worst streaks, from
    `reporting.milestone_records` (itself wrapping `analysis.streaks` — the
    same functions the webapp Records page's Streaks tab uses). Previously
    never reached this appendix at all."""
    from teg_analysis.reporting.milestone_records import (
        detect_streak_records, detect_personal_streak_extremes,
    )

    record_events = detect_streak_records(teg_num)
    personal_events = detect_personal_streak_extremes(teg_num)
    if round_num is not None:
        record_events = [e for e in record_events if e.get("round") == round_num]
        personal_events = [e for e in personal_events if e.get("round") == round_num]

    # A record-setting streak is trivially also that player's personal best —
    # don't print it twice, once per category.
    recorded = {(e["player"], e["streak_type"]) for e in record_events}
    personal_events = [e for e in personal_events
                       if (e["player"], e["streak_type"]) not in recorded]

    def _with_round(fact: str, e: dict) -> str:
        if round_num is None and e.get("round") and f"R{e['round']}" not in fact:
            return f"{fact} (R{e['round']})"
        return fact

    records = [_with_round(e["summary_fact"], e) for e in record_events]
    pbs = [_with_round(e["summary_fact"], e) for e in personal_events
          if e["type"] == "streak_personal_best"]
    worsts = [_with_round(e["summary_fact"], e) for e in personal_events
             if e["type"] == "streak_personal_worst"]
    return records, pbs, worsts


def build_records_block(teg_num: int, round_num: Optional[int] = None) -> str:
    """Deterministic 'Notable Achievements' appendix block. Empty string if none.

    Categories surfaced (best AND worst, TEG record AND personal, throughout):
    - **TEG records**: all-time-best round/9/total, all-time streak ties/breaks.
    - **Personal bests**: player-best round/9/total, personal-best streak.
    - **Personal worsts**: player-worst round/9/total, personal-worst streak.
    - **Rare feats**: holes-in-one, eagles, career/TEG-record-worst blow-ups
      (hole scores over par shown numerically — "+5" — never as a word like
      "quintuple bogey").

    History-depth gated (`MIN_PRIOR_TEGS_FOR_LEAGUE_RANK` etc, top of this
    file) so an early TEG doesn't drown in trivial claims — a debut round is
    not a meaningful "personal best", and "3rd-best in TEG history" means
    nothing when the league has only 2 TEGs of history. No cap on volume
    otherwise: everything clearing the bar prints, however much that is.

    Round-level and single-hole facts come from the existing
    `events.build_notable_events` pipeline (already history-depth-gated on
    its own terms); tournament totals, 9-holes and streaks are pulled
    directly from `analysis.records`/`reporting.milestone_records` — the same
    functions the webapp Records page uses — rather than a second
    implementation. Trophy figures use era-appropriate language: Stableford
    for TEG 8+, net-vs-par for TEGs 1–7; raw Score is never shown.
    """
    from teg_analysis.reporting.events import build_notable_events
    from teg_analysis.reporting.era import trophy_metric
    from teg_analysis.core.data_loader import load_all_data

    all_data = load_all_data()
    events = build_notable_events(teg_num, all_data=all_data)
    if round_num is not None:
        events = [e for e in events if e.round == round_num]
    metric = trophy_metric(teg_num)
    trophy_col = "NetVP" if metric == "net_vs_par" else "Stableford"

    def _with_round(h: str, e) -> str:
        """Suffix headline with (R{round}) for tournament reports."""
        if round_num is None and e.round and f"R{e.round}" not in h:
            return f"{h} (R{e.round})"
        return h

    records, pbs, worsts, feats = [], [], [], []
    for e in events:
        h = e.headline
        if e.type in ("hole_in_one", "eagle"):
            feats.append(_with_round(h, e))
        elif e.type == "big_blowup":
            ctx = e.context or {}
            is_pw = ctx.get("is_player_par_worst", False)
            is_rw = ctx.get("is_teg_par_worst", False)
            if is_pw or is_rw:
                feats.append(_blowup_feat(e, is_pw, is_rw, show_round=round_num is None))
        elif e.type == "round_player":
            if "round in TEG history" in h:
                records.append(_with_round(h, e))
            elif "personal-best round" in h:
                pbs.append(_with_round(h, e))
            elif "worst round to date" in h:
                worsts.append(_with_round(h, e))
        elif e.type == "round_player_gross":
            if "Gross round in TEG history" in h:
                records.append(_with_round(h, e))
            elif "personal-best Gross round" in h:
                pbs.append(_with_round(h, e))
            elif "worst Gross round" in h:
                worsts.append(_with_round(h, e))

    # Tournament totals (Trophy/Gross) — TEG scope only; a round report has
    # no season total to speak of.
    if round_num is None:
        t_recs, t_pbs, t_worsts = _totals_achievements(teg_num, trophy_col, all_data)
        records.extend(t_recs); pbs.extend(t_pbs); worsts.extend(t_worsts)

    # 9-hole and streaks — both tournament and round reports get these.
    n_recs, n_pbs, n_worsts = _nine_hole_achievements(teg_num, round_num, trophy_col, all_data)
    records.extend(n_recs); pbs.extend(n_pbs); worsts.extend(n_worsts)

    s_recs, s_pbs, s_worsts = _streak_achievements(teg_num, round_num)
    records.extend(s_recs); pbs.extend(s_pbs); worsts.extend(s_worsts)

    # Deduplicate within each category
    records = _dedup_entries(records)
    pbs = _dedup_entries(pbs)
    worsts = _dedup_entries(worsts)
    feats = _dedup_entries(feats)

    chunks = []
    for label, css_class, lines in [
        ("TEG records", "records", records),
        ("Personal bests", "records", pbs),
        ("Personal worsts", "records", worsts),
        ("Rare feats", "records", feats),
    ]:
        if lines:
            bullet_items = "\n".join(f'  <li>{line}</li>' for line in lines)
            chunks.append(
                f'<div class="{css_class}">'
                f'<p class="records-header">{label}:</p>'
                f'<ul>\n{bullet_items}\n</ul></div>'
            )
    if not chunks:
        return ""
    return "## Personal bests and TEG records\n\n" + "\n\n".join(chunks)


def _strip_at_a_glance(text: str) -> str:
    """Remove any existing at-a-glance block so it can be re-injected with updated content."""
    return re.sub(
        r'\n*<section class="callout at-a-glance-box">.*?</section>\n?',
        "",
        text,
        flags=re.DOTALL,
    )


def style_text(teg_num: int, text: str) -> str:
    """Apply the full tournament styling pipeline to arbitrary report text.

    Factored out of `style_report` so a *variant* (an A/B voice experiment, say)
    can be styled without being written to `report_final.md` first. That matters
    for comparison: a variant put through the identical styling pipeline is
    directly readable line-for-line against `report_styled.md`.
    """
    from teg_analysis.reporting.history_context import build_win_counts
    venue = build_venue_context(teg_num)
    standings = build_round_standings(teg_num)
    win_counts = build_win_counts(teg_num)
    # Strip old at-a-glance so we can re-inject it with win-count annotations.
    text = _strip_at_a_glance(text)
    styled = apply_styling(text, teg_num, venue, standings=standings, win_counts=win_counts)
    # Strip old records block so we can re-inject the updated version.
    styled = re.sub(r'\n*## Personal bests and TEG records\n[\s\S]*$', '', styled)
    return _append_records(styled, build_records_block(teg_num))


def style_report(teg_num: int) -> str:
    """Read final report + saved plan + venue, write `..._report_styled.md`. Returns path."""
    final_path = f"{output_dir()}/teg_{teg_num}_report_final.md"
    out_path = f"{output_dir()}/teg_{teg_num}_report_styled.md"

    with open(final_path) as f:
        text = f.read()
    styled = style_text(teg_num, text)

    with open(out_path, "w") as f:
        f.write(styled)
    return out_path


# ---------------------------------------------------------------------------
# Round-report styling (Phase E)
# ---------------------------------------------------------------------------
def build_round_scores_data(teg_num: int, round_num: int) -> list[dict]:
    """The structured data behind `build_round_scores`'s markdown block.

    Returns `[{"header": str, "entries": [{"pl": str, "value": str}, ...]}, ...]`
    — Trophy first (era-aware: "Round Stableford" sorted descending for TEG 8+,
    "Round Net VP" sorted ascending, signed, for TEGs 1–7), then "Round Gross"
    (always ascending). Empty list if no data. Shared by the markdown block
    below and `newspaper_edition`'s round-scores rail tables — one source of
    the sort/format so the two never drift apart.
    """
    from teg_analysis.analysis.commentary import create_round_summary
    from teg_analysis.reporting.era import trophy_metric
    rs = create_round_summary()
    rs = rs[(rs["TEGNum"] == teg_num) & (rs["Round"] == round_num)].copy()
    if rs.empty:
        return []

    metric = trophy_metric(teg_num)
    gross = rs.sort_values(["Round_Score_Gross", "Pl"], ascending=[True, True])
    gross_entries = [{"pl": r["Pl"], "value": _fmt_signed(int(r["Round_Score_Gross"]))}
                     for _, r in gross.iterrows()]

    if metric == "net_vs_par":
        trophy_line = rs.sort_values(["Round_Score_NetVP", "Pl"], ascending=[True, True])
        trophy_header = "Round Net VP"
        trophy_entries = [{"pl": r["Pl"], "value": _fmt_signed(int(r["Round_Score_NetVP"]))}
                          for _, r in trophy_line.iterrows()]
    else:
        stab = rs.sort_values(["Round_Score_Stableford", "Pl"], ascending=[False, True])
        trophy_header = "Round Stableford"
        trophy_entries = [{"pl": r["Pl"], "value": str(int(r["Round_Score_Stableford"]))}
                          for _, r in stab.iterrows()]

    return [{"header": trophy_header, "entries": trophy_entries},
            {"header": "Round Gross", "entries": gross_entries}]


def build_round_scores(teg_num: int, round_num: int) -> str:
    """Two-paragraph deterministic round-scores block for a single round.

    For Stableford-era TEGs (8+): Trophy line sorted by `Round_Score_Stableford`
    descending, header "Round Stableford". For net-vs-par-era TEGs (1–7): Trophy
    line sorted by `Round_Score_NetVP` ascending (signed format), header "Round
    Net VP". Gross line always present, sorted by `Round_Score_Gross` ascending.
    Uses player codes (`Pl`). Returns empty string if no data.
    """
    blocks = build_round_scores_data(teg_num, round_num)
    if not blocks:
        return ""
    lines = []
    for b in blocks:
        row = " | ".join(f'{e["pl"]} {e["value"]}' for e in b["entries"])
        lines.append(f'<p class="round-scores"><span class="round-scores-header">'
                     f'{b["header"]}:</span> {row}</p>')
    return "\n".join(lines)


def build_round_dateline(teg_num: int, round_num: int) -> str:
    """Round-report dateline: `TEG N | Round R | Date | Course`."""
    from teg_analysis.constants import ROUND_INFO_CSV
    from teg_analysis.io import read_file
    ri = read_file(ROUND_INFO_CSV)
    row = ri[(ri["TEGNum"] == teg_num) & (ri["Round"] == round_num)]
    if row.empty:
        return ""
    r = row.iloc[0]
    return (f'<p class="dateline">TEG {teg_num} | Round {round_num} | '
            f'{r["Date"]} | {r["Course"]}</p>')


def build_round_at_a_glance(round_results: list[dict], is_final_round: bool) -> str:
    """Round-report at-a-glance callout.

    `round_results` is a list of `{"label": str, "value": str}` — e.g.
    mid-tournament `[{"label": "Round of the day", "value": "David Mullin (43)"},
    {"label": "Trophy lead", "value": "David Mullin, +6"}, ...]`, or on a final
    round the real `Trophy Winner` / `Green Jacket` / `Wooden Spoon` lines,
    matching `_build_at_a_glance`'s markup so `newspaper_edition._parse_results`
    can read either box with the same regex.

    The first entry is tagged `class="trophy-winner"` only when `is_final_round`
    — that class is what the tournament parser's lead-detection keys off, and a
    mid-tournament "round of the day" is not a winner.
    """
    if not round_results:
        return ""
    lines = [
        '<section class="callout at-a-glance-box">',
        '  <p class="at-a-glance-title">RESULTS</p>',
    ]
    for i, r in enumerate(round_results):
        cls = ' class="trophy-winner"' if (is_final_round and i == 0) else ""
        lines.append(f'  <p><strong>{r["label"]}:</strong><span{cls}> {r["value"]}</span></p>')
    lines.append("</section>")
    return "\n".join(lines)


def style_round_text(teg_num: int, round_num: int, text: str, *,
                     appendix_heading: Optional[str] = None,
                     at_a_glance_html: Optional[str] = None) -> str:
    """Apply the round styling pipeline to arbitrary round-report text.

    Factored out of `style_round_report` the same way `style_text` was factored
    out of `style_report` (`restyle_voice`'s round path needs this to style a
    variant without writing it to `report_final.md` first).

    Layout:
        # Title  {.round-report-title}
        <p class="dateline">…</p>
        <p class="round-scores">Round Stableford: …</p>
        <p class="round-scores">Round Gross: …</p>

        …main prose (possibly ending with a one-paragraph race-shift note)…

        <p class="standings">Trophy Standings: …</p>
        <p class="standings">Green Jacket Standings: …</p>

    `appendix_heading`: when given, the end-of-round standings are wrapped in
    `## {appendix_heading}` + `**End of Round N**` before the two standings
    lines, instead of being appended bare. The storyline-first round pipeline
    needs this — `newspaper_edition._split_body_sections` requires a heading to
    split the appendix on, and `_parse_standings` already matches exactly this
    `**End of Round N**` + two `<p class="standings">` shape (it is what the
    legacy `## Standings by round` tournament appendix emits per round). The
    legacy round pipeline leaves this unset and keeps the bare block.

    Idempotent: re-running on already-styled text is a no-op.
    """
    # Tag the H1
    def repl_h1(m):
        line = m.group(0)
        if "{.round-report-title" in line:
            return line
        return f"{line.rstrip()} {{.round-report-title}}"
    text = re.sub(r"^# [^\n]+$", repl_h1, text, count=1, flags=re.MULTILINE)

    # Insert dateline + round-scores (+ at-a-glance, if given) after the H1 (once).
    if 'class="dateline"' not in text and 'class="round-scores"' not in text:
        dateline = build_round_dateline(teg_num, round_num)
        scores = build_round_scores(teg_num, round_num)
        block_parts = [p for p in (dateline, scores, at_a_glance_html) if p]
        if block_parts:
            block = "\n\n" + "\n\n".join(block_parts) + "\n"
            text = re.sub(
                r"^(# [^\n]+\{\.round-report-title\})\s*$",
                lambda m: m.group(1) + block,
                text, count=1, flags=re.MULTILINE,
            )

    # Append end-of-round standings (Trophy + Green Jacket) at the very end.
    if 'class="standings"' not in text:
        end_standings = build_round_standings(teg_num).get(round_num, "")
        if end_standings:
            sep = "" if text.endswith("\n") else "\n"
            if appendix_heading:
                block = (f"## {appendix_heading}\n\n**End of Round {round_num}**\n\n"
                          f"{end_standings}\n")
            else:
                block = end_standings + "\n"
            text = text + sep + "\n" + block

    # Append the PBs / TEG records appendix scoped to this round (if any).
    text = _append_records(text, build_records_block(teg_num, round_num=round_num))

    return text


def style_round_report(teg_num: int, round_num: int) -> str:
    """Read `teg_N_round_R_report_final.md`, apply `style_round_text`, write
    `..._styled.md`. Returns path."""
    final_path = f"{output_dir()}/teg_{teg_num}_round_{round_num}_report_final.md"
    out_path = f"{output_dir()}/teg_{teg_num}_round_{round_num}_report_styled.md"

    with open(final_path) as f:
        text = f.read()

    styled = style_round_text(teg_num, round_num, text)

    with open(out_path, "w") as f:
        f.write(styled)
    return out_path
