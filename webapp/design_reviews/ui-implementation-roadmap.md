# Public UI implementation roadmap

**Status:** execution plan only · **Decision source:** [gpt-ui-review.md](gpt-ui-review.md) · **Path:** Fix → Consistent UI → Improve → Experiment → Test and decide

This roadmap turns the agreed UI direction into small, independent chats. Each chat has one outcome, a bounded reading list, explicit prerequisites, and a copy-ready starter prompt.

## Scope and fixed decisions

- The active workstream covers public analysis pages and public navigation only.
- Gap-to-leader is not required and must not be introduced.
- Admin, TEG setup, round setup, score input, live-round operations, and data-update processes are excluded.
- Deferred operational recommendations remain in [gpt-ui-review.md](gpt-ui-review.md#deferred-operational-recommendations--document-now-implement-later).
- The Clean family is the only active theme family. Its two registered layouts, Clean Page and Clean Layered, must continue to work.
- Editorial Golf is a later experiment, not the starting implementation direction.
- Either CLI may lead an implementation chat as editor and integrator, per the model table below. Claude additionally performs the named independent review gates (F6, C6, I6, T1) and critique chats (C2, I4, E2), which stay read-only.

## How every implementation chat should run

### Choose the starting model

Select the model and reasoning setting shown under each chat before sending its starter prompt. These are task-specific recommendations agreed for this workstream, not permanent repository-wide model requirements or claims that another model cannot do the task.

| Chats | Starting model and reasoning |
|---|---|
| P0; F1–F4 | Astra Medium |
| F5; I1–I2 | Sol High |
| C1; I3; E1; E5; T2 | Astra High |
| C3–C5; I5; E3–E4; T3 | Astra Medium |
| F6; C6; I6; T1 | Sol High; Claude may perform the designated independent visual reviews |
| C2; I4; E2 | Claude, using the available strong reasoning model; Codex reasoning labels do not apply |
| I7 maintenance | Astra Medium for fonts or lab isolation; Sol High for Plotly loading or the Tailwind build |

The owner controls the lead model and reasoning setting. An agent must not claim to have switched its own model. Before implementation, it should flag a recommended change with a concrete reason: unresolved design choices, cross-route state behaviour, shared code risk, or repeated failed attempts. A recommendation alone is not a blocker; continue safe work unless the task is actually blocked or the owner asks to pause.

For workers, explicitly choose a currently available lower-cost model: a fast model for inventories, mechanical edits, and checks; a balanced coding model for bounded implementation. Give each worker only the necessary context, exact files, and acceptance criteria. Keep design decisions, integration, and final review with the strong lead. Skip delegation for a trivial edit when coordination would cost more than the work.

Each starter prompt repeats its starting recommendation and switch guidance so it works when copied into a fresh chat. The following operating rules also apply.

1. Start from the latest accepted UI commit, not an older copy of `main`.
2. Use a dedicated branch and worktree. Record both absolute paths in `.current_session.md` before editing.
3. Read only the documents and source named in that chat, plus `CLAUDE.md` and `.current_session.md` as required by the repository.
4. Use a strong lead model for decisions and integration. Delegate inventories, screenshot matrices, mechanical CSS, and focused tests to lower-cost agents with non-overlapping file ownership.
5. Keep one lead writer. Review agents must not edit the task branch.
6. Preserve unrelated user changes. Never modify `streamlit/`.
7. Update the relevant TODO or documentation in the same chat. Update `STATUS.md` only for shipped user-visible changes or a changed direction.
8. Run only checks justified by the change. Browser widths in this plan are acceptance checks, not permission to rewrite adjacent layouts.
9. End with the branch, commit, files changed, checks run, screenshots captured, unresolved findings, and the exact base commit for the next dependent chat.
10. Do not merge, push, or deploy without the authority that applies to that chat.

If work runs in parallel, do not give two chats concurrent ownership of `webapp/static/mobile.css`, `webapp/static/themes/base-vars.css`, `webapp/templates/base.html`, or the same template partial. Parallel investigation is safe; parallel writes to shared UI files are not.

### Persistent handoffs between chats

- Every producing Codex chat writes a concise handoff to `webapp/design_reviews/ui_workstream/<CHAT-ID>-handoff.md` and commits it with that chat. The handoff records its starting base, scope, decisions, exact checks, screenshot manifest, and unresolved issues. It cannot record its own final SHA.
- The chat’s final response supplies the resulting commit SHA. That SHA becomes the next accepted base after review and is passed explicitly with the next chat’s prompt.
- Screenshots may be committed under `webapp/design_reviews/ui_workstream/screenshots/<CHAT-ID>/` when they are small and useful for later visual comparison. Otherwise the handoff must name the attached artifact and include exact reproduction details: route, data state, viewport, layout, light/dark mode, and commit.
- Read-only Claude/reviewer chats return a named review report. The next Codex chat must receive that report with the prompt and preserve its accepted/rejected findings in its own handoff. Do not rely on an earlier chat's hidden context.
- P0 creates `webapp/design_reviews/ui_workstream/P0-handoff.md`. C1, I3, E1, and T1 create their corresponding handoffs because later gates consume them directly.

### Integration order

- Maintain one current UI integration base. Each implementation chat branches from the exact accepted SHA supplied by the prerequisite chat’s final response and confirms it against that chat’s handoff.
- The lead integrates accepted commits in dependency order. For Fix, use `F1 → F2 → F3 → F4 → F5`; rebase or resolve each later branch against the updated integration base before acceptance.
- F1–F3 may investigate in parallel, but any writes to `mobile.css` are sequenced through the integration branch. C4 completes before C5.
- F6, C6, I6, and T1 review the combined integration base, not a set of unrelated branch tips.
- Integration does not imply push or deployment. Those remain separate owner decisions.

## Dependency map

| Section | Chat | Depends on | Can run in parallel with |
|---|---|---|---|
| Prepare | P0 Baseline | Nothing | Nothing |
| Fix | F1 Small visual defects | P0 | F2/F3 investigation only; sequence shared CSS writes |
| Fix | F2 Records overflow | P0 | F1/F3 investigation only; sequence shared CSS writes |
| Fix | F3 Latest Round Scoring/Streaks | P0 | F1/F2 investigation only; sequence shared CSS writes |
| Fix | F4 Latest Round Records/Scorecard | F2 | None if it owns Latest Round CSS/partials |
| Fix | F5 Navigation persistence | F1–F4 accepted | Nothing; shared shell change |
| Fix | F6 Fix review gate | F1–F5 | Nothing |
| Consistent UI | C1 System proposal | F6 approved | Nothing |
| Consistent UI | C2 Claude critique | C1 | Nothing |
| Consistent UI | C3 Foundation implementation | C2 findings resolved | Nothing |
| Consistent UI | C4 Responsive/table contracts | C3 | Nothing |
| Consistent UI | C5 Leaderboard rhythm/controls | C4 | Nothing |
| Consistent UI | C6 Consistency review gate | C4–C5 | Nothing |
| Improve | I1 Unified standings renderer | C6 | Nothing |
| Improve | I2 Public interaction and URL state | C6; I1 recommended | I3 |
| Improve | I3 Contents product/design contract | C6 | I2 |
| Improve | I4 Claude Contents critique | I3 | Nothing |
| Improve | I5 Contents implementation | I4 resolved; I2 recommended | Nothing |
| Improve | I6 Improve review gate | I1–I5 | Nothing |
| Experiment | E1 Editorial Golf variants | I6 | Nothing |
| Experiment | E2 Claude experiment critique | E1 | Nothing |
| Experiment | E3 Selected leaderboard pilot | E2 decision | Nothing |
| Experiment | E4 Report extension, optional | E3 accepted | E5 |
| Experiment | E5 Telemetry comparison, optional | E3 or explicit owner request | E4 |
| Test | T1 Technical visual QA | E3; E4/E5 if used | Nothing |
| Test | T2 Eight-user test and decision | T1 | Nothing |
| Close | T3 Decision record and next rollout | T2 decision | Nothing |

The shortest useful path is `P0 → F1–F5 → F6 → C1–C6 → I1–I6 → E1–E3 → T1–T3`. I7, E4, and E5 are optional.

---

## Prepare

### P0 — establish the shared baseline

**Starting model:** Astra Medium.

**Goal:** produce a compact route/file/test map and reproducible screenshot baseline without changing the application.

**Starter prompt**

```text
Prepare the implementation baseline for the TEG public UI workstream. Make no application changes; create only the named baseline handoff document.

Starting recommendation: Astra Medium. Before implementation, flag whether this task needs higher reasoning or another lead model, and explain why. The owner controls that setting. Continue safe work while awaiting any optional switch; delegate cheaper work as instructed.
Read the model guidance and operating rules in webapp/design_reviews/ui-implementation-roadmap.md before starting.

Read:
- webapp/design_reviews/gpt-ui-review.md
- webapp/design_principles.md
- webapp/README.md: theme system, key patterns, design principles, and look-and-feel roadmap
- webapp/TODOS.md: UI Changes, Bugs, and Mobile & dark mode
- webapp/MOBILE_PLAN.md, but verify every claim against current source because parts may be stale

Scope:
- Public analysis and navigation only.
- Include /, /contents, /leaderboard, /results, /latest-round, /latest-teg, /records, /scorecard, /player, /teg-reports, and public scoring-analysis pages.
- Exclude admin, setup, score input, live-round operations, and data-update processes.
- Gap-to-leader is out of scope.

Produce and commit `webapp/design_reviews/ui_workstream/P0-handoff.md` containing:
1. Route → template/partial → CSS/JS → relevant test ownership map.
2. A list of shared files that must not be edited concurrently.
3. Exact local run and focused test commands already supported by the repo.
4. A screenshot checklist at 390px phone, 768px tablet portrait, and 1280px desktop in light and dark modes.
5. Before screenshots for every Fix defect.
6. Any stale TODO or MOBILE_PLAN claims that later chats must reconcile.

Use a fast lower-cost explorer for selector, route, and test inventory. The lead verifies the result. Do not edit application files, push, or deploy.
```

**Done when:** later chats can use the map without rediscovering the whole frontend; baseline captures and reproduction steps exist; shared-file collisions are explicit.

---

## Fix

### F1 — repair the two small visual defects

**Starting model:** Astra Medium.

**Prerequisite:** P0.

**Goal:** make the desktop rank toggle discoverable on Latest Round and Latest TEG, and restore dark-mode page-title contrast, without redesigning either component.

**Likely files:** `webapp/static/mobile.css`, `webapp/static/themes/base-vars.css`, `webapp/static/themes/dark.css`, `webapp/routes/latest.py`, and the existing latest-page templates/tests.

**Starter prompt**

```text
Implement only two confirmed public UI defects: the missing +/− rank-toggle glyph above 640px, and page-title variants that become too faint in dark mode.

Starting recommendation: Astra Medium. Before implementation, flag whether this task needs higher reasoning or another lead model, and explain why. The owner controls that setting. Continue safe work while awaiting any optional switch; delegate cheaper work as instructed.
Read the model guidance and operating rules in webapp/design_reviews/ui-implementation-roadmap.md before starting.

Read:
- webapp/design_reviews/ui-implementation-roadmap.md: F1
- webapp/design_reviews/gpt-ui-review.md: Fix
- webapp/design_principles.md: theme invariants, tables, and toggle controls
- the matching entries in webapp/TODOS.md
- current rank-toggle markup/scripts and page-title theme rules

Acceptance:
- On `/latest-round` and `/latest-teg` at 641px and 1280px, collapsed rows visibly show + and expanded rows show −.
- The existing hit area and aria-expanded behaviour remain correct.
- At 390px, existing mobile toggle behaviour is unchanged.
- Representative titles on /contents, /latest-round, /records, /scorecard, and /scoring/streaks are clear in light and dark modes at 390px and 1280px.
- Both registered Clean-family layouts still work.

Rules:
- Do not redesign headings or tables.
- Prefer existing tokens or a narrowly scoped override.
- Do not touch excluded operational surfaces or unrelated CSS.
- A lower-cost worker may own a CSS-only patch after the lead identifies the exact selectors. The lead reviews and integrates it.
- Run focused route/template tests and capture before/after screenshots. Update the exact TODOs you close.
```

### F2 — stop standalone Records overflow

**Starting model:** Astra Medium.

**Prerequisite:** P0.

**Goal:** keep `/records` within a 320–430px viewport while preserving the record value, owner, and event context.

**Likely files:** `webapp/routes/records.py`, `webapp/templates/records.html`, `webapp/templates/partials/records_tab.html`, `webapp/static/mobile.css`, and records tests.

**Starter prompt**

```text
Fix only the public /records narrow-screen overflow.

Starting recommendation: Astra Medium. Before implementation, flag whether this task needs higher reasoning or another lead model, and explain why. The owner controls that setting. Continue safe work while awaiting any optional switch; delegate cheaper work as instructed.
Read the model guidance and operating rules in webapp/design_reviews/ui-implementation-roadmap.md before starting.

Read:
- webapp/design_reviews/ui-implementation-roadmap.md: F2
- webapp/design_reviews/gpt-ui-review.md: Fix and Site functionality
- webapp/design_principles.md: table tiers and mobile reference pattern
- the Records overflow TODO
- the current records route, templates, CSS, and tests

Goal:
Long locations such as “TEG 8 (Lisbon Coast, Portugal, 2015)” must not widen the page or hide the important value and owner at 320px, 375px, or 430px.

Rules:
- First identify the exact overflowing element and computed width.
- Choose the smallest existing pattern: controlled wrapping, shortening, sticky-column scrolling, or route-specific compact treatment.
- Preserve desktop layout and do not impose a global table rule without evidence.
- Keep the shared renderer compatible with Latest Round, which will be handled in F4.
- Do not touch admin or score-entry tables.
- Use a lower-cost explorer for width/selector diagnosis and screenshot capture; the lead owns the solution.

Verify no page-level horizontal overflow, light/dark rendering, representative long locations, desktop stability, and focused records tests. Update the exact TODO closed.
```

### F3 — finish Latest Round Scoring and Streaks on phones

**Starting model:** Astra Medium.

**Prerequisite:** P0.

**Goal:** give both tabs an intentional phone layout rather than a squeezed desktop table.

**Likely files:** `webapp/routes/latest.py`, `webapp/templates/partials/latest_round_tab.html`, `webapp/static/mobile.css`, and latest-round tests.

**Starter prompt**

```text
Finish only the public /latest-round Scoring and Streaks phone layouts.

Starting recommendation: Astra Medium. Before implementation, flag whether this task needs higher reasoning or another lead model, and explain why. The owner controls that setting. Continue safe work while awaiting any optional switch; delegate cheaper work as instructed.
Read the model guidance and operating rules in webapp/design_reviews/ui-implementation-roadmap.md before starting.

Read:
- webapp/design_reviews/ui-implementation-roadmap.md: F3
- webapp/design_reviews/gpt-ui-review.md: Fix
- webapp/design_principles.md: mobile table reference
- the Latest Round mobile TODOs
- webapp/routes/latest.py, the active tab partials, mobile.css, and focused tests

Goal:
Make Scoring and Streaks deliberate and fast to scan at 320px, 375px, and 430px while retaining their existing data and controls.

Rules:
- Inspect current Streaks rules before adding markup.
- Preserve Scoreboard, Bestball, Worstball, tablet, and desktop behaviour.
- Preserve score-type and count/% controls plus HTMX tab switching and URL state.
- Use the existing table-tier guidance; do not squeeze every column into one viewport.
- Do not rewrite latest-round state handling or any live-write path.
- Use a balanced lower-cost coding worker only with explicit ownership of the tab partial/CSS region. The lead owns shared route decisions.

Verify light/dark, 320/375/430/768/1280px, no page-level overflow, variable player counts, HTMX swaps, and relevant tests. Update only the matching TODOs.
```

### F4 — finish Latest Round Records and Scorecard on phones

**Starting model:** Astra Medium.

**Prerequisite:** F2 accepted.

**Goal:** apply the repaired shared Records treatment inside Latest Round and remove the Scorecard tab’s excess phone inset.

**Likely files:** `webapp/routes/latest.py`, `webapp/templates/partials/latest_round_tab.html`, `webapp/templates/partials/records_tab.html`, `webapp/static/mobile.css`, `webapp/static/scorecard.css`, and latest-round tests.

**Starter prompt**

```text
Finish only the public /latest-round Records and Scorecard phone layouts, building on the accepted standalone Records fix.

Starting recommendation: Astra Medium. Before implementation, flag whether this task needs higher reasoning or another lead model, and explain why. The owner controls that setting. Continue safe work while awaiting any optional switch; delegate cheaper work as instructed.
Read the model guidance and operating rules in webapp/design_reviews/ui-implementation-roadmap.md before starting.

Read:
- webapp/design_reviews/ui-implementation-roadmap.md: F4
- the accepted F2 diff and handoff
- webapp/design_reviews/gpt-ui-review.md: Fix
- webapp/design_principles.md: mobile table reference
- current latest-round tab markup, shared Records renderer, scorecard styles, and focused tests

Goal:
- Records & PBs must fit 320–430px across bests, worsts, PBs, and score-count sections.
- Latest Round’s Scorecard tab must lose any double side inset while standalone /scorecard remains unchanged.

Rules:
- Reuse the shared Records renderer; do not create a second renderer.
- Add a wrapper hook only if a scoped CSS solution needs one.
- Preserve standalone /records and /scorecard.
- Preserve Scoreboard, Scoring, Streaks, Bestball, and Worstball.
- Do not touch teg_analysis, score entry, or live-round operations.
- A lower-cost worker may handle a clearly scoped CSS/template patch. The lead checks shared-renderer effects.

Verify 320/375/430/768/1280px, light/dark, Scoreboard → Records → Scoreboard swaps, Gross/Stableford controls, no page overflow, and focused tests. Update only the matching TODOs.
```

### F5 — restore navigation on long pages

**Starting model:** Sol High.

**Prerequisite:** F1–F4 accepted.

**Goal:** keep public navigation available on long pages without creating overlap or scroll jumps.

**Likely files:** `webapp/templates/base.html` and narrowly related navigation CSS/tests.

**Starter prompt**

```text
Fix only long-page public navigation persistence.

Starting recommendation: Sol High. Before implementation, flag whether this task needs higher reasoning or another lead model, and explain why. The owner controls that setting. Continue safe work while awaiting any optional switch; delegate cheaper work as instructed.
Read the model guidance and operating rules in webapp/design_reviews/ui-implementation-roadmap.md before starting.

Read:
- webapp/design_reviews/ui-implementation-roadmap.md: F5
- webapp/design_reviews/gpt-ui-review.md: Fix
- webapp/design_principles.md: navigation and layout invariants
- the matching TODO
- the scroll IIFE and current nav CSS in webapp/templates/base.html and related styles

Preferred behaviour:
The header/navigation may hide while scrolling down, but it should reappear promptly on any upward scroll and remain visible at the top.

Rules:
- Inspect the current one-time nav-height measurement and 300px threshold before changing behaviour.
- Do not redesign navigation or alter the phone bottom tab bar.
- Check content jump, stacking, resize/orientation changes, HTMX swaps, and pages with in-page section navigation.
- Keep excluded admin and operational flows out of scope; if a shared shell rule affects them, report it before broadening the change.
- The strong lead owns this shared-shell change. A lower-cost agent may run the scroll/browser matrix only.

Verify long /records, /latest-round, and /scoring pages at 390/768/1280px in light/dark. Run focused navigation/template tests and update the exact TODO closed.
```

### F6 — Fix review gate

**Starting model:** Sol High.

**Prerequisite:** F1–F5 accepted on one integration base.

**Goal:** decide whether Fix is complete. This is a read-only review chat.

**Starter prompt for Claude or a fresh strong reviewer**

```text
Independently review the combined TEG public UI Fix stage. Do not edit files.

Starting recommendation: Sol High. Before implementation, flag whether this task needs higher reasoning or another lead model, and explain why. The owner controls that setting. Continue safe work while awaiting any optional switch; delegate cheaper work as instructed.
Read the model guidance and operating rules in webapp/design_reviews/ui-implementation-roadmap.md before starting.

Read:
- webapp/design_reviews/gpt-ui-review.md
- webapp/design_reviews/ui-implementation-roadmap.md: Fix
- webapp/design_principles.md
- the combined diff, focused test results, and before/after screenshots

Review only:
- desktop rank-toggle discoverability;
- standalone and Latest Round Records overflow;
- Latest Round Scoring, Streaks, Records, and Scorecard phone layouts;
- dark page-title contrast;
- long-page navigation;
- regressions in the Clean family’s Clean Page and Clean Layered layouts at phone, tablet portrait, and desktop.

Return:
1. blockers with exact page, viewport, selector, and evidence;
2. non-blocking follow-ups;
3. stale or unsupported claims;
4. a clear ready/not-ready verdict for Consistent UI.

Do not propose a new aesthetic and do not review excluded operational surfaces.
```

Codex resolves accepted findings in a small follow-up on the same Fix integration branch before C1 begins.

---

## Consistent UI

### C1 — specify Clean Editorial Precision

**Starting model:** Astra High.

**Prerequisite:** F6 ready verdict.

**Goal:** produce a concrete system proposal and representative mockups; do not migrate the site yet.

**Starter prompt**

```text
Define the Clean Editorial Precision foundation for the TEG public site. This chat is specification and prototype only.

Starting recommendation: Astra High. Before implementation, flag whether this task needs higher reasoning or another lead model, and explain why. The owner controls that setting. Continue safe work while awaiting any optional switch; delegate cheaper work as instructed.
Read the model guidance and operating rules in webapp/design_reviews/ui-implementation-roadmap.md before starting.

Read:
- webapp/design_reviews/gpt-ui-review.md: Optimise the existing aesthetic
- webapp/design_principles.md in full
- webapp/README.md: Theme system and Design principles
- current base-vars.css and Clean theme files
- the accepted Fix-stage screenshots

Specify:
- a small type scale;
- three distinct heading levels;
- spacing, rule, and radius tokens;
- semantic ink, green, sand, focus, muted, success, warning, and failure roles;
- three control patterns: tabs, segmented measures, and compact actions;
- representative phone/tablet/desktop treatments for one standings screen and one analysis screen.

Rules:
- White/high-contrast outdoor readability is the baseline.
- Lora carries identity; Inter carries interface and tabular data.
- Green is semantic, not a universal heading colour.
- Prefer open sections and hairlines over nested cards.
- Preserve Clean Page and Clean Layered.
- Do not create a global cream theme or implement broad CSS changes.
- Use lower-cost agents for value/selector inventory only. The strong lead owns the design proposal.

Deliver and commit `webapp/design_reviews/ui_workstream/C1-handoff.md` with the decision spec, token mapping, affected selectors, migration order, risks, and a reproducible screenshot/mockup manifest for C2.
```

### C2 — Claude consistency critique

**Starting model:** Claude with an available strong reasoning model (Codex reasoning labels do not apply).

**Prerequisite:** C1 proposal and screenshots.

**Goal:** challenge the proposed system before implementation. Read-only.

**Starter prompt for Claude**

```text
Critique the proposed Clean Editorial Precision system for the private eight-player TEG golf app. Do not edit code.

Starting recommendation: Claude with an available strong reasoning model (Codex reasoning labels do not apply). Before reviewing, flag any model or reasoning limitation that affects this critique. The owner selects the lead model; do not claim to switch it yourself.
Read the model guidance and operating rules in webapp/design_reviews/ui-implementation-roadmap.md before starting.

Inputs:
- webapp/design_reviews/gpt-ui-review.md
- webapp/design_principles.md
- the C1 decision spec, token mapping, and phone/tablet/desktop mockups
- current screenshots for comparison

Test the proposal against:
- three-second score scanning;
- bright outdoor phone use;
- bespoke golf/editorial character;
- avoidance of generic AI-dashboard cards, padding, gradients, blur, and template styling;
- hierarchy without making all headings green;
- Clean Page and Clean Layered invariants;
- restrained use of Lora and tabular Inter data.

Return only:
1. elements to keep;
2. changes required before implementation;
3. risks or inconsistencies;
4. a recommended final token/hierarchy/control decision.

Do not expand scope into admin, setup, score input, live operations, or data updates.
```

### C3 — implement the shared foundation

**Starting model:** Astra Medium.

**Prerequisite:** C2 findings resolved by the owner/Codex lead.

**Goal:** implement tokens, heading roles, and control primitives without migrating every page.

**Likely files:** `webapp/design_principles.md`, `webapp/static/themes/base-vars.css`, Clean theme files, and the smallest representative templates/tests.

**Starter prompt**

```text
Implement the approved Clean Editorial Precision foundation only.

Starting recommendation: Astra Medium. Before implementation, flag whether this task needs higher reasoning or another lead model, and explain why. The owner controls that setting. Continue safe work while awaiting any optional switch; delegate cheaper work as instructed.
Read the model guidance and operating rules in webapp/design_reviews/ui-implementation-roadmap.md before starting.

Read:
- webapp/design_reviews/ui-implementation-roadmap.md: C3
- the approved C1 specification and resolved C2 critique
- webapp/design_principles.md
- webapp/README.md theme invariants
- current base-vars.css and Clean theme files

Goal:
Add and document the approved type, spacing, radius, rule, state, heading, and control tokens. Apply them to the smallest representative components needed to prove the system.

Rules:
- Do not perform a mechanical global font-size replacement.
- Preserve existing public page behaviour and both Clean layouts.
- Flag shared selectors that affect untouched pages before changing them.
- Do not redesign page-specific content here.
- Do not touch excluded operational surfaces.
- Lower-cost workers may handle mechanical token declarations or docs with disjoint ownership. The lead integrates shared CSS.

Verify representative /leaderboard, /records, /latest-round, /scorecard, /player, and /teg-reports pages at 390/768/1280px in light/dark. Run focused template/style tests and update design documentation.
```

### C4 — apply responsive and table contracts

**Starting model:** Astra Medium.

**Prerequisite:** C3.

**Goal:** make public table behaviour intentional across phone, tablet portrait, and desktop without forcing one renderer or one breakpoint onto every page.

**Starter prompt**

```text
Apply the approved responsive and table contracts to public analysis pages.

Starting recommendation: Astra Medium. Before implementation, flag whether this task needs higher reasoning or another lead model, and explain why. The owner controls that setting. Continue safe work while awaiting any optional switch; delegate cheaper work as instructed.
Read the model guidance and operating rules in webapp/design_reviews/ui-implementation-roadmap.md before starting.

Read:
- webapp/design_reviews/ui-implementation-roadmap.md: C4
- the accepted C1/C3 specification and diff
- webapp/design_principles.md: Tables and mobile reference implementation
- webapp/MOBILE_PLAN.md, verifying claims against current code
- current public table templates and mobile.css

Contract:
- Phone: compressed data, protected identity columns, intentional bottom navigation.
- Tablet portrait: simplified columns and clear navigation.
- Desktop: full rounds and analysis.
- Route-specific exceptions remain documented.

Rules:
- Reuse proven patterns, especially Latest Round, where appropriate.
- Do not force every table into cards, horizontal scroll, or the same breakpoint.
- Preserve player-name shortening and domain-specific score shapes.
- Do not touch operational/admin tables.
- Reconcile stale MOBILE_PLAN text that this work proves wrong.
- Use lower-cost agents for overflow detection and screenshot matrices, not shared-CSS decisions.

Verify leaderboard, results, records, player, scorecard, latest-round, and scoring pages at 320/390/430/768/1280px in light/dark, plus focused tests.
```

### C5 — tighten leaderboard rhythm and controls

**Starting model:** Astra Medium.

**Prerequisite:** C4.

**Goal:** reduce chrome and improve score scanning without changing the standings data architecture.

**Starter prompt**

```text
Improve only public leaderboard/results rhythm and control grammar using the approved shared UI system.

Starting recommendation: Astra Medium. Before implementation, flag whether this task needs higher reasoning or another lead model, and explain why. The owner controls that setting. Continue safe work while awaiting any optional switch; delegate cheaper work as instructed.
Read the model guidance and operating rules in webapp/design_reviews/ui-implementation-roadmap.md before starting.

Read:
- webapp/design_reviews/ui-implementation-roadmap.md: C5
- webapp/design_reviews/gpt-ui-review.md: Tighten leaderboard rhythm
- the accepted C1/C3 system
- webapp/design_principles.md: Tables, Components, and controls
- current leaderboard/results routes, templates, partials, CSS, and tests

Goal:
- Put view and Net/Gross measure choices in one compact control zone.
- Remove redundant labels and empty vertical space.
- Keep champion and wooden spoon as one concise facts rail.
- Start the table sooner and make Total visually primary.
- Use weight, rule, or restrained sand for leader emphasis.

Rules:
- Do not add Gap.
- Do not unify renderers or delete lb_cards yet; that is I1.
- Do not change charts or backend calculations.
- Preserve links, ties, empty states, and current phone table behaviour.
- A balanced lower-cost worker may own a bounded template/CSS slice. The lead owns composition and integration.

Verify five-player historical and eight-player views, Net/Gross, ties, empty states, phone/tablet/desktop, light/dark, and focused tests.
```

### C6 — Consistent UI review gate

**Starting model:** Sol High.

**Prerequisite:** C4–C5 accepted.

**Goal:** confirm that the public site now reads as one system. Read-only.

**Starter prompt for Claude or a fresh strong reviewer**

```text
Review the completed TEG Consistent UI stage without editing files.

Starting recommendation: Sol High. Before implementation, flag whether this task needs higher reasoning or another lead model, and explain why. The owner controls that setting. Continue safe work while awaiting any optional switch; delegate cheaper work as instructed.
Read the model guidance and operating rules in webapp/design_reviews/ui-implementation-roadmap.md before starting.

Read:
- webapp/design_reviews/gpt-ui-review.md
- the approved C1 system specification
- webapp/design_principles.md
- the combined C3–C5 diff and screenshot matrix

Check:
- heading hierarchy;
- type, spacing, radius, rule, colour, and focus consistency;
- tabs, segmented measures, and compact actions;
- phone/tablet/desktop table contracts;
- leaderboard scan speed and chrome reduction;
- both Clean-family layouts in light and dark modes;
- any drift into generic dashboard styling.

Report blockers, non-blocking follow-ups, exact evidence, and a ready/not-ready verdict for Improve. Do not suggest a new aesthetic yet.
```

---

## Improve

### I1 — unify the public standings renderer

**Starting model:** Sol High.

**Prerequisite:** C6 ready verdict.

**Goal:** replace duplicate active/stale standings paths with one semantic responsive renderer.

**Starter prompt**

```text
Unify the public leaderboard/results standings renderer.

Starting recommendation: Sol High. Before implementation, flag whether this task needs higher reasoning or another lead model, and explain why. The owner controls that setting. Continue safe work while awaiting any optional switch; delegate cheaper work as instructed.
Read the model guidance and operating rules in webapp/design_reviews/ui-implementation-roadmap.md before starting.

Read:
- webapp/design_reviews/ui-implementation-roadmap.md: I1
- webapp/design_reviews/gpt-ui-review.md: unified standings recommendation and correction about active phone tables
- webapp/design_principles.md: Tables
- accepted Consistent UI commits
- current history/leaderboard routes, standings partials, lb_cards markup/CSS, and tests

Support:
- full rounds on desktop;
- an intentional compact round treatment on phone/tablet;
- player links, ties, empty states, leader treatment, and Gross/Net behaviour.

Rules:
- Preserve analytical values and route contracts.
- Do not add Gap.
- Keep the race chart intact.
- Search all uses before deleting stale card markup/CSS.
- Delete the stale path only after browser and test evidence proves nothing uses it.
- Do not touch admin or live-round tables.
- Use a lower-cost explorer for usage/test inventory. A balanced worker may implement a bounded partial; the lead owns route contracts and deletion.

Verify five-player and eight-player data, Gross/Net, ties, links, empty states, 320/390/768/1280px, light/dark, and relevant tests.
```

### I2 — standardise public interaction and URL state

**Starting model:** Sol High.

**Prerequisite:** C6; I1 recommended.

**Goal:** make public tabs and filters honest, reload-safe, shareable, and predictable with Back.

**Starter prompt**

```text
Standardise public tab, filter, loading, error, retry, and canonical URL behaviour.

Starting recommendation: Sol High. Before implementation, flag whether this task needs higher reasoning or another lead model, and explain why. The owner controls that setting. Continue safe work while awaiting any optional switch; delegate cheaper work as instructed.
Read the model guidance and operating rules in webapp/design_reviews/ui-implementation-roadmap.md before starting.

Read:
- webapp/design_reviews/ui-implementation-roadmap.md: I2
- webapp/design_reviews/gpt-ui-review.md: control grammar and interaction state
- webapp/design_principles.md: Components
- the shared interaction-state TODO
- current public HTMX routes/templates and ui-polish.js

Goal:
- Tabs represent views.
- Segmented controls represent mutually exclusive measures.
- Compact buttons represent actions.
- Selected state changes only after a successful response.
- Loading, error, and retry use one public pattern.
- Public tabs/filters have canonical URLs that survive reload, sharing, and Back.

Rules:
- Inventory and decide the shared contract before migrating pages.
- Keep latest-round changes bounded; do not casually rewrite its audited state machine.
- Do not alter score-writing, polling, admin forms, or data-update flows.
- A lower-cost explorer may map current URL/state patterns and tests. The lead owns the contract and shared JavaScript.

Verify direct links, reload, Back/forward, failed and successful HTMX responses, history entries, and focused route/browser tests.
```

### I3 — draft the Contents product contract

**Starting model:** Astra High.

**Prerequisite:** C6. I2 is helpful but not required.

**Goal:** propose what `/contents` should communicate before implementation. Read-only/design chat.

**Starter prompt**

```text
Design the product/content contract for turning public /contents into a current-TEG home. Do not edit code.

Starting recommendation: Astra High. Before implementation, flag whether this task needs higher reasoning or another lead model, and explain why. The owner controls that setting. Continue safe work while awaiting any optional switch; delegate cheaper work as instructed.
Read the model guidance and operating rules in webapp/design_reviews/ui-implementation-roadmap.md before starting.

Read:
- webapp/design_reviews/gpt-ui-review.md: Site functionality and Contents recommendation
- webapp/design_reviews/ui-implementation-roadmap.md: I3
- the Contents redesign TODO and linked mockup, treating it as a proposal rather than authority
- webapp/design_principles.md
- current contents route/template, nav.py, latest/history/report routes, and relevant tests

Define three states:
1. TEG in progress;
2. latest TEG complete;
3. no usable/current data.

For each state, specify exact data, hierarchy, primary and secondary actions, concise copy, and how the complete public sitemap remains available below.

Rules:
- Lead with tournament state, not a prettier sitemap.
- Preserve access to every public destination.
- Do not invent data the current loaders cannot provide cheaply and truthfully.
- Do not touch admin/setup navigation.
- Use a lower-cost explorer to inventory route labels, data availability, and all existing links.
- Do not ask a review agent to edit or silently resolve design choices.

Deliver and commit `webapp/design_reviews/ui_workstream/I3-handoff.md` with the proposed state matrix, wireframes, data contract, copy, link inventory, edge cases, and implementation acceptance criteria for I4.
```

### I4 — Claude Contents critique

**Starting model:** Claude with an available strong reasoning model (Codex reasoning labels do not apply).

**Prerequisite:** I3 proposal and mockups.

**Goal:** independently challenge the information hierarchy before implementation. Read-only.

**Starter prompt for Claude**

```text
Critique the proposed TEG /contents current-tournament home. Do not edit code.

Starting recommendation: Claude with an available strong reasoning model (Codex reasoning labels do not apply). Before reviewing, flag any model or reasoning limitation that affects this critique. The owner selects the lead model; do not claim to switch it yourself.
Read the model guidance and operating rules in webapp/design_reviews/ui-implementation-roadmap.md before starting.

Read:
- webapp/design_reviews/gpt-ui-review.md: Contents recommendation
- webapp/design_reviews/ui-implementation-roadmap.md: I3–I4
- webapp/design_principles.md
- the I3 state matrix, copy, data contract, wireframes, and current page screenshots

Review:
- whether in-progress, complete, and no-data states are immediately clear;
- whether the primary action is correct and honest in each state;
- whether all eight repeat users can still find history, records, scorecards, reports, and analysis;
- phone and desktop hierarchy;
- duplication with top navigation;
- any slide into generic dashboard cards or promotional hero styling.

Return exact changes required, elements to keep, unresolved product decisions, and an approve/revise verdict. Do not expand scope into admin/setup navigation or invent unavailable data.
```

### I5 — implement Contents as the current-TEG home

**Starting model:** Astra Medium.

**Prerequisite:** I4 findings resolved and contract approved; I2 recommended.

**Goal:** implement the approved state-led Contents page without losing any public destination.

**Starter prompt**

```text
Implement the approved /contents current-TEG home contract.

Starting recommendation: Astra Medium. Before implementation, flag whether this task needs higher reasoning or another lead model, and explain why. The owner controls that setting. Continue safe work while awaiting any optional switch; delegate cheaper work as instructed.
Read the model guidance and operating rules in webapp/design_reviews/ui-implementation-roadmap.md before starting.

Read:
- webapp/design_reviews/ui-implementation-roadmap.md: I5
- the approved I3 state matrix, data contract, wireframes, copy, and link inventory plus resolved I4 critique
- accepted Consistent UI and interaction-state work
- current contents route/template and focused tests

Rules:
- Implement in-progress, complete, and no-data states exactly as approved.
- Keep the full public sitemap available below the primary state area.
- Reuse existing loaders/helpers where appropriate; do not duplicate tournament completion logic.
- Preserve honest empty and failure states.
- Do not touch admin, setup, score entry, live operations, or data updates.
- A balanced lower-cost worker may own either the route/data slice or the template/CSS slice, never both without lead review. Assign non-overlapping files.

Verify every link, all three states, 390/768/1280px, light/dark, reload/direct navigation, relevant tests, and the three-second product test. Update the Contents TODO and user-visible status documentation.
```

### I6 — Improve review gate

**Starting model:** Sol High.

**Prerequisite:** I1–I5 accepted.

**Goal:** verify function and product clarity before any aesthetic experiment. Read-only.

**Starter prompt for a fresh strong reviewer**

```text
Review the completed TEG Improve stage without editing files.

Starting recommendation: Sol High. Before implementation, flag whether this task needs higher reasoning or another lead model, and explain why. The owner controls that setting. Continue safe work while awaiting any optional switch; delegate cheaper work as instructed.
Read the model guidance and operating rules in webapp/design_reviews/ui-implementation-roadmap.md before starting.

Read:
- webapp/design_reviews/gpt-ui-review.md
- webapp/design_reviews/ui-implementation-roadmap.md: Improve
- webapp/design_principles.md
- combined diffs, test results, and screenshot matrix for I1–I5

Check:
- one active standings renderer with correct data and responsive behaviour;
- honest, canonical public interaction state;
- Contents communicates current tournament state in three seconds;
- all links, ties, empty states, Gross/Net, and five/eight-player cases;
- no regression into excluded operational flows;
- no aesthetic experiment has leaked in early.

Report blockers, non-blocking follow-ups, exact evidence, and a ready/not-ready verdict for Experiment.
```

### I7 — optional performance/hygiene track

**Starting model:** Astra Medium for fonts/lab isolation; Sol High for Plotly/Tailwind.

**Prerequisite:** run after I1/I2, or defer until the core path is complete.

Do not combine these into one risky chat. Open one chat per item: conditional Plotly loading, pinned Tailwind build, unused font removal, or development-only lab/debug isolation.

**Reusable starter prompt — replace `[ONE ITEM]` before sending**

```text
Implement exactly one TEG public UI maintenance item: [ONE ITEM]. Do not bundle adjacent cleanup.

Starting recommendation: Astra Medium for fonts/lab isolation; Sol High for Plotly/Tailwind. Before implementation, flag whether this task needs higher reasoning or another lead model, and explain why. The owner controls that setting. Continue safe work while awaiting any optional switch; delegate cheaper work as instructed.
Read the model guidance and operating rules in webapp/design_reviews/ui-implementation-roadmap.md before starting.

Read:
- webapp/design_reviews/gpt-ui-review.md: Do later
- webapp/design_reviews/ui-implementation-roadmap.md: I7
- webapp/README.md sections relevant to this asset or tool
- the current templates, routes, static assets, and tests that use it

First inventory every production and development use. Define a measurable before/after result. Then make the smallest change that preserves required public behaviour.

Rules:
- Do not change visual design, chart behaviour, or data contracts.
- Do not touch admin/data-update flows unless the selected asset is shared; report a shared dependency before broadening scope.
- For Plotly, prove every chart route still loads and redraws after HTMX swaps.
- For Tailwind, prove the production build contains every dynamic class the templates require.
- For fonts, prove no rendered surface uses the removed face.
- For lab/debug isolation, prove production routes cannot expose the tool while local development remains documented.
- Use a lower-cost agent for dependency inventory and network/browser measurements. The lead owns the implementation.

Run focused tests and browser/network checks. Update the exact TODO or documentation. Claude review is not required.
```

---

## Experiment

### E1 — build reversible Editorial Golf variants

**Starting model:** Astra High.

**Prerequisite:** I6 ready verdict.

**Goal:** produce two or three real-data variants on leaderboard/results without changing the default production direction.

**Starter prompt**

```text
Build reversible Editorial Golf variants for the public leaderboard/results surface using current TEG data.

Starting recommendation: Astra High. Before implementation, flag whether this task needs higher reasoning or another lead model, and explain why. The owner controls that setting. Continue safe work while awaiting any optional switch; delegate cheaper work as instructed.
Read the model guidance and operating rules in webapp/design_reviews/ui-implementation-roadmap.md before starting.

Read:
- webapp/design_reviews/gpt-ui-review.md: Direction B and code prototype
- webapp/design_reviews/claude-ui-review.md: Editorial Golf source ideas, checking claims against current code
- webapp/design_principles.md
- accepted Consistent UI and Improve work
- current report/newspaper CSS for reusable typography and rule language

Test controlled variations in:
- white versus lightly warm competition surface;
- Lora event identity versus player-name emphasis;
- hairline versus restrained double scorecard rules;
- sand tint versus green inset rule for the leader;
- compact champion/wooden-spoon facts rail.

Rules:
- Use current data structures and no Gap field.
- Keep variants scoped, reversible, and isolated from the default.
- Do not convert the whole site to cream paper.
- No gradients, blur, floating cards, decorative icon sets, or generic dashboard chrome.
- Preserve outdoor contrast, links, ties, empty states, and responsive behaviour.
- Use lower-cost agents for selector audit and screenshot capture only. The strong lead owns the variants.

Deliver and commit `webapp/design_reviews/ui_workstream/E1-handoff.md` with the screenshot manifest, exact side-by-side reproduction states, tradeoffs, and a recommendation for E2. Do not roll the experiment out.
```

### E2 — Claude experiment critique

**Starting model:** Claude with an available strong reasoning model (Codex reasoning labels do not apply).

**Prerequisite:** E1 variants and comparison pack.

**Goal:** obtain an independent taste and usability critique. Read-only.

**Starter prompt for Claude**

```text
Critique the rendered TEG Editorial Golf variants. Do not edit code.

Starting recommendation: Claude with an available strong reasoning model (Codex reasoning labels do not apply). Before reviewing, flag any model or reasoning limitation that affects this critique. The owner selects the lead model; do not claim to switch it yourself.
Read the model guidance and operating rules in webapp/design_reviews/ui-implementation-roadmap.md before starting.

Read:
- webapp/design_reviews/gpt-ui-review.md
- webapp/design_principles.md
- the E1 comparison pack at phone, tablet portrait, and desktop in light/dark
- the Clean Precision baseline screenshots

Judge each variant on:
- three-second leader/Total scanning;
- sunlight readability;
- bespoke golf/editorial character;
- restraint and information density;
- consistency with reports without making the app imitate a newspaper everywhere;
- avoidance of generic AI-dashboard or decorative heritage styling.

Return:
1. the strongest elements across variants;
2. elements to reject;
3. one recommended composite with precise changes;
4. unresolved risks to test with the eight users.

Do not expand scope or implement changes. The owner makes the selection; Codex remains the editor.
```

### E3 — implement the selected leaderboard pilot

**Starting model:** Astra Medium.

**Prerequisite:** owner decision after E2.

**Goal:** turn the selected composite into a production-quality but still reversible pilot on leaderboard/results.

**Starter prompt**

```text
Implement only the owner-selected Editorial Golf pilot on public leaderboard/results.

Starting recommendation: Astra Medium. Before implementation, flag whether this task needs higher reasoning or another lead model, and explain why. The owner controls that setting. Continue safe work while awaiting any optional switch; delegate cheaper work as instructed.
Read the model guidance and operating rules in webapp/design_reviews/ui-implementation-roadmap.md before starting.

Read:
- webapp/design_reviews/ui-implementation-roadmap.md: E3
- the owner’s explicit E2 selection
- accepted E1 variants and rejection notes
- webapp/design_principles.md
- current unified standings implementation and tests

Rules:
- Implement only selected elements; do not revive rejected ideas.
- Keep the pilot scoped and easy to revert.
- Preserve all data, links, ties, empty states, Gross/Net behaviour, and responsive contracts.
- Do not add Gap or change charts.
- Do not expand to player, records, scoring, admin, or operational pages.
- A balanced lower-cost worker may implement a scoped template/CSS slice. The strong lead owns visual integration and browser review.

Verify five/eight-player cases, phone/tablet/desktop, light/dark, both Clean-family layouts, focused tests, and side-by-side baseline captures. Document the experiment status without declaring it the final direction.
```

### E4 — extend to reports, optional

**Starting model:** Astra Medium.

**Prerequisite:** E3 accepted and an explicit owner decision to test reports.

**Starter prompt**

```text
Extend only the accepted Editorial Golf language to the public /teg-reports surface.

Starting recommendation: Astra Medium. Before implementation, flag whether this task needs higher reasoning or another lead model, and explain why. The owner controls that setting. Continue safe work while awaiting any optional switch; delegate cheaper work as instructed.
Read the model guidance and operating rules in webapp/design_reviews/ui-implementation-roadmap.md before starting.

Read:
- webapp/design_reviews/gpt-ui-review.md: Direction B
- accepted E3 decision and screenshots
- webapp/TODOS.md report formatting entry
- webapp/static/newspaper_preview.css
- webapp/static/teg_reports.css
- webapp/templates/teg_reports.html
- report PDF build documentation

Goal:
Make app and report feel related through ink, green, rules, tabular standings, and label blocks while preserving the report’s stronger newspaper identity.

Rules:
- Do not alter report generation, analysis, or prose voice.
- Do not touch admin report generation.
- Do not turn reports into generic cards.
- Remember that changing newspaper_preview.css makes report PDFs stale; run the documented check/build only if that file changes.
- Keep phone and desktop report content readable.

Use a lower-cost explorer for class and screenshot inventory. The lead owns any shared report styling and PDF implications.
```

### E5 — compare Telemetry mechanics, optional

**Starting model:** Astra High.

**Prerequisite:** E3, or an explicit owner request for an alternative before E3.

**Starter prompt**

```text
Create a reversible Modern Telemetry comparison on the public leaderboard only.

Starting recommendation: Astra High. Before implementation, flag whether this task needs higher reasoning or another lead model, and explain why. The owner controls that setting. Continue safe work while awaiting any optional switch; delegate cheaper work as instructed.
Read the model guidance and operating rules in webapp/design_reviews/ui-implementation-roadmap.md before starting.

Read:
- webapp/design_reviews/gpt-ui-review.md: Direction C
- webapp/design_reviews/claude-ui-review.md: telemetry ideas
- accepted Clean Precision and Editorial Golf screenshots
- webapp/design_principles.md

Test mechanics only: compact tabular rows, sharper live/final status, square restrained badges, compact round strips, and optional micro-comparison treatment.

Rules:
- Do not make dark-first the default.
- No acid accents, broadcast effects, gradients, blur, or generic dashboard cards.
- Do not change analytical data or add Gap.
- Keep the variant isolated and removable.
- Compare mechanics independently so the owner can borrow one without adopting the whole direction.

Deliver comparison screenshots and a keep/reject recommendation. Do not roll out the variant.
```

---

## Test and decide

### T1 — technical visual QA

**Starting model:** Sol High.

**Prerequisite:** E3; include E4/E5 if produced.

**Goal:** prove the candidate is technically stable before asking the group to judge it.

**Starter prompt**

```text
Run technical visual QA on the candidate TEG public UI. Fix nothing in this chat.

Starting recommendation: Sol High. Before implementation, flag whether this task needs higher reasoning or another lead model, and explain why. The owner controls that setting. Continue safe work while awaiting any optional switch; delegate cheaper work as instructed.
Read the model guidance and operating rules in webapp/design_reviews/ui-implementation-roadmap.md before starting.

Read:
- webapp/design_reviews/ui-implementation-roadmap.md
- webapp/design_reviews/gpt-ui-review.md
- webapp/design_principles.md
- accepted diffs and prior screenshot baselines

Matrix:
- 320, 390, 430, 768, and 1280px;
- light and dark;
- Clean Page and Clean Layered layouts;
- five-player historical and eight-player data;
- current/complete/no-data states where relevant.

Check every public route for clipping, overflow, heading/control drift, nav overlap, stale state, broken Back/reload, missing links, unexpected assets, and console errors. Run only relevant automated tests and document why each was selected.

Use lower-cost agents for parallel read-only screenshot and route matrices with disjoint route groups. The strong lead verifies findings and commits `webapp/design_reviews/ui_workstream/T1-handoff.md` with one prioritised defect list and the complete reproduction matrix. Do not touch excluded operational surfaces.
```

### T2 — run the eight-user comparison and choose

**Starting model:** Astra High.

**Prerequisite:** T1 blockers resolved in separate bounded chats.

**Goal:** choose the default direction using task performance and preference, not design taste alone.

**Starter prompt**

```text
Prepare and synthesise the final TEG public UI comparison with all eight tournament users. Do not implement changes.

Starting recommendation: Astra High. Before implementation, flag whether this task needs higher reasoning or another lead model, and explain why. The owner controls that setting. Continue safe work while awaiting any optional switch; delegate cheaper work as instructed.
Read the model guidance and operating rules in webapp/design_reviews/ui-implementation-roadmap.md before starting.

Read:
- webapp/design_reviews/gpt-ui-review.md
- the Clean Precision baseline and accepted experiment builds
- T1 technical QA result

Ask each user to:
1. find the current leader and Total;
2. switch Gross/Net or the available measure;
3. expand round detail;
4. find the latest round;
5. find the latest report;
6. find one historical record;
7. use the phone view outdoors or in bright light;
8. reload or use Back and continue successfully.

Record task success, time to first correct answer, wrong taps, visual confusion, device/viewport, and concise preference comments. Compare Clean Precision, Editorial Golf, and only the Telemetry mechanics actually built.

Return one decision:
- retain Clean Precision;
- extend Editorial Golf;
- adopt named Telemetry mechanics;
- or reject the experiment.

All eight users must be represented. Do not infer missing feedback or keep permanent parallel themes by default.
```

### T3 — record the decision and create the rollout backlog

**Starting model:** Astra Medium.

**Prerequisite:** T2 owner decision.

**Goal:** close the experiment and turn only the chosen direction into later bounded work.

**Starter prompt**

```text
Record the owner-approved TEG public UI decision and create the smallest rollout backlog. Make documentation changes only.

Starting recommendation: Astra Medium. Before implementation, flag whether this task needs higher reasoning or another lead model, and explain why. The owner controls that setting. Continue safe work while awaiting any optional switch; delegate cheaper work as instructed.
Read the model guidance and operating rules in webapp/design_reviews/ui-implementation-roadmap.md before starting.

Read:
- the T2 decision and evidence
- webapp/design_reviews/gpt-ui-review.md
- webapp/design_reviews/ui-implementation-roadmap.md
- webapp/README.md
- webapp/TODOS.md
- STATUS.md

Update documentation to state:
- the chosen default direction and rejected alternatives;
- evidence from the eight-user test;
- which pilot code remains or should be removed;
- the next public pages, each as a separate bounded future chat;
- any newly discovered defects;
- that excluded admin/operational recommendations remain deferred.

Do not implement rollout code, reopen Gap-to-leader, or broaden scope. Check local links and Markdown formatting. No application tests are needed for docs-only changes.
```

---

## Deferred workstream seeds

These are documented so they are not lost, but they are not prerequisites for any chat above.

- **Live score-entry truthfulness:** pending, saved, failed, and retry states; idempotent retry behaviour; polling feedback. Open only when score-entry/live-round work is explicitly authorised.
- **Admin and data-update feedback:** one progress/success/warning/failure/retry language, exact previews, and preservation of fail-loudly pipeline semantics. Open only as an admin/data workstream.
- **TEG and round setup consistency:** apply the eventual type/control tokens without redesigning task-focused forms. Open only after the public system is stable.
- **Operational theming:** tokenise live-entry/live-leaderboard colours before extending dark mode. Do not mix this with the public aesthetic pilot.

Each future chat must begin by rereading the operational recommendations in `gpt-ui-review.md`, current invariants in `CLAUDE.md`, and the relevant analysis/admin documentation. It must create its own plan because those flows have higher data-integrity risk than the public read-only UI.

## Recommended immediate start

Open P0 first. Once its evidence pack is accepted, F1 and F2 are the quickest independent trust repairs. F3 can be investigated alongside them, but shared `mobile.css` edits must be sequenced. F4 follows F2. F5 lands last. F6 is the first Claude gate.
