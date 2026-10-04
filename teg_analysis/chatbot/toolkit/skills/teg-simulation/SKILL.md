---
name: teg-simulation
description: Run the site's Predictatron Monte Carlo engine for the next TEG. Use for forecasts, odds, "why is X favourite", "what if X's handicap were Y / last TEG was ignored", handicap-change impact and equalising handicaps.
---

# TEG simulation (Predictatron)

The next TEG is simulated 10,000 times from each player's recent hole-by-hole form, on that TEG's courses and handicaps. This is the same engine as the site's /simulation page. Never reimplement it or do the arithmetic yourself. Run the script and report its numbers.

For a plain "who will win" or "what are the odds" question, use the `get_predictions` lookup instead. It gives the same numbers as `baseline`. Use this skill for why, what-if and attribution questions.

Setup (once per container) is in the system prompt. Then:

```
python /tmp/teg/skills/teg-simulation/scripts/sim.py <command> --json [options]
```

Defaults: seed 1, 10,000 sims (the same as `get_predictions`, so `baseline` matches it exactly), the next TEG's roster, saved (or draft) handicaps. The same command always returns the same numbers. The site page uses a fresh seed, so its figures can differ by a point or two.

## Commands

- `baseline`: the site's default run. Per player: Trophy %, Jacket %, Spoon %, mean Stableford, mean gross vs par, expected finish, and the full finishing-position table.
- `whatif`: a changed run next to the baseline, same roster/seed/sims. Reports the change in Trophy %, Jacket % and mean Stableford.
- `handicap-impact`: how the handicap changes since the previous TEG moved each player's Trophy chance, split fairly between the movers (Shapley).
- `equalising`: the handicap that would give each player about 36 Stableford points a round.

`whatif`, `handicap-impact` and `equalising` take these options:

- `--handicap GW=18` (repeatable): override a handicap. Player = code or name.
- `--exclude-tegs 18,17`: drop TEGs from form history. Recency weights then fall to the next most recent TEGs.
- `--only-tegs 16,17,18`: use only these TEGs.
- `--weights 50,35,15`: recency weights, newest TEG first. Default 50,35,15; older TEGs get 0.
- `--teg-weights 18:0,17:50`: explicit weight per TEG; the rest keep their default.
- `--method window|bands`, `--min-holes`, `--shrinkage` (bands only), `--field-alpha`: model settings. Leave at defaults unless asked.
- Common to all: `--target TEG`, `--players A,B,C`, `--n-sims`, `--seed`.

Python use: `sys.path.insert(0, "/tmp/teg/skills/teg-simulation/scripts"); import sim; sim.whatif(handicaps={"GW": 18})`. It returns the same dict as `--json`.

Errors print a one-line message (for example, an unknown player lists the valid ones). Fix the input and rerun.

## Reading the numbers

- Trophy % = share of sims where the player had the most Stableford points. Jacket % = lowest gross. Spoon % = fewest Stableford points. Each column sums to 100.
- `TrophySEpp` = Monte Carlo standard error in percentage points (about 0.5 near 50% at 10k sims). Differences smaller than about 1 pp between players, or between runs, are noise. Raise `--n-sims` (max 100,000) to tighten.
- Delta columns are scenario minus baseline, in percentage points, on paired random draws. They are steadier than the levels, but still only trust deltas above about 0.5 pp.
- `MeanGrossVP` is the expected gross total relative to par for the whole TEG.

## Method and caveats

- Each hole score is drawn from the player's own history for that par and stroke index, weighted by recency (default: last TEG 50, one before 35, one before that 15). Rare outcomes (eagles, blobs) are blended in from the whole field. This models form, not luck of the day or injuries.
- Handicaps only change the strokes received. A handicap change moves Stableford totals, not gross. So Jacket % does not move with handicap overrides.
- Effects are not additive. Changing two handicaps is not the sum of changing each. Use `handicap-impact` for attribution.
- If the TEG has no scorecard yet, each sim draws random par-72 courses. The notes in the output say so. Handicaps may be a draft calculation.
- Trophy = Stableford applies from TEG 8. All upcoming TEGs are in that era.
- This predicts a future TEG. It cannot re-run a past TEG's actual result.

## Recipes

- Why is X the favourite? Run `baseline`. Then `whatif --exclude-tegs <latest>` and `whatif --handicap X=<hc+3>` to see which input carries the lead. Quote both deltas.
- What if X's handicap were Y? `whatif --handicap X=Y`. Report X's and the field's Trophy % before and after.
- How much does last TEG matter? `whatif --teg-weights <last>:0` (or `--exclude-tegs <last>`) and compare. Also try `--weights 100,0,0` for "only last TEG".
- Who gained most from the handicap changes? `handicap-impact`. Use the `from_<code>_PP` columns for who caused what.
- Are the handicaps fair? `equalising`: compare CurrentHC and EqualisingHC, and Unrounded for size.
- Is a gap real? Look at `TrophySEpp`, or rerun with `--n-sims 100000` or another `--seed`.
