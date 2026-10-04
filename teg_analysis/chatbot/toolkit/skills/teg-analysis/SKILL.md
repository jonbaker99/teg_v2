---
name: teg-analysis
description: Rigorous ad-hoc analysis of TEG scores with tested helpers (site definitions, tie-aware ranks, own-baseline comparisons, bootstrap CIs, handicap re-scoring). Use for any question that needs your own pandas work on hole, round or TEG data.
---

# TEG analysis

Use this for questions the site's lookups do not answer directly. The helpers encode the site's definitions so you do not reinvent them. Read `reference/rules.md` first if you are unsure about competitions, eras, handicaps or score names.

Setup (once per container) is in the system prompt. Then:

```python
import sys; sys.path.insert(0, "/tmp/teg/skills/teg-analysis/scripts")
import tegstats as ts
f = ts.load_frames()          # f.holes, f.rounds, f.tegs, f.winners, f.complete
ts.describe_data(f)           # frames, columns, TEGs, players
```

Do not do arithmetic in your head. Compute everything in code and quote the output.

## Helpers

- `load_precomputed(name)`: one of the site's calculated tables (streaks, bestball, commentary_*). Call with no name to list them.
- `net_measure(teg)` / `net_score(df)`: net competition value by era (NetVP up to TEG 7, Stableford from TEG 8).
- `rank_min(df, value, by, ascending)` and `top_n(df, value, n, ascending, by)`: tie-aware ranks; `top_n` keeps every row tied inside the top n.
- `vs_own_baseline(df, metric, situation_mask)`: each player's metric in a situation vs their own other rows, with n and bootstrap CI, plus an `ALL` row. Use for "does X happen on / after / when ...".
- `bootstrap_ci(x)`, `bootstrap_diff_ci(a, b)`, `small_sample(n)`: uncertainty. Output has `small_n` when n < 30.
- `rescore(holes, handicaps={...}, delta={...}, teg=None)`: counterfactual Stableford/net under other handicaps with the site's stroke allocation. Then `build_rounds(h)` / `build_tegs(h, f.complete)` give totals and positions.

## Playbook

0. Check whether a precomputed table already answers it (`reference/precomputed.md`). Prefer it over recomputing: it is what the site shows. Recompute only when no table fits, and cross-check one value against the table when you do.
1. Restate the question in one line. Name the unit (hole, round, TEG, player) and the period.
2. Choose and name definitions: gross or net, which TEGs, in-progress TEGs in or out, ties. Use the site's (rules.md) unless asked otherwise. If the question is ambiguous in a way that changes the answer, say which reading you took.
3. Sanity-check against a known site figure before the real analysis: a TEG's winner, total holes, a record. If it does not match, fix the definition first.
4. Compute. Compare a player with themselves, not with the field, when "who is better" would confound the answer.
5. Test robustness: an alternative definition, drop outliers, drop one TEG at a time. State whether the answer holds.
6. Report effect size with n and uncertainty (CI). Say when n is small. Do not call a difference real when the CI spans zero.
7. Separate correlation from cause. Say what the data cannot tell: no weather, no shot detail, no intent, few TEGs per player.

## Pitfalls

- Mixed eras: compare net across TEG 7/8 only by position or by gross.
- TEG 2 had 3 rounds. Use per-round averages when it matters.
- Exclude in-progress TEGs from finishing-position and winner questions.
- Holes are numbered in playing order within a round. "Hole 1" is the first hole, not a fixed course hole.
- Many comparisons find something by chance. Say how many you looked at.
