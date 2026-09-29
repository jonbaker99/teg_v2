"""Phase tracking and status helpers in webapp/report_generation.py.

No real LLM or GitHub calls: the pipeline modules are replaced by fakes in
sys.modules and the status directory is redirected into tmp_path.
"""

import sys
import types
from datetime import datetime, timedelta, timezone

import pytest

from webapp import report_generation as rg

NOW = datetime(2026, 9, 29, 12, 0, tzinfo=timezone.utc)


def _iso(delta_seconds):
    return (NOW - timedelta(seconds=delta_seconds)).isoformat()


@pytest.fixture
def store(tmp_path, monkeypatch):
    monkeypatch.setattr(rg, "_store_path", lambda rel: tmp_path / rel)
    return tmp_path


@pytest.fixture
def pipeline(store, monkeypatch):
    """Fake run_one for both pipelines. `calls` records (start, stop, phase seen)."""
    calls = []
    fail_on = {"stage": None}

    def run_one(teg, *args, start_from="storylines", stop_after="voice", **kw):
        rnd = args[0] if args else None
        status = rg.read_status(teg, rnd)
        calls.append((start_from, stop_after, status["phase"], status["state"]))
        if fail_on["stage"] == start_from:
            raise RuntimeError("boom")

    for name in ("scripts.storyline_round_report_experiment",
                 "scripts.storyline_full_report_experiment"):
        mod = types.ModuleType(name)
        mod.run_one = run_one
        monkeypatch.setitem(sys.modules, name, mod)

    monkeypatch.setattr(rg.llm, "get_provider", lambda: "agent")
    monkeypatch.setattr(rg.llm, "has_api_key", lambda: True)
    monkeypatch.setattr(rg, "stage_artefacts_to_store",
                        lambda teg, rnd: rg.artefact_names(teg, rnd))
    monkeypatch.setattr(rg, "push_files",
                        lambda *a, **k: {"failed": [], "committed": True})
    import webapp.deps as deps
    monkeypatch.setattr(deps, "clear_all_data_caches", lambda: None)
    return types.SimpleNamespace(calls=calls, fail_on=fail_on)


def _states(status):
    return [r["state"] for r in rg.phase_rows(status)]


def test_phases_run_in_order_and_are_recorded(pipeline):
    rg.claim(19, 2)
    rg.generate_report(19, 2)
    assert pipeline.calls == [
        ("storylines", "storylines", "storylines", "running"),
        ("draft", "draft", "draft", "running"),
        ("voice", "voice", "voice", "running"),
    ]
    s = rg.read_status(19, 2)
    assert s["state"] == "done" and s["phase"] == "push"
    assert _states(s) == ["done"] * 5


def test_tournament_uses_full_pipeline(pipeline):
    rg.generate_report(19, None)
    assert [c[0] for c in pipeline.calls] == ["storylines", "draft", "voice"]
    assert rg.read_status(19, None)["state"] == "done"


def test_failure_keeps_failed_phase(pipeline):
    pipeline.fail_on["stage"] = "draft"
    rg.generate_report(19, 2)
    s = rg.read_status(19, 2)
    assert s["state"] == "error" and s["phase"] == "draft"
    assert "boom" in s["error"]
    assert _states(s) == ["done", "failed", "todo", "todo", "todo"]
    assert [c[0] for c in pipeline.calls] == ["storylines", "draft"]


def test_no_api_key_fails_before_any_phase(pipeline, monkeypatch):
    monkeypatch.setattr(rg.llm, "get_provider", lambda: rg.llm.PROVIDER_API)
    monkeypatch.setattr(rg.llm, "has_api_key", lambda: False)
    rg.generate_report(19, 2)
    assert pipeline.calls == []
    assert rg.read_status(19, 2)["state"] == "error"


def test_done_local_only_marks_push_failed(pipeline, monkeypatch):
    monkeypatch.setattr(rg, "push_files", lambda *a, **k: {"failed": ["x"], "committed": False})
    rg.generate_report(19, 2)
    s = rg.read_status(19, 2)
    assert s["state"] == "done_local_only"
    assert _states(s) == ["done"] * 4 + ["failed"]


def test_phase_rows_none_and_queued():
    assert _states(None) == ["todo"] * 5
    assert _states({"state": "queued", "phase": None}) == ["todo"] * 5
    assert [r["key"] for r in rg.phase_rows(None)] == [k for k, _ in rg.PHASES]


def test_phase_rows_running_and_stale():
    fresh = {"state": "running", "phase": "voice", "updated_at": rg._now()}
    assert _states(fresh) == ["done", "done", "active", "todo", "todo"]
    stale = {"state": "running", "phase": "draft", "updated_at": _iso(3 * 3600)}
    assert _states(stale) == ["done", "failed", "todo", "todo", "todo"]
    assert _states({"state": "error", "phase": None}) == ["failed"] + ["todo"] * 4


def _write_raw(teg, rnd, **fields):
    rg.write_status(teg, rnd, **fields)
    path = rg.status_path(teg, rnd)
    import json
    d = json.loads(path.read_text())
    d["updated_at"] = fields.get("updated_at", _iso(10))
    path.write_text(json.dumps(d))


def test_running_reports_window_and_order(store):
    _write_raw(19, 2, state="running", phase="draft", started_at=_iso(300))
    _write_raw(19, None, state="pushing", phase="push", started_at=_iso(600))
    _write_raw(18, 1, state="done", phase="push", started_at=_iso(900),
               finished_at=_iso(300), updated_at=_iso(300))
    _write_raw(18, 2, state="done", phase="push", started_at=_iso(4000),
               finished_at=_iso(3600), updated_at=_iso(3600))
    rows = rg.running_reports(now=NOW)
    assert [(r["teg"], r["round"]) for r in rows] == [(18, 1), (19, None), (19, 2)]
    by = {r["label"]: r for r in rows}
    assert by["TEG 19 R2"]["active"] and by["TEG 19 R2"]["phase_label"] == "Draft"
    assert by["TEG 19 tournament"]["active"]
    assert not by["TEG 18 R1"]["active"] and not by["TEG 18 R1"]["stale"]
    assert [r["state"] for r in by["TEG 19 R2"]["phases"]] == [
        "done", "active", "todo", "todo", "todo"]


def test_running_reports_missing_dir(store):
    assert rg.list_statuses() == []
    assert rg.running_reports(now=NOW) == []


def test_confirmation_needed(store):
    assert rg.confirmation_needed(19, 2, now=NOW) is None
    _write_raw(19, 2, state="running", phase="voice", started_at=_iso(60))
    c = rg.confirmation_needed(19, 2, now=NOW)
    assert c["reason"] == "running" and c["phase_label"] == "Voice pass"
    assert c["label"] == "TEG 19 R2"

    _write_raw(19, 3, state="done", finished_at=_iso(3600), updated_at=_iso(3600))
    assert rg.confirmation_needed(19, 3, now=NOW)["reason"] == "recent"

    _write_raw(19, 4, state="done", finished_at=_iso(7 * 3600), updated_at=_iso(7 * 3600))
    assert rg.confirmation_needed(19, 4, now=NOW) is None

    _write_raw(19, 1, state="error", finished_at=_iso(60), updated_at=_iso(60))
    assert rg.confirmation_needed(19, 1, now=NOW) is None


def test_claim_blocks_second_run(store):
    assert rg.claim(19, 2) is None
    msg = rg.claim(19, 2)
    assert "already generating" in msg and "TEG 19 R2" in msg


def test_report_label_and_fmt_hhmm():
    assert rg.report_label(19, 2) == "TEG 19 R2"
    assert rg.report_label(19, None) == "TEG 19 tournament"
    assert rg.phase_label("voice") == "Voice pass" and rg.phase_label("x") is None
    assert rg.fmt_hhmm("2026-09-29T14:05:30+00:00") == "14:05"
    assert rg.fmt_hhmm("2026-09-29T14:05:30+02:00") == "12:05"
    assert rg.fmt_hhmm(None) == "?" and rg.fmt_hhmm("junk") == "?"
