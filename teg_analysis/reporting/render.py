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
    rs = create_round_summary()
    rs = rs[rs["TEGNum"] == teg_num].copy()

    out: dict = {}
    for rnd in sorted(int(r) for r in rs["Round"].unique()):
        rdf = rs[rs["Round"] == rnd]
        trophy = rdf.sort_values("Cumulative_Tournament_Score_Stableford", ascending=False)
        jacket = rdf.sort_values("Cumulative_Tournament_Score_Gross", ascending=True)

        trophy_str = " | ".join(
            f"{r['Pl']} {int(r['Cumulative_Tournament_Score_Stableford'])}"
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


def _build_at_a_glance(plan_d: dict) -> str:
    """Build the at-a-glance callout from `plan.competitions[]`. Winners only;
    margins and (Nth) suffixes are deferred (need win-count history)."""
    winners = {"trophy": None, "jacket": None, "spoon": None}
    for c in plan_d.get("competitions", []) or []:
        kind = _competition_kind(c.get("name", ""))
        if kind and not winners[kind]:
            winners[kind] = c.get("winner_or_loser", "")

    lines = [
        '<section class="callout at-a-glance-box">',
        '  <p class="at-a-glance-title">RESULTS</p>',
    ]
    if winners["trophy"]:
        lines.append(
            f'  <p><strong>Trophy Winner:</strong>'
            f'<span class="trophy-winner"> {winners["trophy"]}</span></p>'
        )
    if winners["jacket"]:
        lines.append(f'  <p><strong>Green Jacket:</strong> {winners["jacket"]}</p>')
    if winners["spoon"]:
        lines.append(f'  <p><strong>Wooden Spoon:</strong> {winners["spoon"]}</p>')
    lines.append("</section>")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Public entry points
# ---------------------------------------------------------------------------
def apply_styling(text: str, plan: Union[StoryPlan, dict], venue: dict,
                  standings: Optional[dict] = None) -> str:
    """Apply CSS-class hooks + dateline + at-a-glance callout + per-round standings.

    Idempotent: if styling hooks or standings are already present, they're not duplicated.
    """
    plan_d = plan.model_dump() if isinstance(plan, StoryPlan) else plan

    text = _add_report_title_class(text)
    text = _add_round_classes(text)

    # Insert dateline + callout right after the styled H1 (once).
    if 'class="dateline"' not in text and 'class="at-a-glance-box"' not in text:
        dateline = _build_dateline(venue)
        callout = _build_at_a_glance(plan_d)
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


def build_records_block(teg_num: int, round_num: Optional[int] = None) -> str:
    """Deterministic 'PBs and TEG records' appendix block. Empty string if none.

    Categories surfaced (from events.py beats):
    - **TEG records**: all-time top-3 round (Stableford), all-time best Trophy total.
    - **Personal bests**: player-PB round, player-PB Trophy total.
    - **Personal worsts**: player-worst round to date.
    - **Rare feats**: holes-in-one, eagles.

    Idempotent injection caller can detect by `class="records"`.
    """
    from teg_analysis.reporting.events import build_notable_events
    events = build_notable_events(teg_num)
    if round_num is not None:
        events = [e for e in events if e.round == round_num]

    def _with_round(h: str, e) -> str:
        """Suffix headline with (R{round}) if not already mentioned."""
        if e.round and f"R{e.round}" not in h:
            return f"{h} (R{e.round})"
        return h

    records, pbs, worsts, feats = [], [], [], []
    for e in events:
        h = e.headline
        if e.type in ("hole_in_one", "eagle"):
            feats.append(_with_round(h, e))
        elif e.type == "big_blowup" and e.holes and e.holes[0].get("sc", 0) >= 10:
            feats.append(h)  # big_blowup headlines already carry (R{rnd})
        elif e.type == "round_player":
            if "round in TEG history" in h:           # all-time top-3 round
                records.append(_with_round(h, e))
            elif "personal-best round" in h:
                pbs.append(_with_round(h, e))
            elif "worst round to date" in h:
                worsts.append(_with_round(h, e))
        elif e.type == "trophy_win":
            ctx = e.context or {}
            ar = ctx.get("all_time_rank")
            pr = ctx.get("player_rank")
            winner = e.players[0] if e.players else "Winner"
            score = ctx.get("score")
            if ar == 1:
                records.append(f"{winner}'s {score} pts is the best Trophy total in TEG history")
            elif ar is not None and ar <= 3:
                ord_str = {2: "2nd", 3: "3rd"}.get(ar, str(ar))
                records.append(f"{winner}'s {score} pts is the {ord_str}-best Trophy total in TEG history")
            elif pr == 1:
                pbs.append(f"{winner}'s {score} pts is a personal Trophy best")

    chunks = []
    for label, lines in [
        ("TEG records", records),
        ("Personal bests", pbs),
        ("Personal worsts", worsts),
        ("Rare feats", feats),
    ]:
        if lines:
            chunks.append(
                f'<p class="records"><span class="records-header">{label}:</span> '
                + "; ".join(lines) + ".</p>"
            )
    if not chunks:
        return ""
    return "## Personal bests and TEG records\n\n" + "\n".join(chunks)


def style_report(teg_num: int) -> str:
    """Read final report + saved plan + venue, write `..._report_styled.md`. Returns path."""
    final_path = f"{OUTPUT_DIR}/teg_{teg_num}_report_final.md"
    out_path = f"{OUTPUT_DIR}/teg_{teg_num}_report_styled.md"

    with open(final_path) as f:
        text = f.read()
    plan = load_story_plan(teg_num)           # dict (from saved JSON)
    venue = build_venue_context(teg_num)
    standings = build_round_standings(teg_num)
    styled = apply_styling(text, plan, venue, standings=standings)
    styled = _append_records(styled, build_records_block(teg_num))

    with open(out_path, "w") as f:
        f.write(styled)
    return out_path


# ---------------------------------------------------------------------------
# Round-report styling (Phase E)
# ---------------------------------------------------------------------------
def build_round_scores(teg_num: int, round_num: int) -> str:
    """Two-paragraph deterministic round-scores block for a single round.

    Stableford line sorted by `Round_Score_Stableford` descending; Gross line
    sorted by `Round_Score_Gross` ascending (signed format). Uses player codes
    (`Pl`). Returns empty string if no data.
    """
    from teg_analysis.analysis.commentary import create_round_summary
    rs = create_round_summary()
    rs = rs[(rs["TEGNum"] == teg_num) & (rs["Round"] == round_num)].copy()
    if rs.empty:
        return ""

    stab = rs.sort_values("Round_Score_Stableford", ascending=False)
    gross = rs.sort_values("Round_Score_Gross", ascending=True)
    stab_str = " | ".join(
        f"{r['Pl']} {int(r['Round_Score_Stableford'])}"
        for _, r in stab.iterrows()
    )
    gross_str = " | ".join(
        f"{r['Pl']} {_fmt_signed(int(r['Round_Score_Gross']))}"
        for _, r in gross.iterrows()
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
