# Handoff: TEG web app — Mono theme

## Overview
A monospace, "record-book" visual theme for the TEG golf-stats web app (currently a
Streamlit/HTMX app branded **The El Golfo**). The core idea: a plain white (light) or
near-black (dark) page with **no cards, no page-background panels**. All tabular/quantitative
content lives in a monospace font inside a subtly **shaded "band"** that sets the data apart
from the page. One accent colour — forest green — used sparingly.

This document covers the two representative pages built: **Full Results** and **Player Profile**.

## About the Design Files
The bundled file `TEG Pages.dc.html` is a **design reference created in HTML** — a prototype
showing the intended look and behaviour. It is **not production code to copy directly**. The
task is to recreate this theme in the app's real environment (server-rendered HTML + CSS here),
using its established patterns. Treat the hex values, spacing, and type scale below as the
source of truth; treat the HTML as a visual reference.

> The prototype toggles Light/Dark, Page-cap On/Off, and Results/Player via a dark "studio
> control bar" at the top. **That bar is a prototyping device — do not ship it.** In the real
> app, Light/Dark is the user's existing mode toggle, and the page cap is a fixed layout rule
> (see Layout).

## Fidelity
**High-fidelity.** Colours, spacing, type scale, and interactions are final. Recreate
pixel-accurately, but see the note on fonts below.

### Fonts (intentionally swappable)
The prototype uses **IBM Plex Sans** (headings/UI) + **IBM Plex Mono** (all data). The user
plans to define fonts separately in the codebase. So: keep the **two-role split** (one UI/sans
face, one monospace face for all numeric/tabular content), but the exact families are the dev's
choice. Everywhere the spec says "mono", it means the monospace face; "sans" means the UI face.

## Design Tokens

Define these as CSS custom properties and switch the whole set on `[data-mode="dark"]`.

### Light mode
| Token | Value | Use |
|---|---|---|
| `--bg` | `#ffffff` | page background |
| `--ink` | `#12140f` | primary text, headings, strong numbers |
| `--ink2` | `#4a4d44` | secondary body text |
| `--muted` | `#8a8d82` | captions, column heads, inactive tabs, eyebrows |
| `--sec` | `#a9aca1` | de-emphasised rank numbers (rows 2..n) |
| `--accent` | `#21663f` | the one accent — tags, active tab/underline, leader, links, chart series |
| `--band-bg` | `#f6f6f3` | the shaded data band |
| `--divider` | `#e6e7e0` | hairline rules (nav border, tab underline track, chip borders) |
| `--data` | `#2a2d24` | body text inside data tables |
| `--star` | `#c0962c` | trophy stars (gold) |
| `--bad` | `#9c3a2a` | negative/"loss" accents (wooden spoon, worst course) |
| `--badgetext` | `#ffffff` | text on a filled accent badge |
| `--grid` | `#e8e8e1` | chart gridlines |
| `--axis` | `#8a8d82` | chart axis text |

### Dark mode ("neutral grey lift" — no warm/olive cast)
| Token | Value |
|---|---|
| `--bg` | `#0d0d0d` |
| `--ink` | `#f0f0ee` |
| `--ink2` | `#b5b5b3` |
| `--muted` | `#7d7d7d` |
| `--sec` | `#6e6e6e` |
| `--accent` | `#6bbf83` |
| `--band-bg` | `#1b1b1b` |
| `--divider` | `#262626` |
| `--data` | `#d7d7d5` |
| `--star` | `#d2ab48` |
| `--bad` | `#d98a7a` |
| `--badgetext` | `#0d0d0d` |
| `--grid` | `#2b2b2b` |
| `--axis` | `#7d7d7d` |

### Spacing / type scale
- Page horizontal padding (`--wrap-pad`): **32px**.
- Page max-width cap: **1040px**, centred (`margin: 0 auto`). This is a **fixed rule**, not a toggle.
- Section-to-section vertical gap: **~34px** (`margin-top` on each block).
- H1 (page title): sans, **34px / 700 / letter-spacing −0.02em / line-height 1.05**.
- H2 (section title): sans, **20px / 700 / −0.01em**.
- Eyebrow (above H1): mono, **11px / letter-spacing .16em / UPPERCASE**, colour `--accent`.
- Band tag (above each band): mono, **10.5px / .14em / UPPERCASE**, colour `--accent`,
  prefixed with "▸ ", `padding-bottom: 8px`. E.g. `▸ leaderboard · net`.
- Table data: mono, **14px** (wide results table 13px).
- Table column heads: mono, **11.5px / 500**, colour `--muted` (10.5px on wide table).
- Captions / metadata: mono, **12px**, colour `--muted`.
- Stat number (metrics): mono, **26px / 600**, colour `--ink`.

## The "band" — the one structural primitive
Every block of data (leaderboard, chart, metrics, trophy cabinet, wide table) is preceded by an
accent **tag line** and wrapped in a **band**. **Locked variant: "Contained".**

```css
.band {
  background: var(--band-bg);
  margin: 0;                 /* contained: hugs the content column */
  padding: 18px 22px;        /* contained */
  border-radius: 3px;
  /* NO borders. No top/bottom hairlines, no box-shadow. */
}
```

> A "Full-width" variant (band bleeds to the page-cap edges via negative margin, 0 radius,
> 22px vertical padding) was explored and **rejected** in favour of Contained. Ship Contained only.

Prose that sits *between* the H2 and the band (section title + caption + the ▸ tag) stays on the
plain page background, **outside** the band. Only the data goes inside.

## Screens / Views

### 1. Full Results
- **Purpose:** view a chosen TEG's final leaderboard + the cumulative-points race chart.
- **Layout (top → bottom):** masthead → controls row → leaderboard block → chart block.
- **Masthead:** eyebrow `HISTORY · TEG 18` (accent mono), H1 `Full Results`. No divider rule.
- **Controls row:** a `<select>` (TEG picker; mono, 12.5px, 1px `--divider` border, radius 5px,
  padding 6px 10px) sitting left of a tab strip. Tabs: `TEG Trophy` (active) · `Green Jacket` ·
  `Scorecards` · `Report`. Tab strip has a bottom `1px --divider` track; the active tab is
  `--ink` 600 with a **2px `--accent` bottom border** (−1px margin so it sits on the track);
  inactive tabs are `--muted`.
- **Leaderboard block:** H2 `TEG Trophy — Final Leaderboard`; caption
  `champion Alex BAKER · wooden spoon Jon BAKER`; tag `▸ leaderboard · net`; then a band
  containing the table.
  - **Table (no horizontal borders at all):** columns `#`, `Player`, `R1`–`R4`, `Total`.
    `#` and `Player` left-aligned; scores and total right-aligned. Column heads `--muted` 11.5px.
    Row cells padded **11px 8px** (10px horizontal on score columns) — airy, whitespace-separated.
    Row 1 (leader): rank `01` in `--accent` 700, player name `--ink` 700, total `--ink` 700.
    Rows 2+: rank in `--sec`, name/scores in `--data`, total 700.
    **Row hover:** all cells in the row → `color: var(--accent)`.
  - Data: `01 Alex BAKER 46 41 44 38 169` / `02 John PATTERSON 34 42 43 42 161` /
    `03 Gregg WILLIAMS 31 42 43 44 160` / `04 David MULLIN 32 35 44 38 149` /
    `05 Jon BAKER 30 39 28 29 126`.
- **Chart block:** H2 `TEG Trophy race`; caption `cumulative stableford · higher = better`;
  tag `▸ chart · teg 18`; band containing a **340px-tall line chart** (see Charts). Below the
  band, a "chart type" mono label + 3 pill toggles (`Standard` active, `Adjusted scale`,
  `Ranking`): pills are mono 12px, radius 999px, padding 4px 13px; active = 1px `--accent`
  border + `--accent` text 600; inactive = 1px `--divider` border + `--muted` text.

### 2. Player Profile
- **Purpose:** a single player's career overview (example player: **Jon BAKER**).
- **Layout:** masthead (eyebrow → roster chips → name+stars → meta) → tabs → metrics band →
  Trophy Cabinet → Career Highlights → Records & Worsts → TEG Results (wide table) → Career Trend chart.
- **Roster chips:** mono 11.5px pills, radius 999px, padding 4px 12px, 1px `--divider` border,
  `--muted` text; the selected player chip uses 1px `--accent` border + `--accent` 600 text.
- **Name + rating:** H1 `Jon BAKER` followed by an 8-star rating inline (21px): first 4 stars
  `--star` (gold), last 4 `--accent`. Meta line (mono, `--muted`): `first TEG 2 (2009) · latest TEG 18 (2025)`.
- **Tabs:** `Overview` (active) · `Rounds` · `Scoring` · `Records & Streaks` — same tab styling as Results.
- **Metrics band:** tag `▸ career · at a glance`; band with a **4-column grid** (26px row gap,
  20px column gap) of stat cells. Each cell = mono uppercase label (10px, .08em, `--muted`) then
  a value row: 26px/600 `--ink` number + optional small `--muted` rank note. Cells:
  `TEGs Played 17 (1st =)`, `Total Trophies 8 (2nd)`, `Avg Gross vs Par +20.5 (2nd)`,
  `Avg Stableford 36.1 (4th)`, `Holes in One 0`, `Eagles 1 (1st =)`, `Birdies 45 (2nd)`.
- **Trophy Cabinet:** H2 + caption `including 3 Trophy / Jacket doubles`; tag `▸ honours`; band
  with a 3-column grid: `TEG Trophies 4 (1st =)` + ★★★★ in `--star`; `Green Jackets 4 (2nd)` +
  ★★★★ in `--accent`; `Wooden Spoons 2 (4th =)`.
- **Career Highlights & Records & Worsts:** each a 2-column grid (22px/40px gaps) of
  **detail cells**. A detail cell = a **2px left border** (colour `--accent`, or `--bad` for a
  negative one like "Worst Course") with 16px left padding, containing: mono uppercase eyebrow
  (10px `--muted`), sans heading (19px/700 `--ink`), mono sub (11.5px `--ink2`).
  These cells sit on the **plain page**, not in a band.
  - Highlights: `Best Course / Littlestone / avg +14.5 over 2 rounds`;
    `Worst Course / Estoril / avg +25.5 over 2 rounds` (bad);
    `Best Round / +8 / TEG 13 R3 · Littlestone`; `Best TEG / +50 / TEG 13`.
  - Records: `Best gross TEG / +50 / TEG 13 (Kent, England, 2020)`;
    `Longest birdies streak / 2 holes / T17 R4 H4 → T17 R4 H5`;
    `Longest pars-or-better streak / 6 holes / T10 R2 H5 → T10 R2 H10`;
    `Most birdies in a round / 4 / TEG 14 R4 (Prince's, Nov 2021)`. Footnote (mono `--muted`):
    `no outright TEG worsts held`.
- **TEG Results (wide table):** H2 + tag `▸ all appearances`; band with `overflow-x: auto` and a
  `white-space: nowrap` mono table (13px). Columns: `TEG`, `Year`, `Gross VP`, `Net/Stab`,
  `Trophy`, `Gross`, `Result`. `TEG` in `--ink` 600, `Year` in `--sec`, figures in `--data`.
  Trophy/Gross rank columns centred; a `win` rank is `--accent` 600, a `loss` rank is `--bad` 600.
  **Result badges:** `win` → filled pill `background: --accent; color: --badgetext` (e.g. Double,
  Trophy, Jacket, 1st); `loss` → outline pill `1px --bad border; --bad text` (e.g. Spoon). No row borders.
- **Career Trend:** H2; two pill toggles above (`Gross vs Par` active / `Stableford`), same pill
  styling as chart-type; tag `▸ per teg · avg / round`; band with a **320px bar chart**.

## Interactions & Behavior
- **Tabs / pills:** click sets active; only visual state in the prototype. Wire to the app's real routing/data.
- **Row hover** on data tables recolours the row to `--accent` (150ms is fine; prototype is instant).
- **Light/Dark:** swap the token set on `[data-mode]`. Charts must be re-rendered on mode change
  (their colours come from the tokens, not CSS).
- **Career Trend toggle:** switches the bar chart's series between Gross-vs-Par and Stableford and
  recomputes the dashed average line + its annotation.
- **Responsive:** page is capped at 1040px and padded 32px. Mobile app-shell view was **not** part
  of this handoff (still to be designed) — implement desktop density first.

## State Management
- `mode`: `'light' | 'dark'` (global; persist to the app's existing mode cookie/localStorage).
- `chart`: `'gross' | 'stab'` (Career Trend series).
- Selected TEG / selected player / active tab: driven by the app's existing data layer/routing.

## Charts
Built with **Plotly** in the prototype (`plotly-2.35.2`). Re-implement with whatever the codebase
uses; the styling contract:
- Transparent paper & plot background; font = mono 11px, colour `--axis`.
- Gridlines `--grid`; no zero-lines; legend horizontal on top where shown.
- **TEG Trophy race:** 5 line series, cumulative stableford over 72 holes, x-ticks at holes
  9/27/45/63 labelled R1–R4. Series palette: `[--accent, #4f9268, #86b893, --star, --muted]`.
- **Career Trend:** single bar series in `--accent`, 17 TEGs on x; dashed `--muted` average line
  with an `Avg NN.N` annotation.

## Assets
None external beyond fonts and the chart library. Trophy "stars" are the `★` glyph coloured via
tokens (no image). The `◐` in the nav is a placeholder mode-toggle glyph — replace with the app's icon.

## Files
- `TEG Pages.dc.html` — the full prototype (both pages, both modes, the page-cap rule, charts).
  Open it in a browser to see every state. Ignore the top dark "studio control bar" (prototyping only).
