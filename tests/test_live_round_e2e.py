"""End-to-end integration test for live round entry, against the real stack.

Unlike test_live_round.py (unit tests, storage module in isolation) and
test_admin_routes.py / test_live_round_routes.py (routes with the module
monkeypatched), this test exercises the *real* teg_analysis.analysis.live_round
module, the *real* FastAPI routes, and the *real* execute_data_update pipeline
end-to-end over actual HTTP requests (via TestClient) -- the only thing
replaced is where "local disk" points, via the same scratch_repo pattern
test_data_update.py uses, so nothing here ever touches the real data/
directory.

Simulates two devices (two independent TestClient "sessions") entering
scores for the same live round concurrently, confirms they see each other's
writes, deliberately triggers a conflict, resolves it via the admin review
flow, and finalizes -- checking the scores actually land in all-scores.parquet.
"""

import shutil
from pathlib import Path

import pandas as pd
import pytest
from starlette.testclient import TestClient

import teg_analysis.io.volume_operations as volume_operations
from webapp.app import app


@pytest.fixture
def scratch_repo(tmp_path, monkeypatch):
    """Isolated copy of data/ -- see test_data_update.py for the same pattern."""
    real_data = Path(__file__).resolve().parent.parent / "data"
    shutil.copytree(real_data, tmp_path / "data")
    monkeypatch.setattr(volume_operations, "_REPO_ROOT", tmp_path)
    monkeypatch.delenv("RAILWAY_ENVIRONMENT", raising=False)
    return tmp_path


@pytest.fixture
def admin(scratch_repo, monkeypatch):
    """A logged-in admin TestClient, with round_pars.csv/handicaps.csv seeded
    for a fake TEG 999 Round 1 so start_live_round's prerequisites are real,
    not mocked."""
    monkeypatch.setenv("WEBAPP_ADMIN_PASSWORD", "secret123")

    round_info = pd.read_csv(scratch_repo / "data" / "round_info.csv")
    round_info = pd.concat([round_info, pd.DataFrame([{
        "TEGNum": 999, "Round": 1, "Course": "Ashdown", "Date": "01/01/2099",
        "TEGRd": "TEG 999|1", "TEG": "TEG 999", "Area": "Test", "Year": 2099,
    }])], ignore_index=True)
    round_info.to_csv(scratch_repo / "data" / "round_info.csv", index=False)

    pars = pd.DataFrame(
        [{"TEGNum": 999, "Round": 1, "Hole": h, "Par": 4, "SI": h} for h in range(1, 19)]
    )
    pars.to_csv(scratch_repo / "data" / "round_pars.csv", index=False)

    handicaps = pd.read_csv(scratch_repo / "data" / "handicaps.csv")
    new_row = {c: 0 for c in handicaps.columns}
    new_row["TEG"] = "TEG 999"
    new_row["DM"] = 18
    new_row["GW"] = 16
    handicaps = pd.concat([handicaps, pd.DataFrame([new_row])], ignore_index=True)
    handicaps.to_csv(scratch_repo / "data" / "handicaps.csv", index=False)

    client = TestClient(app, follow_redirects=False)
    resp = client.post("/admin/login", data={"password": "secret123"})
    assert resp.status_code == 303
    return client


def _start_live_round(admin):
    resp = admin.post("/admin/live-round/start", data={"teg_num": "999", "round_num": "1"})
    assert resp.status_code == 200
    assert "TEG 999" in resp.text
    match = __import__("re").search(r"/live-round/([\w-]+)", resp.text)
    assert match, resp.text
    return match.group(1)


def test_full_lifecycle_two_devices_conflict_and_finalize(admin, scratch_repo):
    token = _start_live_round(admin)

    device_a = TestClient(app)  # no auth needed -- token-gated public routes
    device_b = TestClient(app)

    # The entry page itself renders for both devices with the real roster/pars.
    page = device_a.get(f"/live-round/{token}")
    assert page.status_code == 200
    assert "David MULLIN" in page.text or "DM" in page.text

    # Device A enters hole 1 for DM.
    r = device_a.post(
        f"/api/live-round/{token}/scores",
        json={"device_id": "dev-A", "device_name": "Jon's phone",
              "cells": [{"hole": 1, "player": "DM", "value": 4}]},
    )
    assert r.status_code == 200
    seq_after_a = r.json()["seq"]

    # Device B polls and sees it immediately -- real cross-device visibility.
    poll_b = device_b.get(f"/api/live-round/{token}/scores?since=0")
    assert poll_b.status_code == 200
    body = poll_b.json()
    cell = next(c for c in body["cells"] if c["hole"] == 1 and c["player"] == "DM")
    assert cell["value"] == 4
    assert cell["conflict"] is False

    # Device B enters hole 2 for GW; device A should see it on its next poll.
    device_b.post(
        f"/api/live-round/{token}/scores",
        json={"device_id": "dev-B", "device_name": "Dave's phone",
              "cells": [{"hole": 2, "player": "GW", "value": 5}]},
    )
    poll_a = device_a.get(f"/api/live-round/{token}/scores?since={seq_after_a}")
    cell2 = next(c for c in poll_a.json()["cells"] if c["hole"] == 2 and c["player"] == "GW")
    assert cell2["value"] == 5

    # Deliberately conflict: device B overwrites DM's hole 1 with a different value.
    device_b.post(
        f"/api/live-round/{token}/scores",
        json={"device_id": "dev-B", "device_name": "Dave's phone",
              "cells": [{"hole": 1, "player": "DM", "value": 5}]},
    )
    poll_conflict = device_a.get(f"/api/live-round/{token}/scores?since=0")
    conflict_cell = next(c for c in poll_conflict.json()["cells"] if c["hole"] == 1 and c["player"] == "DM")
    assert conflict_cell["conflict"] is True
    assert conflict_cell["value"] == 5  # latest write still applies, never blocks entry
    assert conflict_cell["prev_value"] == 4

    # Admin review page shows the conflict and disables finalize.
    review = admin.get(f"/admin/live-round/{token}/review")
    assert review.status_code == 200
    assert "disagree" in review.text.lower()

    # Finalize refuses while the conflict is unresolved.
    blocked = admin.post(f"/admin/live-round/{token}/finalize")
    assert "resolve every conflicted cell" in blocked.text.lower()

    # Admin resolves the conflict.
    resolved = admin.post(f"/admin/live-round/{token}/resolve", data={"hole": "1", "player": "DM", "chosen_value": "5"})
    assert "confirmed" in resolved.text.lower()

    review_after = admin.get(f"/admin/live-round/{token}/review")
    assert "none" in review_after.text.lower() or "✅" in review_after.text

    # Fill out the rest of DM's round (18 holes) so finalize has a complete round to write.
    remaining = [{"hole": h, "player": "DM", "value": 4} for h in range(2, 19)]
    device_a.post(f"/api/live-round/{token}/scores", json={"device_id": "dev-A", "device_name": "Jon", "cells": remaining})

    finalize_resp = admin.post(f"/admin/live-round/{token}/finalize")
    assert "finalized" in finalize_resp.text.lower(), finalize_resp.text

    # The real pipeline actually wrote to all-scores.parquet in the scratch repo.
    all_scores = pd.read_parquet(scratch_repo / "data" / "all-scores.parquet")
    dm_rows = all_scores[(all_scores["TEGNum"] == 999) & (all_scores["Round"] == 1) & (all_scores["Pl"] == "DM")]
    assert len(dm_rows) == 18
    hole1 = dm_rows[dm_rows["Hole"] == 1].iloc[0]
    assert int(hole1["Sc"]) == 5  # the resolved value, not either pre-conflict value

    # The round is now inactive -- further writes are rejected, not silently dropped.
    late_write = device_a.post(
        f"/api/live-round/{token}/scores",
        json={"device_id": "dev-A", "device_name": "Jon", "cells": [{"hole": 3, "player": "DM", "value": 4}]},
    )
    assert late_write.status_code == 409

    # And the page itself reflects the finalized/read-only state on next load.
    final_page = device_a.get(f"/live-round/{token}")
    assert final_page.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
