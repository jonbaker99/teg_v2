"""Course colour: sourced setting, history, trivia and hole notes per course.

Each course has a hand-researched file at `data/courses/<slug>.json` (slug from
`course_slug`). Every entry is `{"text", "source"}`; sections are `summary`,
`setting`, `history`, `trivia`, `local` (lists) and `holes` (hole number ->
list). `data/course_info.csv` stays the flat one-line index.

How it reaches a report, so the colour reads as texture and not a brochure:

1. The editor (planner) sees every note for the TEG's courses, each with a
   stable id, in the bundle's `course_colour` key.
2. Each storyline picks at most `MAX_NOTES_PER_STORYLINE` ids in
   `DraftedStoryline.colour_note_ids` (zero is a normal answer).
3. `resolve_for_storyline` turns those ids into the notes the section writer
   sees, enforcing the rules in code: unknown ids dropped, a note used once
   per report, and a hole note only when one of the storyline's own beats
   happened on that hole of that course.

Pure data; no LLM. Missing files simply give no colour.
"""

from __future__ import annotations

import json
import re
import unicodedata
from typing import Iterable, Optional

from teg_analysis.io import read_text_file

COURSES_DIR = "data/courses"
LIST_SECTIONS = ("summary", "setting", "history", "trivia", "local")
MAX_NOTES_PER_STORYLINE = 2


def course_slug(course: str) -> str:
    """'Prince's - Dunes / Himalayas' -> 'princes_dunes_himalayas',
    'Royal Óbidos' -> 'royal_obidos'."""
    s = unicodedata.normalize("NFKD", course).encode("ascii", "ignore").decode().lower()
    s = re.sub(r"['’]", "", s)
    return re.sub(r"[^a-z0-9]+", "_", s).strip("_")


def course_colour_path(course: str) -> str:
    return f"{COURSES_DIR}/{course_slug(course)}.json"


def load_course_colour(course: str) -> Optional[dict]:
    """The raw colour file for a course, or None if there isn't one."""
    try:
        return json.loads(read_text_file(course_colour_path(course)))
    except Exception:
        return None


def colour_notes(course: str, colour: dict) -> list[dict]:
    """Flatten one course file into id'd notes, sources dropped (the writer
    never needs a URL; the file keeps it for fact-checking).

    Ids are stable while the file's order is: `monte_rei/setting/2`,
    `monte_rei/h13/1` (1-based).
    """
    slug = course_slug(course)
    notes = []
    for section in LIST_SECTIONS:
        for i, entry in enumerate(colour.get(section) or [], 1):
            notes.append({"id": f"{slug}/{section}/{i}", "section": section,
                          "text": entry["text"]})
    for hole, entries in sorted((colour.get("holes") or {}).items(), key=lambda kv: int(kv[0])):
        for i, entry in enumerate(entries, 1):
            notes.append({"id": f"{slug}/h{int(hole)}/{i}", "section": "hole",
                          "hole": int(hole), "text": entry["text"]})
    return notes


def build_course_colour(courses: Iterable[str]) -> dict:
    """Bundle key for the planner: `{course: {"full_name", "notes"}}`.
    Courses without a colour file are left out."""
    out = {}
    for course in dict.fromkeys(courses):       # de-dupe, keep round order
        colour = load_course_colour(course)
        if colour:
            out[course] = {"full_name": colour.get("full_name"),
                           "notes": colour_notes(course, colour)}
    return out


def note_index(course_colour: Optional[dict]) -> dict:
    """id -> note (with its `course`) across a bundle's `course_colour`."""
    return {n["id"]: {**n, "course": course}
            for course, c in (course_colour or {}).items() for n in c["notes"]}


def holes_played(evidence: list) -> set:
    """(course, hole) pairs that the storyline's own beats happened on."""
    return {(b.get("course"), h.get("hole")) for b in evidence
            for h in (b.get("holes") or []) if b.get("course")}


def _reject_reason(note_id: str, index: dict, played: set, used: set) -> Optional[str]:
    note = index.get(note_id)
    if note is None:
        return "unknown id"
    if note_id in used:
        return "already used by another storyline"
    if note["section"] == "hole" and (note["course"], note["hole"]) not in played:
        return "hole note with no beat on that hole"
    return None


def resolve_for_storyline(note_ids: list, evidence: list, index: dict,
                          used: Optional[set] = None) -> list[dict]:
    """The colour notes a section writer actually gets. Applies every rule in
    code; `used` (shared across a report's storylines) is updated in place."""
    used = used if used is not None else set()
    played = holes_played(evidence)
    out = []
    for nid in note_ids or []:
        if len(out) >= MAX_NOTES_PER_STORYLINE:
            break
        if _reject_reason(nid, index, played, used):
            continue
        used.add(nid)
        n = index[nid]
        note = {"course": n["course"], "text": n["text"]}
        if n["section"] == "hole":
            note["hole"] = n["hole"]
        out.append(note)
    return out


def check_colour_selection(storylines: list, beats: list, course_colour: Optional[dict]) -> list[str]:
    """Plan-consistency warnings for `colour_note_ids`. `storylines` is a list
    of (name, storyline) pairs in drafting order; storylines are objects or
    dicts with `colour_note_ids` and `beat_ids`."""
    index = note_index(course_colour)
    by_id = {b["id"]: b for b in beats}
    used: set = set()
    warnings = []
    for name, s in storylines:
        get = s.get if isinstance(s, dict) else lambda k, d=None: getattr(s, k, d)
        ids = get("colour_note_ids") or []
        if len(ids) > MAX_NOTES_PER_STORYLINE:
            warnings.append(f"{name} picks {len(ids)} colour notes "
                            f"(max {MAX_NOTES_PER_STORYLINE}); extras dropped")
        played = holes_played([by_id[b] for b in get("beat_ids") or [] if b in by_id])
        for nid in ids[:MAX_NOTES_PER_STORYLINE]:
            reason = _reject_reason(nid, index, played, used)
            if reason:
                warnings.append(f"{name} colour note {nid!r} dropped: {reason}")
            else:
                used.add(nid)
    return warnings
