"""Live round entry: multi-device score sync for a round in progress.

Ported from the `round_entry_grid.html` mockup's design (see
DATA_STORAGE_INGESTION_PLAN.md, "Phase 3.4 design"). Two players entering
scores on separate phones for the same round need a shared, server-arbitrated
state instead of the mockup's same-browser BroadcastChannel/localStorage
stand-in. This module is that shared state.

Storage is two CSVs, read/written through the existing `teg_analysis.io`
layer like everything else in `data/` (no new file type):

    data/live_rounds.csv                registry: one row per live round ever
                                         started (Token, TEGNum, Round,
                                         CreatedAt, Status)
    data/live_rounds/{token}.csv        per-round staging: current state per
                                         cell (not an event log), written
                                         volume-only (defer_github=True,
                                         result discarded) on every score
                                         write so live entry never spams
                                         GitHub commits

The server -- never a client clock -- assigns a monotonic `Seq` to every
write, in arrival order. That's what makes polling deltas
(`?since=seq`) cheap and eliminates the mockup's client-timestamp
tie-divergence bug outright: there's only one ordering, decided in one place.

Conflict model: a write from a *different* device than the cell's current
owner, with a *different* value, sets `Conflict=True` and keeps the old value
in `PrevScore`/`PrevDeviceName` -- entry is never blocked, but
`finalize_live_round` refuses to run while any conflict remains. Conflicts
are cleared only by `resolve_conflict` (an explicit admin action), never by a
later write that happens to match -- a silent auto-clear would hide the exact
disagreement the flag exists to surface.

    start_live_round()      admin: TEG+Round -> token, empty staging file
        -> get_live_round_context()   player page: roster + Par/SI + status
        -> apply_score_writes()       player: write N cells, get the new seq
        -> get_scores_since()         player: poll for changes since a seq
        -> resolve_conflict()         admin: pick a value, clear the flag
        -> finalize_live_round()      admin: staging -> execute_data_update()
        -> cancel_live_round()        admin: abandon without touching all-scores
"""

import logging
import secrets
import threading
from datetime import datetime, timezone

import pandas as pd

from teg_analysis.constants import LIVE_ROUNDS_REGISTRY_CSV, LIVE_ROUND_STAGING_DIR, ROUND_PARS_CSV

logger = logging.getLogger(__name__)

_REGISTRY_COLUMNS = ["Token", "TEGNum", "Round", "CreatedAt", "Status"]
_STAGING_COLUMNS = [
    "Hole", "Pl", "Score", "DeviceId", "DeviceName", "Seq",
    "Conflict", "PrevScore", "PrevDeviceName",
]

# Guards every staging-file read-modify-write cycle, mirroring
# data_update.py's _update_lock. One lock for all live rounds is fine at this
# scale (a handful of devices polling every few seconds) -- no need for a
# lock-per-token map.
_lock = threading.Lock()


class LiveRoundError(Exception):
    """Base class for live-round errors."""


class LiveRoundNotFoundError(LiveRoundError):
    pass


class LiveRoundInactiveError(LiveRoundError):
    pass


class LiveRoundAlreadyActiveError(LiveRoundError):
    pass


class ConflictsUnresolvedError(LiveRoundError):
    pass


class RoundParsNotConfirmedError(LiveRoundError):
    pass


def _staging_path(token: str) -> str:
    return f"{LIVE_ROUND_STAGING_DIR}/{token}.csv"


def _archive_path(token: str) -> str:
    return f"{LIVE_ROUND_STAGING_DIR}/archive/{token}.csv"


def _empty_staging_df() -> pd.DataFrame:
    return pd.DataFrame(columns=_STAGING_COLUMNS)


def _read_staging(token: str) -> pd.DataFrame:
    from teg_analysis.io import read_file

    try:
        return read_file(_staging_path(token))
    except FileNotFoundError:
        return _empty_staging_df()


def _write_staging(token: str, df: pd.DataFrame) -> None:
    from teg_analysis.io import write_file

    # Volume-only: defer_github=True and the returned file-info is discarded,
    # so a live round's dozens of writes never touch GitHub. Only the
    # registry (start/finalize/cancel) and the real all-scores write at
    # finalize are ever committed.
    write_file(_staging_path(token), df, "live round staging (not committed)", defer_github=True)


def _read_registry() -> pd.DataFrame:
    from teg_analysis.io import read_file

    try:
        return read_file(LIVE_ROUNDS_REGISTRY_CSV)
    except FileNotFoundError:
        return pd.DataFrame(columns=_REGISTRY_COLUMNS)


def _write_registry(df: pd.DataFrame) -> None:
    from teg_analysis.io import write_file

    write_file(LIVE_ROUNDS_REGISTRY_CSV, df, "Update live rounds registry")


def _get_registry_row(token: str) -> dict | None:
    registry = _read_registry()
    match = registry[registry["Token"] == token]
    if match.empty:
        return None
    return match.iloc[0].to_dict()


def generate_token() -> str:
    return secrets.token_urlsafe(8)


# ---------------------------------------------------------------------------
# Admin: lifecycle
# ---------------------------------------------------------------------------

def list_live_rounds() -> list[dict]:
    """Every live round ever started, newest first."""
    registry = _read_registry()
    if registry.empty:
        return []
    return registry.sort_values("CreatedAt", ascending=False).to_dict("records")


def start_live_round(teg_num: int, round_num: int) -> dict:
    """Start a live round for an already-set-up TEG+Round.

    Requires round_pars.csv to already have a *confirmed* entry for this
    TEG+Round (Phase 2.5) -- a live round built on an unconfirmed course
    default would let players enter scores against Par/SI nobody's actually
    checked.

    Returns the new registry row (includes the token for the shareable link).
    """
    from teg_analysis.analysis.round_setup import get_round_setup_form

    setup = get_round_setup_form(teg_num, round_num)
    if setup["source"] != "confirmed":
        raise RoundParsNotConfirmedError(
            f"TEG {teg_num} Round {round_num}'s Par/SI isn't confirmed yet -- "
            "set it up on the Round setup page first."
        )

    with _lock:
        registry = _read_registry()
        active_dupe = registry[
            (registry["TEGNum"] == teg_num)
            & (registry["Round"] == round_num)
            & (registry["Status"] == "active")
        ]
        if not active_dupe.empty:
            raise LiveRoundAlreadyActiveError(
                f"TEG {teg_num} Round {round_num} already has an active live round "
                f"(token {active_dupe.iloc[0]['Token']})."
            )

        token = generate_token()
        new_row = {
            "Token": token,
            "TEGNum": teg_num,
            "Round": round_num,
            "CreatedAt": datetime.now(timezone.utc).isoformat(),
            "Status": "active",
        }
        registry = pd.concat([registry, pd.DataFrame([new_row])], ignore_index=True)
        _write_registry(registry)
        _write_staging(token, _empty_staging_df())

    return new_row


def cancel_live_round(token: str) -> dict:
    """Abandon a live round without ever touching all-scores."""
    with _lock:
        reg = _get_registry_row(token)
        if reg is None:
            raise LiveRoundNotFoundError(token)
        registry = _read_registry()
        registry.loc[registry["Token"] == token, "Status"] = "cancelled"
        _write_registry(registry)
    return {"token": token, "status": "cancelled"}


def finalize_live_round(token: str) -> dict:
    """Write a live round's staged scores into the permanent record.

    Refuses while any cell is still flagged Conflict=True. Only complete
    18-hole player-rounds are written, matching
    data_update.process_google_sheets_data's existing rule -- a partial
    scorecard never enters the permanent record. Reuses execute_data_update
    exactly as the "add a round" flow does: one GitHub commit, every derived
    cache regenerated.
    """
    from teg_analysis.io import read_file
    from teg_analysis.analysis.data_update import execute_data_update

    with _lock:
        reg = _get_registry_row(token)
        if reg is None:
            raise LiveRoundNotFoundError(token)
        if reg["Status"] != "active":
            raise LiveRoundInactiveError(f"Live round {token} is {reg['Status']}, not active.")

        staging = _read_staging(token)
        if staging.empty:
            raise ValueError("No scores entered yet -- nothing to finalize.")
        if bool((staging["Conflict"] == True).any()):  # noqa: E712
            raise ConflictsUnresolvedError(
                "Resolve every conflicted cell before finalizing this round."
            )

        teg_num, round_num = int(reg["TEGNum"]), int(reg["Round"])

        pars = read_file(ROUND_PARS_CSV)
        pars = pars[(pars["TEGNum"] == teg_num) & (pars["Round"] == round_num)][["Hole", "Par", "SI"]]

        long_df = staging[staging["Score"].notna()][["Hole", "Pl", "Score"]].copy()
        long_df["Hole"] = long_df["Hole"].astype(int)
        long_df["Score"] = long_df["Score"].astype(int)
        long_df["TEGNum"] = teg_num
        long_df["Round"] = round_num
        long_df = long_df.merge(pars, on="Hole", how="left")

        long_df = long_df.groupby("Pl").filter(lambda x: len(x) == 18)
        if long_df.empty:
            raise ValueError("No complete 18-hole player-rounds to finalize yet.")

        result = execute_data_update(long_df, new_data_only=True)

        registry = _read_registry()
        registry.loc[registry["Token"] == token, "Status"] = "finalized"
        _write_registry(registry)
        _archive_staging(token)

    return {"token": token, "teg_num": teg_num, "round_num": round_num, **result}


def _archive_staging(token: str) -> None:
    from teg_analysis.io import write_file

    staging = _read_staging(token)
    write_file(_archive_path(token), staging, f"Archive finished live round {token}", defer_github=True)


def resolve_conflict(token: str, hole: int, player: str, chosen_value: int, resolved_by: str) -> dict:
    """Admin picks the correct value for one conflicted cell, clearing the flag."""
    with _lock:
        reg = _get_registry_row(token)
        if reg is None:
            raise LiveRoundNotFoundError(token)

        staging = _read_staging(token)
        next_seq = int(staging["Seq"].max()) + 1 if not staging.empty else 1
        mask = (staging["Hole"] == hole) & (staging["Pl"] == player)

        new_row = {
            "Hole": hole, "Pl": player, "Score": chosen_value,
            "DeviceId": "admin", "DeviceName": resolved_by,
            "Seq": next_seq, "Conflict": False,
            "PrevScore": None, "PrevDeviceName": None,
        }
        staging = staging[~mask]
        staging = pd.concat([staging, pd.DataFrame([new_row])], ignore_index=True)
        _write_staging(token, staging)

    return {"seq": next_seq}


# ---------------------------------------------------------------------------
# Player-facing: read the entry page's context, write scores, poll for changes
# ---------------------------------------------------------------------------

def get_live_round_context(token: str) -> dict | None:
    """Everything the entry page needs to render: roster, Par/SI, status.

    Returns None if the token doesn't exist. Raises nothing else -- an empty
    roster or a since-cancelled round are valid states the page itself
    should explain, not exceptions.
    """
    reg = _get_registry_row(token)
    if reg is None:
        return None

    from teg_analysis.analysis.teg_setup import get_teg_roster_form
    from teg_analysis.analysis.round_setup import get_round_setup_form
    from teg_analysis.core.data_loader import get_player_name

    teg_num, round_num = int(reg["TEGNum"]), int(reg["Round"])

    roster = get_teg_roster_form(teg_num)
    players = [p["code"] for p in roster["players"] if p["playing"]]

    setup = get_round_setup_form(teg_num, round_num)

    return {
        "token": token,
        "teg_num": teg_num,
        "round_num": round_num,
        "status": reg["Status"],
        "course": setup["course"],
        "players": players,
        "player_names": {p: get_player_name(p) for p in players},
        "holes": setup["holes"],
    }


def apply_score_writes(token: str, device_id: str, device_name: str, cells: list[dict]) -> dict:
    """Write N cells (a single tap, or a whole voice-entry batch) in one pass.

    Each cell: {"hole": int, "player": str, "value": int | None} (None clears
    the cell). Returns {"seq": <new highest seq>} so the caller can bump its
    own polling cursor past what it just wrote.
    """
    with _lock:
        reg = _get_registry_row(token)
        if reg is None:
            raise LiveRoundNotFoundError(token)
        if reg["Status"] != "active":
            raise LiveRoundInactiveError(f"Live round {token} is {reg['Status']}, not active.")

        staging = _read_staging(token)
        next_seq = int(staging["Seq"].max()) + 1 if not staging.empty else 1

        for cell in cells:
            hole = int(cell["hole"])
            player = cell["player"]
            value = cell.get("value")

            mask = (staging["Hole"] == hole) & (staging["Pl"] == player)
            existing = staging[mask]

            conflict, prev_score, prev_device = False, None, None
            if not existing.empty:
                row = existing.iloc[0]
                existing_score = None if pd.isna(row["Score"]) else row["Score"]
                if row["DeviceId"] != device_id and existing_score != value:
                    conflict = True
                    prev_score, prev_device = existing_score, row["DeviceName"]
                elif bool(row.get("Conflict", False)):
                    # A prior conflict on this cell stays flagged until an
                    # admin explicitly resolves it -- a same-value or
                    # same-device write doesn't get to silently clear it.
                    conflict = True
                    prev_score = row.get("PrevScore")
                    prev_device = row.get("PrevDeviceName")

            new_row = {
                "Hole": hole, "Pl": player, "Score": value,
                "DeviceId": device_id, "DeviceName": device_name,
                "Seq": next_seq, "Conflict": conflict,
                "PrevScore": prev_score, "PrevDeviceName": prev_device,
            }
            staging = staging[~mask]
            staging = pd.concat([staging, pd.DataFrame([new_row])], ignore_index=True)
            next_seq += 1

        _write_staging(token, staging)

    return {"seq": next_seq - 1}


def get_scores_since(token: str, since_seq: int = 0) -> dict:
    """Poll for cell changes with Seq > since_seq (everything, if 0)."""
    reg = _get_registry_row(token)
    if reg is None:
        raise LiveRoundNotFoundError(token)

    staging = _read_staging(token)
    if staging.empty:
        return {"seq": 0, "status": reg["Status"], "cells": []}

    changed = staging[staging["Seq"] > since_seq]
    cells = [
        {
            "hole": int(r["Hole"]),
            "player": r["Pl"],
            "value": None if pd.isna(r["Score"]) else int(r["Score"]),
            "conflict": bool(r["Conflict"]),
            "device_name": r["DeviceName"],
            "prev_value": None if pd.isna(r.get("PrevScore")) else int(r["PrevScore"]),
            # CSV round-tripping turns a written None into NaN on read-back (float,
            # not None) -- unguarded, that reaches Starlette's JSONResponse, which
            # (unlike Python's json module) rejects NaN outright (allow_nan=False).
            "prev_device_name": None if pd.isna(r.get("PrevDeviceName")) else r.get("PrevDeviceName"),
        }
        for _, r in changed.iterrows()
    ]
    return {"seq": int(staging["Seq"].max()), "status": reg["Status"], "cells": cells}
