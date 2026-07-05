# Design round 2 — three themes, nine stylings

Prototype restyles of the webapp against the real Results and Player pages, answering
`BRIEF_v2.md` (three genuinely distinct visual languages, not palette swaps). This folder is
self-contained and **not wired into the webapp** — it's an exploration to choose a direction from.

**Start here: open [`index.html`](index.html)** (serve the folder with `python3 -m http.server`
from `design_round2/`, or open files directly — everything except Google Fonts is vendored).
Full-page PNGs of every variant are in `screenshots/`.

## The nine stylings

| Theme | Language | Stylings |
|---|---|---|
| **A — Plain** | The reference book: no cards, no fills; hierarchy from type, hairline rules, alignment | **Ledger** (warm paper / bottle green · Source Serif 4 + IBM Plex Mono) · **Gridline** (Swiss white / signal red · Archivo + Spline Sans Mono) · **Manila** (records office tan / burnt orange · Public Sans + Fragment Mono) |
| **B — Editorial** | The tournament programme: masthead nav, numbered sections, box-score tables, figure-framed charts | **Broadsheet** (newsprint / press blue · Frank Ruhl Libre + PT Serif + Courier Prime) · **Order of Merit** (cream / racing green / oxblood / gold · Cormorant + EB Garamond + Cousine) · **Pressbox** (navy + tomato · Zilla Slab + Faustina + Space Mono) |
| **C — Striking** | The almanac infographic: solid-block chrome, filled segments, rank-tier colour coding, named chart palettes | **Scoreboard** (Augusta greens + gold · Barlow Semi Condensed + JetBrains Mono) · **Almanac** (538-style paper + 5-hue system · Archivo Black + IBM Plex Mono) · **Floodlight** (dark-first broadcast lime/cyan · Space Grotesk + IBM Plex Mono) |

Every styling has an intentionally designed dark mode under `html[data-mode="dark"]`
(Floodlight is dark-first; its light mode is the secondary design). The light/dark toggle on
each page works client-side and re-renders the Plotly charts from the styling's tokens.

## Layout

```
css/                     copies of the app's structural sheets (base-vars, mobile, teg_reports)
vendor/                  plotly.min.js (2.35.2), pre-compiled tailwind.css — pages work offline
shared/retheme.js        chart re-theming from --chart-* tokens, client mode toggle, tier classes
theme-{a,b,c}-*/
  theme.css              the theme's structural language (component rules, token-driven)
  components.html        component sheet with in-page styling switcher
  {styling}/tokens.css   the styling: light :root + html[data-mode="dark"] block + font imports
  {styling}/results.html + player.html
screenshots/             full-page PNGs: {styling}--{page}--{mode}.png + {styling}--components.png
_build/                  build.py (stamps pages from saved sources) + shoot.py (screenshots)
```

## How a chosen styling goes back into the webapp

1. Its `tokens.css` becomes a theme file in `webapp/static/themes/` (same token names as
   `clean.css`; dark block merges into the `dark.css` pattern).
2. The theme's `theme.css` component rules fold into `base-vars.css` (or a per-theme structural
   sheet loaded after it) — they only touch existing classes.
3. `retheme.js`'s chart theming (reading `--chart-*` / `--font-data` via `getComputedStyle`)
   ports into the webapp's chart-render hook in `base.html`; the tier-class logic maps onto the
   leaderboard template server-side.

## New tokens proposed (called out per BRIEF_v2 §5.1)

- `--font-data` — the data/table mono per styling (currently hard-coded `'Roboto Mono'`).
- `--table-header-text` — header-band text colour, needed once headers get solid fills (Theme C).
- `--table-tier1-bg/-text`, `--table-tier2-bg/-text`, `--table-tiermid-bg/-text`,
  `--table-tierlast-bg/-text` — rank-tier row coding, extending the `--table-toprank-*` pattern.
  Themes A/B leave them unset (the runtime only applies tier classes when `--table-tier1-bg`
  exists); they also reuse `--table-tierlast-text` as the "bad/worst" red where one is needed.
- `--chart-1` … `--chart-8`, `--chart-grid`, `--chart-axis-text` — chart palette + axis chrome.

Everything else re-declares the existing token names from `BRIEF_v2.md` §6.
