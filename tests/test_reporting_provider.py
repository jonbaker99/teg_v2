"""Tests for the API-vs-plan-usage provider switch, the mailbox hand-off and variants.

The point of the design is that the pipeline is identical under both providers, so
these tests exercise the seam rather than the pipeline: the switch resolves as
promised, a hand-off round-trips, structured output still validates without
`messages.parse`, and a variant cannot write outside its directory.

The mailbox is a blocking file protocol, so the round-trip tests run the call in a
worker thread and answer it from the test body — which is exactly what the
`teg-report-respond` skill does, minus the model.
"""
from __future__ import annotations

import json
import threading
from pathlib import Path

import pytest

pytestmark = [pytest.mark.unit]

import pydantic

from teg_analysis.reporting import llm, mailbox, paths


class Tiny(pydantic.BaseModel):
    """Small stand-in for StoryPlan: one required enum, one required string."""
    verdict: str
    vehicle: pydantic.constr(pattern="^(counterfactual|hero_arc)$")


@pytest.fixture(autouse=True)
def _isolated(tmp_path, monkeypatch):
    """Every path in the reporting package is cwd-relative, so isolate on cwd."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv(paths.ENV_VARIANT, raising=False)
    monkeypatch.delenv(llm.ENV_PROVIDER, raising=False)
    monkeypatch.delenv(mailbox.ENV_RESPONDER, raising=False)
    mailbox.reset_active_run()
    yield
    mailbox.reset_active_run()


@pytest.fixture
def plan_usage():
    """Most of these tests exercise the agent path; the default provider is api."""
    with llm.use_provider(llm.PROVIDER_AGENT):
        yield


def _answer_in_background(replies, timeout=10.0):
    """Answer pending mailbox requests, in order, with `replies`.

    Returns the thread and a list that fills with the request directories served,
    so a test can assert on how many attempts happened.
    """
    served: list = []

    def run():
        import time
        deadline = time.time() + timeout
        for reply in replies:
            while time.time() < deadline:
                d = mailbox.next_pending()
                if d is not None:
                    served.append(d)
                    mailbox.write_answer(d, reply)
                    break
                time.sleep(0.05)

    t = threading.Thread(target=run, daemon=True)
    t.start()
    return t, served


# ---------------------------------------------------------------------------
# The switch
# ---------------------------------------------------------------------------
def test_default_provider_is_the_api():
    """The default has to work with nobody present, which plan usage does not."""
    assert llm.get_provider() == llm.PROVIDER_API


def test_env_var_selects_plan_usage(monkeypatch):
    monkeypatch.setenv(llm.ENV_PROVIDER, "agent")
    assert llm.get_provider() == llm.PROVIDER_AGENT


def test_unknown_provider_raises(monkeypatch):
    monkeypatch.setenv(llm.ENV_PROVIDER, "openai")
    with pytest.raises(ValueError, match="not a provider"):
        llm.get_provider()


def test_use_provider_restores_previous(monkeypatch):
    monkeypatch.setenv(llm.ENV_PROVIDER, "agent")
    with llm.use_provider("api"):
        assert llm.get_provider() == "api"
    assert llm.get_provider() == "agent"


def test_api_provider_without_key_says_how_to_avoid_it(monkeypatch):
    """The error should point at the free path, not just complain about the key."""
    for var in ("ANTHROPIC_API_KEY", "TEG_ANTHROPIC_API_KEY"):
        monkeypatch.delenv(var, raising=False)
    with llm.use_provider("api"):
        with pytest.raises(RuntimeError, match="plan usage"):
            llm._client()


# ---------------------------------------------------------------------------
# The hand-off
# ---------------------------------------------------------------------------
def test_text_call_round_trips(plan_usage):
    t, served = _answer_in_background(["the finished prose"])
    text, usage = llm.generate_text("SYS", "USER", stage="report", label="teg14")
    t.join(timeout=5)
    assert text == "the finished prose"
    assert usage.provider == llm.PROVIDER_AGENT
    assert usage.input_tokens is None          # genuinely unknown, not zero
    assert "report" in str(served[0])


def test_request_file_is_self_contained(plan_usage):
    """It has to work as a paste into ChatGPT, not just as an agent's input."""
    t, _ = _answer_in_background(["ok"])
    llm.generate_text("THE-SYSTEM-PROMPT", "THE-USER-MESSAGE", stage="report",
                      label="teg14")
    t.join(timeout=5)
    request = next(Path("data/llm_mailbox").rglob("request.md")).read_text()
    assert "THE-SYSTEM-PROMPT" in request
    assert "THE-USER-MESSAGE" in request
    assert "response.md" in request            # tells the responder where to write


def test_structured_call_validates_without_messages_parse(plan_usage):
    reply = json.dumps({"verdict": "won it", "vehicle": "counterfactual"})
    t, _ = _answer_in_background([reply])
    obj, usage = llm.generate_structured("SYS", "USER", Tiny, stage="story_plan",
                                         label="teg14")
    t.join(timeout=5)
    assert isinstance(obj, Tiny)
    assert obj.vehicle == "counterfactual"
    assert usage.attempts == 1


def test_schema_travels_in_the_prompt(plan_usage):
    """A foreign model has no Pydantic — the enum vocabulary must be in the text."""
    reply = json.dumps({"verdict": "v", "vehicle": "hero_arc"})
    t, _ = _answer_in_background([reply])
    llm.generate_structured("SYS", "USER", Tiny, stage="story_plan", label="teg14")
    t.join(timeout=5)
    request = next(Path("data/llm_mailbox").rglob("request.md")).read_text()
    assert "OUTPUT SCHEMA" in request
    assert "counterfactual" in request         # the enum, not just the field name
    assert "response.json" in request


def test_fenced_json_is_accepted(plan_usage):
    """Chat models fence JSON by reflex; a retry round-trip for that is waste."""
    reply = "```json\n" + json.dumps({"verdict": "v", "vehicle": "hero_arc"}) + "\n```"
    t, _ = _answer_in_background([reply])
    obj, _ = llm.generate_structured("SYS", "USER", Tiny, stage="story_plan")
    t.join(timeout=5)
    assert obj.vehicle == "hero_arc"


def test_invalid_json_is_re_asked_with_the_error(plan_usage):
    """The API path has no retry at all; this is the one place the agent path wins."""
    bad = json.dumps({"verdict": "v", "vehicle": "decisive_moment"})   # wrong vocabulary
    good = json.dumps({"verdict": "v", "vehicle": "counterfactual"})
    t, served = _answer_in_background([bad, good])
    obj, usage = llm.generate_structured("SYS", "USER", Tiny, stage="story_plan")
    t.join(timeout=10)
    assert obj.vehicle == "counterfactual"
    assert usage.attempts == 2
    retry = (served[1] / "request.md").read_text()
    assert "Retry — attempt 2" in retry
    assert "decisive_moment" in retry          # shows what was rejected


def test_gives_up_after_max_attempts(plan_usage):
    bad = json.dumps({"verdict": "v", "vehicle": "nonsense"})
    t, _ = _answer_in_background([bad] * llm.MAX_STRUCTURED_ATTEMPTS)
    with pytest.raises(RuntimeError, match="no valid Tiny"):
        llm.generate_structured("SYS", "USER", Tiny, stage="story_plan")
    t.join(timeout=10)


def test_timeout_names_the_unanswered_request(monkeypatch, plan_usage):
    monkeypatch.setenv(mailbox.ENV_TIMEOUT, "1")
    with pytest.raises(mailbox.MailboxTimeout, match="request.md"):
        llm.generate_text("SYS", "USER", stage="report", label="teg14")


# ---------------------------------------------------------------------------
# Discovery — what the responder sees
# ---------------------------------------------------------------------------
def _request_in(run, stage="report", label="teg1"):
    directory = run.next_dir(stage, label)
    mailbox.write_request(directory, system="s", user="u", stage=stage,
                          label=label, expects="text")
    return directory


def test_a_finished_run_is_not_served():
    """A finished run must not leave requests that look pending forever."""
    run = mailbox.Run("stale-run").start()
    _request_in(run)
    assert len(mailbox.pending_requests()) == 1
    run.finish()
    assert mailbox.pending_requests() == []
    assert mailbox.current_run_dir() is None


# ---------------------------------------------------------------------------
# Two runs at once — plan usage in one window, a paste experiment in another
# ---------------------------------------------------------------------------
def test_two_live_runs_are_both_visible():
    """A second run must not hide the first, which a single global pointer did."""
    a = mailbox.Run("run-a").start()
    b = mailbox.Run("run-b").start()
    _request_in(a)
    _request_in(b)
    assert {p.name for p in mailbox.active_runs()} == {"run-a", "run-b"}


def test_ambiguity_is_an_error_not_a_guess():
    """Guessing would have one model answer another model's prompts."""
    mailbox.Run("run-a").start()
    mailbox.Run("run-b").start()
    with pytest.raises(mailbox.AmbiguousRun, match="--run"):
        mailbox.resolve_run()


def test_naming_a_run_resolves_the_ambiguity():
    mailbox.Run("run-a").start()
    mailbox.Run("run-b").start()
    assert mailbox.resolve_run("run-b").name == "run-b"


def test_a_paste_run_is_invisible_to_the_skill(monkeypatch):
    """The crossover hazard: Claude answering prompts meant for ChatGPT."""
    monkeypatch.setenv(mailbox.ENV_RESPONDER, mailbox.RESPONDER_MANUAL)
    manual = mailbox.Run("paste-run").start()
    _request_in(manual)
    monkeypatch.delenv(mailbox.ENV_RESPONDER)
    agent = mailbox.Run("skill-run").start()
    _request_in(agent)

    # What the skill sees, via `wait`/`next` — only its own run.
    assert mailbox.resolve_run(responder=mailbox.RESPONDER_AGENT).name == "skill-run"
    # And with only the paste run live, the skill sees nothing at all.
    agent.finish()
    assert mailbox.resolve_run(responder=mailbox.RESPONDER_AGENT) is None
    assert mailbox.resolve_run(responder=mailbox.RESPONDER_MANUAL).name == "paste-run"


def test_responder_defaults_to_agent_when_unrecorded(tmp_path):
    """Runs started before responders existed must still be servable."""
    run = mailbox.Run("legacy").start()
    (run.dir / mailbox.RUN_META_NAME).write_text(json.dumps({"pid": 1}))
    assert mailbox.run_responder(run.dir) == mailbox.RESPONDER_AGENT


def test_pending_is_scoped_to_one_run():
    a = mailbox.Run("run-a").start()
    b = mailbox.Run("run-b").start()
    _request_in(a, label="tegA")
    _request_in(b, label="tegB")
    assert len(mailbox.pending_requests(a.dir)) == 1
    assert "tegA" in str(mailbox.pending_requests(a.dir)[0])
    assert "tegB" in str(mailbox.pending_requests(b.dir)[0])


def test_a_dead_run_is_detected():
    """A crashed pipeline must not leave a responder waiting 15 minutes on nothing."""
    run = mailbox.Run("dead-run").start()
    assert mailbox.run_is_alive(run.dir)
    meta = run.dir / mailbox.RUN_META_NAME
    meta.write_text(json.dumps({"pid": 999_999}))     # a PID that cannot exist
    assert not mailbox.run_is_alive(run.dir)


def test_a_run_with_no_pid_is_assumed_alive():
    """Missing evidence of life is not evidence of death — never abandon a live run."""
    run = mailbox.Run("no-meta").start()
    (run.dir / mailbox.RUN_META_NAME).unlink()
    assert mailbox.run_is_alive(run.dir)


def test_meta_tells_the_responder_the_format():
    run = mailbox.Run("r").start()
    directory = run.next_dir("story_plan", "teg14")
    mailbox.write_request(directory, system="s", user="u", stage="story_plan",
                          label="teg14", expects="json", schema={"title": "Tiny"})
    meta = mailbox.read_meta(directory)
    assert meta["expects"] == "json"
    assert meta["response_file"] == "response.json"
    assert meta["schema_name"] == "Tiny"


# ---------------------------------------------------------------------------
# Variants
# ---------------------------------------------------------------------------
def test_canonical_by_default():
    assert paths.output_dir(create=False) == "data/commentary"


def test_variant_redirects_output(monkeypatch):
    monkeypatch.setenv(paths.ENV_VARIANT, "gpt5")
    assert paths.output_dir(create=False) == "data/commentary/variants/gpt5"


@pytest.mark.parametrize("bad", ["../escape", "a/b", "", " ", "with space", "-lead"])
def test_bad_variant_names_are_rejected(monkeypatch, bad):
    """The variant name comes from an env var and becomes a path. Never sanitise
    silently — a typo that wrote somewhere unexpected is worse than a crash."""
    monkeypatch.setenv(paths.ENV_VARIANT, bad)
    if bad.strip() == "":
        assert paths.get_variant() is None      # blank means canonical
    else:
        with pytest.raises(ValueError):
            paths.get_variant()


def test_promote_copies_variant_into_canonical(monkeypatch):
    monkeypatch.setenv(paths.ENV_VARIANT, "gemini")
    out = Path(paths.output_dir())
    (out / "teg_14_report_final.md").write_text("gemini's version")
    (out / "teg_14_report_styled.md").write_text("styled")

    monkeypatch.delenv(paths.ENV_VARIANT)
    written = paths.promote_variant("gemini", 14)
    assert Path("data/commentary/teg_14_report_final.md").read_text() == "gemini's version"
    assert len(written) == 2


def test_promote_refuses_when_there_is_nothing_to_promote():
    Path("data/commentary/variants/empty").mkdir(parents=True)
    with pytest.raises(FileNotFoundError, match="no artefacts"):
        paths.promote_variant("empty", 14)


def test_manifest_records_what_produced_a_variant(monkeypatch):
    monkeypatch.setenv(paths.ENV_VARIANT, "gpt5")
    paths.write_manifest({"provider": "agent", "tegs": [14]})
    paths.write_manifest({"provider": "agent", "tegs": [15]})
    entries = paths.read_manifest("gpt5")
    assert len(entries) == 2
    assert entries[0]["provider"] == "agent"
    assert "at" in entries[0]


def test_manifest_is_a_noop_for_the_canonical_set():
    assert paths.write_manifest({"provider": "api"}) is None


# ---------------------------------------------------------------------------
# CLI argument parsing
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("spec,expected", [
    ("14", [14]),
    ("2-5", [2, 3, 4, 5]),
    ("8,9,14", [8, 9, 14]),
    ("2-4,9", [2, 3, 4, 9]),
    ("14,14", [14]),
    (" 8 , 9 ", [8, 9]),
])
def test_teg_spec_parsing(spec, expected):
    from teg_analysis.reporting.backfill import parse_teg_spec
    assert parse_teg_spec(spec) == expected


def test_empty_teg_spec_raises():
    from teg_analysis.reporting.backfill import parse_teg_spec
    with pytest.raises(ValueError):
        parse_teg_spec(",")
