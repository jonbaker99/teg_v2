"""Leaderboard Reports tab: /leaderboard?tab=reports.

Deterministic tests patch the report lookups on ``webapp.routes.leaderboard``;
the last test hits the real data with no patching.
"""

import re

import pytest
from starlette.testclient import TestClient

from webapp.app import app
from webapp.routes import leaderboard as lb

TEG = 18
MIDDLE_DOT = "·"


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


def _fake_summary(teg, round_num):
    if round_num == 2 or round_num == 4:
        return {
            "teg": teg,
            "round": round_num,
            "title": f"Round {round_num} title",
            "kicker": f"Round {round_num}",
            "headline": f"Headline for round {round_num}",
            "standfirst": "A standfirst.",
            "link": f"/teg-reports?teg={teg}&round={round_num}",
            "other_articles": [],
        }
    if round_num is None:
        return {
            "teg": teg,
            "round": None,
            "title": "Tournament title",
            "kicker": "Tournament",
            "headline": "Tournament headline",
            "standfirst": "A standfirst.",
            "link": f"/teg-reports?teg={teg}",
            "other_articles": [],
        }
    return None


@pytest.fixture
def patched(monkeypatch):
    def apply(complete):
        monkeypatch.setattr(lb, "_round_rows", lambda teg_num: [
            {"round": r, "course": f"Course {r}"} for r in (1, 2, 3, 4)
        ])
        monkeypatch.setattr(lb, "get_edition_summary", _fake_summary_lookup)
        monkeypatch.setattr(lb, "_teg_is_complete", lambda teg_num: complete)
        monkeypatch.setattr(lb, "available_tegs", lambda: [TEG])
    return apply


def _fake_summary_lookup(teg, round_num=None, *args, **kwargs):
    return _fake_summary(teg, round_num)


def _reports_section(html):
    m = re.search(r'<section class="lb-reports".*?</section>', html, re.S)
    assert m, "lb-reports section missing"
    return m.group(0)


def test_in_progress_lists_all_rounds(client, patched):
    patched(complete=False)
    resp = client.get(f"/leaderboard/table?teg={TEG}&tab=reports")
    assert resp.status_code == 200
    section = _reports_section(resp.text)
    for r in (1, 2, 3, 4):
        assert f"Course {r}" in section
    for r in (2, 4):
        assert f"Headline for round {r}" in section
        assert f'href="/teg-reports?teg={TEG}&amp;round={r}"' in section or \
            f'href="/teg-reports?teg={TEG}&round={r}"' in section
    assert section.count("lb-report-pending") == 2
    assert section.count("Pending") == 2
    assert "No report" not in section
    assert "lead-teaser" not in section
    assert MIDDLE_DOT not in section
    # pending rounds are not links
    for block in re.findall(r'<div class="lb-report-pending".*?</div>', section, re.S):
        assert "<a " not in block


def test_complete_shows_no_report_and_tournament_teaser(client, patched):
    patched(complete=True)
    resp = client.get(f"/leaderboard/table?teg={TEG}&tab=reports")
    assert resp.status_code == 200
    section = _reports_section(resp.text)
    assert "No report" in section
    assert "Pending" not in section
    assert "lead-teaser" in section
    assert f'href="/teg-reports?teg={TEG}"' in section
    assert "Tournament report" in section
    assert MIDDLE_DOT not in section


def test_full_page_marks_reports_tab_active(client, patched):
    patched(complete=False)
    resp = client.get(f"/leaderboard?teg={TEG}&tab=reports")
    assert resp.status_code == 200
    assert "lb-reports" in resp.text
    button = re.search(
        r'<button[^>]*data-public-state-value="reports"[^>]*>', resp.text, re.S
    )
    assert button, "Reports tab button missing"
    assert "tab-underline--active" in button.group(0)
    assert 'id="lb-report-tab"' in resp.text


def test_unknown_tab_normalises_to_net(client):
    resp = client.get(f"/leaderboard/table?teg={TEG}&tab=bogus")
    assert resp.status_code == 200
    assert "lb-reports" not in resp.text


def test_real_data_smoke(client):
    resp = client.get(f"/leaderboard/table?teg={TEG}&tab=reports")
    assert resp.status_code == 200
    assert "hl-headline" in resp.text
