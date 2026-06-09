"""Sanity-check the regenerated TEG reports against fabrication risks
and produce density/length stats vs the pretighten baselines and the
standalone tightened references.

Run from repo root:
    venv/bin/python scripts/sanity_check_tightened.py
"""
from __future__ import annotations

import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

from teg_analysis.constants import PLAYER_RELATIONSHIPS
from teg_analysis.core.data_loader import load_all_data
from teg_analysis.reporting.venue import build_venue_context

TEGS = [10, 11, 13, 14, 18]
OUT_DIR = pathlib.Path("data/commentary")

# Surnames whose duplication in a TEG could prompt the LLM to infer a relationship.
RELATIONSHIP_TERMS = [
    "brother", "brothers",
    "cousin", "cousins",
    "father", "son", "dad",
    "uncle", "nephew", "niece",
    "twin", "twins",
    "in-law", "in-laws",
    "sibling", "siblings",
]

# Weekday vocabulary we expect to be VERIFIED against venue.rounds[i].weekday.
WEEKDAY_NAMES = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]


def players_in_teg(teg: int) -> set[str]:
    df = load_all_data()
    sub = df[df["TEGNum"] == teg]
    names = sorted(set(sub["Player"].astype(str)))
    return set(names)


def weekdays_in_venue(teg: int) -> list[str]:
    venue = build_venue_context(teg)
    return [r.get("weekday", "").lower() for r in venue.get("rounds", [])]


def check_beat_ids(text: str) -> list[str]:
    hits = re.findall(r"\b(?:b|cr)\d{2,}\b", text)
    return hits


def check_fabricated_players(text: str, valid: set[str]) -> list[str]:
    """Heuristic: scan for full-name patterns 'Firstname Surname' that aren't
    in the valid set. We only flag if the candidate doesn't appear in the
    valid roster and isn't part of a known place/course name.
    """
    suspects: list[str] = []
    # Match "Firstname Surname" capitalised pairs
    candidates = set(re.findall(r"\b([A-Z][a-z]+)\s+([A-Z][a-z]+)\b", text))
    valid_names = {n.lower() for n in valid}
    valid_firsts = {n.split()[0].lower() for n in valid if " " in n}
    valid_lasts = {n.split()[-1].lower() for n in valid if " " in n}
    for first, last in candidates:
        full = f"{first} {last}".lower()
        if full in valid_names:
            continue
        # If neither first nor last is a known player part, skip — likely a venue/course.
        if first.lower() not in valid_firsts and last.lower() not in valid_lasts:
            continue
        # If just one part matches, that's normal (single-name reference). Only
        # flag if BOTH halves are player parts AND the combined name isn't valid —
        # i.e. plausibly a fabricated combination.
        if first.lower() in valid_firsts and last.lower() in valid_lasts:
            suspects.append(f"{first} {last}")
    return sorted(set(suspects))


def check_invented_relationships(text: str) -> list[str]:
    """Flag lines mentioning a relationship term. Caller cross-checks each
    against PLAYER_RELATIONSHIPS to confirm legitimacy."""
    flags = []
    pat = re.compile(r"\b(" + "|".join(RELATIONSHIP_TERMS) + r")\b", re.IGNORECASE)
    for i, line in enumerate(text.splitlines(), 1):
        if pat.search(line):
            flags.append(f"L{i}: {line.strip()[:200]}")
    return flags


def check_weekdays(text: str, valid_weekdays: list[str]) -> dict:
    """Find weekday mentions and check they appear in venue.rounds[i].weekday."""
    used = re.findall(r"\b(" + "|".join(w.capitalize() for w in WEEKDAY_NAMES) + r")\b", text)
    used_set = {u.lower() for u in used}
    valid_set = {w for w in valid_weekdays if w}
    fabricated = used_set - valid_set
    return {"used": sorted(used_set), "valid": sorted(valid_set),
            "fabricated": sorted(fabricated), "count_total": len(used)}


def check_week_framings(text: str) -> list[str]:
    """Find 'week' mentions and split into idiomatic vs problematic.

    Idiomatic patterns to allow (cosmetic noise, not violations):
      - "of the week"
      - "week prior" / "week earlier" / "week later" / "weeks ago"
      - "for the week" (golf-week-of-... style)
    Problematic:
      - "a week long" / "all week" / "this week" / "the week's"
      - "over the week"
    """
    flags = []
    idiomatic_pat = re.compile(
        r"\b(?:of the week|week (?:prior|earlier|later|ago)s?|weeks (?:prior|ago|earlier|later))\b",
        re.IGNORECASE,
    )
    for i, line in enumerate(text.splitlines(), 1):
        if re.search(r"\bweek(?:s|'s|ly)?\b", line, re.IGNORECASE):
            classification = "IDIOMATIC" if idiomatic_pat.search(line) else "REVIEW"
            flags.append(f"L{i} [{classification}]: {line.strip()[:200]}")
    return flags


def density_stats(text: str) -> dict:
    paragraphs = [p for p in text.split("\n\n") if p.strip() and not p.lstrip().startswith("#")]
    em_dashes_per_para = [p.count("—") for p in paragraphs]
    over_2 = sum(1 for n in em_dashes_per_para if n >= 3)
    return {
        "paragraphs": len(paragraphs),
        "em_dashes_total": sum(em_dashes_per_para),
        "em_dashes_per_para_avg": round(sum(em_dashes_per_para) / max(1, len(paragraphs)), 2),
        "paragraphs_with_3plus_em_dashes": over_2,
        "words": len(text.split()),
        "lines": len(text.splitlines()),
    }


def main():
    relationships_allowed = []
    for r in PLAYER_RELATIONSHIPS:
        a, b = r["players"]
        relationships_allowed.append(f"{a} ↔ {b} ({r['relationship']})")
    print("Allowed relationships:", relationships_allowed)
    print()

    for teg in TEGS:
        final = OUT_DIR / f"teg_{teg}_report_final.md"
        pretight = OUT_DIR / f"teg_{teg}_report_pretighten.md"
        tightened_ref = OUT_DIR / f"teg_{teg}_report_tightened.md"

        new_text = final.read_text()
        pre_text = pretight.read_text() if pretight.exists() else ""
        ref_text = tightened_ref.read_text() if tightened_ref.exists() else ""

        valid_players = players_in_teg(teg)
        valid_weekdays = weekdays_in_venue(teg)

        beat_ids = check_beat_ids(new_text)
        fabricated_players = check_fabricated_players(new_text, valid_players)
        relationship_flags = check_invented_relationships(new_text)
        weekday_report = check_weekdays(new_text, valid_weekdays)
        week_flags = check_week_framings(new_text)

        new_stats = density_stats(new_text)
        pre_stats = density_stats(pre_text) if pre_text else {}
        ref_stats = density_stats(ref_text) if ref_text else {}

        print("=" * 72)
        print(f"TEG {teg}")
        print("=" * 72)
        print(f"valid players ({len(valid_players)}): {sorted(valid_players)}")
        print(f"valid weekdays: {valid_weekdays}")
        print()
        print("CHECKS:")
        print(f"  beat-ID leaks: {beat_ids if beat_ids else 'CLEAN'}")
        print(f"  fabricated player names: {fabricated_players if fabricated_players else 'CLEAN'}")
        print(f"  weekday usage: used={weekday_report['used']} valid={weekday_report['valid']} "
              f"fabricated={weekday_report['fabricated']} total_mentions={weekday_report['count_total']}")
        print(f"  relationship-term lines ({len(relationship_flags)}):")
        for f in relationship_flags:
            print(f"    {f}")
        print(f"  week mentions ({len(week_flags)}):")
        for f in week_flags:
            print(f"    {f}")
        print()
        print("DENSITY STATS:")
        print(f"  new        : {new_stats}")
        if pre_stats:
            print(f"  pretighten : {pre_stats}")
        if ref_stats:
            print(f"  tightened* : {ref_stats}  (* standalone tightening pass, reference only)")
        print()


if __name__ == "__main__":
    main()
