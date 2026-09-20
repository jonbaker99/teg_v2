# Consolidated UI / UX review — TEG webapp

**Reviewed:** 2026-09-19 · **Inputs:** `claude-ui-review.md`, the first GPT review, current source, project TODOs, and live mobile sampling of `/leaderboard`, `/contents`, and `/scorecard` · **Status:** recommendations and prototype only; no application code changed.

**Product test:** can one of eight friends understand the competition in three seconds, outdoors, on a phone?

## 1. Recommendation in one page

**Fix functionality and consistency before adopting a new visual identity.** The app already avoids most generic AI-dashboard habits and has genuinely good golf-native components. The immediate problem is uneven execution, not a lack of decoration.

The recommended path is **Fix → Consistent UI → Improve → Experiment → Test and decide**:

1. **Fix:** repair public-site interaction defects: invisible desktop rank toggle, narrow-screen Records overflow, incomplete Latest Round phone layouts, dark-title contrast, and disappearing long-page navigation.
2. **Consistent UI:** introduce one type scale, three real heading levels, fewer control patterns, tighter leaderboard rhythm, semantic green, and fewer nested rounded panels.
3. **Improve:** unify the standings renderer, simplify controls, and make Contents a current-TEG home rather than a sitemap.
4. **Experiment:** pilot Editorial Golf on the leaderboard and reports, borrowing compact telemetry mechanics without making the whole site cream, dark-first, or broadcast-like.
5. **Test and decide:** validate the pilot with the eight users before extending it to history, records, and scoring analysis.

This path covers the public analysis and navigation experience only. Admin, round setup, score entry, live-round operations, and data-update processes are explicitly deferred; relevant recommendations are recorded in §4 for their later workstream.

The target is a **clean editorial scorecard**, not a dashboard: white or lightly warm surfaces, dark ink, forest-green state, hairline rules, restrained Lora identity, and dense Inter data.

## 2. Critical review of `claude-ui-review.md`

Claude’s review is strongest as a source inventory and visual-direction paper. It is weaker where it infers the rendered result from generic CSS or turns an attractive concept into a site-wide decision.

| Claude claim or proposal | Verdict | Consolidated position |
|---|---|---|
| `.section-title`, `.card-header`, and `.chart-title` collapse into one visual level | **Keep** | Source confirms the three classes intentionally share the same 13px uppercase Lora treatment. The result is consistent but too flat for three semantic levels. |
| The leaderboard table is narrow with about 400px of dead space | **Reject as false for this screen** | `.leaderboard-table { width: 100%; }` specifically overrides the content-sized `.teg-table` default. The real problem is excess chrome and weak composition, not table width. |
| Phone cards currently replace the leaderboard table | **Reject as stale** | The later R3.2 rule deliberately reveals the compact table and hides `.lb-cards` on standings pages. Both renderers still ship, which creates maintenance drift. |
| Breakpoints are fragmented and tablet portrait is under-designed | **Keep, soften the prescription** | The diagnosis is right. Replacing everything mechanically with 640/900/1280 is not; scorecards, reports, Contents, and player pages have different needs. Define phone/tablet/wide contracts, then migrate route by route. |
| Chrome outnumbers data on the leaderboard | **Keep** | Live sampling confirms large vertical gaps and several competing control grammars before the chart. Remove redundancy before redesigning visuals. |
| Gap-to-leader is missing | **Decline for this path** | The owner does not need it. Keep the standings focused on rank, rounds, and Total rather than adding a derived comparison column. |
| The type system has drifted | **Keep with corrected counts** | Static CSS has about 94 distinct `font-size` values across 275 declarations. The count is an inventory signal, not a goal; use a small token scale and migrate incrementally. |
| Token discipline is “genuinely strong” | **Partly keep** | Core theme tokens and global tabular figures are strong. Hardcoded live-round colours, tooltip styling, Contents overrides, and old experiment classes show uneven adoption. |
| Editorial Golf should become the whole site | **Keep as a pilot, reject as an immediate global decision** | Printed-scorecard rules, serif identity, sand leader treatment, and report language are excellent. A site-wide cream-paper conversion risks reducing contrast and over-styling analytical pages. |
| Dark-first Modern Telemetry is a strong alternative | **Keep as an experiment only** | Its movement, status, and compact-round-strip ideas are useful. Dark-first is a poor default for bright outdoor use and could make historical pages feel permanently live. |
| Replace the race chart with row sparklines | **Defer** | Attractive, but the existing chart has comparison, focus, and responsive behaviour. Prototype sparklines before removing a working analytical view. |
| Remove global Plotly, Tailwind Play CDN, dead variants, and lab residue | **Keep as a secondary track** | Valid performance and maintenance work, but it should not outrank score-scanning defects. |

### Best elements retained from Claude

- Quantified evidence for collapsed heading hierarchy, type drift, breakpoint spread, and live-round colour bypasses.
- Printed-scorecard mechanics: double rules, hairlines, serif identity, tabular data, and sand rather than green row tint.
- The insight that the newspaper report is the most distinctive existing visual asset.
- The warning that one accent colour currently carries hierarchy, selection, status, focus, and hover.
- The hygiene inventory: global Plotly and Tailwind, debug tooling, dead variants, lab templates, inline tooltip colours, and `contents.html` shell overrides.

### Best elements retained from the GPT review

- Live evidence from the deployed phone layout and the scorecard as the quality benchmark.
- Current defects already confirmed in `webapp/TODOS.md`: rank-toggle visibility, dark-title contrast, Records overflow, and unfinished Latest Round mobile tabs.
- The correction that the compact phone table is intentional and the older cards are stale code, not the active experience.
- A prototype that preserves player links, empty states, and the current `lb_cards` contract without requiring new analytical data.
- A phased recommendation that separates functional fixes, system consistency, and aesthetic experiments.

## 3. What already works

- **Golf-native scorecards.** Score shapes, totals, initials, and front/back-nine rhythm are fast to read.
- **Real restraint.** There is no glass blur, purple gradient, giant empty metric card, or fake enterprise chrome.
- **Global tabular figures.** Scores align cleanly without forcing the whole interface into monospace.
- **Useful domain language.** Champion, wooden spoon, rounds, Gross, Net, and Stableford need no explanation for this group.
- **A viable theme foundation.** Tokens exist and make refinement possible without a rewrite, even though adoption is incomplete.
- **Bespoke details.** Portrait scorecards, shortened player names, report typography, and contribution bars feel made for this tournament.

## 4. Site functionality recommendations

### Do now — repair trust and scanning

| Priority | Proposal | Impact | Effort | Acceptance test |
|---:|---|---|---|---|
| 1 | Give `.rank-toggle` a visible `+`/`−` glyph and adequate hit area above 640px | High | Low | The detail row is discoverable on desktop without hovering or guessing. |
| 2 | Fix narrow-screen Records overflow | High | Med | Long locations never widen the page; value and owner remain scannable at 320–430px. |
| 3 | Finish Latest Round mobile layouts for Scoring, Streaks, Records, and Scorecard | High | Med | Each tab has one intentional phone treatment; no desktop grid is squeezed into the viewport. |
| 4 | Restore dark-mode page-title contrast | Med | Low | Every page title is clearly visible in both modes. |
| 5 | Keep navigation available on long pages, or restore it on any upward scroll | Med | Low | Users can move sections without returning to the page top. |

### Do next — make tournament state the product

**Turn Contents into a current-TEG home.** Lead with the latest event, current or final leader, latest round, report link, and two or three recent destinations. Keep the full sitemap below or behind “All analysis”. Eight repeat users need state before discovery.

**Use one structured standings component.** Retire the HTML-string table plus stale card dual path. One semantic table should reflow: full rounds on desktop, compact round strip on phone and tablet.

**Reduce control grammar.** Keep three patterns: tabs for views, segmented controls for mutually exclusive measures, and compact buttons for actions. Chart player readouts can remain specialised because they manipulate a series, not page state.

**Standardise interaction state.** Apply selected state only after successful responses, use one loading/error/retry pattern, and preserve public filters and tabs in canonical URLs so reload, sharing, and Back are predictable.

**Preserve the race chart until a better comparison is proven.** Move chart mode above the chart, remove “Choose chart type”, and test any sparkline replacement alongside—not instead of—the current view.

### Do later — speed and maintenance

- Load Plotly only on chart routes.
- Replace the Tailwind Play CDN with a pinned build.
- Remove the unused scorecard Roboto Mono import.
- Move design-lab templates and debug tooling behind development-only paths.
- Delete stale leaderboard-card CSS and markup when the unified component lands.
- Add rank movement only after agreeing its baseline: previous round, previous day, or previous published state.

### Deferred operational recommendations — document now, implement later

These are intentionally outside the current path because they affect admin, setup, score input, live-round operations, or data-update processes:

- **Live score entry:** show pending, saved, failed, and retry states for writes and polling; retries must not duplicate a successful write.
- **Admin and data update:** use one progress, success, warning, failure, and retry language across long-running actions; retain exact previews before destructive or high-impact changes.
- **Round and TEG setup:** keep the current task-focused forms compact; apply the eventual type/control tokens when this workstream is opened, without redesigning their flows now.
- **Field-use theming:** tokenise live-entry and live-leaderboard colours before expanding dark mode to those surfaces.
- **Pipeline truthfulness:** preserve the existing fail-loudly behaviour; UI polish must never turn partial or stale results into a success state.

## 5. Optimise the existing aesthetic

The current aesthetic should evolve into **Clean Editorial Precision**. Keep its restraint; remove its accidental softness and inconsistency.

### Preserve

- White, high-contrast surfaces as the default for outdoor use.
- Forest green as the recognisable product accent.
- Lora for identity: masthead, page titles, and selected editorial moments.
- Inter with tabular figures for data, controls, and tables.
- Existing golf semantics: score shapes, player initials, front/back-nine structure, champion, and wooden spoon.
- The scorecard’s compact visual logic as the reference screen.

### Change

**Create three real heading levels.** Page title: large Lora in ink. Section title: Lora or Inter semibold at 15–16px, ink, optional hairline. Component/chart label: Inter 11–12px, muted uppercase. Static headings should not all be green.

**Adopt a small type scale.** Start with 11, 12, 14, 16, 20, and 28px tokens. Migrate touched components first; do not attempt a risky global replacement.

**Make green semantic.** Use it for active selection, live status, leader emphasis, and positive golf states. Use ink and weight for hierarchy; use a separate focus token for keyboard focus.

**Flatten the shell.** Reduce nested white cards, shadows, and 12–13px radii. Prefer open sections, 1px rules, and 2–4px radii. Cards remain valid when they group a real entity, such as a player highlight or report edition.

**Tighten leaderboard rhythm.** Put Leaderboard/Scorecards and Net/Gross in one compact control zone. Remove redundant labels. Keep champion and wooden spoon as one facts rail. Let the table begin sooner.

**Define responsive contracts, not one magic breakpoint.** Phone: compressed data and bottom navigation. Tablet portrait: simplified columns and a clear navigation affordance. Desktop: full rounds and analysis. Route-specific exceptions remain explicit.

### Proposed visual specification

| Element | Current issue | Proposed treatment |
|---|---|---|
| Page surface | Grey canvas plus floating white panel can feel generic | White primary surface; optional very light warm canvas only on wide screens |
| Section headings | Three classes look identical and green | Ink hierarchy with one optional green state marker |
| Leader row | Green tint competes with hover | Sand tint or 2–3px green inset rule; weight carries priority |
| Tables | Mixed density and mobile strategies | 36–40px desktop rows, 40–44px touch rows, tabular numbers, strong Total |
| Controls | Tabs, pills, switches, and readouts overlap semantically | Three documented patterns with shared height, type, radius, and selected state |
| Cards | Nested shadows and rounded pods soften data | Hairline groups by default; cards only for distinct entities |
| Reports | Visually separate product | Share typography, ink, green, and rule language; keep richer paper treatment inside reports |

## 6. Potential aesthetic directions

### Direction A — Clean Precision

This is the lowest-risk continuation of the current app.

- Pure white, dark ink, forest-green state, and minimal warm neutral.
- Inter-first interface; Lora restricted to masthead and page titles.
- Dense tables, open sections, square-ish controls, and almost no shadow.
- Best when the priority is speed, consistency, and easy rollout.

**Recommendation:** implement this as the baseline system cleanup regardless of later direction.

### Direction B — Editorial Golf

This is the recommended visual evolution, applied selectively first.

- Warm paper inside competition and report surfaces, not necessarily every page.
- Lora for event identity and player surnames; Inter tabular for R1–R4 and Total.
- Printed-scorecard double rules, hairlines, sand leader treatment, and one compact champion/spoon rail.
- Tabs read like publication sections; analysis remains crisp rather than decorative.

**Recommendation:** prototype on `/leaderboard` and `/teg-reports`. If it improves sunlight scanning and feels natural to the group, extend it to Results and Latest TEG.

### Direction C — Modern Telemetry

This is the bold option and should be a mode or experiment, not the default identity.

- Stark ink/white contrast, compact data type, square status badges, and compressed rows.
- Movement, live/final state, and compact round strips become prominent.
- Sparklines or micro-bars may supplement the race chart after comparison testing.
- Avoid acid accents, permanent dark-first surfaces, and broadcast effects on historical pages.

**Recommendation:** borrow its mechanics inside Direction B. Do not adopt a global dark-first theme without outdoor field testing.

## 7. Delivery proposal

The dependency order, bounded chat breakdown, copy-ready starter prompts, checks, and review gates are maintained in [ui-implementation-roadmap.md](ui-implementation-roadmap.md).

### Fix

Fix rank toggle, Records overflow, Latest Round phone gaps, dark titles, and navigation persistence. Do not touch admin, setup, score input, live-round operations, or data-update flows in this workstream.

### Consistent UI

Add type, spacing, radius, focus, and state tokens. Define three heading levels and three control patterns. Remove redundant leaderboard chrome.

### Improve

Unify the standings renderer, simplify its controls, and rebuild Contents around current tournament state. This is the highest-value product change.

### Experiment

Apply the prototype below to leaderboard and report surfaces. Test phone, tablet portrait, desktop, dark mode, five-player historical data, and the full eight-player field.

### Test and decide

Choose one outcome: keep Clean Precision, extend Editorial Golf, or import only telemetry mechanics. Do not run three permanent themes in parallel.

## 8. Working method

Use one implementation owner and independent review gates.

**Codex/Sol leads the worktree.** It owns the plan, code integration, browser verification, tests, documentation, and final diff. This avoids two agents making overlapping edits or re-litigating decisions inside the same branch.

**Use Claude selectively:**

1. Before Consistent UI implementation, ask Claude to challenge the proposed tokens, hierarchy, and control rules against screenshots and the agreed scope.
2. After each implemented stage, give Claude the diff and desktop/phone/tablet captures for a fresh visual review.
3. During Experiment, ask Claude to critique the rendered Editorial Golf variants and propose adjustments. Codex remains the only agent editing and integrating the task branch.

**Use cheaper Codex agents for bounded work:** selector inventory, screenshot matrices, mechanical token migration, and focused test execution. They should receive non-overlapping files and acceptance criteria.

**Do not partner on every edit.** Claude adds most value as an independent taste and review pass. Codex should remain the single implementation lead, and the owner should make the aesthetic choice at the Experiment/Test gate.

Start with one small Fix slice. Ship and verify those public-site defects before opening Consistent UI. Do not mix aesthetic experiments into the first implementation branch.

## 9. Code prototype — Editorial Golf standings pilot

The prototype uses the existing `lb_hero` and `lb_cards` structures from `webapp/routes/history.py`. It needs no new analytical field or backend calculation.

### Jinja partial

```html
{% if lb_cards %}
<section class="editorial-standings" aria-labelledby="standings-title">
  <header class="editorial-standings__head">
    <div>
      <p class="editorial-kicker">TEG {{ selected_teg }} · {{ context_header }}</p>
      <h2 id="standings-title">{{ section_title }}</h2>
    </div>
    <dl class="editorial-facts">
      <div>
        <dt>{{ lb_hero.label }}</dt>
        <dd>{{ lb_hero.champion }} <strong>{{ lb_hero.champion_total }}</strong></dd>
      </div>
      {% if lb_hero.spoon %}
      <div>
        <dt>Wooden spoon</dt>
        <dd>{{ lb_hero.spoon }} <strong>{{ lb_hero.spoon_total }}</strong></dd>
      </div>
      {% endif %}
    </dl>
  </header>

  <table class="editorial-table">
    <thead>
      <tr>
        <th scope="col" class="col-rank">Rank</th>
        <th scope="col" class="col-player">Player</th>
        {% for label, value in lb_cards[0].rounds %}
        <th scope="col" class="col-round">{{ label }}</th>
        {% endfor %}
        <th scope="col" class="col-total">Total</th>
      </tr>
    </thead>
    <tbody>
      {% for player in lb_cards %}
      <tr class="{% if player.lead %}is-leader{% endif %}">
        <td class="col-rank"><span>{{ player.rank }}</span></td>
        <th scope="row" class="col-player">
          {% if link_player_cards and player.code %}
          <a class="player-name" href="/player/{{ player.code }}">{{ player.player }}</a>
          {% else %}
          <span class="player-name">{{ player.player }}</span>
          {% endif %}
          <span class="round-strip">
            {% for label, value in player.rounds %}{{ label }} <b>{{ value }}</b>{% if not loop.last %} · {% endif %}{% endfor %}
          </span>
        </th>
        {% for label, value in player.rounds %}
        <td class="col-round">{{ value }}</td>
        {% endfor %}
        <td class="col-total">{{ player.total }}</td>
      </tr>
      {% endfor %}
    </tbody>
  </table>
</section>
{% else %}
<p class="text-muted">No leaderboard data found.</p>
{% endif %}
```

### CSS

```css
:root {
  --golf-paper: #f7f2e7;
  --golf-paper-deep: #eee4d1;
  --golf-ink: #191812;
  --golf-muted: #6d695e;
  --golf-rule: #b8ae98;
  --golf-green: #17683c;
}

.editorial-standings {
  background: var(--golf-paper);
  color: var(--golf-ink);
  border-block: 1px solid var(--golf-rule);
  padding: 18px 20px 14px;
}

.editorial-standings__head {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 24px;
  align-items: end;
  padding-bottom: 14px;
  border-bottom: 3px double var(--golf-ink);
}

.editorial-kicker,
.editorial-facts dt,
.editorial-table thead th {
  font: 700 10px/1.2 var(--font-sans);
  letter-spacing: 0.09em;
  text-transform: uppercase;
  color: var(--golf-muted);
}

.editorial-kicker {
  margin: 0 0 4px;
  color: var(--golf-green);
}

.editorial-standings h2 {
  margin: 0;
  font: 600 24px/1.05 var(--font-serif);
}

.editorial-facts {
  display: flex;
  gap: 22px;
  margin: 0;
}

.editorial-facts div + div {
  padding-left: 22px;
  border-left: 1px solid var(--golf-rule);
}

.editorial-facts dd {
  margin: 4px 0 0;
  font: 600 13px/1.2 var(--font-serif);
}

.editorial-facts strong {
  margin-left: 6px;
  font: 700 16px/1 var(--font-table);
}

.editorial-table {
  width: 100%;
  border-collapse: collapse;
  table-layout: fixed;
  font-variant-numeric: tabular-nums lining-nums;
}

.editorial-table th,
.editorial-table td {
  padding: 9px 8px;
  border: 0;
}

.editorial-table thead th {
  text-align: right;
  border-bottom: 3px double var(--golf-ink);
}

.editorial-table tbody tr + tr {
  border-top: 1px solid color-mix(in srgb, var(--golf-rule) 55%, transparent);
}

.editorial-table tbody tr.is-leader {
  background: var(--golf-paper-deep);
  box-shadow: inset 3px 0 0 var(--golf-green);
}

.col-rank {
  width: 52px;
  text-align: center !important;
}

.col-player {
  width: 34%;
  text-align: left !important;
}

.player-name {
  display: inline-block;
  font: 600 15px/1.15 var(--font-serif);
  color: inherit;
  text-decoration: none;
}

.col-round {
  text-align: right;
  font: 500 13px/1 var(--font-table);
}

.col-total {
  width: 64px;
  text-align: right;
  font: 700 16px/1 var(--font-table);
}

.round-strip {
  display: none;
}

@media (max-width: 900px) {
  .editorial-standings {
    padding: 14px 12px 10px;
  }

  .editorial-standings__head {
    display: block;
  }

  .editorial-facts {
    margin-top: 12px;
    justify-content: space-between;
  }

  .editorial-table .col-round {
    display: none;
  }

  .col-player {
    width: auto;
  }

  .round-strip {
    display: block;
    margin-top: 3px;
    font: 500 10px/1.3 var(--font-table);
    color: var(--golf-muted);
  }

  .round-strip b {
    color: var(--golf-ink);
  }
}
```

### Why this prototype

- It uses current route data without adding a derived metric.
- It hides round columns on smaller screens but preserves their compact inline strip.
- It preserves conditional player links and handles empty leaderboards.
- It replaces duplicate renderers with one component.
- It combines the strongest parts of both reviews: editorial golf identity and compact, responsive standings mechanics.

## Evidence and limits

- Live sample: deployed `/leaderboard`, `/contents`, and `/scorecard` at mobile width on 2026-09-19.
- Source audit: current routes, templates, styles, `webapp/TODOS.md`, and `webapp/README.md`.
- Claude review claims were rechecked against the current branch; stale statements are called out above.
- Desktop and tablet were assessed from current markup and CSS, not a complete live viewport matrix. The Experiment and Test stages must include that matrix before implementation is accepted.

---

*Synthesis led by GPT-5.6 Sol. GPT-5.6 Luna performed read-only comparison and source inventory. A fresh Sol reviewer checked the combined recommendations and prototype.*
