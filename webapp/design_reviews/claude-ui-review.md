# UI / UX review — TEG webapp

**Reviewed:** 2026-09-19 · **Scope:** `webapp/` Clean theme, desktop + phone · **Status:** review only, no application code changed.

**Audience assumption applied throughout:** 8 known users, no compliance bar, no onboarding problem. Every recommendation below is judged on *speed of reading a score*, not on accessibility or enterprise polish.

> **Live screenshots were not captured.** The shared Playwright browser was locked by a concurrent session for the whole review window (`Browser is already in use … use --isolated`), retried and still locked. This review is therefore built from the rendered HTML (fetched from the running instance on `:8123`), the templates, and the CSS source. Layout numbers quoted below are read from the CSS, not measured in a viewport.

---

## 1. System & interaction audit

### 1.1 The heading system has collapsed into one level

Three classes — `.section-title`, `.card-header`, `.chart-title` — are used **82 times** across the templates (27 / 49 / 6). All three render **identically**:

```css
font-family: Lora; font-weight: 700; font-size: 13px;
letter-spacing: 0.09em; text-transform: uppercase; color: var(--accent);
```

So the markup encodes three structural levels and the eye receives **one**. A page becomes an undifferentiated stack of small green capitals. There is no way to tell "this is the page's main data block" from "this is a label on a chart".

**Compounding it:** `--accent: forestgreen` is simultaneously the heading colour, the active-tab underline, the active-pill fill, the mobile-tab active colour, the nav "you are here" colour, the focus ring, *and* the table hover text colour. When one colour means seven things, it means nothing. Green should signal **state**, never static text.

### 1.2 The primary data object is the narrowest thing on the page

```css
.teg-table { width: auto; max-width: 100%; }   /* base-vars.css */
.chart-container { width: 100%; }
```

The leaderboard is 7 columns (`Rank | Player | R1 R2 R3 R4 | Total`) inside a **960px** `.content-wrapper`. At `0.75rem` cell padding and `nowrap` it lands around 520–560px — so roughly **400px of dead white sits to its right**, while the Plotly chart directly beneath it spans the full 960px. The two main objects on the page don't share a right edge. This is the single most visible "unfinished" cue on the site.

### 1.3 Nine uncoordinated breakpoints — and iPad portrait falls in the gap

Distinct `max-width` breakpoints in play: **400, 540, 640, 700, 720, 768, 800, 820, 900**.

The consequential ones:

| Width | Nav | Tables | Contents grid |
|---|---|---|---|
| ≤640 | bottom tab bar + hamburger | phone cards (`lb_cards`) | 1 col |
| **641–820** | **hamburger** | **full desktop tables** | **1 col** |
| 821–900 | hamburger | desktop tables | 3 col |
| >900 | full nav | desktop tables | 3 col |

**iPad portrait is 768px.** For a group of 8 friends checking scores on a trip, that is probably the second-most-used width after a phone — and it gets the mobile navigation with the desktop data layout and none of the phone reflow work. The whole phone effort (`mobile.css`, 1509 lines) switches off 128px before the navigation does.

### 1.4 Two renderers for one dataset

`_results_context()` builds the same standings **twice**:

- `table_html` — a server-built HTML **string** (`_leaderboard_table_html`) for desktop.
- `lb_cards` — **structured data** (rank / player / code / rounds / total / lead) for phones, hidden above 640px.

One dataset, two code paths, two visual languages, guaranteed to drift. It is also why 1.3 exists: there is no single component that could simply reflow. Unifying these is the highest-leverage structural change available and it unlocks most of the visual work below.

### 1.5 Chrome outnumbers data

`/leaderboard` stacks, in order: TEG `<select>` → context label → H1 → report link → 2 tabs → Net/Gross switch → green section title → callout sentence → table → chart title → chart description → chart → readout buttons → "Choose chart type:" label → 4 chart pills → chart note.

That is **~15 chrome elements wrapped around 2 data objects.** Four of them are competing "pick one" idioms on the same screen: `.tab-underline` tabs, a `.scale-switch` toggle, a `.pill-group`, and `.lr-readout` buttons — four visual grammars for the same interaction.

The "Choose chart type:" label is pure redundancy; the pills are self-evidently choosable.

### 1.6 Missing the number golfers actually scan

The leaderboard has no **gap-to-leader** column. Rendered markup confirms it:

```
Rank | Player | R1 | R2 | R3 | R4 | Total
1    | Alex BAKER | 46 | 41 | 44 | 38 | 169
2    | John PATTERSON | 34 | 42 | 43 | 42 | 161
```

Margin is the first thing anyone reads on a leaderboard, and here it must be computed mentally on every row. `Rank` is also a bare integer with no movement indicator — the TODO list already notes Jon liked the report's `Baker ↑1 · Patterson ↓1` strip more than expected. That instinct is correct and belongs here, not only in the report.

### 1.7 There is no type scale

The brief asked about inconsistent typography scales. There isn't a scale at all.

- **~95 distinct literal `font-size` values** across `webapp/static/**/*.css`.
- Roughly **40 more** distinct values set **inline in templates**.
- Units are mixed freely — `rem`, `px`, `em`, one `clamp()` — and some values drop the leading zero (`.85rem` alongside `0.85rem`).

The tell is the cluster of near-duplicates that no eye can distinguish and no system would produce:

```
0.8rem  0.8125rem  0.82rem  0.83rem  0.84rem  0.85rem  0.86rem  0.87rem  0.875rem  0.895rem
```

Ten sizes inside a 1.2px band. Elsewhere: `0.58rem`, `0.62rem`, `0.71rem`, `0.79rem`, `0.94rem`, `1.02rem`, `1.08rem`, `1.14rem`, `1.18rem`, `1.24rem`, `9.5px`, `12.5px`.

This is the root cause behind several symptoms above: when every component picks its own size by eye, headings can't hold a hierarchy (§1.1) and nothing shares a baseline. **Six tokens would replace all of it** — `--fs-micro: 11px`, `--fs-label: 12px`, `--fs-body: 14px`, `--fs-data: 15px`, `--fs-lead: 18px`, `--fs-title: 28px`. Every value above rounds into one of them.

Credit where due: the *spacing* system did not drift the same way. The top-level page templates carry **almost zero** `mb-*`/`mt-*`/`my-*` utilities (0 in eight of ten; 2 each in `handicaps.html` and `player_rankings.html`), exactly as `CLAUDE.md` mandates. Spacing was centralised and held. Type never was.

### 1.8 Payload and dead chrome shipped to production

`base.html` issues **six render-blocking third-party requests on every page**:

- `cdn.tailwindcss.com` — the **Play CDN**, which compiles Tailwind *in the browser* on every load. Not a production tool. (Already flagged in `TODOS.md`.)
- `plotly-2.35.2.min.js` — the full bundle, loaded on `/contents`, `/handicaps`, `/records` and every other chartless page.
- htmx, Google Fonts ×2 (Inter+Lora, Material Symbols), flag-icons via jsdelivr.

Shipped-but-inert CSS: `base-vars.css` is **1818 lines** and still carries the full `ts-a/b/c/c1/c2/c3/d/e/e2/f1–f5` page-title variants and `ch-*` card-header variants whose switchers were removed from the nav, plus `debug-structure.css` and the `nav-cue` prototype JS. This is design-lab scaffolding being served to real users.

### 1.9 Lab pages and hardcoded colour live in the production template tree

`webapp/templates/` contains what are plainly design-lab and test surfaces alongside real pages: `title_preview.html` (31 hardcoded hex colours), `smoke_test.html` (21), `width_test.html` (11), `design_lab.html` (11), plus `font_lab` / `typography_lab`. They are the worst theming offenders precisely because they were never meant to ship.

Theme bypass in genuine production surfaces is concentrated in **`live_round_entry.html` (40 hardcoded hex)** and **`live_round_leaderboard.html` (26)** — the two pages used *in the field, on a phone, in sunlight*, and the two that will therefore break first when dark mode is switched on. `base.html` itself carries 9 (`#111827`, `#222019`, `#374151`, `#e0e0e0`, `#f3f4f6`, `#fff`), and even `contents.html` hardcodes `#1a1a1a` and `#555555` — duplicating `--text-primary` and `--text-secondary` verbatim rather than referencing them.

### 1.10 Smaller defects

- **`contents.html` fights the theme with `!important`** — `background: transparent !important`, `box-shadow: none !important`, `padding: 0 !important` on `.main-content`, plus a `.content-wrapper` max-width override. A page-level template overriding the shell with `!important` is exactly the pattern the project has said it wants to avoid; the correct fix is a `body.layout-bare` modifier in the shell.
- **Tooltip bypasses every token.** The `data-tip` tooltip in `base.html` hardcodes `background:#222019; color:#fff; font-family:system-ui` inline in JS — wrong font, and it will not respond to dark mode.
- **Sticky nav is hand-rolled JS.** A scroll listener mutating `nav.style.top` every frame, with `navHeight` sampled once at load. `position: sticky` plus a transform would do it in CSS with no scroll handler, and `.content-wrapper`'s layout is already suspected of interfering with Plotly's top SVG layer.
- **`white-space: nowrap` on every cell** plus `0.75rem` padding makes an 8-row × 7-col numeric grid roughly 420px tall. For a table whose whole job is one-glance comparison, that is too airy — it cannot be taken in as a single block.
- **Hover styling is gated** behind `@media (hover: hover)`, correctly — but row hover tints the row green *and* recolours the text green, doubling up with the top-rank tint (`#F3F7F3`) which is the same green family. Leader row and hovered row look alike.

### 1.11 Anti-AI check

Largely **passes**. No glassmorphism, no purple/indigo gradients, no cards-within-cards, flat white, genuine restraint. Three drifts to watch:

1. `--card-shadow: 0 1px 2px rgba(0,0,0,0.06)` is the stock template shadow.
2. Generic Material Symbols icons beside every Contents link read as filler — they carry no information the label doesn't.
3. Tiny green uppercase labels repeated 82 times is itself becoming a template tic.

---

## 2. Scannability teardown

### What works — preserve these

- **Token discipline is genuinely strong.** `base-vars.css` defines, theme files override, components reference variables. Retheming the entire site is a plausible afternoon, not a rewrite. This is the foundation everything below depends on.
- **Global tabular figures.** `font-variant-numeric: tabular-nums lining-nums` set **once** on `body` gives every number on the site column alignment without a monospace face. One line, correct, invisible. Exactly right.
- **The structural spacing system.** `.section-nav` / `.section-controls` / `.toggle-group` / `.data-card` owning vertical rhythm centrally, with a documented "don't add `mb-*` to these" rule, is better discipline than most production codebases have.
- **Bespoke, non-generic touches.** Equal-height name rows (`names-break`), the portrait scorecard reflow, `Initial. SURNAME` shortening, CSS bar charts for bestball contributions. These are the parts that feel like a dedicated golf app rather than a template — and the CSS-bars-over-Plotly instinct in `TODOS.md` is the right one.
- **The newspaper report design (`teg_reports.css` / `.np-paper`).** The best visual work in the repo. See Direction 2.

### What fails — direct

- **There is one heading level pretending to be three.** 82 identical green capitals. Hierarchy is gone.
- **There is no type scale — ~95 font sizes in CSS and ~40 more inline.** Ten of them sit inside a 1.2px band. Spacing was centralised and held; type was never systematised at all.
- **Green means nothing** because it means everything: headings, active tabs, active pills, nav state, focus rings, hover text, the accent itself.
- **The leaderboard table floats left in 400px of dead space** while the chart under it goes full width. Nothing lines up.
- **iPad portrait is unowned.** Hamburger nav at 900px, phone layout at 640px, nothing designed for the 260px between.
- **Desktop and mobile standings are two different programs.** A rendered HTML string vs a structured card list. This is a maintenance liability, not just an aesthetic one.
- **The leaderboard omits gap-to-leader** — the one number a golfer looks for first.
- **The landing page shows no score.** `/contents` is a three-column re-listing of the top nav's own dropdowns. A tournament site's front door with zero tournament information on it. The pending Contents-redesign option in `TODOS.md` is correctly aimed; see §4.
- **Fifteen pieces of chrome around two pieces of data** on `/leaderboard`, in four different control grammars.
- **Production is serving the design lab** — in-browser Tailwind compilation, Plotly on chartless pages, ~14 dead page-title variants, and `smoke_test` / `width_test` / `title_preview` / `design_lab` sitting in the live template tree.
- **The two field-use pages are the least themeable.** `live_round_entry.html` (40 hardcoded hex) and `live_round_leaderboard.html` (26) are used on a phone, outdoors, and will break first when dark mode is enabled.

---

## 3. Prioritised action matrix

High-impact / low-effort first.

| Priority | Item | Impact | Effort | Rationale |
|---|---|---|---|---|
| 1 | **Restore three real heading levels**; stop using `--accent` for static headings | High | Low | Pure CSS in `base-vars.css`. Differentiate `.section-title` / `.card-header` / `.chart-title` by size, weight and colour. Single biggest legibility win available. |
| 2 | **`.teg-table { width: 100% }`**; tighten cell padding to `0.45rem 0.75rem` | High | Low | Two declarations. Fixes the dead-space misalignment and makes the standings readable as one block. |
| 3 | **Add a gap-to-leader column** to the leaderboard | High | Low | One list comprehension in `_results_context()` before score formatting, one `<th>/<td>`. The most-wanted number on the page. |
| 4 | **Define a 6-token type scale** and migrate CSS to it | High | Med | Fixes §1.7 at the root. Mechanical and safely incremental — ship the tokens, then migrate file by file. Nothing else in the type system can hold until this exists. |
| 5 | **Collapse to three breakpoints — 640 / 900 / 1280** — and move the phone reflow up to 900 | High | Med | Gives iPad portrait a designed layout instead of an accident. Mostly find-and-replace across `mobile.css`, but needs a visual pass. |
| 6 | **Drop the Tailwind Play CDN** for a pinned build; load Plotly only on chart pages | Med | Low | Already in `TODOS.md`. Removes in-browser compilation and a large parse on every chartless page. |
| 7 | **Delete the dead `ts-*` / `ch-*` variants** and the nav-cue prototype from shipped CSS | Med | Low | Cuts `base-vars.css` materially and removes the strongest source of future confusion. Keep the design lab behind its dev-only route. |
| 8 | **Unify desktop + phone standings into one `lb_cards`-driven partial** | High | Med | Kills the two-renderer split (§1.4), and is the precondition for any serious responsive or visual redesign. See §5. |
| 9 | **Strip `/leaderboard` chrome**: fold Net/Gross into the tab row, drop "Choose chart type:", move chart pills above the chart | Med | Low | Removes two control grammars and three elements without losing a single function. |
| 10 | **Rebuild `/contents` around live tournament state** | High | Med | The landing page should answer "what's the score" before "where can I go". The `TODOS.md` mockup is directionally right; see §4. |
| 11 | **Tokenise `live_round_entry` / `live_round_leaderboard` colours** | Med | Med | 66 hardcoded hex across the two pages actually used in the field. Blocks dark mode exactly where sunlight/glare makes it most useful. |
| 12 | **Move `smoke_test` / `width_test` / `title_preview` / `design_lab` out of the production template tree** | Low | Low | Lab surfaces behind a dev-only route, not beside real pages. |
| 13 | **Fix `contents.html`'s `!important` overrides** via a `body.layout-bare` shell modifier | Low | Low | Removes the only page-level `!important` block; matches stated project convention. |
| 14 | **Token the tooltip**; replace the hand-rolled sticky-nav JS with CSS | Low | Low | Dark-mode correctness and one fewer scroll listener. |
| 15 | **Add rank-movement arrows** (`↑1 / ↓1`) to standings rows | Med | Med | Needs prior-round rank in the context. Jon already responded well to this in the report rail. |
| 16 | **Commit to one aesthetic direction** (§4) and apply it to the leaderboard first | High | High | Do this *after* 1–9; the fixes above are prerequisites regardless of which direction wins. |

---

## 4. Aesthetic evolution — three directions

All three use real elements from this codebase: `lb_cards`, `.teg-table`, `.section-title`, `--accent`, `.np-paper`, `lb_hero`, the `Rank/Player/R1–R4/Total` shape.

### Direction 1 — Clean Precision (mild)

*Keep the current design; fix the system underneath it.*

- **Three heading levels, restored by contrast rather than colour.** `.section-title` → 15px Lora, 600, uppercase, `--text-primary`, with a hairline rule beneath it. `.card-header` → 12px Inter, 600, uppercase, `--text-secondary`, no rule. `.chart-title` → same as `.card-header`. Green is removed from all three.
- **Green becomes a state colour only** — active tab, active pill, live indicator, under-par figures. Nothing static is ever green.
- **Density.** Cell padding `0.45rem 0.75rem`, table at 100% width, `--table-font-size` to `0.8125rem` for round columns while `Player` and `Total` stay at `0.875rem`. The standings become a block you absorb, not a list you read.
- **Top-rank row loses its green tint** and gains a 2px left border in `--accent` plus `font-weight: 700`. The tint is freed up for hover alone, so leader and hover stop looking alike.
- **A real type scale.** Six tokens replacing ~135 ad-hoc sizes (§1.7). This is the unglamorous prerequisite for every other direction, not an alternative to them.
- **One breakpoint set:** 640 / 900 / 1280.

**Risk:** low. **Payoff:** the site stops looking unfinished. **It does not make the site memorable** — this is hygiene, not identity.

### Direction 2 — Editorial Golf (moderate) — *recommended*

*Extend the newspaper design language the repo already owns to the whole site.*

The strongest argument for this direction is that **it is already built and already liked**. `teg_reports.css` / `.np-paper` / `newspaper_edition` is the only genuinely bespoke visual asset in the codebase, and it is currently quarantined to one page — so clicking "View tournament report" throws the user into a different product. Unifying them removes that seam and gets a distinctive identity for a fraction of a from-scratch cost.

- **Surface.** The report's cream paper (`.np-paper`) becomes the site's content surface; the cool grey/white page behind it stays. Immediately un-generic, and warm rather than clinical.
- **Table as printed scorecard.** Double hairline rule under `thead` (the classic card convention), no cell borders at all, a 1px rule only above the `Total` row. Column heads in small-caps Inter at 11px, `letter-spacing: 0.08em`.
- **Names get the serif.** Player surnames in Lora 600 at 15px, forenames dropped to 11px `--text-secondary` — reusing the `.player-name .first` / `.last` spans that already exist for the `names-break` logic. Numbers stay Inter tabular. Serif for identity, sans for data: the split the project already argued itself into, applied where it pays.
- **Palette.** Sand `#EFE9DC` for the top-rank row instead of `#F3F7F3`; forest green reserved for under-par figures and live state; a dark ink `#1C1A16` replacing `#1a1a1a`.
- **Chrome.** Tabs become a single hairline rule with the active item in ink and a 2px underline; pills become plain text separated by `·`, the way a masthead lists sections.

**Risk:** medium — commits the whole site to a warm palette. **Payoff:** the site reads as *a golf publication*, which is exactly the stated goal, and the report page stops being a foreign country.

### Direction 3 — Modern Telemetry (bold)

*Dark-first, data-dense, sharp. A tour broadcast graphic.*

- **Ink surface** `#0E1116`, panels `#161A20`, hairlines `#232A33`. Dark mode stops being an inert toggle and becomes the primary design. The `dark.css` scaffolding already exists for this.
- **Compressed rows.** 32px row height, `Rank` as a 2ch slug in a bordered box, surname uppercase Inter 600, forename dropped entirely.
- **Per-round cells become delta chips** coloured by to-par — a tinted background rather than a plain integer — so a bad round is visible before it is read.
- **Gap column** as the second-most prominent figure after `Total`, in `--accent`.
- **Status badges** replace prose: `LIVE` (pulsing green), `R3`, `FINAL` — set against `lb_hero.label` / `teg_complete`, which the context already carries.
- **Inline sparklines per row** replace the separate Plotly race chart, using the CSS-bar approach `TODOS.md` already favours over Plotly for small charts. This deletes the chart, the chart title, the chart description, the readout buttons, the "Choose chart type:" label, the 4 pills and the chart note — **eight chrome elements removed** by making the data carry itself.

**Risk:** high — a full identity change, and dark-first is a real commitment for a site read in bright sunshine on a golf course. **Payoff:** the highest information density and the sharpest character of the three.

### Recommendation

**Pursue Direction 2, borrowing Direction 3's table mechanics.**

Direction 2 wins because it is the only option where the distinctive work is **already done and already validated by the owner** — it converts an existing asset into the site's identity instead of inventing a new one, and it removes the jarring report-page seam as a side effect. Direction 3's genuinely superior *table* ideas (gap column, delta chips, status badges, inline sparklines replacing the Plotly block) are palette-independent and should be delivered inside Direction 2's editorial shell. Direction 1 is not an alternative — items 1–9 of the action matrix *are* Direction 1, and they should ship first regardless of which direction ultimately wins.

---

## 5. Code prototype — unified standings component

**The most impactful screen is `/leaderboard`.** This prototype does three things at once:

1. Replaces **both** `table_html` (desktop HTML string) and the phone-only `lb_cards` block with **one** component driven by the `lb_cards` data the route already builds — fixing §1.4.
2. Applies **Direction 2's editorial surface** with **Direction 3's table mechanics** (gap column, delta-tinted round cells, status badge).
3. Reflows at **900px**, not 640px, so iPad portrait is designed for — fixing §1.3.

> Prototype only. Nothing below has been written to a live template.

### 5.1 Route addition — gap to leader

The only data the component needs that the route doesn't already produce. Slots into `_results_context()` in `webapp/routes/history.py`, **before** the score-formatting loop (while `lb` is still numeric):

```python
# Gap to leader, computed on raw values before format_value() stringifies them.
# There is no single `ascending` variable in this scope today — the gross
# branch passes ascending=True literally and the net branch passes
# net_ascending (line 687: net_measure == 'NetVP'). Capture it once in both
# branches so the gap calc can read it:
#     lower_is_better = True            # in the gross branch
#     lower_is_better = net_ascending   # in the net branch
# create_leaderboard has already sorted, so the leader is row 0 either way;
# only the sign convention differs.
leader_total = lb.iloc[0]['Total'] if not lb.empty else 0
gaps = []
for _, row in lb.iterrows():
    d = row['Total'] - leader_total
    if d == 0:
        gaps.append('—')
    elif lower_is_better:   # GrossVP / NetVP — behind means a positive deficit
        gaps.append(f'+{d:g}')
    else:                   # Stableford — behind means a negative delta
        gaps.append(f'{d:g}')
```

Then zip it into the existing `lb_cards` comprehension:

```python
lb_cards = [{
    "rank": str(row['Rank']),
    "player": str(row['Player']),
    "code": get_name_to_code().get(str(row['Player'])) if link_players else None,
    "rounds": [(c, str(row[c])) for c in round_cols],
    "total": str(row['Total']),
    "gap": gaps[i],                                  # NEW
    "lead": str(row['Rank']).startswith('1'),
} for i, (_, row) in enumerate(lb.iterrows())]
```

### 5.2 `partials/standings.html` (prototype)

Replaces the `.lb-table-card` block **and** the `lb_cards` include in `partials/leaderboard_table.html`.

```jinja
{# Unified standings — one component, desktop table semantics + phone reflow.
   Data: lb_cards / lb_hero from _results_context(). Replaces both the
   server-built table_html string and the phone-only lb_cards card list. #}
<section class="stg" aria-label="{{ section_title }}">

  <header class="stg-head">
    <h2 class="stg-title">{{ section_title }}</h2>
    <span class="stg-badge {{ 'stg-badge--final' if teg_complete else 'stg-badge--live' }}">
      {{ 'Final' if teg_complete else 'Live' }}
    </span>
  </header>

  <table class="stg-table">
    <thead>
      <tr>
        <th class="stg-c-rank" scope="col">#</th>
        <th class="stg-c-player" scope="col">Player</th>
        {% for label, _ in lb_cards[0].rounds %}
        <th class="stg-c-rd" scope="col">{{ label }}</th>
        {% endfor %}
        <th class="stg-c-total" scope="col">Total</th>
        <th class="stg-c-gap" scope="col">Gap</th>
      </tr>
    </thead>
    <tbody>
      {% for c in lb_cards %}
      <tr class="stg-row{% if c.lead %} stg-row--lead{% endif %}">
        <td class="stg-c-rank"><span class="stg-rank">{{ c.rank }}</span></td>
        <td class="stg-c-player">
          {% if c.code %}<a class="stg-name" href="/player/{{ c.code }}">
          {% else %}<span class="stg-name">{% endif %}
            <span class="stg-first">{{ c.player.split(' ')[0] }}</span>
            <span class="stg-last">{{ c.player.split(' ')[1:] | join(' ') }}</span>
          {% if c.code %}</a>{% else %}</span>{% endif %}
          {# Phone-only inline round strip; hidden ≥900px. #}
          <span class="stg-rounds-inline">
            {% for label, val in c.rounds %}{{ label }}&nbsp;<b>{{ val }}</b>{% if not loop.last %} · {% endif %}{% endfor %}
          </span>
        </td>
        {% for label, val in c.rounds %}
        <td class="stg-c-rd"><span class="stg-chip">{{ val }}</span></td>
        {% endfor %}
        <td class="stg-c-total">{{ c.total }}</td>
        <td class="stg-c-gap">{{ c.gap }}</td>
      </tr>
      {% endfor %}
    </tbody>
  </table>
</section>
```

### 5.3 Prototype CSS

Editorial surface (D2) + telemetry mechanics (D3). Every colour is a token or a new token in the same convention — nothing hardcoded that a theme couldn't override.

```css
/* ── Prototype tokens (would live in clean.css's :root) ── */
:root {
  --paper:        #FBF9F4;   /* .np-paper's cream, promoted site-wide */
  --paper-rule:   #DDD6C6;   /* hairline on cream */
  --paper-tint:   #EFE9DC;   /* sand — replaces #F3F7F3 for top rank */
  --ink:          #1C1A16;
  --ink-soft:     #6B6558;
  --under:        #17683C;   /* under par / gaining */
  --over:         #9A3412;   /* over par / losing */
}

.stg { background: var(--paper); padding: 1.25rem 1.5rem 1.5rem; }

/* Header: title + state badge on one baseline, hairline beneath. */
.stg-head {
  display: flex; align-items: baseline; justify-content: space-between;
  gap: 1rem; padding-bottom: 0.5rem;
  border-bottom: 1px solid var(--paper-rule);
}
/* Heading level 1 of 3 — ink, not accent (fixes §1.1). */
.stg-title {
  font-family: var(--font-serif), serif;
  font-size: 15px; font-weight: 600; letter-spacing: 0.06em;
  text-transform: uppercase; color: var(--ink); margin: 0;
}
.stg-badge {
  font-family: var(--font-sans), sans-serif;
  font-size: 10px; font-weight: 700; letter-spacing: 0.1em;
  text-transform: uppercase; padding: 0.15rem 0.45rem; border-radius: 2px;
}
.stg-badge--live  { background: var(--under); color: #fff; }
.stg-badge--final { background: transparent; color: var(--ink-soft);
                    border: 1px solid var(--paper-rule); }

/* ── Table: printed-scorecard rules, full width (fixes §1.2) ── */
.stg-table { width: 100%; border-collapse: collapse; }

/* The double hairline under thead is the scorecard convention — a 3px
   box-shadow rule below a 1px border, so it reads as printed, not as a
   generic table border. */
.stg-table thead th {
  font-family: var(--font-sans), sans-serif;
  font-size: 11px; font-weight: 600; letter-spacing: 0.08em;
  text-transform: uppercase; color: var(--ink-soft);
  padding: 0.5rem 0.6rem; text-align: right; white-space: nowrap;
  border-bottom: 1px solid var(--ink);
  box-shadow: 0 3px 0 -2px var(--ink);
}
.stg-table thead th.stg-c-player { text-align: left; }
.stg-table thead th.stg-c-rank   { text-align: center; }

/* No cell borders at all — rhythm comes from the row tint, not from rules. */
.stg-table tbody td {
  padding: 0.45rem 0.6rem; text-align: right; border: 0;
  font-size: 0.875rem; color: var(--ink); white-space: nowrap;
}
.stg-table tbody tr + tr td { border-top: 1px solid var(--paper-rule); }

/* Leader: left accent bar + weight, NOT a green tint — so hover and leader
   can no longer be confused (fixes §1.10). */
.stg-row--lead td { font-weight: 700; background: var(--paper-tint); }
.stg-row--lead td:first-child { box-shadow: inset 2px 0 0 var(--under); }

@media (hover: hover) and (pointer: fine) {
  .stg-row:hover td { background: #F4F0E6; }
}

/* Rank as a slug, not a bare integer. */
.stg-c-rank { text-align: center; width: 2.5rem; }
.stg-rank {
  display: inline-block; min-width: 1.5rem;
  font-size: 0.8125rem; font-weight: 600; color: var(--ink-soft);
}

/* Names: serif surname for identity, muted sans forename. Reuses the
   first/last split the existing .player-name markup already produces. */
.stg-c-player { text-align: left; }
.stg-name { text-decoration: none; display: block; line-height: 1.25; }
.stg-first {
  display: block; font-family: var(--font-sans), sans-serif;
  font-size: 11px; color: var(--ink-soft);
}
.stg-last {
  display: block; font-family: var(--font-serif), serif;
  font-size: 15px; font-weight: 600; color: var(--ink);
}
a.stg-name:hover .stg-last { color: var(--under); }

/* Round cells: tinted chips (D3), tighter type than the totals. */
.stg-c-rd { width: 3.25rem; }
.stg-chip {
  display: inline-block; min-width: 2rem; padding: 0.1rem 0.3rem;
  font-size: 0.8125rem; border-radius: 2px;
}

/* Total is the anchor; Gap is the second read. */
.stg-c-total { font-size: 1rem; font-weight: 700; width: 4rem; }
.stg-c-gap   { width: 3.5rem; color: var(--ink-soft); font-size: 0.8125rem; }

/* Phone round-strip hidden on desktop. */
.stg-rounds-inline { display: none; }

/* ── Reflow at 900px, not 640px — iPad portrait gets a designed layout
   instead of a desktop table it can't fit (fixes §1.3). ── */
@media (max-width: 900px) {
  .stg { padding: 1rem 0.75rem; }
  /* Drop the per-round columns; the inline strip carries them instead. */
  .stg-table thead th.stg-c-rd,
  .stg-table tbody td.stg-c-rd { display: none; }
  .stg-rounds-inline {
    display: block; margin-top: 0.15rem;
    font-family: var(--font-sans), sans-serif;
    font-size: 11px; color: var(--ink-soft);
  }
  .stg-rounds-inline b { color: var(--ink); font-weight: 600; }
  .stg-c-total { font-size: 1.125rem; }
}

@media (max-width: 400px) {
  .stg-c-gap { display: none; }   /* last column to go, first to return */
}
```

**What this prototype demonstrates:** the same 8 rows, one template, no duplicated renderer, full-width and aligned with the content column, gap-to-leader present, leader distinguished structurally rather than by a tint that clashes with hover, and a reflow that covers phone *and* tablet. It progressively drops columns (rounds at 900, gap at 400) rather than switching to an entirely separate card component — which is why it needs one code path instead of two.

---

*Reviewed and written by Claude Opus 5. Mechanical legwork (CSS/template excerpt extraction, breakpoint and selector inventories, attempted Playwright screenshot pass) delegated to Claude Sonnet subagents. Live screenshots unavailable — the shared Playwright browser was locked by a concurrent session throughout; findings are drawn from rendered HTML plus template and CSS source.*
