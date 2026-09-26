"""Claim extraction + code-checked verification (D3's claims layer, WP4).

`verify.py`'s eight mechanical checks work off pattern-matching alone — they
can catch "40 over par through 3 holes" as implausible, but they cannot tell
whether "Patterson was comfortably the better player" is true, because that
needs to know what the report actually SAID and compare it with what the data
says. This module adds that layer:

1. **Extract** (`extract_claims`) — one structured LLM call given ONLY the
   report text (no data, so it cannot launder a fact in). Returns a list of
   `Claim`s, each with a verbatim `quote`. A claim whose quote is not a
   substring of the report is dropped before checking — it isn't a claim
   about THIS report if it can't be found in it.
2. **Check** (`check_claims`) — every surviving claim against a `FactBase`
   built from `load_all_data` + `settled_facts.build_hole_timeline`. One
   checker function per claim type; a type with no checker yet reports
   `severity="unchecked"`, counted and listed, never folded into "passed".
3. **Repair** (`repair_paragraph`, WP5) — a surgical, per-paragraph rewrite
   call for a confirmed error: the published paragraph plus the correct fact
   in, a corrected paragraph out. Deliberately narrow (one paragraph, one
   correction) rather than a full-report regeneration, so the approved
   headline/story structure survives. **Always verify the finding is real
   before repairing** — an extraction error (a claim attached to the wrong
   round or hole) looks identical to a report error until checked against the
   data directly; repairing a mis-diagnosed "error" introduces a real one
   into a paragraph that was already correct (found 2026-09-26, TEG 18).

Caching: `{stem}_claims.json`, keyed on a hash of the report text. `llm.py`
has no response cache of its own (only Anthropic prompt caching), so this is
what keeps `verify --all --claims` cheap and deterministic — the model only
re-runs when the text actually changes.

    from teg_analysis.reporting.claims import check_claims
    findings = check_claims(18)                  # extracts + caches + checks
    findings = check_claims(18, round_num=2)
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import dataclass
from typing import Optional, Tuple

import pandas as pd
from pydantic import BaseModel, Field

from teg_analysis.reporting import llm, prompts
from teg_analysis.reporting.paths import output_dir
from teg_analysis.reporting.settled_facts import build_hole_timeline, build_settled_facts
from teg_analysis.reporting.verify import Finding, report_path

EXTRACTION_MODEL = "claude-sonnet-5"

CLAIM_TYPES = (
    "hole_score", "lead_event", "rank_change", "comparison",
    "run", "weekday", "record", "total", "margin",
)


class Claim(BaseModel):
    """One factual claim extracted from report prose.

    Deliberately flat rather than a discriminated union — only the fields
    relevant to `type` are expected to be filled; the rest stay null. A flat
    schema is easier for the model to fill correctly than a union, and the
    checkers below only ever read the fields their own type uses.
    """
    type: str = Field(description=f"one of: {', '.join(CLAIM_TYPES)}")
    quote: str = Field(description="Verbatim substring of the report text, "
                                   "character-for-character")
    player: Optional[str] = None
    players: Optional[list[str]] = None
    round: Optional[int] = None
    hole: Optional[int] = None
    score: Optional[int] = None
    competition: Optional[str] = Field(
        default=None, description="Trophy / Green Jacket / Wooden Spoon, as named")
    metric: Optional[str] = Field(
        default=None, description="stableford / net_vs_par / gross, ONLY if stated explicitly")
    direction: Optional[str] = Field(
        default=None, description="lead_event: took_lead / lost_lead / drew_level")
    value: Optional[int] = Field(
        default=None, description="the asserted number: a rank, a total, a run length")
    weekday: Optional[str] = None
    span_start_hole: Optional[int] = None
    span_end_hole: Optional[int] = None
    basis: Optional[str] = Field(
        default=None, description="run: 'par or better' / 'bogey or worse' / 'birdie or better' / "
                                   "'par' / 'double bogey or worse'")


class ClaimList(BaseModel):
    claims: list[Claim]


EXTRACTOR_SYSTEM = """You are extracting factual claims from a finished golf report, for \
automated fact-checking against the underlying tournament data. You are given ONLY the \
report text below — no data, so any claim you flag will be checked independently.

For every claim in the text that could in principle be checked against tournament data, \
emit one Claim. Extract every checkable claim — do not skip one because it looks obviously \
true, and do not invent a claim that is not actually in the text.

`quote` is the EXACT sentence or clause the claim comes from, character-for-character as it \
appears in the report — do not paraphrase, truncate with an ellipsis, or fix punctuation. A \
claim whose quote cannot be found verbatim in the report is discarded before checking, so \
precision here matters more than coverage.

**Round/hole context.** A sentence often doesn't restate its own round — it's implied by an \
earlier sentence in the same paragraph ("In round two he took..." two sentences later still \
means round two). Use that surrounding context to fill `round`/`hole` when you are confident. \
**But if you are not confident which round or hole a sentence belongs to, leave `round`/`hole` \
null rather than guess** — an attached WRONG round makes a true sentence look like a false one \
when checked, which is worse than an unchecked claim.

CLAIM TYPES (`type` field) and what to fill:
- `hole_score`: a specific hole score. Fill `player`, `round`, `hole`, `score` (raw strokes) \
— **ONLY when the text gives an explicit number for THAT hole** ("an eight at the 7th", "he \
made a 6"). A relative descriptor alone (double, triple, bogey, birdie) does NOT tell you the \
raw score without knowing the hole's par, which you do not have — do NOT guess a score from a \
descriptor, and do NOT extract a `hole_score` claim for a hole named only in a list like \
"doubles at the 5th, 6th and 10th" (no number is stated for any of those holes). Skip it \
entirely rather than infer a number.
- `lead_event`: a change of lead in a competition. Fill `player`, `round`, `hole`, \
`competition`, `direction` (took_lead / lost_lead / drew_level).
- `rank_change`: a stated position/rank at a point in the tournament, ONLY when the text gives \
an explicit ordinal NUMBER ("third", "fourth", "5th"). Fill `player`, `round`, `hole`, \
`competition`, `value` (that number as an integer, 1 = best/leading REGARDLESS of which \
competition is named, including the Wooden Spoon: "dropped him to fourth" always means \
Trophy-direction rank 4, never an inverted "4th-worst" reading). **"Bottom", "last", or "foot \
of the field" with NO explicit number is NOT a value you can fill** — it depends on the field \
size, which the sentence doesn't give you and you must not guess. Extract the claim with \
`value` left null (it becomes an honest unchecked, not a wrong number) rather than invent 1, \
the field size, or anything else.
- `comparison`: one player judged better/worse than another, overall or in a competition. \
Fill `players` (both), `competition` if a specific one is named, `metric` ONLY if the text \
states it explicitly (Stableford / Gross / net-vs-par) — leave null if the comparison is \
unqualified (e.g. "the better player" with no competition named).
- `run`: ONLY when the text explicitly states the per-hole result category for the WHOLE \
span — e.g. "four straight pars", "nothing worse than bogey", "all birdies", "level par for \
five holes". Fill `player`, `round`, `span_start_hole`, `span_end_hole`, `basis` (one of: \
"birdie or better", "par", "bogey or better", "par or better", "bogey or worse", "double \
bogey or worse" — pick the closest exact match to what the text says). **Any aggregate figure \
for a range of holes is NOT a run claim, even when it names the hole range or uses golf \
language** — "21 points from holes 11 to 16", "16 points in five holes", "gained five shots to \
net par across holes 9-11", "nine shots to par picked up between the 3rd and the 9th" are all \
TOTALS (points or a net stroke count) across the span, NOT a statement that every hole in it \
individually met one category — a net gain of five over three holes could be one eagle and two \
bogeys. Skip every one of these rather than guess a basis. If in doubt whether a basis is truly \
stated for the WHOLE span, skip the claim.
- `weekday`: a weekday name attached to a specific round. Fill `round`, `weekday`.
- `record`: a personal-best, course-record, or "Nth time" claim. Fill `player`, `round`, \
`competition` (the course name, if that's what the record is on).
- `total`: the FINAL TOURNAMENT total in a competition — all rounds combined, the number that \
decides the competition. Fill `player`, `competition`, `value`. **Do NOT use `total` for**: a \
lead or margin ("leads by seven", "his advantage narrowed to eight") — that is `margin` below; \
a SINGLE ROUND's score, even when it reads like a running total ("41 points", "a round of 96", \
"the best round of the day", "his round two score", "+9 net" for one round) — there is no \
checker for a round score and guessing it is the tournament total produces a false contradiction; \
a PARTIAL-round tally ("11 points in three holes", "10 points down the last three"). If a \
number is anything other than the clean four-round final figure, skip it rather than extract it \
as `total`.
- `margin`: the GAP between a player and a rival — a lead, deficit, or how it changed. Fill \
`player` (whose margin is being described), `competition`, `value` (the gap, as a positive \
integer), `players` (the specific rival, if named) when you can. This type has no checker yet; \
extract it anyway so it's counted rather than silently dropped or misread as a `total`.
"""


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def extract_claims(report_text: str, model: str = EXTRACTION_MODEL) -> list[Claim]:
    """One structured LLM call. Drops any claim whose quote isn't in the text."""
    # thinking=False: on claude-sonnet-5, adaptive thinking reproducibly burns
    # the ENTIRE max_tokens budget on this call and returns no parsed output —
    # confirmed identical at 16000, 20000, and the API's non-streaming ceiling
    # (~21333 tokens; larger requires streaming, which generate_structured
    # doesn't support). This is a pure extraction task with no need for
    # reasoning; disabling thinking outright fixed it (2026-09-26).
    result, _usage = llm.generate_structured(
        EXTRACTOR_SYSTEM, report_text, ClaimList, model=model,
        max_tokens=12000, thinking=False, stage="claim_extraction")
    return [c for c in result.claims if c.quote and c.quote in report_text]


def _claims_path(teg_num: int, round_num: Optional[int] = None) -> str:
    infix = f"round_{round_num}_" if round_num else ""
    return f"{output_dir()}/teg_{teg_num}_{infix}claims.json"


def extract_claims_cached(teg_num: int, report_text: str, *,
                          round_num: Optional[int] = None,
                          model: str = EXTRACTION_MODEL) -> list[Claim]:
    """`extract_claims`, cached to `{stem}_claims.json` keyed on the text hash.

    `llm.py` has no response cache of its own, so this is what keeps a repeat
    `verify --all --claims` free and deterministic: the model only re-runs
    when the report text has actually changed.
    """
    path = _claims_path(teg_num, round_num)
    digest = _sha256(report_text)
    if os.path.exists(path):
        try:
            with open(path) as f:
                cached = json.load(f)
            if cached.get("text_sha256") == digest:
                return [Claim.model_validate(c) for c in cached["claims"]]
        except (OSError, json.JSONDecodeError, KeyError):
            pass  # fall through and re-extract
    claims = extract_claims(report_text, model=model)
    with open(path, "w") as f:
        json.dump({"text_sha256": digest,
                  "claims": [c.model_dump() for c in claims]}, f, indent=2)
    return claims


# ---------------------------------------------------------------------------
# Checking
# ---------------------------------------------------------------------------
@dataclass
class FactBase:
    """Everything a checker needs, loaded once per (teg, round_num)."""
    teg_num: int
    round_num: Optional[int]
    teg_df: pd.DataFrame
    spoon_df: pd.DataFrame
    player_names: dict
    metric: str
    settled: dict


def build_fact_base(teg_num: int, round_num: Optional[int] = None) -> FactBase:
    tl = build_hole_timeline(teg_num, through_round=round_num)
    settled = build_settled_facts(teg_num, through_round=round_num)
    return FactBase(teg_num=teg_num, round_num=round_num, teg_df=tl["teg_df"],
                    spoon_df=tl["spoon_df"], player_names=tl["player_names"],
                    metric=tl["metric"], settled=settled)


def _finding(rule: str, severity: str, detail: str, quote: str) -> Finding:
    return Finding(rule=rule, severity=severity, detail=detail, excerpt=quote, source="claim")


def _unchecked(c: Claim, why: str) -> list[Finding]:
    return [_finding(f"claim_{c.type}", "unchecked", why, c.quote)]


def _check_hole_score(fb: FactBase, c: Claim) -> list[Finding]:
    if not (c.player and c.round and c.hole and c.score is not None):
        return _unchecked(c, "hole_score claim missing player/round/hole/score")
    rows = fb.teg_df[(fb.teg_df["Round"] == c.round) & (fb.teg_df["Hole"] == c.hole)
                     & (fb.teg_df["Player"] == c.player)]
    if rows.empty:
        return _unchecked(c, f"no data for {c.player} R{c.round} H{c.hole}")
    actual = int(rows.iloc[0]["Sc"])
    if actual != c.score:
        return [_finding("claim_hole_score", "error",
                         f"{c.player} scored {actual} at R{c.round} H{c.hole}, "
                         f"claim says {c.score}", c.quote)]
    return []


def _check_weekday(fb: FactBase, c: Claim) -> list[Finding]:
    if not (c.round and c.weekday):
        return _unchecked(c, "weekday claim missing round/weekday")
    actual = fb.settled["round_days"].get(c.round)
    if actual is None:
        return _unchecked(c, f"no weekday data for R{c.round}")
    if actual != c.weekday:
        # `verify.py`'s mechanical check_weekdays already catches a flatly
        # INVENTED day name (one that isn't any round of this TEG) as an
        # error. This checker catches the subtler case — a real day
        # attributed to the wrong round, which is exactly the "Sunday quoted
        # inside an R1 paragraph" shape (item 2) — a warning, since it may
        # also reflect the extractor attributing the wrong round rather than
        # the prose itself being wrong.
        return [_finding("claim_weekday", "warning",
                         f"R{c.round} was {actual}, claim says {c.weekday}", c.quote)]
    return []


def _canonical_competition(fb: FactBase, competition: Optional[str]) -> Optional[str]:
    """Map a free-text competition name ('TEG 18 Trophy', 'the Green Jacket',
    'Wooden Spoon race') to the exact key `settled_facts.py` uses. Claims name
    competitions the way prose does; `final_totals`/`lead_timeline` are keyed
    on the exact strings `_trophy_label`/`JACKET` produce — without this
    normalisation every claim naming "TEG 18 Trophy" (rather than the bare
    trophy label) came back `unchecked` for no real reason. Returns None for
    anything else (a course name, "the field") — those are out of scope here.
    """
    from teg_analysis.reporting.events import JACKET, _trophy_label
    name = (competition or "").lower()
    trophy_label = _trophy_label(fb.metric)
    if competition == trophy_label or "trophy" in name:
        return trophy_label
    if competition == JACKET or "jacket" in name:
        return JACKET
    if "spoon" in name:
        return "Wooden Spoon"
    return None


def _check_total(fb: FactBase, c: Claim) -> list[Finding]:
    if not (c.player and c.competition and c.value is not None):
        return _unchecked(c, "total claim missing player/competition/value")
    if c.round is not None:
        # `final_totals` is the TOURNAMENT total; a claim naming a specific
        # round ("Alex Baker signed for 106 gross" in R2) is a round score,
        # not the running total — checking it against the tournament figure
        # produced a false error ("106" vs "412"). No per-round total is
        # wired into FactBase yet; honest unchecked rather than a wrong check.
        return _unchecked(c, "total claim names a specific round — not checked "
                             "against the tournament total")
    comp = _canonical_competition(fb, c.competition)
    if comp is None:
        return _unchecked(c, f"{c.competition!r} is not a Trophy/Jacket/Spoon total "
                             f"(likely a course or other total, not checked here)")
    comp_totals = fb.settled["final_totals"].get(comp)
    if not comp_totals:
        return _unchecked(c, f"no final totals for {comp!r}")
    row = next((r for r in comp_totals if r["player"] == c.player), None)
    if row is None:
        return _unchecked(c, f"{c.player} not found in {comp} totals")
    # The Jacket is validly stated either as raw strokes ("412 gross") or as
    # gross-vs-par ("+66") — accept either representation as correct rather
    # than assuming the one `settled_facts.py` leads with.
    valid_values = {row["total"]}
    if "total_vs_par" in row and row["total_vs_par"] is not None:
        valid_values.add(row["total_vs_par"])
    # "18 under par net" naturally states the magnitude, not a signed number —
    # the stored NetVP total is signed (-18). Accept the unsigned magnitude of
    # any valid signed value too, so "under"/"clear" phrasing isn't flagged as
    # a false mismatch purely on sign.
    valid_values |= {abs(v) for v in valid_values if isinstance(v, (int, float)) and v < 0}
    if c.value not in valid_values:
        return [_finding("claim_total", "error",
                         f"{c.player}'s {comp} total is {row['total']} gross"
                         + (f" ({row['total_vs_par']:+d} vs par)" if "total_vs_par" in row else "")
                         + f", claim says {c.value}", c.quote)]
    return []


def _rank_source_for(fb: FactBase, competition: str) -> Optional[tuple]:
    """(dataframe, rank_col) for a named competition, or None if unrecognised.

    Wooden Spoon claims use the ORDINARY Trophy rank column, 1 = best — NOT
    `spoon_df`'s derived `_SpoonRank` (1 = worst). That inverted metric exists
    purely for `events.py`'s internal beat labelling ("T2 of 5, 1 pt above
    last"); it is not how prose actually describes a spoon-race standing.
    Real prose always uses ordinary field-position language regardless of
    which competition is being narrated — "dropped him from third to fifth"
    means Trophy rank 5 (of N), not "spoon rank 5". Confirmed against real
    data (2026-09-26, full-corpus sweep): the checker was comparing spoon
    claims against the wrong column and produced 19 false errors, one of
    them literally "was rank 1 in Wooden Spoon ... claim says 4" for a
    player whose real Trophy rank at that hole WAS 4.
    """
    from teg_analysis.reporting.events import JACKET, _trophy_cols, _trophy_label
    comp = _canonical_competition(fb, competition)
    if comp is None:
        return None
    cols = _trophy_cols(fb.metric)
    if comp == JACKET:
        return fb.teg_df, "Rank_GrossVP_TEG"
    # Trophy AND Wooden Spoon both read off the same ordinal standings.
    return fb.teg_df, cols["rank_hole"]


def _check_rank_change(fb: FactBase, c: Claim) -> list[Finding]:
    if not (c.player and c.round and c.hole and c.competition and c.value is not None):
        return _unchecked(c, "rank_change claim missing player/round/hole/competition/value")
    source = _rank_source_for(fb, c.competition)
    if source is None:
        return _unchecked(c, f"unrecognised competition {c.competition!r} for rank_change")
    df, rank_col = source
    rows = df[(df["Round"] == c.round) & (df["Hole"] == c.hole) & (df["Player"] == c.player)]
    if rows.empty:
        return _unchecked(c, f"no data for {c.player} R{c.round} H{c.hole}")
    actual = int(rows.iloc[0][rank_col])
    if actual != c.value:
        return [_finding("claim_rank_change", "error",
                         f"{c.player} was rank {actual} in {c.competition} at "
                         f"R{c.round} H{c.hole}, claim says {c.value}", c.quote)]
    # Technically-correct-but-hides-a-tie: the number matches, but the quote
    # doesn't say the position was shared. Real case: "second to the bottom
    # of the Spoon race" was true as a bare number but the player was tied
    # 2nd with two others — a materially different picture the reader can't
    # get from the number alone.
    hole_snap = df[(df["Round"] == c.round) & (df["Hole"] == c.hole)]
    tie_size = int((hole_snap[rank_col] == actual).sum())
    if tie_size > 1 and not re.search(r"\btied?\b|\blevel\b|\bshares?\b", c.quote, re.IGNORECASE):
        return [_finding("claim_rank_change", "warning",
                         f"{c.player}'s rank {actual} in {c.competition} at R{c.round} "
                         f"H{c.hole} was SHARED with {tie_size - 1} other player(s); "
                         f"the claim doesn't say so", c.quote)]
    return []


def _check_lead_event(fb: FactBase, c: Claim) -> list[Finding]:
    if not (c.player and c.round and c.hole and c.competition):
        return _unchecked(c, "lead_event claim missing player/round/hole/competition")
    comp = _canonical_competition(fb, c.competition)
    if comp is None:
        return _unchecked(c, f"{c.competition!r} is not a recognised Trophy/Jacket/Spoon name")
    changes = fb.settled["lead_timeline"].get(comp)
    if changes is None:
        return _unchecked(c, f"no lead timeline for {comp!r}")
    if c.direction == "drew_level":
        # The settled-facts timeline only records OUTRIGHT changes (by design
        # — it is the tenure ledger, not the play-by-play); a "drew level"
        # claim needs the tie-aware beat data verify.py doesn't have access
        # to here, so this is an honest unchecked rather than a guess.
        return _unchecked(c, "drew_level claims are not checked against the outright-only "
                             "lead timeline")
    at_hole = next((ch for ch in changes if ch["round"] == c.round and ch["hole"] == c.hole), None)
    if c.direction == "took_lead":
        if at_hole is None or at_hole["new_leader"] != c.player:
            return [_finding("claim_lead_event", "error",
                             f"no record of {c.player} taking the {comp} lead at "
                             f"R{c.round} H{c.hole}", c.quote)]
        return []
    if c.direction == "lost_lead":
        if at_hole is None or at_hole["previous_leader"] != c.player:
            return [_finding("claim_lead_event", "error",
                             f"no record of {c.player} losing the {comp} lead at "
                             f"R{c.round} H{c.hole}", c.quote)]
        return []
    return _unchecked(c, f"unrecognised lead_event direction {c.direction!r}")


def _check_comparison(fb: FactBase, c: Claim) -> list[Finding]:
    if not (c.players and len(c.players) == 2):
        return _unchecked(c, "comparison claim missing both players")
    a, b = c.players
    totals = fb.settled["final_totals"]
    if c.metric or c.competition:
        # A specific basis was named — nothing to disambiguate, leave to a
        # future numeric check (not implemented in this first cut).
        return _unchecked(c, "comparison with an explicit metric/competition "
                             "is not numerically checked yet")
    # No basis stated — the exact ambiguity item 4 diagnosed. Check whether the
    # Trophy and Jacket actually agree on who was "better"; if they don't, an
    # unqualified comparison is misleading regardless of which one is meant.
    comps = [k for k in totals if k != "decisive_metric"]
    if len(comps) < 2:
        return _unchecked(c, "fewer than two competitions with totals to compare")
    from teg_analysis.reporting.events import JACKET, _trophy_cols
    # Lower-is-better per competition: Jacket is raw gross strokes (always
    # lower wins); the Trophy flips with era (net-vs-par is lower-is-better,
    # Stableford is higher-is-better) via `_trophy_cols`'s own flag.
    lower_is_better = {JACKET: True,
                      fb.settled["final_totals"].get("decisive_metric"):
                          _trophy_cols(fb.metric)["score_ascending"]}
    winners = set()
    for comp in comps:
        rows = {r["player"]: r["total"] for r in totals[comp]}
        if a not in rows or b not in rows:
            return _unchecked(c, f"{a} or {b} missing from {comp} totals")
        ascending = lower_is_better.get(comp, False)
        better = a if (rows[a] < rows[b]) == ascending else b
        winners.add(better)
    if len(winners) > 1:
        return [_finding("claim_comparison", "warning",
                         f"'better player' claim between {a} and {b} is unqualified, but "
                         f"they lead different competitions ({comps}) — Stableford and Gross "
                         f"measure different things, not the same axis", c.quote)]
    return []


_RUN_BASIS_PRED = {
    "par or better": lambda vp: vp <= 0,
    "birdie or better": lambda vp: vp <= -1,
    "par": lambda vp: vp == 0,
    "bogey or better": lambda vp: vp <= 1,
    "bogey or worse": lambda vp: vp >= 1,
    "double bogey or worse": lambda vp: vp >= 2,
}


def _check_run(fb: FactBase, c: Claim) -> list[Finding]:
    if not (c.player and c.round and c.span_start_hole and c.span_end_hole and c.basis):
        return _unchecked(c, "run claim missing player/round/span/basis")
    pred = _RUN_BASIS_PRED.get((c.basis or "").strip().lower())
    if pred is None:
        return _unchecked(c, f"run basis {c.basis!r} not recognised")
    span = fb.teg_df[(fb.teg_df["Round"] == c.round) & (fb.teg_df["Player"] == c.player)
                     & (fb.teg_df["Hole"].between(c.span_start_hole, c.span_end_hole))]
    n_expected = c.span_end_hole - c.span_start_hole + 1
    if len(span) != n_expected:
        return _unchecked(c, f"expected {n_expected} holes for the span, found {len(span)}")
    bad = span[~span["GrossVP"].apply(pred)]
    if not bad.empty:
        hole = int(bad.iloc[0]["Hole"])
        vp = int(bad.iloc[0]["GrossVP"])
        return [_finding("claim_run", "error",
                         f"{c.player} R{c.round} H{hole} ({vp:+d} vs par) does not satisfy "
                         f"{c.basis!r} — claimed span H{c.span_start_hole}-{c.span_end_hole}",
                         c.quote)]
    return []


_CHECKERS = {
    "hole_score": _check_hole_score,
    "weekday": _check_weekday,
    "total": _check_total,
    "rank_change": _check_rank_change,
    "lead_event": _check_lead_event,
    "comparison": _check_comparison,
    "run": _check_run,
    # "record" has no checker yet — falls through to the default below.
}


def check_claim_list(fb: FactBase, claims: list[Claim]) -> list[Finding]:
    """Run every claim through its checker. An uncovered type is `unchecked`,
    never silently dropped or reported as passed."""
    out: list[Finding] = []
    for c in claims:
        checker = _CHECKERS.get(c.type)
        if checker is None:
            out.extend(_unchecked(c, f"claim type {c.type!r} has no checker yet"))
        else:
            out.extend(checker(fb, c))
    return out


def check_claims(teg_num: int, *, round_num: Optional[int] = None,
                 label: str = "storylinefirst", text: Optional[str] = None,
                 model: str = EXTRACTION_MODEL) -> list[Finding]:
    """Extract (cached) + check every claim in one report. The one paid path
    in this module — everything else here is free once claims are cached."""
    if text is None:
        from teg_analysis.io import read_text_file
        path = report_path(teg_num, round_num=round_num, label=label)
        try:
            text = read_text_file(path)
        except Exception:
            with open(path) as f:
                text = f.read()
    claims = extract_claims_cached(teg_num, text, round_num=round_num, model=model)
    fb = build_fact_base(teg_num, round_num=round_num)
    return check_claim_list(fb, claims)


# ---------------------------------------------------------------------------
# Repair (WP5) — surgical, per-paragraph, always re-verified
# ---------------------------------------------------------------------------
REPAIR_CONTRACT = """You are correcting exactly ONE factual error in a paragraph of an \
already-published, finished golf report. This is a surgical repair, not a rewrite:

- Change ONLY what is necessary to fix the stated error. Every other sentence, and every \
part of the corrected sentence that isn't wrong, stays exactly as published — same wording, \
same order, same voice, same length.
- Do not add commentary about the correction, and do not hedge or flag that a change was \
made. The reader must not be able to tell this paragraph was ever wrong.
- Use ONLY the correct fact given below. Do not introduce any other number, name, hole, or \
claim that isn't already in the paragraph or in the correction itself.

Return ONLY the corrected paragraph text — no preamble, no quotation marks, no explanation.
"""


def find_paragraph(report_text: str, quote: str) -> Optional[str]:
    """The `\n\n`-delimited paragraph containing a claim's verbatim quote."""
    for para in report_text.split("\n\n"):
        if quote in para:
            return para
    return None


def repair_paragraph(paragraph: str, correction: str,
                     model: str = "claude-opus-5") -> Tuple[str, object]:
    """One targeted rewrite call: a published paragraph + the correct fact in,
    a corrected paragraph out. `correction` should be a plain-English
    statement of what's wrong and what the true fact is (`Finding.detail` is
    usually sufficient, written by hand where more context helps)."""
    system = "\n\n".join((REPAIR_CONTRACT, prompts.SENTENCE_DISCIPLINE))
    user = f"PUBLISHED PARAGRAPH:\n{paragraph}\n\nERROR AND CORRECT FACT:\n{correction}"
    text, usage = llm.generate_text(system, user, model=model, max_tokens=2000,
                                    thinking=False, stage="claim_repair")
    return text.strip(), usage


def repair_report(teg_num: int, report_text: str, corrections: list[tuple], *,
                  round_num: Optional[int] = None,
                  model: str = "claude-opus-5") -> dict:
    """Repair a set of confirmed paragraph errors and re-verify each fix.

    `corrections` is a list of `(quote, correction_text)` — `quote` locates
    the paragraph (via `find_paragraph`), `correction_text` is what's wrong
    and what's true. Each paragraph is repaired independently, then the whole
    edited text is re-checked with `verify_report` (mechanical — the free
    check, run on every repair since it's the fast net for a repair call
    introducing a beat id, an em-dash, an invented mechanism, etc.) against
    the ORIGINAL, to isolate faults this pass introduced rather than ones
    already present (same `(rule, detail)` diff pattern `restyle_voice` uses).
    **Does not write anything to disk** — review `result["diffs"]` before
    deciding to publish; writing is a deliberate, separate step.

    Returns {"text": new_text, "diffs": [{"quote", "before", "after"}],
    "skipped": [quote, ...], "new_mechanical_findings": [str, ...]}.
    """
    from teg_analysis.reporting.verify import verify_report

    text = report_text
    diffs = []
    skipped = []
    for quote, correction in corrections:
        para = find_paragraph(text, quote)
        if para is None:
            skipped.append(quote)
            continue
        new_para, _usage = repair_paragraph(para, correction, model=model)
        if new_para == para:
            skipped.append(quote)
            continue
        text = text.replace(para, new_para, 1)
        diffs.append({"quote": quote, "before": para, "after": new_para})

    before = {(f.rule, f.detail) for f in verify_report(teg_num, text=report_text, round_num=round_num)}
    after = verify_report(teg_num, text=text, round_num=round_num)
    new_mechanical = [str(f) for f in after if (f.rule, f.detail) not in before]
    return {"text": text, "diffs": diffs, "skipped": skipped,
            "new_mechanical_findings": new_mechanical}
