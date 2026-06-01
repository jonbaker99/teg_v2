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
from typing import Union

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
    """Insert each round's standings block at the end of its section in document order
    (immediately before the next `## ` heading, or EOF). Idempotent — skip if already
    present (detected by `class="standings"` near the injection point)."""
    if not standings:
        return text
    if 'class="standings"' in text:
        return text  # already injected

    lines = text.splitlines(keepends=True)
    result = []
    current_round = None
    for line in lines:
        m_round = re.match(r"^## Round (\d+)\b", line)
        m_h2 = re.match(r"^## ", line)
        if m_round:
            # New round heading. If we were inside a round, flush its standings first.
            if current_round is not None and current_round in standings:
                result.append("\n" + standings[current_round] + "\n\n")
            current_round = int(m_round.group(1))
            result.append(line)
        elif m_h2 and current_round is not None:
            # Non-round H2 closes the round section. Inject standings before it.
            if current_round in standings:
                result.append("\n" + standings[current_round] + "\n\n")
            current_round = None
            result.append(line)
        else:
            result.append(line)
    # Document ended inside a round section
    if current_round is not None and current_round in standings:
        result.append("\n" + standings[current_round] + "\n")
    return "".join(result)


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

    with open(out_path, "w") as f:
        f.write(styled)
    return out_path
