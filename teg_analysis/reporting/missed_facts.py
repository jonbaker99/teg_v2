"""WP6 — missed-fact detection: must-mention facts a report never mentions.

The claim checker (`claims.py`) can only judge what a report *says*. TEG 18's
item 6 was the opposite failure: Gregg Williams's R4 84 equalled David
Mullin's R3 84 Stadium course record, and the report never said so. It said
"His 84 in round four was his best score on the Stadium Course" — the number
is there, the record is not.

So code lists the facts a report must carry, from the same detectors the
bundle uses (no model call), and looks for each one in the text:

- **Course records** set or equalled, low and high
  (`course_history.detect_course_records`) — round and tournament reports.
- **The decisive lead change** — the moment the final outright leader took the
  lead for good, Trophy and Jacket (`settled_facts.build_hole_timeline`). A
  tournament report always has one per competition; a round report only when
  that change happened in its own round.
- **All-time streak / score-count records** and **personal-best/worst
  streaks** (`milestone_records`) — tournament reports only.

A fact is **covered** when one block (a paragraph or a heading) holds its
number AND a keyword for that fact type, and the player is named in the block,
in its section heading, or on a cached claim whose quote sits in the block (the
extractor resolves "he" to a name; `{stem}_claims.json` is read, never
written). An equalled record needs an equal-word ("equalled", "matched",
"tied") plus "record" or the other holder's name — "best score on the Stadium"
is a personal best, not the record.

Every miss is a **warning** (`rule="missed_fact"`): the matcher is lexical, so
it can misjudge, and a warning still reaches `_verify.json` and the CLI.

    from teg_analysis.reporting.missed_facts import check_missed_facts
    findings = check_missed_facts(18, round_num=4)

CLI: python -m teg_analysis.reporting.verify --all --rounds --missed
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Optional

import pandas as pd

from teg_analysis.reporting.paths import output_dir
from teg_analysis.reporting.verify import Finding, _NUMBER_WORDS

_WORD_FOR = {v: k for k, v in _NUMBER_WORDS.items()}

_ORDINAL_WORDS = {
    1: "first", 2: "second", 3: "third", 4: "fourth", 5: "fifth", 6: "sixth",
    7: "seventh", 8: "eighth", 9: "ninth", 10: "tenth", 11: "eleventh",
    12: "twelfth", 13: "thirteenth", 14: "fourteenth", 15: "fifteenth",
    16: "sixteenth", 17: "seventeenth", 18: "eighteenth",
}

# Keyword alternations per fact type. Kept as plain regex fragments so a noisy
# one is easy to see and tune from the sweep output.
_EQUAL = r"equal(?:l?ed|s|l?ing)?|match(?:ed|es|ing)?|tied|ties|tying|level with|same as|shares?|shared"
_WIRE = r"wire[\s-]to[\s-]wire|never headed|never relinquish\w*|never (?:once )?(?:trailed|behind)"
_LEAD = rf"lead(?:s|ing)?|led|ahead|in front|on top|top of|clear|advantage|held|{_WIRE}"
_KEYWORDS = {
    "course_record_low": r"record|lowest (?:round|score|gross|ever)",
    "course_record_high": r"record|worst|highest",
    "streak_record": r"record|all[\s-]time|in TEG history|ever",
    "score_count_record": r"record|all[\s-]time|most|in TEG history|ever",
    "streak_personal_best": r"best|longest|career|personal|ever",
    "streak_personal_worst": r"worst|longest|career|personal|ever",
}


@dataclass
class MustMention:
    """One fact the report should carry."""
    kind: str                  # detector type, e.g. "course_record_equalled", "lead_change"
    player: str                # proper case
    summary: str               # human-facing, for the warning detail
    numbers: list = field(default_factory=list)   # any one must appear (as regex)
    # Alternative keyword sets: the fact is covered when EVERY entry of ANY one
    # set matches. An entry is a regex (searched in the block) or
    # `("or_heading", regex)` (the block or its section heading).
    keyword_sets: list = field(default_factory=list)
    round: Optional[int] = None
    hole: Optional[int] = None
    competition: Optional[str] = None


@dataclass
class Block:
    text: str
    heading: str               # the section heading it sits under ("" before the first)
    claim_players: set = field(default_factory=set)


# ---------------------------------------------------------------------------
# Listing the facts
# ---------------------------------------------------------------------------
@lru_cache(maxsize=1)
def _load_df() -> pd.DataFrame:
    from teg_analysis.core.data_loader import load_all_data
    return load_all_data(exclude_teg_50=True, exclude_incomplete_tegs=False)


def _num_patterns(n: int) -> list:
    pats = [rf"(?<![\d.]){n}(?![\d])"]
    if n in _WORD_FOR:
        pats.append(rf"\b{_WORD_FOR[n]}\b")
    return pats


def _hole_patterns(h: int) -> list:
    suf = "th" if 10 <= h % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(h % 10, "th")
    pats = [rf"\b{h}{suf}\b", rf"\bhole {h}\b", rf"\b{_ORDINAL_WORDS[h]}\b"]
    if h == 1:
        pats += [r"\bopening hole\b", r"\bfirst hole\b", r"\bstart\b"]
    return pats


def _round_patterns(r: int, max_round: int, weekday: Optional[str]) -> str:
    pats = [rf"\bR{r}\b", rf"\bround {r}\b", rf"\bround {_WORD_FOR.get(r, r)}\b",
            rf"\b{_ORDINAL_WORDS.get(r, '')} round\b"]
    if r == 1:
        pats += [r"\bopening round\b", r"\bopening day\b"]
    if r == max_round:
        pats += [r"\bfinal round\b", r"\blast round\b", r"\bclosing round\b",
                 r"\bfinal day\b"]
    if weekday:
        pats.append(rf"\b{weekday}\b")
    return "|".join(pats)


def _record_holders(df: pd.DataFrame, course: str, gross: int, teg_num: int,
                    rnd: int) -> list:
    """(player, teg, round) for every earlier round of `gross` on `course` —
    the record being equalled. "Earlier" includes the same round: the
    detector walks one round's cards in row order, so of two identical
    record cards in a round one is "set" and the other "equalled"."""
    from teg_analysis.reporting.course_history import _proper, _round_aggregates
    rounds = _round_aggregates(df[df["Course"] == course])
    prior = rounds[(rounds["TEGNum"] < teg_num)
                   | ((rounds["TEGNum"] == teg_num) & (rounds["Round"] <= rnd))]
    prior = prior[prior["Gross"] == gross]
    return [(_proper(r["Player"]), int(r["TEGNum"]), int(r["Round"]))
            for _, r in prior.iterrows()]


def _course_facts(teg_num: int, round_num: Optional[int], df: pd.DataFrame) -> list:
    from teg_analysis.reporting.course_history import detect_course_records
    events = detect_course_records(teg_num, df, through_round=round_num)
    if round_num:
        events = [e for e in events if e["round"] == round_num]
    facts = []
    for e in events:
        kind = e["type"]
        if kind in ("course_record_equalled", "course_record_high_equalled"):
            high = kind == "course_record_high_equalled"
            holders = _record_holders(df, e["course"], e["gross"], teg_num, e["round"])
            me = e["player"]
            others = sorted({p for p, _, _ in holders if p != me})
            names = [rf"\b{re.escape(n.split()[-1])}\b" for n in others]
            base = r"record|worst|highest" if high else r"record"
            sets = [[_EQUAL, "|".join([base] + names)]]
            if any(p == me for p, _, _ in holders):
                # Matching his own earlier card: "matched his TEG 13 figure of 100".
                sets.append([_EQUAL])
            if any(p != me and (t, r) == (teg_num, e["round"]) for p, t, r in holders):
                # Co-record in the same round: "broken twice, by Mullin and Neumann".
                sets.append([_KEYWORDS["course_record_high" if high else "course_record_low"]])
        else:
            sets = [[_KEYWORDS[kind]]]
        facts.append(MustMention(
            kind=kind, player=e["player"], summary=e["summary_fact"],
            numbers=_num_patterns(e["gross"]), keyword_sets=sets, round=e["round"]))
    return facts


def _lead_facts(teg_num: int, round_num: Optional[int], df: pd.DataFrame) -> list:
    from teg_analysis.reporting.events import JACKET
    from teg_analysis.reporting.settled_facts import build_hole_timeline
    from teg_analysis.reporting.venue import build_venue_context

    tl = build_hole_timeline(teg_num, all_data=df, through_round=round_num)
    names = tl["player_names"]
    max_round = int(tl["teg_df"]["Round"].max())
    try:
        weekdays = {int(r["round"]): r.get("weekday")
                    for r in build_venue_context(teg_num).get("rounds", [])}
    except Exception:
        weekdays = {}

    facts = []
    for comp in (tl["trophy_label"], JACKET):
        timeline = tl["timelines"][comp]
        ordered = timeline["ordered"]
        if not ordered or timeline["leader_at"].get(ordered[-1]) is None:
            continue  # tied at the end — decided off the data (override), skip
        final = timeline["leader_at"][ordered[-1]]
        # The decisive moment is the start of the final leader's last
        # unbroken OUTRIGHT spell — a tie ends it, so going clear again from
        # level counts. (Deliberately stricter than `settled_facts`'s
        # lead_timeline, where a tie is not a change: TEG 12's Patterson "took
        # the lead" at R3 H4 but was level again after three rounds.)
        took = ordered[-1]
        for key in reversed(ordered):
            if timeline["leader_at"].get(key) != final:
                break
            took = key
        rnd, hole = took
        if round_num and rnd != round_num:
            continue
        player = names.get(final, final)
        state = f"led it after R{round_num}" if round_num else "won it"
        sets = [[_LEAD, "|".join(_hole_patterns(hole))]]
        if not round_num:
            sets[0].append(("or_heading", _round_patterns(rnd, max_round, weekdays.get(rnd))))
        if all(timeline["leader_at"].get(k) in (final, None) for k in ordered):
            sets.append([_WIRE])  # nobody else ever led outright: "wire to wire"
        facts.append(MustMention(
            kind="lead_change", player=player, competition=comp, round=rnd, hole=hole,
            summary=(f"{player} went clear in the {comp} for good at R{rnd} H{hole} "
                     f"and {state}"),
            numbers=[], keyword_sets=sets))
    return facts


def _milestone_facts(teg_num: int, df: pd.DataFrame) -> list:
    from teg_analysis.reporting import milestone_records as mr
    facts = []
    for e in (mr.detect_streak_records(teg_num, df)
              + mr.detect_personal_streak_extremes(teg_num, df)):
        facts.append(MustMention(
            kind=e["type"], player=e["player"], summary=e["summary_fact"],
            numbers=_num_patterns(int(e["value"])), keyword_sets=[[_KEYWORDS[e["type"]]]],
            round=e.get("round")))
    for e in mr.detect_score_count_records(teg_num, df):
        facts.append(MustMention(
            kind=e["type"], player=e["player"], summary=e["summary_fact"],
            numbers=_num_patterns(int(e["count"])), keyword_sets=[[_KEYWORDS[e["type"]]]]))
    return facts


def list_must_mention(teg_num: int, round_num: Optional[int] = None,
                      df: Optional[pd.DataFrame] = None) -> list[MustMention]:
    """Every fact the report for (teg_num, round_num) should mention."""
    if df is None:
        df = _load_df()
    facts = _course_facts(teg_num, round_num, df) + _lead_facts(teg_num, round_num, df)
    if not round_num:
        facts += _milestone_facts(teg_num, df)
    return facts


# ---------------------------------------------------------------------------
# Looking for them
# ---------------------------------------------------------------------------
def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s.replace("’", "'")).strip()


def split_blocks(text: str, claims: Optional[list] = None) -> list[Block]:
    """Paragraphs and headings, each tagged with its section heading and the
    players any cached claim quoted from it names."""
    blocks: list[Block] = []
    heading = ""
    for chunk in re.split(r"\n\s*\n", text):
        for part in _split_headings(chunk):
            part = part.strip()
            if not part:
                continue
            if part.startswith("#"):
                heading = part.lstrip("#").strip()
                blocks.append(Block(text=heading, heading=heading))
            else:
                blocks.append(Block(text=_norm(part), heading=heading))
    for c in claims or []:
        quote = _norm(c.get("quote") or "")
        if not quote:
            continue
        who = {p for p in [c.get("player")] + list(c.get("players") or []) if p}
        for b in blocks:
            if quote in b.text:
                b.claim_players |= who
    return blocks


def _split_headings(chunk: str) -> list:
    """A heading line glued to a paragraph (no blank line) is still a heading."""
    out, buf = [], []
    for line in chunk.splitlines():
        if line.lstrip().startswith("#"):
            if buf:
                out.append("\n".join(buf))
                buf = []
            out.append(line)
        else:
            buf.append(line)
    if buf:
        out.append("\n".join(buf))
    return out


def _name_patterns(player: str, all_players: list) -> list:
    """Full name, plus surname / first name when no other player shares it."""
    parts = player.split()
    pats = [re.escape(player)]
    others = [p for p in all_players if p != player]
    if len(parts) > 1:
        if not any(o.split()[-1] == parts[-1] for o in others):
            pats.append(rf"\b{re.escape(parts[-1])}\b")
        if not any(o.split()[0] == parts[0] for o in others):
            pats.append(rf"\b{re.escape(parts[0])}\b")
    return pats


def _names_player(block: Block, player: str, all_players: list) -> bool:
    if player in block.claim_players:
        return True
    pats = _name_patterns(player, all_players)
    return any(re.search(p, block.text) or re.search(p, block.heading) for p in pats)


def _entry_matches(entry, block: Block) -> bool:
    if isinstance(entry, tuple):
        _, pat = entry
        return bool(re.search(pat, block.text, flags=re.IGNORECASE)
                    or re.search(pat, block.heading, flags=re.IGNORECASE))
    return bool(re.search(entry, block.text, flags=re.IGNORECASE))


def covering_block(fact: MustMention, blocks: list[Block],
                   all_players: list) -> Optional[Block]:
    """The first block that covers `fact`, or None."""
    for b in blocks:
        if fact.numbers and not any(re.search(p, b.text) for p in fact.numbers):
            continue
        if not any(all(_entry_matches(k, b) for k in ks) for ks in fact.keyword_sets):
            continue
        if _names_player(b, fact.player, all_players):
            return b
    return None


def _load_claims(teg_num: int, round_num: Optional[int]) -> list:
    """Cached claims, read-only. A stale cache (hash mismatch) is still used:
    only quotes that are verbatim in the current text attach to a block."""
    infix = f"round_{round_num}_" if round_num else ""
    path = f"{output_dir()}/teg_{teg_num}_{infix}claims.json"
    if not os.path.exists(path):
        return []
    try:
        with open(path) as f:
            return json.load(f).get("claims", [])
    except (OSError, json.JSONDecodeError):
        return []


def check_missed_facts(teg_num: int, round_num: Optional[int] = None,
                       text: Optional[str] = None, label: str = "storylinefirst",
                       df: Optional[pd.DataFrame] = None,
                       claims: Optional[list] = None) -> list[Finding]:
    """One `missed_fact` warning per must-mention fact the report never covers.

    `text` / `claims` override reading the report and `{stem}_claims.json`.
    """
    from teg_analysis.reporting.verify import report_path

    if text is None:
        with open(report_path(teg_num, round_num=round_num, label=label)) as f:
            text = f.read()
    if df is None:
        df = _load_df()
    if claims is None:
        claims = _load_claims(teg_num, round_num)

    from teg_analysis.reporting.course_history import _proper
    all_players = sorted({_proper(p) for p in df[df["TEGNum"] == teg_num]["Player"].unique()})
    blocks = split_blocks(text, claims)
    findings = []
    for fact in list_must_mention(teg_num, round_num=round_num, df=df):
        if covering_block(fact, blocks, all_players) is None:
            findings.append(Finding(
                rule="missed_fact", severity="warning",
                detail=f"not mentioned: {fact.summary}", source="missed"))
    return findings
