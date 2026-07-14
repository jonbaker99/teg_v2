# Pre-Mono design backup

Pristine copies of the theme CSS as they were **before** the Mono theme was
introduced (2026-07-13). This is the full "current design" the site shipped with
(`clean-page` theme, light + dark).

## Files here
- `base-vars.css`, `clean.css`, `clean-page.css`, `clean-layered.css`, `dark.css`

These are byte-identical snapshots of the live files at backup time.

## How the current design is still live

Adding Mono did **not** remove the old design. The old design is still the
`clean-page` theme, selectable via the `theme` cookie. Mono was added as a new
theme and made the default.

## Reverting to the pre-Mono design

**Quick revert (per browser):** set the `theme` cookie to `clean-page`
(and the design is back for that browser).

**Full revert (whole site) — three small edits:**
1. `webapp/theme.py` → `DEFAULT_THEME = "clean-page"` (was `"mono"`).
2. `webapp/theme.py` → remove the `("mono", "Mono")` entry from `THEMES` and the
   `"mono"` entry from `PLOTLY_THEMES` (optional — harmless if left).
3. Nothing else is required: `webapp/templates/base.html`'s `data-theme`
   attribute and `dark.css`'s `:not([data-theme="mono"])` guards are inert for
   `clean-page` and can be left in place.

If you want to remove Mono entirely, also delete
`webapp/static/themes/mono.css`.

To restore a specific file to its exact pre-Mono state, copy it back from this
folder over the live one in `webapp/static/themes/`.
