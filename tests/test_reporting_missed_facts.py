"""WP6 — missed-fact detection (`reporting/missed_facts.py`).

Real TEG 18 data, hand-written report text: no LLM call, and no dependence on
the published report files (WP5 may repair those in place).
"""
from __future__ import annotations

import pytest

from teg_analysis.reporting.missed_facts import (
    Block,
    MustMention,
    _EQUAL,
    _name_patterns,
    check_missed_facts,
    covering_block,
    list_must_mention,
    split_blocks,
)

PLAYERS = ["Alex Baker", "David Mullin", "Gregg Williams", "John Patterson", "Jon Baker"]

# The sentence the published TEG 18 report actually carries: the number, the
# course, a personal best — and no record. Item 6's exact shape.
OMITS = (
    "## Gregg Williams recovers to take the TEG 18 Green Jacket\n\n"
    "From there he mostly held on. His 84 in round four was his best score on "
    "the Stadium Course, eight better than his previous best there."
)
MENTIONS = (
    "## Gregg Williams recovers to take the TEG 18 Green Jacket\n\n"
    "From there he mostly held on. His 84 in round four equalled the Stadium "
    "course record Mullin had set the day before."
)


def _equalled(findings):
    return [f for f in findings if "Gregg Williams equals" in f.detail]


# ---------------------------------------------------------------------------
# Acceptance: TEG 18 item 6
# ---------------------------------------------------------------------------
class TestTeg18Item6:
    def test_tournament_lists_the_equalled_record(self):
        facts = list_must_mention(18)
        eq = [f for f in facts if f.kind == "course_record_equalled"]
        assert [(f.player, f.round) for f in eq] == [("Gregg Williams", 4)]

    @pytest.mark.parametrize("round_num", [None, 4])
    def test_flags_when_omitted(self, round_num):
        findings = check_missed_facts(18, round_num=round_num, text=OMITS, claims=[])
        hits = _equalled(findings)
        assert len(hits) == 1
        assert hits[0].severity == "warning"
        assert hits[0].rule == "missed_fact"
        assert hits[0].source == "missed"

    @pytest.mark.parametrize("round_num", [None, 4])
    def test_passes_when_mentioned(self, round_num):
        findings = check_missed_facts(18, round_num=round_num, text=MENTIONS, claims=[])
        assert _equalled(findings) == []

    def test_round_report_only_lists_its_own_round(self):
        assert not [f for f in list_must_mention(18, round_num=3)
                    if f.kind == "course_record_equalled"]

    def test_lead_change_is_decisive_outright_moment(self):
        leads = {f.competition: (f.player, f.round, f.hole)
                 for f in list_must_mention(18) if f.kind == "lead_change"}
        assert leads["Green Jacket (Gross)"] == ("Gregg Williams", 3, 2)
        assert leads["Trophy (Stableford)"][0] == "Alex Baker"


# ---------------------------------------------------------------------------
# The matcher
# ---------------------------------------------------------------------------
def test_blocks_carry_section_heading_and_claim_players():
    text = "# Title\n\n## Williams wins\n\nHe shot 84.\n## Next\nOther text."
    claims = [{"quote": "He shot 84.", "player": "Gregg Williams", "players": None}]
    blocks = split_blocks(text, claims)
    body = next(b for b in blocks if b.text == "He shot 84.")
    assert body.heading == "Williams wins"
    assert body.claim_players == {"Gregg Williams"}
    assert any(b.text == "Other text." and b.heading == "Next" for b in blocks)


def test_shared_surname_needs_first_name():
    pats = _name_patterns("Jon Baker", PLAYERS)
    assert r"\bBaker\b" not in pats
    assert r"\bJon\b" in pats


def _fact(**kw):
    base = dict(kind="course_record_equalled", player="Gregg Williams", summary="s",
                numbers=[r"(?<![\d.])84(?![\d])"], keyword_sets=[[_EQUAL, r"record|\bMullin\b"]])
    base.update(kw)
    return MustMention(**base)


def test_number_alone_is_not_enough():
    b = Block(text="Williams shot 84, his best on the course.", heading="")
    assert covering_block(_fact(), [b], PLAYERS) is None


def test_equal_word_and_holder_name_covers():
    b = Block(text="Williams's 84 matched Mullin's from the day before.", heading="")
    assert covering_block(_fact(), [b], PLAYERS) is b


def test_pronoun_resolved_by_claim_player():
    b = Block(text="He equalled the record with 84.", heading="",
              claim_players={"Gregg Williams"})
    assert covering_block(_fact(), [b], PLAYERS) is b


def test_or_heading_entry_reads_the_section_heading():
    fact = _fact(numbers=[], keyword_sets=[[r"lead", ("or_heading", r"\bR3\b")]])
    b = Block(text="Williams took the lead at the 2nd.", heading="Williams in R3")
    assert covering_block(fact, [b], PLAYERS) is b
    assert covering_block(fact, [Block(text=b.text, heading="")], PLAYERS) is None


# ---------------------------------------------------------------------------
# Pipeline wiring: verify_report(missed=True) and the voice pass
# ---------------------------------------------------------------------------
def test_verify_report_runs_missed_facts_only_when_asked():
    from teg_analysis.reporting.verify import verify_report
    rules = lambda fs: [f.rule for f in fs]
    assert "missed_fact" not in rules(verify_report(18, text=OMITS, round_num=4))
    assert "missed_fact" in rules(verify_report(18, text=OMITS, round_num=4, missed=True))


def test_verify_report_surfaces_a_failed_missed_check_as_a_warning(monkeypatch):
    from teg_analysis.reporting import missed_facts
    from teg_analysis.reporting.verify import verify_report

    def boom(*a, **k):
        raise RuntimeError("no data")
    monkeypatch.setattr(missed_facts, "check_missed_facts", boom)
    failed = [f for f in verify_report(18, text=OMITS, round_num=4, missed=True)
              if f.rule == "missed_fact_check_failed"]
    assert len(failed) == 1 and failed[0].severity == "warning"


def test_voice_pass_reports_missed_facts_even_when_inherited(monkeypatch, isolated_report_dir):
    """A fact the draft never carried is inherited by the voice pass, so it is
    not a NEW finding, but `restyle_voice` must still report it."""
    import os
    from unittest.mock import patch
    from teg_analysis.reporting import authoring, verify

    src_path = f"{isolated_report_dir}/teg_18_round_4_report_unittest_src.md"
    out_path = f"{isolated_report_dir}/teg_18_round_4_report_unittest_tmp.md"
    with open(src_path, "w") as f:
        f.write(OMITS)
    try:
        with patch.object(authoring.llm, "generate_text", return_value=(OMITS, {})):
            out = authoring.restyle_voice(18, "VOICE: x", "unittest_tmp", round_num=4,
                                          source_label="unittest_src", style=False)
        assert any("Gregg Williams equals" in m for m in out["missed_facts"])
        assert not any("missed_fact" in n for n in out["new_findings"])
    finally:
        for p in (src_path, out_path):
            if os.path.exists(p):
                os.remove(p)
