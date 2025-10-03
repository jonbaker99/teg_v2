# Data Dictionary Structure for Golf Reporter Instructions

Here's an optimized format organized by domain and usage hierarchy:

---

## **DATA DICTIONARY**

### **Format Guide**
- **Field Name** | *Type* | Source File(s)
  - Description and usage notes

---

## **A. CORE IDENTIFIERS** (Present across multiple files)

**TEG** | *String* | All files
- Tournament identifier (e.g., "TEG 17")
- Use to confirm which tournament you're analyzing

**TEGNum** | *Integer* | All files
- Numeric tournament sequence (17 = 17th tournament in history)
- Use for historical context and ranking comparisons

**Player** | *String* | All files
- Full player name
- Primary identifier for narrative subjects

**Pl** | *String* | All files
- Player initials
- Not to be used in article

**Round** | *Integer* | round_summary, round_events, round_streaks
- Round number (1-4 for typical tournament)
- Use to track tournament progression

**Hole** | *Integer* | round_events
- Hole number (1-18)
- Use for specific dramatic moments and location references
- Holes 1-9 are collectively the 'Front 9', 10-18 are collectively the 'Back 9'

**Year** | *Integer* | tournament_summary, round_summary
- Calendar year of tournament
- Use for temporal context

---

## **B. TOURNAMENT-LEVEL METRICS** (tournament_summary.csv)

### **B1. Final Outcomes & Rankings**

**Tournament_Score_Sc** | *Float* | tournament_summary
- Player's gross score *NOT* relative to par for entire tournament (e.g., 80)
- **Critical:** Use this for overall tournament performance comparisons
- For context: <81 is excellent; <85 is good; <90 is ok; <100 is mediocre; >100 is bad; >110 is terrible; use that as guidance

**Tournament_Score_Gross** | *Float* | tournament_summary
- Total gross score vs. par
- Refer to as "+12" / "12 over" / "12 over par"
- Use for Green Jacket (Gross) competition totals

**Tournament_Score_Stableford** | *Float* | tournament_summary
- Total Stableford points earned across all rounds
- Use for TEG Trophy (Stableford) competition totals

**Final_Rank_Gross** | *Integer* | tournament_summary
- Player's finishing position in Gross competition (1 = winner)
- Use to identify Green Jacket winner and final standings

**Final_Rank_Stableford** | *Integer* | tournament_summary
- Player's finishing position in Stableford competition (1 = winner)
- Use to identify TEG Trophy winner and final standings

**Final_Gap_Gross** | *Float* | tournament_summary
- Strokes behind leader at tournament end (0 for winner)
- Use to describe margins of victory/defeat in Gross

**Final_Gap_Stableford** | *Float* | tournament_summary
- Stableford points behind leader at tournament end (0 for winner)
- Use to describe margins of victory/defeat in Stableford

**Won_Gross** | *Boolean* | tournament_summary
- TRUE if player won Green Jacket
- Quick winner identification

**Won_Stableford** | *Boolean* | tournament_summary
- TRUE if player won TEG Trophy
- Quick winner identification

**Wooden_Spoon** | *Boolean* | tournament_summary
- TRUE if player finished last in Stableford
- Use to identify and narrate Wooden Spoon recipient

**Margin_Gross** | *Float* | tournament_summary
- Winner's margin of victory in strokes (Gross)
- Use to describe dominance/closeness of Gross competition

**Margin_Stableford** | *Float* | tournament_summary
- Winner's margin of victory in points (Stableford)
- Use to describe dominance/closeness of Stableford competition

### **B2. Round Performance Statistics**

**Best_Round_Gross** | *Float* | tournament_summary
- Player's best single-round stroke total in the tournament
- Use for highlighting peak performances

**Worst_Round_Gross** | *Float* | tournament_summary
- Player's worst single-round stroke total in the tournament
- Use for contrasting struggles or discussing consistency

**Range_Round_Gross** | *Float* | tournament_summary
- Difference between best and worst rounds (strokes)
- Use to discuss consistency vs. volatility

**StdDev_Round_Gross** | *Float* | tournament_summary
- Standard deviation of round scores (strokes)
- Use to quantify consistency (lower = more consistent)

**Best_Round_Stableford** | *Float* | tournament_summary
- Player's best single-round Stableford points total in the tournament
- Use for highlighting peak performances

**Worst_Round_Stableford** | *Float* | tournament_summary
- Player's worst single-round Stableford points total in the tournament
- Use for contrasting struggles

**Range_Round_Stableford** | *Float* | tournament_summary
- Difference between best and worst rounds (Stableford points)
- Use to discuss consistency

**StdDev_Round_Stableford** | *Float* | tournament_summary
- Standard deviation of round scores (Stableford)
- Use to quantify consistency

**StdDev_Hole_Gross** | *Float* | tournament_summary
- Standard deviation of hole-by-hole scores
- Use to describe shot-to-shot consistency across entire tournament

**StdDev_Hole_Stableford** | *Float* | tournament_summary
- Standard deviation of hole-by-hole Stableford points
- Use to describe scoring consistency at granular level

### **B3. Leadership & Position Tracking**

**Total_Holes_In_Lead_Gross** | *Integer* | tournament_summary
- Total holes spent in outright lead (Gross)
- Use to describe dominance and control of tournament
- A very high number (>60) is particularly notable

**Total_Holes_In_Lead_Stableford** | *Integer* | tournament_summary
- Total holes spent in outright lead (Stableford)
- Use to describe dominance and control of tournament
- A very high number (>60) is particularly notable

**Rounds_Leading_After_Gross** | *Integer* | tournament_summary
- Number of rounds where player led after round ended (Gross)
- Use to identify wire-to-wire performances or late surges

**Rounds_Leading_After_Stableford** | *Integer* | tournament_summary
- Number of rounds where player led after round ended (Stableford)
- Use to identify wire-to-wire performances or late surges

**Total_Lead_Gained_Gross** | *Integer* | tournament_summary
- Count of times player took the lead (Gross)
- Use to describe back-and-forth battles

**Total_Lead_Lost_Gross** | *Integer* | tournament_summary
- Count of times player lost the lead (Gross)
- Use to describe volatility and momentum shifts

**Total_Lead_Gained_Stableford** | *Integer* | tournament_summary
- Count of times player took the lead (Stableford)
- Use to describe battles for position

**Total_Lead_Lost_Stableford** | *Integer* | tournament_summary
- Count of times player lost the lead (Stableford)
- Use to describe position changes

### **B4. Scoring Events (Tournament Totals)**

**Total_Eagles** | *Integer* | tournament_summary
- Eagles across entire tournament
- Use for spectacular shot narratives
- Note an Eagle is very rare and should always be highlighted

**Total_Birdies** | *Integer* | tournament_summary
- Birdies across entire tournament
- Use to describe scoring prowess

**Total_Pars** | *Integer* | tournament_summary
- Pars across entire tournament
- Use to describe steady play

**Total_Bogeys** | *Integer* | tournament_summary
- Bogeys across entire tournament
- Use to describe struggles

**Total_Double_Bogeys** | *Integer* | tournament_summary
- Double bogeys across entire tournament
- Use to highlight trouble spots

**Total_Worse_Than_Double** | *Integer* | tournament_summary
- Scores worse than double bogey
- Use for disaster hole narratives

**Holes_In_One** | *Integer* | tournament_summary
- Aces during tournament
- Major dramatic moment if > 0

**Total_Stableford_5s** | *Integer* | tournament_summary
- Holes where player earned 5+ Stableford points (eagles or better)
- Use to highlight exceptional holes in Stableford context

**Total_Stableford_0s** | *Integer* | tournament_summary
- Holes where player earned 0 Stableford points (double bogey or worse)
- Use to highlight disaster holes in Stableford context

### **B5. Historical Context Rankings**

**Rank_Among_Player_TEGs_Gross** | *Integer* | tournament_summary
- Where this tournament ranks in player's personal history (Gross)
- Example: "3 of 10" = player's 3rd best performance ever, out of 10 rounds (Gross)
- **Use judiciously:** Only mention if high/low (career best/worst)

**Rank_Among_Player_TEGs_Stableford** | *Integer* | tournament_summary
- Where this tournament ranks in player's personal history (Stableford)
- **Use judiciously:** Only mention if exceptionally high/low

**Rank_Among_All_TEGs_To_Date_Gross** | *Integer* | tournament_summary
- Where this tournament ranks among ALL tournaments to date (Gross)
- **Use judiciously:** Only for truly historic performances

**Rank_Among_All_TEGs_To_Date_Stableford** | *Integer* | tournament_summary
- Where this tournament ranks among ALL tournaments to date (Stableford)
- **Use judiciously:** Only for truly historic performances

---

## **C. ROUND-LEVEL METRICS** (round_summary.csv)

### **C1. Round Identifiers & Context**

**Date** | *String* | round_summary
- Date round was played
- Use for temporal storytelling

**Course** | *String* | round_summary
- Course name
- Use for setting and context

**Area** | *String* | round_summary
- Geographic area/region
- Use for location context

**index** | *Integer* | round_summary
- Internal row index
- Ignore

### **C2. Round Scoring (All Formats)**

**Round_Score_Sc** | *Float* | round_summary
- Round gross score *NOT* relative to par (e.g., 80)
- Primary metric for round performance

**Round_Score_Gross** | *Float* | round_summary
- Total gross score relative to par (e.g. +12)
- Use for Gross competition round analysis

**Round_Score_Stableford** | *Float* | round_summary
- Total Stableford points for the round
- Use for Stableford competition round analysis

### **C3. Nine-Hole Splits**

**Front_9_Score_Sc** | *Float* | round_summary
- Score for front nine (not vs par)
- Use to describe first-half performance

**Back_9_Score_Sc** | *Float* | round_summary
- Score for back nine  (not vs par)
- Use to describe second-half performance

**Front_9_vs_Back_9_Sc** | *Float* | round_summary
- Difference between front and back nine (Sc)
- Use to highlight momentum shifts within round

**Front_9_Score_Gross** | *Float* | round_summary
- Gross score vs par on front nine
- Use for Gross round split analysis

**Back_9_Score_Gross** | *Float* | round_summary
- Gross score vs par on back nine
- Use for Gross round split analysis

**Front_9_vs_Back_9_Gross** | *Float* | round_summary
- Difference between front and back nine (Gross)
- Use to highlight split performance

**Front_9_Score_Stableford** | *Float* | round_summary
- Stableford points on front nine
- Use for Stableford round split analysis

**Back_9_Score_Stableford** | *Float* | round_summary
- Stableford points on back nine
- Use for Stableford round split analysis

**Front_9_vs_Back_9_Stableford** | *Float* | round_summary
- Difference between front and back nine (Stableford)
- Use to highlight split performance

### **C4. Cumulative Tournament Position**

**Cumulative_Tournament_Score_Gross** | *Float* | round_summary
- Running total strokes after this round
- Track tournament trajectory (Gross)

**Cumulative_Tournament_Score_Stableford** | *Float* | round_summary
- Running total Stableford points after this round
- Track tournament trajectory (Stableford)

**Cumulative_Tournament_Rank_Before_Round_Gross** | *Float* | round_summary
- Player's rank before round started (Gross)
- Track position changes

**Cumulative_Tournament_Rank_Gross** | *Float* | round_summary
- Player's rank after round completed (Gross)
- Identify rises/falls

**Cumulative_Tournament_Rank_Before_Round_Stableford** | *Float* | round_summary
- Player's rank before round started (Stableford)
- Track position changes

**Cumulative_Tournament_Rank_Stableford** | *Float* | round_summary
- Player's rank after round completed (Stableford)
- Identify rises/falls

### **C5. Round Performance Rankings**

**Player_Round_Rank_Gross** | *Float* | round_summary
- Player's rank for this specific round (Gross)
- Identify round winners and struggles

**Player_Round_Rank_Stableford** | *Float* | round_summary
- Player's rank for this specific round (Stableford)
- Identify round winners and struggles

### **C6. Gap to Leader Tracking**

**Gap_To_Leader_Before_Round_Gross** | *Float* | round_summary
- Strokes behind leader at round start (Gross)
- Track comeback/collapse potential

**Gap_To_Leader_After_Round_Gross** | *Float* | round_summary
- Strokes behind leader at round end (Gross)
- Measure ground gained/lost

**Gap_To_Leader_Before_Round_Stableford** | *Float* | round_summary
- Points behind leader at round start (Stableford)
- Track comeback/collapse potential

**Gap_To_Leader_After_Round_Stableford** | *Float* | round_summary
- Points behind leader at round end (Stableford)
- Measure ground gained/lost

### **C7. Leadership During Round**

**Holes_In_Lead_Gross** | *Integer* | round_summary
- Holes spent in lead during this round (Gross)
- Describe in-round dominance

**Leading_At_Start_Of_Round_Gross** | *Integer* | round_summary
- Binary: 1 if leading at start, 0 if not (Gross)
- Identify defending leaders

**Leading_At_End_Of_Round_Gross** | *Integer* | round_summary
- Binary: 1 if leading at end, 0 if not (Gross)
- Identify who claimed/held lead

**Lead_Gained_Count_Gross** | *Integer* | round_summary
- Times player took lead during this round (Gross)
- Describe in-round momentum

**Lead_Lost_Count_Gross** | *Integer* | round_summary
- Times player lost lead during this round (Gross)
- Describe in-round volatility

**Holes_In_Lead_Stableford** | *Integer* | round_summary
- Holes spent in lead during this round (Stableford)
- Describe in-round dominance

**Leading_At_Start_Of_Round_Stableford** | *Integer* | round_summary
- Binary: 1 if leading at start, 0 if not (Stableford)
- Identify defending leaders

**Leading_At_End_Of_Round_Stableford** | *Integer* | round_summary
- Binary: 1 if leading at end, 0 if not (Stableford)
- Identify who claimed/held lead

**Lead_Gained_Count_Stableford** | *Integer* | round_summary
- Times player took lead during this round (Stableford)
- Describe momentum

**Lead_Lost_Count_Stableford** | *Integer* | round_summary
- Times player lost lead during this round (Stableford)
- Describe volatility

### **C8. Historical Round Rankings**

**Round_Rank_In_Player_History_Gross** | *String* | round_summary
- Where this round ranks in player's career (Gross)
- **Use selectively:** Only for career bests/worsts

**Round_Rank_In_Player_History_Stableford** | *String* | round_summary
- Where this round ranks in player's career (Stableford)
- **Use selectively:** Only for career bests/worsts

**Round_Rank_In_All_History_Gross** | *String* | round_summary
- Where this round ranks among all rounds ever (Gross)
- **Use rarely:** Only for truly exceptional rounds

**Round_Rank_In_All_History_Stableford** | *String* | round_summary
- Where this round ranks among all rounds ever (Stableford)
- **Use rarely:** Only for truly exceptional rounds

### **C9. Round Scoring Events**

**Eagles_Count** | *Integer* | round_summary
- Eagles in this round
- Highlight exceptional holes

**Birdies_Count** | *Integer* | round_summary
- Birdies in this round
- Describe scoring surge

**Pars_Or_Better_Count** | *Integer* | round_summary
- Holes at par or better
- Describe solid play

**Triple_Bogeys_Or_Worse_Count** | *Integer* | round_summary
- Disaster holes in round
- Highlight struggles

**Zero_Stableford_Points_Count** | *Integer* | round_summary
- Holes earning 0 Stableford points (double+ bogey)
- Stableford-specific struggles

**Four_Plus_Stableford_Points_Count** | *Integer* | round_summary
- Holes earning 4+ Stableford points (birdie+)
- Stableford-specific excellence

**Five_Plus_Stableford_Points_Count** | *Integer* | round_summary
- Holes earning 5+ Stableford points (eagle+)
- Exceptional Stableford holes

### **C10. Historical Round Context**

**Total_Player_Rounds_To_Date** | *Integer* | round_summary
- Career rounds played by this player up to this point
- Use for milestone references

**Total_Rounds_To_Date** | *Integer* | round_summary
- Total rounds in tournament history up to this point
- Use for all-time context

---

## **D. EVENT-LEVEL METRICS** (round_events.csv)

### **D1. Hole Details**

**Par** | *Integer* | round_events
- Par for the hole
- Use to describe hole difficulty and context

**Sc** | *Float* | round_events
- Score for this hole (e.g. 4), not vs par
- Generally use GrossVP instead

**GrossVP** | *Float* | round_events
- Gross score relative to par (alternative measure)
- Primary metric for hole-by-hole drama


**Stableford** | *Float* | round_events
- Stableford points earned on this hole
- Use for Stableford-specific narratives

**Final_Hole_Flag** | *Boolean* | round_events
- TRUE if this was the final hole of the round
- Use to identify climactic moments

### **D2. Event Identification**

**Event** | *String* | round_events
- Type of notable event that occurred
- **CRITICAL FIELD:** This identifies what happened (e.g., "Eagle", "Lead_Change", "Collapse")
- Use to source dramatic moments and storylines

**Metric** | *Float* | round_events
- Numerical value associated with the event
- Context-dependent based on Event type

### **D3. Rank Changes**

**Rank_Gross_Before** | *Float* | round_events
- Player's rank before this hole (Gross)
- Track intra-round position changes

**Rank_Gross_After** | *Float* | round_events
- Player's rank after this hole (Gross)
- Identify key position swings

**Rank_Stableford_Before** | *Float* | round_events
- Player's rank before this hole (Stableford)
- Track intra-round position changes

**Rank_Stableford_After** | *Float* | round_events
- Player's rank after this hole (Stableford)
- Identify key position swings

---

## **E. STREAK METRICS** (tournament_streaks.csv & round_streaks.csv)

**Streak_Type** | *String* | tournament_streaks, round_streaks
- Type of streak (e.g., "Consecutive_Birdies", "Pars_Or_Better", "Bogey_Free")
- Use to identify momentum sequences

**Max_Streak** | *Integer* | tournament_streaks, round_streaks
- Length of the streak (number of consecutive holes)
- Use to quantify sustained excellence/struggles

**Location** | *String* | tournament_streaks, round_streaks
- Hole range where streak occurred (e.g., "Holes 5-9")
- Use to specify when momentum occurred

---

## **USAGE HIERARCHY FOR NARRATIVE CONSTRUCTION**

1. **Start with Tournament Summary** → Identify winners, margins, main storylines
2. **Move to Round Summaries** → Build round-by-round progression and momentum
3. **Reference Events** → Source specific dramatic moments (eagles, lead changes)
4. **Incorporate Streaks** → Add momentum sequences for texture
5. **Cross-reference constantly** → Verify every number against source data

---

## **CRITICAL TERMINOLOGY REMINDERS**

- **Gross scores:** Always specify "strokes" for aggregates and make clear if absolute (e.g., "67 strokes") vs. relative to par (e.g., "+5 for the round")
- **Stableford:** Always specify "points" (e.g., "34 points")
- **Rankings:** Use ordinal clarity (1st, 2nd, T-3rd)
- **Margins:** Distinguish between stroke margins (Gross) and point margins (Stableford)

---

**This data dictionary structure prioritizes narrative workflow while ensuring complete data coverage and accuracy.**