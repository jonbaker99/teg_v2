"""Course colour files (`data/courses/*.json`) and how notes reach a report.

The files are hand-researched and fact-checked reports depend on them, so the
data tests guard the shape that keeps them checkable: a source on every fact,
hole notes on real holes, and any par a hole note states matching
`course_pars.csv`. The resolver tests guard the rules that keep colour from
reading like a brochure (see `teg_analysis/reporting/course_colour.py`).
"""
import json
import re
import sys
from pathlib import Path

import pandas as pd
import pytest

from teg_analysis.reporting import course_colour as cc
from teg_analysis.reporting import prompts, round_storyline, story_plan

ROOT = Path(__file__).resolve().parents[1]
COURSES = ROOT / "data" / "courses"
LIST_SECTIONS = cc.LIST_SECTIONS
PARS = {(r.Course, int(r.Hole)): int(r.Par)
        for r in pd.read_csv(ROOT / "data" / "course_pars.csv").itertuples()}
COURSE_KEYS = list(pd.read_csv(ROOT / "data" / "course_info.csv")["Course"])
FILES = sorted(COURSES.glob("*.json"))
_PAR_RE = re.compile(r"\bpar[- ](3|4|5|three|four|five)\b", re.I)
_WORDS = {"three": 3, "four": 4, "five": 5}


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# The data
# ---------------------------------------------------------------------------
def test_every_course_has_a_colour_file():
    missing = [c for c in COURSE_KEYS if not (COURSES / f"{cc.course_slug(c)}.json").exists()]
    assert not missing, f"no colour file for: {missing}"


def test_every_file_belongs_to_a_course():
    slugs = {cc.course_slug(c) for c in COURSE_KEYS}
    assert {p.stem for p in FILES} <= slugs


@pytest.mark.parametrize("path", FILES, ids=lambda p: p.stem)
def test_file_shape_and_sources(path):
    d = _load(path)
    assert cc.course_slug(d["course"]) == path.stem
    assert {"course", "full_name", "researched", "holes", *LIST_SECTIONS} <= set(d)
    entries = [e for s in LIST_SECTIONS for e in d[s]] + [e for es in d["holes"].values() for e in es]
    assert entries, "empty colour file"
    for e in entries:
        assert set(e) == {"text", "source"}, e
        assert e["text"].strip()
        assert e["source"].startswith("http"), e


@pytest.mark.parametrize("path", FILES, ids=lambda p: p.stem)
def test_hole_notes_agree_with_course_pars(path):
    d = _load(path)
    for hole, entries in d["holes"].items():
        key = (d["course"], int(hole))
        assert key in PARS, f"hole {hole} is not a hole of {d['course']}"
        for e in entries:
            said = {_WORDS.get(m.lower()) or int(m) for m in _PAR_RE.findall(e["text"])}
            if len(said) == 1:
                assert said == {PARS[key]}, f"h{hole}: {e['text']!r} vs par {PARS[key]}"


def test_slug_handles_punctuation_and_accents():
    assert cc.course_slug("Prince's - Dunes / Himalayas") == "princes_dunes_himalayas"
    assert cc.course_slug("Royal Óbidos") == "royal_obidos"
    assert cc.course_slug("Praia D'El Rey") == "praia_del_rey"


# ---------------------------------------------------------------------------
# Resolution rules
# ---------------------------------------------------------------------------
COLOUR = {"Monte Rei": {"full_name": "Monte Rei", "notes": cc.colour_notes("Monte Rei", {
    "summary": [{"text": "S1", "source": "http://x"}],
    "trivia": [{"text": "T1", "source": "http://x"}, {"text": "T2", "source": "http://x"}],
    "holes": {"13": [{"text": "H13", "source": "http://x"}],
              "18": [{"text": "H18", "source": "http://x"}]},
})}}
INDEX = cc.note_index(COLOUR)
AT_13 = [{"id": "b1", "course": "Monte Rei", "holes": [{"hole": 13}]}]


def test_note_ids_are_stable_and_readable():
    assert set(INDEX) == {"monte_rei/summary/1", "monte_rei/trivia/1", "monte_rei/trivia/2",
                          "monte_rei/h13/1", "monte_rei/h18/1"}


def test_hole_note_needs_a_beat_on_that_hole():
    got = cc.resolve_for_storyline(["monte_rei/h18/1", "monte_rei/h13/1"], AT_13, INDEX)
    assert got == [{"course": "Monte Rei", "text": "H13", "hole": 13}]


def test_hole_note_needs_the_same_course():
    elsewhere = [{"id": "b1", "course": "Boavista", "holes": [{"hole": 13}]}]
    assert cc.resolve_for_storyline(["monte_rei/h13/1"], elsewhere, INDEX) == []


def test_cap_unknown_ids_and_reuse():
    used = set()
    first = cc.resolve_for_storyline(["bogus", "monte_rei/trivia/1", "monte_rei/trivia/2",
                                      "monte_rei/summary/1"], [], INDEX, used)
    assert [n["text"] for n in first] == ["T1", "T2"]
    second = cc.resolve_for_storyline(["monte_rei/trivia/1", "monte_rei/summary/1"], [], INDEX, used)
    assert [n["text"] for n in second] == ["S1"]


def test_consistency_warnings_name_each_problem():
    beats = [{"id": "b1", "course": "Monte Rei", "holes": [{"hole": 13}]}]
    storylines = [
        ("a", {"beat_ids": ["b1"], "colour_note_ids": ["monte_rei/h13/1", "monte_rei/h18/1"]}),
        ("b", {"beat_ids": [], "colour_note_ids": ["monte_rei/h13/1", "x", "monte_rei/trivia/1"]}),
    ]
    w = "\n".join(cc.check_colour_selection(storylines, beats, COLOUR))
    assert "h18/1' dropped: hole note with no beat" in w
    assert "h13/1' dropped: already used" in w
    assert "'x' dropped: unknown id" in w
    assert "b picks 3 colour notes" in w


def test_missing_file_gives_no_colour():
    assert cc.build_course_colour(["No Such Course"]) == {}


# ---------------------------------------------------------------------------
# Prompt wiring: editors get the selection rule, draft writers the usage rule
# ---------------------------------------------------------------------------
def test_editors_carry_the_plan_rule():
    assert prompts.COURSE_COLOUR_PLAN_RULE in story_plan.STORYLINE_SYSTEM_PROMPT
    assert prompts.COURSE_COLOUR_PLAN_RULE in round_storyline.round_storyline_system(False)
    assert prompts.COURSE_COLOUR_PLAN_RULE in round_storyline.round_storyline_system(True)


def test_draft_writers_carry_the_writer_rule():
    sys.path.insert(0, str(ROOT / "scripts"))
    import storyline_full_report_experiment as full
    assert prompts.COURSE_COLOUR_WRITER_RULE in full.DRAFT_WRITER_SYSTEM
    assert prompts.COURSE_COLOUR_WRITER_RULE in round_storyline.round_draft_writer_system(False)
    assert prompts.COURSE_COLOUR_WRITER_RULE in round_storyline.round_draft_writer_system(True)


def test_colour_rules_are_not_in_each_others_prompts():
    assert prompts.COURSE_COLOUR_WRITER_RULE not in story_plan.STORYLINE_SYSTEM_PROMPT
    assert prompts.COURSE_COLOUR_PLAN_RULE not in round_storyline.round_draft_writer_system(False)


def test_malformed_file_gives_no_colour_not_a_crash(monkeypatch):
    monkeypatch.setattr(cc, "load_course_colour",
                        lambda c: {"full_name": "X", "holes": {"13a": [{"text": "t", "source": "http://x"}]}})
    assert cc.build_course_colour(["Monte Rei"]) == {}


def test_band_words_are_a_guide_not_the_vocabulary():
    """Writers must describe difficulty in their own words, not the band labels."""
    assert "Never describe a" in prompts.COURSE_COLOUR_WRITER_RULE
    assert "kind / standard / tough / brutal" in prompts.COURSE_COLOUR_WRITER_RULE
    assert "not vocabulary for the report" in prompts.COURSE_COLOUR_PLAN_RULE
