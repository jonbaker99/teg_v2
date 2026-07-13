# Kickoff prompt for claude.ai/design

Paste the text below into Claude Design. Attach: `BRIEF.md`, the three HTML files in `pages/`, and the screenshots in `pages/screenshots/` (at least the `*-light`, `*-dark`, and `*-card-light` images).

---

I'm refining the visual design of a data-dense web app — a private golf-tournament analysis site (an annual event called "the TEG"). It shows leaderboards, scorecards, player rankings, statistical tables and charts. The audience is small and knowledgeable; the feel should be clean, editorial and professional — an "almanac / record book", not a flashy sports app.

I've attached: (1) a design brief (`BRIEF.md`) with the current design-token system and component inventory, (2) rendered HTML of three representative pages (Contents, Results, Player profile) with real data, and (3) screenshots of those pages in the current light and dark themes, plus a "card" layout variant. **Read the brief first** — it lists hard constraints and the exact CSS token names I need you to reuse.

Please design **two base directions**, each as a complete, consistent visual language:

1. **Refined Clean Page** — a more polished, professional evolution of the current look: a single white content surface on a warm neutral page, editorial serif headings + monospace data, one confident accent colour.
2. **Card** — every distinct piece of content (a table, a chart, a stat group) sits in its own card artifact on a quiet panel background, with clear elevation and rhythm.

For each direction, show **2–3 colour/font variants** rendered on the same Results and Player pages so I can compare.

Then design a **unified component system** used across both directions and show it as a component sheet: primary tabs (underline style), segmented/secondary buttons, rounded **option/filter pills**, dropdown selects, buttons, badges, stat cards, card headers, and data tables (including a wide table that scrolls and a Plotly chart framed inside a card).

Hard constraints: express everything as **CSS custom properties using the token names in the brief** (restyle the values, keep the names); support **light and dark mode** via `html[data-mode="dark"]` variable overrides; **preserve the desktop information density** shown in the screenshots (this is a refinement, not a layout teardown) while making the mobile view feel app-like; use Google Fonts; tables can be wide and charts are arbitrary embedded blocks.

Start by proposing the two directions at a high level with a mini moodboard / token set for each, then render the Results and Player pages. Ask me anything ambiguous before going wide.
