# Dry run 4: preview checklist

Temporary. Delete with the PR once the run is done. Log findings in `TEST_TOURNAMENT_ISSUES.md`.

Setup: use this PR's Railway environment (own branch and volume, `main` untouched). Confirm that first. Create a dummy TEG at `/admin/teg-setup` and use Go live per round. The random-fill button is available off production.

## New since dry run 3

1. **Live entry, two phones.** Each phone sees the other's scores without reload. Turn off signal, save, see the unsaved banner, reload, restore signal, scores sync.
2. **Live tab on `/simulation`.** After each finalise: latest Trophy/Jacket chances, change since last round, hole-by-hole chart, slider and Play. Check a debutant is centred on handicap. Check the replay picker.
3. **Prediction tab.** Next-TEG odds, handicap what-ifs, equalise handicaps.
4. **TEGBot** (`/tegbot`). Ask about the dummy TEG: leader, round winners, win chances, "who is favourite for the trophy". Try Dig deeper. Expect it to see finalised rounds only; note whether it sees live-round scores or live chances.
5. **`/records` New Records tab** (incl. personal worsts) for the dummy TEG, plus `?new_teg=N`.
6. **Regression:** finalise feedback, reports tab, home page and `/handicaps` after round 4 (see `TEG19_FIX_PLAN.md`, second dry run).

Known gap to check: win chances use finalised data, so they likely move per round, not per hole, during live entry.
