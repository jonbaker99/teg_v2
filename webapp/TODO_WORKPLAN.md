# Webapp to-dos — work plan (2026-07-10)

Temporary working doc (delete/consolidate when done — CLAUDE.md doc rule 3).
Source: Jon's notes, reviewed against the code. Each item lists the tier
(Opus / Sonnet / Haiku per CLAUDE.md Model Selection), the exact files, the
approach agreed, and acceptance criteria. Work in batch order; run the Opus
review gate at the end of each batch (read modified files, grep for callers,
`python -m pytest tests/ -v`).

**Clarifications already answered by Jon (don't re-ask):**
- Eclectic player ranks: **both** vs own history **and** vs all players all-time, in a **separate table** (separate from the scorecard/contribution bars).
- Distributions: chart should follow the Percentage/Count toggle; in % mode overlay an "all players" team-average mark per score category.
- Slow pages are slow on **every** load, not just cold start → per-request recomputation is the target, not warmup.

---

## Batch 1 — Quick fixes (Sonnet; Haiku for 1.2 & 1.4 if run separately)

### 1.1 `nan` shown in tables → render `-`  (Sonnet)
Seen on `/scoring/by-teg` (pivot of GrossVP by TEG × Player: players who missed
a TEG produce NaN → `str(val)` → literal `nan`).

- **Fix centrally** in `webapp/tables.py::df_to_html` (webapp/tables.py:68-74):
  before building `cell_html`, treat missing values as `-`:
  ```python
  if pd.api.types.is_scalar(val) and pd.isna(val):
      cell_html = "-"
  ```
  (the `is_scalar` guard keeps list-valued cells safe with `pd.isna`).
- This fixes by-teg and any other page rendering NaN through the shared
  renderer. Do **not** also fillna in `scoring_by_teg_page` — one fix, one place.
- Check other pages don't rely on the string `nan` (grep templates/routes for
  `'nan'` — none expected).
- **Accept:** `/scoring/by-teg` table shows `-` where a player has no TEG;
  test suite passes. Add a small unit test for `df_to_html` NaN handling in
  `tests/` alongside any existing tables tests.

### 1.2 `/scoring/by-par` table too cramped  (Haiku-able, CSS only)
Route `webapp/routes/scoring.py:281`; template `webapp/templates/scoring_by_par.html`
renders `partials/scoring_matrix_content.html` (a plain `teg-table`) into
`#bp-content`. The partial is **shared with `/scoring/matrix`**, so don't style
the partial itself — scope to the page:

- Add a wrapper class in `scoring_by_par.html`: `<div id="bp-content" class="section-panel by-par-panel">`.
- In the webapp stylesheet where page-scoped table tweaks live (follow the
  existing pattern in `webapp/static/` — e.g. base-vars.css / a page css already
  loaded by base.html; do NOT create a new stylesheet), add:
  `.by-par-panel .teg-table th, .by-par-panel .teg-table td { padding-left/right: ~14px; }`
  and optionally `white-space: nowrap;` — enough that columns breathe on desktop.
- **Accept:** by-par table has visibly wider columns; `/scoring/matrix` is
  unchanged; no horizontal scroll on a laptop viewport for the by-par table.

### 1.3 `/scoring/distributions` — Display toggle doesn't affect the chart + team-average marks  (Sonnet)
`webapp/routes/scoring.py:761-834`: the table respects `mode`, but the chart is
hard-coded to counts (`chart_table = prepare_score_count_display(count_data, ..., False)`
at scoring.py:792). Agreed behaviour:

- Chart follows the toggle: in Count mode plot counts (as now); in % mode plot
  each player's percentage distribution (reuse the same `display_data` the
  table uses, i.e. count ÷ column total × 100).
- **% mode only:** overlay an "All players" mark per score category — a
  horizontal line/tick across each bar group, **not** a bar. Compute the
  combined distribution from `filtered` (TEG + par filters applied, player
  filter NOT applied), as pct of all holes. Implement as a `go.Scatter` trace,
  `mode='markers'`, `marker=dict(symbol='line-ew-open', size=~26, line_width=2)`,
  name `All players`, drawn after the bars so it sits on top. Y-axis title
  becomes `% of holes` in % mode.
- Pass `mode` (and the all-players series) into `_distributions_chart`
  (scoring.py:718) rather than computing inside; keep the existing
  swallow-to-None error handling.
- Only applies to the "By Player" tab (the chart isn't rendered on By TEG).
- **Accept:** toggling Display re-renders the chart between counts and
  percentages; % mode shows the All-players ticks; a single-player selection
  in % mode shows that player's bars vs the team ticks; Count mode has no ticks.

### 1.4 Eclectic scorecard — birdie circle too tight  (Haiku-able, CSS only)
`webapp/static/scorecard.css`. The circle is the `::before` shape on
`.score-cell[data-vs-par="-1"]` sized by `--shape-size-birdie` (scorecard.css:228-239);
the complaint is on the eclectic/bestball team rows (`.eclectic-scorecard` /
`.bw-scorecard` context) where the `-1` text nearly touches the ring.

- Preferred fix: scoped override, e.g.
  `.eclectic-scorecard { --shape-size-birdie: <current + ~3-4px>; }`
  (check the `--shape-size*` var definitions at scorecard.css:40-78 and the
  bw/eclectic overrides near scorecard.css:778-856 — there's already an
  eclectic-context birdie override block there; put the size change with it).
  If the bigger circle collides with cell borders, shrink the cell font in the
  same scope instead. Keep eagle visually ≥ birdie.
- Verify in BOTH light and dark modes (dark overrides at scorecard.css:460ish)
  and on the portrait/mobile scorecard, which resizes shapes.
- **Accept:** visible breathing room between the digit and the ring on
  `/latest-teg` → Eclectic and the bestball tab, light + dark, no layout shift
  in the standard scorecard pages.

**Batch 1 gate:** Opus review + full test run. Commit per item or as one
"quick fixes" commit.

---

## Batch 2 — Performance (diagnosis CONFIRMED by Opus 2026-07-10; Sonnet implements)

Jon confirmed slowness is on **every load**. Timings taken with all webapp
caches warm (so this is pure per-request compute, not data loading):
- **Scorecard context: ~0.26s/request.** Locally `load_all_data` is only ~12ms
  of that, but on Railway the data is a mounted volume where each per-request
  read is far slower — this is why it's "slow on every load" in prod but barely
  shows locally. Fix (2.1) is still correct and cheap.
- **Player overview context: ~1.7–1.9s/request**, all caches warm. Profiled:
  `_records_held` (~1.5s) + `_worsts_held` (~1.5s) are essentially the entire
  cost. Both build **player-independent global tables** (`prepare_records_table`
  / `prepare_worst_records_table` over the three ranked datasets, plus
  `prepare_record_best/worst_streaks_data` and `prepare_score_count_records_table`)
  and only then filter rows to the one player — so the whole global computation
  is redone on every request and for every player.

**Decided caching boundary (2.2):** cache the six global artifacts (not the
per-player context), keyed by nothing, cleared via `register_cache_clearer`.
That makes even the first visit to each player fast and maximally helps the
roster landing page. NOTE: `register_cache_clearer` exists in `deps.py:41` but
is currently UNUSED — player.py will be its first consumer (the winners cache
lives in deps.py, not player.py, contrary to an earlier note).

### 2.1 `/scorecard` slow  (root cause found — Sonnet)
`teg_analysis/core/metadata.py::get_scorecard_data` (metadata.py:105-135) calls
**`load_all_data()` uncached on every request** — a full parquet read + all the
loader's derivation work, per page view and per HTMX control change. The
webapp already holds the identical frame in `webapp/deps.py::cached_load_all_data`
(same flags: `exclude_teg_50=True, exclude_incomplete_tegs=False`).
`get_teg_metadata` also re-reads `round_info.csv` per request (cheap by
comparison; fix only if timings say otherwise).

- **Fix:** add an optional `data: pd.DataFrame | None = None` parameter to
  `get_scorecard_data`; when provided, filter it instead of calling
  `load_all_data()` (keeps teg_analysis UI-agnostic — no webapp import).
  Update **all webapp callers** to pass `cached_load_all_data()`:
  `webapp/routes/scorecard.py` (3 context builders) and
  `webapp/routes/latest.py` (scorecard tab, latest.py:318; grep for other
  `get_scorecard_data(` callers — leaderboard/results inline scorecards use it
  too). Streamlit does not import this module's new param path — do not touch
  `streamlit/`.
- **Accept:** timed locally, `/scorecard` and `/scorecard/content` drop the
  per-request `load_all_data` cost (should go from ~seconds to ~tens of ms
  after first load); tests pass; `teg_analysis` still has no webapp/streamlit
  imports.

### 2.2 `/player` pages slow  (diagnosis to confirm — Opus decides caching boundary, Sonnet implements)
`webapp/routes/player.py` uses cached frames, so the cost is per-request
compute. Suspects, in likely order (confirm with timings):

1. `_build_overview_context` (player.py:667) loops every TEG the player played
   and calls `_compute_teg_ranks(teg_num, rd_data)` per TEG — each call
   recomputes full leaderboards for that TEG. ~18 TEGs × every page view.
2. `_records_held` / `_worsts_held` build `prepare_records_table` over three
   ranked datasets per request (player.py:263-265, 349-351).
3. `_metric_specs`, `_build_highlights`, `_build_overview_metrics`, and the
   roster landing page computing per-player card stats for all players.
4. Two Plotly figs per overview (cheap-ish; ignore unless timings disagree).

- **Fix pattern (already established in this file):** module-level
  `lru_cache`d helpers registered with `deps.register_cache_clearer` (see the
  existing winners cache in player.py) so a data update clears them.
  Candidates: `_compute_teg_ranks` keyed by `teg_num` (it's
  player-independent — returns a per-player dict); the records/worsts tables
  keyed by nothing (they're global); per-player overview context keyed by
  `player_code` if the above isn't enough. Opus picks the smallest set that
  gets p95 under ~300ms server-side; don't cache the whole rendered context
  unless needed.
- **Accept:** timed before/after on `/player` and `/player/{code}`; caches
  cleared by `clear_all_data_caches()` (verify via
  `deps.register_cache_clearer` registration, and that an add-round admin flow
  still refreshes player pages); tests pass.

**Batch 2 gate:** Opus review; include before/after timings in the commit message.

---

## Batch 3 — Latest-TEG Eclectic enhancements (Opus designs, Sonnet implements)

Goal: make `/latest-teg` → Eclectic mirror the bestball "round in context" tab
(`webapp/routes/latest.py:330-365`). The rank summary line already exists
(latest.py:547-554). Add, in order below the summary:

**Opus design (2026-07-10), decided — implement exactly:**

### 3.1 Player ranks table (separate table — per Jon)
New analysis in `teg_analysis/analysis/eclectic.py` (UI-agnostic; compute
directly, don't reuse the pivot helper):

```python
def eclectic_player_teg_totals(data):
    """One row per (Player, TEGNum): the player's eclectic total for that TEG
    (sum over holes of their per-hole minimum GrossVP within the TEG)."""
    per_hole = data.groupby(['Player','TEGNum','Hole'])['GrossVP'].min().reset_index()
    return per_hole.groupby(['Player','TEGNum'])['GrossVP'].sum().reset_index(name='Total')

def rank_teg_eclectics(data, teg_num, complete_teg_nums=None):
    """For each player who played teg_num, their eclectic Total plus two ranks:
      - all-time: Total vs the pool of ALL player-TEG eclectic totals
      - own-history: Total vs that player's own per-TEG totals
    Ranks use 'min' (ties share the lower rank). If complete_teg_nums is given,
    the all-time POOL is restricted to those TEGs (see completeness rule below);
    the player's own-history pool is NOT restricted (a player's own progression
    is comparable regardless). Returns DataFrame with columns:
    Player, Total(int), AllTimeRank(int), AllTimeN(int), OwnRank(int), OwnN(int).
    Lower Total is better; ascending rank."""
```
- **Completeness rule (decided):** the route passes
  `complete_teg_nums = set(cached_complete_teg_data()['TEGNum'])`. All-time pool
  = player-TEG totals whose TEGNum is complete. Rationale: an in-progress TEG
  has fewer rounds, so its eclectic is systematically worse and not comparable
  to 4-round TEGs. This is simpler and more correct than trying to normalise.
- **In-progress caption (decided):** if the displayed `teg_num` is NOT in
  `complete_teg_nums`, the route adds a caption: "TEG N is still in progress —
  its eclectic will improve as more rounds are played; all-time ranks compare
  only completed TEGs." (Still show the row; the current TEG's own total is
  always included for the player's own-history rank.)
- Render in the eclectic tab context (latest.py:529-563) via
  `webapp/tables.py::df_to_html`, `link_players=True`. Display columns/labels:
  `Player | Eclectic | All-time | Own history`, where Eclectic uses
  `format_vs_par(Total)`, All-time shows `f"{AllTimeRank} / {AllTimeN}"`,
  Own history shows `f"{OwnRank} of {OwnN}"`. Build the display DataFrame in the
  route (keep the analysis function returning raw ints).

### 3.2 Contribution by player (bestball-style CSS bars)
New analysis in `teg_analysis/analysis/eclectic.py`, mirroring
`calculate_player_contributions` (`teg_analysis/analysis/bestball.py:58`) but
over a whole TEG using each player's personal eclectic per hole:

```python
def calculate_eclectic_contributions(teg_data):
    """Per-player contribution to a TEG's team eclectic. For each player:
      - holes:  holes where their personal eclectic (min GrossVP over their
                rounds that hole) equals the team eclectic (min over ALL
                players/rounds that hole) — i.e. the highlighted cells on the
                eclectic scorecard.
      - solo:   of those, holes where they are the ONLY player whose personal
                eclectic reaches the team value.
      - impact: signed shots contributed = (team eclectic total WITH player)
                minus (WITHOUT). Only moves on solo holes; equals
                sum over solo holes of (team_value - second_best_personal_ecl).
                <= 0 (shots the player saved the team).
    Returns one row per player: columns ['Pl','Player','ecl_holes','ecl_solo',
    'ecl_impact'] (int). Row order follows input player order."""
```
- Note the difference from bestball: value per (player, hole) is the player's
  *personal eclectic* (min over their rounds), not a single round's score.
  Compute personal eclectics once (`groupby(['Pl','Hole'])['GrossVP'].min()`),
  the team eclectic per hole (`groupby('Hole')['GrossVP'].min()`), then apply
  the same holes/solo/impact logic as bestball over those personal-eclectic
  values.
- HTML builder `build_eclectic_contribution_bars(teg_data)` in
  `teg_analysis/display/scorecards.py`, adapted from
  `build_bestball_contribution_bars` (scorecards.py:777) but a SINGLE table
  (not the best/worst pair), reusing the existing `bw-bars-*` CSS classes and
  `_holes_bar`/`_impact`/`_player_name_spans` helpers. Columns: Player | Impact
  | Holes. Sort by |impact| desc (biggest savers first), then input order.

### Eclectic tab assembly (latest.py:529-563)
Order below the existing rank-summary line (latest.py:547-554):
1. rank-summary line (exists)
2. **3.1 player ranks table** (new)
3. eclectic scorecard `build_teg_eclectic_scorecard` (exists)
4. **3.2 contribution bars** (new) + a caption explaining Holes/Solo/Impact,
   modelled on the bestball caption (latest.py:351-361).

- **Accept (whole batch):**
  - Cross-check by hand against one TEG's eclectic scorecard: the dark-green
    highlighted holes per player (`_bw_player_cell` highlight in
    `build_teg_eclectic_scorecard`) must equal that player's `ecl_holes`; solo
    holes are those where exactly one player is highlighted; impact signs are
    all <= 0.
  - Unit tests in `tests/` for BOTH new analysis functions using a small
    synthetic multi-round TEG frame (assert totals, ranks incl. a tie, and a
    hand-computed solo/impact case).
  - In-progress path: pick an in-progress TEG (or simulate one) and confirm the
    caption appears and all-time N counts only complete TEGs.
  - `python -m pytest tests/ -v` green; no webapp/streamlit imports in
    teg_analysis.

**Batch 3 gate:** Opus review (esp. the in-progress-TEG ranking rule and
impact definition) + tests.

---

## Batch 4 — Multi-player chart series highlight on hover (Sonnet)

All Plotly charts render through one centralised renderer in
`webapp/templates/base.html` (~line 312: `.chart-container[data-figure]` →
`Plotly.newPlot`). Implement once there so every multi-series chart gets it.

- After `newPlot`, if `fig.data.length > 1`:
  - **Legend hover** (primary trigger — works with `hovermode: 'x unified'`,
    which most charts use and where per-point trace hover is meaningless):
    plotly.js has no legend-hover event, so attach DOM `mouseenter`/`mouseleave`
    listeners to the rendered legend groups (`.legend .traces` `<g>` elements;
    index order matches trace order). On enter: `Plotly.restyle(el, {opacity: 0.25}, otherIndices)`
    (hovered trace stays 1); on leave: restore all to 1. Re-attach after any
    `Plotly.newPlot` (HTMX swaps re-run the renderer already).
  - **Plot-area hover:** only for charts NOT in unified hover mode, use
    `el.on('plotly_hover', ...)` with `points[0].curveNumber` for the same
    restyle, and `plotly_unhover` to restore. Skip when layout.hovermode
    starts with 'x' to avoid flicker.
- Keep it dependency-free vanilla JS in the same `<script>` block; guard
  everything so a failure degrades to no-highlight (never a broken chart).
- **Accept:** on `/scoring/by-teg`, `/scoring/distributions`, leaderboard race
  charts, hovering a legend entry dims the other series and restores on leave;
  single-trace charts (player trend bars) are untouched; HTMX tab swaps keep
  the behaviour; no console errors.

**Batch 4 gate:** Opus review; manual spot-check across 3+ chart pages,
light + dark.

---

## Suggested execution order

1. Batch 1 (fast wins, independent) → review gate
2. Batch 2.1 (found root cause, biggest UX win) → 2.2 → review gate
3. Batch 4 (self-contained JS) — can run any time
4. Batch 3 (largest; needs Opus design first) → review gate

When all batches land: fold the outcome one-liners into `webapp/TODOS.md`,
update CLAUDE.md "Current state" if warranted, and **delete this file**.
