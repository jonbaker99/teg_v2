---
name: teg-analysis
description: Ad-hoc TEG score analysis in a dev session using the site's tested helpers (tegstats). Use for questions needing your own pandas work on hole, round or TEG data: tie-aware ranks, own-baseline comparisons, bootstrap CIs, handicap re-scoring, precomputed tables.
---

# TEG analysis (dev sessions)

`tegstats.py` is the same helper module TEGBot's sandbox uses. It encodes the site's definitions (net by era, tie-aware ranks, Stableford re-scoring). Use it instead of re-deriving them, so numbers match the site.

## Run it

From the repo root (or any worktree root). No setup: it finds `teg_analysis/` and `data/` from its own location, or from `$TEG_ROOT`.

```python
import sys; sys.path.insert(0, "teg_analysis/chatbot/toolkit/skills/teg-analysis/scripts")
import tegstats as ts
f = ts.load_frames()      # f.holes, f.rounds, f.tegs, f.winners, f.complete
ts.describe_data(f)
```

For forecasts, what-ifs and handicap attribution use the `teg-simulation` skill instead.

## Rules

- Compute in code and quote output. Sanity-check one known site figure before real analysis.
- Helper list, playbook and pitfalls: `teg_analysis/chatbot/toolkit/skills/teg-analysis/SKILL.md`.
- Definitions: `teg_analysis/chatbot/toolkit/skills/teg-analysis/reference/rules.md`. Check `reference/precomputed.md` in the same folder for a table that already answers it.
- Ignore its "/tmp/teg" setup lines. They only apply inside the bot's sandbox.
- New reusable analysis belongs in `teg_analysis/`, not in a one-off script.

## Data

Reads the local `data/` checkout, not the Railway volume. Read-only: never write data from these helpers.
