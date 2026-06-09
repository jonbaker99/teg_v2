"""Venue scene-setting context for a TEG.

Provides the colour a report needs around the course and location:
- a one-line course description (per round),
- whether TEG has been here before ("a new course for TEG" / "the Nth TEG round
  at this venue"),
- area-return context ("TEG's first visit to ..." / "TEG's Nth visit to ...").

Pure data assembly from round_info.csv + data/course_info.csv (the latter
relocated from the legacy streamlit course dictionary so teg_analysis stays
UI-agnostic). Visit counts are chronological and inclusive of the TEG in question.
"""

from __future__ import annotations

from typing import Optional
import pandas as pd

from teg_analysis.io import read_file
from teg_analysis.constants import ROUND_INFO_CSV
from teg_analysis.reporting.events import _ord

COURSE_INFO_CSV = "data/course_info.csv"


def _clean(v):
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return None
    return v


def _load_course_info() -> dict:
    try:
        df = read_file(COURSE_INFO_CSV)
    except Exception:
        return {}
    return {row["Course"]: {k: _clean(v) for k, v in row.items()}
            for _, row in df.iterrows()}


def build_venue_context(teg_num: int, round_info: Optional[pd.DataFrame] = None,
                        course_info: Optional[dict] = None) -> dict:
    """Return venue/location scene-setting for a TEG (per round + area level)."""
    if round_info is None:
        round_info = read_file(ROUND_INFO_CSV)
    ri = round_info.copy()
    ri["Date_parsed"] = pd.to_datetime(ri["Date"], format="%d/%m/%Y", errors="coerce")

    if course_info is None:
        course_info = _load_course_info()

    teg_rows = ri[ri["TEGNum"] == teg_num].sort_values("Round")
    if teg_rows.empty:
        raise ValueError(f"No round_info for TEG {teg_num}")

    area = teg_rows.iloc[0]["Area"]
    year = _safe_int(teg_rows.iloc[0]["Year"])
    teg_date = teg_rows["Date_parsed"].min()

    # area visit history: distinct TEGs in this area, chronological, inclusive
    area_first_dates = ri[ri["Area"] == area].groupby("TEGNum")["Date_parsed"].min()
    area_visit_n = int((area_first_dates <= teg_date).sum())
    if area_visit_n <= 1:
        area_visit = f"TEG's first visit to {area}"
    else:
        area_visit = f"TEG's {_ord(area_visit_n)} visit to {area}"

    rounds = []
    for _, r in teg_rows.iterrows():
        course = r["Course"]
        d = r["Date_parsed"]
        visit_n = int(((ri["Course"] == course) & (ri["Date_parsed"] <= d)).sum())
        visit_str = ("a new course for TEG" if visit_n <= 1
                     else f"the {_ord(visit_n)} TEG round at this venue")
        info = course_info.get(course, {})
        # Verified weekday so the writer doesn't have to derive it from the date string.
        # The writer prompt restricts weekday mentions to round openers; anywhere else
        # (callbacks, lookforwards) must use round numbers.
        weekday = d.strftime("%A") if pd.notna(d) else None
        rounds.append({
            "round": int(r["Round"]),
            "course": course,
            "date": r["Date"],
            "weekday": weekday,
            "visit_n": visit_n,
            "visit_str": visit_str,
            "full_name": info.get("full_name"),
            "location": info.get("location"),
            "type": info.get("type"),
            "designer": info.get("designer"),
            "description": info.get("description"),
        })

    return {
        "teg_num": teg_num,
        "area": area,
        "year": year,
        "area_visit": area_visit,
        "area_visit_n": area_visit_n,
        "n_rounds": len(rounds),
        "rounds": rounds,
    }


def _safe_int(x):
    try:
        if pd.isna(x):
            return None
        return int(x)
    except (TypeError, ValueError):
        return None


def render_venue_markdown(ctx: dict) -> str:
    lines = [f"# TEG {ctx['teg_num']} - Venue context",
             "",
             f"**Location:** {ctx['area']} ({ctx['year']}) - {ctx['area_visit']}",
             ""]
    for r in ctx["rounds"]:
        lines.append(f"### Round {r['round']}: {r['course']}  ({r['visit_str']})")
        if r["description"]:
            lines.append(f"- {r['description']}")
        meta = ", ".join(str(x) for x in [r.get("type"), r.get("designer"), r.get("location")] if x)
        if meta:
            lines.append(f"- _{meta}_")
        lines.append("")
    return "\n".join(lines)
