"""PDF download route and button gating on /teg-reports.

Companion to tests/test_webapp_pages.py (same TestClient-against-the-real-app
pattern). These cover the serving half of the PDF feature only -- the rendering
half lives offline in scripts/build_report_pdfs.py and is not exercised here,
deliberately: it needs headless Chromium, which is a dev-only dependency and is
not installed on Railway or in CI.

The manifest is the source of truth for "does this report have a PDF", so most
of what's worth testing is that the button and the route agree with it, and
that a report without one degrades to no-button/404 rather than a broken link.
"""


import pytest
from starlette.testclient import TestClient

from webapp.app import app
from webapp.routes import reports as reports_route
from teg_analysis.reporting.newspaper_edition import available_report_tegs


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


@pytest.fixture
def fake_manifest(monkeypatch):
    """Point the route's manifest at a controlled set of entries.

    Patches the cached accessor rather than the file so the test doesn't depend
    on whether the PDFs happen to have been built in this checkout.
    """
    def _install(entries):
        monkeypatch.setattr(
            reports_route, "_pdf_manifest",
            lambda: {"entries": {k: {"sha": "x", "bytes": 1} for k in entries}},
        )
    return _install


# ---------------------------------------------------------------------------
# Manifest -> button gating
# ---------------------------------------------------------------------------

def test_button_shown_when_manifest_lists_the_edition(client, fake_manifest):
    teg = sorted(available_report_tegs(), reverse=True)[0]
    fake_manifest([f"teg_{teg}"])
    resp = client.get("/teg-reports", params={"teg": teg})
    assert resp.status_code == 200
    assert "np-pdf-link" in resp.text
    assert f"/teg-reports/pdf?teg={teg}" in resp.text


def test_button_hidden_when_manifest_has_no_entry(client, fake_manifest):
    teg = sorted(available_report_tegs(), reverse=True)[0]
    fake_manifest([])
    resp = client.get("/teg-reports", params={"teg": teg})
    assert resp.status_code == 200
    assert "np-pdf-link" not in resp.text


def test_page_still_renders_when_manifest_is_missing(client, monkeypatch):
    """A missing manifest must hide the button, not break the page."""
    monkeypatch.setattr(reports_route, "_pdf_manifest", lambda: {})
    teg = sorted(available_report_tegs(), reverse=True)[0]
    resp = client.get("/teg-reports", params={"teg": teg})
    assert resp.status_code == 200
    assert "np-pdf-link" not in resp.text


def test_round_button_carries_the_round_param(client, fake_manifest):
    from teg_analysis.reporting.newspaper_edition import available_rounds
    teg = next(
        (t for t in sorted(available_report_tegs(), reverse=True) if available_rounds(t)),
        None,
    )
    if teg is None:
        pytest.skip("no TEG with round reports in this checkout")
    rnd = sorted(available_rounds(teg))[0]
    fake_manifest([f"teg_{teg}_round_{rnd}"])
    resp = client.get("/teg-reports", params={"teg": teg, "round": rnd})
    assert resp.status_code == 200
    # Bare "&", not "&amp;": the separator is literal template text, which
    # Jinja does not autoescape, and the existing round pills above it are
    # written the same way.
    assert f"/teg-reports/pdf?teg={teg}&round={rnd}" in resp.text


# ---------------------------------------------------------------------------
# The download route itself
# ---------------------------------------------------------------------------

def test_pdf_route_serves_bytes(client, monkeypatch):
    monkeypatch.setattr(reports_route, "read_binary_file", lambda path: b"%PDF-1.4 fake")
    resp = client.get("/teg-reports/pdf", params={"teg": 18})
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    assert resp.content.startswith(b"%PDF")
    assert 'filename="TEG-18-report.pdf"' in resp.headers["content-disposition"]


def test_pdf_route_round_filename(client, monkeypatch):
    monkeypatch.setattr(reports_route, "read_binary_file", lambda path: b"%PDF-1.4 fake")
    resp = client.get("/teg-reports/pdf", params={"teg": 18, "round": 3})
    assert resp.status_code == 200
    assert 'filename="TEG-18-round-3-report.pdf"' in resp.headers["content-disposition"]


def test_pdf_route_404s_when_absent(client, monkeypatch):
    def _missing(path):
        raise FileNotFoundError(path)
    monkeypatch.setattr(reports_route, "read_binary_file", _missing)
    resp = client.get("/teg-reports/pdf", params={"teg": 99})
    assert resp.status_code == 404


def test_pdf_route_reads_the_expected_path(client, monkeypatch):
    seen = {}

    def _capture(path):
        seen["path"] = path
        return b"%PDF-1.4 fake"

    monkeypatch.setattr(reports_route, "read_binary_file", _capture)
    client.get("/teg-reports/pdf", params={"teg": 14, "round": 2})
    assert seen["path"] == "data/commentary/pdfs/teg_14_round_2.pdf"
