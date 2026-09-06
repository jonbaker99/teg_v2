# Newspaper report layout — the settled design

Tournament reports are presented as a **newspaper edition**: a lead story on the Trophy winner,
the remaining storylines as separate articles. This folder holds the prototypes that settled that
design and the record of how each choice was made.

**The design is decided. What has not happened is wiring it into the site** — see
[Still to do](#still-to-do).

Served at `/report-layouts/` when the webapp runs (mounted in `webapp/app.py` beside `/mockups/`).

## The files

| File | What it is for |
|---|---|
| `composite.html` | **The desktop design.** The chosen elements assembled, with the composition rule as its default. This is the thing to build from. |
| `mobile.html` | **The mobile design.** Pattern A is chosen and is the default; B and C remain switchable as the record. |
| `elements.html` | The element-by-element chooser: ten elements, 4–5 variants each, all on identical copy so only the element varies. Its job is done; it is the tool to reopen any single choice. |
| `newspaper.html` | The original four directions (A Broadsheet, B Modern editorial, C Sports section, D Back page) that settled the overall approach. Kept as the record. |
| `editions.json` | Content for TEG 14, 16 and 18, built by `scripts/build_newspaper_edition.py`. |
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

`scripts/build_newspaper_edition.py` turns a `storyline_plan.json` plus a
`report_storylinefirst_styled.md` into an edition object. Deterministic, no LLM, no cost.

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

1. **Wire it into the site.** `webapp/routes/reports.py` currently renders the styled markdown to
   one HTML blob; the edition parser replaces that. Sync `def` handler (CLAUDE.md invariant), and
   reports are read through `teg_analysis.io.read_text_file` (volume-then-GitHub aware), not the
   filesystem.
2. **`StorylinePlan` needs `headline` (3–8 words) and `standfirst` (one sentence) per storyline.**
   `subject` is neither — it is a 15–25 word descriptive line that works as a section heading and
   fails as a headline. Every layout has to derive one, and derived headlines are the weakest text
   on the page; `_derive_headline` and `_choose_standfirst` in the build script exist only to stop
   that reading as a bug. The unrequested `**bold**` mini-header is this missing field arriving by
   accident about half the time. **Fix it by asking for it**, in `story_plan.py`.
   One decision is parked behind this: on TEG 14 the second-lead slot goes to the Wooden Spoon
   (compelling 9) over the Green Jacket (7), a margin of exactly `CLEAR_MARGIN`. That cannot be
   judged fairly while every headline is derived.
3. **A cross-cut section needs a kicker the merge step can name.** ` / `-joined headings are a
   parsing artefact; the merge should emit a single subject.

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
