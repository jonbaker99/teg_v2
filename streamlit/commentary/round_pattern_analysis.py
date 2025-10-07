"""
Round Pattern Analysis

This module analyzes patterns within a single round to identify:
- Key momentum shifts and turning points
- Position changes (who moved up/down)
- Dramatic moments and critical holes

Functions are designed to feed LLM story generation.
"""

import pandas as pd


def identify_round_momentum_shifts(round_data):
    """
    Identify key momentum shifts and turning points in the round.

    Uses events data + hole-by-hole positions to find:
    - Lead changes (when position 1 changed hands)
    - Critical holes where multiple players' fortunes changed
    - Turning points (blow-ups, eagles, big position swings)

    Args:
        round_data: Output from load_round_report_data()

    Returns:
        Dict with:
        - lead_changes: List of holes where lead changed
        - critical_holes: Holes where lots changed (multiple events/big swings)
        - turning_points: Key moments that altered the round
    """
    positions_df = pd.DataFrame(round_data['positions_through_round'])
    events_list = round_data['events']

    # Find lead changes
    lead_changes = []
    prev_leader = None

    for hole in range(1, 19):
        hole_positions = positions_df[positions_df['Hole'] == hole].sort_values('Position')
        if len(hole_positions) > 0:
            current_leader = hole_positions.iloc[0]['Player']

            if prev_leader is not None and current_leader != prev_leader:
                # Lead changed!
                lead_changes.append({
                    'hole': hole,
                    'from': prev_leader,
                    'to': current_leader,
                    'new_leader_total': int(hole_positions.iloc[0]['Tournament_Cumulative_Stableford'])
                })

            prev_leader = current_leader

    # Identify critical holes (lots of activity)
    hole_event_counts = {}
    for event in events_list:
        hole = event.get('Hole')
        if hole:
            hole_event_counts[hole] = hole_event_counts.get(hole, 0) + 1

    # Critical holes = 3+ events OR lead change
    critical_holes = []
    lead_change_holes = {lc['hole'] for lc in lead_changes}

    for hole in range(1, 19):
        event_count = hole_event_counts.get(hole, 0)
        is_lead_change = hole in lead_change_holes

        # Get position changes on this hole
        if hole > 1:
            prev_hole_pos = positions_df[positions_df['Hole'] == hole - 1][['Player', 'Position']].set_index('Player')
            curr_hole_pos = positions_df[positions_df['Hole'] == hole][['Player', 'Position']].set_index('Player')

            position_changes = []
            for player in curr_hole_pos.index:
                if player in prev_hole_pos.index:
                    change = prev_hole_pos.loc[player, 'Position'] - curr_hole_pos.loc[player, 'Position']
                    if abs(change) >= 2:  # Moved up/down 2+ places
                        position_changes.append({'player': player, 'change': int(change)})

            if event_count >= 3 or is_lead_change or len(position_changes) >= 2:
                critical_holes.append({
                    'hole': hole,
                    'event_count': event_count,
                    'lead_change': is_lead_change,
                    'position_changes': position_changes
                })

    # Turning points: Eagles, disasters (0 pts), lead changes
    turning_points = []

    for event in events_list:
        event_type = event.get('Event', '')
        player = event.get('Player', '')
        hole = event.get('Hole')

        # Eagles are always turning points
        if event_type == 'Eagle':
            turning_points.append({
                'type': 'eagle',
                'player': player,
                'hole': hole,
                'description': f"{player} eagle at hole {hole}"
            })

        # Zero-point holes (disasters)
        if event_type == 'Zero_Stableford_Points':
            turning_points.append({
                'type': 'disaster',
                'player': player,
                'hole': hole,
                'description': f"{player} disaster (0 pts) at hole {hole}"
            })

    # Add lead changes to turning points
    for lc in lead_changes:
        turning_points.append({
            'type': 'lead_change',
            'player': lc['to'],
            'hole': lc['hole'],
            'description': f"{lc['to']} takes lead from {lc['from']} at hole {lc['hole']}"
        })

    return {
        'lead_changes': lead_changes,
        'critical_holes': critical_holes,
        'turning_points': sorted(turning_points, key=lambda x: x['hole'])
    }


def analyze_position_changes(round_data):
    """
    Analyze who gained/lost ground during the round.

    Args:
        round_data: Output from load_round_report_data()

    Returns:
        Dict with:
        - biggest_movers_up: Players who gained most positions
        - biggest_movers_down: Players who lost most positions
        - position_summary: All players' changes
    """
    positions_df = pd.DataFrame(round_data['positions_through_round'])

    # Get start and end positions for each player
    position_changes = []

    for player in positions_df['Player'].unique():
        player_data = positions_df[positions_df['Player'] == player]

        starting_position = player_data.iloc[0]['Starting_Position']
        ending_position = player_data.iloc[-1]['Position']  # After hole 18

        change = starting_position - ending_position  # Positive = moved up

        position_changes.append({
            'player': player,
            'starting_position': int(starting_position),
            'ending_position': int(ending_position),
            'change': int(change),
            'moved_up': change > 0,
            'moved_down': change < 0,
            'stayed_same': change == 0
        })

    # Sort by change
    position_changes = sorted(position_changes, key=lambda x: x['change'], reverse=True)

    # Biggest movers
    movers_up = [p for p in position_changes if p['change'] > 0]
    movers_down = [p for p in position_changes if p['change'] < 0]

    return {
        'biggest_movers_up': movers_up,
        'biggest_movers_down': sorted(movers_down, key=lambda x: x['change']),
        'position_summary': position_changes
    }


def get_round_storylines(round_data):
    """
    High-level function to extract key storylines from round data.
    Combines momentum shifts + position changes for easy consumption.

    Args:
        round_data: Output from load_round_report_data()

    Returns:
        Dict with organized storyline data ready for LLM prompts
    """
    momentum = identify_round_momentum_shifts(round_data)
    positions = analyze_position_changes(round_data)

    # Combine into structured storylines
    storylines = {
        'round_winner': None,  # Will be filled from round_summary
        'lead_battle': {
            'lead_changes': momentum['lead_changes'],
            'final_leader': None,
            'final_margin': None
        },
        'biggest_stories': {
            'movers_up': positions['biggest_movers_up'][:3],  # Top 3
            'movers_down': positions['biggest_movers_down'][:3],  # Top 3 (worst)
            'turning_points': momentum['turning_points']
        },
        'critical_holes': momentum['critical_holes'],
        'drama_level': 'high' if len(momentum['lead_changes']) > 1 else 'medium' if len(momentum['lead_changes']) == 1 else 'low'
    }

    # Fill in round winner from round_summary
    round_summary = round_data['round_summary']
    if len(round_summary) > 0:
        # Find best Stableford score
        best_stableford = max(round_summary, key=lambda x: x['Round_Score_Stableford'])
        storylines['round_winner'] = {
            'player': best_stableford['Player'],
            'score': int(best_stableford['Round_Score_Stableford']),
            'gross': int(best_stableford['Round_Score_Gross']),
            'rank': int(best_stableford['Player_Round_Rank_Stableford'])
        }

        # Final leader
        final_leader = min(round_summary, key=lambda x: x['Cumulative_Tournament_Rank_Stableford'])
        second_place = sorted(round_summary, key=lambda x: x['Cumulative_Tournament_Rank_Stableford'])[1] if len(round_summary) > 1 else None

        storylines['lead_battle']['final_leader'] = final_leader['Player']
        storylines['lead_battle']['final_margin'] = int(abs(second_place['Gap_To_Leader_After_Round_Stableford'])) if second_place else 0

    return storylines


if __name__ == "__main__":
    # Test with TEG 17, Round 2
    print("\n" + "="*60)
    print("TESTING ROUND PATTERN ANALYSIS - TEG 17, Round 2")
    print("="*60 + "\n")

    from round_data_loader import load_round_report_data

    round_data = load_round_report_data(17, 2)

    print("\n" + "="*60)
    print("MOMENTUM SHIFTS")
    print("="*60)

    momentum = identify_round_momentum_shifts(round_data)

    print(f"\nLead Changes: {len(momentum['lead_changes'])}")
    for lc in momentum['lead_changes']:
        print(f"  Hole {lc['hole']}: {lc['from']} -> {lc['to']}")

    print(f"\nCritical Holes: {len(momentum['critical_holes'])}")
    for ch in momentum['critical_holes'][:5]:  # Show top 5
        print(f"  Hole {ch['hole']}: {ch['event_count']} events" + (" + LEAD CHANGE" if ch['lead_change'] else ""))

    print(f"\nTurning Points: {len(momentum['turning_points'])}")
    for tp in momentum['turning_points'][:5]:  # Show first 5
        print(f"  {tp['description']}")

    print("\n" + "="*60)
    print("POSITION CHANGES")
    print("="*60)

    positions = analyze_position_changes(round_data)

    print(f"\nBiggest Movers Up:")
    for p in positions['biggest_movers_up']:
        print(f"  {p['player']}: +{p['change']} (pos {p['starting_position']} -> {p['ending_position']})")

    print(f"\nBiggest Movers Down:")
    for p in positions['biggest_movers_down'][:3]:  # Top 3 worst
        print(f"  {p['player']}: {p['change']} (pos {p['starting_position']} -> {p['ending_position']})")

    print("\n" + "="*60)
    print("HIGH-LEVEL STORYLINES")
    print("="*60)

    storylines = get_round_storylines(round_data)

    print(f"\nRound Winner: {storylines['round_winner']['player']} ({storylines['round_winner']['score']} pts)")
    print(f"Final Leader: {storylines['lead_battle']['final_leader']} (margin: {storylines['lead_battle']['final_margin']} pts)")
    print(f"Drama Level: {storylines['drama_level'].upper()}")
    print(f"Lead Changes: {len(storylines['lead_battle']['lead_changes'])}")
    print(f"Turning Points: {len(storylines['biggest_stories']['turning_points'])}")

    print("\n" + "="*60)
    print("> ROUND PATTERN ANALYSIS TEST COMPLETE")
    print("="*60 + "\n")
