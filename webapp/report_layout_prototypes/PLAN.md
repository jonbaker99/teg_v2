# Newspaper report layout — prototype plan

**Status:** working doc for the prototype only. Delete or fold into `STATUS.md` once a direction is
chosen (CLAUDE.md → Documentation rule 3). Written 2026-09-04.

> **The trial ran and the direction was confirmed. For where it got to and what to do next, read
> [PICKUP.md](PICKUP.md) first** — this file is the original specification, kept for the reasoning
> behind each choice.

## What is being tested

Whether a newspaper front-page layout — lead story = the Trophy winner, sub-stories in a grid — is a
better presentation for TEG tournament reports than the current single flowing column.

This is a **presentation trial only**. No pipeline change, no LLM call, no cost.

## What it is built from

The storyline-first work on `origin/claude/storyline-first-reports` already produces exactly the
content shape a newspaper needs. Do not merge that branch — copy only the artefacts.

Per TEG, two files:

| File | Gives us |
|---|---|
| `data/commentary/teg_N_storyline_plan.json` | `trophy_storyline`, `jacket_storyline`, `spoon_storyline`, `discovered_storylines[]` — each with `subject`, `compelling_score`, `humour_score` |
| `data/commentary/teg_N_report_storylinefirst_styled.md` | `# title {.report-title}`, `<p class="dateline">`, the at-a-glance results block, one `## <subject>` section per storyline, then the `## Standings by round` and `## Personal bests and TEG records` appendices |

**Tournaments: TEG 14 and TEG 16.** 14 is the clean case — five discrete articles, a two-point
finish. 16 is four articles including one cross-cut (two storylines merged into one section by the
interweave step, heading joined with ` / `). TEG 18 is available as a third if two prove too few;
its merged section uses `**Round N, Course.**` paragraph prefixes, which is a harder case and out of
scope for step 1.

## Phase 1 — get the artefacts onto this branch

```bash
git checkout origin/claude/storyline-first-reports -- \
  data/commentary/teg_14_storyline_plan.json \
  data/commentary/teg_14_report_storylinefirst_styled.md \
  data/commentary/teg_16_storyline_plan.json \
  data/commentary/teg_16_report_storylinefirst_styled.md
```

Identical blobs from the same commit, so they merge conflict-free later. Nothing else from that
branch — its pipeline changes are a separate review.

## Phase 2 — `scripts/build_newspaper_edition.py`

Deterministic parser. No LLM. Reads the two files per TEG, emits one `edition` dict per TEG:

```python
{
  "teg": 14,
  "title": "Nine Ahead, Two Home: Mullin's Kent Double",
  "dateline": {"teg": "TEG 14", "venue": "Kent, England", "year": "2021"},
  "results": [{"label": "Trophy Winner", "value": "David Mullin (3rd Trophy)", "lead": True},
              {"label": "Green Jacket",  "value": "David Mullin (9th Jacket)"},
              {"label": "Wooden Spoon",  "value": "Jon Baker (1st Spoon)"}],
  "articles": [{"kicker": "TROPHY", "headline": "...", "standfirst": "...",
                "paragraphs": [...], "words": 431, "compelling": 8, "humour": 5,
                "is_lead": True}],
  "standings": [{"round": 1, "trophy": "DM 40 | AB 37 | GW 33 | JB 29",
                 "jacket": "DM +15 | JB +20 | GW +21 | AB +26"}],
  "records": ["Gregg Williams's +76 is a personal Gross best"]
}
```

Rules:

1. **Split the body on `^## `.** Stop at `## Standings by round`; everything from there is appendix.
2. **Join each section to the plan.** Split the heading on ` / `, match each part against the plan's
   `subject` strings exactly. A merged section carries both storylines: kicker becomes
   `"JACKET & SPOON"`, scores become the max of the two.
3. **Kicker** from which plan slot matched: `TROPHY` / `GREEN JACKET` / `WOODEN SPOON` /
   `SIDEBAR` for a `discovered_storylines` entry.
4. **Headline and standfirst.** A newspaper needs a short headline plus a longer deck, and the
   pipeline reliably produces neither — this is the trial's main finding, see *Feedback to the
   pipeline* below. For the prototype:
   - The `**bold**` line the draft writer inserts after ~half the `##` headings (logged as a
     cosmetic bug in `reporting/STATUS.md`) is a usable short headline — `"Mullin holds on for the
     Trophy"`, `"Neumann's first Trophy"`. Use it when present, and drop it from the body.
   - Otherwise derive one by truncating the `##` heading at the first `—`, `:` or `,`.
   - The full `##` heading always becomes the `standfirst`.
5. **Lead article** is the one whose kicker is `TROPHY`. Always. Sub-articles are ordered by
   `compelling_score` desc, then `humour_score` desc — an editorial ordering the current report
   does not apply.
6. **`words`** per article, so a layout can size a block to its copy rather than assuming.

Output: writes `editions.json` next to the prototype, and is importable so Phase 3 can inline it.

## Phase 3 — the prototype page

One self-contained HTML file: `webapp/report_layout_prototypes/newspaper.html`.

Content for both TEGs inlined as a JS object (a published Artifact cannot fetch a sibling file —
CSP blocks it). Two switchers at the top, outside the page frame:

- **Tournament**: TEG 14 / TEG 16
- **Layout**: A / B / C / D

Eight renderings from one content model, so a layout is judged against the same copy. Rendering is
plain JS building DOM from the edition object; layout is a class on the frame plus a per-layout CSS
block. No libraries, no build step.

### The four directions

| | Direction | Lead treatment | Sub-stories | Type | The risk it tests |
|---|---|---|---|---|---|
| **A** | **Broadsheet** | Spans two thirds. Big condensed serif headline, drop cap, body set in 2 CSS columns with hairline rules | Right-hand rail (1) + bottom row (3), separated by rules | Condensed serif headlines, serif body, mono kickers | Most authentically newspaper. Does 300-word copy survive being set in narrow columns? |
| **B** | **Modern editorial** | Full-width headline + standfirst, single generous measure, no columns | 3-up card grid, kicker labels, no rules | Sans headlines, serif body, whitespace | The Athletic / Guardian look. Likeliest to actually ship. Does it still read as an *edition* rather than a list of blog posts? |
| **C** | **Sports section** | Two thirds, with the results + standings-by-round rail pinned alongside | Asymmetric 2-column grid below, one wide + one narrow, pull quotes | Serif headlines, tabular mono for all numbers | Puts the data next to the prose — the thing a golf site has that a newspaper does not. Does the rail compete with the lead? |
| **D** | **Back page** | Huge uppercase condensed headline, short lead, strong rule under the masthead | 4 short high-contrast blocks, heavy kickers | Very condensed uppercase headlines, tight leading | Matches the reports' comic register (Spoon storylines score 8–9 on humour). Does it read as funny, or as kitsch? |

### Shared across all four

- **Masthead** — the title as the paper's name is wrong; the paper's name is constant and the title
  is the lead headline. Masthead is a fixed wordmark (`THE TEG` or similar) plus the dateline
  (`TEG 14 · KENT, ENGLAND · 2021`), then the lead headline below it.
- **Results panel** — the at-a-glance block, styled per layout, Trophy winner emphasised.
- **Appendices** — standings by round and records, below the grid in every layout. They are
  reference, not story; do not let them into the article grid.
- **Mobile reflow (required).** Every layout stacks to one column under 640px, in the order
  lead → sub-stories by score → appendices. Column-split body text must collapse to single column.
  Test each layout at 375px as well as desktop; a grid that only works at 1280px has failed.
- No dark mode — explicitly out of scope for this trial.

## Phase 4 — publish and record

1. Publish `newspaper.html` as an Artifact, favicon 📰, title `TEG Newspaper Layouts`.
2. Mount the folder in `webapp/app.py` at `/report-layouts/` beside the existing `/mockups/` mount,
   so it is also browsable against a local server.
3. Docs, same session:
   - `webapp/README.md` — one line under the mockups note, pointing at the folder and the mount.
   - `STATUS.md` — the trial exists, what it is built from, awaiting a direction.
   - `teg_analysis/reporting/STATUS.md` — one line: a newspaper presentation trial is running on the
     storyline-first output, plus the headline/standfirst gap below.
   - `webapp/TODOS.md` — choose a direction; then wire it into `routes/reports.py`.

## Feedback to the pipeline (the trial's real output)

Record these in `teg_analysis/reporting/STATUS.md`, because they are what a layout trial can tell the
pipeline that reading prose cannot:

1. **`StorylinePlan` needs a `headline` (3–8 words) and a `standfirst` (one sentence) per
   storyline.** `subject` is neither — it is a 15–25 word descriptive line that works as a section
   heading and fails as a headline. Every layout has to derive one, and derived headlines are the
   weakest text on the page.
2. **The unrequested `**bold**` mini-header is not a cosmetic bug — it is the missing headline
   field, arriving by accident and only half the time.** Fix it by asking for it, not by removing it.
3. **A cross-cut section needs a kicker the merge step can name.** ` / `-joined headings are a
   parsing artefact; the merge should emit a single subject.
4. Whether article count (4 vs 5) and length spread (300–450 words) suit a grid — answerable only
   once a direction is picked.

## Out of scope

- Round reports.
- Any change to `story_plan.py`, `authoring.py` or `render.py`.
- Wiring a chosen layout into `routes/reports.py` — that is the follow-up, after a direction is chosen.
- Voice, tone, humour dials.
