"""
Data Loader Module for Tournament Story Generation

This module provides functions to load and filter tournament data
for specific rounds, preparing focused datasets for story generation.
"""

import sys
import os

# Add parent directory to path to import utils
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))


def load_round_data(teg_num, round_num, all_processed_data):
    """
    Load all data for a specific round from processed data.

    Filters multi-round data to just this round, creating a focused
    dataset including records, PBs, and course records.

    Args:
        teg_num: Tournament number
        round_num: Round number
        all_processed_data: Output from process_all_data_types()

    Returns:
        Dict with focused data points for this round:
        - round: Round number
        - lead_timeline: Leader info for this round
        - lead_changes: Lead changes in this round
        - momentum_patterns: Momentum windows for this round
        - nine_patterns: Front/back 9 patterns for this round
        - pattern_details: Enriched patterns with hole details
        - events: Notable events from this round
        - summary: Round summary data for all players
        - records_and_pbs: Records and personal bests for this round
        - course_records: Course records for this round
    """
    # Filter lead data to this round
    lead_timeline = [
        entry for entry in all_processed_data['lead_data']['lead_timeline']
        if entry['round'] == round_num
    ]

    lead_changes = [
        entry for entry in all_processed_data['lead_data']['lead_changes']
        if entry['round'] == round_num
    ]

    # Filter momentum patterns to this round
    momentum_patterns = [
        pattern for pattern in all_processed_data['momentum_data']
        if pattern['round'] == round_num
    ]

    # Filter nine patterns to this round
    nine_patterns = [
        pattern for pattern in all_processed_data['nine_data']
        if pattern['round'] == round_num
    ]

    # Filter pattern details to this round
    pattern_details = [
        detail for detail in all_processed_data['pattern_details']
        if detail['round'] == round_num
    ]

    # Filter events to this round
    round_events = [
        event for event in all_processed_data['round_events']
        if event['Round'] == round_num
    ]

    # Filter round summary to this round
    round_summary = [
        summary for summary in all_processed_data['round_summary']
        if summary['Round'] == round_num
    ]

    # Get records and PBs for this round
    records_and_pbs = all_processed_data['records_by_round'].get(round_num, {
        'all_time_records': [],
        'all_time_worsts': [],
        'personal_bests': [],
        'personal_worsts': []
    })

    # Get course records for this round
    course_records = all_processed_data['course_records_by_round'].get(round_num, [])

    return {
        'round': round_num,
        'lead_timeline': lead_timeline,
        'lead_changes': lead_changes,
        'momentum_patterns': momentum_patterns,
        'nine_patterns': nine_patterns,
        'pattern_details': pattern_details,
        'events': round_events,
        'summary': round_summary,
        'records_and_pbs': records_and_pbs,
        'course_records': course_records
    }


def get_round_ending_context(round_data):
    """
    Extract ending context from round data to pass to next round.

    Provides the context of how the round ended - standings, gaps,
    and momentum - to feed into the opening of the next round's story.

    Args:
        round_data: Output from load_round_data()

    Returns:
        Dict with standings, gaps, and momentum after this round:
        - round: Round number
        - leader: Leader after this round
        - margin: Margin to 2nd place
        - standings: Top 5 standings with gaps
        - hot_momentum: Players finishing hot
        - cold_momentum: Players finishing cold
    """
    # Get final standings after this round from round_summary
    standings = sorted(
        round_data['summary'],
        key=lambda x: x['Cumulative_Tournament_Rank_Stableford']
    )

    # Get final lead situation
    final_lead = round_data['lead_timeline'][0] if round_data['lead_timeline'] else None

    # Identify who's hot/cold going into next round
    # Look for momentum patterns that finish late in the round (holes 15-18)
    hot_players = []
    cold_players = []

    for pattern in round_data['pattern_details']:
        if 'birdies_in_window' in pattern:  # It's a momentum pattern
            holes_str = pattern['holes']
            end_hole = int(holes_str.split('-')[1])

            if end_hole >= 15:  # Finished hot/cold late in round
                if pattern['type'] == 'hot':
                    hot_players.append(pattern['player'])
                elif pattern['type'] == 'cold':
                    cold_players.append(pattern['player'])

    # Remove duplicates while preserving order
    hot_players = list(dict.fromkeys(hot_players))
    cold_players = list(dict.fromkeys(cold_players))

    return {
        'round': round_data['round'],
        'leader': final_lead['leader'] if final_lead else None,
        'margin': final_lead['margin_to_2nd'] if final_lead else None,
        'standings': [
            {
                'player': s['Player'],
                'rank': s['Cumulative_Tournament_Rank_Stableford'],
                'gap': s['Gap_To_Leader_After_Round_Stableford']
            }
            for s in standings[:5]  # Top 5 for context
        ],
        'hot_momentum': hot_players,
        'cold_momentum': cold_players
    }


if __name__ == "__main__":
    # Test with TEG 17 Round 2
    print("\n" + "=" * 60)
    print("TESTING DATA LOADER - TEG 17 Round 2")
    print("=" * 60 + "\n")

    # First process all data
    from pattern_analysis import process_all_data_types

    print("Processing all TEG 17 data...")
    all_data = process_all_data_types(17)

    # Load Round 2 specific data
    print("\n" + "=" * 60)
    print("Loading Round 2 data...")
    print("=" * 60 + "\n")

    round_2_data = load_round_data(17, 2, all_data)

    # Show what we got
    print(f"Round {round_2_data['round']} Data Summary:")
    print(f"  Lead timeline entries: {len(round_2_data['lead_timeline'])}")
    print(f"  Lead changes: {len(round_2_data['lead_changes'])}")
    print(f"  Momentum patterns: {len(round_2_data['momentum_patterns'])}")
    print(f"  Nine-hole patterns: {len(round_2_data['nine_patterns'])}")
    print(f"  Pattern details (with drill-down): {len(round_2_data['pattern_details'])}")
    print(f"  Round events: {len(round_2_data['events'])}")
    print(f"  Player summaries: {len(round_2_data['summary'])}")

    total_data_points = (
        len(round_2_data['lead_timeline']) +
        len(round_2_data['lead_changes']) +
        len(round_2_data['momentum_patterns']) +
        len(round_2_data['nine_patterns']) +
        len(round_2_data['pattern_details']) +
        len(round_2_data['events']) +
        len(round_2_data['summary'])
    )
    print(f"\n  Total data points: {total_data_points}")

    # Show lead change if any
    if round_2_data['lead_changes']:
        print("\nLead Change:")
        for lc in round_2_data['lead_changes']:
            print(f"  {lc['from']} -> {lc['to']} (new margin: {lc['new_margin']})")

    # Show top momentum patterns
    print("\nTop 3 Momentum Patterns:")
    net_hot = [p for p in round_2_data['pattern_details']
              if p.get('scoring_type') == 'net' and p['type'] == 'hot']
    for p in sorted(net_hot, key=lambda x: x['points'], reverse=True)[:3]:
        print(f"  {p['player']:15} holes {p['holes']:8} - {p['points']} pts")
        if p['birdies_in_window']:
            print(f"    Birdies: {p['birdies_in_window']}")

    # Get ending context
    print("\n" + "=" * 60)
    print("Extracting Round 2 Ending Context...")
    print("=" * 60 + "\n")

    ending_context = get_round_ending_context(round_2_data)

    print(f"After Round {ending_context['round']}:")
    print(f"  Leader: {ending_context['leader']}")
    print(f"  Margin: {ending_context['margin']} points")

    print("\n  Top 5 Standings:")
    for s in ending_context['standings']:
        print(f"    {s['rank']}. {s['player']:15} (gap: {s['gap']})")

    if ending_context['hot_momentum']:
        print(f"\n  Hot momentum: {', '.join(ending_context['hot_momentum'])}")

    if ending_context['cold_momentum']:
        print(f"  Cold momentum: {', '.join(ending_context['cold_momentum'])}")

    print("\n" + "=" * 60)
    print("> DATA LOADER TEST COMPLETE")
    print("=" * 60)
