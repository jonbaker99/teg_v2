"""Phase F unified backfill orchestrator.

Generates the canonical set of reports for a list of TEGs: one tournament
report + one report per round. Computes `build_notable_events` and
`build_venue_context` once per TEG and reuses them across the tournament and
round runs — that's the heaviest pure-Python step in the pipeline.

Idempotent: skips a report when its `_final.md` already exists (override with
`force=True`). Logs per-call usage if the LLM stages return it; aggregate cost
tally printed at the end.

Usage:
    from teg_analysis.reporting.backfill import backfill_all
    summary = backfill_all(range(8, 19))   # TEGs 8-18, both tournament + rounds
    summary = backfill_all([8, 9, 10], scope="tournament", force=True)
"""

from __future__ import annotations

import os
import time
from typing import Iterable, Literal

from teg_analysis.reporting.events import build_notable_events
from teg_analysis.reporting.venue import build_venue_context
from teg_analysis.reporting.story_plan import build_story_plan
from teg_analysis.reporting.authoring import (
    generate_dry_draft,
    report_around_draft,
    repetition_lint,
)
from teg_analysis.reporting.render import style_report
from teg_analysis.reporting.round_report import generate_round_report

OUTPUT_DIR = "data/commentary"

Scope = Literal["tournament", "rounds", "both"]


def _tournament_exists(teg_num: int) -> bool:
    return os.path.exists(f"{OUTPUT_DIR}/teg_{teg_num}_report_final.md")


def _round_exists(teg_num: int, round_num: int) -> bool:
    return os.path.exists(f"{OUTPUT_DIR}/teg_{teg_num}_round_{round_num}_report_final.md")


def backfill_teg(teg_num: int, *, force: bool = False, scope: Scope = "both") -> dict:
    """Generate the chosen scope for a single TEG. Returns per-call paths + timings."""
    t0 = time.time()
    events = build_notable_events(teg_num)
    venue = build_venue_context(teg_num)
    total_rounds = len(venue.get("rounds", []))
    cache_secs = time.time() - t0

    out: dict = {
        "teg": teg_num,
        "total_rounds": total_rounds,
        "cache_secs": round(cache_secs, 1),
        "tournament": None,
        "rounds": [],
    }

    if scope in ("tournament", "both"):
        if force or not _tournament_exists(teg_num):
            ts = time.time()
            plan_out = build_story_plan(teg_num, events_cache=events, venue_cache=venue)
            plan = plan_out["plan"]
            dry = generate_dry_draft(teg_num, plan, events_cache=events, venue_cache=venue)
            around = report_around_draft(teg_num, plan, dry["text"])
            linted, _ = repetition_lint(around["text"])
            final = f"{OUTPUT_DIR}/teg_{teg_num}_report_final.md"
            with open(final, "w") as f:
                f.write(linted)
            styled = style_report(teg_num)
            out["tournament"] = {
                "final": final,
                "styled": styled,
                "secs": round(time.time() - ts, 1),
            }
        else:
            out["tournament"] = {"skipped": f"{OUTPUT_DIR}/teg_{teg_num}_report_final.md"}

    if scope in ("rounds", "both"):
        for r in range(1, total_rounds + 1):
            if force or not _round_exists(teg_num, r):
                ts = time.time()
                rout = generate_round_report(teg_num, r, events_cache=events, venue_cache=venue)
                out["rounds"].append({
                    "round": r,
                    "final": rout["final_path"],
                    "styled": rout["styled_path"],
                    "secs": round(time.time() - ts, 1),
                })
            else:
                out["rounds"].append({
                    "round": r,
                    "skipped": f"{OUTPUT_DIR}/teg_{teg_num}_round_{r}_report_final.md",
                })
    return out


def backfill_all(teg_nums: Iterable[int], *, force: bool = False,
                 scope: Scope = "both") -> list:
    """Backfill a range of TEGs. Prints per-TEG progress to stdout."""
    results = []
    teg_list = list(teg_nums)
    print(f"backfill: {len(teg_list)} TEGs, scope={scope}, force={force}")
    for i, teg in enumerate(teg_list, 1):
        print(f"  [{i}/{len(teg_list)}] TEG {teg} …", flush=True)
        r = backfill_teg(teg, force=force, scope=scope)
        # one-line summary
        t_done = "skip" if (r["tournament"] and "skipped" in r["tournament"]) else (
            "done" if r["tournament"] else "—")
        rounds_done = sum(1 for x in r["rounds"] if "final" in x)
        rounds_skipped = sum(1 for x in r["rounds"] if "skipped" in x)
        print(f"    cache {r['cache_secs']}s | tournament: {t_done} | rounds: "
              f"{rounds_done} done, {rounds_skipped} skip", flush=True)
        results.append(r)
    return results
