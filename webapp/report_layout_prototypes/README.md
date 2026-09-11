# Newspaper report layout — the settled design

Tournament reports are presented as a **newspaper edition**: a lead story on the Trophy winner,
the remaining storylines as separate articles. This folder holds the prototypes that settled that
design and the record of how each choice was made.

**The design is decided and is wired into the site as a preview** at `/teg-reports-preview`
(`webapp/routes/report_preview.py`) — not linked from the nav, `/teg-reports` untouched. See
[Still to do](#still-to-do) for what's left before switching `/teg-reports` over to it.

Where this sits in the wider pipeline: `DATA_FLOW.md` → §10 *Report build*.

Served at `/report-layouts/` when the webapp runs (mounted in `webapp/app.py` beside `/mockups/`).

## The files

| File | What it is for |
|---|---|
| `composite.html` | **The desktop design.** The chosen elements assembled, with the composition rule as its default. This is the thing to build from. |
| `mobile.html` | **The mobile design.** Pattern A is chosen and is the default; B and C remain switchable as the record. |
| `elements.html` | The element-by-element chooser: ten elements, 4–5 variants each, all on identical copy so only the element varies. Its job is done; it is the tool to reopen any single choice. |
| `newspaper.html` | The original four directions (A Broadsheet, B Modern editorial, C Sports section, D Back page) that settled the overall approach. Kept as the record. |
| `editions.json` | Content for whichever TEGs have storyline-first artefacts, built by `scripts/build_newspaper_edition.py` (discovered, not a fixed list). **Feeds these prototype pages only** — the live route builds its edition in memory and never reads this file. |
| `checks/check_mobile_patterns.py` | Browser assertions on the mobile patterns. Not in the pytest suite — see [Checks](#checks). |

## The design

### Elements

Chosen one at a time against rendered specimens in `elements.html`:

| Element | Chosen |
|---|---|
| Type & palette | **T1** broadsheet — Fraunces / Source Serif 4, cream paper, oxblood accent |
| Masthead | **M1** wordmark left, dateline right, thick/thin rule under |
| Results panel | **R5** ruled scorecard, tabular values, with the runner-up under each line. *Mono overridden* — the preview page sets the rail in the body serif with `tabular-nums`, on request (2026-09-08); the rest of R5 stands. |
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
- **Exactly three sub-articles, one materially longer → E3.** `E1`'s 3-up row leaves a badly
  unbalanced column when one sub-article runs much longer than the other two. E3 fires when the
  longest is at least `LONG_STORY_RATIO` (1.4) times the median of the other two's word counts: the
  two shorter subs sit in a 2-up row, the long one runs full width, after the row. Measured
  (longest ÷ median of rest): TEG 16 — 430/273/250 words, 1.64; TEG 18 — 409/247/225 words, 1.73;
  TEG 14 — 289/249/232/220 words, 1.20 (but 5 articles, so it takes E2 regardless). Added in
  `teg_analysis/reporting/newspaper_edition.py` (`choose_arrangement`, `_render_e3`) for the
  `/teg-reports-preview` switch matrix — E1/E2/E3 are all this route's `arr-*` CSS classes in
  `webapp/static/newspaper_preview.css`; `composite.html` itself still only has E1/E2.
- **Otherwise → E1 classic front**, where three sub-articles fit the row exactly.
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

1. **Wired in as a preview; not yet switched over.** `/teg-reports-preview`
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
   the preview is confirmed right. The preview page also currently carries three **provisional**
   switches (`?pal=`, `?sf=`, `?rail=`, alongside the existing `?teg=`) for comparing the type &
   palette, standfirst and standings-rail options directly against real content, server-rendered
   and validated (unrecognised values fall back to the shipped default). `?sf=` carries four
   options: `italic` (H1, the default), `roman` (H2), `edge` (H4) and `contrast` — upright in
   the palette's `--font-contrast`, the opposite family from the headline's `--font-display`
   (a sans under a serif headline and vice versa), so it varies with `?pal=`. This is throwaway
   scaffolding for layout review, not part of the design — remove the switcher markup in
   `teg_reports_preview.html`, its CSS in `newspaper_preview.css`, and the query-param handling in
   `report_preview.py` once the choices are locked in.
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

## The CSS reset trap (fixed 2026-09-08)

`newspaper_preview.css` resets margins and padding on the bare elements the renderers emit. It was
written as `.np-page h1,.np-page h2,...{ margin:0; padding:0 }` — specificity **(0,1,1)**, which
silently beat every single-class component rule **(0,1,0)** on the page. Eight settled values were
computing to `0` without anyone noticing: `.r5-title` padding (the "AT A GLANCE" bar sat flush against
the box edge), `.sb-row` padding, the `margin-top` on `.lead-headline`, `.lead-standfirst`,
`.sub-headline` and `.sub-standfirst`, and the `margin-bottom` on `.apx-h` and `.recs-cat`. The
at-a-glance highlight bleeding outside its box was the same bug via `.r-list` (that tinted
highlight has since been removed from both rail variants, so only the accent-coloured value
marks the trophy row — the bug record stands, the highlight does not).

The first attempt fixed it per-rule, by rewriting the losers as `.np-page .r-list` to out-specify the
reset. That treats the symptom and leaves the trap armed for the next rule someone adds. The reset is
now wrapped in `:where()`, which contributes **zero** specificity — it still beats UA defaults but
loses to every component rule, so the per-rule workarounds could be reverted.

**Do not "simplify" it back to a bare selector list.**

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
- **The production desktop renderer no longer uses named arrangements (E1/E2/E3) at all**
  (2026-09-11) — it packs sub-articles into full-width rows instead (`plan_rows` in
  `teg_analysis/reporting/newspaper_edition.py`), because the old fixed-arrangement system produced
  broken layouts (an orphan single-story row) whenever the leftover count didn't divide evenly.
  `composite.html`'s `chooseArrangement`/`renderE1`/`renderE2` (this file has no E3) predate that
  change and are retained purely as frozen historical reference — they are not kept in sync with
  the Python renderer, and `renderE3` here is a different, unrelated design from the one that
  shipped.
