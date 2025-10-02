# Records & Personal Bests: Hybrid Approach Implementation Plan

## Overview

Implement a comprehensive records and personal bests identification system for both `latest_teg_context.py` and `latest_round.py` pages using a hybrid approach that:
1. Leverages existing rank data already computed in the ranked datasets
2. Identifies ALL types of records and PBs visible on these pages
3. Displays results in a clean, expandable summary section

---

## Data Sources & What We Can Identify

### Available Ranked Data (Already Computed)
Both TEG and Round data include ranking columns for all aggregate score metrics:
- `Rank_within_player_Sc` / `Rank_within_all_Sc`
- `Rank_within_player_GrossVP` / `Rank_within_all_GrossVP`
- `Rank_within_player_NetVP` / `Rank_within_all_NetVP`
- `Rank_within_player_Stableford` / `Rank_within_all_Stableford`

9-hole (frontback) data also has same ranking structure.

### Records/PBs We Can Identify

#### 1. **Aggregate Score Records & PBs** (Already on pages)
From the "Aggregate Score" / "Scoreboards" tabs:
- **Records:** `Rank_within_all_[metric] = 1` for Score, GrossVP, NetVP, Stableford
- **Personal Bests:** `Rank_within_player_[metric] = 1`
- **Personal Worsts:** `Rank_within_player_[metric] = max` for each player

#### 2. **9-Hole Records & PBs** (New - requires lookup)
For rounds, check if any 9-hole segments (front 9 or back 9) set records:
- Load `get_ranked_frontback_data()`
- Filter for selected TEG + Round
- Check rankings for both Front 9 and Back 9
- Same metrics: Score, GrossVP, NetVP, Stableford

#### 3. **Scoring Pattern Records** (New - requires analysis)
From the "Scoring" tab data:
- **Most of a specific score in a round/TEG** (e.g., "Most eagles in a round")
- **Fewest bogeys in a round/TEG**
- **Most birdies in a round/TEG**
- These would require comparing to historical maxes/mins

#### 4. **Streak Records** (New - requires lookup)
From the "Streaks" tab:
- Check if any displayed streak values match all-time records
- Compare against `prepare_record_best_streaks_data()` and `prepare_record_worst_streaks_data()`
- Identify: Eagles, Birdies, Pars, No +2s, Over Par, TBPs

---

## Implementation Approach

### Phase 1: Core Aggregate Score Records (Simplest - Already Have Data)

**What:** Identify records and PBs from the existing context tables (Score, GrossVP, NetVP, Stableford)

**How:**
1. After preparing context display data in each metric tab, collect the underlying dataframe
2. Scan for `Rank_within_all_[metric] = 1` (all-time records)
3. Scan for `Rank_within_player_[metric] = 1` (personal bests)
4. Collect worst rankings (max rank within player for each player)

**Implementation:**
```python
def identify_aggregate_records_and_pbs(df_teg_or_round, selected_teg, selected_round=None):
    """
    Identify records and PBs from aggregate score metrics.

    Args:
        df_teg_or_round: Ranked TEG or round data
        selected_teg: Selected TEG string (e.g., "TEG 17")
        selected_round: Selected round number (for rounds only)

    Returns:
        dict with keys: 'records', 'personal_bests', 'personal_worsts'
        Each is a list of dicts: [{'player': 'Jim', 'metric': 'GrossVP', 'value': -12, 'type': 'TEG'}, ...]
    """
    # Filter to selected TEG/round
    if selected_round:
        filtered = df_teg_or_round[(df_teg_or_round['TEG'] == selected_teg) &
                                    (df_teg_or_round['Round'] == selected_round)]
    else:
        filtered = df_teg_or_round[df_teg_or_round['TEG'] == selected_teg]

    metrics = ['Sc', 'GrossVP', 'NetVP', 'Stableford']
    records = []
    personal_bests = []
    personal_worsts = []

    for metric in metrics:
        rank_all_col = f'Rank_within_all_{metric}'
        rank_player_col = f'Rank_within_player_{metric}'

        # Check each player's performance
        for _, row in filtered.iterrows():
            player = row['Player']
            value = row[metric]

            # All-time record
            if row[rank_all_col] == 1:
                records.append({
                    'player': player,
                    'metric': metric,
                    'value': value,
                    'friendly_name': get_friendly_metric_name(metric)
                })

            # Personal best
            if row[rank_player_col] == 1:
                personal_bests.append({
                    'player': player,
                    'metric': metric,
                    'value': value,
                    'friendly_name': get_friendly_metric_name(metric)
                })

            # Personal worst (check if this is player's worst for this metric)
            player_data = df_teg_or_round[df_teg_or_round['Player'] == player]
            max_rank = player_data[rank_player_col].max()
            if row[rank_player_col] == max_rank and max_rank > 1:
                personal_worsts.append({
                    'player': player,
                    'metric': metric,
                    'value': value,
                    'friendly_name': get_friendly_metric_name(metric)
                })

    return {
        'records': records,
        'personal_bests': personal_bests,
        'personal_worsts': personal_worsts
    }
```

### Phase 2: 9-Hole Records (Round Page Only)

**What:** Check if front 9 or back 9 of selected round set any records

**How:**
1. Load `get_ranked_frontback_data()`
2. Filter for selected TEG + Round
3. Check rankings for both front and back 9s
4. Same logic as Phase 1

**Implementation:**
```python
def identify_9hole_records_and_pbs(selected_teg, selected_round):
    """
    Identify 9-hole records and PBs for the selected round.

    Returns:
        dict with same structure as Phase 1, plus 'segment' key (Front/Back)
    """
    from utils import get_ranked_frontback_data

    df_9hole = get_ranked_frontback_data()

    # Parse TEG number
    teg_num = int(selected_teg.split()[1])

    # Filter to selected round
    filtered = df_9hole[(df_9hole['TEGNum'] == teg_num) &
                        (df_9hole['Round'] == selected_round)]

    # Apply same logic as Phase 1, but include FrontBack column
    # ... (similar scanning logic)

    return results
```

### Phase 3: Streak Records

**What:** Identify if any streaks shown match all-time records

**How:**
1. Load streak records using existing functions: `prepare_record_best_streaks_data()` and `prepare_record_worst_streaks_data()`
2. Compare displayed streak values against these records
3. Check if player's streak value matches the record value

**Implementation:**
```python
def identify_streak_records(all_data, streaks_df, selected_teg, selected_round=None):
    """
    Identify streak records for selected TEG/round.

    Returns:
        dict with 'records' and 'personal_bests' for streaks
    """
    from helpers.streak_analysis_processing import (
        prepare_record_best_streaks_data,
        prepare_record_worst_streaks_data,
        get_player_window_streaks
    )

    # Get record streaks
    best_streak_records = prepare_record_best_streaks_data(all_data)
    worst_streak_records = prepare_record_worst_streaks_data(all_data)

    # Get streaks for this TEG/round
    if selected_round:
        teg_streaks = get_player_window_streaks(all_data, streaks_df,
                                                 teg=selected_teg, round_num=selected_round)
    else:
        # For TEG, get through last round
        teg_num = int(selected_teg.split()[1])
        last_round = all_data[all_data['TEGNum'] == teg_num]['Round'].max()
        teg_streaks = get_player_window_streaks(all_data, streaks_df,
                                                 teg=selected_teg, round_num=last_round)

    records = []

    # Compare each player's streak to records
    for _, row in teg_streaks.iterrows():
        streak_type = row['Streak Type']
        player = row['Player']
        max_streak = row['Max Streak']

        # Check if this matches a record
        matching_record = best_streak_records[
            best_streak_records['Streak Type'] == streak_type
        ]

        if not matching_record.empty:
            record_value = int(matching_record.iloc[0]['Record'])
            if max_streak == record_value:
                records.append({
                    'player': player,
                    'streak_type': streak_type,
                    'value': max_streak
                })

    return {'records': records}
```

### Phase 4: Display Component

**What:** Create clean, expandable UI component to show all identified records/PBs

**Implementation:**
```python
def display_records_and_pbs_summary(records_dict, page_type='TEG'):
    """
    Display records and PBs in an expandable section.

    Args:
        records_dict: Combined dict from all identification phases
        page_type: 'TEG' or 'Round'
    """
    import streamlit as st
    from utils import format_vs_par

    # Count total items
    total_items = (len(records_dict.get('aggregate_records', [])) +
                   len(records_dict.get('aggregate_pbs', [])) +
                   len(records_dict.get('aggregate_worsts', [])) +
                   len(records_dict.get('9hole_records', [])) +
                   len(records_dict.get('9hole_pbs', [])) +
                   len(records_dict.get('streak_records', [])))

    if total_items == 0:
        return  # Don't show section if nothing to display

    # Expandable section
    st.markdown("---")
    with st.expander(f"🏆 Records & Personal Bests for this {page_type}", expanded=True):

        # All-Time Records
        aggregate_records = records_dict.get('aggregate_records', [])
        nine_hole_records = records_dict.get('9hole_records', [])
        streak_records = records_dict.get('streak_records', [])

        if aggregate_records or nine_hole_records or streak_records:
            st.markdown("**🏆 All-Time Records:**")

            if aggregate_records:
                for record in aggregate_records:
                    value = format_value(record['value'], record['metric'])
                    st.markdown(f"- **{record['friendly_name']}:** {value} ({record['player']})")

            if nine_hole_records:
                for record in nine_hole_records:
                    value = format_value(record['value'], record['metric'])
                    segment = record['segment']
                    st.markdown(f"- **{segment} 9 - {record['friendly_name']}:** {value} ({record['player']})")

            if streak_records:
                for record in streak_records:
                    st.markdown(f"- **{record['streak_type']} streak:** {record['value']} holes ({record['player']})")

        # Personal Bests
        aggregate_pbs = records_dict.get('aggregate_pbs', [])
        nine_hole_pbs = records_dict.get('9hole_pbs', [])

        if aggregate_pbs or nine_hole_pbs:
            st.markdown("")
            st.markdown("**⭐ Personal Bests:**")

            # Group by player
            from collections import defaultdict
            pbs_by_player = defaultdict(list)

            for pb in aggregate_pbs:
                pbs_by_player[pb['player']].append(pb)
            for pb in nine_hole_pbs:
                pbs_by_player[pb['player']].append(pb)

            for player in sorted(pbs_by_player.keys()):
                player_pbs = pbs_by_player[player]
                pb_list = []
                for pb in player_pbs:
                    value = format_value(pb['value'], pb['metric'])
                    if 'segment' in pb:
                        pb_list.append(f"{pb['segment']} 9 - {pb['friendly_name']}: {value}")
                    else:
                        pb_list.append(f"{pb['friendly_name']}: {value}")

                st.markdown(f"- **{player}:** {', '.join(pb_list)}")

        # Personal Worsts
        aggregate_worsts = records_dict.get('aggregate_worsts', [])

        if aggregate_worsts:
            st.markdown("")
            st.markdown("**⚠️ Personal Worsts:**")

            # Group by player
            worsts_by_player = defaultdict(list)
            for worst in aggregate_worsts:
                worsts_by_player[worst['player']].append(worst)

            for player in sorted(worsts_by_player.keys()):
                player_worsts = worsts_by_player[player]
                worst_list = []
                for worst in player_worsts:
                    value = format_value(worst['value'], worst['metric'])
                    worst_list.append(f"{worst['friendly_name']}: {value}")

                st.markdown(f"- **{player}:** {', '.join(worst_list)}")

def format_value(value, metric):
    """Format value based on metric type."""
    from utils import format_vs_par

    if metric in ['GrossVP', 'NetVP']:
        return format_vs_par(value)
    else:
        return str(int(value))
```

---

## File Structure

### New Helper File
Create: `streamlit/helpers/records_identification.py`

Contains:
- `identify_aggregate_records_and_pbs()`
- `identify_9hole_records_and_pbs()`
- `identify_streak_records()`
- `display_records_and_pbs_summary()`
- `format_value()`
- Helper functions for formatting and grouping

### Updates to Existing Files

**`streamlit/latest_teg_context.py`:**
```python
# After all main tabs, before navigation links:

# Identify all records and PBs
from helpers.records_identification import (
    identify_aggregate_records_and_pbs,
    identify_streak_records,
    display_records_and_pbs_summary
)

records_dict = {}

# Phase 1: Aggregate scores
aggregate_results = identify_aggregate_records_and_pbs(df_teg, teg_t)
records_dict.update({
    'aggregate_records': aggregate_results['records'],
    'aggregate_pbs': aggregate_results['personal_bests'],
    'aggregate_worsts': aggregate_results['personal_worsts']
})

# Phase 3: Streaks
streak_results = identify_streak_records(all_data, streaks_df, teg_t)
records_dict.update({
    'streak_records': streak_results['records']
})

# Display
display_records_and_pbs_summary(records_dict, page_type='TEG')
```

**`streamlit/latest_round.py`:**
```python
# After all main tabs, before navigation links:

from helpers.records_identification import (
    identify_aggregate_records_and_pbs,
    identify_9hole_records_and_pbs,
    identify_streak_records,
    display_records_and_pbs_summary
)

records_dict = {}

# Phase 1: Aggregate scores
aggregate_results = identify_aggregate_records_and_pbs(df_round, teg_r, rd_r)
records_dict.update({
    'aggregate_records': aggregate_results['records'],
    'aggregate_pbs': aggregate_results['personal_bests'],
    'aggregate_worsts': aggregate_results['personal_worsts']
})

# Phase 2: 9-hole records (round only)
nine_hole_results = identify_9hole_records_and_pbs(teg_r, rd_r)
records_dict.update({
    '9hole_records': nine_hole_results['records'],
    '9hole_pbs': nine_hole_results['personal_bests']
})

# Phase 3: Streaks
streak_results = identify_streak_records(all_data, streaks_df, teg_r, rd_r)
records_dict.update({
    'streak_records': streak_results['records']
})

# Display
display_records_and_pbs_summary(records_dict, page_type='Round')
```

---

## Implementation Order

1. **Create helper file** with basic structure and Phase 1 functions
2. **Implement Phase 1** (aggregate scores) on both pages - TEST
3. **Implement display component** - TEST with Phase 1 data
4. **Implement Phase 2** (9-hole) on round page only - TEST
5. **Implement Phase 3** (streaks) on both pages - TEST
6. **Polish and refinement** (formatting, edge cases, performance)

---

## Edge Cases to Handle

1. **No records/PBs found:** Don't show the expander section at all
2. **Tied records:** Show all players who share the record
3. **Multiple PBs by same player:** Group them together in display
4. **Current incomplete TEG:** Handle gracefully (may have incomplete data)
5. **Missing streak data:** Check if streak data exists before analysis
6. **Worst rankings:** Only show if rank > 1 (not if it's their only performance)

---

## Testing Checklist

- [ ] Test with TEG that has records (e.g., TEG with best-ever score)
- [ ] Test with TEG that has no records
- [ ] Test with player's personal best TEG
- [ ] Test with round that has 9-hole records
- [ ] Test with round that has streak records
- [ ] Test with incomplete/in-progress TEG
- [ ] Test display formatting for all value types
- [ ] Test grouping of multiple PBs by same player
- [ ] Test performance with large datasets

---

## Notes on Scope Reduction

**Not implementing in initial version:**
- Scoring pattern records (most eagles, fewest bogeys, etc.) - requires additional analysis
- Historical context beyond rank (e.g., "3rd best ever") - adds complexity
- Personal best/worst streaks (only showing all-time records)
- Scorecard-specific records (hole-by-hole analysis)

These can be added later if desired.
