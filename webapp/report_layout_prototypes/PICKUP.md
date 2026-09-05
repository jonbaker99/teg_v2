# Newspaper layout — picking this up in a new chat

**Read this first.** The trial specification is [PLAN.md](PLAN.md); this file is where it got to and
what to do next. Working doc — delete or fold into `STATUS.md` when a final layout ships
(CLAUDE.md → Documentation rule 3).

**Status: direction confirmed, elements chosen, composition and mobile pattern open.**
Written 2026-09-05, updated the same day.

---

## Where this got to

**Update — the element-by-element pass has run.** Jon chose from `elements.html`, and the
vocabulary below is settled. What is still open is narrower: how the blocks compose on the page
(`composite.html`, E1/E2/E3 + rail fill F1/F2/F3) and which mobile pattern wins (`mobile.html`,
A/B/C). See *Open* below.

| Element | Chosen |
|---|---|
| Type & palette | **T1** broadsheet — Fraunces / Source Serif, cream, oxblood |
| Masthead | **M1** wordmark left, dateline right, thick/thin rule under |
| Results panel | **R5** ruled scorecard, mono tabular values (rail-shaped), now carrying the runner-up under each line |
| Lead headline | **H1** kicker over, italic standfirst under |
| Drop cap | **D2** three-line Fraunces initial |
| Lead body | **B2** two columns, hairline rule |
| Card treatment | **C2** ruled columns, no gaps, no boxes *(desktop; mobile decided separately)* |
| Kickers | **K1** plain mono caps in the accent colour |
| Standings rail | **S2** results + final standings beside the lead |
| Appendices | **P1** open block at the foot |


Tournament reports move from one flowing document to a **newspaper edition**: a lead story on the
Trophy winner, then the remaining storylines as separate articles in a grid.

Jon's verdict on the prototype: *"this approach in general is really good — much more digestible
than just one long report."* Direction is settled. Layout is not.

Four directions were built, rendered from one shared content model on TEG 14 and TEG 16, so each
was judged against identical copy:

| | Direction | Lead | Sub-stories |
|---|---|---|---|
| **A** | Broadsheet | Two thirds, drop cap, ruled columns | Right rail + bottom row |
| **B** | Modern editorial | Full width, generous measure | 3-up cards |
| **C** | Sports section | Two thirds + results/standings rail | Asymmetric 2-column |
| **D** | Back page | Huge condensed caps | Four short blocks |

### The files

| File | What it is for |
|---|---|
| `newspaper.html` | The original A–D trial. Kept as the record of how the direction was settled. |
| `elements.html` | The element-by-element chooser: ten elements, 4–5 variants each, one neutral type system so only the element varies. Its job is done, but it is the tool to reopen any single choice. |
| `composite.html` | The chosen elements assembled. Switches arrangement (E1/E2/E3) and rail fill (F1/F2/F3). **This is the live candidate.** |
| `mobile.html` | The three mobile patterns (A index-first, B swipeable cards, C accordion). |

All four are served at `/report-layouts/` and all three tournaments (14, 16, 18) render in each.
Artifact of the original trial:
https://claude.ai/code/artifact/37e0dc5d-5cc3-4475-bf7b-7857de19bf91

## Decided — do not re-litigate

- **Newspaper edition over one long report.** Confirmed by Jon against the live prototype.
- **Lead story is always the Trophy winner.** Sub-articles order by `compelling_score` desc, then
  `humour_score` desc.
- **Interweaving is mothballed** (2026-09-05, `--interweave`, off by default). Its A/B win stands,
  but it was measured on a flowing document; an edition wants one subject per article. Reasoning:
  `teg_analysis/reporting/STORYLINE_PLAN.md` → "Interweaving mothballed".
- **The content model is settled and free.** `scripts/build_newspaper_edition.py` turns a
  `storyline_plan.json` + `report_storylinefirst_styled.md` into an edition object. Deterministic,
  no LLM, no cost. Rerun it and `editions.json` rebuilds; then
  `python -m scripts.inline_editions` pushes the result back into every prototype page (they carry
  the data inline because a published Artifact cannot fetch a sibling file).
- **All three tournaments are in.** TEG 18's artefacts landed on main with the storyline-first
  pipeline and parse cleanly. Its merged section opens paragraphs with a `**Round N, Course.**`
  run-in, which the pages now render as bold rather than printing the asterisks.
- **Runners-up belong in the at-a-glance box.** Derived in the build script from the final
  standings — second place on Trophy and Green Jacket, second from last on Trophy for the Wooden
  Spoon — with codes resolved through `get_player_dict()`.
- **The element vocabulary** in the table above. Reopen a single choice in `elements.html`; do not
  restart the whole pass.

## Open — and what is needed to close it

### 1. Page composition — needs Jon's pick from `composite.html`

The elements are chosen; how they compose is not. Six arrangements, all using the same vocabulary.

**E1–E3 vary where the blocks sit.** Jon's read: they "do a good job of fixing the main issues".

- **E1 classic front** — lead across two thirds with the rail beside it, one heavy rule, then a
  3-up ruled row. A fourth sub-article spans the full width.
- **E2 second lead** — the highest-scoring sub-article is promoted to full width with its own
  three columns; the rest follow in one ruled row. Uses `compelling_score` for more than ordering.
- **E3 two decks** — the rail runs the full height of the lead block, so the page opens as two
  columns rather than a band; then a 2×2 ruled grid.

**G1–G3 attack tessellation and white space**, which is what Jon flagged as the remaining fault
along with the lead and the grid reading as two pages:

- **G1 packed** — the whole page is one three-column flow. Stories break across columns the way a
  newspaper's do, so the browser balances them; no divider rule anywhere.
- **G2 balanced** — three columns, but no story is ever split. Each is placed into the shortest
  column by measured height (longest-processing-time packing, `balanceG2`).
- **G3 interlocked** — the lead occupies an L, the rail runs the right edge full height and the
  remaining stories fill under the lead in the other two columns.

**Measured, not judged by eye.** Spread between the tallest and shortest column bottom, in px —
lower tessellates better:

| | TEG 14 | TEG 16 | TEG 18 |
|---|---:|---:|---:|
| E1 | 66 | 608 | 629 |
| E2 | 100 | 1348 | 1331 |
| E3 | 1199 | 55 | 55 |
| **G1** | **202** | **124** | **8** |
| G2 | 638 | 501 | 563 |
| G3 | 733 | 694 | 814 |

**G1 is the only arrangement that tessellates consistently.** E1 and E3 each look tidy on some
tournaments and ragged on others, which is copy-dependence, not layout. And G2 is the useful
negative result: with only three to five stories of 220–410 words, keeping every story whole and
balancing three columns is close to arithmetically impossible — better packing does not help,
because there are too few pieces. **Splitting stories across columns is what makes a newspaper
page tessellate**, and G1 is the only option here that does it.

Crossed with a second, smaller decision the rail forces. The rail is shorter than the lead body,
so its column ends in a void unless something follows the standings:

- **F1** nothing — accept the gap.
- **F2** the round-by-round Trophy table.
- **F3** the shortest sub-article moved up into the rail, picked by `words`.

Two arrangements were rebuilt during this pass and the reasons are worth keeping: E2 originally
stacked the remaining stories in a narrow column beside the promoted one, and three full-length
articles in that column left a column-height void; G3 originally spanned the rail across two grid
rows, which stretched the first row to the rail's height and left a gap under the headline.

### 2. Mobile — three patterns built, one to choose

All three are in `mobile.html`, on the same element vocabulary. The measured first-screen length
is the number that matters, because the defect being fixed is scroll length:

| | Pattern | First screen | Notes |
|---|---|---|---|
| — | *Desktop composite at 390px* | *9,085px — 10.8 phone screens* | *the problem, quantified* |
| **A** | Index first | 938px — 1.1 screens | Article is its own screen, prev/next at the foot. Costs a tap. |
| **B** | Swipeable cards | 1,227px — 1.5 screens | Kicker tabs across the top carry the affordance; next panel peeks. |
| **C** | Accordion | 1,774px closed — 2.1 screens | Two sections open: 3,657px, 4.3 screens. The long-report risk, visible. |

Note the card treatment answer (C2, ruled columns) was given for desktop only — mobile card
separation follows from whichever pattern wins here, not from that answer.

### 3. `StorylinePlan` needs `headline` and `standfirst`

The pipeline gives each storyline a `subject`: a 15–25 word descriptive line. Good section heading,
poor headline. The parser derives one, and derived headlines are the weakest text on the page —
`_derive_headline` / `_choose_standfirst` in the build script exist only to stop that reading as a
bug. The unrequested `**bold**` mini-header, logged in `reporting/STATUS.md` as cosmetic, is this
missing field arriving by accident about half the time. **Fix it by asking for it.**

That is a change to `story_plan.py` on the storyline branch, not to the prototype.

### 4. Wiring it into the site

Once a layout is chosen: `webapp/routes/reports.py` currently renders the styled markdown to one
HTML blob. The edition parser replaces that. Sync `def` handler (CLAUDE.md invariant), and reports
are read through `teg_analysis.io.read_text_file` (volume-then-GitHub aware) — not the filesystem.

## Dependencies — check these before starting

- **The storyline-first pipeline has merged to main** (PR #93), so the artefacts are no longer a
  dependency to manage. TEG 14, 16 and 18 all have storyline artefacts and all three are in the
  prototypes.

## What not to redo

- Do not re-run the element-by-element pass. Ten choices were made against rendered specimens; the
  table at the top is the answer. Reopen one element in `elements.html` if it turns out wrong.
- Do not rebuild the parser or re-derive the content model; rerun the script.
- Do not re-run the interweaving A/B — it was won and then superseded, which is not the same as
  wrong.
- Do not merge `claude/storyline-first-reports` into the prototype branch to get the artefacts. The
  four files are already here.
