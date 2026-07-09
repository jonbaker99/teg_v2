# Portrait scorecard — implementation & merge-to-main plan

A self-contained work-package: add the **portrait (holes-as-rows) scorecard** to
the real architecture so it's reusable project-wide, and get it onto `main`.

It is deliberately **separable from the A-vs-B mobile-shell decision** (see
[MOBILE_PLAN.md](MOBILE_PLAN.md)): the builders + CSS are pure additions to the
shared layer and can merge to `main` on their own, ahead of the wider redesign.
Target look is set by the mockups in `mobile_mockups/` (`scorecard_app.html`,
`scorecard_teg_app.html`, `scorecard_field_app.html`).

---

## 1. Why this is its own work-package

- The portrait builders belong in the **UI-agnostic analysis layer**
  (`teg_analysis/display/`), so *any* client can use them — the webapp now, the
  planned **REST API** later, notebooks, etc.
- The logic exists today **only in the old architecture** and is UI-coupled:
  `streamlit/scorecard_utils.py` → `generate_single_round_html_mobile`,
  `generate_tournament_html_mobile`, `generate_round_comparison_html_mobile`.
  These must **not** be imported by `teg_analysis`/`webapp` (Streamlit is the
  frozen old layer) — they're the **parity reference**, nothing more.
- Most of the contract is already in place on the new side, so the port is small.

## 2. What already exists (don't rebuild)

| Piece | Location | State |
|---|---|---|
| Landscape builders (3 views) | `teg_analysis/display/scorecards.py` | ✅ `build_single_round_combined_table`, `build_tournament_gross_table` / `…_stableford_table`, `build_round_comparison_gross_table` / `…_stableford_table` — return HTML strings |
| Score-shape contract | both builders + `webapp/static/scorecard.css` | ✅ cells are `<td class="score-cell" data-vs-par="N">` / `data-stableford="N"`; CSS maps those to circles/squares/heat via `--color-eagle`, `--color-birdie`, `--color-stableford-*`, etc. (already CSS variables) |
| Route + view dispatch | `webapp/routes/scorecard.py` | ✅ `TYPE_ONE_ROUND_ONE_PLAYER` / `TYPE_ONE_PLAYER_ALL_ROUNDS` / `TYPE_ONE_ROUND_ALL_PLAYERS`, `_build_scorecard_context` |
| Partial | `webapp/templates/partials/scorecard_content.html` | ✅ renders the chosen view |
| Data fields | `teg_analysis` loaders | ✅ `Hole, PAR, Sc, GrossVP, Stableford` — the exact fields the portrait builders need |

**So the only genuinely new things are:** portrait *builders* (holes as rows),
portrait *CSS*, *dark-mode* colour tokens, and the *orientation switch*.

## 3. The data contract (unchanged)

Each view consumes the same DataFrames the landscape builders already take —
no new analysis/aggregation code:

- **Single round** (1 player × 1 round): 18 rows, `Hole, PAR, Sc, GrossVP, Stableford`.
- **Whole TEG** (1 player × all rounds): the per-round frames; render rounds as columns.
- **vs Field** (1 round × all players): per-player frames; render players as columns.

Cell rule (same as landscape): gross cell carries `data-vs-par="Sc-PAR"`;
Stableford cell carries `data-stableford="pts"`; OUT/IN/TOTAL are plain subtotal
cells. (Streamlit field-name → new field-name map is 1:1; the new builders
already use `Sc`/`GrossVP`/`Stableford`.)

## 4. Steps (each independently testable)

**Step 1 — Portrait single-round builder** ✅ **DONE.**
`build_single_round_combined_portrait(df) -> str` in
`teg_analysis/display/scorecards.py`: header `Hole · PAR · Gross · Stableford`,
one row per hole, `OUT/IN/TOTAL` rows, reusing the **same** `score-cell` +
`data-vs-par`/`data-stableford` contract.

**Step 2 — Portrait tournament + field builders** ✅ **DONE.**
`build_tournament_gross_portrait` / `…_stableford_portrait` (holes × rounds) and
`build_round_comparison_gross_portrait` / `…_stableford_portrait` (holes ×
players, columns ordered by gross total). Same data, transposed; same cell
contract. Tests in `tests/test_scorecards_portrait.py` assert **parity** with the
landscape builders (identical per-hole cells) plus correct subtotals and column
ordering. *(Note: full `pytest` run needs the project venv — pandas + streamlit +
PyGithub; the new builders were verified against these assertions in isolation.)*

**Step 3 — Portrait CSS** in `webapp/static/scorecard.css` (new `@media (max-width:640px)`
section per the MOBILE_PLAN breakpoint — desktop/iPad untouched). Holes-as-rows
layout; **reuse the existing shape tokens**. Add: the Gross/Stableford toggle
(pure-CSS radios — copy from the mockups, no JS) and, for the field view,
sticky `Hole`+`PAR` columns + horizontal scroll.

**Step 4 — Dark-mode tokens.** The scorecard colours are already CSS variables,
so dark mode = one override block (under the app's dark mechanism, MOBILE_PLAN
§4.2) re-pointing `--color-eagle/-birdie/-bogey/-stableford-*` + text colours to
dark-appropriate values (the mockups carry a validated dark palette). **Look
decision:** keep the current **amber** Stableford scale, or adopt the **green**
heat used in the mockups (ties Stableford to the app accent). 

**Step 5 — Webapp wiring.** Make the route render portrait under the mobile
breakpoint. Two options:
  - **(a) CSS-only:** render both orientations, show/hide by `@media` — simplest,
    no route change, but doubles the markup payload.
  - **(b) Server-picked:** add an `orientation` (or reuse a `layout`) param/cookie
    to `scorecard_page`/`scorecard_content` and the context dispatch — leaner
    payload, a little more plumbing.
  *Recommendation:* (b) for the field view (8 players × 2 tables is heavy),
  (a) is fine for single-round. Confirm before building.

**Step 3 — Portrait CSS** ✅ **DONE.** Added to `webapp/static/scorecard.css`,
scoped under `@media (max-width: 640px)` (desktop/iPad untouched): holes-as-rows
layout for `.scorecard-table-portrait`, pinned `Hole`+`PAR` columns + horizontal
scroll for the wide views, and the pure-CSS **Gross/Stableford metric toggle**
(`.sc-metric-toggle`). Reuses the existing `.score-cell` shape tokens.
Score columns use `table-layout: fixed` with an explicit width (~15% wider
than `--shape-size`, i.e. just past the circle/square) instead of `width:
100%` on the table — otherwise `table-layout: auto` stretched them to fill
whatever space was left, especially on narrow views (single round, few
rounds/players). A table narrower than its `.sc-scroll` wrapper now centers
via `margin: 0 auto`; wide tables (many rounds/players) still overflow into
horizontal scroll exactly as before.

**Step 4 — Dark-mode tokens** ✅ **DONE and live** (the app-wide `data-mode`
toggle shipped — see CLAUDE.md "Current state"). A `html[data-mode="dark"]`
override block re-points the scorecard colour variables for dark. Over-par
cells (bogey/double-bogey/triple-bogey+) use a blue shade progression
(`#234668` → `#2f6db3` → `#4da3ff`, mirroring light mode's grey→black
intensity ramp) instead of light mode's grey/black, which read as
black-on-black against the dark background. Birdie is a solid white circle
(`--color-birdie: #ffffff`) with the same red outline/font as light mode
(`--color-text-birdie: #dc1a21`), replacing the previous dark, low-contrast
reddish fill. Eagle is unchanged. Stableford stays on the **amber** scale
(see §6). Verified in-browser (Chromium, phone viewport, light + dark, single
round / whole TEG / field views).

**Step 5 — Webapp wiring** ✅ **DONE, verified in-browser.**
`routes/scorecard.py` builds the portrait HTML alongside landscape for all three
views; `partials/scorecard_content.html` renders both, wrapped in `.sc-landscape`
/ `.sc-portrait`, and the CSS shows the right one by breakpoint. *Static checks
pass (py_compile, Jinja parse, CSS-comment guard); rendered and screenshotted
in Chromium (single round / whole TEG / field views, light + dark, phone
viewport).*

**Step 6 — Tests, parity, a11y.** Builder parity tests ✅ done
(`tests/test_scorecards_portrait.py`). Dark contrast spot-checked visually
(blue over-par shades + white/red birdie clearly readable against the dark
background). Still to do: formal AA contrast check; keyboard/scroll behaviour
for the field table.

**Step 7 — Docs.** ✅ `teg_analysis/README.md`, `webapp/README.md`, and the
MOBILE_PLAN §6 cross-link updated. `streamlit/` untouched.

## 5. Merge-to-`main` strategy

- **PR 1 — shared layer (Steps 1–4, 6, 7-partial).** Portrait builders + portrait
  CSS + dark tokens + tests. **Pure additions**; no dependence on the A/B shell
  decision. Mergeable to `main` first and immediately usable by the future REST
  API and any client. `streamlit/` not touched.
- **PR 2 — webapp wiring (Step 5).** Depends on the breakpoint/orientation choice;
  can ship as an explicit "Portrait" view selector even before the full mobile
  redesign, so it's independently releasable too.

Keeping PR 1 free of webapp-shell coupling is the whole point: the reusable
asset (builders + visual contract) lands on `main` regardless of where the
A-vs-B look-and-feel conversation ends up.

## 6. Decisions (resolved — best-practice defaults)

1. **Builder return type:** **HTML string** — matches the existing landscape
   builders. Revisit only when the REST API needs structured data.
2. **Orientation switch:** **CSS-only** — render both, toggle at `≤640px`. No JS,
   and desktop/iPad cannot be affected (they only ever see landscape).
3. **Stableford palette:** **keep amber** — changing it would alter desktop
   scorecards too (breaks "don't impact laptop"); consistency over accent-tie-in.
4. **Default on mobile:** **portrait is the default** under 640px, landscape
   above it.

> **Resolved:** dark mode is live (app-wide `data-mode` toggle shipped), and the
> wired webapp views have had a real in-browser pass (§Step 5/6 above).

## 7. Model-tier guide (per CLAUDE.md)

- Builder ports (Steps 1–2), CSS (Step 3), dark tokens (Step 4): **Sonnet** (moderate).
- Architecture decisions (§6 items 1–2), final review gate: **Opus**.
- Doc updates (Step 7): **Haiku/Sonnet**.
