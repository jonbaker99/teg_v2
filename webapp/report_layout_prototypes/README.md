# Newspaper report layout — the settled design

Tournament reports are presented as a **newspaper edition**: a lead story on the Trophy winner,
the remaining storylines as separate articles. This folder holds the prototypes that settled that
design and the record of how each choice was made.

**The design is decided, and the code that serves it is written** — `/teg-reports-preview`
(`webapp/routes/report_preview.py`), not linked from the nav, `/teg-reports` untouched.
⚠️ **The route is not reachable on `main`**: merge `9b6f423` dropped the `report_preview` import and
`app.include_router(report_preview.router)` line from `webapp/app.py`. Restoring those two lines is
the whole fix. See [Still to do](#still-to-do).

Where this sits in the wider pipeline: `DATA_FLOW.md` → §10 *Report build*.

Served at `/report-layouts/` when the webapp runs (mounted in `webapp/app.py` beside `/mockups/`).

## The files

| File | What it is for |
|---|---|
| `composite.html` | **The desktop design.** The chosen elements assembled, with the composition rule as its default. This is the thing to build from. |
| `mobile.html` | **The mobile design.** Pattern A is chosen and is the default; B and C remain switchable as the record. |
| `elements.html` | The element-by-element chooser: ten elements, 4–5 variants each, all on identical copy so only the element varies. Its job is done; it is the tool to reopen any single choice. |
| `newspaper.html` | The original four directions (A Broadsheet, B Modern editorial, C Sports section, D Back page) that settled the overall approach. Kept as the record. |
| `editions.json` | Content for TEG 14, 16 and 18, built by `scripts/build_newspaper_edition.py`. **Feeds these prototype pages only** — the live route builds its edition in memory and never reads this file. |
| `checks/check_mobile_patterns.py` | Browser assertions on the mobile patterns. Not in the pytest suite — see [Checks](#checks). |

## The design

### Elements

Chosen one at a time against rendered specimens in `elements.html`:

| Element | Chosen |
|---|---|
| Type & palette | **T1** broadsheet — Fraunces / Source Serif 4, cream paper, oxblood accent |
| Masthead | **M1** wordmark left, dateline right, thick/thin rule under |
| Results panel | **R5** ruled scorecard, mono tabular values, with the runner-up under each line |
| Lead headline | **H1** kicker over, italic standfirst under |
| Drop cap | **D2** three-line Fraunces initial |
| Lead body | **B2** two columns, hairline rule |
| Card treatment | **C2** ruled columns, no gaps, no boxes *(desktop only)* |
| Kickers | **K1** plain mono caps in the accent colour |
| Standings rail | **S2** results and final standings beside the lead, **nothing below them** |
| Appendices | **P1** open at the foot — standings full width, records in two columns beneath |

### Desktop composition

The **Auto** setting in `composite.html`, and its default:

- **Five or more stories → E2 second lead.** A fifth story leaves E1's 3-up row with an orphan
  spanning the page; E2 promotes one story to a second lead and the remaining three fill the row.
- **Fewer than five → E1 classic front**, where three sub-articles fit the row exactly.
- **The second lead defaults to the Green Jacket**, as the second competition. A discovered
  storyline takes the slot only when it beats it by `CLEAR_MARGIN` (2) or more on
  `compelling_score`.

### Mobile

**Pattern A, index first.** The front screen is the masthead, the results and the headlines; each
article is its own screen. Stacking the desktop grid vertically was the thing being fixed, and
measured first-screen length is the evidence:

| | Pattern | First screen |
|---|---|---|
| — | *desktop composite at 390px* | *9,069px — 10.7 phone screens* |
| **A** | **Index first** | **921px — 1.1 screens** |
| B | Swipeable cards | 1,268px — 1.5 screens |
| C | Accordion | 1,815px closed, 3,698px with two sections open |

A and B are built to ship: hash routing so the phone's Back gesture works and any screen
deep-links cold, scroll position restored on return to the index, focus moved to the article
heading, 44px touch targets, `env(safe-area-inset-*)` and `100dvh`, full `tablist`/`tabpanel`
semantics with arrow keys on B and Escape on A. C was left at prototype quality.

## Content

`teg_analysis/reporting/newspaper_edition.py` turns a `storyline_plan.json` plus a
`report_storylinefirst_styled.md` into an edition object. Deterministic, no LLM, no cost. It lives in
the package, not in `scripts/`, because `webapp/` cannot import from `scripts/` and the live route
needs the same parser; it reads through `teg_analysis.io.read_text_file`, so it works on Railway's
volume as well as locally.

⚠️ `scripts/build_newspaper_edition.py` **is currently a second copy of that parser**, not the thin
CLI wrapper it was reduced to — merge `9b6f423` restored the old body. The two are byte-identical
apart from the file reads, so they agree today and will diverge on the next parser change.

```bash
python -m scripts.build_newspaper_edition    # rebuilds editions.json
python -m scripts.inline_editions            # pushes it back into the pages
```

The pages carry the data inline because a published Artifact cannot fetch a sibling file.

## Checks

`checks/check_mobile_patterns.py` asserts routing, the Back gesture, scroll restore, focus
movement, tab and keyboard control, touch-target sizes and horizontal overflow. It needs a browser
and a served copy of the folder, so it is a by-hand step rather than part of pytest:

```bash
python -m http.server 8899 --bind 127.0.0.1 --directory webapp/report_layout_prototypes &
python webapp/report_layout_prototypes/checks/check_mobile_patterns.py
```

Run it at 390×844 and again at 1280×900 — the two take different code paths, and only the first
matters to a reader.

## Still to do

1. **Written as a preview; currently unregistered, and not yet switched over.**
   ⚠️ **Do this first:** merge `9b6f423` dropped `report_preview` from `webapp/app.py`'s router
   imports and its `include_router` call, so the page 404s despite every file being present.
   Everything below describes the code as written. `/teg-reports-preview`
   (`webapp/routes/report_preview.py` + `webapp/templates/teg_reports_preview.html`) renders the
   settled layout: desktop server-side (`teg_analysis.reporting.newspaper_edition.render_desktop_html`,
   a straight Python port of `composite.html`'s JS — no interactivity needed there), mobile pattern
   A client-side (`webapp/static/newspaper_preview.js`, ported from `mobile.html`'s pattern A only —
   index screen + one screen per article, hash routing so the phone's Back gesture works and any
   article deep-links cold, scroll restored on return to the index, focus moved to the article
   heading). A CSS breakpoint in `webapp/static/newspaper_preview.css` (`max-width:700px`, matching
   mobile.html's own "this is a real phone" breakpoint) picks which stage is visible; both are
   always rendered so a resize across it is instant. Sync `def` handler; reports are read through
   `teg_analysis.io.read_text_file` (volume-then-GitHub aware), not the filesystem — the parser
   moved to `teg_analysis/reporting/newspaper_edition.py` for exactly this (`scripts/` cannot be
   imported from `webapp/`). Verified in a real browser at 390×844 and 1280×900: index → article →
   Back, cold deep-link to `#story/N`, focus-on-open, E1/E2 arrangement both render correctly.
   **Not done yet:** `/teg-reports` itself is untouched and still renders the old one-blob markdown;
   switching it over (or deciding the two coexist) is a separate, deliberately small change once
   the preview is confirmed right.
2. ~~`StorylinePlan` needs `headline` and `standfirst` fields.~~ **Done (2026-09-06).**
   `DraftedStoryline` now carries `headline_candidates`/`chosen_headline`/`standfirst`, mirroring
   `RoundPlan`'s shape (`teg_analysis/reporting/story_plan.py`). `newspaper_edition.py` uses them
   when present, falling back to `_derive_headline`/`_choose_standfirst` only for artefacts that
   predate the fields. TEG 14/16/18 regenerated with real headlines. **Not yet clean** — the model
   still reaches for a two-clause "X — Y" headline over the requested single 3-8 word clause on
   several storylines; `check_storyline_plan_consistency` flags it as a warning rather than
   failing. See `STORYLINE_PLAN.md` → "Real headlines" for detail and the follow-up prompt fix
   needed.
   The parked TEG 14 decision (Wooden Spoon compelling 9 vs Green Jacket 7, margin exactly
   `CLEAR_MARGIN`) is answered there too: regeneration reshuffled the scores (now Jacket 7 vs
   Spoon 6, since `compelling_score` is a per-run LLM rating, not deterministic), so the exact case
   can't be re-litigated — but judged on the real headlines now in the artefact, either would read
   fine as second lead.
3. **A cross-cut section needs a kicker the merge step can name.** ` / `-joined headings are a
   parsing artefact from the mothballed interweave path. Partially addressed: `newspaper_edition.py`
   now joins the matched storylines' own `chosen_headline`s with `&` for a merged article instead of
   truncating to the first fragment. The merge step itself
   (`scripts/storyline_interweave_experiment.py`) still emits a `' / '`-joined `subject` — untouched,
   since interweaving is off by default and this is low priority until it's turned back on.

## Decisions worth not relitigating

- **Newspaper edition over one long report.** Confirmed against the live prototype: markedly more
  digestible.
- **Lead story is always the Trophy winner.** Sub-articles order by `compelling_score` desc, then
  `humour_score` desc.
- **Interweaving is mothballed** (`--interweave`, off by default). Its A/B win stands, but it was
  measured on a flowing document; an edition wants one subject per article. Reasoning:
  `teg_analysis/reporting/STORYLINE_PLAN.md` → *Interweaving mothballed*.
- **G1 "packed" was rejected despite winning on measurement.** A single three-column flow with
  stories breaking across columns was the only arrangement that tessellated consistently —
  column-bottom spread 202/124/8px across TEG 14/16/18, against 66–1348px for everything else —
  and was still rejected as too dense. Measured tessellation is not readability. Do not
  re-propose it on the strength of that number.
- **Balancing whole stories across three columns does not work at this article count.** With three
  to five stories of 220–410 words there are too few pieces; better packing does not help. That is
  what G2 demonstrates.
- **Below 700px the document scrolls, not `.scroller`.** Scroll restore written to the inner
  element silently did nothing on an actual phone while working perfectly in the desktop preview
  frame. Anything touching scroll position needs `scrollHost()`.
