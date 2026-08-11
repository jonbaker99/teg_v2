"""H10(a) -- selection-weight profiler. Pure Python, no LLM, no API key needed.

Sweeps candidate (importance, rarity, entertainment) weight vectors over the
cached `build_notable_events()` output across TEGs 9-18 and reports, per
setting:

- type mix of the top-20 (the baseline figure quoted in EXPERIMENTS.md ->
  H10 is "big_blowup is 106/200 top-20 slots, 53%")
- tone balance -- disasters vs achievements vs neutral
- coverage -- distinct players and rounds represented in the top-20
- mandatory survival at the real production cut (`assemble_bundle`'s
  top_n=50 + force-add of mandatory beats) -- must stay 100%
- churn vs the (1,1,1) baseline -- top-20 beat overlap

`build_notable_events()` is the slow part (a few seconds per TEG); it is
computed once per TEG and reused across all weight settings.

Run from repo root:
    python scripts/weight_profiler.py
"""
from __future__ import annotations

import pathlib
import sys
from collections import Counter

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

from teg_analysis.reporting.events import build_notable_events

TEGS = range(9, 19)

SETTINGS = {
    "current (1,1,1)": (1.0, 1.0, 1.0),
    "importance-led (2.0,0.5,0.5)": (2.0, 0.5, 0.5),
    "fast (1.5,0.8,0.7)": (1.5, 0.8, 0.7),
    "archive (1.0,1.3,1.3)": (1.0, 1.3, 1.3),
}
BASELINE = "current (1,1,1)"

DISASTER_TYPES = {"cold_stretch", "collapse_after_steady", "big_blowup",
                   "spoon_change", "wooden_spoon"}
ACHIEVEMENT_TYPES = {"hot_stretch", "recovery", "eagle", "hole_in_one",
                      "trophy_win", "jacket_win", "jacket_pb",
                      "feat_eagles", "feat_hole_in_one"}
NEUTRAL_TYPES = {"lead_change", "round_leadership"}
# Tone depends on outcome, not type -- classify from the headline text.
MIXED_TYPES = {"round_player", "round_player_gross"}

# Mirrors assemble_bundle's MANDATORY_TYPES / mandatory test exactly
# (story_plan.py) so the profiler's force-add logic matches production.
MANDATORY_TYPES = {"hole_in_one", "eagle", "feat_hole_in_one", "feat_eagles",
                    "trophy_win", "jacket_win", "wooden_spoon"}

TOP_N_HEADLINE = 20   # matches the EXPERIMENTS.md "106/200" methodology
TOP_N_BUNDLE = 50     # matches assemble_bundle's production trim


def tone(e) -> str:
    if e.type in DISASTER_TYPES:
        return "disaster"
    if e.type in ACHIEVEMENT_TYPES:
        return "achievement"
    if e.type in MIXED_TYPES:
        h = e.headline.lower()
        if "worst" in h:
            return "disaster"
        if "best" in h:
            return "achievement"
        return "neutral"
    return "neutral"


def is_mandatory(e) -> bool:
    is_double_figure = bool(e.holes) and (e.holes[0].get("sc", 0) >= 10)
    return e.type in MANDATORY_TYPES or e.rarity >= 7 or is_double_figure


def weighted_score(e, weights) -> float:
    wi, wr, we = weights
    return wi * e.importance + wr * e.rarity + we * e.entertainment


def rank(events, weights):
    return sorted(events, key=lambda e: weighted_score(e, weights), reverse=True)


def profile_teg(events):
    """Return {setting_name: {...}} for one TEG's cached events."""
    mandatory_ids = {id(e) for e in events if is_mandatory(e)}
    out = {}
    for name, weights in SETTINGS.items():
        ranked = rank(events, weights)
        top20 = ranked[:TOP_N_HEADLINE]
        keep_ids = {id(e) for e in ranked[:TOP_N_BUNDLE]} | mandatory_ids
        out[name] = {
            "top20": top20,
            "top20_ids": {id(e) for e in top20},
            "mandatory_total": len(mandatory_ids),
            "mandatory_survived": len(mandatory_ids & keep_ids),
        }
    return out


def aggregate(all_teg_profiles):
    """Combine per-TEG profiles into one summary per setting."""
    summary = {name: {
        "type_counts": Counter(),
        "tone_counts": Counter(),
        "players": set(),
        "rounds": set(),
        "n_top20_slots": 0,
        "mandatory_total": 0,
        "mandatory_survived": 0,
        "churn_overlap": [],   # per-TEG fraction of top20 shared with baseline
    } for name in SETTINGS}

    for teg_num, profile in all_teg_profiles.items():
        baseline_ids = profile[BASELINE]["top20_ids"]
        for name, data in profile.items():
            s = summary[name]
            for e in data["top20"]:
                s["type_counts"][e.type] += 1
                s["tone_counts"][tone(e)] += 1
                s["players"].update(e.players)
                if e.round is not None:
                    s["rounds"].add((teg_num, e.round))
            s["n_top20_slots"] += len(data["top20"])
            s["mandatory_total"] += data["mandatory_total"]
            s["mandatory_survived"] += data["mandatory_survived"]
            if name != BASELINE:
                overlap = len(data["top20_ids"] & baseline_ids)
                denom = len(data["top20_ids"]) or 1
                s["churn_overlap"].append(overlap / denom)
    return summary


def print_report(summary):
    for name in SETTINGS:
        s = summary[name]
        n = s["n_top20_slots"]
        print(f"\n=== {name} ===")
        print(f"top-20 slots across {len(TEGS)} TEGs: {n}")
        print("Type mix:")
        for etype, cnt in s["type_counts"].most_common():
            print(f"  {etype:24s} {cnt:4d}  ({100*cnt/n:.1f}%)")
        print("Tone balance:")
        for t in ("disaster", "achievement", "neutral"):
            cnt = s["tone_counts"].get(t, 0)
            print(f"  {t:12s} {cnt:4d}  ({100*cnt/n:.1f}%)")
        print(f"Coverage: {len(s['players'])} distinct players, "
              f"{len(s['rounds'])} distinct (teg, round) pairs")
        mt, ms = s["mandatory_total"], s["mandatory_survived"]
        pct = 100 * ms / mt if mt else 100.0
        print(f"Mandatory survival: {ms}/{mt} ({pct:.1f}%)")
        if s["churn_overlap"]:
            mean_overlap = sum(s["churn_overlap"]) / len(s["churn_overlap"])
            print(f"Churn vs baseline: mean top-20 overlap "
                  f"{100*mean_overlap:.0f}% (per-TEG: "
                  f"{[f'{100*x:.0f}%' for x in s['churn_overlap']]})")


def main():
    all_teg_profiles = {}
    for teg_num in TEGS:
        print(f"Computing beats for TEG {teg_num}...", flush=True)
        events = build_notable_events(teg_num)
        all_teg_profiles[teg_num] = profile_teg(events)
    summary = aggregate(all_teg_profiles)
    print_report(summary)


if __name__ == "__main__":
    main()
