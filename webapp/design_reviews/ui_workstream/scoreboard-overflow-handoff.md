# Latest Round Scoreboard overflow fixed

Date: 2026-09-20. Base: `e50078d68719cb1697894ead7b24daff2f0ba919` (main). Worktree: `/Users/jon/projects/teg/worktrees/latest-round-scoreboard-overflow`. Branch: `codex/latest-round-scoreboard-overflow`. The final response supplies the resulting commit and next accepted base; this document cannot record its own commit SHA.

## Cause and scope

Reproduced P0 on `/latest-round?teg=18&round=4&tab=scoreboard&metric=Sc`, local TEG 18 R4, five players. At 390px in Clean Page light/dark, `.lr-total-toggle` computed width was 390px, height 44px, horizontal margins 12px, x=12 and right=402. Document width was 402px. The table itself was exactly 390px.

The existing mobile `.latest-round-page #lr-content .scale-switch` rule set `width:100%` in addition to both gutters. Changing only the total switch initially passed the default Score view, but HTMX selection of Stableford exposed the same cause in `.lr-scale-toggle`: width320, x12, right332, height44 at 320px. Both controls belong exclusively to Scoreboard in the current partial.

The final patch changes that existing rule to `width:calc(100% - 2 * var(--lr-inset))`. It preserves the 44px minimum height, labels, switch track, margins, and table column sizes. No clipping or horizontal-scroll workaround was added. The rule remains inside the existing ≤640px media query. No markup, route, JavaScript, other tab, or base-theme rule changed.

Clean Layered already fit the viewport because its existing page inset absorbed the overflow. The fix also keeps its switches within their parent gutters. At 390px, total-switch width is now 366px in Clean Page and 326px in Clean Layered. At 320px, the smallest tested control is 256×44px in Clean Layered.

## Verification

- Baseline and corrected geometry: 320/375/390/430/768/1280 × Clean Page/Clean Layered × light/dark, 24 states. Every corrected document and body width equals the viewport. Every table column x-position and width matches the baseline. Raw measurements: [measurements.json](screenshots/scoreboard-overflow/measurements.json).
- Final browser interactions: all 24 states, 13 overflow checkpoints each (312 total). Expand/collapse the first rank row; switch Round → TEG total → Round; switch Scoreboard → Scoring → Scoreboard and expand again; select Stableford, Gross vs Par, Net vs Par, and Score; toggle each available chart scale both ways. All pass, including visible detail and ARIA state assertions. Scoring was used only for navigation; no changes to that tab.
- All eight 768/1280 before/after screenshot pairs are pixel-identical. Phone screenshots were visually inspected. Browser: Chromium 153.0.8010.50. No page JavaScript errors in the interaction matrix; the existing Tailwind CDN warning remains.
- `/Users/jon/projects/teg/teg_v2/venv/bin/python -m pytest tests/test_webapp_pages.py -k latest_round -v`: **10 passed, 65 deselected**, 0.99s. This checks relevant server markup/state contracts; browser geometry is checked separately. No full suite justified for this CSS-only change.
- Runtime caveat: local tests use Python 3.14.7 (repository pin 3.12) and pandas 2.3.3 (requirements 3.x), as in P0. Pytest reported deprecation warnings and a non-failing sandbox cache-write warning. No runtime dependencies changed.

## Screenshot manifest and reproduction

All screenshots are under [screenshots/scoreboard-overflow](screenshots/scoreboard-overflow), JPEG quality65, viewport height844. Set cookies `theme=clean-page|clean-layered` and `mode=light|dark` at `/`, navigate to the exact route above, await fonts and 200ms layout settling, and capture at scrollY=0.

- `before-{clean-page,clean-layered}-{light,dark}-{390,768,1280}.jpg`: 12 captures at base e50078d.
- `after-{clean-page,clean-layered}-{light,dark}-{390,768,1280}.jpg`: 12 captures with the final CSS patch.
- `after-clean-page-light-320-stableford-scale.jpg`: change metric to Stableford at 320×844, then scroll `.lr-scale-toggle` into view. Both switches measure 296×44px; document width320.

Run locally from this worktree with `/Users/jon/projects/teg/teg_v2/venv/bin/python -m uvicorn webapp.app:app --host 127.0.0.1 --port 8137`. Browser actions were public reads; no data writes. Stop the server after verification.

## Review and remaining work

Astra Medium was sufficient; no higher-reasoning or lead-model change was needed. Luna ran focused tests. A fresh Astra Medium reviewer found no correctness or scope issues in the final CSS diff. The lead owned diagnosis, implementation, browser checks, and integration.

The matching TODO is closed. C4 may revisit the selector independently. No unresolved issue remains within this task. No push, merge, or deployment; STATUS.md remains unchanged because this branch has not shipped, following the roadmap operating rule. After acceptance, use the final response's commit as the exact next base.
