"""TEG-level roster + handicap setup, ahead of a TEG being played.

Not every player plays every TEG. ``handicaps.csv`` (wide format: one row per
TEG, one column per player) already has an implicit "not playing" convention
-- a 0 or blank cell -- but nothing surfaced it for editing, and handicaps for
a brand-new TEG were only ever seen as a read-only calculated draft on the
Handicaps page. This module lets an admin confirm, ahead of a TEG, who's
actually playing and what handicap to use, prepopulated from the same two
sources the read-only page already used:

    handicaps.csv row for this TEG (if already confirmed/saved)
        -> get_teg_roster_form()  else fall back to the calculated draft
                                   (teg_analysis.analysis.handicaps.get_hc)
        -> save_teg_roster()      upsert the one row for this TEG, writing 0
                                   for players marked not-playing
"""

import pandas as pd

from teg_analysis.constants import HANDICAPS_CSV


def _read_handicaps_raw() -> pd.DataFrame:
    from teg_analysis.io import read_file

    return read_file(HANDICAPS_CSV)


def get_roster_players() -> list[str]:
    """Player codes with a column in handicaps.csv, in file order."""
    raw = _read_handicaps_raw()
    return [c for c in raw.columns if c != "TEG"]


def get_next_teg() -> int:
    """The TEG that should default to the top of the setup page."""
    from teg_analysis.analysis.handicaps import get_next_teg_and_check_if_in_progress_fast

    _, next_teg, _ = get_next_teg_and_check_if_in_progress_fast()
    return next_teg


def get_teg_roster_form(teg_num: int) -> dict:
    """Build the roster + handicap form for a TEG.

    Prefers, in order: an existing handicaps.csv row for this TEG (already
    confirmed), then the calculated draft (``get_hc``), then blank/not-playing
    for anyone in neither.

    Returns ``{teg_num, source, players}`` where ``source`` is one of
    ``'confirmed' | 'calculated' | 'blank'`` (whole-row summary) and
    ``players`` is a list of ``{code, name, playing, handicap, source}``.
    """
    from teg_analysis.core.data_loader import get_player_name
    from teg_analysis.analysis.handicaps import get_hc

    raw = _read_handicaps_raw()
    players = get_roster_players()
    teg_str = f"TEG {teg_num}"

    existing = raw[raw["TEG"] == teg_str]
    confirmed = not existing.empty

    calculated = {}
    if not confirmed:
        try:
            calc_df = get_hc(teg_num)
            calculated = dict(zip(calc_df["Pl"], calc_df["hc"]))
        except Exception:
            calculated = {}  # not enough history to calculate (e.g. brand-new player)

    rows = []
    for p in players:
        if confirmed:
            raw_val = existing.iloc[0][p]
            hc = None if pd.isna(raw_val) else int(raw_val)
            playing = bool(hc)
            source = "confirmed"
        elif p in calculated:
            hc = int(calculated[p])
            playing = True
            source = "calculated"
        else:
            hc = None
            playing = False
            source = "blank"
        rows.append(
            {
                "code": p,
                "name": get_player_name(p),
                "playing": playing,
                "handicap": hc,
                "source": source,
            }
        )

    return {
        "teg_num": teg_num,
        "source": "confirmed" if confirmed else ("calculated" if calculated else "blank"),
        "players": rows,
    }


def save_teg_roster(teg_num: int, players: list[dict]) -> dict:
    """Upsert the one handicaps.csv row for ``teg_num``.

    Args:
        teg_num: which TEG.
        players: list of ``{code, playing, handicap}`` dicts (or matching
            keys 'Code'/'Playing'/'Handicap'). A not-playing player is
            written as 0, matching the existing convention in the data.

    Returns:
        ``{teg_num, players_saved}``.
    """
    from teg_analysis.io import write_file

    raw = _read_handicaps_raw()
    teg_str = f"TEG {teg_num}"

    row = {"TEG": teg_str}
    for p in players:
        code = p.get("code", p.get("Code"))
        playing = p.get("playing", p.get("Playing"))
        hc = p.get("handicap", p.get("Handicap"))
        row[code] = int(hc) if playing and hc not in (None, "") else 0

    existing_mask = raw["TEG"] == teg_str
    if existing_mask.any():
        idx = raw.index[existing_mask][0]
        for col, val in row.items():
            raw.loc[idx, col] = val
    else:
        raw = pd.concat([raw, pd.DataFrame([row])], ignore_index=True)

    write_file(HANDICAPS_CSV, raw, f"Set roster/handicaps for TEG {teg_num}")
    return {"teg_num": teg_num, "players_saved": len(players)}
