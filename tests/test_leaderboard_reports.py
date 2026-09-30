"""Leaderboard Reports tab: /leaderboard?tab=reports.

Deterministic tests patch the report lookups on ``webapp.routes.leaderboard``;
the last test hits the real data with no patching.
"""

import re

import pandas as pd
import pytest
from starlette.testclient import TestClient

from webapp.app import app
from webapp.routes import leaderboard as lb

TEG = 18
MIDDLE_DOT = "·"


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


def _others(teg, round_num):
    base = f"/teg-reports?teg={teg}" + (f"&round={round_num}" if round_num else "")
    return [{"kicker": f"KICK {i} | Sub", "headline": f"Other {round_num or 'T'}-{i}",
             "link": f"{base}#story/{i}"} for i in range(1, 7)]


def _fake_summary(teg, round_num=None, max_others=4):
    if round_num == 2 or round_num == 4:
        return {
            "teg": teg,
            "round": round_num,
            "title": f"Round {round_num} title",
            "kicker": f"Round {round_num}",
            "headline": f"Headline for round {round_num}",
            "standfirst": "A standfirst.",
            "link": f"/teg-reports?teg={teg}&round={round_num}",
            "lead_link": f"/teg-reports?teg={teg}&round={round_num}#story/0",
            "other_articles": _others(teg, round_num)[:max_others],
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
            "other_articles": _others(teg, round_num)[:max_others],
        }
    return None


@pytest.fixture
def patched(monkeypatch):
    def apply(complete):
        monkeypatch.setattr(lb, "_round_rows", lambda teg_num: [
            {"round": r, "course": f"Course {r}"} for r in (1, 2, 3, 4)
        ])
        monkeypatch.setattr(lb, "get_edition_summary", _fake_summary)
        monkeypatch.setattr(lb, "_teg_is_complete", lambda teg_num: complete)
        monkeypatch.setattr(lb, "available_tegs", lambda: [TEG])
    return apply


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
        # Rows open the round report itself, not its lead-story anchor.
        assert f'href="/teg-reports?teg={TEG}&amp;round={r}"' in section
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
    # The full page renders the title itself: no OOB swaps.
    assert "hx-swap-oob" not in _reports_section(resp.text)


def test_partial_swaps_title_and_header_out_of_band(client, patched):
    patched(complete=False)
    html = client.get(f"/leaderboard/table?teg={TEG}&tab=reports").text
    assert re.search(r'id="lb-context-header" hx-swap-oob="true"', html)
    assert re.search(rf'id="lb-page-title" hx-swap-oob="true"[^>]*>TEG {TEG} Leaderboard', html)


def test_no_rounds_is_an_empty_state_not_an_error(client, monkeypatch):
    monkeypatch.setattr(lb, "_round_rows", lambda teg_num: [])
    resp = client.get(f"/leaderboard/table?teg={TEG}&tab=reports")
    assert resp.status_code == 200
    assert "data-public-response-error" not in resp.text
    assert "No rounds scheduled yet" in _reports_section(resp.text)


def test_round_rows_coerces_and_dedupes(monkeypatch):
    frame = pd.DataFrame({
        "TEGNum": ["18", "18", "18", "18", "17"],
        "Round": [2, 1, 1, None, 1],
        "Course": ["B Course", float("nan"), "dupe", "x", "other"],
    })
    monkeypatch.setattr(lb, "read_file", lambda path: frame)
    assert lb._round_rows(18) == [
        {"round": 1, "course": None},
        {"round": 2, "course": "B Course"},
    ]


def test_unknown_tab_normalises_to_net(client):
    resp = client.get(f"/leaderboard/table?teg={TEG}&tab=bogus")
    assert resp.status_code == 200
    assert "lb-reports" not in resp.text


def test_real_data_smoke(client):
    resp = client.get(f"/leaderboard/table?teg={TEG}&tab=reports")
    assert resp.status_code == 200
    assert "hl-headline" in resp.text


def _all(client, path):
    return _reports_section(client.get(path).text)


def test_all_view_lists_every_story_and_pending_panels(client, patched):
    patched(complete=False)
    section = _all(client, f"/leaderboard/table?teg={TEG}&tab=reports&view=all")
    assert section.count('class="lb-reports-grid"') == 1
    assert section.count('<article class="lb-report-panel">') == 4
    for r in (2, 4):
        for i in range(1, 7):
            assert f"Other {r}-{i}" in section
        assert f"Round {r} headlines" in section
        assert f'href="/teg-reports?teg={TEG}&amp;round={r}#story/0"' in section
    assert "KICK 1 / Sub" in section
    assert section.count('<p class="hl-pending">Pending</p>') == 2
    assert MIDDLE_DOT not in section


def test_lead_view_unchanged_without_grid(client, patched):
    patched(complete=False)
    section = _all(client, f"/leaderboard/table?teg={TEG}&tab=reports")
    assert "lb-reports-grid" not in section
    assert "Other 2-1" not in section
    assert section.count("lb-report-pending") == 2


def test_bogus_view_falls_back_to_lead(client, patched):
    patched(complete=False)
    section = _all(client, f"/leaderboard/table?teg={TEG}&tab=reports&view=bogus")
    assert "lb-reports-grid" not in section
    lead = re.search(r'<button[^>]*data-public-state-value="lead"[^>]*>', section, re.S)
    assert lead and 'aria-pressed="true"' in lead.group(0)
    html = client.get(f"/leaderboard?teg={TEG}&tab=reports&view=bogus").text
    assert '<input type="hidden" id="lb-reports-view" name="view" value="lead">' in html


def test_full_page_all_view_marks_toggle_and_hidden_input(client, patched):
    patched(complete=False)
    html = client.get(f"/leaderboard?teg={TEG}&tab=reports&view=all").text
    assert re.search(r'<input type="hidden" id="lb-reports-view" name="view" value="all">', html)
    button = re.search(r'<button[^>]*data-public-state-value="all"[^>]*>', html, re.S)
    assert button and 'aria-pressed="true"' in button.group(0)
    assert re.search(r'hx-include="[^"]*#lb-reports-view', html)


def test_complete_all_view_has_tournament_panel_first(client, patched):
    patched(complete=True)
    section = _all(client, f"/leaderboard/table?teg={TEG}&tab=reports&view=all")
    assert section.count('<article class="lb-report-panel">') == 4
    assert section.index('<article class="lb-report-panel lb-report-wide">') < section.index("Round 1")
    assert f"TEG {TEG} headlines" in section
    assert f'href="/teg-reports?teg={TEG}"' in section
    assert "Other T-6" in section
