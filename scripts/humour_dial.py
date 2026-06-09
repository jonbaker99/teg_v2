"""Quick experiment: 8/10 humour dial, BROOKER-ONLY variant. Drops Clive
James (and the literary-comparison register that came with him); adds
Marina Hyde for matched contemporary punch. Aim is the Guardian-column
voice: physical, present-tense, observational, staccato cruelty. No
sustained literary metaphor; no winking; no flourish.

Outputs: data/commentary/teg_{N}_report_humour8bb.md (+ styled variant).
Run from repo root:
    venv/bin/python scripts/humour_dial.py
"""
from __future__ import annotations

import pathlib
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

import re

from teg_analysis.reporting import llm
from teg_analysis.reporting.authoring import load_story_plan
from teg_analysis.reporting.history_context import build_win_counts
from teg_analysis.reporting.render import (
    apply_styling,
    build_records_block,
    build_round_standings,
    _append_records,
    _strip_at_a_glance,
)
from teg_analysis.reporting.venue import build_venue_context

TEGS = [18]  # TEG 14 already produced; retrying just TEG 18 after a connection-reset on the first run.
OUT_DIR = pathlib.Path("data/commentary")


HUMOUR_DIAL_SYSTEM = """You are rewriting an existing TEG golf tournament report \
to dial the humour up from its current level (≈3/10) to ≈8/10. The existing voice \
register (deadpan, gravitas — in the spirit of Barney Ronay, Tom Peck, Jesse \
Armstrong, Armando Iannucci) is the floor. You are ADDING TWO MORE INFLUENCES to \
that roster — both modern Guardian-column voice, both punch-not-flourish:

- **Charlie Brooker** (Screen Burn / TV Go Home era): contemporary, vicious, \
specific, physical. Speaking-voice prose, not essay-voice. Comparisons are \
PHYSICAL and CONTEMPORARY (broken household objects, malfunctioning tech, \
mundane horrors, bodily indignity), not literary or classical. Escalation through \
specificity. Sentences are usually short. He never reaches for a Shakespeare \
reference where a phrase about a stuck pixel or a faulty kettle will do. The \
voice of a man watching something dreadful and describing it precisely, fast.
- **Marina Hyde** (Guardian political/cultural sketch): same register, applied to \
public absurdity. Running jokes that accumulate, recurring jabs that pay off \
across the piece, sharp specific cruelty about behaviour and pattern. Refuses to \
pretty up the subject; refuses to soften the verdict. A natural rhythm: state \
the absurd thing, follow with the deadpan correction or the cruel restatement, \
move on.

WHAT TO AIM FOR — THE BROOKER/HYDE MODE:
- PHYSICAL, CONTEMPORARY comparisons. The card looks like a malfunctioning \
spreadsheet, a player drops shots like a man trying to find the right key in the \
dark, a quadruple sits on the scorecard the way an alert appears on a phone you \
were trying to ignore. Things from the present day, things from ordinary life.
- STACCATO escalation, not sustained metaphor. One short sharp image, then move. \
If the line wants to keep going, cut it short and let the next sentence carry. \
This is the OPPOSITE of "earning paragraph length with a comparison".
- SPEAKING VOICE. The reader should hear it being said, not written. Contractions \
allowed. Asides allowed. The occasional rhetorical question — sparingly.
- 7–10 landed comic moments across the report. NOT all big-swing. A mix: 3–4 \
sharp images, the rest wry observational asides and cruel restatements built \
into existing sentences.
- BIG SWINGS still permitted, but in Brooker's mode: a single short image that \
lands, not a sustained passage. "five identical bricks laid in a row" works; \
"sits on the card in the manner of a stranger at a funeral" is leaning literary \
and would be cut in this variant.

EXPLICIT FAILURE MODES — DO NOT REPEAT:
- ❌ Literary/classical register. "In the manner of", "the kind of stretch that", \
"that suggested either remarkable resilience or", "the way the room seemed for a \
moment unsure how to absorb" — all out. This isn't Ronay-on-Sunday-supplement. \
This is Brooker-on-deadline.
- ❌ Sustained metaphor running across multiple clauses or a whole paragraph. If \
you start an image, finish it inside the sentence; do not extend it.
- ❌ Generic kicker formulas ("Timing has never been the strong suit of a title \
defence"). The kicker must be specific to THIS player, THIS round, THIS card.
- ❌ Setup-punchline structures (feed line / payoff). No "It was as if…", no \
"What can you say about…", no "you have to admire…".
- ❌ Surface wit / "look at me being witty" register. You say the cruel thing as \
if it were the only honest description of what happened. Never advertise the joke.
- ❌ Adding flourish to a sentence that's already working. The dial is about \
WHICH sentences get the swing, not bolting wit onto every sentence.
- ❌ Loosening the deadpan. The cruelty stays gravitas. No exclamation marks, no \
puns, no wacky tropes, no winking at the camera, no jokes ABOUT golf as a sport.
- ❌ Clever-for-clever's-sake numerical games (e.g. "the seventeenth-from-last \
hole" — twee, also mathematically wrong). If the cleverness requires the reader \
to do mental arithmetic to land, cut it.

ECONOMY RULES STILL APPLY (the prose density rules are non-negotiable):
- Em-dashes: max two per paragraph.
- Subordinate clauses: max two per sentence unless every clause carries a fact, \
image or beat.
- No "particular kind of X / one of them" preambles.
- No subject-burying preambles ("The detail that elevates X to Y is that…").
- Punchline isolation: short payoff sentences belong as their own paragraph.
- One dominant idea per paragraph.

FAITHFULNESS (non-negotiable):
- DO NOT change any facts: holes, scores, players, par values, weekdays, SI \
references, course names, records, margins. Every number stays exactly as written.
- DO NOT invent player relationships. Bakers and Pattersons are brothers; nothing else.
- DO NOT change section headings or the report's structural shape.
- DO NOT add weekday names anywhere they aren't already.
- British English. The protected nomenclature ("Trophy", "Green Jacket", "Jacket", \
"Wooden Spoon", "Spoon", "Stableford", "Gross", bogey terms) stays exactly as written.

OUTPUT: the complete rewritten report as markdown — same structure, same headings, \
same facts, voice register preserved but with Brooker/Hyde cruelty dialled to 8/10 \
in their MODERN, PHYSICAL, STACCATO mode (not literary-comparison mode). No \
preamble, no commentary, just the report."""


def dial_one(teg: int) -> dict:
    src = OUT_DIR / f"teg_{teg}_report_final.md"
    dst = OUT_DIR / f"teg_{teg}_report_humour8b.md"
    print(f"\n=== TEG {teg}: humour-dial start ===", flush=True)
    t0 = time.time()
    src_text = src.read_text()
    print(f"  src: {len(src_text.split())} words", flush=True)

    new_text, usage = llm.generate_text(
        HUMOUR_DIAL_SYSTEM, src_text,
        model=llm.DEFAULT_MODEL,
        max_tokens=16000,
    )
    dst.write_text(new_text)
    print(f"  new: {len(new_text.split())} words ({time.time()-t0:.1f}s) -> {dst}", flush=True)

    # Style it for direct comparison with the existing _styled.md.
    plan = load_story_plan(teg)
    venue = build_venue_context(teg)
    standings = build_round_standings(teg)
    win_counts = build_win_counts(teg)
    styled = _strip_at_a_glance(new_text)
    styled = apply_styling(styled, plan, venue, standings=standings, win_counts=win_counts)
    styled = re.sub(r'\n*## Personal bests and TEG records\n[\s\S]*$', '', styled)
    styled = _append_records(styled, build_records_block(teg))
    styled_path = OUT_DIR / f"teg_{teg}_report_humour8b_styled.md"
    styled_path.write_text(styled)
    print(f"  styled -> {styled_path}", flush=True)
    print(f"=== TEG {teg}: done in {time.time()-t0:.1f}s ===", flush=True)
    return {"teg": teg, "usage": usage, "elapsed": time.time() - t0}


def main():
    overall = time.time()
    results = [dial_one(teg) for teg in TEGS]
    print("\n=== SUMMARY ===", flush=True)
    for r in results:
        print(f"  TEG {r['teg']}: {r['elapsed']:.1f}s", flush=True)
    print(f"TOTAL: {time.time()-overall:.1f}s", flush=True)


if __name__ == "__main__":
    main()
