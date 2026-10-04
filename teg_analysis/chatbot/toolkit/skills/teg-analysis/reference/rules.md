# TEG rules for analysis

Matches the site and the data guide the model is given with the CSV files.

## Competitions

A TEG is an annual golf tournament, usually 4 rounds of 18 holes (front 9 = holes 1-9, back 9 = 10-18). TEG 2 had 3 rounds.

- **Green Jacket (gross):** lowest total GrossVP (strokes minus par).
- **TEG Trophy (net):** up to TEG 7, lowest total NetVP. From TEG 8 (`STABLEFORD_ERA_TEG = 8`), highest total Stableford points.
- **HMM Wooden Spoon:** worst finisher in the net competition.
- Positions use `rank(method="min")`: tied players share a position, the next position is skipped.
- Official winners (`f.winners`) include manual overrides. The TEG 5 Green Jacket was awarded to Stuart NEUMANN for best Stableford round, while David MULLIN had the best gross.
- In-progress TEGs have partial totals. Exclude them from finishing-position and winner questions.

## Handicaps and strokes

- `HC` is the player's whole-number handicap for that TEG (`data/handicaps.csv`).
- Strokes received on a hole: `HC // 18 + (HC % 18 >= SI)`. A handicap of 20 gets 2 strokes on SI 1-2 and 1 on the rest. Handicaps over 36 give extra strokes on low-SI holes.
- `NetVP = GrossVP - HCStrokes`.
- Stableford points per hole: `max(0, 2 - NetVP)`. Net par = 2, net birdie = 3, net bogey = 1, net double or worse = 0.
- Handicaps are set before each TEG. A counterfactual handicap changes NetVP and Stableford, never gross.

## Score names (gross vs par)

- eagle or better: <= -2. birdie: -1. par: 0. bogey: +1. double bogey: +2.
- "+2s": double bogey or worse (>= +2). "TBP" (triple bogey or worse): >= +3.
- "Blob": a hole with 0 Stableford points.

## Data

- `holes`: Player, Pl (initials), TEGNum, Year, Area, Course, Date, Round, Hole, FrontBack, PAR, SI, HC, HCStrokes, Sc, GrossVP, NetVP, Stableford.
- `rounds`: round totals plus RoundJacketPos / RoundTrophyPos (that round alone) and JacketPosAfterRound / TrophyPosAfterRound (TEG standings after that round).
- `tegs`: TEG totals, Complete flag, final JacketPosition / TrophyPosition (blank if in progress), FieldSize.
- Players come from `data/players.csv` (Code, Name). Use full names ("David MULLIN") in answers.
- TEG 50 is test data and is excluded.
