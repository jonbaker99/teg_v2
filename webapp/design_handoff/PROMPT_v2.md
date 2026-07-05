# Kickoff prompt for Fable (round 2 — three-theme reimagine)

Paste the text below into Fable. Attach: `BRIEF_v2.md`, the three HTML files in `pages/`, and the screenshots in `pages/screenshots/` (at least the `*-light`, `*-dark`, and `*-card-light` images). You can also attach `BRIEF.md` from the first round purely as a "here's what we don't want to repeat" reference — flag it as such.

---

I'm doing a full design reimagine of a data-dense web app — a private golf-tournament analysis site (an annual event called "the TEG"). It shows leaderboards, scorecards, player rankings, statistical tables and charts. The audience is small and knowledgeable, and this is a personal/hobby project — the feel should be considered and well-crafted, not corporate.

I've attached: (1) a design brief (`BRIEF_v2.md`) with the constraints, token system, and three theme concepts I want explored, (2) rendered HTML of three representative pages (Contents, Results, Player) with real data, (3) screenshots of those pages in the current light/dark themes, and (4) for reference only, the brief and output from a first attempt at this (`BRIEF.md`) that came back too generic — three palettes on the same skeleton, with the kind of soft-gradient, rounded-everything, Inter-font look that a lot of AI-assisted design defaults to. **Please read `BRIEF_v2.md` first** — it explains exactly what went wrong last time and lists the hard constraints (token names, light/dark, desktop density) I need honoured regardless of how different the visual language gets.

I want **three broad themes**, each a genuinely distinct visual language — not palette swaps of the same layout:

1. **Plain** — elegant, clean, no distractions, but still clearly professionally designed (not "unstyled").
2. **Editorial** — reads like a newspaper sports section or tournament programme, with real typographic hierarchy.
3. **Striking** — visually engaging, bolder use of colour and contrast, colour-coded data — while staying legible for serious repeated use.

Within **each** theme, show **3 distinct colour/font stylings** (9 total), each with its own name — different enough from each other to be clearly separate options, not near-duplicates. For every theme, cover: overall page chrome and site navigation, in-page navigation (tabs/filter pills), and the layout/presentation of prose, data tables, and charts.

Push hard against generic AI-generated web design — no purple/blue gradients, no glassmorphism, no Inter-everywhere, no floating soft-shadow cards as the default surface, no rounded-corner-on-everything. Each of the 9 stylings should feel like someone made specific, opinionated choices for *this* data and *this* audience.

Design a **unified component sheet per theme** (components can vary between the 3 themes, but must be internally consistent across each theme's 3 stylings): site nav, primary tabs (in-page), option/filter pills, buttons, selects, badges, stat cards, card headers, and data tables (including a wide table that scrolls, and rank/tier colour-coding for the Striking theme), plus a Plotly chart frame.

Hard constraints (detailed in the brief): express everything as **CSS custom properties using the token names in `BRIEF_v2.md`** (propose new token names only where genuinely needed, and call those out); support **light and dark mode** via `html[data-mode="dark"]` overrides, designed intentionally per styling rather than inverted; **preserve the desktop information density** shown in the screenshots while making mobile feel app-like; use Google Fonts.

Start by proposing the three themes at a high level — a mini moodboard + token set for each, explicitly naming what makes them different from each other and from round 1 — before rendering all 9 full-page variants. Ask me anything ambiguous before going wide.
