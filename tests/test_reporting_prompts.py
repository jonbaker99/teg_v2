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
    "prompts.ELEVATION_DEVICE": prompts.ELEVATION_DEVICE,
    "authoring._WRITER_EDITORIAL": authoring._WRITER_EDITORIAL,
    "authoring._WRITER_COMIC_AIM": authoring._WRITER_COMIC_AIM,
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
    m = re.search(r'ELEVATED \(right\): "(.*?)"', WRITER_SYSTEM, re.S)
    assert m, "the ELEVATED exemplar has gone missing"
    example = re.sub(r"\s+", " ", m.group(1))
    assert "—" not in example, "the exemplar uses a banned em-dash"
    sentences = [s for s in re.split(r"(?<=[.!?]) ", example) if s.strip()]
    longest = max(len(s.split()) for s in sentences)
    assert longest <= 25, f"exemplar has a {longest}-word sentence; the rule caps at 25"


def test_the_sentence_length_rule_is_not_contradicted():
    """`ECONOMY` used to license exactly what `CRAFT` capped."""
    assert "earn their length stay long" not in WRITER_SYSTEM
    assert "no exception for a long" in WRITER_SYSTEM


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


# ---------------------------------------------------------------------------
# The occasion device reads win_anatomy. Its archetype table is prose, so a new
# enum value in the code would leave a branch silently unaddressed.
# ---------------------------------------------------------------------------
def test_every_win_anatomy_classification_has_an_archetype():
    """`ELEVATION_DEVICE` must cover every value `win_anatomy` can emit.

    The block tells the writer to read the frame off `attribution` and `shape`.
    If the detector gains a value and the block does not, the writer meets a
    classification with no instruction attached and improvises a frame, which
    is exactly the fabrication the data-driven approach exists to prevent.
    """
    import re
    from pathlib import Path

    src = Path("teg_analysis/reporting/win_anatomy.py").read_text()
    emitted = set()
    for field in ("attribution", "shape"):
        emitted |= set(re.findall(rf'{field} = "([a-z_]+)"', src))
        emitted |= set(re.findall(rf'{field} = "([a-z_]+)" if ', src))
    assert emitted, "found no classification literals — did win_anatomy.py move?"

    missing = [v for v in sorted(emitted)
               if f'"{v}"' not in prompts.ELEVATION_DEVICE]
    assert not missing, (
        f"win_anatomy can emit {missing} but ELEVATION_DEVICE names no archetype "
        "for it; the writer would meet that classification with no instruction")


def test_the_occasion_device_names_real_bundle_fields():
    """Guards the other direction: an archetype keyed off a renamed field."""
    from teg_analysis.reporting import authoring
    for field in ("attribution", "shape", "biggest_lead_blown",
                  "rival_could_have_flipped_it", "close_finish"):
        assert f"`{field}" in prompts.ELEVATION_DEVICE, field
    # And the data actually reaches the writer when the context block is sent.
    assert "win_anatomy" in authoring.BUNDLE_CONTEXT_KEYS
    assert "tournament_shape" in authoring.BUNDLE_CONTEXT_KEYS


def test_the_occasion_device_is_contract_not_voice():
    """It must survive a voice swap, or a plain register loses the opening."""
    from teg_analysis.reporting import authoring
    assert prompts.ELEVATION_DEVICE in authoring.WRITER_CONTRACT
    assert prompts.ELEVATION_DEVICE not in authoring.WRITER_VOICE
    assert prompts.ELEVATION_DEVICE in authoring.build_writer_system("VOICE: plain.")


def test_the_occasion_device_covers_both_axes_of_the_data():
    """The career axis must stay in step with what `history_context` emits.

    `notable_milestones` is the only licensed source for career framing, so an
    archetype keyed off a phrase the generator cannot produce is dead, and a
    milestone category with no archetype is material the writer will not use.
    Both are silent failures: the report simply comes out flatter.
    """
    from pathlib import Path

    src = Path("teg_analysis/reporting/history_context.py").read_text()

    # Each pair is (a phrase the milestone generator emits, a word the
    # archetype table must use to pick that milestone up).
    for emitted, archetype_cue in (
            ("runner-up in", "runner-up"),
            ("back-to-back", "back-to-back"),
            ("Wooden Spoon in", "Wooden Spoon in"),
            ("rank {_ordinal(rank)} in each of the last", "in each of the last"),
            ("reigning Wooden Spoon holder", "reigning Wooden Spoon holder"),
            ("defending Trophy champion", "defending champion"),
    ):
        assert emitted in src, f"history_context no longer emits {emitted!r}"
        assert archetype_cue in prompts.ELEVATION_DEVICE, (
            f"history_context emits {emitted!r} but ELEVATION_DEVICE has no "
            f"archetype cued by {archetype_cue!r}")

    assert "notable_milestones" in prompts.ELEVATION_DEVICE
    assert "last_4_positions" in prompts.ELEVATION_DEVICE


def test_the_occasion_device_demands_both_hammable_and_hammed():
    """Jon, 2026-08-17: "it needs to be both 'hammable' and 'hammed'."

    Two distinct failures. Framing material that cannot carry it (overstatement
    over nothing) and finding the angle then under-delivering it. The block
    states both as tests and shows the second with worked pairs, because
    "commit to it" is not an instruction a model can act on without one.
    """
    block = prompts.ELEVATION_DEVICE
    assert "HAMMABLE" in block and "HAMMED" in block
    # The hammable half must warn against manufacturing an angle, or it reads
    # as pure encouragement and every report opens with something strained.
    assert "manufacture" in block
    # The hammed half is diagnostic rather than exemplary: a specimen sentence
    # would demonstrate a register as well as a technique, and the register is
    # supplied by the voice, not by this block. See the test below.
    assert "You have under-hammed if" in block


def test_the_occasion_device_is_about_inflation_not_parallels():
    """Jon, 2026-08-17: "over-do the achievement, the drama, the defeat. not
    *necessarily* to draw parallels."

    The first version read the Bristow quote as the mechanism rather than as an
    illustration, and instructed "reach outside golf: history, myth, war,
    geology, statecraft". Every report then opened on a historical comparison.
    The move is overstating the SUBJECT. A comparison is one optional way to do
    that, neither the mechanism nor forbidden.
    """
    block = prompts.ELEVATION_DEVICE

    # The three things being inflated are named, each unpacked in bullets.
    for thing in ("The achievement.", "The drama.", "The defeat."):
        assert thing in block, thing
    assert "not a template" in block

    # Comparisons: permitted, not mandated, not the default.
    assert "allowed, never automatic" in block
    assert "default to inflating the thing in front of you" in block
    # Not forbidden either. Banning them outright was the over-correction.
    assert "perfectly good" in block

    # The instruction that produced the tic must not come back.
    assert "Reach outside golf. History, myth" not in block


def test_readability_rules_survive_a_voice_swap():
    """Jon, 2026-08-17: "we need the em dash and sentence length rules."

    They lived in VOICE_CORE and `_WRITER_ECONOMY`, both in the half a `voice=`
    swap REPLACES, so every style trial silently dropped them. They exist
    because Jon found the reports hard to read, and that verdict does not stop
    applying because the register changed.
    """
    from teg_analysis.reporting import authoring

    custom = authoring.build_writer_system("VOICE: whatever you like.")
    assert "NO EM-DASHES" in custom
    assert "Average around 15 words" in custom
    assert "Em-dashes are banned outright" in custom      # the ECONOMY restatement
    assert prompts.SENTENCE_DISCIPLINE in authoring.WRITER_CONTRACT
    assert prompts.SENTENCE_DISCIPLINE not in authoring.WRITER_VOICE
    # The round writer lost it from VOICE_CORE too and must carry it explicitly.
    from teg_analysis.reporting import round_report
    assert prompts.SENTENCE_DISCIPLINE in round_report.ROUND_WRITER_SYSTEM


def test_sentence_discipline_reconciles_styles_that_want_an_ornate_build():
    """Several house styles call for a long build. The rule must say how.

    Without this the block simply contradicts the style brief, and the model
    picks one at random. The resolution is that a build is made of several short
    sentences, which is what VOICE_CORE already said about the Ronay device.
    """
    assert "ACROSS SENTENCES" in prompts.SENTENCE_DISCIPLINE


def test_arc_scope_carries_no_editor_prose():
    """`arc` is the frame VOCABULARY, not a précis of the report.

    `opening_hook` is a draft of the opening and `theme` is a written
    through-line; shipping them to a voice experiment contaminates the thing
    being measured, which is the same reason `players[].arc` was never in `arc`.
    """
    from teg_analysis.reporting.authoring import ARC_PLAN_FIELDS
    for prose_field in ("title", "theme", "opening_hook", "foreshadow",
                        "payoffs", "why_the_champion_won"):
        assert prose_field not in ARC_PLAN_FIELDS, prose_field
    assert set(ARC_PLAN_FIELDS) == {"narrative_structure", "narrative_vehicles",
                                    "prominent_vehicle", "prominent_palette"}


def test_the_two_writer_entry_points_default_the_same_way():
    """One parameter, one default. Two was a trap."""
    import inspect
    from teg_analysis.reporting import authoring
    for fn in (authoring.report_around_draft, authoring.write_from_dry):
        assert inspect.signature(fn).parameters["plan_scope"].default == "full", fn.__name__


def test_the_occasion_device_shows_no_specimen_prose():
    """Jon, 2026-08-17: the worked examples were "far too style specific".

    A specimen sentence teaches a register as well as a technique, and the
    model copies both. In this pipeline the register arrives separately, as a
    `voice=` argument or a style brief, so any example here actively fights the
    thing the block is embedded in. The technique is taught as operations in
    bullets instead, and the block says out loud why there are no examples.

    The one quotation that remains is the Bristow line, which is confined to the
    comparisons warning and labelled there as an illustration of attitude rather
    than a template.
    """
    block = prompts.ELEVATION_DEVICE

    assert "there are none, deliberately" in block
    for exemplar_marker in ("STATED:", "HAMMED:", "STATED (wrong)", "HAMMED (right)"):
        assert exemplar_marker not in block, exemplar_marker

    # Bristow survives only inside the comparisons warning.
    assert block.count("Bristow") == 1
    warning = block[block.index("**COMPARISONS"):]
    assert "Bristow" in warning

    # Operations, not phrasings. The old version listed literal words to use
    # ("Never again, for the last time, permanently, henceforth").
    assert "They are operations, not" in block
    assert "henceforth" not in block
