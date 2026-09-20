# C6 — Consistent UI review gate

Captured 2026-09-20. Worktree: `/Users/jon/projects/teg/worktrees/ui-c6`; branch: `claude/ui-c6`. Read-only review — no application code touched in this file's own commit (a separate `claude/ui-c6a` follow-up may fix the blocker below; see the end of this file).

## Base and method

**Base:** `main` @ `4f79f76` ("Merge C5: leaderboard/results rhythm tightening and .segmented migration"). `4fcaa34`/`16ce49b` ("Discover reports for in-progress TEGs"), merged into `main` ahead of C5, is unrelated to this workstream and excluded from the reviewed diff — confirmed by scoping all diffs to `e50af5c..4f79f76 -- webapp/` (C1 merge → C5 merge).

**Reviewed:** `C1-handoff.md`, `C1b-handoff.md` (the approved spec — C1b authoritative where they diverge), `C3`/`C4`/`C5-handoff.md` (claims verified against source, not trusted), `design_principles.md`, `gpt-ui-review.md`, the full `base-vars.css`/`clean.css`/`dark.css` diff, template/route diffs, and `webapp/README.md`.

**Live verification:** local server (Python 3.12 venv, port 8131) driving three disjoint Sonnet subagent Playwright sweeps (standings/tables; latest-round/scorecard/player; nav/contents/scoring/token-focus), covering every public route named in the roadmap's scope × {320, 390, 430, 768, 1280}px × {light, dark} × {Clean Page, Clean Layered} — 380 combined page loads, all from fresh browser contexts. Every subagent finding was re-checked against source or re-measured directly before being included below; two were found to be misreadings and are corrected in **Stale or unsupported claims**. No eight-player TEG exists in the data (max is six, per C5's own prior finding) — the "widest available" checks used six-player TEGs, not eight, matching C5's precedent.

No merge, push, or deploy performed. No `streamlit/` or `teg_analysis/` file touched or read for editing.

---

## Blockers

### B1 — `/latest-round`'s Round/TEG-total toggle: C5 broke the neutral-toggle styling it was never told about

**What C5 removed:** `.measure-toggle`'s CSS block in `base-vars.css` (margin, plus track/thumb colour overrides), believing it was dead weight left over from the Leaderboard/Results Net-Gross toggle it had just migrated to `.segmented`. C5's handoff states: *"`.scale-switch` itself, `.switch-track`, `.switch-thumb` are untouched — still load-bearing for `/latest-round`'s Round/TEG-total and Normal-scale toggles (genuinely binary, correctly still switches)."*

**What's actually true:** `/latest-round`'s Round/TEG-total button (`partials/latest_round_tab.html`, class `scale-switch measure-toggle lr-total-toggle`) still carries the `measure-toggle` class — and its own inline template comment says exactly why: *"Round vs TEG total isn't a better/worse pair the way Normal/Vs-bogey scale arguably reads, so the default `.scale-switch` accent-on-checked look would wrongly imply one side is 'on'."* This is the same non-binary semantics as the Net/Gross toggle C5 correctly migrated — not the genuinely-binary case C5's handoff assumed. (`lr-scale-toggle`, the Normal/Vs-bogey control, does not carry `measure-toggle` and is unaffected — C5's claim is correct for that one control, wrong for the other.)

**Confirmed live** (`/latest-round?tab=scoreboard&round=2`, 1280px, light, Clean Page):
- `aria-checked="false"` (Round selected, the default): `.switch-track` background `rgb(255,255,255)`, `.switch-thumb` background `rgb(255,255,255)`, against a `rgb(255,255,255)` card. **Track and thumb are both white on a white card** — this is exactly the bug `design_principles.md`'s "Toggle switches: check the 'off' state" section documents and calls out as having "bitten the live site before... and again on the Leaderboard/Results Net-Gross toggle (`.measure-toggle`)." Only a 1px `rgb(208,208,208)` track border remains visible.
- `aria-checked="true"` (TEG total selected): `.switch-track` background `rgb(34,139,34)` (forestgreen/`--accent`) — the control now visually reads as a normal on/off switch with TEG-total "turned on," which is the exact wrong semantic the template's own comment says this toggle must avoid.
- The button's `margin: 0.25rem 0 1rem` also disappeared (computed margin now `0px`), a minor spacing regression on top of the colour one.

**Why this blocks I1:** it's a real, live, visible defect on a public route, reintroduced by this stage's own diff, that contradicts a documented rule the codebase already learned once. I1 is a rewrite of the standings renderer; shipping it on top of an already-regressed sibling control invites the same category of bug to resurface unnoticed a third time.

**Fix scope:** narrow and mechanical — restore `.measure-toggle`'s margin/track/thumb rule, scoped to (or including) `.lr-total-toggle` specifically, without reintroducing it as a live pattern for the already-migrated Leaderboard/Results control. Eligible for the C6a follow-up (see end of file).

---

## Non-blocking follow-ups

1. **`/history` player-name column overflows its cell by 7–25px** at 320/390px in Clean Layered specifically (Clean Page's narrower gutter avoids it at 390px; both layouts show it at 320px). The site's own `.names-break` two-line wrap mechanism (`mobile.css`, built for exactly this case — "Stuart NEUMANN") exists but doesn't fully contain "John PATTERSON" at Clean Layered's narrower content width. Contained inside the table (no document-level scroll); a candidate for the next History-focused pass, not urgent.
2. **Sitewide green focus ring** (`ui-polish.css`'s `:where(a,button,select,input):focus-visible`) remains on every control outside the five specifically fixed (`.tab-underline`, `.seg-option`, `.action`, plus the two more implied by C4). Confirmed live: plain `<a>` tags, `.nav-brand`, `.nav-link`/`.nav-dropdown-btn`, `.pp-back`, and `.pill`/`.pill--active` all still show `rgb(34,139,34)` (light) / `rgb(108,199,127)` (dark) outlines. Already flagged by C3/C4 as a deferred sitewide pass, not silently dropped — reconfirmed with exact colours, not a new finding.
3. **`.mode-toggle`/`.theme-select` use a *different* focus mechanism** than the outline-based fix above — a green `box-shadow` ring, not `outline`. Worth noting for whoever eventually does the sitewide focus pass: fixing `:focus-visible`'s `outline` colour alone won't touch these two controls, which need their `box-shadow` colour changed separately.
4. **`--focus` and `--ink` are the same token value**, per C1b's own flagged risk (§6) — reconfirmed still true in `clean.css`. Not a problem today (nothing needs to distinguish "this is ink" from "this has focus" simultaneously), but worth remembering if a future component needs both.

---

## Stale or unsupported claims

Two claims from the parallel Playwright sweeps did not survive verification against source and are corrected here rather than carried into the record:

- **`/contents`'s section headings are *not* the merged `.section-title`/`.card-header`/`.chart-title` rule.** One sweep reported them as "pixel-identical... confirming C3's merge is true for this class." In fact `/contents` uses its own bespoke `.contents-section-title`, defined inline in `webapp/templates/contents.html`'s own `<style>` block — Inter (not Lora), weight 600 (not 700), grey `var(--text-secondary)` (not green), never migrated into the C1/C3 heading system at all. The font-size happened to compute to the same 13px, which is what produced the false "identical" read. `/contents` was not in any C3–C5 files-changed list — this isn't a regression, it's a page the Consistent UI stage never touched. Correctly in scope for I3/I5 (`/contents` redesign), not a C6 blocker, but the record should say "not yet migrated," not "confirmed consistent."
- **`/latest-round`'s `lr-total-toggle` does not control Stableford vs Gross.** A sweep inferred this from the `aria-label="Score basis"`. The template (`partials/latest_round_tab.html`) confirms it toggles **Round vs TEG-total** (the chart/table's cumulative basis), unrelated to scoring method. This misreading is also what led to finding B1 above being independently re-derived and confirmed correct.
- **`.records-tabs`' internal `scrollWidth` "overflow" is not a bug.** A sweep flagged `.section-nav.records-tabs` overflowing its container by 300–414px at phone widths. `.section-nav` (`mobile.css`) is deliberately `overflow-x: auto` with a scroll mask and hidden scrollbar at ≤640px — the documented MOBILE_PLAN M1.5 "scrolls when the labels overflow" pattern. An inner element's `scrollWidth` exceeding its `clientWidth` is exactly what makes that scroll container work; it is not page-level overflow (which was independently confirmed clean, 0/80 failures) and not a defect.
- **The reported ~197px gap between `/leaderboard`'s tab row and its first table row is not a rhythm regression.** Direct re-measurement shows the true chain is: nav (bottom 329.5) → 16px gap (C5's fix, exact) → toggle-group (355–393) → 16px gap (toggle-group's own margin, C5's fix) → section-title (409–425.9) → champion/wooden-spoon callout (441.9–464.4) → 16px gap → table (480.4). The larger number one sweep measured was to a `tbody tr`, not the table's own top, and the intervening 150px is legitimate content (heading + facts rail), not slack. C5's two targeted spacing fixes both measure exactly as claimed.
- **Four intermittent `net::ERR_TIMED_OUT`/`ERR_CONNECTION_CLOSED` console entries** during one 80-load sweep, with no consistent route/theme pattern, are most likely Google Fonts contention from three concurrent Playwright sweeps hitting one dev server — not re-verified in isolation, and not treated as a finding.

---

## Open owner decisions (carried forward, unchanged)

1. **History's desktop disclosure affordance** — still no visible `+`/`−` above 640px (`.history-toggle-indicator`'s `::before` glyph is inside `mobile.css`'s whole-file `≤640px` scope). Open since C1b, restated by C3 and C4, untouched here.
2. **`.main-content` padding/radius** (C4 §3) — comparison delivered as screenshots, not applied. Owner decides.
3. **`bw-name-full`/`bw-name-short` site-wide rollout** — still wired up only for bestball/eclectic contribution bars.
4. **Bare `.teg-table tbody tr.top-rank`** on Records/History — still the flat pre-L2 colour, by design (leader-tint fix is Leaderboard/Results-scoped only).

---

## Ready / not-ready verdict for I1

**Not ready, pending B1.** Everything else checked — token consistency, control grammar, table contracts, hit areas, both Clean layouts in light/dark, generic-dashboard drift — held up under live verification, including two cases where the automated sweeps' own claims needed correcting rather than the underlying implementation. B1 is a confirmed, live, narrow defect with an obvious mechanical fix; once it's resolved (a small C6a-style follow-up, not a re-litigation of any C1–C5 decision), this stage is ready for I1 to begin.

---

## Screenshot manifest

Three representative captures committed to `screenshots/C6/` (390px and 1280px, light, Clean Page — the rest of the 380-load matrix was inspected via computed styles and pass/fail assertions, not archived, to keep this commit small):

- `leaderboard-390-light-clean-page.png`, `leaderboard-1280-light-clean-page.png` — `/leaderboard` GET, default TEG, light mode, Clean Page cookie, Chromium, viewport height 900.
- `results-1280-light-clean-page.png` — `/results` GET, same conditions.

## C6a — trivial fix applied

**B1 fixed** on a separate branch (`claude/ui-c6a`, based on `4f79f76`, not mixed into this review's commit) — see `webapp/design_reviews/ui_workstream/C6a-handoff.md` for the diff, verification, and resulting commit SHA.
