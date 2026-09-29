"""TEG-level roster + handicap setup, ahead of a TEG being played.

Not every player plays every TEG. Two files hold that:

* ``handicaps.csv`` (wide: one row per TEG, one column per player) holds each
  player's handicap for the TEG. A player who sits a TEG out still keeps a
  handicap for it (their calculated one unless one is given): the handicap
  calculation counts a missed TEG as that TEG's handicap ("36-point rule"), so
  a 0 or blank there would break the next TEG's calculation. A blank cell only
  means nothing could be calculated. Never written as 0.
* ``teg_rosters.csv`` (``TEGNum,Pl,Playing``) says who is actually playing.
  TEGs with no rows there fall back to the legacy convention
  (``playing = bool(handicap)``, i.e. 0/blank = not playing).

    teg_rosters.csv rows for this TEG / handicaps.csv row (if confirmed)
        -> get_teg_roster_form()  else fall back to the calculated draft
                                   (teg_analysis.analysis.handicaps.get_hc)
        -> save_teg_roster()      upsert this TEG's handicaps row and replace
                                   its teg_rosters.csv rows (one GitHub commit)
"""

import pandas as pd

from teg_analysis.constants import HANDICAPS_CSV

TEG_ROSTERS_CSV = "data/teg_rosters.csv"  # TEGNum,Pl,Playing


ROSTER_COLUMNS = ["TEGNum", "Pl", "Playing"]


def _read_handicaps_raw() -> pd.DataFrame:
    from teg_analysis.io import read_file

    return read_file(HANDICAPS_CSV)


def _read_rosters_raw() -> pd.DataFrame:
    """teg_rosters.csv, or an empty frame if missing/unreadable.

    The Railway volume won't have the file until it's synced, so callers treat
    "empty" as "use the legacy bool(handicap) convention".
    """
    from teg_analysis.io import read_file

    try:
        df = read_file(TEG_ROSTERS_CSV)
        if not {"TEGNum", "Pl", "Playing"} <= set(df.columns):
            raise ValueError("unexpected columns")
        df = df[ROSTER_COLUMNS].copy()
        df["Playing"] = df["Playing"].map(lambda v: str(v).strip().lower() == "true")
        return df
    except Exception:  # noqa: BLE001 - any failure -> legacy fallback
        return pd.DataFrame(columns=ROSTER_COLUMNS)


def get_roster_players() -> list[str]:
    """Every known player code, offerable on a TEG's roster.

    handicaps.csv column order first (stable for the existing players), then
    any player known to players.csv/PLAYER_DICT without a handicaps column yet
    (i.e. added via "Add a new player" but never rostered) -- save_teg_roster's
    upsert creates their column the first time they're saved onto a TEG.
    """
    from teg_analysis.core.players import get_player_dict

    raw = _read_handicaps_raw()
    from_handicaps = [c for c in raw.columns if c != "TEG"]
    known = get_player_dict()
    return from_handicaps + [c for c in known if c not in from_handicaps]


def get_next_teg() -> int:
    """The TEG that should default to the top of the setup page."""
    from teg_analysis.analysis.handicaps import get_next_teg_and_check_if_in_progress_fast

    _, next_teg, _ = get_next_teg_and_check_if_in_progress_fast()
    return next_teg


def get_teg_roster_form(teg_num: int) -> dict:
    """Build the roster + handicap form for a TEG.

    Prefers, in order: an existing handicaps.csv row for this TEG (already
    confirmed; who is playing comes from teg_rosters.csv if it has rows for
    this TEG, else the legacy ``bool(handicap)``), then the calculated draft (``get_hc``), then blank/not-playing
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

    rosters = _read_rosters_raw()
    this_roster = rosters[pd.to_numeric(rosters["TEGNum"], errors="coerce") == teg_num]
    roster_flags = dict(zip(this_roster["Pl"], this_roster["Playing"])) if not this_roster.empty else None

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
            # A player added after this TEG's row was saved has no column yet
            # -- treat exactly like a blank cell (not playing).
            raw_val = existing.iloc[0][p] if p in existing.columns else None
            hc = None if raw_val is None or pd.isna(raw_val) else int(raw_val)
            playing = bool(hc) if roster_flags is None else bool(roster_flags.get(p, False))
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
    """Upsert this TEG's handicaps.csv row and teg_rosters.csv rows.

    Args:
        teg_num: which TEG.
        players: list of ``{code, playing, handicap}`` dicts (or matching
            keys 'Code'/'Playing'/'Handicap').

    The handicap cell is the given handicap whenever one is given, playing or
    not. A non-player with none given gets their calculated ``get_hc`` value,
    or a blank if it can't be calculated -- never 0. Playing flags go to
    teg_rosters.csv (this TEG's rows replaced). On Railway both files land in
    one GitHub commit.

    Returns:
        ``{teg_num, players_saved}``.
    """
    from teg_analysis.io import write_file, batch_commit_to_github, _is_railway

    raw = _read_handicaps_raw()
    teg_str = f"TEG {teg_num}"

    calculated = None  # lazily computed, only if a non-player needs it

    def calc_for(code):
        nonlocal calculated
        if calculated is None:
            try:
                from teg_analysis.analysis.handicaps import get_hc

                df = get_hc(teg_num)
                calculated = dict(zip(df["Pl"], df["hc"]))
            except Exception:  # noqa: BLE001 - not enough history
                calculated = {}
        val = calculated.get(code)
        return None if val is None or pd.isna(val) else int(val)

    row = {"TEG": teg_str}
    flags = []
    for p in players:
        code = p.get("code", p.get("Code"))
        playing = bool(p.get("playing", p.get("Playing")))
        hc = p.get("handicap", p.get("Handicap"))
        if hc not in (None, "") and not pd.isna(hc):
            value = int(hc)
        elif not playing:
            value = calc_for(code)
        else:
            value = None
        row[code] = float("nan") if value is None else value
        flags.append({"TEGNum": teg_num, "Pl": code, "Playing": playing})

    existing_mask = raw["TEG"] == teg_str
    if existing_mask.any():
        idx = raw.index[existing_mask][0]
        for col, val in row.items():
            raw.loc[idx, col] = val
    else:
        raw = pd.concat([raw, pd.DataFrame([row])], ignore_index=True)

    rosters = _read_rosters_raw()
    rosters = rosters[pd.to_numeric(rosters["TEGNum"], errors="coerce") != teg_num]
    rosters = pd.concat([rosters, pd.DataFrame(flags, columns=ROSTER_COLUMNS)], ignore_index=True)
    rosters["TEGNum"] = rosters["TEGNum"].astype(int)
    rosters = rosters.sort_values("TEGNum", kind="stable").reset_index(drop=True)

    defer = bool(_is_railway())
    message = f"Set roster/handicaps for TEG {teg_num}"
    infos = [
        write_file(HANDICAPS_CSV, raw, message, defer_github=defer),
        write_file(TEG_ROSTERS_CSV, rosters, message, defer_github=defer),
    ]
    infos = [i for i in infos if i]
    if defer and infos:
        batch_commit_to_github(infos, message)
    return {"teg_num": teg_num, "players_saved": len(players)}
