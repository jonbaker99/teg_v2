"""Phase F unified backfill orchestrator.

Generates the canonical set of reports for a list of TEGs: one tournament
report + one report per round. Computes `build_notable_events` and
`build_venue_context` once per TEG and reuses them across the tournament and
round runs — that's the heaviest pure-Python step in the pipeline.

Idempotent: skips a report when its `_final.md` already exists (override with
`force=True`). Logs per-call usage if the LLM stages return it; aggregate cost
tally printed at the end.

Runs on claude.ai plan usage by default: each model call hands off through
`data/llm_mailbox` and waits for an answer (see `llm.py` and `mailbox.py`).
`--provider api` calls the Anthropic API instead and bills per token. The loop is
the same either way.

Usage:
    from teg_analysis.reporting.backfill import backfill_all
    summary = backfill_all(range(8, 19))   # TEGs 8-18, both tournament + rounds
    summary = backfill_all([8, 9, 10], scope="tournament", force=True)

    python -m teg_analysis.reporting.backfill --tegs 14
    python -m teg_analysis.reporting.backfill --tegs 2-18 --provider api
    python -m teg_analysis.reporting.backfill --tegs 14 --variant gpt5 --force
"""

from __future__ import annotations

import os
import time
from contextlib import nullcontext
from typing import Iterable, Literal

from teg_analysis.reporting import llm, mailbox
from teg_analysis.reporting.paths import (
    ENV_VARIANT,
    get_variant,
    output_dir,
    write_manifest,
)
from teg_analysis.reporting.events import build_notable_events
from teg_analysis.reporting.venue import build_venue_context
from teg_analysis.reporting.story_plan import build_story_plan
from teg_analysis.reporting.authoring import (
    generate_dry_draft,
    report_around_draft,
    repetition_lint,
)
from teg_analysis.reporting.render import style_report
from teg_analysis.reporting.verify import verify_report, format_findings
from teg_analysis.reporting.round_report import generate_round_report

Scope = Literal["tournament", "rounds", "both"]


def _tournament_exists(teg_num: int) -> bool:
    return os.path.exists(f"{output_dir()}/teg_{teg_num}_report_final.md")


def _round_exists(teg_num: int, round_num: int) -> bool:
    return os.path.exists(f"{output_dir()}/teg_{teg_num}_round_{round_num}_report_final.md")


def backfill_teg(teg_num: int, *, force: bool = False, scope: Scope = "both",
                 style: bool = True) -> dict:
    """Generate the chosen scope for a single TEG. Returns per-call paths + timings.

    `style=False` stops at `teg_N_report_final.md` — the prose — and skips
    `style_report`, which is the step that injects the deterministic blocks
    (per-round standings, the at-a-glance box, and the "Personal bests and TEG
    records" appendix) into `teg_N_report_styled.md`. Use it when you want to
    read or compare the writing itself without the surrounding furniture.
    D3 verification still runs either way: it checks the prose, not the blocks.
    """
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
            linted, _ = repetition_lint(around["text"], label=f"teg{teg_num}")
            final = f"{output_dir()}/teg_{teg_num}_report_final.md"
            with open(final, "w") as f:
                f.write(linted)
            styled = style_report(teg_num) if style else None
            # D3 — verify the finished prose against the data. Findings are
            # reported, never raised: a report that trips a check is still
            # written, but it can no longer ship unnoticed.
            findings = verify_report(teg_num)
            if findings:
                print(format_findings(findings, teg_num=teg_num))
            out["tournament"] = {
                "final": final,
                "styled": styled,
                "secs": round(time.time() - ts, 1),
                "verify": [str(f) for f in findings],
            }
        else:
            out["tournament"] = {"skipped": f"{output_dir()}/teg_{teg_num}_report_final.md"}

    if scope in ("rounds", "both"):
        for r in range(1, total_rounds + 1):
            if force or not _round_exists(teg_num, r):
                ts = time.time()
                rout = generate_round_report(teg_num, r, events_cache=events, venue_cache=venue)
                rfindings = verify_report(teg_num, round_num=r)
                if rfindings:
                    print(format_findings(rfindings, teg_num=teg_num))
                out["rounds"].append({
                    "round": r,
                    "final": rout["final_path"],
                    "styled": rout["styled_path"],
                    "secs": round(time.time() - ts, 1),
                    "verify": [str(f) for f in rfindings],
                })
            else:
                out["rounds"].append({
                    "round": r,
                    "skipped": f"{output_dir()}/teg_{teg_num}_round_{r}_report_final.md",
                })
    return out


def backfill_all(teg_nums: Iterable[int], *, force: bool = False,
                 scope: Scope = "both", style: bool = True) -> list:
    """Backfill a range of TEGs. Prints per-TEG progress to stdout.

    `style=False` stops at the final prose — see `backfill_teg`.

    Provider-agnostic: under `api` this calls the API for every stage, under
    `agent` (the default) each stage hands off through the mailbox and waits.
    The loop itself is identical — that is the point of the provider switch.
    """
    results = []
    teg_list = list(teg_nums)
    provider = llm.get_provider()
    variant = get_variant()
    print(f"backfill: {len(teg_list)} TEGs, scope={scope}, force={force}, "
          f"style={style}, provider={provider}"
          + (f", variant={variant}" if variant else ""))
    if provider == llm.PROVIDER_AGENT:
        # Start the run now rather than lazily on the first call, so the run id
        # can be printed up front. With two runs live, the responder needs it.
        run = mailbox.active_run()
        if run.responder == mailbox.RESPONDER_MANUAL:
            print(f"  paste mode — run {run.run_id}. The skill will NOT touch this "
                  f"run. Answer each prompt with:\n"
                  f"    python -m teg_analysis.reporting.mailbox show --run {run.run_id}\n"
                  f"    python -m teg_analysis.reporting.mailbox answer <dir> --file reply.txt",
                  flush=True)
        else:
            print(f"  plan usage — run {run.run_id}. Answer the prompts with the "
                  f"`teg-report-respond` skill in Claude Code (same directory), or "
                  f"by hand:\n"
                  f"    python -m teg_analysis.reporting.mailbox show --run {run.run_id}",
                  flush=True)
    started = time.time()
    try:
        for i, teg in enumerate(teg_list, 1):
            print(f"  [{i}/{len(teg_list)}] TEG {teg} …", flush=True)
            r = backfill_teg(teg, force=force, scope=scope, style=style)
            # one-line summary
            t_done = "skip" if (r["tournament"] and "skipped" in r["tournament"]) else (
                "done" if r["tournament"] else "—")
            rounds_done = sum(1 for x in r["rounds"] if "final" in x)
            rounds_skipped = sum(1 for x in r["rounds"] if "skipped" in x)
            print(f"    cache {r['cache_secs']}s | tournament: {t_done} | rounds: "
                  f"{rounds_done} done, {rounds_skipped} skip", flush=True)
            results.append(r)
    finally:
        # Mark the run finished even on failure, so a responder does not sit
        # waiting on a run that has stopped.
        mailbox.reset_active_run()

    write_manifest({
        "provider": provider,
        "model": llm.DEFAULT_MODEL if provider == llm.PROVIDER_API else "session model (not pinned)",
        "tegs": teg_list,
        "scope": scope,
        "force": force,
        "secs": round(time.time() - started, 1),
    })
    return results


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def parse_teg_spec(spec: str) -> list:
    """Parse `--tegs` into a list: `14`, `2-18`, `8,9,14`, or a mix of those."""
    out: list = []
    for chunk in spec.replace(" ", "").split(","):
        if not chunk:
            continue
        if "-" in chunk:
            lo, _, hi = chunk.partition("-")
            out.extend(range(int(lo), int(hi) + 1))
        else:
            out.append(int(chunk))
    if not out:
        raise ValueError(f"no TEGs in {spec!r}")
    # Preserve order, drop duplicates.
    seen, ordered = set(), []
    for t in out:
        if t not in seen:
            seen.add(t)
            ordered.append(t)
    return ordered


def main(argv=None) -> int:
    import argparse

    p = argparse.ArgumentParser(
        prog="python -m teg_analysis.reporting.backfill",
        description="Generate tournament and round reports.",
        epilog="Runs on claude.ai plan usage by default (prompts hand off through "
               "data/llm_mailbox). Pass --provider api to spend API credit instead.",
    )
    p.add_argument("--tegs", required=True,
                   help="which TEGs: 14, 2-18, or 8,9,14")
    p.add_argument("--scope", default="both", choices=["tournament", "rounds", "both"])
    p.add_argument("--force", action="store_true",
                   help="regenerate even when a final report already exists")
    p.add_argument("--no-style", action="store_true",
                   help="stop at the prose; skip the deterministic styled blocks")
    p.add_argument("--plan", action="store_true",
                   help="run on claude.ai plan usage instead of the API: prompts "
                        "hand off through data/llm_mailbox and the "
                        "`teg-report-respond` skill answers them")
    p.add_argument("--paste", metavar="NAME",
                   help="hand prompts off for you to paste into another model "
                        "(ChatGPT, Gemini, claude.ai). Implies --plan, keeps the "
                        "skill's hands off this run, and writes output to "
                        "data/commentary/variants/NAME/")
    p.add_argument("--provider", choices=list(llm.PROVIDERS),
                   help=f"the long way round: override {llm.ENV_PROVIDER} for this "
                        f"run (default: {llm.DEFAULT_PROVIDER})")
    p.add_argument("--variant",
                   help="write to data/commentary/variants/<name>/ instead of the "
                        "canonical set — use for model comparisons")
    args = p.parse_args(argv)

    if args.provider and (args.plan or args.paste):
        p.error("--provider conflicts with --plan/--paste; use one or the other")

    variant = args.paste or args.variant
    if variant:
        os.environ[ENV_VARIANT] = variant
    if args.paste:
        # A paste run must be invisible to the responder skill, or a Claude Code
        # session will cheerfully answer the prompts meant for ChatGPT and the
        # output lands in a directory labelled as another model's work.
        os.environ[mailbox.ENV_RESPONDER] = mailbox.RESPONDER_MANUAL

    provider = args.provider or (llm.PROVIDER_AGENT if (args.plan or args.paste) else None)
    tegs = parse_teg_spec(args.tegs)
    ctx = llm.use_provider(provider) if provider else nullcontext()
    with ctx:
        backfill_all(tegs, force=args.force, scope=args.scope, style=not args.no_style)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
