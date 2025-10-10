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

DRY_RUN = False   # set to False when you're ready to actually call the LLM
DEBUG   = True   # master switch for all debug prints & debug file saves
DEBUG_WRITE = False # write debug files

# Feature toggles
INCLUDE_STREAKS = True  # Include streak data (Birdies, Eagles, +2s or Worse) in round story generation
                        # Set to False to exclude streak data if it doesn't add value

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
from prompts import ROUND_STORY_PROMPT, TOURNAMENT_SYNTHESIS_PROMPT, MAIN_REPORT_PROMPT, BRIEF_SUMMARY_PROMPT, SATIRICAL_REPORT_PROMPT
from utils import get_teg_rounds, write_text_file, read_file, read_text_file
import anthropic
from batch_api import (
    create_batch_request, save_batch_requests, submit_batch,
    poll_until_complete, get_batch_results, save_batch_info,
    find_batch_info_file, load_batch_info, check_batch_status, list_recent_batches
)

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
    Writes an inspection bundle for this round (only when DEBUG_WRITE=True).
    """
    if not DEBUG_WRITE:
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
                                  "avg_gross_vs_par", "birdies_in_window", "blow_ups_in_window"}}
            metrics = {}
            for it in items:
                metrics[it["scoring_type"]] = {
                    "type": it.get("type"),
                    "points": it.get("points"),
                    "avg_gross_vs_par": it.get("avg_gross_vs_par"),
                    "birdies": it.get("birdies_in_window"),
                    "blow_ups": it.get("blow_ups_in_window"),
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
KEY_MAP_METRICS = {"type":"t","points":"pts","avg_gross_vs_par":"agvp","birdies":"brd","blow_ups":"dst"}
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
        "agvp=Avg Gross vs Par","brd=Birdies","dst=Blow Ups","sp=Span","dl=Delta","lb=Label",
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
            print(f"    - Rate-limit (rolling): used~{used:,} tok / budget={self.budget:,}, next='{label}', est_input~{tokens:,}, planned_sleep={wait}s")
        now = self._now()
        if self.dry_run:
            self.events.append((now, tokens))  # simulate consumption
        else:
            if wait > 0:
                time.sleep(wait)
            self.events.append((self._now(), tokens))

# Global limiter instance
TOKEN_LIMITER = TokenMinuteLimiter(RATE_BUDGET_INPUT_TOKENS_PER_MIN, RATE_SAFETY, DRY_RUN, DEBUG)

def safe_create_message(client, max_retries=12, **kwargs):
    """
    Wrapper around client.messages.create with retry logic for rate limits and overload errors.
    - Handles 429 (rate limit) with Retry-After headers
    - Handles 500 (internal server error) with exponential backoff
    - Handles 529 (overloaded) with exponential backoff
    - Handles connection errors (IncompleteRead, Connection, Timeout) with exponential backoff
    - Exponential backoff otherwise (cap 120s)

    Args:
        client: Anthropic client instance
        max_retries: Maximum number of retry attempts (default 12, increased from 5)
        **kwargs: Arguments to pass to client.messages.create()
    """
    backoff = 3.0  # Start with 3s instead of 2s
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
                backoff = min(backoff * 2, 120.0)  # Increased cap to 120s
            print(f"    · Rate limit (429). Backing off {sleep_for:.1f}s (attempt {attempt}/{max_retries})")
            time.sleep(sleep_for)
        except anthropic.APIStatusError as e:
            # Handle 500, 529, and other transient errors
            attempt += 1
            if attempt > max_retries:
                raise
            status_code = getattr(e, 'status_code', None)
            if status_code == 500:
                print(f"    · Internal server error (500). Backing off {backoff:.1f}s (attempt {attempt}/{max_retries})")
            elif status_code == 529:
                print(f"    · Server overloaded (529). Backing off {backoff:.1f}s (attempt {attempt}/{max_retries})")
            else:
                print(f"    · Transient API error ({status_code}). Backing off {backoff:.1f}s (attempt {attempt}/{max_retries})")
            time.sleep(backoff)
            backoff = min(backoff * 2, 120.0)  # Increased cap to 120s
        except Exception as e:
            # Handle connection errors (IncompleteRead, Connection, Timeout, ChunkedEncodingError)
            attempt += 1
            if attempt > max_retries:
                raise

            error_str = str(e)
            error_type = type(e).__name__

            # Check if this is a known transient connection error
            is_connection_error = any(x in error_str for x in [
                'IncompleteRead', 'Connection', 'Timeout', 'ChunkedEncodingError',
                'ConnectionError', 'ConnectionResetError', 'BrokenPipeError'
            ]) or any(x in error_type for x in [
                'IncompleteRead', 'Connection', 'Timeout', 'ChunkedEncoding'
            ])

            if is_connection_error:
                sleep_for = backoff
                print(f"    · Connection error: {error_type}: {error_str[:100]}")
                print(f"    · Backing off {sleep_for:.1f}s (attempt {attempt}/{max_retries})")
                time.sleep(sleep_for)
                backoff = min(backoff * 2, 120.0)  # Increased cap to 120s
            else:
                # Not a known transient error - re-raise immediately
                raise

# ========================
# API key helper
# ========================

try:
    import streamlit as st
    def get_api_key():
        """Get Anthropic API key from Streamlit secrets or environment variables."""
        try:#
            if hasattr(st, 'secrets') and 'ANTHROPIC_API_KEY' in st.secrets:
                return st.secrets['ANTHROPIC_API_KEY']
        except Exception:
            # If secrets.toml doesn't exist or can't be read, fall through to env var
            pass
        return os.getenv('ANTHROPIC_API_KEY')
except ImportError:
    def get_api_key():
        """Get Anthropic API key from environment variables."""
        return os.getenv('ANTHROPIC_API_KEY')

# ========================
# Main generation functions
# ========================

def generate_round_story(teg_num, round_num, round_data, previous_context):
    """
    Generate story notes for a single round.
    Note: Records/PBs/course records are added directly after LLM generation (not in prompt).
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

# Build prompt (NO records/PBs/course records - those are added directly)
    # Don't format the prompt - keep it static for caching
    system_prompt = legend_text + "\n\n" + ROUND_STORY_PROMPT

    # Pass the variable data in the user message instead
    user_message = f"""**Round Number:** {round_num}

    **Round Data:**
    {round_data_json}

    **Previous Context:**
    {previous_context_json}"""

    # Combine for debugging and token estimation
    full_prompt_for_debug = system_prompt + "\n\n" + user_message

    # ---- Rolling-minute limiter (simulate in DRY_RUN, sleep when live) ----
    est_in_tokens = _est_tokens(full_prompt_for_debug)
    TOKEN_LIMITER.acquire(est_in_tokens, label=f"R{round_num}")

    # Debug-only instrumentation
    dprint("    · Prompt section sizes:")
    dprint("      " + _blob_stats("round_data_json", round_data_json))
    dprint("      " + _blob_stats("previous_context_json", previous_context_json))
    dprint("      " + _blob_stats("FULL prompt", full_prompt_for_debug))

    # Debug-only prompt dump & inspection bundle
    if DEBUG_WRITE:
        debug_dir = "streamlit/commentary/debug_prompts"
        os.makedirs(debug_dir, exist_ok=True)
        with open(os.path.join(debug_dir, f"teg_{teg_num}_round_{round_num}_prompt.txt"), "w", encoding="utf-8") as fdbg:
            fdbg.write(full_prompt_for_debug)
        write_round_inspection(teg_num, round_num, round_data, previous_context, full_prompt_for_debug)

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
        system=[
            {
                "type": "text",
                "text": system_prompt,
                "cache_control": {"type": "ephemeral"}
            }
        ],
        messages=[
            {
                "role": "user",
                "content": user_message
            }
        ]
    )

    round_story = message.content[0].text
    ending_context = get_round_ending_context(round_data)
    print(f"    > Round {round_num} story complete ({len(round_story)} chars)")
    return round_story, ending_context

def build_venue_context(teg_num):
    """
    Build venue and course context for tournament synthesis.
    Returns formatted string with area, course history, and return context.
    """
    # Load course/area data
    rounds_df = pd.read_csv('data/round_info.csv')

    # Get this TEG's information
    current_teg = rounds_df[rounds_df['TEGNum'] == teg_num]
    if len(current_teg) == 0:
        return "Venue information not available."

    area = current_teg['Area'].iloc[0]
    year = current_teg['Year'].iloc[0]
    courses = current_teg[['Round', 'Course']].values.tolist()

    # Build context string
    context_lines = []
    context_lines.append(f"Tournament Area: {area} ({year})")
    context_lines.append("")

    # Check for area returns
    all_teg_areas = rounds_df[['TEGNum', 'Area']].drop_duplicates().sort_values('TEGNum')
    same_area_tegs = all_teg_areas[all_teg_areas['Area'] == area]
    previous_in_area = same_area_tegs[same_area_tegs['TEGNum'] < teg_num]

    if len(previous_in_area) > 0:
        last_teg_in_area = previous_in_area.iloc[-1]['TEGNum']
        gap = teg_num - last_teg_in_area
        if gap > 1:
            context_lines.append(f"Area Return: {gap}-TEG gap since TEG {int(last_teg_in_area)}")
        else:
            context_lines.append(f"Area Return: Consecutive TEG (following TEG {int(last_teg_in_area)})")
    else:
        # Check for broader geographic returns (e.g., different England areas)
        area_country = area.split(',')[-1].strip() if ',' in area else area
        country_tegs = all_teg_areas[all_teg_areas['Area'].str.contains(area_country, na=False, regex=False)]
        previous_in_country = country_tegs[country_tegs['TEGNum'] < teg_num]

        if len(previous_in_country) > 0:
            last_teg_in_country = previous_in_country.iloc[-1]['TEGNum']
            last_area = previous_in_country.iloc[-1]['Area']
            gap = teg_num - last_teg_in_country
            context_lines.append(f"First time in {area}")
            if gap > 1:
                context_lines.append(f"Return to {area_country} after {gap}-TEG gap (last: TEG {int(last_teg_in_country)} in {last_area})")
        else:
            context_lines.append(f"NEW DESTINATION: First TEG in {area}")

    context_lines.append("")
    context_lines.append("Courses:")

    # Course information with history
    all_courses = rounds_df[['TEGNum', 'Course']].drop_duplicates()
    previous_all_tegs = all_courses[all_courses['TEGNum'] < teg_num]

    for round_num, course in courses:
        course_history = previous_all_tegs[previous_all_tegs['Course'] == course]
        if len(course_history) > 0:
            prev_tegs = sorted(course_history['TEGNum'].unique())
            prev_teg_str = ', '.join([f"TEG {int(t)}" for t in prev_tegs])
            context_lines.append(f"- Round {round_num}: {course} (previously: {prev_teg_str})")
        else:
            context_lines.append(f"- Round {round_num}: {course} (NEW COURSE)")

    return "\n".join(context_lines)

def build_career_context(teg_num, players_in_teg):
    """
    Build career context for players BEFORE this tournament.

    IMPORTANT: Only includes data from TEGs BEFORE this one (TEGNum < teg_num).
    This ensures no "future" information is leaked from the perspective of this tournament.

    Args:
        teg_num: Current tournament number
        players_in_teg: List of player names in this tournament

    Returns:
        Formatted string with career context for each player
    """
    all_tournament_data = read_file('data/commentary_tournament_summary.parquet')

    # CRITICAL: Only use data BEFORE this TEG
    pre_tournament_data = all_tournament_data[all_tournament_data['TEGNum'] < teg_num].copy()

    career_context = "**PRE-TOURNAMENT Career Context (all data BEFORE this TEG):**\n\n"

    for player in sorted(players_in_teg):
        player_history = pre_tournament_data[pre_tournament_data['Player'] == player].copy()

        if len(player_history) == 0:
            # Debut player
            career_context += f"**{player}**: DEBUT (first TEG)\n\n"
            continue

        # Sort by TEGNum to get chronological order
        player_history = player_history.sort_values('TEGNum')

        # Recent finishes (last 3-5 TEGs they played, in reverse chronological order)
        recent_tegs = player_history.tail(5).sort_values('TEGNum', ascending=False)
        recent_finishes = []
        for _, row in recent_tegs.iterrows():
            teg_label = f"TEG {int(row['TEGNum'])}"
            position = f"{int(row['Final_Rank_Stableford'])}"
            recent_finishes.append(f"{teg_label}: {position}")

        # Position counts (Stableford/Trophy competition)
        position_counts = {}
        for _, row in player_history.iterrows():
            pos = int(row['Final_Rank_Stableford'])
            position_counts[pos] = position_counts.get(pos, 0) + 1

        # Format position counts (1st, 2nd, 3rd, etc.)
        pos_count_str = ", ".join([f"{pos}: {count}" for pos, count in sorted(position_counts.items())])

        # Build player summary
        career_context += f"**{player}**:\n"
        career_context += f"- Recent: {', '.join(recent_finishes)}\n"
        career_context += f"- Career positions: {pos_count_str}\n\n"

    return career_context

def generate_tournament_synthesis(round_stories, teg_num, all_processed_data=None):
    """
    Generate tournament-level sections using all round stories.
    Note: Venue context is added directly after LLM generation (not in prompt).

    Args:
        round_stories: List of round story notes
        teg_num: Tournament number
        all_processed_data: Dict with all processed data including victory_context
    """
    print(f"\n  Generating tournament synthesis...")

    # Load tournament summary
    all_tournament_data = read_file('data/commentary_tournament_summary.parquet')
    tournament_summary = all_tournament_data[all_tournament_data['TEGNum'] == teg_num].copy()

    # Add historical context: count wins BEFORE this TEG for each player
    # IMPORTANT: Use TEG_winners.csv (source of truth) instead of calculated wins
    # because some tournaments used different scoring systems (e.g. TEG 5)
    winners_df = read_file('data/TEG_winners.csv')
    winners_df['TEGNum'] = winners_df['TEG'].str.extract(r'(\d+)').astype(int)
    historical_winners = winners_df[winners_df['TEGNum'] < teg_num]

    def calc_wins_before(row):
        player = row['Player']
        return pd.Series({
            'teg_trophy_wins_before': int((historical_winners['TEG Trophy'] == player).sum()),
            'green_jacket_wins_before': int((historical_winners['Green Jacket'] == player).sum()),
            'wooden_spoons_before': int((historical_winners['HMM Wooden Spoon'] == player).sum())
        })

    historical_counts = tournament_summary.apply(calc_wins_before, axis=1)
    tournament_summary = pd.concat([tournament_summary, historical_counts], axis=1)

    round_summaries_text = "\n\n".join([f"## Round {i+1}\n{story}" for i, story in enumerate(round_stories)])
    tournament_data_json = json.dumps(tournament_summary.to_dict('records'), indent=2, default=str)

    # Build historical context summary (win counts)
    historical_context = "**Historical wins BEFORE this tournament (for context on '1st', '2nd', etc.):**\n"
    for _, row in tournament_summary.iterrows():
        player = row['Player']
        trophies = row['teg_trophy_wins_before']
        jackets = row['green_jacket_wins_before']
        spoons = row['wooden_spoons_before']
        historical_context += f"- {player}: {trophies} Trophy wins (Stableford), {jackets} Green Jacket wins (Gross), {spoons} Wooden Spoons\n"

    # Build career context (recent finishes + position counts)
    players_in_teg = tournament_summary['Player'].tolist()
    career_context = build_career_context(teg_num, players_in_teg)

    # Get victory context if available
    victory_context = None
    if all_processed_data and 'victory_context' in all_processed_data:
        victory_context = all_processed_data['victory_context']
        victory_context_json = json.dumps(victory_context, indent=2, default=str)
    else:
        victory_context_json = "Not available"

# Build prompt (NO venue context - that's added directly)
    # Don't format - keep static for caching
    system_prompt = TOURNAMENT_SYNTHESIS_PROMPT

    # Pass variable data in user message
    user_message = f"""Round Summaries:
    {round_summaries_text}

    Tournament Data:
    {tournament_data_json}

    Victory Context (use this to craft varied victory descriptions per Victory Classification Framework):
    {victory_context_json}

    Historical Context:
    {historical_context}

    Career Context:
    {career_context}"""

    # Combine for debugging and token estimation
    full_prompt_for_debug = system_prompt + "\n\n" + user_message

    if DEBUG:
        write_synthesis_inspection(teg_num, round_stories, full_prompt_for_debug, tournament_summary)

    # Rolling-minute limiter for synthesis
    est_in_tokens = _est_tokens(full_prompt_for_debug)
    TOKEN_LIMITER.acquire(est_in_tokens, label="SYN")

    # Debug-only instrumentation & prompt dump
    dprint("    · Synthesis prompt sizes:")
    dprint("      " + _blob_stats("round_summaries_text", round_summaries_text))
    dprint("      " + _blob_stats("tournament_data_json", tournament_data_json))
    dprint("      " + _blob_stats("FULL prompt", full_prompt_for_debug))

    if DEBUG_WRITE:
        debug_dir = "streamlit/commentary/debug_prompts"
        os.makedirs(debug_dir, exist_ok=True)
        with open(os.path.join(debug_dir, f"teg_{teg_num}_synthesis_prompt.txt"), "w", encoding="utf-8") as fdbg:
            fdbg.write(full_prompt_for_debug)

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
        max_tokens=4000,
        system=[
            {
                "type": "text",
                "text": system_prompt,
                "cache_control": {"type": "ephemeral"}
            }
        ],
        messages=[
            {
                "role": "user",
                "content": user_message
            }
        ]
    )

    synthesis = message.content[0].text
    print(f"    > Tournament synthesis complete ({len(synthesis)} chars)")
    return synthesis

# ========================
# LEVEL 3: Report Generation (from story notes)
# ========================

def generate_main_report(teg_num, use_batch_api=False):
    """
    Generate full narrative tournament report from existing story notes.
    Reads story notes file and transforms structured bullets into prose.

    Args:
        teg_num: Tournament number
        use_batch_api: If True, prepare for batch API instead of immediate generation
    """
    if use_batch_api:
        # Batch API mode handled separately - this shouldn't be called
        raise ValueError("Batch API mode should use generate_reports_via_batch_api()")

    print(f"\n{'='*60}")
    print(f"GENERATING MAIN REPORT FOR TEG {teg_num}")
    print(f"{'='*60}\n")

    # Read story notes file using Railway-aware helper
    story_notes_path = f"data/commentary/teg_{teg_num}_story_notes.md"
    try:
        story_notes = read_text_file(story_notes_path)
    except Exception as e:
        raise FileNotFoundError(
            f"Story notes not found: {story_notes_path}\n"
            f"Generate story notes first using: python generate_tournament_commentary_v2.py {teg_num}"
        ) from e

    print(f"Read story notes from: {story_notes_path}")
    print(f"Story notes length: {len(story_notes):,} characters")

    # Build prompt - don't format, keep static for caching
    system_prompt = MAIN_REPORT_PROMPT
    user_message = f"Story Notes:\n\n{story_notes}"
    full_prompt_for_debug = system_prompt + "\n\n" + user_message

    # Rate limiting
    est_in_tokens = _est_tokens(full_prompt_for_debug)
    TOKEN_LIMITER.acquire(est_in_tokens, label=f"MainReport-TEG{teg_num}")

    dprint("    · Main Report prompt stats:")
    dprint("      " + _blob_stats("story_notes", story_notes))
    dprint("      " + _blob_stats("FULL prompt", full_prompt_for_debug))

    # DRY RUN gate
    if DRY_RUN:
        dprint("    ⚙️  DRY RUN: Skipping LLM call")
        return "DRY_RUN_MAIN_REPORT"

    # Real call
    api_key = get_api_key()
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY not found in Streamlit secrets or environment variables")
    client = anthropic.Anthropic(api_key=api_key)

    message = safe_create_message(
        client,
        model="claude-sonnet-4-5",
        max_tokens=8000,
        system=[
            {
                "type": "text",
                "text": system_prompt,
                "cache_control": {"type": "ephemeral"}
            }
        ],
        messages=[
            {
                "role": "user",
                "content": user_message
            }
        ]
    )

    main_report = message.content[0].text

    # Save output using Railway-aware function
    output_path = f"data/commentary/drafts/teg_{teg_num}_main_report.md"
    write_text_file(
        output_path,
        main_report,
        commit_message=f"Generate main report for TEG {teg_num}"
    )

    print(f"\n{'='*60}")
    print(f"MAIN REPORT COMPLETE")
    print(f"{'='*60}")
    print(f"Saved to: {output_path}")
    print(f"Report length: {len(main_report):,} characters")
    print(f"{'='*60}\n")

    return main_report

def generate_brief_summary(teg_num, use_batch_api=False):
    """
    Generate concise 2-3 paragraph summary from existing story notes.

    Args:
        teg_num: Tournament number
        use_batch_api: If True, prepare for batch API instead of immediate generation
    """
    if use_batch_api:
        # Batch API mode handled separately - this shouldn't be called
        raise ValueError("Batch API mode should use generate_reports_via_batch_api()")

    print(f"\n{'='*60}")
    print(f"GENERATING BRIEF SUMMARY FOR TEG {teg_num}")
    print(f"{'='*60}\n")

    # Read story notes file using Railway-aware helper
    story_notes_path = f"data/commentary/teg_{teg_num}_story_notes.md"
    try:
        story_notes = read_text_file(story_notes_path)
    except Exception as e:
        raise FileNotFoundError(
            f"Story notes not found: {story_notes_path}\n"
            f"Generate story notes first using: python generate_tournament_commentary_v2.py {teg_num}"
        ) from e

    print(f"Read story notes from: {story_notes_path}")
    print(f"Story notes length: {len(story_notes):,} characters")

    # Build prompt - don't format, keep static for caching
    system_prompt = BRIEF_SUMMARY_PROMPT
    user_message = f"Story Notes:\n\n{story_notes}"
    full_prompt_for_debug = system_prompt + "\n\n" + user_message

    # Rate limiting
    est_in_tokens = _est_tokens(full_prompt_for_debug)
    TOKEN_LIMITER.acquire(est_in_tokens, label=f"BriefSummary-TEG{teg_num}")

    dprint("    · Brief Summary prompt stats:")
    dprint("      " + _blob_stats("story_notes", story_notes))
    dprint("      " + _blob_stats("FULL prompt", full_prompt_for_debug))

    # DRY RUN gate
    if DRY_RUN:
        dprint("    ⚙️  DRY RUN: Skipping LLM call")
        return "DRY_RUN_BRIEF_SUMMARY"

    # Real call
    api_key = get_api_key()
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY not found in Streamlit secrets or environment variables")
    client = anthropic.Anthropic(api_key=api_key)

    message = safe_create_message(
        client,
        model="claude-sonnet-4-5",
        max_tokens=2000,
        system=[
            {
                "type": "text",
                "text": system_prompt,
                "cache_control": {"type": "ephemeral"}
            }
        ],
        messages=[
            {
                "role": "user",
                "content": user_message
            }
        ]
    )

    brief_summary = message.content[0].text

    # Save output using Railway-aware function
    output_path = f"data/commentary/drafts/teg_{teg_num}_brief_summary.md"
    write_text_file(
        output_path,
        brief_summary,
        commit_message=f"Generate brief summary for TEG {teg_num}"
    )

    print(f"\n{'='*60}")
    print(f"BRIEF SUMMARY COMPLETE")
    print(f"{'='*60}")
    print(f"Saved to: {output_path}")
    print(f"Summary length: {len(brief_summary):,} characters")
    print(f"{'='*60}\n")

    return brief_summary

def generate_satirical_report(teg_num, use_batch_api=False):
    """
    Generate satirical tournament report from existing story notes.
    Written in the style of Armando Iannucci, Charlie Brooker, Jesse Armstrong, Sam Bain, and Martin Amis.

    Args:
        teg_num: Tournament number
        use_batch_api: If True, prepare for batch API instead of immediate generation
    """
    if use_batch_api:
        # Batch API mode handled separately - this shouldn't be called
        raise ValueError("Batch API mode should use generate_reports_via_batch_api()")

    print(f"\n{'='*60}")
    print(f"GENERATING SATIRICAL REPORT FOR TEG {teg_num}")
    print(f"{'='*60}\n")

    # Read story notes file using Railway-aware helper
    story_notes_path = f"data/commentary/teg_{teg_num}_story_notes.md"
    try:
        story_notes = read_text_file(story_notes_path)
    except Exception as e:
        raise FileNotFoundError(
            f"Story notes not found: {story_notes_path}\n"
            f"Generate story notes first using: python generate_tournament_commentary_v2.py {teg_num}"
        ) from e

    print(f"Read story notes from: {story_notes_path}")
    print(f"Story notes length: {len(story_notes):,} characters")

    # Build prompt - don't format, keep static for caching
    system_prompt = SATIRICAL_REPORT_PROMPT
    user_message = f"Story Notes:\n\n{story_notes}"
    full_prompt_for_debug = system_prompt + "\n\n" + user_message

    # Rate limiting
    est_in_tokens = _est_tokens(full_prompt_for_debug)
    TOKEN_LIMITER.acquire(est_in_tokens, label=f"SatiricalReport-TEG{teg_num}")

    dprint("    · Satirical Report prompt stats:")
    dprint("      " + _blob_stats("story_notes", story_notes))
    dprint("      " + _blob_stats("FULL prompt", full_prompt_for_debug))

    # DRY RUN gate
    if DRY_RUN:
        dprint("    ⚙️  DRY RUN: Skipping LLM call")
        return "DRY_RUN_SATIRICAL_REPORT"

    # Real call
    api_key = get_api_key()
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY not found in Streamlit secrets or environment variables")
    client = anthropic.Anthropic(api_key=api_key)

    message = safe_create_message(
        client,
        model="claude-sonnet-4-5",
        max_tokens=8000,
        system=[
            {
                "type": "text",
                "text": system_prompt,
                "cache_control": {"type": "ephemeral"}
            }
        ],
        messages=[
            {
                "role": "user",
                "content": user_message
            }
        ]
    )

    satirical_report = message.content[0].text

    # Save output using Railway-aware function
    output_path = f"data/commentary/drafts/teg_{teg_num}_satire.md"
    write_text_file(
        output_path,
        satirical_report,
        commit_message=f"Generate satirical report for TEG {teg_num}"
    )

    print(f"\n{'='*60}")
    print(f"SATIRICAL REPORT COMPLETE")
    print(f"{'='*60}")
    print(f"Saved to: {output_path}")
    print(f"Report length: {len(satirical_report):,} characters")
    print(f"{'='*60}\n")

    return satirical_report

def generate_reports_from_story_notes(teg_num, main_report=True, brief_summary=True, satirical=False):
    """
    Generate reports from existing story notes.

    Args:
        teg_num: Tournament number
        main_report: Generate full narrative report (default True)
        brief_summary: Generate concise summary (default True)
        satirical: Generate satirical report (default False)

    Returns:
        Dict with generated reports
    """
    results = {}

    if main_report:
        results['main_report'] = generate_main_report(teg_num)

    if brief_summary:
        results['brief_summary'] = generate_brief_summary(teg_num)

    if satirical:
        results['satirical'] = generate_satirical_report(teg_num)

    return results


def generate_reports_via_batch_api(teg_nums, main_report=True, brief_summary=True, satirical=False, submit_only=False):
    """
    Generate tournament reports using Anthropic Batch API (50% cost reduction).

    Args:
        teg_nums: List of TEG numbers to process
        main_report: Generate full narrative reports (default True)
        brief_summary: Generate brief summaries (default True)
        satirical: Generate satirical reports (default False)
        submit_only: If True, submit batch and exit (don't wait for results)

    Returns:
        Dict with generated reports, or list of batch_ids if submit_only=True
    """
    print("\n" + "="*60)
    print("BATCH API MODE FOR TOURNAMENT REPORTS (50% cost reduction)")
    if submit_only:
        print("SUBMIT ONLY - Will exit after submission")
    print("="*60)

    api_key = get_api_key()
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY not found in environment variables or Streamlit secrets")

    timestamp = time.strftime("%Y%m%d_%H%M%S")
    batch_dir = "streamlit/commentary/batch_requests"
    results_dir = "streamlit/commentary/batch_results"
    os.makedirs(batch_dir, exist_ok=True)
    os.makedirs(results_dir, exist_ok=True)

    results = {}
    batch_ids = []

    # Phase 1: Main Reports (batched for prompt caching)
    main_reports_batch_id = None
    if main_report:
        print("\nPHASE 1: Building main report batch requests...")
        main_report_requests = []

        for teg_num in teg_nums:
            # Read story notes file using Railway-aware helper
            story_notes_path = f"data/commentary/teg_{teg_num}_story_notes.md"
            try:
                story_notes = read_text_file(story_notes_path)
            except Exception:
                print(f"  ✗ Story notes not found for TEG {teg_num}")
                continue

            print(f"  Preparing TEG {teg_num}...")

            user_message = f"Story Notes:\n\n{story_notes}"

            request = create_batch_request(
                custom_id=f"TEG{teg_num}_main_report",
                model="claude-sonnet-4-5",
                max_tokens=8000,
                system_prompt=MAIN_REPORT_PROMPT,
                user_message=user_message,
                use_cache=True
            )
            main_report_requests.append(request)

        if main_report_requests:
            # Save and submit main reports batch
            batch_file = f"{batch_dir}/main_reports_{timestamp}.jsonl"
            save_batch_requests(main_report_requests, batch_file)

            print("\nSubmitting main reports batch to Anthropic...")
            batch_info = submit_batch(batch_file, api_key)
            main_reports_batch_id = batch_info['batch_id']
            save_batch_info(batch_info, results_dir, batch_type="main_reports")
            batch_ids.append(('main_reports', main_reports_batch_id))
            print(f"  ✓ Batch ID: {main_reports_batch_id}")

    # Phase 2: Brief Summaries (batched for prompt caching)
    brief_summaries_batch_id = None
    if brief_summary:
        print("\nPHASE 2: Building brief summary batch requests...")
        brief_summary_requests = []

        for teg_num in teg_nums:
            # Read story notes file using Railway-aware helper
            story_notes_path = f"data/commentary/teg_{teg_num}_story_notes.md"
            try:
                story_notes = read_text_file(story_notes_path)
            except Exception:
                print(f"  ✗ Story notes not found for TEG {teg_num}")
                continue

            print(f"  Preparing TEG {teg_num}...")

            user_message = f"Story Notes:\n\n{story_notes}"

            request = create_batch_request(
                custom_id=f"TEG{teg_num}_brief_summary",
                model="claude-sonnet-4-5",
                max_tokens=2000,
                system_prompt=BRIEF_SUMMARY_PROMPT,
                user_message=user_message,
                use_cache=True
            )
            brief_summary_requests.append(request)

        if brief_summary_requests:
            # Save and submit brief summaries batch
            batch_file = f"{batch_dir}/brief_summaries_{timestamp}.jsonl"
            save_batch_requests(brief_summary_requests, batch_file)

            print("\nSubmitting brief summaries batch to Anthropic...")
            batch_info = submit_batch(batch_file, api_key)
            brief_summaries_batch_id = batch_info['batch_id']
            save_batch_info(batch_info, results_dir, batch_type="brief_summaries")
            batch_ids.append(('brief_summaries', brief_summaries_batch_id))
            print(f"  ✓ Batch ID: {brief_summaries_batch_id}")

    # Phase 3: Satirical Reports (batched for prompt caching)
    satirical_batch_id = None
    if satirical:
        print("\nPHASE 3: Building satirical report batch requests...")
        satirical_report_requests = []

        for teg_num in teg_nums:
            # Read story notes file using Railway-aware helper
            story_notes_path = f"data/commentary/teg_{teg_num}_story_notes.md"
            try:
                story_notes = read_text_file(story_notes_path)
            except Exception:
                print(f"  ✗ Story notes not found for TEG {teg_num}")
                continue

            print(f"  Preparing TEG {teg_num}...")

            user_message = f"Story Notes:\n\n{story_notes}"

            request = create_batch_request(
                custom_id=f"TEG{teg_num}_satire",
                model="claude-sonnet-4-5",
                max_tokens=8000,
                system_prompt=SATIRICAL_REPORT_PROMPT,
                user_message=user_message,
                use_cache=True
            )
            satirical_report_requests.append(request)

        if satirical_report_requests:
            # Save and submit satirical reports batch
            batch_file = f"{batch_dir}/satirical_reports_{timestamp}.jsonl"
            save_batch_requests(satirical_report_requests, batch_file)

            print("\nSubmitting satirical reports batch to Anthropic...")
            batch_info = submit_batch(batch_file, api_key)
            satirical_batch_id = batch_info['batch_id']
            save_batch_info(batch_info, results_dir, batch_type="satirical_reports")
            batch_ids.append(('satirical_reports', satirical_batch_id))
            print(f"  ✓ Batch ID: {satirical_batch_id}")

    # If submit_only, exit now
    if submit_only:
        print("\n" + "="*60)
        print("BATCHES SUBMITTED - YOU CAN NOW CLOSE THIS WINDOW")
        print("="*60)
        for batch_type, batch_id in batch_ids:
            print(f"  {batch_type}: {batch_id}")
        print(f"\nTo retrieve results later, check batch_results/ directory")
        print("="*60)
        return [batch_id for _, batch_id in batch_ids]

    # Otherwise, poll and retrieve results for each batch
    # Main Reports
    if main_reports_batch_id:
        print("\nPolling for main reports completion...")
        poll_until_complete(main_reports_batch_id, api_key, check_interval=60)

        print("\nRetrieving main report results...")
        main_report_results = get_batch_results(main_reports_batch_id, api_key, results_dir)

        # Save main reports to files
        print("\nSaving main reports to files...")
        for teg_num in teg_nums:
            custom_id = f"TEG{teg_num}_main_report"
            if custom_id in main_report_results and main_report_results[custom_id]:
                main_report_text = main_report_results[custom_id]
                output_path = f"data/commentary/drafts/teg_{teg_num}_main_report.md"
                write_text_file(
                    output_path,
                    main_report_text,
                    commit_message=f"Generate main report for TEG {teg_num} (Batch API)"
                )
                results.setdefault(teg_num, {})['main_report'] = main_report_text
                print(f"  ✓ Saved: {output_path}")

    # Brief Summaries
    if brief_summaries_batch_id:
        print("\nPolling for brief summaries completion...")
        poll_until_complete(brief_summaries_batch_id, api_key, check_interval=60)

        print("\nRetrieving brief summary results...")
        brief_summary_results = get_batch_results(brief_summaries_batch_id, api_key, results_dir)

        # Save brief summaries to files
        print("\nSaving brief summaries to files...")
        for teg_num in teg_nums:
            custom_id = f"TEG{teg_num}_brief_summary"
            if custom_id in brief_summary_results and brief_summary_results[custom_id]:
                brief_summary_text = brief_summary_results[custom_id]
                output_path = f"data/commentary/drafts/teg_{teg_num}_brief_summary.md"
                write_text_file(
                    output_path,
                    brief_summary_text,
                    commit_message=f"Generate brief summary for TEG {teg_num} (Batch API)"
                )
                results.setdefault(teg_num, {})['brief_summary'] = brief_summary_text
                print(f"  ✓ Saved: {output_path}")

    # Satirical Reports
    if satirical_batch_id:
        print("\nPolling for satirical reports completion...")
        poll_until_complete(satirical_batch_id, api_key, check_interval=60)

        print("\nRetrieving satirical report results...")
        satirical_report_results = get_batch_results(satirical_batch_id, api_key, results_dir)

        # Save satirical reports to files
        print("\nSaving satirical reports to files...")
        for teg_num in teg_nums:
            custom_id = f"TEG{teg_num}_satire"
            if custom_id in satirical_report_results and satirical_report_results[custom_id]:
                satirical_report_text = satirical_report_results[custom_id]
                output_path = f"data/commentary/drafts/teg_{teg_num}_satire.md"
                write_text_file(
                    output_path,
                    satirical_report_text,
                    commit_message=f"Generate satirical report for TEG {teg_num} (Batch API)"
                )
                results.setdefault(teg_num, {})['satire'] = satirical_report_text
                print(f"  ✓ Saved: {output_path}")

    # Summary
    print("\n" + "="*60)
    print("BATCH API PROCESSING COMPLETE")
    print("="*60)
    print(f"Successfully processed: {len(results)} TEGs")
    print(f"Cost savings: ~50% compared to standard API")
    print("="*60 + "\n")

    return results


# ========================
# Factual Section Formatting (Direct Addition)
# ========================

def format_venue_section(teg_num):
    """
    Format venue context as markdown section (direct addition, no LLM).
    Returns formatted Location & Venue section.
    """
    venue_context = build_venue_context(teg_num)

    # Parse venue_context to extract key info
    lines = venue_context.split('\n')
    area_line = lines[0] if len(lines) > 0 else ""

    # Extract area and year
    area = ""
    if "Tournament Area:" in area_line:
        area = area_line.replace("Tournament Area:", "").strip()

    # Find return context
    return_context = ""
    for line in lines:
        if "Area Return:" in line or "Return to" in line or "NEW DESTINATION:" in line or "First time in" in line:
            return_context = line.strip()
            break

    # Extract courses
    courses = []
    in_courses = False
    for line in lines:
        if line.strip() == "Courses:":
            in_courses = True
            continue
        if in_courses and line.strip().startswith("- Round"):
            courses.append(line.strip()[2:])  # Remove "- " prefix

    # Build formatted section
    section = "## Location & Venue\n"
    if area:
        if return_context:
            section += f"- {area}\n"
            section += f"- {return_context}\n"
        else:
            section += f"- {area}\n"

    if courses:
        section += "- Courses:\n"
        for course in courses:
            section += f"  - {course}\n"

    return section

def _stringify_holders(value) -> str | None:
    """Normalise holder(s) into a clean string."""
    if value is None:
        return None
    if isinstance(value, (list, tuple, set)):
        vals = [str(v).strip() for v in value if str(v).strip()]
        if not vals:
            return None
        return " & ".join(vals) if len(vals) == 2 else ", ".join(vals)
    s = str(value).strip()
    return s or None


def _coerce_record_dict(cr: dict, current_teg_num: int | None = None) -> dict:
    """
    Canonicalise record dictionaries so downstream formatting never KeyErrors.
    Returns keys: course, record_holder, record_score, record_teg.

    Known input variants handled:
      - course / Course
      - record_holders / record_players_this_round / record_holder / holder / player / name
      - record_score / score / value
      - record_teg / teg / TEG / teg_num
      - is_record_this_round (if True and no explicit teg found => use f"TEG {current_teg_num}")
    """
    def pick(d, *names):
        for n in names:
            if n in d and d[n] not in (None, ""):
                return d[n]
        return None

    course = pick(cr, "course", "Course")

    # holders can be a list or a string under several keys
    raw_holders = pick(
        cr,
        "record_holder",
        "record_holders",
        "record_players_this_round",
        "holder",
        "player",
        "name",
        "Record Holder",
    )
    holder_str = _stringify_holders(raw_holders)

    # score
    record_score = pick(cr, "record_score", "score", "value", "Record Score")

    # teg: try direct keys, else infer from flag
    record_teg = pick(cr, "record_teg", "record_set_in_teg", "teg", "TEG", "teg_num")
    if not record_teg:
        is_this_round = bool(cr.get("is_record_this_round"))
        if is_this_round and current_teg_num is not None:
            record_teg = f"TEG {current_teg_num}"
        elif is_this_round:
            record_teg = "this round"
        else:
            record_teg = "previous"

    return {
        "course": course,
        "record_holder": holder_str,
        "record_score": record_score,
        "record_teg": record_teg,
    }


def _normalise_records_payload(all_processed_data: dict, teg_num: int) -> None:
    """
    In-place normalisation of records payload so downstream formatters get canonical keys.
    Expects course-level records under all_processed_data['records']['course_records'].
    Safe no-op if path or types don't match.
    """
    records = all_processed_data.get("records")
    if not isinstance(records, dict):
        return
    course_records = records.get("course_records")
    if not isinstance(course_records, list):
        return
    normalised = []
    for cr in course_records:
        if isinstance(cr, dict):
            normalised.append(_coerce_record_dict(cr, current_teg_num=teg_num))

    records["course_records"] = normalised
    all_processed_data["records"] = records


def format_records_and_pbs_section(all_processed_data, teg_num):
    """
    Format records and personal bests as markdown sections (direct addition, no LLM).
    Returns formatted sections for each round.
    """
    num_rounds = get_teg_rounds(teg_num)
    sections = {}

    for round_num in range(1, num_rounds + 1):
        records_data = all_processed_data['records_by_round'].get(round_num, {})
        course_records = all_processed_data['course_records_by_round'].get(round_num, [])

        round_section = ""

        # Add records & PBs if any exist
        if any(records_data.values()):
            round_section += "\n### Records & Personal Bests\n"

            # All-time records
            if records_data.get('all_time_records'):
                round_section += "**All-Time TEG Records:**\n"
                for record in records_data['all_time_records']:
                    round_section += f"- {record['player']}: {record['value']} ({record['metric']}) - {record['rank']}\n"

            # All-time worsts
            if records_data.get('all_time_worsts'):
                round_section += "**All-Time TEG Worsts:**\n"
                for record in records_data['all_time_worsts']:
                    round_section += f"- {record['player']}: {record['value']} ({record['metric']}) - {record['rank']}\n"

            # Personal bests
            if records_data.get('personal_bests'):
                round_section += "**Personal Bests:**\n"
                for pb in records_data['personal_bests']:
                    round_section += f"- {pb['player']}: {pb['value']} ({pb['metric']}) - {pb['rank']}\n"

            # Personal worsts
            if records_data.get('personal_worsts'):
                round_section += "**Personal Worsts:**\n"
                for pw in records_data['personal_worsts']:
                    round_section += f"- {pw['player']}: {pw['value']} ({pw['metric']}) - {pw['rank']}\n"

        # Add course records if any exist
        if course_records:
            round_section += "\n### Course Records\n"
            for cr in course_records:
                # round_section += f"- {cr['course']}: {cr['record_holder']} {cr['record_score']} ({cr['record_teg']})\n"
                if not isinstance(cr, dict):
                    raise TypeError(f"Record entry is not a dict: {type(cr)}")

                crn = _coerce_record_dict(cr, current_teg_num=teg_num)

                missing = [k for k in ("course", "record_holder", "record_score", "record_teg") if not crn.get(k)]
                if missing:
                    raise KeyError(
                        f"format_records_and_pbs_section: missing fields {missing}; original keys={sorted(cr.keys())}"
                    )

                round_section += f"- {crn['course']}: {crn['record_holder']} {crn['record_score']} ({crn['record_teg']})\n"

                if cr.get('tied_or_set_this_round'):
                    round_section += f"  - **Record {'tied' if cr.get('tied') else 'set'} this round by {cr['player_this_round']}**\n"

        sections[round_num] = round_section

    return sections


def append_factual_sections(story_notes, teg_num, all_processed_data):
    """
    Append factual sections (venue, records, PBs) directly to story notes.
    This data doesn't need LLM synthesis - just formatting.

    Args:
        story_notes: LLM-generated story notes string
        teg_num: Tournament number
        all_processed_data: Dict with all processed data from pattern_analysis

    Returns:
        Complete story notes with factual sections appended
    """
    
    _normalise_records_payload(all_processed_data, teg_num)

    
    lines = story_notes.split('\n')

    # Find where to insert venue section (after synthesis, before round notes)
    # Look for first "## Round" heading
    insert_pos = 0
    for i, line in enumerate(lines):
        if line.startswith("## Round"):
            insert_pos = i
            break

    # Insert venue section before first round
    venue_section = format_venue_section(teg_num)
    if insert_pos > 0:
        lines.insert(insert_pos, venue_section)
        insert_pos += venue_section.count('\n') + 1

    # Get records/PBs sections for each round
    records_sections = format_records_and_pbs_section(all_processed_data, teg_num)

    # Insert records/PBs after each round's notes
    # Work backwards to preserve line numbers
    num_rounds = get_teg_rounds(teg_num)
    for round_num in range(num_rounds, 0, -1):
        # Find end of this round's section
        round_header = f"## Round {round_num} Notes"
        next_round_header = f"## Round {round_num + 1} Notes" if round_num < num_rounds else None

        start_idx = None
        end_idx = len(lines)

        for i, line in enumerate(lines):
            if round_header in line:
                start_idx = i
            elif next_round_header and next_round_header in line:
                end_idx = i
                break

        if start_idx is not None and records_sections.get(round_num):
            # Insert before next round (or at end)
            lines.insert(end_idx, records_sections[round_num])

    return '\n'.join(lines)


# ========================
# File assembly
# ========================

def format_course_info_section(teg_num):
    """
    Format course information section from course_info.py (direct addition, no LLM).
    Returns formatted Course Information section with details about each course played.
    """
    from course_info import COURSE_INFO

    # Load course data for this TEG
    rounds_df = pd.read_csv('data/round_info.csv')
    current_teg = rounds_df[rounds_df['TEGNum'] == teg_num]

    if len(current_teg) == 0:
        return ""

    # Get unique courses played in this TEG (maintaining order)
    courses_played = current_teg[['Round', 'Course']].values.tolist()
    unique_courses = []
    seen = set()
    for _, course in courses_played:
        if course not in seen:
            unique_courses.append(course)
            seen.add(course)

    # Build course information section
    section = "\n## Course Information\n\n"

    for course in unique_courses:
        if course in COURSE_INFO:
            info = COURSE_INFO[course]
            section += f"**{course}**\n"
            section += f"- {info['full_name']}\n"
            section += f"- {info['location']}\n"
            section += f"- Type: {info['type']}"
            if info['par']:
                section += f" | Par: {info['par']}"
            section += "\n"
            if info['designer']:
                section += f"- Designer: {info['designer']}\n"
            if info['rankings']:
                section += f"- Rankings: {info['rankings']}\n"
            section += f"- {info['description']}\n"
            section += "\n"

    return section


def build_story_notes_file(teg_num, round_stories, synthesis, all_processed_data):
    """
    Build complete story notes file with LLM-generated content + factual sections.

    Args:
        teg_num: Tournament number
        round_stories: List of LLM-generated round stories
        synthesis: LLM-generated tournament synthesis
        all_processed_data: Dict with all processed data (for factual sections)
    """
    # Build initial content from LLM-generated parts
    content = f"# TEG {teg_num} Story Notes\n\n"
    content += synthesis + "\n\n"
    for i, round_notes in enumerate(round_stories, 1):
        content += round_notes + "\n\n"

    # Append factual sections (venue, records, PBs)
    content = append_factual_sections(content, teg_num, all_processed_data)

    # Add course information section at the end as manual overlay
    course_info = format_course_info_section(teg_num)
    if course_info:
        content += "\n" + course_info

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
    synthesis = generate_tournament_synthesis(round_stories, teg_num, all_data)
    print("> Tournament synthesis complete")

    story_notes = build_story_notes_file(teg_num, round_stories, synthesis, all_data)

    # Save output using Railway-aware function
    output_path = f"data/commentary/teg_{teg_num}_story_notes.md"
    write_text_file(
        output_path,
        story_notes,
        commit_message=f"Generate story notes for TEG {teg_num}"
    )

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

    # Save output using Railway-aware function
    output_path = f"data/commentary/teg_{teg_num}_story_notes_partial.md"
    write_text_file(
        output_path,
        content,
        commit_message=f"Generate partial story notes for TEG {teg_num} ({completed_rounds} rounds)"
    )

    print(f"\n{'='*60}")
    print(f"PARTIAL STORY NOTES COMPLETE")
    print(f"{'='*60}")
    print(f"\nSaved to: {output_path}")
    print(f"Completed rounds: {completed_rounds}")
    print(f"Total LLM calls: {completed_rounds}")
    print(f"Total characters: {len(content):,}")
    print(f"\n{'='*60}\n")
    return content


def generate_story_notes_via_batch_api(teg_nums, submit_only=False):
    """
    Generate story notes for multiple TEGs using Anthropic Batch API (50% cost reduction).

    Args:
        teg_nums: List of TEG numbers to process
        submit_only: If True, submit batch and exit (don't wait for results)

    Returns:
        Dict with story notes for each TEG, or list of batch_ids if submit_only=True
    """
    print("\n" + "="*60)
    print("BATCH API MODE FOR STORY NOTES (50% cost reduction)")
    if submit_only:
        print("SUBMIT ONLY - Will exit after submission")
    print("="*60)

    api_key = get_api_key()
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY not found in environment variables or Streamlit secrets")

    timestamp = time.strftime("%Y%m%d_%H%M%S")
    batch_dir = "streamlit/commentary/batch_requests"
    results_dir = "streamlit/commentary/batch_results"
    os.makedirs(batch_dir, exist_ok=True)
    os.makedirs(results_dir, exist_ok=True)

    # PHASE 1: Build requests for all round stories
    print("\nPHASE 1: Building round story batch requests...")
    round_story_requests = []

    for teg_num in teg_nums:
        print(f"  Preparing TEG {teg_num}...")

        # Load data
        all_data = process_all_data_types(teg_num)
        num_rounds = get_teg_rounds(teg_num)

        previous_context = None
        for round_num in range(1, num_rounds + 1):
            round_data = load_round_data(teg_num, round_num, all_data)

            # Prepare prompt data
            from round_data_loader import compact_round_data_lossless, abbreviate_for_prompt
            rd_compact = compact_round_data_lossless(round_data)
            rd_abbrev, legend_text = abbreviate_for_prompt(rd_compact)

            round_data_json = json.dumps(rd_abbrev, separators=(",", ":"), ensure_ascii=False, default=str)
            previous_context_json = (
                json.dumps(previous_context, separators=(",", ":"), ensure_ascii=False, default=str)
                if previous_context else "First round of the tournament"
            )

            system_prompt = legend_text + "\n\n" + ROUND_STORY_PROMPT
            user_message = f"""**Round Number:** {round_num}

**Round Data:**
{round_data_json}

**Previous Context:**
{previous_context_json}"""

            request = create_batch_request(
                custom_id=f"TEG{teg_num}_round_{round_num}",
                model="claude-sonnet-4-5",
                max_tokens=4000,
                system_prompt=system_prompt,
                user_message=user_message,
                use_cache=True
            )
            round_story_requests.append(request)

            # Update context for next round
            previous_context = get_round_ending_context(round_data)

    # Submit round stories batch
    batch_file = f"{batch_dir}/story_notes_rounds_{timestamp}.jsonl"
    save_batch_requests(round_story_requests, batch_file)

    print("\nSubmitting round stories batch to Anthropic...")
    batch_info = submit_batch(batch_file, api_key)
    rounds_batch_id = batch_info['batch_id']
    save_batch_info(batch_info, results_dir, batch_type="tournament_round_stories")

    if submit_only:
        print("\n" + "="*60)
        print("BATCH SUBMITTED - YOU CAN NOW CLOSE THIS WINDOW")
        print("="*60)
        print(f"Round stories batch ID: {rounds_batch_id}")
        print(f"\nTo retrieve results later, run:")
        print(f"  python generate_tournament_commentary_v2.py --retrieve-batch {rounds_batch_id}")
        print("\nBatch info saved to:")
        print(f"  {results_dir}/batch_{rounds_batch_id}_info.json")
        print("="*60)
        return [rounds_batch_id]

    # Wait for round stories to complete
    print("\nPolling for round stories completion...")
    poll_until_complete(rounds_batch_id, api_key, check_interval=60)

    print("\nRetrieving round story results...")
    round_story_results = get_batch_results(rounds_batch_id, api_key, results_dir)

    # PHASE 2: Build synthesis requests (need round stories first)
    print("\nPHASE 2: Building synthesis batch requests...")
    synthesis_requests = []

    # Group round stories by TEG
    round_stories_by_teg = {}
    for custom_id, content in round_story_results.items():
        if content is None:
            continue
        # Parse TEG{num}_round_{num}
        parts = custom_id.split('_')
        teg_num = int(parts[0].replace('TEG', ''))

        if teg_num not in round_stories_by_teg:
            round_stories_by_teg[teg_num] = []
        round_stories_by_teg[teg_num].append(content)

    for teg_num in teg_nums:
        if teg_num not in round_stories_by_teg:
            print(f"  ✗ No round stories for TEG {teg_num}")
            continue

        print(f"  Preparing synthesis for TEG {teg_num}...")

        # Load data
        all_data = process_all_data_types(teg_num)
        round_stories = round_stories_by_teg[teg_num]

        # Build synthesis prompt
        all_tournament_data = read_file('data/commentary_tournament_summary.parquet')
        tournament_summary = all_tournament_data[all_tournament_data['TEGNum'] == teg_num].copy()

        # Add historical context
        # IMPORTANT: Use TEG_winners.csv (source of truth) instead of calculated wins
        # because some tournaments used different scoring systems (e.g. TEG 5)
        winners_df = read_file('data/TEG_winners.csv')
        winners_df['TEGNum'] = winners_df['TEG'].str.extract(r'(\d+)').astype(int)
        historical_winners = winners_df[winners_df['TEGNum'] < teg_num]

        def calc_wins_before(row):
            player = row['Player']
            return pd.Series({
                'teg_trophy_wins_before': int((historical_winners['TEG Trophy'] == player).sum()),
                'green_jacket_wins_before': int((historical_winners['Green Jacket'] == player).sum()),
                'wooden_spoons_before': int((historical_winners['HMM Wooden Spoon'] == player).sum())
            })

        historical_counts = tournament_summary.apply(calc_wins_before, axis=1)
        tournament_summary = pd.concat([tournament_summary, historical_counts], axis=1)

        round_summaries_text = "\n\n".join([f"## Round {i+1}\n{story}" for i, story in enumerate(round_stories)])
        tournament_data_json = json.dumps(tournament_summary.to_dict('records'), indent=2, default=str)

        # Historical context
        historical_context = "**Historical wins BEFORE this tournament:**\n"
        for _, row in tournament_summary.iterrows():
            player = row['Player']
            trophies = row['teg_trophy_wins_before']
            jackets = row['green_jacket_wins_before']
            spoons = row['wooden_spoons_before']
            historical_context += f"- {player}: {trophies} Trophy, {jackets} Green Jacket, {spoons} Wooden Spoons\n"

        # Career context
        players_in_teg = tournament_summary['Player'].tolist()
        career_context = build_career_context(teg_num, players_in_teg)

        # Victory context
        victory_context_json = "Not available"
        if all_data and 'victory_context' in all_data:
            victory_context_json = json.dumps(all_data['victory_context'], indent=2, default=str)

        system_prompt = TOURNAMENT_SYNTHESIS_PROMPT
        user_message = f"""Round Summaries:
{round_summaries_text}

Tournament Data:
{tournament_data_json}

Victory Context:
{victory_context_json}

Historical Context:
{historical_context}

Career Context:
{career_context}"""

        request = create_batch_request(
            custom_id=f"TEG{teg_num}_synthesis",
            model="claude-sonnet-4-5",
            max_tokens=4000,
            system_prompt=system_prompt,
            user_message=user_message,
            use_cache=True
        )
        synthesis_requests.append(request)

    # Submit synthesis batch
    batch_file = f"{batch_dir}/story_notes_synthesis_{timestamp}.jsonl"
    save_batch_requests(synthesis_requests, batch_file)

    print("\nSubmitting synthesis batch to Anthropic...")
    batch_info = submit_batch(batch_file, api_key)
    synthesis_batch_id = batch_info['batch_id']
    save_batch_info(batch_info, results_dir, batch_type="tournament_synthesis")

    print("\nPolling for synthesis completion...")
    poll_until_complete(synthesis_batch_id, api_key, check_interval=60)

    print("\nRetrieving synthesis results...")
    synthesis_results = get_batch_results(synthesis_batch_id, api_key, results_dir)

    # PHASE 3: Assemble and save story notes
    print("\nPHASE 3: Assembling and saving story notes...")
    results = {}

    for teg_num in teg_nums:
        if teg_num not in round_stories_by_teg:
            continue

        synthesis_id = f"TEG{teg_num}_synthesis"
        if synthesis_id not in synthesis_results or synthesis_results[synthesis_id] is None:
            print(f"  ✗ No synthesis for TEG {teg_num}")
            continue

        print(f"  Assembling TEG {teg_num}...")

        # Load data for post-processing
        all_data = process_all_data_types(teg_num)
        round_stories = round_stories_by_teg[teg_num]
        synthesis = synthesis_results[synthesis_id]

        # Build complete story notes with post-processing
        story_notes = build_story_notes_file(teg_num, round_stories, synthesis, all_data)

        # Save
        output_path = f"data/commentary/teg_{teg_num}_story_notes.md"
        write_text_file(
            output_path,
            story_notes,
            commit_message=f"Generate story notes for TEG {teg_num} (Batch API)"
        )

        results[teg_num] = story_notes
        print(f"  ✓ Saved: {output_path}")

    # Summary
    print("\n" + "="*60)
    print("BATCH API PROCESSING COMPLETE")
    print("="*60)
    print(f"Successfully processed: {len(results)}/{len(teg_nums)} TEGs")
    print(f"Cost savings: ~50% compared to standard API")
    print(f"Round stories batch ID: {rounds_batch_id}")
    print(f"Synthesis batch ID: {synthesis_batch_id}")
    print("="*60 + "\n")

    return results


def retrieve_story_notes_batch(batch_id):
    """
    Retrieve results from a previously submitted story notes batch.

    Args:
        batch_id: Batch ID to retrieve

    Returns:
        Results dict or None if batch not complete
    """
    print("\n" + "="*60)
    print(f"RETRIEVING STORY NOTES BATCH: {batch_id}")
    print("="*60)

    api_key = get_api_key()
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY not found")

    results_dir = "streamlit/commentary/batch_results"

    # Check status
    print("\nChecking batch status...")
    status = check_batch_status(batch_id, api_key)
    print(f"  Status: {status['status']}")
    print(f"  Request counts: {status['request_counts']}")

    if status['status'] != 'ended':
        print(f"\n⚠️  Batch not complete yet. Current status: {status['status']}")
        print(f"Check again later or run:")
        print(f"  python generate_tournament_commentary_v2.py --retrieve-batch {batch_id}")
        return None

    # Load batch info to determine type
    batch_info_file = find_batch_info_file(batch_id, results_dir)
    if not batch_info_file:
        print(f"\n⚠️  Warning: Batch info file not found for {batch_id}")
        batch_type = "unknown"
    else:
        batch_info = load_batch_info(batch_info_file)
        batch_type = batch_info.get('batch_type', 'unknown')
        print(f"  Batch type: {batch_type}")

    # Retrieve results
    print("\nRetrieving results...")
    results = get_batch_results(batch_id, api_key, results_dir)

    if batch_type == "tournament_round_stories":
        print("\n⚠️  This is a round stories batch.")
        print("You also need the synthesis batch to complete story notes.")
        print("Round stories have been saved. Check for synthesis batch ID in batch info.")
        return results

    elif batch_type == "tournament_synthesis":
        print("\n⚠️  This is a synthesis batch.")
        print("You also need the round stories batch to complete story notes.")
        print("Run this command with the round stories batch ID first.")
        return results

    else:
        print(f"  ⚠️  Unknown batch type '{batch_type}'")
        print("Results saved but may require manual processing.")
        return results


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

    parser = argparse.ArgumentParser(
        description='Generate tournament story notes and reports',
        epilog='''
Examples:
  # Generate story notes only
  python %(prog)s 17

  # Generate story notes for partial tournament (first 2 rounds)
  python %(prog)s 17 --partial 2

  # Generate reports from existing story notes
  python %(prog)s 17 --generate-reports

  # Generate story notes AND reports in one go
  python %(prog)s 17 --full-pipeline

  # Generate only main report (no brief summary)
  python %(prog)s 17 --main-report-only

  # Generate only brief summary (no main report)
  python %(prog)s 17 --brief-summary-only

  # Generate only satirical report
  python %(prog)s 17 --satirical-only

  # Generate all reports including satirical
  python %(prog)s 17 --generate-reports --include-satire

  # Use batch API for reports (50%% cheaper, submit and wait)
  python %(prog)s --range 3 17 --generate-reports --use-batch

  # Submit batch and exit (retrieve results later)
  python %(prog)s --range 3 17 --main-report-only --use-batch --submit-only

  # Process multiple tournaments
  python %(prog)s --range 10 12
        ''',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    # Either provide a single TEG number (positional) OR use --range START END
    parser.add_argument('teg_num', type=int, nargs='?', help='Single tournament number (omit if using --range)')
    parser.add_argument('--partial', type=int, help='Number of completed rounds (for in-progress tournaments)')
    parser.add_argument('--range', type=int, nargs=2, metavar=('START','END'),
                        help='Run a range of TEGs inclusive, e.g. --range 10 12')
    parser.add_argument('--stop-on-error', action='store_true', help='Abort batch on first error')
    parser.add_argument('--pause-between', type=float, default=0.0, help='Seconds to pause between tournaments')

    # Report generation options (Level 3)
    parser.add_argument('--generate-reports', action='store_true',
                        help='Generate reports from existing story notes (both main report and brief summary)')
    parser.add_argument('--main-report-only', action='store_true',
                        help='Generate only the main report from existing story notes')
    parser.add_argument('--brief-summary-only', action='store_true',
                        help='Generate only the brief summary from existing story notes')
    parser.add_argument('--satirical-only', action='store_true',
                        help='Generate only the satirical report from existing story notes')
    parser.add_argument('--include-satire', action='store_true',
                        help='Include satirical report in addition to other selected reports')
    parser.add_argument('--full-pipeline', action='store_true',
                        help='Generate story notes AND reports in one go')
    parser.add_argument('--batch-reports', action='store_true',
                        help='When using --range, batch reports by type for optimal prompt caching (all main reports, then all summaries)')
    parser.add_argument('--use-batch', action='store_true',
                        help='Use Anthropic Batch API (50%% cheaper, up to 24hr processing)')
    parser.add_argument('--submit-only', action='store_true',
                        help='Submit batch and exit (retrieve results later with --retrieve-batch)')
    parser.add_argument('--retrieve-batch', type=str, metavar='BATCH_ID',
                        help='Retrieve results from previously submitted batch')
    parser.add_argument('--list-batches', action='store_true',
                        help='List recent batch submissions and their status')

    args = parser.parse_args()

    # Handle list-batches command
    if args.list_batches:
        list_recent_batches()
        sys.exit(0)

    # Handle retrieve-batch command
    if args.retrieve_batch:
        retrieve_story_notes_batch(args.retrieve_batch)
        sys.exit(0)

    if args.range:
        start, end = args.range
        
        # Batch reports mode: optimize for prompt caching
        if args.batch_reports:
            print(f"\n{'='*60}")
            print(f"BATCH MODE: Optimized for prompt caching")
            print(f"{'='*60}\n")

            successful_tegs = []

            # Phase 1: Generate all story notes (unless skipped)
            if not (args.generate_reports or args.main_report_only or args.brief_summary_only):
                print("Phase 1: Generating story notes for all TEGs...")

                # Use Batch API for story notes if requested
                if args.use_batch:
                    teg_list = list(range(start, end + 1))
                    try:
                        generate_story_notes_via_batch_api(teg_list, submit_only=args.submit_only)
                        if args.submit_only:
                            # Exit after submission
                            sys.exit(0)
                        successful_tegs = teg_list
                    except Exception as e:
                        print(f"✗ Batch story notes failed: {e}")
                        successful_tegs = []
                else:
                    # Standard API
                    for teg in range(start, end + 1):
                        try:
                            if args.partial:
                                generate_story_notes_up_to_round(teg, args.partial)
                            else:
                                generate_complete_story_notes(teg)
                            successful_tegs.append(teg)
                        except Exception as e:
                            print(f"✗ TEG {teg} story notes failed: {e}")
            else:
                # If only generating reports, assume all TEGs succeeded
                successful_tegs = list(range(start, end + 1))

            # Phase 2 & 3: Generate reports (if requested)
            if args.generate_reports or args.main_report_only or args.brief_summary_only or args.satirical_only or args.include_satire or args.full_pipeline:
                if args.use_batch:
                    # Use Batch API for all report types
                    generate_main = args.generate_reports or args.main_report_only or args.full_pipeline
                    generate_brief = args.generate_reports or args.brief_summary_only or args.full_pipeline
                    generate_satire = args.satirical_only or args.include_satire or args.full_pipeline
                    generate_reports_via_batch_api(
                        successful_tegs,
                        main_report=generate_main,
                        brief_summary=generate_brief,
                        satirical=generate_satire,
                        submit_only=args.submit_only
                    )
                else:
                    # Phase 2: Generate main reports (batched for caching)
                    if args.generate_reports or args.main_report_only or args.full_pipeline:
                        print(f"\nPhase 2: Generating main reports (batched for caching)...")
                        for teg in successful_tegs:
                            try:
                                generate_main_report(teg)
                            except Exception as e:
                                print(f"✗ TEG {teg} main report failed: {e}")

                    # Phase 3: Generate brief summaries (batched for caching)
                    if args.generate_reports or args.brief_summary_only or args.full_pipeline:
                        print(f"\nPhase 3: Generating brief summaries (batched for caching)...")
                        for teg in successful_tegs:
                            try:
                                generate_brief_summary(teg)
                            except Exception as e:
                                print(f"✗ TEG {teg} brief summary failed: {e}")

                    # Phase 4: Generate satirical reports (batched for caching)
                    if args.satirical_only or args.include_satire or args.full_pipeline:
                        print(f"\nPhase 4: Generating satirical reports (batched for caching)...")
                        for teg in successful_tegs:
                            try:
                                generate_satirical_report(teg)
                            except Exception as e:
                                print(f"✗ TEG {teg} satirical report failed: {e}")

            print(f"\n{'='*60}")
            print(f"BATCH COMPLETE: Processed TEGs {successful_tegs}")
            print(f"{'='*60}\n")
        
        # Normal mode: process each TEG completely before moving to next
                # Normal mode: process according to report flags (no batch)
        else:
            start, end = args.range
            teg_list = list(range(start, end + 1))

            # Full pipeline over a range (generate notes then all reports)
            if args.full_pipeline:
                for teg in teg_list:
                    try:
                        if args.partial:
                            generate_story_notes_up_to_round(teg, args.partial)
                        else:
                            generate_complete_story_notes(teg)
                        generate_reports_from_story_notes(
                            teg,
                            main_report=True,
                            brief_summary=True,
                            satirical=args.include_satire
                        )
                    except Exception as e:
                        print(f"✗ TEG {teg} full pipeline failed: {e}")

            # Report-only modes over a range (DO NOT generate story notes here)
            elif args.generate_reports or args.main_report_only or args.brief_summary_only or args.satirical_only or args.include_satire:
                for teg in teg_list:
                    # main report only (or both via --generate-reports)
                    if args.generate_reports or args.main_report_only:
                        try:
                            generate_main_report(teg)
                        except Exception as e:
                            print(f"✗ TEG {teg} main report failed: {e}")

                    # brief summary only (or both via --generate-reports)
                    if args.generate_reports or args.brief_summary_only:
                        try:
                            generate_brief_summary(teg)
                        except Exception as e:
                            print(f"✗ TEG {teg} brief summary failed: {e}")

                    # satirical only (or with --include-satire)
                    if args.satirical_only or args.include_satire:
                        try:
                            generate_satirical_report(teg)
                        except Exception as e:
                            print(f"✗ TEG {teg} satirical report failed: {e}")

            # No report flags: default to generating story notes across the range
            else:
                generate_story_notes_for_teg_range(
                    start, end,
                    partial=args.partial,
                    stop_on_error=args.stop_on_error,
                    pause_between=args.pause_between,
                )

    else:
        if args.teg_num is None:
            parser.error("Provide a single TEG number or --range START END")

        # Handle report generation modes
        if args.generate_reports:
            generate_reports_from_story_notes(
                args.teg_num,
                main_report=True,
                brief_summary=True,
                satirical=args.include_satire
            )
        elif args.main_report_only:
            generate_main_report(args.teg_num)
        elif args.brief_summary_only:
            generate_brief_summary(args.teg_num)
        elif args.satirical_only:
            generate_satirical_report(args.teg_num)
        elif args.full_pipeline:
            # Generate story notes first
            if args.partial:
                generate_story_notes_up_to_round(args.teg_num, args.partial)
                print("\nSkipping report generation for partial tournament (story notes only)")
            else:
                generate_complete_story_notes(args.teg_num)
                # Then generate reports
                print("\nProceeding to report generation...")
                generate_reports_from_story_notes(
                    args.teg_num,
                    main_report=True,
                    brief_summary=True,
                    satirical=args.include_satire
                )
        else:
            # Default behavior: story notes only
            if args.partial:
                generate_story_notes_up_to_round(args.teg_num, args.partial)
            else:
                generate_complete_story_notes(args.teg_num)
