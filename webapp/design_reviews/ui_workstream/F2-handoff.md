# F2 — Records overflow (not reproduced)

Captured 2026-09-20. Starting base: `24aa920` (accepted F1 commit). Worktree: `/Users/jon/projects/teg/worktrees/ui-f2`; branch: `codex/ui-f2`. The tree was clean at entry. The final response supplies this handoff's resulting commit SHA.

F2 was scoped to fix standalone `/records` narrow-screen overflow. P0 had already found the claim **not reproduced** in Clean Page at 320/375/430px across all five tabs with disclosures open, and flagged that F2 must validate the remaining layout/mode combinations before proposing any CSS. This chat ran that validation and found the same result everywhere: **no fix needed.** No CSS, template, or route changed.

## Why it doesn't overflow

`_build_records_html` (`webapp/routes/records.py`) already emits a phone-only disclosure list (`.records-list` of `<details class="rec-row">`) alongside the unchanged desktop `<table class="records-table">`, toggled by `mobile.css`'s `≤640px` media query. The long venue+date string (e.g. `TEG 8 (Lisbon Coast, Portugal, 2015)`) is rendered into `.rec-detail`, the panel a `<details>` row reveals when tapped open. `.rec-detail` (`mobile.css` inside the Records block) has no `white-space: nowrap` or `text-overflow: ellipsis` — it wraps onto multiple lines inside its padded box instead of forcing the row, or the page, wider. `.rec-identity` (the record holder's name — the "owner" the acceptance criteria requires to stay scannable) does carry `overflow: hidden; text-overflow: ellipsis; white-space: nowrap`, so it truncates gracefully rather than overflowing too.

The TODO this chat closes (webapp/TODOS.md, Mobile & dark mode) predates this disclosure pattern's introduction and describes the "apply the mobile table approach" fix as if `/records` still rendered its desktop `<table>` unstyled on phones. It doesn't — the fix it asked for already exists in a different, already-correct form.

## Validation performed

Combined with P0's existing Clean Page evidence, this chat's own testing covers both dimensions P0 flagged as unvalidated: layout (Clean Layered) and mode (dark), plus a full tab sweep.

| Dimension | Values tested |
|---|---|
| Layout | Clean Page (P0, prior handoff) + **Clean Layered (this chat)** |
| Mode | Light (P0) + **light and dark (this chat, both layouts)** |
| Width | 320, 375, 430px |
| Tabs | teg, round, 9hole, streaks, score_counts (all five) |
| Disclosure state | Every `details.rec-row` forced open (`el.open = true`) — the worst case; closed rows never show `.rec-detail` at all |

Method: Playwright, driven programmatically (`browser_run_code_unsafe`) against this worktree's local server (`http://127.0.0.1:8122`, port dedicated to this task). For each of the 30 new (mode × width × tab) combinations in Clean Layered, navigated to `/records`, clicked the matching tab button to trigger its `hx-get` swap, force-opened every `<details class="rec-row">`, waited for layout to settle, then compared `document.documentElement.scrollWidth` / `document.body.scrollWidth` against `window.innerWidth`.

**Result: 0 of 30 states overflow** (all `scrollWidth <= innerWidth`, exact values e.g. 305/305/320 at 320px, 415/415/430 at 430px — the ~15px margin is the page gutter, not overflow). Combined with P0's 15 Clean Page states, that's 45 disclosure-open (mode × width × tab) states with zero overflow; P0's separate 15-state "all tabs open simultaneously" sweep in Clean Page adds no new failures either.

Confirmed the exact reported string is present in this checkout's data and was exercised: `.rec-detail` text for the TEG-records tab includes `"TEG 8 (Lisbon Coast, Portugal, 2015)"` and `"TEG 4 (East Sussex, England, 2011)"` verbatim — this is not a stale/removed-data false negative.

**Focused test:**
```
python -m pytest "tests/test_webapp_pages.py::test_nav_page_renders[/records]" -v
```
1 passed. No source changed, so this is a sanity check only — no wider suite run (CLAUDE.md blast-radius guidance: docs-only change here needs no test).

**Screenshot:** `webapp/design_reviews/ui_workstream/screenshots/F2/f2-records-layered-375-dark-expanded.png` — Clean Layered, dark, 375px, every disclosure open, full page. Representative evidence; the full 30-state sweep was measured programmatically, not screenshotted individually (same approach F1 used for its glyph/contrast checks).

## Rules followed

- No CSS/template/route change proposed or made — the acceptance criterion (no page/panel widening, value and owner stay scannable) was already met.
- Did not touch the Latest Round Records tab (shared renderer via `_render_records_summary`) — that stays F4's scope per the roadmap.
- No admin/score-entry tables touched.
- Desktop (1280px) untouched by construction — no source edited.
- Delegation: this chat's diagnosis was Playwright-driven measurement, not CSS authoring, so no lower-cost worker was spun up — running it directly was cheaper than the coordination/review overhead of delegating a measurement task this bounded (same judgment call F1 made for its two small patches).
- No lead-model change needed or requested.

## TODO closed

`webapp/TODOS.md` → Mobile & dark mode → "Records table horizontal overflow on narrow screens" marked `[X]`, with the disclosure-pattern explanation and the 60-state (P0 + F2) evidence summary replacing the stale "apply the mobile table approach" prescription.

## Unresolved / explicitly out of scope

- Latest Round's embedded Records tab (shared `_build_records_html` output reused via `_render_records_summary`) was not tested here — remains F4.
- `.rec-identity` name truncation (ellipsis) was noted but not treated as a defect: names are short enough in current data that this wasn't observed to actually truncate in the states tested; flagging only as something F4 or a later pass should re-check if roster names lengthen.
- No new automated overflow-regression test was added (P0 already noted this test-coverage gap generally); this chat's validation was manual/programmatic, matching F1's precedent for this kind of visual check.

## Handoff

This chat made no application changes — only `webapp/TODOS.md` and this handoff/screenshot were committed. F3 and F4 may branch from either P0's or this chat's resulting commit per the roadmap ("F1/F2/F3 investigation only" in parallel); F4 specifically depends on F2 being accepted before extending the (unmodified) shared Records renderer into Latest Round. No push, merge, or deploy performed.
