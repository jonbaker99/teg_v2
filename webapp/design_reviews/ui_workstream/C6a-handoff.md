# C6a — resolve C6's blocker (B1)

Captured 2026-09-20. Worktree: `/Users/jon/projects/teg/worktrees/ui-c6a`; branch: `claude/ui-c6a`. Base: `4f79f76` (the same base C6 reviewed) — this branch does **not** build on `claude/ui-c6`'s own commit, per the plan's instruction to keep the review commit and the fix commit separate.

C6 (`webapp/design_reviews/ui_workstream/C6-review.md`, B1) found one blocker: C5's removal of `.measure-toggle`'s CSS silently regressed `/latest-round`'s Round/TEG-total toggle, which still carries that class and needs it. This is a small, mechanical, no-design-judgement follow-up per the roadmap's own C6→trivial-fix pattern (mirrors F6a's role after F6).

## Fix

`webapp/static/themes/base-vars.css`: restored the `.measure-toggle` rule block C5 deleted (margin + neutral track/thumb colours), immediately after `.switch-thumb`'s rules, with a comment explaining the one remaining call site (`.lr-total-toggle`) and pointing back to `C6-review.md`'s B1 for the full diagnosis. No other file touched — the Leaderboard/Results `.segmented` control C5 migrated is unaffected (it never carried `.measure-toggle` in the first place; verified below).

## Verify

Local server: same throwaway venv as C6 (`/tmp/teg-c6-venv`, Python 3.12), `uvicorn webapp.app:app --port 8132`.

- **Before fix** (confirmed live during C6's review, `/latest-round?tab=scoreboard&round=2`, 1280px light Clean Page): unchecked `.switch-track`/`.switch-thumb` both `rgb(255,255,255)` on a `rgb(255,255,255)` card (invisible); checked state `.switch-track` `rgb(34,139,34)` (wrongly implies "on"); button margin `0px`.
- **After fix**, same route/state: unchecked *and* checked both render `.switch-track` `rgb(243,247,243)` / `.switch-thumb` `rgb(34,139,34)` — identical in both states, confirming the intended neutral (non-directional) look is restored; button margin `4px 0px 16px` (0.25rem/1rem, restored).
- **Leaderboard's `.segmented` control unaffected**: `/leaderboard`'s active `.seg-option[aria-pressed="true"]` still computes `color: rgb(34,139,34)` as before — this fix touches no selector the C3/C5 segmented-control work uses.
- `python scripts/check_css_comments.py` — OK, 15 files scanned.
- `python scripts/check_python_compat.py` — OK, 98 files parse cleanly under the pinned 3.12.
- `python scripts/check_pandas_compat.py` — 0 errors on the touched file (CSS only, N/A); pre-existing warnings elsewhere (`webapp/routes/player.py`) unrelated to this change.
- `python -m pytest tests/test_webapp_pages.py -q` — **76 passed.** Chosen over the full suite: this is a one-selector CSS-only fix restoring previously-shipped styling on a single public route, no `teg_analysis/` module, schema, or cross-module signature touched.

No `streamlit/` file touched. No `teg_analysis/` file touched.

## Files changed

```
webapp/static/themes/base-vars.css   (.measure-toggle rule restored)
```

## Handoff

Base `4f79f76`. This chat's resulting commit resolves C6's B1. C6's own verdict (not-ready pending B1) should be read alongside this fix — once integrated, the Consistent UI stage is ready for I1. No merge, push, or deploy performed.
