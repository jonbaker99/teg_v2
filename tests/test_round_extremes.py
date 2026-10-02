"""Best/worst single rounds within a TEG (analysis.records.get_teg_round_extremes)
and the two places that show them: /latest-teg's Records & PBs tab and the
tournament report's records appendix."""
import pandas as pd

from teg_analysis.analysis.records import get_teg_round_extremes


def _holes(pl, rnd, teg, grossvp, stableford, netvp=0, n=18, course="Links"):
    """n hole rows whose sums are the given round totals (all on hole 1)."""
    rows = []
    for h in range(1, n + 1):
        first = h == 1
        rows.append({"TEGNum": teg, "Pl": pl, "Player": f"{pl} PLAYER", "Round": rnd,
                     "Course": course, "Hole": h,
                     "GrossVP": grossvp if first else 0,
                     "Stableford": stableford if first else 0,
                     "NetVP": netvp if first else 0})
    return rows


def _data(teg):
    return pd.DataFrame(
        _holes("AA", 1, teg, 10, 40, -4) + _holes("BB", 1, teg, 20, 30, 6)
        + _holes("AA", 2, teg, 10, 35, 1, course="Heath")
        # A round still in play: the lowest gross so far, but only 9 holes.
        + _holes("BB", 2, teg, 2, 20, -10, n=9))


def test_extremes_stableford_era_ignores_partial_rounds_and_lists_ties():
    out = get_teg_round_extremes(_data(18), 18)
    assert [(e["kind"], e["metric"], e["value"]) for e in out] == [
        ("best", "GrossVP", 10), ("worst", "GrossVP", 20),
        ("best", "Stableford", 40), ("worst", "Stableford", 30)]
    assert [(h["pl"], h["round"], h["course"]) for h in out[0]["holders"]] == [
        ("AA", 1, "Links"), ("AA", 2, "Heath")]


def test_extremes_pre_stableford_era_uses_net():
    out = get_teg_round_extremes(_data(5), 5)
    assert [(e["metric"], e["value"]) for e in out[2:]] == [("NetVP", -4), ("NetVP", 6)]


def test_extremes_empty_for_unknown_teg():
    assert get_teg_round_extremes(_data(18), 99) == []


def test_records_tab_section_uses_round_and_course_as_detail():
    """Detail is pinned to the round/course column: "R1 / Links" is shorter
    than most player names, so the length heuristic alone would swap them."""
    from webapp.routes.latest import _render_records_summary

    html = _render_records_summary({}, "TEG", get_teg_round_extremes(_data(18), 18))
    assert "Best &amp; Worst Rounds" in html
    assert "<div class='rec-detail'>R1 / Links</div>" in html
    assert "No records or personal bests" not in html
    # Full names (first/last spans that wrap together), never "A.PLAYER".
    assert "<span class='first'>AA</span> <span class='last'>PLAYER</span>" in html
    assert "bw-name-short" not in html


def test_report_appendix_lists_best_and_worst_rounds():
    from teg_analysis.reporting.render import build_records_block

    block = build_records_block(5)
    assert '<p class="records-header">Best and worst rounds:</p>' in block
    assert "Best gross: David Mullin, +11 at Boavista (R2)" in block
    assert "Best gross: Stuart Neumann, +11 at Boavista (R2)" in block
    assert "Best net: Stuart Neumann, -9 at Boavista (R2)" in block
    assert "Best and worst rounds" not in build_records_block(18, round_num=2)
