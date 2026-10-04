---
name: teg-simulation
description: Run the site's Predictatron simulator from a dev session. Use for next-TEG forecasts, "why is X favourite", handicap what-ifs, form what-ifs (ignore/reweight a TEG), handicap-change impact (Shapley) and equalising handicaps. Do not rebuild these by hand.
---

# TEG simulation (dev sessions)

`sim.py` is the same script TEGBot's sandbox uses. It wraps `teg_analysis/analysis/simulation.py`, the engine behind `/simulation`. One implementation serves the bot, the site and dev sessions. Never re-derive Shapley splits, form what-ifs or equalising handicaps.

## Run it

From the repo root (or any worktree root). No setup: the script finds `teg_analysis/` and `data/` from its own location, or from `$TEG_ROOT` if set.

```
S=teg_analysis/chatbot/toolkit/skills/teg-simulation/scripts/sim.py
python $S baseline --json
python $S whatif --json --handicap GW=18
python $S whatif --json --exclude-tegs 18
python $S handicap-impact --json
python $S equalising --json
```

Python: `sys.path.insert(0, "teg_analysis/chatbot/toolkit/skills/teg-simulation/scripts"); import sim; sim.whatif(handicaps={"GW": 18})`.

## Rules

- Defaults match the site and the bot's `get_predictions`: seed 1, 10,000 sims, next TEG roster, saved handicaps. `baseline` equals `get_predictions`. The live `/simulation` page uses a fresh seed, so it differs by a point or two.
- Quote the script's numbers. Treat gaps under about 1 pp as noise (see `TrophySEpp`).
- Method, options, reading the output, caveats and recipes: `teg_analysis/chatbot/toolkit/skills/teg-simulation/SKILL.md`. Read it rather than guessing flags.
- Ignore its "/tmp/teg" setup lines. They only apply inside the bot's sandbox.

## Data

Reads the local `data/` checkout (the Railway volume is the production copy; sync via the normal GitHub flow). Read-only: never write data from these scripts.
