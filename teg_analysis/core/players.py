"""Player identity: the writable source of truth for player codes and names.

Historically the code->name mapping lived only in ``constants.PLAYER_DICT``,
which made adding a never-before-seen player a code change (the deployed
webapp can write data files, but not edit constants.py). ``data/players.csv``
(columns: Code, Name) replaces it as the source of truth so an admin can add
a player from the TEG setup page; ``PLAYER_DICT`` remains as the seed/fallback
for environments where the file doesn't exist yet, and any code present in
both places takes its name from the file.

All lookups go through :func:`get_player_dict`. The file is tiny but read on
hot paths (name-mapping every hole row on data updates), so it's cached at
module level -- ``clear_player_cache()`` must be called after any write to
players.csv (``add_player`` does this itself; the webapp's
``deps.clear_all_data_caches`` also clears it, same as every other data cache).
"""

import re
import threading

import pandas as pd

from teg_analysis.constants import PLAYERS_CSV, PLAYER_DICT

_CODE_RE = re.compile(r"^[A-Z]{2,3}$")

# Cache of the merged code->name dict. Guarded by a lock only around the
# read-populate cycle; writers (add_player) hold it across read-modify-write.
_lock = threading.Lock()
_cache: dict[str, str] | None = None


class PlayerError(ValueError):
    """Invalid player data (bad code format, duplicate code/name, ...)."""


def _read_players_file() -> pd.DataFrame:
    from teg_analysis.io import read_file

    try:
        return read_file(PLAYERS_CSV)
    except FileNotFoundError:
        return pd.DataFrame(columns=["Code", "Name"])


def get_player_dict() -> dict[str, str]:
    """Code -> full-name mapping: players.csv merged over the PLAYER_DICT seed.

    File order is preserved for players in the file (it drives roster/selector
    ordering); seed-only players (present in constants but not yet in the
    file) are appended after.
    """
    global _cache
    with _lock:
        if _cache is None:
            df = _read_players_file()
            from_file = {
                str(r["Code"]).strip().upper(): str(r["Name"]).strip()
                for _, r in df.iterrows()
                if pd.notna(r.get("Code")) and str(r.get("Code")).strip()
            }
            merged = dict(from_file)
            for code, name in PLAYER_DICT.items():
                merged.setdefault(code, name)
            _cache = merged
        return dict(_cache)


def get_name_to_code() -> dict[str, str]:
    """Full-name -> code reverse lookup."""
    return {name: code for code, name in get_player_dict().items()}


def get_player_name(code: str) -> str:
    """Full name for a player code, or 'Unknown Player'."""
    return get_player_dict().get(code.upper(), "Unknown Player")


def clear_player_cache() -> None:
    global _cache
    with _lock:
        _cache = None


def add_player(code: str, name: str) -> dict:
    """Register a brand-new player (someone who has never played a TEG).

    Appends one row to players.csv after validating the code (2-3 letters,
    stored uppercase) and that neither the code nor the name is already
    taken. Doesn't touch handicaps.csv -- the TEG setup roster form already
    scopes to all known players and its save upserts a column per player, so
    the new player simply appears there as not-playing until ticked.

    Returns ``{"code": ..., "name": ...}`` as stored.
    """
    from teg_analysis.io import write_file

    code = (code or "").strip().upper()
    name = " ".join((name or "").split())  # collapse internal whitespace
    if not _CODE_RE.match(code):
        raise PlayerError("Code must be 2-3 letters (e.g. JS).")
    if not name:
        raise PlayerError("A name is required.")

    global _cache
    with _lock:
        _cache = None  # force fresh read inside the write cycle
        df = _read_players_file()
        existing = {
            str(r["Code"]).strip().upper(): str(r["Name"]).strip()
            for _, r in df.iterrows()
            if pd.notna(r.get("Code"))
        }
        for c, n in PLAYER_DICT.items():
            existing.setdefault(c, n)

        if code in existing:
            raise PlayerError(f"Code {code} is already taken ({existing[code]}).")
        taken_names = {n.casefold() for n in existing.values()}
        if name.casefold() in taken_names:
            raise PlayerError(f'"{name}" already exists.')

        # Seed the file with the full current roster on first write, so the
        # file is the complete source of truth from then on (not a delta).
        if df.empty:
            df = pd.DataFrame(
                [{"Code": c, "Name": n} for c, n in existing.items()]
            )
        df = pd.concat([df, pd.DataFrame([{"Code": code, "Name": name}])], ignore_index=True)
        write_file(PLAYERS_CSV, df, f"Add new player {code} ({name})")
        _cache = None

    return {"code": code, "name": name}
