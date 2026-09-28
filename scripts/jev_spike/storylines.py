"""Jev spike, part 2: does Jev rank storylines the way the Opus editor does?

Temporary. See teg_analysis/reporting/JEV_ASSESSMENT.md.

    TYPESAFE_API_KEY=... python scripts/jev_spike/storylines.py

Scores every storyline in data/commentary/*storyline_plan.json on compellingness
and humour, then compares Jev with the editor's self-scored compelling_score and
humour_score. There is no human ground truth, so this measures agreement with
Opus only.
"""

import json
import os
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
RESULTS = HERE / "storyline_results.json"
BASE_URL = os.environ.get("TYPESAFE_BASE_URL", "https://api.typesafe.ai")
MODEL = os.environ.get("TYPESAFE_DEFAULT_MODEL", "jev-latest")
PRICE_PER_M_INPUT = 0.042

QUESTIONS = {
    "compelling": {
        "type": "score",
        "instructions": (
            "This is one storyline planned for a newspaper-style report on an amateur golf "
            "tournament between old friends. How compelling will it be to the players who read it?"
        ),
        "criteria": [
            "Dull: routine result, nothing a reader would remember",
            "Fair: some interest, but predictable",
            "Good: a clear story with real stakes or a turn",
            "Gripping: a story the players will retell for years",
        ],
    },
    "humour": {
        "type": "score",
        "instructions": "How much comic potential does this storyline have for a gently mocking report?",
        "criteria": [
            "None: played straight",
            "Some: a light moment",
            "Strong: clearly funny material",
            "Superb: farce the players will laugh about",
        ],
    },
}
SLOTS = ("trophy_storyline", "jacket_storyline", "spoon_storyline")


def storylines():
    for f in sorted((ROOT / "data" / "commentary").glob("*storyline_plan.json")):
        plan = json.loads(f.read_text())
        items = [(s, plan.get(s)) for s in SLOTS] + [
            (f"discovered_{i}", d) for i, d in enumerate(plan.get("discovered_storylines") or [])
        ]
        for slot, s in items:
            if s and s.get("compelling_score") is not None:
                yield f.stem, slot, s


def state(s):
    keys = ("chosen_headline", "standfirst", "subject", "why_it_matters", "shape")
    return {k: s[k] for k in keys if s.get(k)}


def expected(ans):
    """Expected level from Jev's probabilities, rescaled to 0-1."""
    p = ans["probabilities"]
    return sum(int(k) * v for k, v in p.items()) / (len(p) - 1)


def call(st, key):
    body = json.dumps({"model": MODEL, "state": st, "questions": QUESTIONS}).encode()
    req = urllib.request.Request(
        f"{BASE_URL}/v1/systemone", data=body,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    )
    t0 = time.perf_counter()
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r), time.perf_counter() - t0


def ranks(xs):
    order = sorted(range(len(xs)), key=lambda i: xs[i])
    r = [0.0] * len(xs)
    i = 0
    while i < len(xs):
        j = i
        while j + 1 < len(xs) and xs[order[j + 1]] == xs[order[i]]:
            j += 1
        for k in range(i, j + 1):
            r[order[k]] = (i + j) / 2
        i = j + 1
    return r


def spearman(a, b):
    ra, rb = ranks(a), ranks(b)
    n = len(a)
    ma, mb = sum(ra) / n, sum(rb) / n
    cov = sum((x - ma) * (y - mb) for x, y in zip(ra, rb))
    va = sum((x - ma) ** 2 for x in ra) ** 0.5
    vb = sum((y - mb) ** 2 for y in rb) ** 0.5
    return cov / (va * vb)


def main():
    key = os.environ.get("TYPESAFE_API_KEY") or sys.exit("TYPESAFE_API_KEY is not set")
    rows, lat, tokens = [], [], 0
    for plan, slot, s in storylines():
        payload, dt = call(state(s), key)
        a = payload["answers"]
        rows.append({
            "plan": plan, "slot": slot, "headline": s.get("chosen_headline"),
            "opus_compelling": s["compelling_score"], "opus_humour": s.get("humour_score"),
            "jev_compelling": round(expected(a["compelling"]), 3),
            "jev_humour": round(expected(a["humour"]), 3),
        })
        lat.append(dt)
        tokens += (payload.get("usage") or {}).get("input_tokens", 0)
    RESULTS.write_text(json.dumps(rows, indent=1))

    print(f"{len(rows)} storylines from {len({r['plan'] for r in rows})} plans")
    print("compelling Spearman:", round(spearman([r["opus_compelling"] for r in rows], [r["jev_compelling"] for r in rows]), 2))
    h = [r for r in rows if r["opus_humour"] is not None]
    if h:
        print(f"humour Spearman (n={len(h)}):", round(spearman([r["opus_humour"] for r in h], [r["jev_humour"] for r in h]), 2))

    # Does Jev pick the same top storyline in each plan? Ties in Opus score count as a match.
    plans = {}
    for r in rows:
        plans.setdefault(r["plan"], []).append(r)
    same = total = 0
    for rs in plans.values():
        if len(rs) < 2:
            continue
        total += 1
        best = max(r["opus_compelling"] for r in rs)
        same += max(rs, key=lambda r: r["jev_compelling"])["opus_compelling"] == best
    print(f"Jev's top pick is also Opus's top (or tied top): {same}/{total}")

    by_slot = {}
    for r in rows:
        by_slot.setdefault(r["slot"].split("_")[0], []).append(r)
    for k, rs in by_slot.items():
        print(f"  {k:10} n={len(rs):3} mean opus {sum(r['opus_compelling'] for r in rs)/len(rs):.1f}/10  "
              f"mean jev {sum(r['jev_compelling'] for r in rs)/len(rs):.2f}")
    lat.sort()
    print(f"median {lat[len(lat)//2]*1000:.0f} ms / {tokens} input tokens / ${tokens*PRICE_PER_M_INPUT/1e6:.5f}")


if __name__ == "__main__":
    main()
