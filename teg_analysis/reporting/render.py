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
from typing import Optional, Union

from teg_analysis.reporting.story_plan import StoryPlan
from teg_analysis.reporting.venue import build_venue_context
from teg_analysis.reporting.authoring import load_story_plan

OUTPUT_DIR = "data/commentary"


# ---------------------------------------------------------------------------
# Per-round standings (deterministic; no LLM)
# ---------------------------------------------------------------------------
def _fmt_signed(n: int) -> str:
    """Signed integer with no sign for zero."""
    return "0" if n == 0 else f"{n:+d}"


def build_round_standings(teg_num: int) -> dict:
    """Build per-round Trophy + Green Jacket standings markdown blocks for a TEG.

    Returns {round_num: standings_markdown}. Pure data — uses cumulative totals
    from `create_round_summary`; no LLM, no fabrication risk.
    """
    from teg_analysis.analysis.commentary import create_round_summary
    from teg_analysis.reporting.era import trophy_metric
    rs = create_round_summary()
    rs = rs[rs["TEGNum"] == teg_num].copy()

    metric = trophy_metric(teg_num)
    if metric == "net_vs_par":
        trophy_col = "Cumulative_Tournament_Score_NetVP"
        trophy_ascending = True
        trophy_fmt = lambda x: _fmt_signed(int(x))
    else:
        trophy_col = "Cumulative_Tournament_Score_Stableford"
        trophy_ascending = False
        trophy_fmt = lambda x: str(int(x))

    out: dict = {}
    for rnd in sorted(int(r) for r in rs["Round"].unique()):
        rdf = rs[rs["Round"] == rnd]
        trophy = rdf.sort_values(trophy_col, ascending=trophy_ascending)
        jacket = rdf.sort_values("Cumulative_Tournament_Score_Gross", ascending=True)

        trophy_str = " | ".join(
            f"{r['Pl']} {trophy_fmt(r[trophy_col])}"
            for _, r in trophy.iterrows()
        )
        jacket_str = " | ".join(
            f"{r['Pl']} {_fmt_signed(int(r['Cumulative_Tournament_Score_Gross']))}"
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


def _competition_kind(name: str) -> str:
    n = (name or "").lower()
    if "trophy" in n or "stableford" in n:
        return "trophy"
    if "jacket" in n or "gross" in n:
        return "jacket"
    if "spoon" in n:
        return "spoon"
    return ""


def _nth_suffix(n: int) -> str:
    """'1st', '2nd', '3rd', '4th', … for win-count annotations."""
    if 10 <= n % 100 <= 20:
        suf = "th"
    else:
        suf = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suf}"


def _build_at_a_glance(plan_d: dict, win_counts: Optional[dict] = None) -> str:
    """Build the at-a-glance callout from `plan.competitions[]`.

    `win_counts` is a dict {player_name: {"trophy_wins": N, "jacket_wins": N,
    "spoon_count": N}} covering all TEGs through the current one.  When supplied,
    the winner's running total is appended in parentheses, e.g. "(2nd Trophy)".
    """
    winners = {"trophy": None, "jacket": None, "spoon": None}
    for c in plan_d.get("competitions", []) or []:
        kind = _competition_kind(c.get("name", ""))
        if kind and not winners[kind]:
            winners[kind] = c.get("winner_or_loser", "")

    # Build a case-insensitive lookup — plan names are proper-cased, win_counts
    # keys use the raw all-caps-surname format from the data ("John PATTERSON").
    _wc_lower: dict = {k.lower(): v for k, v in (win_counts or {}).items()}

    def _suffix(player: Optional[str], key: str) -> str:
        if not win_counts or not player:
            return ""
        counts = _wc_lower.get(player.lower(), {})
        n = counts.get(key, 0)
        if n == 0:
            return ""
        label = {"trophy_wins": "Trophy", "jacket_wins": "Jacket", "spoon_count": "Spoon"}[key]
        return f" ({_nth_suffix(n)} {label})"

    lines = [
        '<section class="callout at-a-glance-box">',
        '  <p class="at-a-glance-title">RESULTS</p>',
    ]
    if winners["trophy"]:
        suffix = _suffix(winners["trophy"], "trophy_wins")
        lines.append(
            f'  <p><strong>Trophy Winner:</strong>'
            f'<span class="trophy-winner"> {winners["trophy"]}{suffix}</span></p>'
        )
    if winners["jacket"]:
        suffix = _suffix(winners["jacket"], "jacket_wins")
        lines.append(f'  <p><strong>Green Jacket:</strong> {winners["jacket"]}{suffix}</p>')
    if winners["spoon"]:
        suffix = _suffix(winners["spoon"], "spoon_count")
        lines.append(f'  <p><strong>Wooden Spoon:</strong> {winners["spoon"]}{suffix}</p>')
    lines.append("</section>")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Public entry points
# ---------------------------------------------------------------------------
def apply_styling(text: str, plan: Union[StoryPlan, dict], venue: dict,
                  standings: Optional[dict] = None,
                  win_counts: Optional[dict] = None) -> str:
    """Apply CSS-class hooks + dateline + at-a-glance callout + per-round standings.

    `win_counts` is passed to `_build_at_a_glance` to annotate wins with ordinal
    suffixes, e.g. "(2nd Jacket)".  Idempotent: existing hooks are not duplicated.
    """
    plan_d = plan.model_dump() if isinstance(plan, StoryPlan) else plan

    text = _add_report_title_class(text)
    text = _add_round_classes(text)

    # Insert dateline + callout right after the styled H1 (once).
    if 'class="dateline"' not in text and 'class="at-a-glance-box"' not in text:
        dateline = _build_dateline(venue)
        callout = _build_at_a_glance(plan_d, win_counts=win_counts)
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
    """Deduplicate entries, combining round suffixes when the base text is the same.

    E.g. "Baker posts a personal-best round: 44 pts (R2)" and the same for (R4)
    become "Baker posts a personal-best round: 44 pts (R2, R4)".
    """
    # Group by base text (with round suffix stripped), preserving insertion order.
    seen: dict[str, list[str]] = {}   # base_lower -> [round_strs] or []
    order: list[str] = []             # insertion order of base keys
    for e in entries:
        e = e.strip()
        m = _ROUND_SUFFIX_RE.search(e)
        if m:
            base = e[: m.start()]
            rnd = f"R{m.group(1)}"
        else:
            base = e
            rnd = None
        key = base.lower()
        if key not in seen:
            seen[key] = []
            order.append(key)
        if rnd and rnd not in seen[key]:
            seen[key].append(rnd)

    out = []
    for key in order:
        # Recover original-cased base from the first entry stored under this key
        original_base = next(
            (e if not _ROUND_SUFFIX_RE.search(e) else e[: _ROUND_SUFFIX_RE.search(e).start()]
             for e in entries if e.strip().lower().startswith(key) and
             e.strip().lower().rstrip(")0123456789r(, ").rstrip() == key or
             _ROUND_SUFFIX_RE.sub("", e.strip()).strip().lower() == key),
            key,
        )
        # Simpler: find first entry whose base matches
        for e in entries:
            m = _ROUND_SUFFIX_RE.search(e.strip())
            base_cased = e.strip()[: m.start()] if m else e.strip()
            if base_cased.strip().lower() == key:
                original_base = base_cased.strip()
                break
        rounds = seen[key]
        if rounds:
            out.append(f"{original_base} ({', '.join(rounds)})")
        else:
            out.append(original_base)
    return out


def _nine_hole_records(teg_num: int, round_num: Optional[int] = None) -> tuple[list, list]:
    """Return (records, pbs) strings for 9-hole Stableford and Gross records.

    Loads the full ranked 9-hole data, filters to the TEG (and optionally one
    round), checks `Rank_within_all_*` and `Rank_within_player_*` for rank == 1,
    and returns plain-English strings.  Only surfaces Stableford and GrossVP —
    Sc / NetVP are noisier and less meaningful to the audience.
    """
    try:
        from teg_analysis.analysis.aggregation import get_9_data
        from teg_analysis.analysis.rankings import add_ranks
        from teg_analysis.reporting.era import trophy_metric

        df9 = get_9_data()          # loads data internally
        df9 = add_ranks(df9)

        mask = df9["TEGNum"] == teg_num
        if round_num is not None:
            mask &= df9["Round"] == round_num
        filtered = df9[mask]
        if filtered.empty:
            return [], []

        metric = trophy_metric(teg_num)
        # Show Stableford for TEG 8+, NetVP for TEGs 1-7 (as the Trophy metric)
        trophy_col = "Stableford" if metric != "net_vs_par" else "NetVP"
        active_metrics = [trophy_col, "GrossVP"]

        friendly = {
            "Stableford": "Stableford",
            "NetVP": "net-vs-par",
            "GrossVP": "Gross",
        }
        direction = {
            "Stableford": "high",   # higher is better → rank 1 = highest
            "NetVP": "low",          # lower is better → rank 1 = lowest
            "GrossVP": "low",
        }

        records, pbs = [], []
        seen_rec = set()
        seen_pb = set()

        for col in active_metrics:
            rank_all = f"Rank_within_all_{col}"
            rank_pl = f"Rank_within_player_{col}"
            if rank_all not in filtered.columns or rank_pl not in filtered.columns:
                continue

            for _, row in filtered.iterrows():
                player = row["Player"]
                segment = row.get("FrontBack", "nine")
                val = row[col]
                r_str = f"{round_num}" if round_num else f"R{int(row['Round'])}"
                seg_label = f"{segment} nine" if segment in ("Front", "Back") else "nine"
                fname = friendly.get(col, col)

                if direction[col] == "high":
                    val_str = str(int(val))
                else:
                    val_str = f"{int(val):+d}"

                # TEG record (all-time best)
                if row[rank_all] == 1:
                    key = (player, col, segment, "rec")
                    if key not in seen_rec:
                        seen_rec.add(key)
                        records.append(
                            f"{player} — {val_str} {fname} on the {seg_label} (R{int(row['Round'])}) "
                            f"is the best {seg_label} {fname} in TEG history"
                        )

                # Personal best
                if row[rank_pl] == 1:
                    key = (player, col, segment, "pb")
                    if key not in seen_pb:
                        seen_pb.add(key)
                        pbs.append(
                            f"{player} — {val_str} {fname} on the {seg_label} (R{int(row['Round'])}) "
                            f"is a personal-best {seg_label} {fname}"
                        )

        return records, pbs

    except Exception:
        return [], []


def build_records_block(teg_num: int, round_num: Optional[int] = None) -> str:
    """Deterministic 'PBs and TEG records' appendix block. Empty string if none.

    Categories surfaced:
    - **TEG records**: all-time top-3 round, all-time best Trophy/Gross total,
      all-time best 9-hole score.
    - **Personal bests**: player-PB round, player-PB Trophy/Gross total,
      player-PB 9-hole score.
    - **Personal worsts**: player-worst round to date.
    - **Rare feats**: holes-in-one, eagles, career/TEG-worst blow-ups.

    Each entry is its own bullet. Duplicate entries (same player, same feat)
    are collapsed into one.  Trophy records use era-appropriate language:
    Stableford for TEG 8+, net-vs-par for TEGs 1–7.
    """
    from teg_analysis.reporting.events import build_notable_events
    from teg_analysis.reporting.era import trophy_metric
    events = build_notable_events(teg_num)
    if round_num is not None:
        events = [e for e in events if e.round == round_num]
    metric = trophy_metric(teg_num)

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
                par = e.holes[0].get("par") if e.holes else None
                tags = []
                if is_rw:
                    tags.append(f"a new TEG-record worst on a par-{par}")
                if is_pw:
                    tags.append(f"his career-worst on a par-{par}")
                feats.append(f"{_with_round(h, e)} — " + "; ".join(tags))
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
        elif e.type == "trophy_win":
            ctx = e.context or {}
            ar = ctx.get("all_time_rank")
            pr = ctx.get("player_rank")
            winner = e.players[0] if e.players else "Winner"
            score = ctx.get("score")
            if metric == "net_vs_par":
                score_str = f"{score:+d}" if isinstance(score, int) else str(score)
                score_label = f"{score_str} net-vs-par"
            else:
                score_str = f"{score} pts"
                score_label = score_str
            if ar == 1:
                records.append(f"{winner}'s {score_label} is the best Trophy total in TEG history")
            elif ar is not None and ar <= 3:
                ord_str = {2: "2nd", 3: "3rd"}.get(ar, str(ar))
                records.append(f"{winner}'s {score_label} is the {ord_str}-best Trophy total in TEG history")
            elif pr == 1:
                pbs.append(f"{winner}'s {score_label} is a personal Trophy best")
        elif e.type in ("jacket_win", "jacket_pb"):
            ctx = e.context or {}
            ar = ctx.get("all_time_rank")
            pr = ctx.get("player_rank")
            winner = e.players[0] if e.players else "Winner"
            score = ctx.get("score")
            score_label = f"{score:+d}" if isinstance(score, int) else str(score)
            if ar == 1:
                records.append(f"{winner}'s {score_label} is the best Gross total in TEG history")
            elif ar is not None and ar <= 3:
                ord_str = {2: "2nd", 3: "3rd"}.get(ar, str(ar))
                records.append(f"{winner}'s {score_label} is the {ord_str}-best Gross total in TEG history")
            elif pr == 1:
                pbs.append(f"{winner}'s {score_label} is a personal Gross best")

    # Add 9-hole records (tournament and round reports both get them)
    nine_recs, nine_pbs = _nine_hole_records(teg_num, round_num)
    records.extend(nine_recs)
    pbs.extend(nine_pbs)

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


def style_report(teg_num: int) -> str:
    """Read final report + saved plan + venue, write `..._report_styled.md`. Returns path."""
    from teg_analysis.reporting.history_context import build_win_counts
    final_path = f"{OUTPUT_DIR}/teg_{teg_num}_report_final.md"
    out_path = f"{OUTPUT_DIR}/teg_{teg_num}_report_styled.md"

    with open(final_path) as f:
        text = f.read()
    plan = load_story_plan(teg_num)           # dict (from saved JSON)
    venue = build_venue_context(teg_num)
    standings = build_round_standings(teg_num)
    win_counts = build_win_counts(teg_num)
    # Strip old at-a-glance so we can re-inject it with win-count annotations.
    text = _strip_at_a_glance(text)
    styled = apply_styling(text, plan, venue, standings=standings, win_counts=win_counts)
    # Strip old records block so we can re-inject the updated version.
    styled = re.sub(r'\n*## Personal bests and TEG records\n[\s\S]*$', '', styled)
    styled = _append_records(styled, build_records_block(teg_num))

    with open(out_path, "w") as f:
        f.write(styled)
    return out_path


# ---------------------------------------------------------------------------
# Round-report styling (Phase E)
# ---------------------------------------------------------------------------
def build_round_scores(teg_num: int, round_num: int) -> str:
    """Two-paragraph deterministic round-scores block for a single round.

    For Stableford-era TEGs (8+): Trophy line sorted by `Round_Score_Stableford`
    descending, header "Round Stableford". For net-vs-par-era TEGs (1–7): Trophy
    line sorted by `Round_Score_NetVP` ascending (signed format), header "Round
    Net VP". Gross line always present, sorted by `Round_Score_Gross` ascending.
    Uses player codes (`Pl`). Returns empty string if no data.
    """
    from teg_analysis.analysis.commentary import create_round_summary
    from teg_analysis.reporting.era import trophy_metric
    rs = create_round_summary()
    rs = rs[(rs["TEGNum"] == teg_num) & (rs["Round"] == round_num)].copy()
    if rs.empty:
        return ""

    metric = trophy_metric(teg_num)
    gross = rs.sort_values("Round_Score_Gross", ascending=True)
    gross_str = " | ".join(
        f"{r['Pl']} {_fmt_signed(int(r['Round_Score_Gross']))}"
        for _, r in gross.iterrows()
    )

    if metric == "net_vs_par":
        trophy_line = rs.sort_values("Round_Score_NetVP", ascending=True)
        trophy_str = " | ".join(
            f"{r['Pl']} {_fmt_signed(int(r['Round_Score_NetVP']))}"
            for _, r in trophy_line.iterrows()
        )
        return (
            f'<p class="round-scores"><span class="round-scores-header">Round Net VP:</span>'
            f' {trophy_str}</p>\n'
            f'<p class="round-scores"><span class="round-scores-header">Round Gross:</span>'
            f' {gross_str}</p>'
        )
    else:
        stab = rs.sort_values("Round_Score_Stableford", ascending=False)
        stab_str = " | ".join(
            f"{r['Pl']} {int(r['Round_Score_Stableford'])}"
            for _, r in stab.iterrows()
        )
        return (
            f'<p class="round-scores"><span class="round-scores-header">Round Stableford:</span>'
            f' {stab_str}</p>\n'
            f'<p class="round-scores"><span class="round-scores-header">Round Gross:</span>'
            f' {gross_str}</p>'
        )


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


def style_round_report(teg_num: int, round_num: int) -> str:
    """Read `teg_N_round_R_report_final.md`, inject styling hooks, write
    `..._styled.md`. Returns path.

    Layout:
        # Title  {.round-report-title}
        <p class="dateline">…</p>
        <p class="round-scores">Round Stableford: …</p>
        <p class="round-scores">Round Gross: …</p>

        …main prose (possibly ending with a one-paragraph race-shift note)…

        <p class="standings">Trophy Standings: …</p>
        <p class="standings">Green Jacket Standings: …</p>

    Idempotent: re-running on an already-styled file is a no-op.
    """
    final_path = f"{OUTPUT_DIR}/teg_{teg_num}_round_{round_num}_report_final.md"
    out_path = f"{OUTPUT_DIR}/teg_{teg_num}_round_{round_num}_report_styled.md"

    with open(final_path) as f:
        text = f.read()

    # Tag the H1
    def repl_h1(m):
        line = m.group(0)
        if "{.round-report-title" in line:
            return line
        return f"{line.rstrip()} {{.round-report-title}}"
    text = re.sub(r"^# [^\n]+$", repl_h1, text, count=1, flags=re.MULTILINE)

    # Insert dateline + round-scores after the H1 (once).
    if 'class="dateline"' not in text and 'class="round-scores"' not in text:
        dateline = build_round_dateline(teg_num, round_num)
        scores = build_round_scores(teg_num, round_num)
        block_parts = [p for p in (dateline, scores) if p]
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
            text = text + sep + "\n" + end_standings + "\n"

    # Append the PBs / TEG records appendix scoped to this round (if any).
    text = _append_records(text, build_records_block(teg_num, round_num=round_num))

    with open(out_path, "w") as f:
        f.write(text)
    return out_path
