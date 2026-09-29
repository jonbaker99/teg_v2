# Test tournament issue log

Temporary working log for the TEG 19 test run on PR #140 (test site: teg-test.up.railway.app). Delete once the issues below are moved into `webapp/TODOS.md` on `main` or fixed.

| # | Area | Issue | Status |
|---|---|---|---|
| 1 | Admin / live round | After Go live, the player score-entry link is shown once and can't be found again. The admin list and review pages link only to Review and the leaderboard. | Fix prompt written |
| 2 | Live round / leaderboard | From the leaderboard, the way back to score entry is hidden (see issue 6). Nothing tells players how the round gets finalised; it's admin-only via Admin → Live round → Review & Finalize. | Open |
| 3 | Admin / general | Admin pages aren't mobile-friendly. E.g. the live-round review grid overflows the screen width and cells are oversized. | Open |
| 4 | Admin / live round finalise | Finalise takes ~40s with no visible progress (the button only greys out). The success message renders below the fold and there's no redirect, so it looks like nothing happened. A second tap then shows "finalized, not active". Wanted: a clear progress state, then a confirmation and a jump to the leaderboard. | Open |
| 5 | Admin / live round review | After finalising, the review page still shows Save edits, Finalize and Cancel round as if the round were active. It should switch to a read-only view. | Open |
| 6 | Live round / leaderboard | The fixed Light / Dark toggle (`.demobar`, z-index 60, top-right) covers the "Enter scores" link in the app bar, so players can't get back to score entry. Same toggle is on the entry page; check it hides nothing there. Likely a design-mockup leftover: move it into the app bar/menu or remove it. `webapp/templates/live_round_leaderboard.html`, `live_round_entry.html`. | Open |
| 7 | Admin / live round finalise → reports | After a successful finalise (see issues 3–5), offer a direct next step: a button to the round report page pre-selected for that TEG/round (`/admin/reports?teg=N&round=R`). | Open |
