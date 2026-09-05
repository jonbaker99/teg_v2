# Newspaper layout — picking this up in a new chat

**Read this first.** The trial specification is [PLAN.md](PLAN.md); this file is where it got to and
what to do next. Working doc — delete or fold into `STATUS.md` when a final layout ships
(CLAUDE.md → Documentation rule 3).

**Status: direction confirmed, layout not chosen.** Written 2026-09-05.

---

## Where this got to

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

Prototype: `newspaper.html` (also at `/report-layouts/`). Artifact:
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
  no LLM, no cost. Rerun it and `editions.json` rebuilds; re-inline that into `newspaper.html`.

## Open — and what is needed to close it

### 1. The final layout — needs Jon's specifics

Jon: *"there are elements from each prototype that I like and dislike."* Nobody can guess which.
**Ask for it element by element, not direction by direction** — masthead, results panel, lead
headline treatment, drop cap, column rules, card borders, kickers, the standings rail, appendix
placement. The answer is a fifth composite layout, not one of A–D as built.

### 2. Mobile — the real design problem, not a reflow bug

Jon: *"the mobile layout needs work — as it all goes vertical it still feels a bit too much like
one long report."*

**This is the trial's finding repeating itself one level down.** Stacking a grid vertically
recreates exactly the problem the newspaper layout solved. Making the stack tidier will not fix it,
because the defect is structural: on a phone the reader gets one continuous scroll again.

So mobile needs a genuinely different pattern. Options worth prototyping (Jon has not chosen):

- **Index first** — the masthead, results and a headline list; tap a headline to read that article.
  Most faithful to "separate articles"; costs a tap to reach any prose.
- **Swipeable cards** — one article per horizontal panel. Keeps everything one gesture away;
  discoverability of the remaining articles depends on the affordance.
- **Accordion** — all headlines visible, bodies collapsed, expand in place. Cheapest, but a
  half-expanded page can read as a long report again.

Do not just tune the existing breakpoints. Prototype two or three of these the way A–D were done.

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

- **The storyline-first pipeline is on `claude/storyline-first-reports`, not main.** Everything here
  depends on its output. If it has not merged, the layout has no pipeline behind it.
- The prototype's four data artefacts were copied from that branch verbatim, so they merge cleanly.
- Only TEG 14 and 16 have storyline artefacts (18 too, unused here — its merged section uses
  `**Round N, Course.**` paragraph prefixes and was left out of the trial).

## What not to redo

- Do not rebuild the parser or re-derive the content model; rerun the script.
- Do not re-run the interweaving A/B — it was won and then superseded, which is not the same as
  wrong.
- Do not merge `claude/storyline-first-reports` into the prototype branch to get the artefacts. The
  four files are already here.
