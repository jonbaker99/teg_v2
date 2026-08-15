"""Guards on the shared prompt blocks.

These exist because of a specific failure. Between 2026-08-11 and 2026-08-14 three
sessions reworked the report voice (`ef67417` Herron, `ac55be8` the four humour
mechanisms, `342db93` dropping the Peck device). All three edited
`authoring.WRITER_VOICE` and nothing else, because that is where the voice
experiments were run.

The voice existed in FOUR places. The other three — both editor prompts and the
round writer — went on describing a Ronay/Peck register that had been tested and
replaced, still naming Peck, whose device had been deliberately removed. Nothing
linked the copies and nothing tested them, so it surfaced only when Jon read the
editor prompt and asked why the work hadn't landed.

`prompts.py` makes the copies one copy. These tests make re-inlining a test
failure rather than a four-day silence.
"""
import pytest

from teg_analysis.reporting import authoring, prompts, round_report, story_plan
from teg_analysis.reporting.authoring import WRITER_SYSTEM, WRITER_VOICE
from teg_analysis.reporting.round_report import ROUND_PLAN_SYSTEM, ROUND_WRITER_SYSTEM
from teg_analysis.reporting.story_plan import SYSTEM_PROMPT as TOURNAMENT_PLAN_SYSTEM

# Changing this list is a real voice decision — it should show up in a diff.
VOICE_WRITERS = prompts.VOICE_WRITERS

# Surnames that identify a voice reference in a prompt, current or historical.
# `Peck` is here so a resurrected copy is caught by the sweep below.
_VOICE_SURNAMES = ("Herron", "Ronay", "Armstrong", "Iannucci", "Peck")


def _named_prompt_constants():
    """Every module-level prompt string in the reporting package.

    Deliberately discovered rather than listed. The named-constant version of
    this test passed while `TIGHTEN_SYSTEM` — a fifth copy nobody had inventoried
    — went on naming Peck. An explicit list only guards what you remembered.
    """
    for mod in (authoring, round_report, story_plan):
        for attr, val in vars(mod).items():
            if isinstance(val, str) and attr.isupper() and len(val) > 200:
                yield f"{mod.__name__.rsplit('.', 1)[-1]}.{attr}", val


ALL_PROMPT_CONSTANTS = dict(_named_prompt_constants())

WRITER_PROMPTS = {
    "tournament writer": WRITER_SYSTEM,
    "round writer": ROUND_WRITER_SYSTEM,
}
PLANNER_PROMPTS = {
    "tournament editor": TOURNAMENT_PLAN_SYSTEM,
    "round editor": ROUND_PLAN_SYSTEM,
}
ALL_PROMPTS = {**WRITER_PROMPTS, **PLANNER_PROMPTS}


@pytest.mark.parametrize("name", sorted(ALL_PROMPTS))
def test_every_prompt_names_the_current_voice(name):
    """All four prompts describe the same register — the drift that started this."""
    prompt = ALL_PROMPTS[name]
    for writer in VOICE_WRITERS:
        assert writer in prompt, f"{name} does not name {writer}"


@pytest.mark.parametrize("name", sorted(ALL_PROMPTS))
def test_no_prompt_still_names_the_dropped_peck_device(name):
    """`342db93` removed the mock-parliamentary device. Three prompts kept advertising it."""
    assert "Peck" not in ALL_PROMPTS[name], (
        f"{name} still names Tom Peck — that device was tested and dropped in 342db93"
    )


@pytest.mark.parametrize("name", sorted(WRITER_PROMPTS))
def test_both_writers_share_the_voice_block_verbatim(name):
    """Not 'both mention Herron' — literally the same string, so they cannot diverge."""
    assert prompts.VOICE_CORE in WRITER_PROMPTS[name]
    assert prompts.NAMED_PRINCIPLES in WRITER_PROMPTS[name]


@pytest.mark.parametrize("name", sorted(WRITER_PROMPTS))
def test_both_writers_share_the_faithfulness_rules_verbatim(name):
    """The rules that existed twice and were edited independently."""
    assert prompts.SHARED_FAITHFULNESS in WRITER_PROMPTS[name]
    assert prompts.STROKE_INDEX_RULE in WRITER_PROMPTS[name]


@pytest.mark.parametrize("name", sorted(PLANNER_PROMPTS))
def test_both_planners_share_the_house_voice_summary(name):
    assert prompts.HOUSE_VOICE_SUMMARY in PLANNER_PROMPTS[name]


def test_house_voice_summary_matches_the_voice_it_summarises():
    """The editors plan for a writer they never see. If the summary drifts from the
    real voice, the plans get aimed at a register the writer will not produce —
    which is exactly the state the tournament editor was in for four days."""
    for writer in VOICE_WRITERS:
        assert writer in prompts.VOICE_CORE, f"{writer} missing from VOICE_CORE"
        assert writer in prompts.HOUSE_VOICE_SUMMARY, f"{writer} missing from the summary"


@pytest.mark.parametrize("name", sorted(ALL_PROMPTS))
def test_shared_blocks_are_not_duplicated_within_a_prompt(name):
    """Catches a shared block being re-inlined alongside the import."""
    prompt = ALL_PROMPTS[name]
    for block_name in ("VOICE_CORE", "NAMED_PRINCIPLES", "SHARED_FAITHFULNESS",
                       "STROKE_INDEX_RULE", "HOUSE_VOICE_SUMMARY"):
        block = getattr(prompts, block_name)
        assert prompt.count(block) <= 1, f"{name} contains {block_name} more than once"


def test_voice_and_faithfulness_stay_separate_concerns():
    """A voice experiment must not be able to edit a guardrail by accident."""
    assert "FAITHFULNESS" not in prompts.VOICE_CORE
    assert "Never invent" not in prompts.VOICE_CORE
    assert "HUMOUR MECHANISMS" not in prompts.SHARED_FAITHFULNESS


@pytest.mark.parametrize("name", sorted(ALL_PROMPT_CONSTANTS))
def test_no_prompt_anywhere_describes_a_stale_voice(name):
    """Swept over every prompt constant, not a list someone maintains by hand.

    Any prompt that mentions the voice at all must describe the CURRENT one. This
    is the test that catches the next `TIGHTEN_SYSTEM`.
    """
    prompt = ALL_PROMPT_CONSTANTS[name]
    if not any(surname in prompt for surname in _VOICE_SURNAMES):
        pytest.skip(f"{name} does not reference the voice")
    assert "Peck" not in prompt, f"{name} names Tom Peck, dropped in 342db93"
    for writer in VOICE_WRITERS:
        surname = writer.rsplit(" ", 1)[-1]
        assert surname in prompt, f"{name} references the voice but omits {writer}"


def test_the_sweep_actually_sees_the_known_prompts():
    """Guards the guard: if discovery silently returned nothing, every sweep test
    above would skip and prove nothing."""
    found = set(ALL_PROMPT_CONSTANTS)
    for expected in ("authoring.WRITER_SYSTEM", "authoring.TIGHTEN_SYSTEM",
                     "round_report.ROUND_WRITER_SYSTEM", "round_report.ROUND_PLAN_SYSTEM",
                     "story_plan.SYSTEM_PROMPT"):
        assert expected in found, f"prompt discovery missed {expected}"


# ---------------------------------------------------------------------------
# Em-dash ban + sentence discipline (Jon, 2026-08-15): long constructions were
# the main readability complaint. The rule is only credible if the prompt does
# not demonstrate the thing it bans, which is what killed the old 25-word cap.
# ---------------------------------------------------------------------------
STYLE_SETTING_BLOCKS = {
    "prompts.VOICE_CORE": prompts.VOICE_CORE,
    "prompts.NAMED_PRINCIPLES": prompts.NAMED_PRINCIPLES,
    "authoring._WRITER_AIM": authoring._WRITER_AIM,
    "authoring._WRITER_ECONOMY": authoring._WRITER_ECONOMY,
}


@pytest.mark.parametrize("name", sorted(STYLE_SETTING_BLOCKS))
def test_style_setting_blocks_contain_no_em_dashes(name):
    """The blocks that teach register must not model the punctuation they ban.

    Scoped deliberately to the style-setting blocks. The structural and
    faithfulness blocks are procedural lists rather than prose the model imitates,
    and still contain em-dashes; see STATUS.md for that call.
    """
    assert "—" not in STYLE_SETTING_BLOCKS[name], (
        f"{name} uses an em-dash while instructing the writer never to"
    )


@pytest.mark.parametrize("name", sorted(WRITER_PROMPTS))
def test_both_writers_are_told_to_ban_em_dashes(name):
    assert "NO EM-DASHES" in WRITER_PROMPTS[name]


def test_the_worked_example_obeys_its_own_rules():
    """The FLAT/ELEVATED pair is the clearest picture of the target the model gets.

    The old ELEVATED example was a single 40-word sentence sitting above a rule
    capping sentences at 25 words. The exemplar wins that argument every time, so
    the cap was dead on arrival. It now demonstrates the rule instead.
    """
    import re
    m = re.search(r'ELEVATED \(right\): "(.*?)"', WRITER_VOICE, re.S)
    assert m, "the ELEVATED exemplar has gone missing"
    example = re.sub(r"\s+", " ", m.group(1))
    assert "—" not in example, "the exemplar uses a banned em-dash"
    sentences = [s for s in re.split(r"(?<=[.!?]) ", example) if s.strip()]
    longest = max(len(s.split()) for s in sentences)
    assert longest <= 25, f"exemplar has a {longest}-word sentence; the rule caps at 25"


def test_the_sentence_length_rule_is_not_contradicted():
    """`ECONOMY` used to license exactly what `CRAFT` capped."""
    assert "earn their length stay long" not in WRITER_VOICE
    assert "no exception for a long" in WRITER_VOICE


def test_comic_density_is_specified_not_left_to_taste():
    """"Be funny" is not an instruction. The dial-up trial settled on 5-7."""
    assert "COMIC DENSITY" in prompts.VOICE_CORE
    assert "five to seven" in prompts.VOICE_CORE


def test_em_dash_check_is_wired_into_verification():
    """A prompt rule alone was never going to hold; D3 runs after every generation."""
    from teg_analysis.reporting import verify
    assert verify.check_no_em_dashes in verify.CHECKS


@pytest.mark.parametrize("rule", [
    "countback",
    "drew level",
    "DIFFERENT hole",
    "not paradox",
    "Arithmetic must be exact",
    "trophy_metric",
])
def test_shared_faithfulness_carries_every_rule_that_was_duplicated(rule):
    """Each of these previously existed in two files, edited independently."""
    assert rule in prompts.SHARED_FAITHFULNESS, rule
