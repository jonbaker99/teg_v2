"""'New round' setup wizard orchestration.

Setting up a brand-new TEG's first round means doing four things, in order:

    1. round metadata      (a round_info.csv row: Course, Date, ...)
    2. roster + handicaps  (a handicaps.csv row -- once per TEG, not per round)
    3. Par / SI            (round_pars.csv -- once per round)
    4. go live             (a live_rounds token -> the shareable link)

Each of those already has a purpose-built, tested save function elsewhere
(``teg_setup``, ``round_setup``, ``live_round``) and its own status probe. This
module is a thin orchestration layer on top of them: it computes *what's left
to do* for a given TEG+Round from those probes -- so the wizard holds no
session state and a half-finished setup resumes just by revisiting the URL --
and it adds the one net-new step that never had a home before: a purpose-built
round-metadata form that *derives* round_info's ``TEGRd``/``TEG``/``Area``/
``Year`` instead of making an admin hand-type them into the raw CSV grid.

    suggest_next_target()       landing default (next TEG, round 1)
    get_wizard_status()         per-step done flags + first-incomplete step
    get_round_metadata_form()   step 1: course dropdown + date, prefilled
    save_round_metadata()       step 1: upsert the derived round_info row
"""

import pandas as pd

from teg_analysis.constants import (
    ROUND_INFO_CSV, COURSE_PARS_CSV, ROUND_PARS_CSV, ALL_SCORES_PARQUET,
)

FUTURE_TEGS_CSV = "data/future_tegs.csv"

# Step order + human labels, single source of truth for the stepper UI.
STEP_KEYS = ["metadata", "roster", "parsi", "golive"]
STEP_LABELS = {
    "metadata": "Round details",
    "roster": "Players & handicaps",
    "parsi": "Par & stroke index",
    "golive": "Go live",
}


def _read_csv_or_empty(path: str, columns: list[str]) -> pd.DataFrame:
    from teg_analysis.io import read_file

    try:
        return read_file(path)
    except FileNotFoundError:
        return pd.DataFrame(columns=columns)


def suggest_next_target() -> dict:
    """Best guess at the TEG+Round the admin wants to set up.

    Next TEG (from the same handicap logic the read-only Handicaps page uses),
    round 1. Only a default for the landing form -- the admin can type any
    TEG/Round, and the resume list surfaces already-started setups directly.
    """
    try:
        from teg_analysis.analysis.teg_setup import get_next_teg

        teg = get_next_teg()
    except Exception:  # noqa: BLE001
        teg = 1
    return {"teg_num": int(teg), "round_num": 1}


def get_course_options() -> list[str]:
    """Course names to offer in the metadata dropdown, from course_pars.csv."""
    course_pars = _read_csv_or_empty(COURSE_PARS_CSV, ["Course"])
    if course_pars.empty or "Course" not in course_pars.columns:
        return []
    courses = (
        course_pars["Course"].dropna().astype(str).str.strip().replace("", pd.NA).dropna()
    )
    return sorted(courses.unique().tolist())


def _metadata_done(teg_num: int, round_num: int) -> tuple[bool, str | None]:
    round_info = _read_csv_or_empty(ROUND_INFO_CSV, ["TEGNum", "Round", "Course"])
    match = round_info[
        (round_info["TEGNum"] == teg_num) & (round_info["Round"] == round_num)
    ]
    if match.empty:
        return False, None
    return True, str(match.iloc[0]["Course"])


def _roster_done(teg_num: int) -> tuple[bool, int | None]:
    """Whether TEG ``teg_num`` has a confirmed handicaps.csv row, and how many
    players it lists as playing (a non-zero handicap cell)."""
    from teg_analysis.analysis.teg_setup import get_teg_roster_form

    try:
        form = get_teg_roster_form(teg_num)
    except Exception:  # noqa: BLE001
        return False, None
    if form["source"] != "confirmed":
        return False, None
    playing = sum(1 for p in form["players"] if p["playing"])
    return True, playing


def _parsi_done(teg_num: int, round_num: int) -> bool:
    round_pars = _read_csv_or_empty(ROUND_PARS_CSV, ["TEGNum", "Round"])
    if round_pars.empty:
        return False
    match = round_pars[
        (round_pars["TEGNum"] == teg_num) & (round_pars["Round"] == round_num)
    ]
    return not match.empty


def _already_played(teg_num: int, round_num: int) -> bool:
    """Whether TEG+Round already has scores recorded in all-scores.parquet.

    A played round's real Par/SI is already locked in, so there's nothing left
    for the wizard to set up -- same scoping as ``round_setup.get_rounds_status``.
    """
    from teg_analysis.io import read_file

    all_scores = read_file(ALL_SCORES_PARQUET)
    if all_scores.empty:
        return False
    match = all_scores[
        (all_scores["TEGNum"].astype(int) == teg_num)
        & (all_scores["Round"].astype(int) == round_num)
    ]
    return not match.empty


def _live_status(teg_num: int, round_num: int) -> dict | None:
    """The most recent live-round registry row for this TEG+Round, if any."""
    from teg_analysis.analysis.live_round import list_live_rounds

    try:
        rounds = list_live_rounds()
    except Exception:  # noqa: BLE001
        return None
    for r in rounds:  # list_live_rounds is already newest-first
        if int(r["TEGNum"]) == teg_num and int(r["Round"]) == round_num:
            return {"token": r["Token"], "status": r["Status"]}
    return None


def get_wizard_status(teg_num: int, round_num: int) -> dict:
    """Per-step completion for a TEG+Round, plus the first incomplete step.

    Returns::

        {
          teg_num, round_num,
          steps: [{key, label, done, locked, summary}, ...],  # STEP_KEYS order
          current,               # key of the first actionable incomplete step
          ready_to_go_live,      # metadata + roster + parsi all done
          live,                  # {token, status} | None
          already_played,        # True if scores already exist -- nothing to set up
        }

    ``locked`` marks a step whose prerequisite isn't met yet (Par/SI needs the
    round's metadata for its course; Go live needs all three) so the UI can
    show it greyed rather than lead the admin into a step that would error.

    If the round has already been played (scores in all-scores.parquet), the
    wizard has nothing left to do -- ``already_played`` is True and ``steps``
    is empty rather than walking the admin toward re-confirming Par/SI on a
    round that's already locked in.
    """
    if _already_played(teg_num, round_num):
        return {
            "teg_num": teg_num,
            "round_num": round_num,
            "steps": [],
            "current": "played",
            "ready_to_go_live": False,
            "live": None,
            "already_played": True,
        }

    meta_done, course = _metadata_done(teg_num, round_num)
    roster_done, playing = _roster_done(teg_num)
    parsi_done = _parsi_done(teg_num, round_num) if meta_done else False
    live = _live_status(teg_num, round_num)
    live_done = live is not None and live["status"] in ("active", "finalized")

    done = {
        "metadata": meta_done,
        "roster": roster_done,
        "parsi": parsi_done,
        "golive": live_done,
    }
    locked = {
        "metadata": False,
        "roster": False,
        "parsi": not meta_done,
        "golive": not (meta_done and roster_done and parsi_done),
    }
    summary = {
        "metadata": course if meta_done else None,
        "roster": (f"{playing} playing" if playing is not None else None) if roster_done else None,
        "parsi": "Confirmed" if parsi_done else None,
        "golive": (live["status"].capitalize() if live else None),
    }

    steps = [
        {
            "key": k,
            "label": STEP_LABELS[k],
            "done": done[k],
            "locked": locked[k],
            "summary": summary[k],
        }
        for k in STEP_KEYS
    ]

    # First incomplete step that isn't locked -- where "Continue" should land.
    current = next((k for k in STEP_KEYS if not done[k] and not locked[k]), "golive")

    return {
        "teg_num": teg_num,
        "round_num": round_num,
        "steps": steps,
        "current": current,
        "ready_to_go_live": meta_done and roster_done and parsi_done,
        "live": live,
        "already_played": False,
    }


def get_round_metadata_form(teg_num: int, round_num: int) -> dict:
    """Build the round-details form: course dropdown + date, prefilled.

    Prefills from an existing round_info.csv row if this round is already in
    the file (editing), else leaves Course/Date blank for a new round. Also
    returns the ``Area``/``Year`` that :func:`save_round_metadata` will derive,
    so the form can show the admin what will be recorded without asking them to
    type it.

    Returns ``{teg_num, round_num, courses, course, date, exists, area, year}``.
    """
    round_info = _read_csv_or_empty(
        ROUND_INFO_CSV, ["TEGNum", "Round", "Course", "Date", "Area", "Year"]
    )
    match = round_info[
        (round_info["TEGNum"] == teg_num) & (round_info["Round"] == round_num)
    ]
    exists = not match.empty

    area, year = _derive_area_year(round_info, teg_num, date=None)
    if exists:
        row = match.iloc[0]
        course = str(row["Course"])
        date = str(row["Date"])
        if "Area" in row and pd.notna(row["Area"]):
            area = str(row["Area"])
        if "Year" in row and pd.notna(row["Year"]):
            year = str(row["Year"])
    else:
        course, date = "", ""

    return {
        "teg_num": teg_num,
        "round_num": round_num,
        "courses": get_course_options(),
        "course": course,
        "date": date,
        "exists": exists,
        "area": area,
        "year": year,
    }


def _derive_area_year(round_info: pd.DataFrame, teg_num: int, date: str | None):
    """Area/Year for a TEG: inherit from the TEG's other rounds, else the
    planned future_tegs.csv entry, else (for Year) the date's year."""
    area, year = "", ""

    same_teg = round_info[round_info["TEGNum"] == teg_num]
    if not same_teg.empty:
        first = same_teg.iloc[0]
        if "Area" in first and pd.notna(first["Area"]):
            area = str(first["Area"])
        if "Year" in first and pd.notna(first["Year"]):
            year = str(first["Year"])

    if not area or not year:
        future = _read_csv_or_empty(FUTURE_TEGS_CSV, ["TEGNum", "Area", "Year"])
        fmatch = future[future["TEGNum"] == teg_num]
        if not fmatch.empty:
            frow = fmatch.iloc[0]
            if not area and "Area" in frow and pd.notna(frow["Area"]):
                area = str(frow["Area"])
            if not year and "Year" in frow and pd.notna(frow["Year"]):
                year = str(frow["Year"])

    if not year and date:
        # Dates are stored dd/mm/yyyy -- fall back to the trailing year.
        parts = str(date).split("/")
        if len(parts) == 3 and parts[-1].strip().isdigit():
            year = parts[-1].strip()

    return area, year


def save_round_metadata(teg_num: int, round_num: int, course: str, date: str) -> dict:
    """Upsert one round_info.csv row, deriving the non-obvious columns.

    ``TEGRd`` and ``TEG`` are derived from the TEG/Round numbers; ``Area`` and
    ``Year`` are inherited from the TEG's other rounds or future_tegs.csv (Year
    falling back to the date's trailing year). The admin only ever supplies
    Course and Date.

    Returns ``{teg_num, round_num, course, area, year}``.
    """
    from teg_analysis.io import write_file

    course = (course or "").strip()
    date = (date or "").strip()
    if not course:
        raise ValueError("A course is required.")
    if not date:
        raise ValueError("A date is required.")

    round_info = _read_csv_or_empty(
        ROUND_INFO_CSV, ["TEGNum", "Round", "Course", "Date", "TEGRd", "TEG", "Area", "Year"]
    )
    area, year = _derive_area_year(round_info, teg_num, date=date)

    row = {
        "TEGNum": teg_num,
        "Round": round_num,
        "Course": course,
        "Date": date,
        "TEGRd": f"TEG {teg_num}|{round_num}",
        "TEG": f"TEG {teg_num}",
        "Area": area,
        "Year": year,
    }

    # Drop any existing row for this TEG+Round, then append the fresh one.
    round_info = round_info[
        ~((round_info["TEGNum"] == teg_num) & (round_info["Round"] == round_num))
    ]
    new_row = pd.DataFrame([row]).reindex(columns=round_info.columns.tolist() or list(row.keys()))
    round_info = pd.concat([round_info, new_row], ignore_index=True)
    round_info["TEGNum"] = round_info["TEGNum"].astype(int)
    round_info["Round"] = round_info["Round"].astype(int)
    round_info = round_info.sort_values(["TEGNum", "Round"]).reset_index(drop=True)

    write_file(
        ROUND_INFO_CSV, round_info, f"Add round metadata for TEG {teg_num} Round {round_num}"
    )
    return {"teg_num": teg_num, "round_num": round_num, "course": course, "area": area, "year": year}
