"""One-off: regenerate TEG reports for 10/11/13/14/18 end-to-end
with the new ECONOMY rules baked into WRITER_SYSTEM.

Run from repo root: venv/bin/python scripts/regen_tightened_writers.py
"""
from __future__ import annotations

import pathlib
import sys
import time
import traceback

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

from teg_analysis.reporting import build_story_plan
from teg_analysis.reporting.authoring import (
    generate_dry_draft,
    report_around_draft,
    repetition_lint,
)
from teg_analysis.reporting.render import style_report

TEGS = [10, 11, 13, 14, 18]
OUT_DIR = "data/commentary"

def log(msg: str) -> None:
    print(msg, flush=True)

def run_one(teg: int) -> dict:
    t0 = time.time()
    log(f"\n=== TEG {teg}: start ===")

    log(f"  [1/5] build_story_plan…")
    t = time.time()
    plan = build_story_plan(teg)["plan"]
    log(f"        plan ok ({time.time()-t:.1f}s)")

    log(f"  [2/5] generate_dry_draft…")
    t = time.time()
    dry = generate_dry_draft(teg, plan)
    log(f"        dry draft ok ({time.time()-t:.1f}s)")

    log(f"  [3/5] report_around_draft…")
    t = time.time()
    rpt = report_around_draft(teg, plan, dry["text"])
    log(f"        around draft ok ({time.time()-t:.1f}s)")

    log(f"  [4/5] repetition_lint…")
    t = time.time()
    linted, _ = repetition_lint(rpt["text"])
    final_path = f"{OUT_DIR}/teg_{teg}_report_final.md"
    with open(final_path, "w") as f:
        f.write(linted)
    log(f"        linted+saved ok ({time.time()-t:.1f}s) -> {final_path}")

    log(f"  [5/5] style_report…")
    t = time.time()
    styled = style_report(teg)
    log(f"        styled ok ({time.time()-t:.1f}s) -> {styled}")

    elapsed = time.time() - t0
    log(f"=== TEG {teg}: done in {elapsed:.1f}s ===")
    return {"teg": teg, "elapsed": elapsed}

def main():
    results = []
    overall = time.time()
    for teg in TEGS:
        try:
            results.append(run_one(teg))
        except Exception as e:
            log(f"!!! TEG {teg} FAILED: {e!r}")
            traceback.print_exc()
            results.append({"teg": teg, "error": repr(e)})
    log("\n=== SUMMARY ===")
    for r in results:
        if "error" in r:
            log(f"  TEG {r['teg']}: FAIL — {r['error']}")
        else:
            log(f"  TEG {r['teg']}: {r['elapsed']:.1f}s")
    log(f"TOTAL: {time.time()-overall:.1f}s")
    return 0 if all("elapsed" in r for r in results) else 1

if __name__ == "__main__":
    sys.exit(main())
