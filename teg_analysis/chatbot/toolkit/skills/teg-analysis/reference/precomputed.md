# Precomputed tables

The site has already calculated these. They are what the site shows, so prefer them over recomputing. Load one with `ts.load_precomputed("<name>")`; `ts.load_precomputed()` lists what is available.

All are built from the same hole data as `holes`. TEG 50 (test data) is excluded. In-progress TEGs are included, so drop them for finishing-position questions (see the `Complete` flag in `f.tegs`). They are rebuilt whenever data is added. "Gross" means GrossVP (vs par, lower is better). Stableford is points (higher is better).

## streaks

One row per player per hole, in career order (`Hole Order Ever`, across all TEGs).
- Keys: `Pl`, `HoleID` (like `T07|R01|H01`), `Career Count`, `Hole Order Ever`; scores `Sc`, `GrossVP`.
- Flags per hole: `eagle`, `birdie`, `par_better`, `double_bogey` (+2 or worse), `TBP` (+3 or worse).
- Running counters: `<flag>_true_streak` = current run of holes with the flag; `<flag>_false_streak` = current run without it. A streak's length is the counter's maximum before it resets to 0.
- Answers: longest runs ever (max of a counter per player), what streak a player was on at a given hole.
- Gotcha: runs continue across rounds and TEGs. Use the commentary streak tables for within-round or within-TEG maxima.

## bestball

One row per round and format: `Bestball` and `Worstball` (team total of the best / worst score on each hole across the field).
- Columns: `TEG`, `TEGNum`, `Round`, `Course`, `Year`, `GrossVP`, `Sc`, `Format`.
- Answers: best and worst bestball rounds of all time, trend by course or year.
- Gotcha: gross only (no Stableford).

## commentary_round_summary

One row per player per round (the table behind round reports).
- Keys: `TEG`, `TEGNum`, `Round`, `Date`, `Course`, `Area`, `Year`, `Player`, `Pl`.
- Scores: `Round_Score_Sc/Gross/Stableford`, plus `Front_9_...`, `Back_9_...` and `Front_9_vs_Back_9_...`.
- Standings: `Cumulative_Tournament_Score_*`, `Player_Round_Rank_*` (rank in this round), `Cumulative_Tournament_Rank_*` (after the round) and `..._Before_Round_*` (blank in round 1), `Gap_To_Leader_*` before/after.
- Lead story: `Holes_In_Lead_*`, `Leading_At_Start/End_Of_Round_*`, `Lead_Gained/Lost_Count_*`.
- History ranks: `Round_Rank_In_Player_History_*` and `Round_Rank_In_All_History_*`, as text like `"1 of 5"` (rank among rounds up to and including that one, so it changes as history grows).
- Counts: `Eagles_Count`, `Birdies_Count`, `Pars_Or_Better_Count`, `Triple_Bogeys_Or_Worse_Count`, `Zero_Stableford_Points_Count`, `Four_Plus_...`, `Five_Plus_...`.
- Answers: "who led after round 2", comeback and collapse questions, best rounds in history at the time.
- Gotcha: ranks use both competitions side by side (`_Gross`, `_Stableford`). Before TEG 8 the net competition was NetVP, which this table does not carry; use `f.rounds` for that.

## commentary_tournament_summary

One row per player per TEG.
- Keys: `TEGNum`, `TEG`, `Year`, `Player`, `Pl`.
- Result: `Tournament_Score_Sc/Gross/Stableford`, `Final_Rank_*`, `Final_Gap_*`, `Won_Gross`, `Won_Stableford`, `Wooden_Spoon`, `Margin_*`.
- Consistency: best, worst, range and std dev of round scores; std dev of hole scores.
- Lead story: `Total_Holes_In_Lead_*`, `Rounds_Leading_After_*`, `Total_Lead_Gained/Lost_*`.
- Score mix: `Total_Eagles/Birdies/Pars/Bogeys/Double_Bogeys/Worse_Than_Double`, `Holes_In_One`, `Total_Stableford_5s/0s`.
- History: `Rank_Among_Player_TEGs_*` and `Rank_Among_All_TEGs_To_Date_*`.
- Answers: margins of victory, most consistent TEG, score-mix questions, who won each competition.
- Gotchas: `Won_Stableford` is the Stableford winner in every era, not the official Trophy winner (up to TEG 7 the Trophy was NetVP; manual overrides such as the TEG 5 Green Jacket are only in `f.winners`). For official winners use `f.winners`. TEG 2 had 3 rounds, so totals are lower. Rows exist for in-progress TEGs, with partial totals.

## commentary_round_events

One row per notable hole event (about 3,000 rows).
- Keys: `TEG`, `TEGNum`, `Round`, `Hole`, `Player`, `Pl`; hole data `Par`, `Sc`, `GrossVP`, `Stableford`, `Final_Hole_Flag`.
- `Event` is one of: `Eagle`, `Birdie`, `4+ Points`, `5+ Points`, `Zero Points`, `Triple Bogey or Worse`, `Quintuple Bogey or Worse`, `Took Lead (Gross/Stableford)`, `Lost Lead (Gross/Stableford)`, `Hit Bottom (Spoon)`, `Left Bottom (Spoon)`.
- Ranks around the event: `Rank_Gross_Before/After`, `Rank_Stableford_Before/After`.
- Answers: when the lead changed hands, who last took the lead, how often a player had a blow-up hole.
- Gotcha: only events are here, not every hole. Counting absence of an event needs `holes`.

## commentary_round_streaks and commentary_tournament_streaks

One row per player per streak type, giving the longest streak in that round (or in that TEG).
- Columns: `TEG`, `TEGNum`, (`Round`,) `Player`, `Pl`, `Streak_Type`, `Max_Streak`, `Location` (start to end hole, like `T02 R2 H16 to T02 R2 H18`).
- `Streak_Type`: `Birdies`, `Eagles`, `Pars or Better`, `Over Par`, `+2s or Worse`, `TBPs`, and the "no" runs `No Birdies`, `No Eagles`, `No +2s`, `No TBPs`.
- Answers: longest streak in a given round or TEG and exactly where it happened.
- Gotcha: streaks do not run across rounds in the round table, and not across TEGs in either. For career-long runs use `streaks`.
