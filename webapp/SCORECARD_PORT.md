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

**Step 1 — Portrait single-round builder** in `teg_analysis/display/scorecards.py`.
`build_single_round_portrait(df) -> str`: header `Hole · PAR · Gross · Stableford`,
one row per hole, `OUT/IN/TOTAL` rows. Reuse the **same** `score-cell` +
`data-vs-par`/`data-stableford` contract. Unit-test: every cell value equals the
landscape builder's for the same TEG/round (it's a transpose).

**Step 2 — Portrait tournament + field builders.**
`build_tournament_portrait(...)` (holes × rounds) and
`build_round_comparison_portrait(...)` (holes × players), each emitting a Gross
table and a Stableford table. Same data, transposed; same cell contract.

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

**Step 6 — Tests, parity, a11y.** pytest for the three portrait builders
(values match landscape + match the Streamlit mobile reference numbers); dark
contrast check (AA); keyboard/scroll behaviour for the field table.

**Step 7 — Docs.** Update `teg_analysis/README.md` (new display functions),
`webapp/README.md` (portrait view), and cross-link this file from MOBILE_PLAN §6.
Leave `streamlit/` untouched.

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

## 6. Decisions to confirm before coding

1. **Builder return type:** HTML string (matches the existing landscape builders
   — fastest, consistent) vs structured rows (cleaner for the REST API).
   *Default:* HTML now; revisit when the API is built.
2. **Orientation switch:** CSS-only show/hide vs server-picked param (Step 5).
3. **Stableford palette:** amber (current) vs green (mockup).
4. **Default on mobile:** is portrait the *default* under 640px, or an opt-in view?

## 7. Model-tier guide (per CLAUDE.md)

- Builder ports (Steps 1–2), CSS (Step 3), dark tokens (Step 4): **Sonnet** (moderate).
- Architecture decisions (§6 items 1–2), final review gate: **Opus**.
- Doc updates (Step 7): **Haiku/Sonnet**.
