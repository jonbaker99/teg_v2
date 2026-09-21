# I2 — Public interaction and canonical URL state

Captured 2026-09-20. Worktree: `/Users/jon/projects/teg/worktrees/ui-i2`; branch: `codex/ui-i2`.

Base: `2f0baeff7e6042f56728c6c715fbb5e69a4db66a` (main tip after I1 and its mobile-polish follow-ups). Not merged, pushed or deployed. This handoff cannot include its own final commit SHA because it is part of that commit.

## Scope

Standardise public read-only tabs, filters, loading, failure, retry and canonical URLs. Preserve data and write paths. Score-writing, polling, admin forms, data updates, `teg_analysis/` and `streamlit/` are untouched.

Latest Round remains bounded. Its audited pending/confirmed state machine is unchanged; only its failure banner adopts the shared visual grammar.

## Contract decided before migration

- Tabs are views and use `.tab-underline`.
- Mutually exclusive measures use `.segmented > .seg-option`.
- Compact buttons are actions and use `.action`.
- A public page opts in with `<body data-public-state-keys="…">`.
- The server-rendered DOM is confirmed state. Requested controls, selected styles and the canonical URL commit only after the main HTMX target swaps successfully.
- Discrete state pushes one history entry. Text, number and range inputs replace the current entry.
- Back and forward reload the canonical URL, so server and client state cannot diverge.
- Transport failures and `data-public-response-error` partials retain the prior view and URL, restore confirmed controls, and expose Retry plus Dismiss.
- Retry replays the exact failed GET. Writes never enter this controller.

## What changed

`base.html` now provides a `body_attrs` block and one shared request-feedback region. `static/ui-polish.js` owns opt-in public GET state, busy state, successful commits, rollback, canonical history and exact-request retry. It commits once per response even when standings responses include out-of-band title or header swaps.

Public partial error branches now include `partials/_public_response_error.html`. A successful HTTP response carrying that marker is treated as an application failure and is not swapped over the confirmed view.

Full-page and partial routes now accept and render matching query state across Leaderboard, Results, Latest TEG, Honours, Records, Player Rankings, Eclectic, Eclectic Records, Top Performances, Personal Bests, Bestball, Scorecards, Player Profiles, Charts and the public scoring pages. Invalid enumerated values normalise to safe defaults.

Templates declare their canonical keys and annotate state-bearing tabs, segments and filter pills. Report links and conditional controls listen for shared commit or rollback events instead of changing optimistically.

Measures touched by this work moved from pill styling to segmented controls. Page-specific read spinners and error treatments were replaced by the shared pattern.

## Latest Round boundary

`latest_round.html` does not opt into `data-public-state-keys`. Its existing request ordering, pending state, URL sync, retry behaviour and polling interactions remain authoritative. I2 only reuses `.request-feedback` and `.action` styling for its existing failure controls and updates a stale comment.

## Verification

- Pinned Python 3.12: `tests/test_webapp_pages.py` — 103 passed. New coverage exercises direct query links, shared shell markup, static controller guards and invalid-state normalisation, including Scorecard state.
- JavaScript syntax: `node --check webapp/static/ui-polish.js` and `node --check webapp/static/player-profile.js`.
- Route syntax: changed route modules compile under Python 3.12.
- Repository checks: `scripts/check_python_compat.py`, `scripts/check_css_comments.py` and `git diff --check`.
- Browser, Chromium: server-authoritative default and invalid URLs; direct links and reload; successful selection commit; visible loading state; exactly one history entry for an OOB standings response; Back and forward; transport failure rollback; exact-request Retry; marked application failure rollback and Retry; Scorecard dependent-control rollback, retry and server-clamped OOB round state; overlapping same-target responses with the older response delayed; pending numeric input preserved across an earlier response with its confirmed rollback baseline retained; Results Gross/ranking → Scorecards → Back; Latest Round tab regression.

The browser and review runs exposed controller defects before completion. Programmatic HTMX retry requires an ordinary object because HTMX calls `hasOwnProperty`; retry values now use one. Out-of-band swaps initially pushed duplicate history entries; commits are restricted to the declared target and guarded once per response. Initial state comes from the normalised server DOM rather than raw query text. Per-target ordering rejects stale swaps. Server state is collected from the response, including OOB controls, before commit. A committed response does not overwrite a newer value still waiting for its delayed request, while rollback baselines remain confirmed.

## Models and ownership

Sol High led the contract, shared JavaScript, templates, tests, docs and integration. Luna performed the read-only URL/state inventory. Two Terra workers implemented bounded full-page route parity in non-overlapping route modules. A fresh strong review checked the combined diff before handoff.

## Unresolved

No I2 blocker remains. The existing Latest Round overlapping-request resilience TODO remains deliberately out of scope. The separate live-entry save-feedback TODO remains open because I2 does not alter writes or polling.
