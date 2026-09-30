"""Report readiness gating on /admin/reports and the generate refusal."""

import pytest
from starlette.testclient import TestClient

import teg_analysis.analysis.live_round as lrmod
from webapp import deps, finalize_jobs, report_generation
from webapp.app import app


@pytest.fixture(autouse=True)
def _env(tmp_path, monkeypatch):
    monkeypatch.setenv("WEBAPP_ADMIN_PASSWORD", "secret123")
    monkeypatch.setattr(finalize_jobs, "_store_path", lambda rel: tmp_path / rel)
    monkeypatch.setattr(deps, "get_available_teg_numbers", lambda: [19])
    monkeypatch.setattr(deps, "get_default_teg_num", lambda: 19)
    monkeypatch.setattr(deps, "get_rounds_for_teg", lambda teg: [1, 2, 3])
    monkeypatch.setattr(deps, "get_current_in_progress_teg_fast", lambda: (20, None))


@pytest.fixture
def client():
    c = TestClient(app, follow_redirects=False)
    assert c.post("/admin/login", data={"password": "secret123"}).status_code == 303
    return c


def _readiness(monkeypatch, result):
    monkeypatch.setattr(lrmod, "report_readiness", lambda teg, rnd=None: result)


READY = {"ready": True, "state": "ready", "reason": None, "token": None, "round": None}


def _not_ready(state, reason):
    return {"ready": False, "state": state, "reason": reason, "token": "tok3", "round": 3}


def _round_button(html):
    start = html.index("Generate round report")
    return html[html.rindex("<button", 0, start):start]


def test_panel_ready_is_enabled(client, monkeypatch):
    _readiness(monkeypatch, READY)
    html = client.get("/admin/reports/panel?teg=19&round=3").text
    assert "disabled" not in _round_button(html)
    assert "See finalise progress" not in html


def test_panel_not_finalised_disables_with_message_and_link(client, monkeypatch):
    _readiness(monkeypatch, _not_ready("not_finalised", "Round 3 hasn't been finalised yet."))
    html = client.get("/admin/reports/panel?teg=19&round=3").text
    assert "disabled" in _round_button(html)
    assert "Round 3 hasn&#39;t been finalised yet." in html or "Round 3 hasn't been finalised yet." in html
    assert 'href="/admin/live-round/tok3/review"' in html
    assert "See finalise progress" in html


def test_panel_processing_shows_step_number(client, monkeypatch):
    _readiness(monkeypatch, _not_ready("processing", "Round 3 data still being processed."))
    finalize_jobs.claim("tok3")
    finalize_jobs.write_status("tok3", state="running", step="all_data")
    idx = [k for k, _ in lrmod.FINALIZE_STEPS].index("all_data") + 1
    html = client.get("/admin/reports/panel?teg=19&round=3").text
    assert f"Round 3 data still being processed, step {idx} of {len(lrmod.FINALIZE_STEPS)}." in html


def test_panel_failed_shows_reason(client, monkeypatch):
    _readiness(monkeypatch, _not_ready("failed", "Round 3 finalise failed at scores."))
    html = client.get("/admin/reports/panel?teg=19&round=3").text
    assert "Round 3 finalise failed at scores." in html
    assert "disabled" in _round_button(html)


def test_generate_refused_when_not_ready(client, monkeypatch):
    _readiness(monkeypatch, _not_ready("failed", "Round 3 finalise failed at scores."))
    claimed = []
    monkeypatch.setattr(report_generation, "claim", lambda *a: claimed.append(a))
    monkeypatch.setattr(report_generation, "confirmation_needed", lambda *a: claimed.append(a))
    resp = client.post("/admin/reports/generate", data={"kind": "round", "teg": 19, "round": 3})
    assert resp.status_code == 200
    assert "Round 3 finalise failed at scores." in resp.text
    assert "/admin/live-round/tok3/review" in resp.text
    assert "HX-Trigger" not in resp.headers
    assert claimed == []  # refused before the confirmation/claim logic


def test_generate_refusal_uses_same_text_as_panel(client, monkeypatch):
    _readiness(monkeypatch, _not_ready("processing", "Round 3 data still being processed."))
    finalize_jobs.claim("tok3")
    finalize_jobs.write_status("tok3", state="running", step="status")
    expected = finalize_jobs.report_block(19, 3)["message"]
    assert "step" in expected
    resp = client.post("/admin/reports/generate", data={"kind": "round", "teg": 19, "round": 3})
    assert expected in resp.text


def test_generate_proceeds_when_ready(client, monkeypatch):
    _readiness(monkeypatch, READY)
    started = []
    monkeypatch.setattr(report_generation, "confirmation_needed", lambda *a: None)
    monkeypatch.setattr(report_generation, "claim", lambda teg, rnd: None)
    monkeypatch.setattr(report_generation, "generate_report", lambda teg, rnd: started.append((teg, rnd)))
    resp = client.post("/admin/reports/generate", data={"kind": "round", "teg": 19, "round": 3})
    assert resp.status_code == 200
    assert resp.headers.get("HX-Trigger") == "report-started"
    assert started == [(19, 3)]


def test_tournament_gated_on_tournament_readiness(client, monkeypatch):
    seen = []

    def readiness(teg, rnd=None):
        seen.append(rnd)
        return _not_ready("not_finalised", "Round 3 hasn't been finalised yet.") if rnd is None else READY

    monkeypatch.setattr(lrmod, "report_readiness", readiness)
    resp = client.post("/admin/reports/generate", data={"kind": "tournament", "teg": 19})
    assert "Round 3" in resp.text and "finalised" in resp.text
    assert None in seen
