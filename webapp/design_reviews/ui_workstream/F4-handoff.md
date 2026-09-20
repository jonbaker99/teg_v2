# F4 — Latest Round Records and Scorecard phone layouts

Captured 2026-09-20. Starting base: `b3076c4` (accepted F3 commit). Worktree: `/Users/jon/projects/teg/worktrees/ui-f4`; branch: `claude/ui-f4`. The tree was clean at entry. The final response supplies this handoff's resulting commit SHA.

F4 was scoped to finish `/latest-round`'s Records & PBs and Scorecard tabs on phones, building on F2's accepted (not-reproduced) standalone Records fix and F3's baseline note that generic Latest Round `.data-card` rules already zero side padding. This chat found and fixed one real, reproduced bug (Records tab double-wrapped in an extra card) and validated the Scorecard claim as not reproduced, with one pre-existing shared-CSS finding logged for a future chat.

## What was actually wrong (and what wasn't)

**Scorecard: not reproduced.** `_latest_round_tab_context`'s `scorecard` branch already sets `"raw": True` on its section dict, so `latest_round_tab.html` inserts `build_round_comparison_responsive`'s own markup (`.sc-landscape`/`.sc-portrait`, each with its own `.data-card`) directly — it never passes through the generic `<div class="data-card"><div class="table-wrapper">...` wrap the task brief suspected. Measured `.main-content`, `#lr-content`/`#scorecard-content`, `.sc-scroll` and the table itself against standalone `/scorecard` at 320/375/430/768/1280px, light/dark, both Clean layouts:

- At 375/430/768/1280px the table's absolute page position and width were **pixel-identical** between Latest Round and standalone.
- At 320px, Latest Round's container was actually **20px wider** (0px `.main-content` padding vs standalone's 12px generic phone inset — an existing Latest Round mobile.css rule, not something F4 added), so Latest Round's table rendered *less* compressed than standalone's, not more.
- The one genuine inset found is a **12px `scrollWidth` overflow at 768px in Clean Layered** (`.sc-landscape .data-card { padding: 0 12px }` exceeding its container). It reproduces byte-for-byte on standalone `/scorecard` at the same width/theme — confirmed side by side, same 780px `scrollWidth` on both pages. This is a pre-existing shared-CSS issue affecting both pages equally, not a Latest-Round-specific "double inset." Fixing it would mean touching `.sc-landscape .data-card`/`webapp/static/scorecard.css`, which the "preserve standalone /scorecard exactly" rule puts out of scope for this chat.

The narrow, visually centred look of the phone Scorecard table (large side gutters at 320-430px) is real but is caused by the table's own fixed per-column widths (`calc(var(--shape-size) * 1.15)`) not stretching to fill the viewport for small rosters — identical behaviour on both pages, by design, not a padding bug.

**Records & PBs: one real, reproduced bug.** `_latest_round_tab_context` and `_latest_teg_tab_context`'s `records` sections built their HTML via `_render_records_summary` (which already returns a complete, self-contained `.records-page` block — un-boxed `<h2 class="section-title">` headings plus its own per-section `.data-card`s, matching standalone `/records`'s structure) but did **not** set `"raw": True` on the section dict, unlike the neighbouring `scorecard`/`bestball` sections. The generic template branch (`{% else %}<div class="data-card"><div class="table-wrapper">{{ section.table_html | safe }}</div></div>{% endif %}`) then wrapped that entire already-complete block in a second, unwanted `.data-card > .table-wrapper`.

This was invisible in Clean Page (no `.data-card` styling at all) and at ≤640px in either theme (`mobile.css` zeroes `.data-card` padding inside `#lr-content`/`#lt-content`), which is why P0/F3's screenshot sampling didn't catch it. It was clearly visible in Clean Layered above 640px: the section headings, which should sit outside any card (as they do on standalone `/records`), instead sat nested inside a second bordered/shadowed box — see `screenshots/F4/f4-records-layered-1280-before.png` vs `-after.png`.

## Fix

| File | Change |
|---|---|
| `webapp/routes/latest.py` | Added `"raw": True` to the `records` section dict in both `_latest_round_tab_context` and `_latest_teg_tab_context`, matching the pattern already used by the `scorecard`/`bestball` sections in the same functions. |

No change to `_build_records_html` (`webapp/routes/records.py`) or `_render_records_summary` — the shared renderer itself was already correct; only the caller's wrapping decision was wrong. No CSS or template change; no wrapper hook needed.

## Verification

Ran locally from this worktree:

```bash
cd /Users/jon/projects/teg/worktrees/ui-f4
/Users/jon/projects/teg/teg_v2/venv/bin/python -m uvicorn webapp.app:app --host 127.0.0.1 --port 8124
```

Same runtime caveat as P0/F1/F2/F3: available interpreter is Python 3.14.7, while `.python-version` pins 3.12. UI verification only, not deployment-runtime compatibility.

**Focused tests:**
```
python -m pytest tests/test_webapp_pages.py -k 'latest_round or latest_teg' -v   # 17 passed
python -m pytest tests/test_scorecards_portrait.py -v                            # 15 passed
```
No wider suite run — a two-line route-context change scoped to Latest Round/TEG's records section, not a shared/core module (CLAUDE.md blast-radius guidance).

**Browser verification (Playwright, Chromium):**

| Check | Coverage | Result |
|---|---|---|
| Records & PBs no page overflow | 320/375/430/768/1280px × Clean Page/Clean Layered × light/dark × TEG18R4, TEG17R2, TEG10R1, TEG8R1 (120 states), every `details.rec-row` force-opened | 0/120 `scrollWidth > innerWidth` |
| Records double-wrap fix, visual | `/latest-round?tab=records`, `/latest-teg` Records tab, Clean Layered, 1280px, both light/dark | Extra outer card gone; headings sit outside cards, matching standalone `/records` (screenshots below) |
| Records double-wrap fix, both call sites | `_latest_round_tab_context` and `_latest_teg_tab_context` | Both verified independently (TEG 17 R2 round records; TEG 17 aggregate records) |
| Scorecard vs standalone, absolute position | 320/375/430/768/1280px, both themes | Pixel-identical at ≥375px; Latest Round *less* inset at 320px (see above) |
| Scorecard 768px Clean Layered overflow | Both pages, same width/theme | Identical 780px `scrollWidth` on both — pre-existing, shared, not introduced or fixed here |
| Scoreboard → Records → Scoreboard → Scoring HTMX swap sequence | 390px, Clean Page, light, live clicks (not direct URL loads) | No overflow after swap; Scoreboard/Scoring render correctly on return; 0 console errors |
| Gross vs Stableford scoring control (regression) | Live click, 390px | `table.scoring-table` renders correctly after toggle |
| Regression sweep: Scoreboard, Bestball/Worstball | 390/1280px × Clean Page/Clean Layered × light/dark | 0 overflow, 0 console/page errors |
| Full-matrix overflow sweep, all 6 Latest Round tabs | 320/375/430/768/1280px × 2 themes × 2 modes = 120 states | Only the pre-existing shared 768px Clean Layered Scorecard overflow (2 states); Records, Scoreboard, Scoring, Streaks, Bestball clean throughout |

Console: 0 errors on every page checked (the pre-existing Tailwind production-CDN warning is the only recurring entry, as noted in P0/F1/F2/F3).

Screenshots: `webapp/design_reviews/ui_workstream/screenshots/F4/` —
- `f4-records-layered-1280-before.png` / `f4-records-layered-1280-after.png` — the double-wrap bug and its fix, `/latest-round` Records tab, Clean Layered, 1280px, dark
- `f4-latest-teg-records-layered-1280-after.png` — same fix confirmed on `/latest-teg`'s Records tab (TEG 17)
- `F4-records-320-dark-layered-expanded.png` — Records & PBs at 320px, Clean Layered, dark, all disclosures open
- `f4-lr-scorecard-390.png` / `f4-standalone-scorecard-390.png` — side-by-side evidence that Scorecard renders identically on both pages at 390px

## Rules followed

- Reused the shared Records renderer (`_build_records_html`/`_render_records_summary`) unchanged; the fix is entirely in the caller's section-wrapping flag, not a second renderer.
- No wrapper hook added — the existing `raw` flag already covers this case, matching the scorecard/bestball precedent in the same functions.
- Standalone `/records` and `/scorecard` untouched — no file under either route's direct ownership was edited.
- Scoreboard, Scoring, Streaks, Bestball, Worstball verified unchanged (regression sweep above).
- No `teg_analysis`, score entry, or live-round code touched.
- Delegation: the lead (this chat) performed the diagnosis (DOM/CSS measurement, side-by-side screenshot comparison against standalone) and the fix directly — a two-line, two-call-site change was cheaper to write than to scope and review as a delegated task, matching F1/F2's precedent for small, tightly-bounded patches.

## Unresolved / explicitly out of scope

- **Shared `.sc-landscape .data-card` 12px overflow at 768px in Clean Layered** — reproduces identically on standalone `/scorecard` and Latest Round's Scorecard tab. Pre-existing, not introduced by this chat, not fixed here (would require touching shared `scorecard.css`, which the "preserve standalone /scorecard exactly" rule places outside F4). Worth a small future chat scoped to `scorecard.css` tablet padding, covering both pages together.
- The Scorecard tab's inherently narrow/centred phone table (fixed per-column widths not stretching to the viewport for small rosters) is shared, by-design behaviour on both pages — not treated as a defect; flagged here in case a future pass wants the table to use more available width on 5-player rosters.
- No new automated overflow/regression test was added (P0/F1/F2/F3 precedent — this class of visual check is verified manually/programmatically via Playwright each time, not via a new test file); the general test-coverage gap the workstream has flagged repeatedly still stands.
- The F4 task brief's "Scorecard tab must lose its double side inset" framing (carried from F3's baseline note) did not reproduce on direct measurement; documented as not-reproduced in `webapp/TODOS.md` rather than silently dropped.

## Handoff

This chat's resulting commit is the next accepted integration base after `F1 → F2 → F3 → F4`; F5 (navigation persistence) depends on F1-F4 accepted and should branch from this commit's SHA. No push, merge, or deploy performed.
