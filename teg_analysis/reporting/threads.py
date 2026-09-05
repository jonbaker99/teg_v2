"""Deterministic, free subplot detection: cluster beats into candidate threads.

Phase 1 of the storyline-first proposal (`STORYLINE_PLAN.md`). Nothing in the
pipeline groups beats into a subject-based thread spanning rounds today —
`vehicle_fit.py` scores named *frames* against the whole beat set, but a frame
isn't a subplot, and beats are otherwise scored individually. This module is
the missing candidate signal: same shape as `vehicle_fit_hints`, an advisory
list for the editor, not a verdict.

A thread is beats sharing a subject — a player, a repeated course, or a
recurring failure motif for one player — that span 2+ rounds. Single-round
clusters aren't subplots; they're just what happened in a round, which the
dry draft's mandatory-beat ledger already covers.
"""

from __future__ import annotations

from collections import defaultdict

# Beat types that ARE the tournament outcome, not material for a subplot —
# excluded from every clustering pass. round_leadership/round_player/
# round_player_gross are standings snapshots, not events, and long_lead_lost
# is Trophy-race-specific unless it happens to a non-Trophy player.
_OUTCOME_TYPES = {"trophy_win", "jacket_win", "wooden_spoon"}

# The failure family a "recurring failure mode" thread clusters on.
_FAILURE_TYPES = {"cold_stretch_gross", "cold_stretch_net", "collapse_after_steady", "long_lead_lost"}


def _rounds(beats: list) -> set:
    return {b["round"] for b in beats if b.get("round") is not None}


def _is_trophy_restating(beats: list, trophy_winner: str) -> bool:
    """A cluster that's just the Trophy arc retold isn't a subplot. True when
    every beat belongs to the Trophy winner AND is one of the types that
    `win_anatomy`/the Trophy arc already narrates (leadership snapshots and
    the lead-loss/gain beats), i.e. there's no beat in the cluster that isn't
    already spoken for by the winner's-story material."""
    if not trophy_winner or not beats:
        return False
    trophy_types = {"round_leadership", "round_player", "round_player_gross", "long_lead_lost"}
    return all(
        trophy_winner in (b.get("players") or []) and b["type"] in trophy_types
        for b in beats
    )


def _score_cluster(beats: list, trophy_winner: str) -> dict:
    rounds = _rounds(beats)
    entertainment_sum = sum(b["scores"]["entertainment"] for b in beats)
    rarity_max = max((b["scores"]["rarity"] for b in beats), default=0.0)
    independent = not _is_trophy_restating(beats, trophy_winner)
    score = (
        3.0 * len(rounds)
        + 0.5 * entertainment_sum
        + 1.0 * rarity_max
        + (2.0 if independent else -5.0)
    )
    return {
        "round_span": sorted(rounds),
        "entertainment_sum": round(entertainment_sum, 1),
        "rarity_max": round(rarity_max, 1),
        "independent_of_trophy": independent,
        "score": round(score, 1),
    }


def cluster_by_player(beats: list) -> list:
    """One cluster per player, over every non-outcome beat they appear in."""
    by_player = defaultdict(list)
    for b in beats:
        if b["type"] in _OUTCOME_TYPES:
            continue
        for p in b.get("players") or []:
            by_player[p].append(b)
    return [
        {"subject_type": "player", "subject": player, "beats": cluster}
        for player, cluster in by_player.items()
    ]


def cluster_by_course(beats: list) -> list:
    """One cluster per course that was played in 2+ rounds of this TEG
    (most TEGs use a different course each round, so this usually fires
    zero clusters — that's a real 'no course subplot' signal, not a gap)."""
    by_course = defaultdict(list)
    for b in beats:
        if b["type"] in _OUTCOME_TYPES:
            continue
        course = b.get("course")
        if course:
            by_course[course].append(b)
    return [
        {"subject_type": "course", "subject": course, "beats": cluster}
        for course, cluster in by_course.items()
        if len(_rounds(cluster)) >= 2
    ]


def cluster_by_failure_mode(beats: list) -> list:
    """One cluster per player who has 2+ beats in the failure family
    (cold stretches, collapses, a blown lead) across different rounds — a
    recurring pattern, not a single bad round."""
    by_player = defaultdict(list)
    for b in beats:
        if b["type"] not in _FAILURE_TYPES:
            continue
        for p in b.get("players") or []:
            by_player[p].append(b)
    return [
        {"subject_type": "failure_mode", "subject": player, "beats": cluster}
        for player, cluster in by_player.items()
    ]


def detect_threads(beats: list, arcs: dict, top_n: int = 8) -> list:
    """Cluster `beats` (the `all_beats` list `assemble_bundle` builds) into
    candidate subplot threads and return the top `top_n` scored desc.

    Each candidate: {subject_type, subject, round_span, entertainment_sum,
    rarity_max, independent_of_trophy, score, beat_ids, headlines}.

    Only clusters spanning 2+ rounds are returned — a subplot is defined by
    persisting across the tournament, not by happening once.
    """
    trophy_winner = (arcs.get("trophy") or {}).get("winner")
    raw_clusters = (
        cluster_by_player(beats) + cluster_by_course(beats) + cluster_by_failure_mode(beats)
    )

    candidates = []
    for c in raw_clusters:
        cluster_beats = c["beats"]
        if len(_rounds(cluster_beats)) < 2:
            continue
        scored = _score_cluster(cluster_beats, trophy_winner)
        candidates.append({
            "subject_type": c["subject_type"],
            "subject": c["subject"],
            **scored,
            "beat_ids": [b["id"] for b in cluster_beats],
            "headlines": [b["headline"] for b in cluster_beats],
        })

    candidates.sort(key=lambda x: -x["score"])
    return candidates[:top_n]
