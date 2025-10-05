"""
Tournament Commentary Generator V2 - Multi-Pass Story Generation

This module implements the complete two-level multi-pass pipeline:
- Level 1: Process all data types (6 Python passes)
- Level 2: Generate round stories + tournament synthesis (4-5 LLM passes)

Output: story_notes.md files ready for final report generation
"""

import sys
import os
import json
import time
import math, hashlib
import pandas as pd
from pathlib import Path
from typing import Any, Dict, Optional, List
from collections import defaultdict, deque

# ========================
# Config
# ========================

# Anthropic org limit reference (from your 429)
RATE_BUDGET_INPUT_TOKENS_PER_MIN = 30000
RATE_SAFETY = 0.90  # adjust 0.85–0.95 as you like

DRY_RUN = True   # set to False when you're ready to actually call the LLM
DEBUG   = True   # master switch for all debug prints & debug file saves

# Small helper for gated printing
def dprint(*args, **kwargs):
    if DEBUG:
        print(*args, **kwargs)

# ========================
# Local imports
# ========================

# Add parent directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from pattern_analysis import process_all_data_types
from data_loader import load_round_data, get_round_ending_context
from prompts import ROUND_STORY_PROMPT, TOURNAMENT_SYNTHESIS_PROMPT
from utils import get_teg_rounds
import anthropic

# ========================
# Utilities & Inspection
# ========================

def _safe_len(x: Any) -> int:
    try:
        return len(x)  # lists, dicts, strings
    except Exception:
        return 1

def _is_list_of_dicts(x: Any) -> bool:
    return isinstance(x, list) and (len(x) == 0 or isinstance(x[0], dict))

def _json_size(obj: Any) -> int:
    try:
        return len(json.dumps(obj, default=str))
    except Exception:
        return 0

def write_round_inspection(
    teg_num: int,
    round_num: int,
    round_data: Dict[str, Any],
    previous_context: Any,
    prompt_text: str
) -> None:
    """
    Writes an inspection bundle for this round (only when DEBUG=True).
    """
    if not DEBUG:
        return

    base = Path("streamlit/commentary/inspection") / f"teg_{teg_num}" / f"round_{round_num}"
    base.mkdir(parents=True, exist_ok=True)

    # 1) Full round_data (pretty + min)
    with open(base / "round_data_full_pretty.json", "w", encoding="utf-8") as f:
        json.dump(round_data, f, indent=2, ensure_ascii=False, default=str)
    with open(base / "round_data_full_min.json", "w", encoding="utf-8") as f:
        json.dump(round_data, f, separators=(",", ":"), ensure_ascii=False, default=str)

    # 2) Previous context
    with open(base / "previous_context.json", "w", encoding="utf-8") as f:
        if previous_context is None:
            f.write('"First round of the tournament"')
        else:
            json.dump(previous_context, f, indent=2, ensure_ascii=False, default=str)

    # 3) Prompt text (exact as sent)
    with open(base / "prompt.txt", "w", encoding="utf-8") as f:
        f.write(prompt_text)

    # 4) Summary (per top-level key)
    lines = []
    lines.append(f"Summary for TEG {teg_num}, Round {round_num}")
    lines.append("=" * 60)
    lines.append(f"Top-level keys: {list(round_data.keys())}\n")

    for k, v in round_data.items():
        t = type(v).__name__
        n = _safe_len(v)
        jsz = _json_size(v)
        lines.append(f"- {k}: type={t}, len={n}, approx_json_size={jsz:,} chars")

    totalsize = _json_size(round_data)
    lines.append(f"\nTOTAL approx_json_size: {totalsize:,} chars")

    # 5) Previews (first 2 items) for list-of-dicts sections
    previews_dir = base / "previews"
    previews_dir.mkdir(exist_ok=True)
    for k, v in round_data.items():
        if _is_list_of_dicts(v):
            preview = v[:2]
            with open(previews_dir / f"{k}_preview.json", "w", encoding="utf-8") as f:
                json.dump(preview, f, indent=2, ensure_ascii=False, default=str)
            lines.append(f"Preview saved: previews/{k}_preview.json (first 2 items)")

    with open(base / "summary.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

def _est_tokens(text: str) -> int:
    """Rough token estimate (chars/4 ≈ tokens)."""
    return math.ceil(len(text) / 4)

def _blob_stats(label: str, text: str) -> str:
    est = _est_tokens(text)
    sha = hashlib.sha1(text.encode("utf-8")).hexdigest()[:10]
    return f"{label}: {len(text):,} chars ~{est:,} tok (sha:{sha})"

def write_synthesis_inspection(teg_num: int, round_stories: list, prompt_text: str, tournament_summary_df: pd.DataFrame):
    if not DEBUG:
        return
    base = Path("streamlit/commentary/inspection") / f"teg_{teg_num}" / "synthesis"
    base.mkdir(parents=True, exist_ok=True)
    with open(base / "round_stories_preview.txt", "w", encoding="utf-8") as f:
        for i, s in enumerate(round_stories, 1):
            f.write(f"Round {i}: {len(s)} chars\n")
            f.write(s[:300] + ("\n...\n\n" if len(s) > 300 else "\n\n"))
    with open(base / "tournament_summary.json", "w", encoding="utf-8") as f:
        json.dump(tournament_summary_df.to_dict("records"), f, indent=2, ensure_ascii=False, default=str)
    with open(base / "prompt.txt", "w", encoding="utf-8") as f:
        f.write(prompt_text)

# ========================
# Lossless compaction (merge gross/net + drop nulls)
# ========================

def _drop_null_keys(obj):
    """Recursively drop keys with value None/NaN from dicts/lists."""
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            if v is None:
                continue
            if isinstance(v, float) and math.isnan(v):
                continue
            out[k] = _drop_null_keys(v)
        return out
    elif isinstance(obj, list):
        return [_drop_null_keys(x) for x in obj]
    else:
        return obj

def _merge_gross_net_windows(patts: list) -> list:
    """
    Merge duplicate windows that differ only by scoring_type ('gross'/'net')
    and have identical hole_scores. Keep differentiation under metrics.net / metrics.gross.
    """
    def key_of(p):
        return (p.get("player"), p.get("round"), p.get("holes"), p.get("window_size"))

    def hole_sig(p):
        return json.dumps(p.get("hole_scores", []), sort_keys=True)

    groups = defaultdict(list)
    for p in patts:
        groups[key_of(p)].append(p)

    merged = []
    for _, items in groups.items():
        kinds = {i.get("scoring_type") for i in items}
        if len(items) == 2 and kinds == {"gross", "net"} and hole_sig(items[0]) == hole_sig(items[1]):
            base = {kk: vv for kk, vv in items[0].items()
                    if kk not in {"scoring_type", "type", "points",
                                  "avg_gross_vs_par", "birdies_in_window", "disasters_in_window"}}
            metrics = {}
            for it in items:
                metrics[it["scoring_type"]] = {
                    "type": it.get("type"),
                    "points": it.get("points"),
                    "avg_gross_vs_par": it.get("avg_gross_vs_par"),
                    "birdies": it.get("birdies_in_window"),
                    "disasters": it.get("disasters_in_window"),
                }
            base["metrics"] = _drop_null_keys(metrics)
            merged.append(base)
        else:
            merged.extend(items)
    return merged

def compact_round_data_lossless(round_data: dict) -> dict:
    """Lossless compaction for prompt building."""
    rd = json.loads(json.dumps(round_data, default=str))  # deep copy
    if isinstance(rd.get("pattern_details"), list) and rd["pattern_details"]:
        rd["pattern_details"] = _merge_gross_net_windows(rd["pattern_details"])
    rd = _drop_null_keys(rd)
    return rd

# ========================
# Abbreviations (prompt-only)
# ========================

KEY_MAP_EVENTS = {
    "Pl":"pl","Player":"pl","Hole":"h","Event":"ev","Type":"ty","Impact":"imp","OneLiner":"ol",
    "Rank_Stableford_After":"rsa","Rank_Gross_After":"rga",
    "Rank_Stableford_Before":"rsb","Rank_Gross_Before":"rgb",
    "Gap_After":"gap","Gap_Before":"gb",
    "GrossVP":"gvp","NetVP":"nvp","Stableford":"stb","Par":"par","Sc":"sc"
}
KEY_MAP_HOLES = {"Hole":"h","Stableford":"stb","GrossVP":"gvp","NetVP":"nvp","Par":"par","Sc":"sc"}
KEY_MAP_METRICS = {"type":"t","points":"pts","avg_gross_vs_par":"agvp","birdies":"brd","disasters":"dst"}
KEY_MAP_MOMENTUM = {"Pl":"pl","Player":"pl","Span":"sp","Delta":"dl","Label":"lb"}
KEY_MAP_SUMMARY = {
    "Pl":"pl","Player":"pl","Course":"crs",
    "GrossVP":"gvp","NetVP":"nvp","Stableford":"stb",
    "Front9":"f9","Back9":"b9","Gap_After":"gap",
    "Round_Rank_Stableford":"rrs","Round_Rank_Gross":"rrg",
    "Rank_Stableford_After":"rsa","Rank_Gross_After":"rga"
}

def _rename_keys(obj, keymap):
    if isinstance(obj, dict):
        return { keymap.get(k, k): _rename_keys(v, keymap) for k, v in obj.items() }
    if isinstance(obj, list):
        return [ _rename_keys(x, keymap) for x in obj ]
    return obj

def abbreviate_for_prompt(rd: dict) -> tuple[dict, str]:
    """Return (rd_abbrev, legend_text)."""
    import copy
    rd2 = copy.deepcopy(rd)

    if isinstance(rd2.get("events"), list):
        rd2["events"] = [_rename_keys(e, KEY_MAP_EVENTS) for e in rd2["events"]]
    if isinstance(rd2.get("pattern_details"), list):
        for item in rd2["pattern_details"]:
            if isinstance(item.get("hole_scores"), list):
                item["hole_scores"] = [_rename_keys(h, KEY_MAP_HOLES) for h in item["hole_scores"]]
            if isinstance(item.get("metrics"), dict):
                for k in list(item["metrics"].keys()):
                    item["metrics"][k] = _rename_keys(item["metrics"][k], KEY_MAP_METRICS)
    if isinstance(rd2.get("momentum_patterns"), list):
        rd2["momentum_patterns"] = [_rename_keys(m, KEY_MAP_MOMENTUM) for m in rd2["momentum_patterns"]]
    if isinstance(rd2.get("summary"), list):
        rd2["summary"] = [_rename_keys(s, KEY_MAP_SUMMARY) for s in rd2["summary"]]

    pairs = {
        "pl=Player","h=Hole","gvp=Gross vs Par","nvp=Net vs Par","stb=Stableford","par=Par","sc=Score",
        "rsa=Rank Stableford After","rga=Rank Gross After","rsb=Rank Stableford Before","rgb=Rank Gross Before",
        "gap=Gap to leader","gb=Gap before","crs=Course","f9=Front 9","b9=Back 9",
        "rrs=Round Rank (Stableford)","rrg=Round Rank (Gross)","t=Type","pts=Points",
        "agvp=Avg Gross vs Par","brd=Birdies","dst=Disasters","sp=Span","dl=Delta","lb=Label",
        "ev=Event","ty=Type","imp=Impact","ol=One-liner"
    }
    legend_text = "Legend: " + ", ".join(sorted(pairs))
    return rd2, legend_text

# ========================
# Token bucket limiter + 429-safe wrapper
# ========================

class TokenMinuteLimiter:
    """
    Rolling 60s token limiter with simulation during DRY_RUN.
    Stores (timestamp, tokens) and plans waits so sum(tokens) <= budget within last 60s.
    """
    def __init__(self, budget_per_min: int, safety: float, dry_run: bool, debug: bool):
        self.budget = int(budget_per_min * safety)
        self.events = deque()  # (ts, tokens)
        self.dry_run = dry_run
        self.debug = debug

    def _now(self):
        return time.monotonic()

    def _prune(self, now=None):
        now = now or self._now()
        while self.events and now - self.events[0][0] > 60:
            self.events.popleft()

    def used_last_min(self):
        now = self._now()
        self._prune(now)
        return sum(t for _, t in self.events)

    def plan_wait(self, tokens: int) -> int:
        now = self._now()
        self._prune(now)
        used = self.used_last_min()
        if used + tokens <= self.budget:
            return 0
        # Find when enough oldest tokens age out
        temp = list(self.events)
        total = used
        wait = 0
        for ts, t in temp:
            total -= t
            expire_in = (ts + 60) - now
            if total + tokens <= self.budget:
                wait = max(0, math.ceil(expire_in))
                break
        else:
            wait = 60
        return wait

    def acquire(self, tokens: int, label: str = ""):
        """Plan wait; in DRY_RUN simulate consumption; in live, sleep then record."""
        wait = self.plan_wait(tokens)
        used = self.used_last_min()
        if self.debug:
            print(f"    · Rate-limit (rolling): used≈{used:,} tok / budget={self.budget:,}, next='{label}', est_input≈{tokens:,}, planned_sleep={wait}s")
        now = self._now()
        if self.dry_run:
            self.events.append((now, tokens))  # simulate consumption
        else:
            if wait > 0:
                time.sleep(wait)
            self.events.append((self._now(), tokens))

# Global limiter instance
TOKEN_LIMITER = TokenMinuteLimiter(RATE_BUDGET_INPUT_TOKENS_PER_MIN, RATE_SAFETY, DRY_RUN, DEBUG)

def safe_create_message(client, **kwargs):
    """
    Wrapper around client.messages.create with 429-aware backoff.
    - Honors Retry-After and/or tokens-reset headers if present.
    - Exponential backoff otherwise (cap 60s).
    """
    max_retries = 5
    backoff = 2.0
    attempt = 0
    while True:
        try:
            return client.messages.create(**kwargs)
        except anthropic.RateLimitError as e:
            attempt += 1
            if attempt > max_retries:
                raise
            resp = getattr(e, "response", None)
            headers = getattr(resp, "headers", {}) if resp is not None else {}
            retry_after = headers.get("retry-after")
            reset_secs = headers.get("anthropic-ratelimit-tokens-reset")
            sleep_for = None
            if retry_after:
                try:
                    sleep_for = float(retry_after)
                except Exception:
                    pass
            if sleep_for is None and reset_secs:
                try:
                    sleep_for = float(reset_secs)
                except Exception:
                    pass
            if sleep_for is None:
                sleep_for = backoff
                backoff = min(backoff * 2, 60.0)
            # Always print backoff errors (even if DEBUG=False) so you know what's happening
            print(f"    · 429 received. Backing off {sleep_for:.1f}s (attempt {attempt}/{max_retries}).")
            time.sleep(sleep_for)
        except anthropic.APIStatusError as e:
            attempt += 1
            if attempt > max_retries:
                raise
            print(f"    · Transient API error ({getattr(e, 'status_code', '?')}). Backoff {backoff:.1f}s (attempt {attempt}/{max_retries}).")
            time.sleep(backoff)
            backoff = min(backoff * 2, 60.0)

# ========================
# API key helper
# ========================

try:
    import streamlit as st
    def get_api_key():
        if hasattr(st, 'secrets') and 'ANTHROPIC_API_KEY' in st.secrets:
            return st.secrets['ANTHROPIC_API_KEY']
        return os.getenv('ANTHROPIC_API_KEY')
except ImportError:
    def get_api_key():
        return os.getenv('ANTHROPIC_API_KEY')

# ========================
# Main generation functions
# ========================

def generate_round_story(teg_num, round_num, round_data, previous_context):
    """
    Generate story notes for a single round using all 6 data types.
    """
    print(f"\n  Generating Round {round_num} story...")

    # LOSSLESS compact + abbreviate for the prompt (raw data untouched for inspection)
    rd_compact = compact_round_data_lossless(round_data)
    rd_abbrev, legend_text = abbreviate_for_prompt(rd_compact)

    # Minify JSON for prompt
    round_data_json = json.dumps(rd_abbrev, separators=(",", ":"), ensure_ascii=False, default=str)
    previous_context_json = (
        json.dumps(previous_context, separators=(",", ":"), ensure_ascii=False, default=str)
        if previous_context else "First round of the tournament"
    )

    # Build prompt
    prompt_body = ROUND_STORY_PROMPT.format(
        round_num=round_num,
        round_data=round_data_json,
        previous_context=previous_context_json
    )
    prompt = legend_text + "\n\n" + prompt_body

    # ---- Rolling-minute limiter (simulate in DRY_RUN, sleep when live) ----
    est_in_tokens = _est_tokens(prompt)
    TOKEN_LIMITER.acquire(est_in_tokens, label=f"R{round_num}")

    # Debug-only instrumentation
    dprint("    · Prompt section sizes:")
    dprint("      " + _blob_stats("round_data_json", round_data_json))
    dprint("      " + _blob_stats("previous_context_json", previous_context_json))
    dprint("      " + _blob_stats("FULL prompt", prompt))

    # Debug-only prompt dump & inspection bundle
    if DEBUG:
        debug_dir = "streamlit/commentary/debug_prompts"
        os.makedirs(debug_dir, exist_ok=True)
        with open(os.path.join(debug_dir, f"teg_{teg_num}_round_{round_num}_prompt.txt"), "w", encoding="utf-8") as fdbg:
            fdbg.write(prompt)
        write_round_inspection(teg_num, round_num, round_data, previous_context, prompt)

    # ---- DRY RUN gate FIRST (no API key required) ----
    if DRY_RUN:
        dprint("    ⚙️  DRY RUN: Skipping LLM call")
        dprint("    (Prompt built successfully, ready for submission if enabled.)")
        ending_context = get_round_ending_context(round_data)
        return "DRY_RUN_STORY", ending_context

    # ---- Real call only if not dry run ----
    api_key = get_api_key()
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY not found in Streamlit secrets or environment variables")
    client = anthropic.Anthropic(api_key=api_key)

    message = safe_create_message(
        client,
        model="claude-sonnet-4-5",
        max_tokens=4000,
        messages=[{"role": "user", "content": prompt}]
    )

    round_story = message.content[0].text
    ending_context = get_round_ending_context(round_data)
    print(f"    > Round {round_num} story complete ({len(round_story)} chars)")
    return round_story, ending_context

def generate_tournament_synthesis(round_stories, teg_num):
    """
    Generate tournament-level sections using all round stories.
    Respects DRY_RUN to avoid any paid API calls during diagnosis.
    """
    print(f"\n  Generating tournament synthesis...")

    tournament_summary = pd.read_parquet('data/commentary_tournament_summary.parquet')
    tournament_summary = tournament_summary[tournament_summary['TEGNum'] == teg_num]

    round_summaries_text = "\n\n".join([f"## Round {i+1}\n{story}" for i, story in enumerate(round_stories)])
    tournament_data_json = json.dumps(tournament_summary.to_dict('records'), indent=2, default=str)

    prompt = TOURNAMENT_SYNTHESIS_PROMPT.format(
        round_summaries=round_summaries_text,
        tournament_data=tournament_data_json,
        historical_context="[Historical context placeholder - will be enhanced in future version]"
    )

    if DEBUG:
        write_synthesis_inspection(teg_num, round_stories, prompt, tournament_summary)

    # Rolling-minute limiter for synthesis
    est_in_tokens = _est_tokens(prompt)
    TOKEN_LIMITER.acquire(est_in_tokens, label="SYN")

    # Debug-only instrumentation & prompt dump
    dprint("    · Synthesis prompt sizes:")
    dprint("      " + _blob_stats("round_summaries_text", round_summaries_text))
    dprint("      " + _blob_stats("tournament_data_json", tournament_data_json))
    dprint("      " + _blob_stats("FULL prompt", prompt))

    if DEBUG:
        debug_dir = "streamlit/commentary/debug_prompts"
        os.makedirs(debug_dir, exist_ok=True)
        with open(os.path.join(debug_dir, f"teg_{teg_num}_synthesis_prompt.txt"), "w", encoding="utf-8") as fdbg:
            fdbg.write(prompt)

    dprint(f"    DRY_RUN (synthesis) = {DRY_RUN}")
    if DRY_RUN:
        dprint("    ⚙️  DRY RUN: Skipping LLM call (synthesis)")
        return "DRY_RUN_SYNTHESIS"

    # Real call
    api_key = get_api_key()
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY not found in Streamlit secrets or environment variables")
    client = anthropic.Anthropic(api_key=api_key)

    message = safe_create_message(
        client,
        model="claude-sonnet-4-5",
        max_tokens=3000,
        messages=[{"role": "user", "content": prompt}]
    )
    synthesis = message.content[0].text
    print(f"    > Tournament synthesis complete ({len(synthesis)} chars)")
    return synthesis

# ========================
# File assembly
# ========================

def build_story_notes_file(teg_num, round_stories, synthesis):
    content = f"# TEG {teg_num} Story Notes\n\n"
    content += synthesis + "\n\n"
    for i, round_notes in enumerate(round_stories, 1):
        content += round_notes + "\n\n"
    return content

# ========================
# Pipelines
# ========================

def generate_complete_story_notes(teg_num):
    print(f"\n{'='*60}")
    print(f"GENERATING STORY NOTES FOR TEG {teg_num}")
    print(f"{'='*60}\n")

    print("LEVEL 1: Data Type Processing (6 passes)")
    print("-" * 60)
    all_data = process_all_data_types(teg_num)
    print("> All data types processed")

    print(f"\nLEVEL 2: Round Story Generation")
    print("-" * 60)
    num_rounds = get_teg_rounds(teg_num)
    print(f"Tournament has {num_rounds} rounds")

    round_stories = []
    previous_context = None

    for round_num in range(1, num_rounds + 1):
        round_data = load_round_data(teg_num, round_num, all_data)
        round_story, round_context = generate_round_story(
            teg_num, round_num, round_data, previous_context
        )
        round_stories.append(round_story)
        previous_context = round_context

    print(f"\n> All {num_rounds} round stories complete")

    print(f"\nLEVEL 2: Tournament Synthesis")
    print("-" * 60)
    synthesis = generate_tournament_synthesis(round_stories, teg_num)
    print("> Tournament synthesis complete")

    story_notes = build_story_notes_file(teg_num, round_stories, synthesis)

    output_path = f"streamlit/commentary/outputs/teg_{teg_num}_story_notes.md"
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(story_notes)

    print(f"\n{'='*60}")
    print(f"STORY NOTES COMPLETE")
    print(f"{'='*60}")
    print(f"\nSaved to: {output_path}")
    print(f"Total rounds: {num_rounds}")
    print(f"Total LLM calls: {num_rounds + 1} ({num_rounds} rounds + 1 synthesis)")
    print(f"Total characters: {len(story_notes):,}")
    print(f"\n{'='*60}\n")
    return story_notes

def generate_story_notes_up_to_round(teg_num, completed_rounds):
    print(f"\n{'='*60}")
    print(f"GENERATING STORY NOTES FOR TEG {teg_num}")
    print(f"(IN PROGRESS - {completed_rounds} rounds completed)")
    print(f"{'='*60}\n")

    print("LEVEL 1: Data Type Processing (6 passes)")
    print("-" * 60)
    all_data = process_all_data_types(teg_num)
    print("> All data types processed")

    print(f"\nLEVEL 2: Round Story Generation ({completed_rounds} rounds)")
    print("-" * 60)
    round_stories = []
    previous_context = None

    for round_num in range(1, completed_rounds + 1):
        round_data = load_round_data(teg_num, round_num, all_data)
        round_story, round_context = generate_round_story(
            teg_num, round_num, round_data, previous_context
        )
        round_stories.append(round_story)
        previous_context = round_context

    print(f"\n> All {completed_rounds} round stories complete")

    content = f"# TEG {teg_num} Story Notes (In Progress - {completed_rounds} rounds)\n\n"
    content += "**Note:** Tournament synthesis will be added when all rounds are complete.\n\n"
    for i, round_notes in enumerate(round_stories, 1):
        content += round_notes + "\n\n"

    output_path = f"streamlit/commentary/outputs/teg_{teg_num}_story_notes_partial.md"
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"\n{'='*60}")
    print(f"PARTIAL STORY NOTES COMPLETE")
    print(f"{'='*60}")
    print(f"\nSaved to: {output_path}")
    print(f"Completed rounds: {completed_rounds}")
    print(f"Total LLM calls: {completed_rounds}")
    print(f"Total characters: {len(content):,}")
    print(f"\n{'='*60}\n")
    return content

# ========================
# Batch helper (range of TEGs)
# ========================

def _output_path_for(teg_num: int, partial: Optional[int]) -> str:
    """Compute the markdown output path used by the generators."""
    base = "streamlit/commentary/outputs"
    return f"{base}/teg_{teg_num}_story_notes_partial.md" if partial else f"{base}/teg_{teg_num}_story_notes.md"

def generate_story_notes_for_teg_range(
    teg_start: int,
    teg_end: int,
    partial: Optional[int] = None,
    stop_on_error: bool = False,
    pause_between: float = 0.0,
) -> List[Dict]:
    """
    Run the story-notes pipeline for every TEG in [teg_start, teg_end], inclusive.

    Args:
        teg_start: First TEG number.
        teg_end: Last TEG number (inclusive).
        partial: If provided, run 'in-progress' pipeline up to this round count.
        stop_on_error: If True, abort on first error; else continue and record failures.
        pause_between: Seconds to sleep between tournaments (0.0 for none).

    Returns:
        A list of dicts:
        [{"teg": 17, "status": "ok", "output_path": "...", "error": None}, ...]
    """
    if teg_end < teg_start:
        teg_start, teg_end = teg_end, teg_start  # normalize

    results: List[Dict] = []
    print(f"\n=== Batch run for TEGs {teg_start} → {teg_end} (partial={'up to ' + str(partial) if partial else 'full'}) ===")

    for teg in range(teg_start, teg_end + 1):
        print(f"\n--- TEG {teg} --------------------------------------------------")
        try:
            if partial:
                _ = generate_story_notes_up_to_round(teg, partial)
            else:
                _ = generate_complete_story_notes(teg)

            out_path = _output_path_for(teg, partial)
            results.append({"teg": teg, "status": "ok", "output_path": out_path, "error": None})
            print(f"> Done TEG {teg}  → {out_path}")

        except Exception as e:
            err_msg = f"{type(e).__name__}: {e}"
            results.append({"teg": teg, "status": "error", "output_path": None, "error": err_msg})
            print(f"! Failed TEG {teg}: {err_msg}")
            if stop_on_error:
                print("Stopping due to stop_on_error=True.")
                break

        # Optional pause between tournaments (useful when DRY_RUN=False)
        if pause_between and teg < teg_end:
            try:
                import time
                dprint(f"(pausing {pause_between}s before next TEG…)")
                time.sleep(pause_between)
            except Exception:
                pass

    ok = sum(1 for r in results if r["status"] == "ok")
    fail = len(results) - ok
    print(f"\n=== Batch complete: {ok} ok, {fail} failed ===")
    return results

# ========================
# CLI
# ========================

if __name__ == "__main__":
    import argparse

    print(f"DRY_RUN mode is {'ON' if DRY_RUN else 'OFF'} • DEBUG is {'ON' if DEBUG else 'OFF'}")

    parser = argparse.ArgumentParser(description='Generate tournament story notes')
    # Either provide a single TEG number (positional) OR use --range START END
    parser.add_argument('teg_num', type=int, nargs='?', help='Single tournament number (omit if using --range)')
    parser.add_argument('--partial', type=int, help='Number of completed rounds (for in-progress tournaments)')
    parser.add_argument('--range', type=int, nargs=2, metavar=('START','END'),
                        help='Run a range of TEGs inclusive, e.g. --range 10 12')
    parser.add_argument('--stop-on-error', action='store_true', help='Abort batch on first error')
    parser.add_argument('--pause-between', type=float, default=0.0, help='Seconds to pause between tournaments')
    args = parser.parse_args()

    if args.range:
        start, end = args.range
        generate_story_notes_for_teg_range(
            start, end,
            partial=args.partial,
            stop_on_error=args.stop_on_error,
            pause_between=args.pause_between,
        )
    else:
        if args.teg_num is None:
            parser.error("Provide a single TEG number or --range START END")
        if args.partial:
            generate_story_notes_up_to_round(args.teg_num, args.partial)
        else:
            generate_complete_story_notes(args.teg_num)
