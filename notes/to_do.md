[ ] Round commentary + speculation as to what's to come if tournament is in progress

[ ] review the files generated for commentary, is it still useful? is it being used?



[***] UPDATE NOTES TAHT JSON NEEDS TO BE EFFICIENT / COMPACTED
[X] UPDATE STABLEFORD 'COLD' TO AVERAGE OF <0.7 pts
[X] REMOVE DEBUG FILES IN THE STORY GENERATION (PUT UNDER A SWITCH)
[X] WRITE THE PROMPTS TO MAKE BEST USE OF THE NEW STORY SUMMARIES
[ ] Test quality of output generated from storyline for 1 TEG. Use similar prompt to what we initally had?

CHANGES:
-> at end of round, summarise gross and stableford scores by player (initials)
-> at end of tournament, do same
-> on stretch averages, approximate instead of 0.00 vs par (e.g. 'under par', 'marginally higher than par', 'bogey golf', 'close to +3')

-> it's not that interesting for someone to do well in gross and not in stableford, as it's a handicapped tournament

-> marginally too much 'spell' detail
-> still not enough on sizes of leads through the round / any battles of interest

-> Baker needs to be either A or J Baker
-> leverage the 'story notes' better, either in summary or through the rounds. The round descriptions can be shorter especially if it frees up a bit of space for the storylines.

-> focus is on stableord but score is useful for contextualising

ERRORS: Why? Fix at root

- TEG 10: "- David MULLIN's 1st Trophy - won Gross by 12 strokes, led all 72 holes for Gross championship"

REVIEW PROMPT AT END AGAIN FOR CLARITY


[x] Add the Area and Course info as another layer of data to the story file

[ ] add those to the story points without LLM needed (e.g. add after). can they be programatically added?
[ ] do records and PBs need LLM too or can they be programatically added?




NOTES
-> don't talk about the differences between gross and stableford as though they're interesting
-> quoting 'disasters' too frequently, use varied language and illustrate with hole scores (e.g. "a 10 on the par 4 7th")

Add double figure gross scores?

[*] CACHE PROMPTS TO SAVE TOKENS...
[ ] Create a course description and area description dictionary as an intro

----------------

Starting Prompt for Next Conversation
Context: We're enhancing the TEG tournament commentary generation pipeline. Recently completed token optimization (direct addition of factual data) and career context enhancement (pre-tournament history). Current Task: Implement streak data integration with the INCLUDE_STREAKS toggle. What's Already Done:
✅ INCLUDE_STREAKS config toggle created in generate_tournament_commentary_v2.py:33-34 (set to True by default)
✅ Documentation updated in RECENT_CHANGES.md and IMPLEMENTATION_PLAN_FINAL.md
What Needs to Be Done (4 tasks):
Load streak data in pattern_analysis.py (Pass 8, conditional):
Load data/commentary_round_streaks.parquet if include_streaks=True
Filter to current TEG
Group by round: streaks_by_round[round_num] = round_streaks[round_streaks['Round'] == round_num].to_dict('records')
Add to return dict from process_all_data_types()
Update data_loader.py:
Add streak data to load_round_data() return dict (conditional on whether streaks exist in all_processed_data)
Filter to current round
Update prompts.py:
Add streak data documentation to ROUND_STORY_PROMPT
Document structure: Player, Streak_Type (Birdies, Eagles, +2s or Worse), Max_Streak, Location
Update generate_round_story() in generate_tournament_commentary_v2.py:
Pass INCLUDE_STREAKS flag through to process_all_data_types()
Conditionally include streak data in prompt (only if present in round_data)
Key Design Constraint:
All changes must respect the INCLUDE_STREAKS toggle - when False, pipeline should work exactly as before with zero token overhead
Reference Files:
generate_tournament_commentary_v2.py
pattern_analysis.py
data_loader.py
prompts.py
RECENT_CHANGES.md - Full context on recent work
Testing: After implementation, test with TEG 17 with INCLUDE_STREAKS=True and INCLUDE_STREAKS=False to verify toggle works correctly.


=======================

Fix formatting on teg_reports

Change the contents generation so I can target the section headers with css


======= 

Finalise the remote report functionality. COntinue with what you were working on. 


MAJOR PROBLEM FOR REPORT RELIABILITY:
Previous wins still appear to based on a calculation not on fact. This is critically important. The previous tournament winners can not be calculated just from Stableford and gross results, because we have changed the criteria for winning the competition at various points over the years.

E.g. generated story notes for TEG 6, 
Says it was Gregg Williams' 1st trophy. It was his 2nd win, as he won TEG 5 (using a different scoring system).
Says it was David Mullin's 5th Jacket when it was his 4th, as we awarded the Green Jacket on a different basis in TEG 5.

Past winners can be found in multiple places:
data/TEG_winners.csv -> a list of who won which competition at which TEG
streamlit/player_history.py -> this should be good for generating a rich history as it has finishing positions for all players for all tournaments
streamlit/101TegHonoursBoard.py -> calculates number of wins and the tournaments won

Do two things:
1) Identify why the number of previous tournaments won are not coming into the story point files correctly
2) Pass previous finishing positions from the player history page functionality to the functions that generate the story points.

WHen that's working, create a page to regenerate a report for any chosen  round or tournament remotely. The user should be able to choose between using preexisting story notes (if they do exist) or regenerating story notes too.

retrieve batches - didn't know what to do with satire
satire batch now saved in jsonl file -> use that to populate the reports


Add a segmented control to the report tab on streamlit/102TEGResults.py and the full tournament report tab on teg_reports.py to choose between 'Normal' report and '"Satire"'. Normal should be the default and load reports as they currently are from the data/commentary folder with file format teg_{n}_main_report.md. Satire should load the reports with file format teg_{n}_satire.md from the data/commentary/drafts folder.

THEN

Replicate the TEG report from streamlit/102TEGResults.py on a new tab in streamlit/latest_teg_context.py IF the tournament is complete (using the existing functionality in the codebase to check if a given tournament is complete)

---

Add choice for mobile scorecard on leaderboard scorecard tabs (same as in latest_round). Controls should go between the first set of tabs and the 2nd set of tabs
 
change subtabs on 'Scoreboards' tab to segmented controls in latest_round