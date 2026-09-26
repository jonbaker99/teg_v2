# STATUS

Current state and next priorities. Instructions and architecture live in `CLAUDE.md`; outstanding items live in `TODOS.md`.

**Last updated:** 2026-09-26 (Records stacked list; honours board restyle)

## 2026-09-26 — Mobile records show full names

Every `/records` tab, on phones and desktop, now uses one stacked layout (the desktop table is gone): record label and value on top, then each holder's full name with their occasion(s) in muted text. Details sit beside the name when every row fits; otherwise all drop below their names. TEG, Round and 9-Hole labels drop "Best"/"Worst", since the section heading says it. Score Counts and Streaks hide records below 2. Holders of one record share a group with no rules between them. Streak locations read in plain words, e.g. "TEG 7, R1 H8 to R2 H12", or "to date" for a live streak; this also shows wherever record streaks appear (Scoring, player pages).

## 2026-09-26 — Honours board restyle and aligned mobile tab rows

Each `/honours` tab has a section heading, such as "TEG Trophy wins". Trophy, Green Jacket, Wooden Spoon and Doubles use full-width fixed-column tables on mobile with bold win counts and wrapping TEG lists. They have no leader shading, zebra striping or shortened names. Eagles and Holes in One are a plain list: bold name, then date and course, then TEG, round and hole. Across the site on mobile, tab rows now line up with the page title: the hidden scroll arrow no longer takes up space, and the first tab's underline starts at its text. Dark mode is unchecked.

## 2026-09-25 — Shared scorecard options

Standalone Scorecard filters are grouped in a collapsible “Scorecard options” box; Results and Leaderboard show their filters directly on the page. Gross/Stableford stays beside the card. Results and Leaderboard replace stacked rounds with the same controls for one round/all players or all rounds/one player. Small breaks after the header, OUT and IN make portrait cards easier to scan. Header and OUT rules are removed; spacing separates those sections.

## 2026-09-25 — Mobile scorecards use available width

Scorecards on Results, Leaderboard, Latest Round and Scorecard now scale their square score marks and text within bounded sizes. Equal row/column gaps keep the grid regular; sparse cards stop growing and dense cards retain horizontal scrolling with pinned Hole/Par columns. Existing score colours and symbols remain. Gross/Stableford selectors have consistent spacing before the card. Mobile View has its own row with clearer labels, dropdowns use consistent sizing, and section spacing replaces the header and OUT rules. Clean Layered is mothballed; Clean Page is the active layout for routine UI verification.

## 2026-09-22 — Landing-page links open individual report stories

Landing-page lead and secondary headlines link directly to their report stories. Desktop scrolls to the selected article; mobile opens it in the reader. Full-report links still open the report front page. The same story remains selected when switching between desktop and mobile layouts.

## 2026-09-22 — Tighter home headline and quieter honours

The landing headline uses a tighter 1.2 line-height. Champion and its winner use primary text; Green Jacket and Wooden Spoon labels and winners use secondary grey, with theme-aware dark-mode colours.

## 2026-09-22 — Gross comparison on the landing page

The main standings table adds Gross as the final metric column after Points (net vs par before TEG 8). Gross totals are versus par, signed including +0, and regular weight so the net competition remains primary. Mobile names stay on one line when they fit; the shared name-wrapping fallback applies only when space requires it.

## 2026-09-22 — Completed landing-page honours and panel links

Completed standings show matte gold trophy, green star and wood-brown spoon icons beside their winners. The Full Results and View full report links sit at the bottom left of their cards, aligned with the content. Landing-page link arrows use ↗. Honour icons sit close to the names, vertically centred, and use lighter shades in dark mode for visibility.

## 2026-09-22 — Landing page handicap links follow tournament state

The landing page names the current TEG in its handicap link while play is in progress, and the next TEG once complete. This also works without a report or future tournament metadata. The “Next:” line uses primary text (black in light mode); the handicap link uses secondary grey.

## 2026-09-22 — Report "Sidebar" badges replaced with real topics

The newspaper-style report badge above a story's headline (`JON BAKER`, `GREEN JACKET`,
`STADIUM COURSE`) is meant to name the story's actual subject. 17 report-page badges and every
Contents-page "Also in this report" teaser still showed the machine slot name `SIDEBAR`. Fixed:
the Contents teaser now reads the same `descriptor` field the report page shows (it was reading
the bare `kicker`); a literal `descriptor: "SIDEBAR"` on a mandatory Trophy/Jacket/Spoon/race
story now falls through to that story's real kicker instead of printing the machine name; and 7
genuinely mixed-subject or course stories that predated the `descriptor` field were hand-given a
real theme (`STADIUM COURSE`, `THE RECORD BOOK`, `BLOW-UP HOLES`, etc.). Future reports can no
longer produce `SIDEBAR` as a badge — see `teg_analysis/reporting/README.md` → "Story descriptor
badges". PDFs for the 15 affected editions rebuilt.

## 2026-09-22 — Readable dark newspaper reports

`/teg-reports` now has a warm dark palette: cream headlines, readable secondary text, brighter green accents and quieter rules. It covers the mobile front page and article reader, plus desktop and round editions. Light styling and PDF build inputs are unchanged.

## 2026-09-22 — Plain Contents expander label

The landing page sitemap expander now reads “Full site contents (click to expand)”, replacing the promotional wording and page-count blurb.

## 2026-09-22 — Phone Explore navigation

Phone bottom navigation now has **Latest · History · Records · Cards · Explore**. The phone hamburger and Explore open the same native all-pages dialog, driven by `NAV_SECTIONS`; tablet and desktop navigation keep their existing behaviour.

Verified with focused server-render tests and Playwright checks at phone, tablet and desktop widths.

## 2026-09-22 — Latest Round/TEG streak labels show inclusive thresholds

The Streaks tabs on `/latest-round` and `/latest-teg` now label their inclusive score rows `⩽Birdie`, `⩽Par`, and `⩽Bogey`. This makes clear that better scores count in each streak.

Verified with the focused pivot-label test and both Streaks-tab route tests.

## 2026-09-22 — Mobile pass: control convergence, Records/Scoring columns, collapsible scorecards

Branch `claude/loving-goodall-ge1foo`. Not yet merged. Phone-width fixes across
`/latest-teg`, `/latest-round`, `/leaderboard` and `/results`.

Latest TEG's metric row was styled by nothing — the template had migrated to
`.segmented` while `mobile.css` still targeted the old `.metric-grid`/
`.metric-pill` classes, so four long labels wrapped inside a content-sized bar.
Both pages' metric rows now share `.segmented` plus a new `.segmented--grid`
phone modifier (even two-column grid below 640px, inert above), and Latest
Round's scoring pills moved to the same segmented grammar. `.metric-grid`/
`.metric-pill` is retired as a control.

Records & PBs no longer renders `G.Par`/`N.Par`: `_build_records_html` was
running the player-name abbreviator over a column that holds metric names in
the Personal Bests and Personal Worsts sections. Gated behind a new
`identity_is_player` flag that defaults to the old behaviour, so `/records` is
unchanged. First column gained a left margin and the final column is now
left-aligned.

The Scoring table's first column showed the raw pandas index name (`GrossVP`/
`Stableford`); it now reads `Score` in both views at every width, and gained a
left inset on phones. Latest TEG's aggregate expander fits all round tiles on
one row; Latest Round's Out/In pair stays two-up. Latest TEG alone now defaults
to Stableford, ordered Stableford / Gross vs Par / Score / Net vs Par — Latest
Round keeps its order and `Sc` default.

`/leaderboard` and `/results` Scorecards now have one page-level
Gross/Stableford selector instead of one per round, and each round sits in a
collapsible container (Round 1 open, the rest collapsed) — both phone-only.
Rounds render `open` server-side, so desktop and the no-JS path are unchanged.

Two changes are deliberately visible at all widths: the `Score` header, and
Latest Round's metric and scoring controls becoming segmented.

Verified: full suite 754 passed, 23 skipped; the one failure
(`test_agent_handoff.py`, `FileNotFoundError: 'zsh'`) is a container
limitation, unrelated. `check_css_comments.py` and `check_pandas_compat.py`
clean.

**Next:** owner review on a phone, then merge decision.

## 2026-09-21 — Public HTMX loads no longer move or fade the page

Branch `codex/nonintrusive-loading`, based on `1f96cc1`. Not yet merged.

Routine public GET requests now keep the confirmed view visually unchanged while loading. The in-flow `Loading view…` banner and busy-panel opacity were removed; `aria-busy` and the progress cursor remain. Real failures still preserve the prior view and URL and show Retry/Dismiss. Retrying keeps that error stable in place and disables repeat clicks until success or failure.

## 2026-09-22 — I5 revision 2: full leaderboard on complete state + collapsible sitemap

Merged to `main` and pushed. Two further owner requests via five more prototype rounds
(`https://claude.ai/artifact/UD49p88BHCfBTTNH4GRstz`, now v11): the sitemap is now a native
`<details>` disclosure, closed by default with a signpost naming the real page count/groups
(reopens the "always visible" decision); and the complete state gets the same two-panel richness
as in-progress — a compact honours line, then real final standings (left) next to "Also in this
report" secondary headlines (right), reopening the "no full standings on complete" decision.

Both states' standings now share one `_standings_table_context()` helper and defer to
`GET /contents/panel` (only the complete-state headline, whose text depends on report
availability, stays synchronous). `get_edition_summary()` gained `other_articles`; the shared
standings-table partial gained an optional unit-aware header (`"Points"`/`"vs Par"`).

Caught and fixed three real CSS bugs via an automated 24-combination overflow sweep before
shipping: a specificity mismatch that let equal-width columns beat the phone-width single-column
override; a classic CSS Grid non-shrinking-item overflow; and a table narrowly too wide at 320px,
fixed with the site's standard `overflow-x:auto` wrapper. Zero overflow across the full matrix
after fixes. `pytest tests/ -v` — 769 passed. Full detail:
`webapp/design_reviews/ui_workstream/I5-handoff.md` → Revision 2.

## 2026-09-22 — I5 revision: real standings + report-led headline on Contents

Same branch/worktree as the 2026-09-21 entry below (`claude/ui-i5`). The owner reviewed the
shipped page and found it "too thin" — leader names only, no real content. Compared against
Codex's independent, never-merged `codex/contents-home-proposals` plan, adopted selectively via
an approved interactive prototype (`https://claude.ai/artifact/UD49p88BHCfBTTNH4GRstz`).

In-progress now shows a real net-competition standings table (every player, ties as genuine
duplicate rows) plus a compact gross-competition line, two-column (≥900px) next to a round-report
teaser when one exists — reusing I1's `_standings_rows()`/`_standings_table.html` directly rather
than a second renderer. Complete state: when a tournament report exists, its own headline becomes
the page's h1 (linked to the report), with a `TEG N results | Area | Month Year` dateline; falls
back to the original "TEG N — Final Results" treatment, unchanged, when no report exists.

New `get_edition_summary()` (`teg_analysis/reporting/newspaper_edition.py`, `@lru_cache`) makes
this affordable — full artefact-parse cost once per process, free after. In-progress rich content
now always defers to `GET /contents/panel` (dropped the old cache-warmth branching); the complete
state's report resolves synchronously, since its headline determines the page's own h1 and
deferring it would flash.

Verified against real data throughout (TEG 18's actual report headline renders correctly), full
`pytest tests/ -v` (766 passed), 24-combination browser matrix (320–1280px × both Clean layouts ×
light/dark), zero overflow. Full detail, three bugs caught and fixed pre-commit, and the prototype
iteration history: `webapp/design_reviews/ui_workstream/I5-handoff.md` → Revision.

## 2026-09-21 — UI implementation roadmap Improve stage: I5 Contents as the current-TEG home

Originally branch `claude/ui-i5`, based on `6218c0c` (main tip, I1+I2 merged); merged to `main`
2026-09-22 after two further revision rounds (see above).

`/contents` (the site's de facto home via `/` → `/contents`) replaces its flat three-column link
grid with a state-led panel — implementing the I3 product contract with I4's critique folded in,
plus three owner decisions taken live: the TEG report is the primary action in the complete state
(Full Results secondary, or primary itself when no report exists yet); a cold parquet-cache miss
defers State 1's leader rows to an HTMX partial rather than blocking the page; the wooden spoon
stays visible mid-tournament, matching existing `/history` precedent.

`webapp.deps.get_tournament_state()` is the single source of truth for the three states —
in-progress, latest-complete, no usable data — read from the two small status CSVs, never
`get_default_teg_num()` (which silently falls back to a hardcoded TEG on unreadable data). The
complete state costs no parquet load: winners come straight from `data/teg_winners.csv`. The five
`NAV_SECTIONS` groups render unchanged below the panel, one per bounded surface (not the old
`!important`-laden three-column layout), preserving all 28 public destinations byte-for-byte
against `webapp/nav.py`.

Verified: all three states, 320/390/768/1280px, light/dark, both Clean-family layouts, direct
navigation and reload, warm- and cold-cache leader rendering, ties (no countback — every tied
player named). 9 new focused tests (`tests/test_webapp_pages.py -k contents`); full suite of
`test_webapp_pages.py` (110), `test_imports.py`/`test_no_streamlit_imports.py` (30) and
`check_pandas_compat.py` (0 errors) all pass. `design_principles.md`'s accent-colour rule (line 29
+ checklist) updated to record green's actual jobs (honours, live status, active selection,
top-rank emphasis) and that they never combine on one render. Full contract, rulings and
verification: `webapp/design_reviews/ui_workstream/I3-handoff.md`, `I4-handoff.md`,
`I5-handoff.md`.

**Next:** I6 (Improve review gate).

## 2026-09-20 — UI implementation roadmap Improve stage: I2 public interaction and URL state

Branch `codex/ui-i2`, based on `2f0baef` after I1 and its mobile-polish follow-ups. Not yet merged.

Public read-only HTMX pages now share one opt-in state controller. Tabs denote views, segmented controls denote exclusive measures, and compact actions handle Retry. Selected state and canonical history commit only after the main target swaps successfully. Failed transports or marked application errors retain the previous view and URL, restore confirmed controls, and can replay the exact GET.

Full-page routes now accept the same public state as their partial endpoints across standings, Latest TEG, history, player profiles, scorecards, scoring, performance, eclectic, bestball and charts. Direct links, reload, sharing, Back and forward therefore reproduce the confirmed view. Latest Round's audited pending/confirmed controller remains intact; only its failure presentation joins the shared visual pattern.

Verified with focused page tests under pinned Python 3.12 and browser flows covering direct links, reload, successful and failed swaps, retry, one history entry per response, Back/forward, standings OOB swaps, marked application errors and a Latest Round regression check. Full detail: `webapp/design_reviews/ui_workstream/I2-handoff.md`.

**Next:** owner review and merge decision, then I3 (Contents product contract) or the next roadmap item.

## 2026-09-20 — Latest Round/TEG detail row: Score mix as a CSS bar chart

Branch `claude/ui-score-mix-chart`, worktree, based on `2f0baef`. Not yet merged. Replaced the
plain-text "label: count, ..." Score mix list in the leaderboard/TEG expandable detail row with a
dependency-free CSS bar chart (`_score_mix_chart_html` in `webapp/routes/latest.py`; `.score-mix`
rules in `webapp/static/themes/base-vars.css`) — grid rows with width-percentage fills, tokens
only, no JS/SVG/library.

## 2026-09-20 — UI implementation roadmap Improve stage: I1 unified standings renderer

Branch `claude/ui-i1`, worktree, based on `bb3f8df` (C6/C6a's accepted base). Not yet merged.

`/leaderboard` and `/results` already shared one context builder but shipped three overlapping
render paths: a Python HTML-string table, a phone-only card list (`.lb-cards`) that turned out to
be CSS-dead at every viewport since R3.2 (`.standings-page .lb-cards { display: none }` always
won), and two page partials that had silently drifted (`/leaderboard`'s Scorecards tab was
double-wrapping already-complete markup, the same defect class F4 fixed on Latest Round).

Replaced all three with one semantic Jinja standings table (`partials/_standings_table.html`, fed
by `_standings_rows` in `webapp/routes/history.py`) behind one shared page partial
(`partials/_standings_page.html`), included by two thin id-prefixed wrappers so route URLs,
element ids and HTMX swap targets are unchanged. The table reflows at ≤640px: each row's round
values render once as desktop `<td>` cells and once as a `.standings-rounds` strip, with CSS
showing exactly one copy per viewport — so the two can't drift the way the old card path did.
Deleted the dead `.lb-cards`/`.lb-card*` markup and CSS; fixed `/leaderboard`'s Scorecards
double-wrap along the way. Player links stay off (`link_players=False`, unchanged default).

Verified: `tests/test_webapp_pages.py` (83 passed, 8 new — round-count-varies, strip/cell parity,
ties, empty state, card-markup-gone, `/leaderboard` and `/results` render byte-identical standings,
Gross omits the spoon); `tests/test_imports.py` + `tests/test_no_streamlit_imports.py`;
`scripts/check_pandas_compat.py` (0 errors); `scripts/check_python_compat.py`. Browser: TEG 18
(5 players), TEG 7 (6 players, `NetVP` era — no eight-player TEG exists), TEG 2 (3 rounds), TEG 14
(4 players) at 320–1280px, light/dark, both Clean layouts; HTMX TEG-swap re-fires `names-break`
and keeps the race-chart readout wired. Full detail: `webapp/design_reviews/ui_workstream/I1-handoff.md`.

**Next:** owner review and merge decision, then I2 (public interaction/URL state) or I3 (Contents
product contract) — see `webapp/design_reviews/ui-implementation-roadmap.md`.

## 2026-09-20 — UI implementation roadmap Consistent UI stage complete: C5 rhythm pass, C6 review, C6a fix

Closes out Consistent UI (C1–C6). All now merged to `main` and deployed.

- **C5** (leaderboard/results rhythm/controls) — compacted the tab-row-to-table gap on
  `/leaderboard`/`/results` (two targeted margin fixes, `base-vars.css`), migrated `/results`'
  Net/Gross toggle from `.scale-switch` to `.segmented` to match `/leaderboard` (C3), and dropped
  a redundant "Leaderboard" word from the section title when a TEG is in progress. Full detail:
  `webapp/design_reviews/ui_workstream/C5-handoff.md`.
- **C6** (independent review gate, read-only) — verified the combined C1–C5 diff live across 380
  page loads (all in-scope public routes × 5 widths × light/dark × both Clean layouts). Found one
  confirmed blocker: C5's removal of `.measure-toggle` CSS (believed dead after the Leaderboard
  migration) also silently broke `/latest-round`'s Round/TEG-total toggle, which still needs it
  and regressed to an invisible white-on-white unchecked state. Also corrected two automated
  Playwright-sweep misreads before they entered the record (`/contents`'s headings were reported
  as matching C3's merged rule but are actually a separate, never-migrated style; a toggle was
  misidentified as Stableford/Gross when it's Round/TEG-total). Full findings, corrections and
  verdict: `webapp/design_reviews/ui_workstream/C6-review.md`.
- **C6a** (blocker fix) — restored the deleted `.measure-toggle` rule, scoped by comment to its
  one remaining call site. Verified before/after computed styles and that the Leaderboard's
  `.segmented` control is unaffected. `webapp/design_reviews/ui_workstream/C6a-handoff.md`.

**Next:** Improve stage, starting with **I1** (unify the public standings renderer) — see
`webapp/design_reviews/ui-implementation-roadmap.md`.

## 2026-09-20 — UI implementation roadmap Consistent UI stage: C4 responsive/table contract pass

Built on C3's foundation (`62b68b5`), on branch `worktree-c4-responsive-tables` in a dedicated
worktree — not yet merged. Two parts: the roadmap's generic C4 brief (audit every public table
route against the phone/tablet/desktop contract) plus three owner-assigned items beyond it.

**Owner-assigned items:**

- **`.pill`/`.section-controls select` 44px touch floor** — both defaulted to 40px on phone
  (`mobile.css`); raised to 44px. Removed the now-redundant page-scoped 44px compensations this
  uncovered on Latest Round/Latest TEG/Leaderboard/Results (`mobile.css`) and Player Profile's
  chart-control pills (`player-profile.css`) — same value, no longer needed once the default
  covers it.
- **`.action` adopted** on `.rank-toggle` (Latest Round/Latest TEG) and History's
  `button.teg-cell` disclosure — colour/hit-area tokens and the shared `--focus` ring (not the
  sitewide green) only, no redesign. Both already carried higher-specificity page-scoped
  selectors that continue to win the cascade for geometry, so rendering is unchanged except the
  keyboard focus ring. History's desktop disclosure affordance (still no visible `+`/`-` above
  640px, carried from C1b) remains an **open owner question** — not decided here.
- **`.main-content` padding/radius before/after comparison** — screenshot-only, per the owner's
  request; the tokenised alternative (`--sp-6` 32px / `--r-1` 3px vs the shipped 40px/4px
  literal) was **not applied**. Paired screenshots:
  `webapp/design_reviews/ui_workstream/screenshots/C4/main-content-padding/`. Finding: a visible
  but modest ~8px-per-side tightening in Clean Page; **zero effect in Clean Layered**, since
  `.page-panel .main-content` there already overrides padding/radius independently of the plain
  `.main-content` rule this token swap would touch.

**Table-contract audit:** every public table route (leaderboard, results, records, player,
scorecard, latest-round/teg, and the scoring-analysis pages) checked against phone/tablet/desktop
compression, identity-column protection and navigation — full per-route table in
`webapp/design_reviews/ui_workstream/C4-handoff.md`. Two real gaps found and fixed:

- **`/scoring/heatmap` page-level overflow at ≤390px** — the colour-legend row
  (`.hm-legend`/`.hm-legend-range`) was an unwrapped flex row with `white-space: nowrap`, not the
  transposed table itself. Fixed in `heatmap.css` (the file that actually wins the cascade —
  `mobile.css` loads first, page-specific `heatmap.css` after).
- **`/scorecard` page-level overflow at 768px in Clean Layered** — `.sc-landscape:not(.data-card)`
  (`width: fit-content`) sized to its un-clipped table content rather than the scroll-container's
  available width. Fixed with `max-width: 100%`; verified the title/table joint-centering this
  rule exists for is unaffected, and the internal horizontal scroll for wider TEG-wide views still
  works.

**Regression found and fixed during verification** (not by the audit): adopting `.action` on
`.rank-toggle` introduced a new phone `min-width: 44px` floor via CSS's per-property cascade — the
page-scoped rank-toggle rule has higher overall specificity but never declared `min-width`, so
`.action`'s value leaked through anyway and pushed the button past its narrow toggle-table-cell,
causing a 2–13px page overflow on `/latest-round`/`/latest-teg` at phone widths in Clean Page.
Fixed with an explicit `min-width: 0` override (`mobile.css`) — the button's 44px touch target
comes from filling its column at 100% width/full row height, not from a literal 44px min-width.

**Process note:** several CSS files here are served with `?v=N` cache-busting query params in
their `<link>` tags (`mobile.css`, `scorecard.css`, `player-profile.css`). Edited without bumping
the version, a live/test browser keeps serving the old cached file — this produced a false
12-failure overflow report mid-session until the versions were bumped. Bump the relevant `?v=N` in
`base.html`/the owning template whenever one of these files changes.

MOBILE_PLAN.md reconciled: dark-mode page-title contrast (fixed by F1) removed from "remaining
work"; M2.9's tap-target/route-audit scope marked covered by this pass, spacing/empty-state polish
still open.

Verified: 200-state fresh-cache overflow sweep (10 routes × 320/390/430/768/1280px × Clean
Page/Clean Layered × light/dark) — 0 failures. Scoreboard-overflow width formula and F5's
scroll-delta nav guard both re-confirmed intact. `python -m pytest tests/test_webapp_pages.py
tests/test_scorecards_portrait.py -q` — 90 passed. `check_css_comments.py`,
`check_python_compat.py`, `check_pandas_compat.py` — all clean.

Full detail, per-route audit table, and screenshot manifest:
`webapp/design_reviews/ui_workstream/C4-handoff.md`. Unresolved items:
`webapp/TODOS.md`.

## 2026-09-20 — UI implementation roadmap Consistent UI stage: C3 foundation merged

Foundation implementation for the Clean Editorial Precision system (C1/C1b's approved spec),
merged from `claude/ui-c3` onto `main`. Declares the type/spacing/radius/rule/shadow/colour
token set (`--fs-*`, `--sp-*`, `--r-*`, `--rule-*`, `--shadow-card`, `--ink*`, `--green`,
`--focus`, `--leader-tint*`, `--bg-content`) in `webapp/static/themes/clean.css`'s `:root`, with
dark counterparts in `dark.css`, and applies it to the smallest representative components:

- `.section-title`/`.card-header`/`.chart-title` — previously three byte-identical CSS blocks —
  merged into one shared rule.
- New `.segmented`/`.seg-option` control, wired into `/leaderboard`'s Net/Gross measure
  (replacing the binary `.scale-switch`, whose "on/off" semantics didn't fit two equally-weighted
  options). `.action` declared for a future disclosure/expand control pattern; no call site yet.
- `/player/<code>`'s tab bar (`.pp-tab`) folded into the site's one canonical `.tab-underline`
  pattern.
- Leader-row tint/hover fix (previously identical to the hover colour) scoped to
  `.leaderboard-table` — also benefits `/results`, which renders through the same table partial.
- Twelve dead `ts-*` page-title-style CSS blocks deleted (superseded design-lab variants);
  `.rank-toggle`'s duplicated glyph rule and a `dark.css` `#16150f` hard-code fixed in passing.
- `webapp/design_principles.md` corrected: hit-area contract is two-tier (44px touch / 28–36px
  fine-pointer), not a flat 44px floor — the previous wording didn't match the shipped desktop
  `.rank-toggle`.

Verified before merge (re-run independently, not taken from the branch's own report): merge-tree
dry run clean against `main`; the branch's only `mobile.css` change (glyph-rule dedup) doesn't
touch `.scale-switch`, so the already-merged Scoreboard-overflow width fix and F5's scroll-delta
nav guard both survive in `base.html`/`mobile.css` post-merge; 75 focused tests pass; full suite
run once at merge (shared theme CSS + `base.html` + two partials justify it).

Full detail, decisions and screenshot matrix: `webapp/design_reviews/ui_workstream/C3-handoff.md`.
Unresolved items assigned to C4/C5 or left open: `webapp/TODOS.md`.

## 2026-09-20 — UI implementation roadmap Fix stage (F1–F6) shipped

Public UI defect-fix stage from `webapp/design_reviews/ui-implementation-roadmap.md`, staged as
five independent chats (F1–F5) plus a read-only review gate (F6) and its remediation follow-up.
Shipped:

- **Desktop rank-toggle glyph/hit-area** — the `/latest-round`/`/latest-teg` `+`/`-` expand
  button on the Scoreboard detail row was invisible and unclickable above 640px (`mobile.css`'s
  glyph rule never reaches desktop widths). Added a desktop-scoped counterpart, later corrected
  to explicitly exclude phone widths so its `min-width` couldn't leak there.
- **Dark-mode `title_style=e2` contrast** — that title variant hard-codes a light title-band
  background with no dark override; fixed with a `dark.css` override.
- **Latest Round Scoring tab phone header overflow** — the score-count pivot's raw field-name
  header (`GrossVP`/`Stableford`) bled into the adjacent column at ≤640px; given its own class
  and the existing site wrap pattern.
- **Latest Round/TEG Records & PBs double-wrapped in an extra card** — the records section
  wasn't marked `raw`, so the shared renderer's own card markup got wrapped a second time,
  visible in Clean Layered above 640px. Fixed by setting `raw: True`, matching the neighbouring
  scorecard/bestball sections.
- **Long-page navigation persistence** — the sticky-nav scroll handler originally computed hide
  state from absolute `scrollY` only. F5 added direction tracking; a follow-up now filters isolated
  micro-jitter and reveals after 8px of uninterrupted upward movement. A 384-state public sweep
  across 32 route states, both Clean layouts, light/dark, and 390/768/1280px closed F6's missing
  cross-route verification follow-up without finding a nav regression.
- Three other suspected defects (standalone `/records` overflow, Latest Round Streaks, Latest
  Round Scorecard phone inset) were investigated and found **not reproduced** — closed with
  evidence in `webapp/TODOS.md` rather than "fixed."
- The three CSS files changed (`base-vars.css`, `dark.css`, `mobile.css`) had their `base.html`
  cache-bust query strings bumped so the fixes reach returning visitors.

Full evidence trail (screenshots, browser verification matrices, per-stage root-cause analysis):
`webapp/design_reviews/ui_workstream/{P0,F1,F2,F3,F4,F5,F5-followups,F6a}-handoff.md`. A read-only F6 review
gate found two evidence-integrity issues (a stale/mismatched F3 screenshot pair, an unrecorded
P0 finding) before Consistent UI could proceed — both resolved in the F6a follow-up.

**Next:** C4 — apply the responsive/table contracts on top of C3's foundation, plus the follow-ups
assigned to it in `webapp/TODOS.md` (two 44px phone-default fixes, `.action` adoption, a
before/after comparison of the content-card padding/radius). Then C5 (leaderboard rhythm).

## 2026-09-19 — New page: `/scoring/round-distribution`

New Scoring analysis page: a small-multiples grid of per-player round-score
(18-hole total) histograms. All charts share one fixed x-axis (5-stroke bins,
spanning the full historical score range) so shapes compare directly across
players, and a dashed line marks each player's mean. A pill filter at the top
(All TEGs / Last 5 TEGs / Last 10 TEGs) restricts which rounds feed the
histograms without ever changing the axis. Backed by `cached_round_data()`
(no new data plumbing); one Plotly bar chart per player, same
`get_chart_style('streamlit')` theme as the rest of the site. New files:
`webapp/templates/scoring_round_distribution.html`,
`webapp/templates/partials/scoring_round_distribution_content.html`,
`webapp/static/round-distribution.css`. Route/context logic added to the end
of `webapp/routes/scoring.py`; nav entry added to `webapp/nav.py`.

## 2026-09-19 — Report link relocated under the page title

On `/latest-round`, `/latest-teg`, `/leaderboard` and `/results`, the "View report" link now sits
right under the page title, inside the hero/background area, instead of between the selector and
the tab bar in the page body. Keeps the page body cleaner. Purely a markup move (same ids, same
visibility logic, same JS sync) — no behavioural change.

## 2026-09-19 — Dynamic hero title/label on `/leaderboard` and `/results`

Same hero restructuring as `/latest-teg`/`/latest-round` (below), applied to `/leaderboard` and
`/results`: TEG selector moved into the hero title area with a white background, small-caps label
now shows live location/year, and the title itself is now dynamic — "TEG {n} Results" normally, or
"TEG {n} Leaderboard" if that TEG is still in progress (same rule on both pages, since it's driven
by TEG state, not page identity). Updates live via HTMX out-of-band swap on TEG change, no reload.
The Report link on `/leaderboard` is already correctly hidden for an in-progress TEG — its
visibility check (`report_tegs`, sourced only from completed TEGs) already covers this, no code
change needed. Caught and fixed the same class of duplicate-header-on-full-page-load bug found on
`/latest-teg` earlier, using the same `..._full_page` guard pattern.

## 2026-09-19 — Dynamic hero title/label, selectors moved into title area

On `/latest-teg` and `/latest-round`, the TEG selector (and, on the round page, the round-pill
selector) now sits in the page's hero title block instead of below it. The small-caps label above
the title now shows the location/date that used to render as a separate line below the selector
(e.g. "Catalonia, Spain | 2025"), and the page title itself is now dynamic: "TEG 18" on the teg
page, "TEG 18, Round 4" on the round page — both update live via the existing HTMX out-of-band-swap
mechanism when the selector changes, no page reload. Along the way, fixed a real bug: `/latest-teg`
was missing the full-page-load duplicate-OOB guard the round page already had, causing a duplicate
location/TEG line to render at the bottom of the tab content on first load.

## 2026-09-19 — Streaks/Scoring formatting, Records expander removal, report-link relocation

Five more changes to `codex/mobile-ui-rollout`, following the batch below:
- Emojis removed from Records & PBs section headings (`🏆`/`💀`/`⭐`/`⚠️`) on `/latest-round` and `/latest-teg`.
- Streaks tab (both pages): `0` now displays as `-`, and both `0`s and `1`s (a single occurrence barely
  counts as a "streak") render in muted grey text; `2+` values unaffected.
- Scoring tab (both pages): `0` now displays as `-` (plain text, no colour change).
- Records & PBs tab (both pages): rows no longer render as a tap-to-expand `<details>` element, since
  there was never any extra detail to reveal there — now plain rows. The standalone `/records` page's
  real venue/date expand behaviour is unchanged (it has genuine detail to show).
- The "Report" link, previously inline in the tab bar (looking like a same-page tab despite navigating
  away), is now in its own distinct row with dashed-underline small-caps styling on `/latest-teg`,
  `/results` and `/leaderboard` too — matching the treatment `/latest-round` already had. `/results` and
  `/leaderboard` share one CSS class pair (`.res-report-row`/`.res-report-link`) since they already share
  a page wrapper (`.standings-page`) and data builder; `/latest-teg` shares `/latest-round`'s classes via
  comma-joined selectors.

## 2026-09-19 — Records & PBs fix + `/latest-teg` parity batch

Four changes to `codex/mobile-ui-rollout`:
- **Records & PBs bug fix** (`/latest-round` and `/latest-teg`): the tab showed category headings
  but no actual record/PB values, at every screen width. Root cause was a class-name collision —
  `_render_records_summary()` in `webapp/routes/latest.py` reused the `records-list` class for
  plain content, colliding with a global mobile-only `display:none` hook meant only for `/records`'
  dual desktop-table/mobile-list markup. Fixed by routing both pages' Records & PBs tab through the
  same `_build_records_html()` used by `/records`, so values now render correctly in both the
  desktop table and mobile tap-to-expand list formats.
- **Eclectic tab contribution table**: the CSS bar-chart cell for Holes on `/latest-teg`'s ECLECTIC
  tab is now a plain Holes/Solo two-column table, matching `/latest-round`'s BESTBALL/WORSTBALL
  contribution table. Dead bar-chart CSS removed from `scorecard.css`.
- **Scoreboard leaderboard styling adopted onto `/latest-teg`**: the SCOREBOARD (aggregate) tab now
  uses the same ranked `table.leaderboard` styling as `/latest-round`'s AGGREGATE SCORE tab (rank
  badges, personal/all-time rank columns, tap-to-expand detail row — one tile per round played
  instead of round's Out/In) — without the Plotly chart or the Round↔TEG-total toggle, both of
  which stay round-only by design. `_build_scoreboard_table()` was generalized (`detail_cols`
  param) to serve both pages from one implementation.
- **Eclectic tab's "Player ranks" table**: fixed layout overflow/column misalignment by reusing the
  same `_build_scoreboard_table()` leaderboard styling (no detail row, since there's no natural
  per-player breakdown to hide behind a tap).

See `webapp/MOBILE_PLAN.md` for phase status.

## 2026-09-19 — `/latest-round` Scoreboard mobile polish batch

Eight changes to `codex/mobile-ui-rollout`, all at every page width unless noted:
- Player names on the Scoreboard table are no longer bold.
- The `.lr-readout` pill-style chart/graph legend is now unified across all page widths, not just
  `/latest-round` — since it shares CSS with the tournament-race and scoring-analysis charts, this
  also affects `/results`, `/leaderboard`, `/scoring/by-teg` and `/scoring/distributions`.
- Rank-header (Personal rank / All-time rank) column-width and centring fix — see
  `webapp/design_principles.md` → *Mobile table pattern* for the underlying `overflow-wrap`
  pitfall this fixed.
- A site-wide scroll-jump bug on htmx tab-bar swaps was fixed in `base.html` — **not**
  `/latest-round`-specific; it also fixed `/records`.
- The Report link on `/latest-round` moved out of the tab bar to its own row below it, with
  distinct dashed-underline italic-serif styling signalling it navigates away (same treatment
  still owed to `/results` and `/latest-teg` — see `webapp/TODOS.md`).
- Streaks tab headers on `/latest-round` and `/latest-teg` now show initials instead of full names.
- New Round-vs-TEG-cumulative-total toggle on the Scoreboard tab.
- The mobile-table pattern behind the Scoreboard table (columns, typography, primary/secondary
  column treatment, player-name handling, row shading, expandable detail row, and two pitfalls
  already hit) is now documented as a reusable reference in `webapp/design_principles.md`, for
  converting other tables to this pattern later.

Two follow-ups surfaced during this work and logged in `webapp/TODOS.md`: the detail-row toggle
button has no glyph above 640px, and the Report-tab relocation is still owed to `/results` and
`/latest-teg`.

## 2026-09-16 — Player progression charts mobile treatment (pending review)

`codex/mobile-ui-rollout` gains R4.2: the player profile's Career Trend and Gross vs Par by Round charts now state measure/direction without hover on phones, and the Rounds chart reuses `player-profile.js`'s existing tick-thinning/theme-adaptation/live-breakpoint pattern instead of a new chart system, keeping dense histories (a 17-TEG player was the stress case) readable at 320px. Desktop and iPad are unchanged. Committed directly (checkpoint `890c510`) to avoid losing progress ahead of the usual review step — **needs review**. Scoring-analysis charts (R4.3) are next.

## 2026-09-15 — Core mobile data layouts recovered on rollout branch

The mobile work lost in the reboot has been recovered and extended on `codex/mobile-ui-rollout`, based on the deployed PDF/reporting commit. The pending rollout now includes the compact interactive Latest Round view, mobile History disclosure, equal-height standings rows, portrait scorecard refinements, responsive Best/Worstball views and phone-only tournament chart readouts for Results and Leaderboard. Desktop, iPad and `/charts` retain their prior chart output. The branch remains unmerged and undeployed.

## 2026-09-15 — Pre-rendered PDF download for reports

`/teg-reports` gained a Download PDF button: each tournament/round report now has a pre-rendered,
single-page A4 PDF carrying the desktop newspaper layout regardless of the downloading device.
PDFs are built **offline** by `python scripts/build_report_pdfs.py --all` (headless Chromium via
Playwright, ~1s/report, ~90s for all 84) — Railway never renders one, matching the existing rule
that the webapp only reads finished reports. `read_binary_file` (new, `teg_analysis/io/file_operations.py`)
serves the bytes; the button is gated on `data/commentary/pdfs/manifest.json` so an unbuilt report
shows no button rather than a dead link. Playwright is a dev-only dependency
(`requirements-dev.txt`) and never enters `requirements.txt`. **Known weakness, by design:** a PDF
can drift from its report or from `newspaper_preview.css` with no automatic signal —
`--check` detects it, nothing enforces it yet (follow-up in `webapp/TODOS.md`). Detail:
`webapp/README.md`, `teg_analysis/reporting/README.md` → *Pre-render to PDF*,
`teg_analysis/reporting/ARTEFACTS.md` → *The PDF artefact*, `DATA_FLOW.md` → §10.

## 2026-09-15 — Standfirsts now set in Libre Franklin italic

Follow-on from the entry below. After an A/B of five treatments (upright sans, sans italic, and a
vertical-bar variant of serif italic / sans / sans italic), Jon chose **sans italic**: upright Libre
Franklin read as a label under the headline, the italic reads as a voice introducing the story. The
`.sf-contrast` rule now sets `font-style:italic`, covering the lead, sub-article and mobile
standfirsts alike. `.topbar .tb-title` also uses `--font-contrast` but sets no style, so it stays
upright — both axes are loaded and bundled.

The PDF build also became **byte-deterministic**: Chromium stamps a fresh `/CreationDate` and `/ID`
into every render, so previously every rebuild rewrote all 84 files and cost a ~24 MB diff even when
no report had changed. Those fields are now normalised in place (equal-length replacement, so the
xref offsets stay valid), meaning a rebuild only produces new blobs for reports that genuinely
changed.

## 2026-09-15 — Standfirsts now set in Libre Franklin

`--font-contrast` has named `'Libre Franklin'` since the standfirst redesign (2026-09-11), but the
font was never in `teg_reports.html`'s Google Fonts link — so every standfirst on the live site
silently fell back to Arial, and to Liberation Sans in the new PDFs. Found while checking font
fidelity in the PDF build. Fixed on both sides: added to the page's font link (29 KB latin subset)
and bundled into `webapp/static/fonts/` for the PDF build, whose font-load guard now covers all
four families. The 84 PDFs were rebuilt. Jon picked Libre Franklin over three alternatives
(Arial as-is, the pre-2026-09-11 upright serif, a serif italic) — it is the treatment the
`.sf-contrast` sizes were tuned for.

## 2026-09-13 — Grouped player detail approved

The approved prototype is implemented for `/player/{code}`. Glance statistics
and Trophy Cabinet stay clearly grouped; Career Highlights remain four cards.
A compact player picker, responsive neutral chart, recent/full results toggle
and complete held-record details reduce overview clutter. The liked `/player`
roster and all analytical calculations are unchanged. Further aesthetic work
to make the page less generic remains open in `webapp/TODOS.md`.

## 2026-09-12 — Shared UI polish approved

Working branch `ui/shared-polish-review`: button-based navigation, tablet
hamburger, default title alignment, phone control/text insets and visible tab
scrollbars. HTMX read requests expose busy state and dismissible failure
feedback. No data-write changes. User reviewed and approved the UI for merge;
automated browser visual verification was unavailable.

## 2026-09-13 — Report sync refreshes current editions with immediate feedback

“Sync all reports from GitHub” now includes tournament and round storyline-first styled markdown
and storyline plan JSON. It previously pulled only legacy report filenames,
leaving regenerated current editions stale on the Railway volume. Existing
backup and cache-clearing behavior is retained; no report regeneration needed.
Pull/Push selected now show “Checking selected files…” during the slow GitHub
preview request and disable repeated clicks. Confirmation shows a busy label
before copy progress starts, and the preview/progress scrolls into view.

## 2026-09-12 — Shared CLI recovery

Added model-free Claude/Codex lifecycle capture and read-only startup recovery
in `scripts/agent_handoff.py`, plus continuation shortcuts in
`scripts/agent_handoff.zsh`. Local notes record intent; automatic snapshots
retain requests, tool outcomes, Git state and source session baselines even
without a final handoff. Setup is in `README.md` → *Shared CLI recovery*.
Project hooks and backed-up zsh shell integration are installed. All 20 focused
recovery checks pass under Python 3.12. Codex `/hooks` trust and real CLI runtime
verification remain pending. Automatic CLI launching on quota exhaustion
remains separate work.

## Where things stand

**`teg_analysis/`** — Phases 1–7 cleanup complete (all Streamlit imports removed; aggregation/streaks/scoring refactored; dead code removed). Merged to `main`. Canonical analysis layer, fully UI-agnostic.

**`webapp/`** — Full Streamlit page set replicated and functionally complete. `/` lands on the Contents site map. Nav mirrors Streamlit sections/titles/order from a single source of truth (`webapp/nav.py` → `NAV_SECTIONS`).

**Feature parity — closed.** Every functional gap against Streamlit is closed; all endpoints render their Streamlit-equivalent content. Not an active workstream; `webapp/PARITY_AUDIT.md` is an archive. Modules that came out of it: `analysis/player_rankings.py`, `analysis/handicaps.py`, `display/scorecards.py`, `pivot_window_streaks` in `analysis/streaks.py`. The only residue is cosmetic, absorbed into the formatting pass below.

**Data admin** — Behind cookie auth in `webapp/routes/admin.py`, driven by headless `analysis/data_update.py` + `io/sync.py`: add a round; delete rounds/TEGs; edit metadata CSVs; selective GitHub↔store file sync (pre-action preview + text diff); volume browser (per-file edit/sync/download/delete-with-backup); backups browser (restores back up the replaced copy first); file guide (`io/file_catalog.py`). Report generation is out of scope here.

**Reporting** — LLM-powered tournament reports (`teg_analysis/reporting/`). **Two pipelines now
exist:** the production **five-stage** chain below, and a newer **storyline-first** chain (TEGs 14,
16, 18) that produces the separate-articles content the settled newspaper layout renders. Neither has
replaced the other; `/teg-reports` still serves the five-stage output. The end-to-end route for both
— scores entered through to the rendered report — is `DATA_FLOW.md` → §10. Five-stage pipeline: scored evidence-carrying beats + competition arcs (code) → structured story plan (LLM) → dry draft as QA scaffold + entertaining write-up + repetition lint (LLM) → CSS-class styled markdown, with mechanical verification (`verify.py`, 8 checks) after every generation. **All 17 TEGs (2–18) published and regenerated on one vintage**; ~$0.65 each. Can run on the Anthropic API (default) or hand prompts off to claude.ai plan usage. ⚠️ **What the site serves lags what was generated** — 16 of 17 styled files still hold pre-2026-08-13 prose, because the regeneration ran `style=False`. Details: `teg_analysis/reporting/README.md`, `teg_analysis/reporting/STATUS.md`.

**Player profiles** — the roster keeps its player cards. Detail pages now use
grouped career statistics and honours, four Career Highlights cards, responsive
career charts and expandable full TEG history. Landmarks and complete held
records/worsts remain available. Structural design approved; a less-generic
aesthetic pass and the pre-existing career-average weighting mismatch remain
open (`webapp/TODOS.md`). Page patterns: `webapp/README.md` → Player profiles.

**Data storage + native round entry** — Railway-volume + GitHub foundation kept and hardened (backups on add, concurrency lock, dead CSV mirrors retired). Google Sheets score capture replaced with a native mobile-first flow:

Code: `teg_analysis/analysis/round_setup.py`, `teg_setup.py`, `live_round.py`; `webapp/routes/admin_round_setup.py`, `admin_teg_setup.py`, `admin_live_round.py`, `live_round.py`.

- **Pre-round setup** (`/admin/round-setup`) — confirm Par/SI (`round_pars.csv`, defaults from `course_pars.csv`)
- **TEG setup** (`/admin/teg-setup`) — confirm roster + handicaps (not every player plays every TEG)
- **Live round entry** — `/admin/live-round` to start/review/finalize; `/live-round/{token}` for players, no login (the link is the access control). Fixed/relative keypad toggle, player-group chip picker, OS dictation voice entry on a sticky-keypad grid. Server assigns write order, so concurrent edits to the same cell are flagged for admin review rather than silently resolved. Finalize runs reviewed scores through `execute_data_update` — one GitHub commit, same as any round addition.
- **Live leaderboard** — `/live-round/{token}/leaderboard`, `get_live_leaderboard` computing gross + net/Stableford from staging via `process_round_for_all_scores`. Shows "scoring in progress" until every player is thru 18; reads staging only (a live round isn't on the main site until finalized). "View leaderboard" banner once a group has all 18 in.
- **Admin review** — full staged scorecard as an editable grid. `apply_admin_edits` is the authoritative bulk-edit primitive; `resolve_conflict` wraps it.
- **Direct entry + score ceiling** — physical-keyboard entry on the active cell (digits, Enter/Tab, arrows, Backspace) plus an "Other" keypad field; ceiling raised 12 → `MAX_SCORE = 20` across keypad/voice/admin. Covered by `tests/test_live_round_e2e.py::test_live_leaderboard_out_of_range_and_admin_edit`.

Design detail lives in docstrings in `analysis/live_round.py` and `webapp/README.md` → "Live round entry". Planning doc retained as reference: `DATA_STORAGE_INGESTION_PLAN.md`.

**Guided new-round wizard** (`teg_analysis/analysis/round_wizard.py`, `webapp/routes/admin_new_round.py`, templates `admin_new_round.html` / `admin_new_round_wizard.html`) — `/admin/new-round` (first in admin sub-nav) orchestrates round metadata → roster+handicaps → Par/SI → go live as one linear stepper. Stateless and resumable: each step saves via the existing tested functions and the current step is recomputed from data on every visit (`get_wizard_status`), so round 2/3/4 auto-skips confirmed roster and a half-finished setup resumes by revisiting the URL. Net-new piece is a round-metadata form (`get_round_metadata_form`/`save_round_metadata`) deriving `TEGRd`/`TEG`/`Area`/`Year`. Standalone pages remain reachable for edits. Detail: `webapp/README.md` → "New round (guided wizard)".

## Recent change log

### 2026-09-04 — Newspaper report-layout prototype (presentation trial)

Presentation trial only — no pipeline change, no LLM call. Tests whether a newspaper front-page
layout (lead = Trophy winner, sub-stories in a grid) beats the current single flowing column.
Built from the storyline-first artefacts on `origin/claude/storyline-first-reports` (TEG 14 and
16 only, copied not merged) via a deterministic parser, `scripts/build_newspaper_edition.py`, into
`webapp/report_layout_prototypes/newspaper.html` — four distinct layouts (A Broadsheet, B Modern
editorial, C Sports section, D Back page), switchable per TEG, served at `/report-layouts/` and as
a published Artifact.

**Verdict (2026-09-05): the direction is confirmed** — a newspaper edition is markedly more
digestible than one long report. One knock-on: interweaving in the storyline pipeline is now
mothballed (off by default), because an edition wants one subject per article.

### 2026-09-05 — Composite layout and mobile patterns

The layout was then chosen element by element rather than direction by direction, since elements
from all four prototypes were wanted. `elements.html` renders ten elements with 4–5 variants each
on identical copy; the answers are T1 broadsheet type, M1 masthead, R5 scorecard results, H1
headline, D2 drop cap, B2 two ruled columns, C2 ruled sub-columns, K1 plain kickers, S2 rail and
P1 appendices. Those are assembled in `composite.html`, which now switches only page composition and what fills
the rail below the standings (F1 nothing / F2 round table / F3 shortest story). Six arrangements were built and **the composition is now decided**: five or more stories render as
E2 (one sub-article promoted to a second lead, the rest filling the row), fewer as E1; the second
lead defaults to the Green Jacket unless a storyline beats it by 2 or more on `compelling_score`;
and nothing sits below the standings in the rail. That rule is the page's Auto setting and the
default.

Worth keeping: G1, a single three-column flow with stories breaking across columns, was the only
arrangement that tessellated consistently (column-bottom spread 202/124/8px against 66-1348px for
the rest) and was still rejected as too dense. Measured tessellation is not readability. The
at-a-glance box now also carries the runner-up on each line, derived in the build script from the
final standings.

**Mobile is decided too: pattern A, index first** — the front screen is the masthead, results and
headlines, and each article is its own screen. Measured first-screen length is the evidence: the
desktop composite squeezed to 390px runs 10.7 phone screens, A runs 1.1, B swipeable cards 1.5, C
accordion 2.2 closed and 4.4 with two sections open. A and B are built to shippable quality (hash
routing so the phone's Back gesture works, deep links, scroll restore, focus management, 44px
targets, safe-area insets, full tab semantics and keyboard control); C stays at prototype quality
as the record. `checks/check_mobile_patterns.py` asserts that behaviour in a browser at both phone
and desktop widths — it is not in the pytest suite because it needs a browser and a served copy of
the folder.

All three tournaments (14, 16, 18) render in every prototype; TEG 18 joined once the
storyline-first pipeline merged. `scripts/inline_editions.py` pushes a regenerated `editions.json`
back into the pages. Composition and mobile pattern were both picked; the `headline`/`standfirst`
gap noted here was closed on 2026-09-06 (below). Full record:
`webapp/report_layout_prototypes/README.md`, which the trial's two working docs were folded into
once the design was settled.

### 2026-09-06 — Newspaper layout wired in as a preview page

`/teg-reports-preview` (`webapp/routes/report_preview.py`) renders the settled design for real
data — not linked from the nav, `/teg-reports` untouched. Desktop renders server-side (a Python
port of `composite.html`'s JS, `teg_analysis/reporting/newspaper_edition.py::render_desktop_html`);
mobile pattern A renders client-side (`webapp/static/newspaper_preview.js`, ported from
`mobile.html`'s pattern A — hash routing, Back gesture, cold deep-links, scroll restore, focus
management), switched by a CSS breakpoint. The parser (`build_edition`) moved out of
`scripts/build_newspaper_edition.py` into `teg_analysis/reporting/newspaper_edition.py` — UI-agnostic,
so the webapp route can import it without reaching into `scripts/`; the CLI script is now a thin
wrapper. Only TEG 14/16/18 have storyline-first artefacts, so those are the only editions the
preview can render; other TEG numbers fall back to the newest available. Verified in a real
browser at 390×844 and 1280×900.

A parallel PR (#95, headline/standfirst fields) briefly broke all three: it regenerated
`teg_{14,16,18}_storyline_plan.json` without the paired styled markdown, desyncing the parser's
exact-string matching. **Fixed by hand 2026-09-08** (renamed headings for 14/16, restored a
dropped storyline for 18 — no LLM call). All three verified rendering again. Still only 3 of 17
TEGs have storyline-first artefacts at all — generating the rest is a real LLM-cost task, not
started. Detail: `teg_analysis/reporting/STATUS.md` → START HERE.

**Also landed (PR #95): `DraftedStoryline` gained real
`headline_candidates`/`chosen_headline`/`standfirst` fields**, so the layout stops deriving headlines
from `subject`. Open follow-up: the model still reaches for a two-clause "X — Y" headline over the
requested 3–8 word single clause; `check_storyline_plan_consistency` warns rather than fails.

### 2026-09-08 — Report build documented end to end

Docs only. `DATA_FLOW.md` gained **§10 "Report build"** — the single path from a round of scores to
the report a reader sees, as a mermaid diagram plus a hop-by-hop table (what each step writes, what
reads it, whether it costs an LLM call), covering both pipelines. `DATA_FLOW.md`'s commentary section
no longer claims five artefacts per TEG; `teg_analysis/reporting/README.md` gained a "Two pipelines"
block and the presentation stage that was missing after the styled markdown; `ARTEFACTS.md` gained
the storyline-first artefact set.

Three code/doc contradictions were found while verifying and have since been fixed:
`scripts/build_newspaper_edition.py` was restored to the thin wrapper; `render.style_text()` now
falls back to the storyline-first plan when the legacy one is absent, unblocking storyline-first
generation for the other 14 TEGs; and `paths.promote_variant` now promotes storyline-first
artefacts too.


### 2026-08-17 — Reporting docs reconciled against the code

No pipeline change. `teg_analysis/reporting/` docs (README, ARTEFACTS, STATUS, ONBOARDING, EXPERIMENTS)
were checked against the code, the artefacts on disk, a full test run (**518 passed** then; 520 after the 08-16 voice-slot tests) and a full
`verify --all --rounds` run, and corrected. Four corrections change what to do next:

- **The library has no fixture gaps and only one vintage.** All 17 TEGs have the complete artefact chain;
  the old "regenerate 2–8, 15, 16, 9" and "rebuild TEG 14's fixtures" items were already done.
- **D3 is clean on every tournament report** — 0 errors across all 17, so the 81-fault backlog cleared on
  the 2026-08-13 regeneration. The only 4 errors left are in round reports.
- ⚠️ **16 of 17 styled reports don't match their finals**, so none of the regenerated prose has reached a
  reader. `style=False` was deliberate; the consequence was never measured until now.
- **Three new small issues logged**: `TIGHTEN_SYSTEM` still contradicts the em-dash ban (dormant), a
  stray tracked `reply.txt` at the repo root holding an unpublished TEG 17 report, and raw `SI n` leaking
  into published prose.

### 2026-08-16 — Writer prompt gains a swappable voice slot

`WRITER_SYSTEM` went from two composed constants to three. The new `WRITER_CONTRACT` holds everything
true of a report whatever register it is written in (the winner's-story duty, structure, palette,
notation rules); `WRITER_VOICE` keeps only the register and can be replaced per call via
`build_writer_system(voice=...)`. `write_from_dry(teg, voice, label)` runs the real writer over a
frozen dry draft in a supplied voice, so trialling a register no longer needs a source edit;
`plan_scope=` and `bundle_context=` control how much material goes in with the draft.

Opt-in throughout — the production chain passes no voice, and nothing regenerates until a backfill
runs. Detail: `teg_analysis/reporting/STATUS.md` → START HERE.

### 2026-08-14 → 08-15 — Report quality: counterfactual importance, then a readability pass

Two rounds of change to what a report says and how it reads. Detail in
`teg_analysis/reporting/STATUS.md` → START HERE.

**The data layer (08-14).** Three root causes of "the reports are hard on the champion" turned out to be
in the data, not the prompts. `importance` claimed to measure contribution to the result but never
consulted the result — it is now **counterfactual** (`impact.py`): replace a player's scores over the
event with their own TEG average, recompute each competition in its own metric, and measure the swing.
Detection was lopsided 2.6:1 negative because bad things were found on gross and good things on net —
two new detectors bring it to 1.52:1. And nothing computed *why* the champion won, so `win_anatomy.py`
plus a required `why_the_champion_won` plan field now do. Champion's share of negative beats: 20% → 14%.

**The voice (08-15).** Voice was being defined in four places and three had drifted; it now lives once in
`reporting/prompts.py` and every prompt imports it, which incidentally moved the round writer onto the
current register. Then Jon read the reports — *"80% good, lacking a bit in humour, and a bit hard to
read"* — and the humour dial was settled at `humour6`, em-dashes banned outright, sentences capped at a
~15-word average. Enforced by a new `verify.py` check, not just prompt text, because the previous
sentence cap was contradicted elsewhere in the prompt and consequently ignored 18–31% of the time.

### 2026-08-15 — Report generation can run on plan usage, or in any other model

Report generation no longer has to bill per API call. `llm.py` gained a provider switch —
`TEG_LLM_PROVIDER=api|agent` — with **`api` still the default**, because it is the only mode that
works with nobody present. Three ways to run, one flag each:

- `--tegs 2-18` — the API, as before.
- `--tegs 14 --plan` — the pipeline writes each prompt to `data/llm_mailbox/` and waits; the
  `teg-report-respond` Claude Code skill answers it in-session, drawing on claude.ai plan usage.
- `--tegs 14 --paste gpt5` — same hand-off, but for you to paste into ChatGPT or Gemini, with
  output kept in `data/commentary/variants/gpt5/`.

Both hand-off modes can run at once: runs are discovered by scanning, and a paste run is marked
manual so the skill cannot answer prompts meant for another model.

The pipeline itself is unchanged — `backfill_all` and the four-call chain have one
implementation under either provider. Structured output, which the API path got free from
`messages.parse`, now ships its JSON Schema in the prompt and validates with Pydantic on the way
back, re-asking with the error on failure.

New: `teg_analysis/reporting/mailbox.py`, `paths.py`, a `--tegs` CLI on `backfill`, and
`.claude/skills/teg-report-respond/`. **The mechanism has since been run on real reports** (TEG 17 and
TEG 14 both went through the hand-off); what remains unmeasured is whether plan-usage output matches API
output in quality. Detail in `teg_analysis/reporting/README.md` → *Who answers the prompts*.

### 2026-07-09 → 07-10 — Codebase review remediation (complete)

Batched review of `webapp/` and `teg_analysis/` (streamlit frozen throughout), eight change-sets plus a closing review pass. All resulting rules are now recorded as invariants in `CLAUDE.md`.

- **Live-round data integrity** — server-side validation in `apply_score_writes`/`apply_admin_edits`; a stray value/hole/player can no longer silently drop a round
- **Pipelines fail loudly** — `update_*_cache` take `all_data` and raise; orchestrators collect into `cache_errors` via `_run_cache_step`, surfaced as an admin warning banner
- **One copy of the scoring math** — `process_round_for_all_scores` canonical in `data_update.py`, thin re-export in `core/data_loader.py`
- **No event-loop blocking** — route handlers sync `def`; finalize's GitHub commit runs outside `live_round._lock`, with an in-process `_finalizing` set gating mid-commit writes (409, not silent drop)
- **Webapp dedup** — one escaping `webapp/tables.py::df_to_html` replaced 7 copy-pasted renderers (all cells now HTML-escaped); swallowed `except` → `logger.exception`; `deps.cached_winners()`/`cached_streaks_data()` replaced three ad-hoc winner sources and per-request streak reads
- **Deterministic aggregation** — `aggregate_data` uses a fixed `_AGGREGATION_LEVEL_FIELDS` map instead of per-call `groupby().nunique()` discovery (byte-identical output, deterministic order)
- **Stableford gate** — aligned to the domain rule via `STABLEFORD_ERA_TEG = 8`
- **Prototype routes deleted** — `charts_proto`, `width_test`, `title_preview`, `showcase`, `smoke_test`, `placeholder`
- **Test guards made real** — streamlit-import guard and the `test_core_functions.py`/`test_independence.py` smoke tests now assert/raise instead of returning a bool pytest ignored; this also exposed a stale `format_vs_par(0)` expectation

Tests: 349 passed, 4 skipped (env-only altair imports). No `streamlit/` file changed.

### 2026-07-10 — Webapp to-do batch (branch `claude/web-app-todos-planning-0o3uui`, PR #67)

- **Quick fixes** — `df_to_html` renders scalar NaN/None as `-` (fixes `/scoring/by-teg`); `/scoring/by-par` column padding; `/scoring/distributions` chart follows the %/Count toggle and overlays an "All players" team-average tick per category in % mode; eclectic/bestball birdie-ring sizing
- **Performance** (profiled with warm caches) — player pages ~1.7s → ~190ms by caching player-independent global records/worsts tables in `webapp/routes/player.py` via `deps.register_cache_clearer` (first consumer); `core/metadata.py::get_scorecard_data` gained an optional `data=` param so five webapp callers pass `cached_load_all_data()` instead of re-reading the dataset per request (biggest win on Railway's mounted volume)
- **Latest-TEG Eclectic** — now mirrors the bestball "in context" tab: player-ranks table (all-time vs completed TEGs + own history) and CSS-bar contribution breakdown, via new UI-agnostic `eclectic_player_teg_totals`/`rank_teg_eclectics`/`calculate_eclectic_contributions` (`analysis/eclectic.py`) and `build_eclectic_contribution_bars` (`display/scorecards.py`); in-progress TEG shows a provisional-ranks caption
- **Charts** — multi-series charts dim other series on legend hover (centralised Plotly renderer in `base.html`)

Tests: 357 passed, 4 skipped.

### 2026-07-12 — Report refresh + sync filter (branch `claude/railway-mounted-storage-badrzy`)

`main` had already moved report reads onto the volume (`read_text_file`, discovery from `completed_tegs.csv`), auto-caching a *new* report on first view. Gap: a *regenerated* report (same filename, new content) stayed stale with no refresh path. Added `sync.sync_report_files()` — re-pulls every report-pattern file (`_REPORT_FILE_PATTERNS`, excluding the ~250 draft/version `.md`) GitHub→store with backups — wired to a one-click "Sync all reports from GitHub" on `/admin/volume-sync`. Sync page also gained a filter/search box and visible-only "select all".

Tests: `tests/test_sync.py` (pattern filter + overwrite), `tests/test_admin_routes.py` (endpoint). Docs: `DATA_FLOW.md` I/O layer.

### 2026-07-12 — TEG Reports load-perf fix (branch `claude/teg-reports-load-perf-0e74ea`)

`/teg-reports` was slow on every load. Two causes in `webapp/routes/reports.py`:

1. `read_text_file` cached volume *hits* but never *misses*, so each probe of a non-existent candidate path was an uncached GitHub 404 round-trip — ~3–4 per load (~1–2s) even with a warm volume
2. Discovery rendered the full markdown of every existing round report to HTML just to test existence, then discarded it (4 wasted renders/load)

Fix: discovery is existence-only (new `_round_report_text`/`_tournament_report_text` raw-text finders; `_load_*_report` renders only for display) and memoised in-process (`lru_cache` on `_completed_teg_numbers`/`_rounds_played_for_teg`/`_available_rounds_for_teg` + new `_satire_available`), cleared via `deps.register_cache_clearer` so the report-sync button still surfaces regenerated reports. The *displayed* report stays uncached. Steady state: 4 renders + 9 reads → 1 render + 1 read; per-load GitHub 404s now paid once per process.

Tests: 116 passed (report/admin/sync subset).

## Next priorities

1. **Mobile UI + dark mode** — the app shell, core data layouts through R3.4 and tournament chart treatment are committed on `codex/mobile-ui-rollout`. **Next: R4.2 player progression charts, then scoring-analysis charts and the remaining page audit.** Approach + progress + pickup pointer: `webapp/MOBILE_PLAN.md`; scorecard work-package: `webapp/SCORECARD_PORT.md`; mockups in `webapp/mobile_mockups/` (served at `/mockups/`).
2. **Webapp formatting pass** — visual polish, number formatting, table styling consistency, layout refinement, plus the WIP heatmap. In progress in local branches.
3. **REST API** — proper `/api` layer over `teg_analysis`, so any client can use the analysis layer without Python. Currently a placeholder in `teg_analysis/api/`.
4. **Retire Streamlit** — delete `streamlit/` once the REST API and webapp are production-ready. Nothing depends on it now; it is kept only as a reference.
