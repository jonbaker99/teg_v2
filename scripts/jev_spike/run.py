"""Jev spike: can TypeSafe's Jev catch the four semantic faithfulness faults
that `verify.py` cannot check mechanically?

Temporary. See teg_analysis/reporting/JEV_ASSESSMENT.md. Delete this folder
once the verdict is recorded there.

    python scripts/jev_spike/run.py --dry-run     # regex baseline + one sample payload, no network
    TYPESAFE_API_KEY=... python scripts/jev_spike/run.py

Each labelled paragraph is sent once, with all four rules asked as yes/no
("noul") questions in the same request. The state carries the facts the rules
depend on: which course each round was played on, and the recorded player
relationships. Results are scored against the hand labels in labels.json and
against a keyword-regex baseline.
"""

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

HERE = Path(__file__).resolve().parent
LABELS = HERE / "labels.json"
RESULTS = HERE / "results.json"

BASE_URL = os.environ.get("TYPESAFE_BASE_URL", "https://api.typesafe.ai")
MODEL = os.environ.get("TYPESAFE_DEFAULT_MODEL", "jev-latest")
PRICE_PER_M_INPUT = 0.042  # USD, launch pricing; output is free

RULES = ("same_hole", "paradox", "chaos", "relationship")

QUESTIONS = {
    "same_hole": {
        "type": "noul",
        "instructions": (
            "Does the paragraph treat a hole played in one round as the same physical hole as the "
            "same-numbered hole played in a different round on a DIFFERENT course? Use "
            "tournament_facts.rounds to see which course each round was on. The same hole within "
            "one round, or the same hole number across rounds played on the same course, is fine."
        ),
        "criteria": {
            "true": "Links same-numbered holes from rounds on different courses as if one hole",
            "false": "No such link, or the rounds were on the same course",
        },
    },
    "paradox": {
        "type": "noul",
        "instructions": (
            "Does the paragraph present the gap between a player's Stableford result (points, the "
            "Trophy, the Wooden Spoon) and their Gross result (strokes, the Green Jacket) as a "
            "paradox, contradiction, puzzle, mystery or injustice, rather than as normal handicapping?"
        ),
        "criteria": {
            "true": "Frames the Stableford/Gross gap as paradoxical or inexplicable",
            "false": "No such framing, or treats it as normal handicapping",
        },
    },
    "chaos": {
        "type": "noul",
        "instructions": (
            "Does the paragraph describe routine lead changes early in a round or tournament as "
            "chaos, turmoil, bedlam or high drama? Chaos words about blow-ups or bad scoring, with "
            "no lead changes involved, are fine."
        ),
        "criteria": {
            "true": "Early lead changes framed as chaos or drama",
            "false": "No such framing",
        },
    },
    "relationship": {
        "type": "noul",
        "instructions": (
            "Does the paragraph state a relationship between players, or a detail of a relationship "
            "(for example who is older), that is not in tournament_facts.player_relationships? "
            "Figurative uses of family words are fine."
        ),
        "criteria": {
            "true": "States a relationship or relationship detail not in the recorded list",
            "false": "Only recorded relationships, or none",
        },
    },
}

# Keyword baseline: the grep a developer would add to verify.py from past
# incidents. Deliberately excludes the paraphrases used in the seeded items,
# which exist to test exactly what a grep misses.
REGEX = {
    "same_hole": re.compile(r"same hole", re.I),
    "paradox": re.compile(r"paradox|puzzl", re.I),
    "chaos": re.compile(r"chao", re.I),
    "relationship": re.compile(r"\b(older|younger|elder) (baker )?brother|cousin", re.I),
}


def load_facts():
    """Round -> course per TEG, plus recorded relationships, from the real data."""
    import pandas as pd
    from teg_analysis.constants import PLAYER_RELATIONSHIPS

    df = pd.read_parquet(ROOT / "data" / "all-data.parquet", columns=["TEGNum", "Round", "Course"])
    rounds = {}
    for (teg, rnd), g in df.drop_duplicates(["TEGNum", "Round"]).groupby(["TEGNum", "Round"]):
        rounds.setdefault(int(teg), []).append({"round": int(rnd), "course": g["Course"].iloc[0]})
    rels = [f"{' and '.join(r['players'])} are {r['relationship']}" for r in PLAYER_RELATIONSHIPS]
    return rounds, rels


def build_state(item, rounds, rels):
    return {
        "report_paragraph": item["text"],
        "tournament_facts": {
            "teg": item["teg"],
            "rounds": rounds.get(item["teg"], []),
            "player_relationships": rels,
        },
    }


def call_jev(state, api_key):
    body = json.dumps({"model": MODEL, "state": state, "questions": QUESTIONS}).encode()
    req = urllib.request.Request(
        f"{BASE_URL}/v1/systemone",
        data=body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )
    t0 = time.perf_counter()
    with urllib.request.urlopen(req, timeout=30) as resp:
        payload = json.load(resp)
    return payload, time.perf_counter() - t0


def auroc(scores, labels):
    pos = [s for s, y in zip(scores, labels) if y]
    neg = [s for s, y in zip(scores, labels) if not y]
    if not pos or not neg:
        return None
    wins = sum((p > n) + 0.5 * (p == n) for p in pos for n in neg)
    return wins / (len(pos) * len(neg))


def prf(pred, labels):
    tp = sum(p and y for p, y in zip(pred, labels))
    fp = sum(p and not y for p, y in zip(pred, labels))
    fn = sum(y and not p for p, y in zip(pred, labels))
    prec = tp / (tp + fp) if tp + fp else None
    rec = tp / (tp + fn) if tp + fn else None
    return tp, fp, fn, prec, rec


def fmt(x):
    return "n/a" if x is None else f"{x:.2f}"


def report(items, jev=None, threshold=0.5):
    lines = ["| Rule | Pos/N | Regex P / R | Jev P / R @0.5 | Jev AUROC |", "|---|---|---|---|---|"]
    for r in RULES:
        y = [it["labels"][r] for it in items]
        _, _, _, rp, rr = prf([bool(REGEX[r].search(it["text"])) for it in items], y)
        jp = jr = ja = None
        if jev:
            s = [jev[it["id"]][r] for it in items]
            _, _, _, jp, jr = prf([v >= threshold for v in s], y)
            ja = auroc(s, y)
        lines.append(f"| {r} | {sum(y)}/{len(y)} | {fmt(rp)} / {fmt(rr)} | {fmt(jp)} / {fmt(jr)} | {fmt(ja)} |")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="no network: regex baseline and a sample payload")
    args = ap.parse_args()

    items = json.loads(LABELS.read_text())
    rounds, rels = load_facts()

    if args.dry_run:
        print(report(items))
        print("\nSample request state:")
        print(json.dumps(build_state(items[0], rounds, rels), indent=1, ensure_ascii=False))
        return

    api_key = os.environ.get("TYPESAFE_API_KEY")
    if not api_key:
        sys.exit("TYPESAFE_API_KEY is not set")

    jev, raw, latencies, tokens = {}, {}, [], 0
    for it in items:
        try:
            payload, dt = call_jev(build_state(it, rounds, rels), api_key)
        except urllib.error.HTTPError as e:
            sys.exit(f"{it['id']}: HTTP {e.code} {e.read()[:200]!r}")
        answers = payload["answers"]
        jev[it["id"]] = {r: answers[r]["noul"] for r in RULES}
        raw[it["id"]] = payload
        latencies.append(dt)
        tokens += (payload.get("usage") or {}).get("input_tokens", 0)

    RESULTS.write_text(json.dumps({"model": MODEL, "scores": jev, "raw": raw}, indent=1))
    latencies.sort()
    print(report(items, jev))
    print(f"\n{len(items)} requests / median {latencies[len(latencies) // 2] * 1000:.0f} ms / "
          f"max {latencies[-1] * 1000:.0f} ms / {tokens} input tokens / "
          f"${tokens * PRICE_PER_M_INPUT / 1e6:.5f}")
    print("\nMisses and false alarms at 0.5:")
    for it in items:
        for r in RULES:
            s, y = jev[it["id"]][r], it["labels"][r]
            if (s >= 0.5) != y:
                print(f"  {it['id']:18} {r:12} label={y!s:5} p={s:.2f}  {it['note']}")


if __name__ == "__main__":
    main()
