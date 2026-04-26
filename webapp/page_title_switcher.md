# Page Title and Card Header Switcher

Two cookie-based style switchers in the nav bar allow testing of visual variants without changing code. Styles are applied via body classes.

## Page Title Switcher

Body class: `body.ts-{id}`. CSS defined in `base-vars.css`. Default: **F5**.

### Active styles

| ID | Description |
|---|---|
| A | — |
| B | — |
| C | — |
| E | Underline below title |
| E2 | Underline on page/panel (see below) |
| C1 | — |
| C3 | — |
| F1 | Card-top band |
| F3 | Card-top band |
| F4 | Card-top band |
| F5 | Green band, title left, category right (default) |

### Archived styles (CSS kept, removed from dropdown)

| ID | Description |
|---|---|
| D | Left green border rule |
| C2 | White band with green text |
| F2 | White band card-top with green text |

### E2 — Underline on page

Like E (underline below title) but positioned on the page/panel rather than above it.

- **Clean Layered**: title area blends into panel — `.page-container` gets shadow/bg; `.page-title-outer` is transparent
- **Clean Page**: `.page-title-outer` gets white bg; shadow moves to `.page-container`
- Implemented via `body.ts-e2` rules in `clean-layered.css` and `clean-page.css`

## Page Container Architecture

`base.html` wraps `.page-title-outer` and `.page-panel` in a `.page-container`:

```html
<div class="page-container">
    <div class="page-title-outer">...</div>
    <div class="page-panel">...</div>
</div>
```

In `clean-layered.css`:
- `.page-container` handles width constraints (max-width, min-width, centering, margin)
- **A–E styles**: `.page-panel` has its own bg/shadow/radius; container is transparent
- **F/E2 styles**: `.page-container` gets bg/shadow/radius; `.page-panel` is transparent

This ensures the title bar and panel always share the same width — fixes desync on wide content pages.

## Card Header Switcher

Body class: `body.ch-{id}`. CH0–CH3 implemented. Default: **CH1**.

| ID | Description |
|---|---|
| CH0 | Off (hidden) |
| CH1 | Grey bar, mono caps — sits on top of data card (default) |
| CH2 | Mono label above card, on panel surface |
| CH3 | Lora serif above card, editorial feel |
| CH4 | Not yet designed |

### Theme behaviour

- **Clean Layered**: CH1 grey bar and CH3 serif render as designed
- **Clean Page**: CH1/CH3 fall back to CH2 label style (no cards to attach to)
- Cascade fix: `clean-layered.css` re-asserts CH1/CH3 rules after importing `clean-page.css`

### Relevant files

| File | Purpose |
|---|---|
| `webapp/theme.py` | `CARD_HEADER_STYLES`, `get_card_header_style()` |
| `webapp/app.py` | Middleware injection of body class |
| `webapp/templates/base.html` | Body class + dropdown UI |
| `webapp/static/themes/base-vars.css` | CH0–CH3 CSS rules |
| `webapp/static/themes/clean-layered.css` | CH1/CH3 restore rules |
| `webapp/static/themes/clean-page.css` | CH1/CH3 fallback to CH2 |
