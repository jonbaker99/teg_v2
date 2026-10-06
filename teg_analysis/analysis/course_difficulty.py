"""How hard a course plays for TEG golfers, from its official ratings.

`data/course_info.csv` carries the men's Course Rating and Slope Rating from
the tee TEG plays. Neither number means much to a reader on its own, so this
module turns them into an interpretation:

- **extra strokes**: the WHS course handicap of an 18-index golfer, minus 18.
  That is `18 * slope / 113 + (course rating - par) - 18`. Zero is an average
  course (slope 113, rating equal to par); +3 means a typical TEG golfer gets
  about three more strokes than on an average course, which is the honest
  "this course is harder" signal for mid-handicappers. It folds slope (how
  much harder for a bogey golfer) and rating vs par (how hard for scratch)
  into one figure.
- **band**: a rough verbal band on that figure (kind / standard / tough /
  brutal). Internal shorthand: the prompts tell writers and TEGBot to use it
  as a guide and describe difficulty in their own, varied words.
- **rank** (once there are enough courses to rank against): where it sits
  among the rated courses TEG had played by a given date, so a report on an
  old TEG never compares with courses played later.

No LLM, no I/O beyond reading the two CSVs.
"""

from __future__ import annotations

from typing import Iterable, Optional

import pandas as pd

from teg_analysis.io import read_file

COURSE_INFO_CSV = "data/course_info.csv"
STANDARD_SLOPE = 113
TYPICAL_INDEX = 18

MIN_POOL_FOR_RANK = 8

# Upper bounds on extra strokes for each band. Calibrated on the 28 courses on
# file (2026-10): Crowborough -2.2 to Camiral Stadium +6.8.
BANDS = ((-0.5, "kind"), (1.5, "standard"), (4.0, "tough"), (float("inf"), "brutal"))


def load_course_table() -> pd.DataFrame:
    """`course_info.csv` as a frame (empty on failure)."""
    try:
        return read_file(COURSE_INFO_CSV)
    except Exception:
        return pd.DataFrame(columns=["Course", "par", "course_rating", "slope_rating"])


def extra_strokes(course_rating, slope_rating, par) -> Optional[float]:
    """Strokes an 18-index golfer gets here beyond an average course's 18."""
    if any(pd.isna(v) for v in (course_rating, slope_rating, par)):
        return None
    return round(TYPICAL_INDEX * float(slope_rating) / STANDARD_SLOPE
                 + float(course_rating) - float(par) - TYPICAL_INDEX, 1)


def band(extra: Optional[float]) -> Optional[str]:
    if extra is None or pd.isna(extra):
        return None
    return next(label for upper, label in BANDS if extra <= upper)


def course_difficulty(course: str, table: Optional[pd.DataFrame] = None,
                      among: Optional[Iterable[str]] = None) -> Optional[dict]:
    """Interpretation for one course, or None when it has no ratings.

    `among`: the courses to rank against (default: every rated course). Pass
    the courses TEG had played by the date in question to stay leak-safe.
    Rank 1 is the hardest; ties share a rank. The rank is left out below
    `MIN_POOL_FOR_RANK` courses, where "the hardest TEG had played" is trivia.
    """
    table = load_course_table() if table is None else table
    t = table.assign(extra=[extra_strokes(r.course_rating, r.slope_rating, r.par)
                            for r in table.itertuples()])
    t = t[t["extra"].notna()]
    row = t[t["Course"] == course]
    if row.empty:
        return None
    x = float(row["extra"].iloc[0])
    pool = t if among is None else t[t["Course"].isin(set(among) | {course})]
    out = {"extra_strokes": x, "band": band(x)}
    if len(pool) >= MIN_POOL_FOR_RANK:
        out.update(rank_hardest=int((pool["extra"] > x).sum()) + 1,
                   rank_tied=int((pool["extra"] == x).sum()) > 1,
                   rated_courses=len(pool))
    return out


def courses_played_by(date, round_info: pd.DataFrame) -> list[str]:
    """Courses with a TEG round on or before `date` (a Timestamp)."""
    d = pd.to_datetime(round_info["Date"], format="%d/%m/%Y", errors="coerce")
    return sorted(set(round_info.loc[d <= date, "Course"]))
