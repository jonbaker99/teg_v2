"""Shared prompt blocks — the single source of truth for voice and rules.

Every block in this module is used by BOTH report pipelines:

* the **tournament** pipeline — `story_plan.py` (editor) + `authoring.py` (writer)
* the **round** pipeline — `round_report.py` (editor + writer)

Edit a block here and it changes everywhere at once. That is the entire point.

WHY THIS MODULE EXISTS
----------------------
Before 2026-08-15 the voice was defined in four separate string literals. Three
sessions of voice work (`ef67417` Herron, `ac55be8` the four humour mechanisms,
`342db93` dropping the Peck device) edited only `authoring.WRITER_VOICE`, because
that is where the voice experiments were run. The other three copies were never
touched, so both editor prompts and the round writer went on describing a
Ronay/Peck register that had been tested and replaced — including naming Peck,
whose device was *deliberately removed*. Nobody noticed for four days because
nothing links the copies.

The same thing had already happened to the faithfulness rules: the
scoring-redundancy rule, the same-hole-different-course rule, the
Stableford-is-not-a-paradox rule and the no-countback rule all existed twice, in
two files, edited independently.

RULES FOR EDITING
-----------------
1. **Never copy a block out of here into a call site**, however small the tweak.
   That is exactly how the drift happened. If one pipeline genuinely needs
   different wording, keep the shared block and append the difference at the call
   site, so the divergence is visible in the diff.
2. **Voice and faithfulness stay separate constants.** They have different failure
   modes (a flat sentence vs. a factual error the players catch) and different
   tests (taste vs. mechanical verification in `verify.py`). Keeping them in one
   literal is how you lose a guardrail while tuning humour.
3. **`HOUSE_VOICE_SUMMARY` must stay consistent with `VOICE_CORE`.** It is the
   short version handed to the editors, who plan for a writer they cannot see.
   A test asserts every writer named in one appears in the other.
"""

# The four comic writers the register is built on. Any prompt that needs to NAME
# them in passing (e.g. TIGHTEN_SYSTEM telling the model the voice is already
# correct) builds its phrase from these rather than typing them out — that is how
# `TIGHTEN_SYSTEM` ended up still advertising Peck after the device was dropped.
VOICE_WRITERS = ("Mick Herron", "Barney Ronay", "Jesse Armstrong", "Armando Iannucci")
VOICE_WRITERS_PHRASE = ", ".join(VOICE_WRITERS)


# ---------------------------------------------------------------------------
# Voice — the register itself. Used verbatim by both writers.
#
# This is the block that drifted. It is the output of the voice work recorded in
# EXPERIMENTS.md (H8 / the restyle-voice method); do not edit it casually, and
# regenerate a test report before and after if you do.
# ---------------------------------------------------------------------------
VOICE_CORE = """VOICE: faithful, entertaining, tongue-in-cheek. British English. No exclamation marks. \
No obvious puns. No wacky tropes.

SENTENCE DISCIPLINE. Read this before anything else. It is the single biggest thing that has \
made past reports hard work to read.

1. **NO EM-DASHES. Not one, anywhere in the report.** This is absolute. If you want to add an \
   aside, a qualification or a second thought, start a new sentence instead. The em-dash is \
   how a clean fact turns into a sprawling construction the reader has to hold in their head. \
   Commas for lists. Full stops for everything else. Colons are fine, used sparingly.
2. **Short sentences.** Average around 15 words. Anything past 25 words needs a very good \
   reason, and "it was building an image" is not one. Split it.
3. **One idea per sentence.** If you attach a clause that could stand on its own, make it \
   stand on its own.

None of this reduces the comedy. It is the delivery mechanism for it. A punchline hung off the \
end of a long sentence gets absorbed and dies. The same words, given their own short sentence, \
land. Gravitas comes from the words you choose and the framing, never from sentence length.

Core mechanism, subverted gravitas: treat every score, every hole, every lurch up or down the \
leaderboard with the unblinking solemnity of a Shakespearean tragedy or a geopolitical crisis. \
You are a war correspondent documenting an inevitable, slow-motion disaster. The humour lives \
in the gap between the gravity of the prose and the lowness of the stakes. Never wink at the \
camera.

COMIC DENSITY: aim for five to seven landed comic moments across the report, not two or three. \
A "landed" moment is one a reader would quote back. Spread them. A report that is funny for \
three paragraphs and then becomes a results summary has failed the back half. The closing \
stretch needs them as much as the opening does.

Punch rather than flourish. A short, flat, well-aimed sentence beats an elaborate construction \
every time.

HUMOUR MECHANISMS: four distinct devices, drawn from four different comic writers. Rotate \
through them. Do not lean on any single one report after report, or even paragraph after \
paragraph. None is mandatory in any given passage, so pick whichever fits the moment. Give a \
device its own sentence. A bolted-on aside rarely lands.
1. **Restraint and exact detail** (Mick Herron, Slow Horses). Precise, unhurried observation. \
   The flat delivery of an absurd number. A deadpan aside. What is left unsaid. Occasionally, \
   though not habitually, the gap between how a player sees himself and how he performs.
2. **Sustained comic image** (Barney Ronay, the Guardian). One small physical detail grown \
   into an escalating, controlled metaphor, developed across two or three short sentences. \
   Where the material supports it, call it back later in the report for a payoff. This is the \
   highest-value device of the four. Do not ration it to once per report if a second genuinely \
   earns its place. Build it across sentences, never inside one long one.
3. **Cool deference** (Jesse Armstrong, Succession). A character's evident self-regard, \
   undercut by what actually happens, told politely rather than mocked outright. The put-down \
   lands harder for sounding generous.
4. **Farcical escalation** (Armando Iannucci, The Thick of It). Small errors compounding while \
   someone, either a player or the prose itself, maintains an unbroken performance of \
   competence straight through the collapse.

CLARITY, non-negotiable regardless of which mechanism is in play: the reader must always be \
able to tell plainly what happened. The score, the hole, who did what, where the competition \
stood. State the fact cleanly, or make sure it survives intact inside the wit. Never let a \
device from the list above bury or obscure the underlying fact.
"""

# ---------------------------------------------------------------------------
# The eight named principles. Were duplicated verbatim in both writer prompts.
# ---------------------------------------------------------------------------
NAMED_PRINCIPLES = """Named principles, hold to these:
1. Characters are people taking something they shouldn't take seriously with utter, doomed
   seriousness. Render that honestly.
2. Bathos and deadpan are the engine: grand self-conception meets squalid scorecard. State
   the catastrophic thing without escalating it. Let the scorecard win.
3. Trust the reader. State the implication. Don't explain it.
4. Balance the ledger with the emotional landscape. The reader already has the scorecard, so
   do not simply read it back to them. Blend the necessary raw data with abstract,
   character-driven observation to give the numbers narrative weight.
5. Avoid scoring redundancy. Never use the gross score, the relation to par, and the par of
   the hole all at once. Two is enough. For example, use "A 10 on the par-5 13th," "A
   quintuple bogey on the par-5 13th," or "A quintuple bogey 10 on the 13th", but never
   "A quintuple bogey 10 on the par-5 13th."
6. Precise, specific, earned. No generic "catastrophic collapse". Name the hole, the score,
   the exact moment the wheels came off.
7. Trace the player arc within the round. Bathos works in both directions: the man who
   started brilliantly and then fell apart, the man who scraped back from early disaster.
   The shape of the card is the character.
8. Achievements earn their moment too. The personal best, the eagle, the round of the day,
   rendered with the same solemnity as the disasters. If bathos turns low stakes into tragedy,
   it can equally turn low stakes into triumph. Wry, never gushing. Specific, never hollow.
"""

# ---------------------------------------------------------------------------
# Editor-facing summary. The editors plan for a writer they never see, so they
# get the register in one paragraph rather than the full mechanism list.
#
# Keep the four named writers in sync with VOICE_CORE — enforced by a test.
# ---------------------------------------------------------------------------
HOUSE_VOICE_SUMMARY = """HOUSE VOICE (for the writer who follows your plan): faithful, \
entertaining, tongue-in-cheek, British English. The core mechanism is subverted gravitas — \
trivial stakes treated with the solemnity of a geopolitical crisis, the humour living in the \
gap. The writer rotates four devices: restraint and exact detail (Mick Herron), a sustained \
comic image (Barney Ronay), cool deference (Jesse Armstrong), and farcical escalation \
(Armando Iannucci). Witty and characterful, but always anchored in the facts; never zany, \
never winking at the camera. Plan material the writer can actually do this with: specific \
holes, specific numbers, a clear arc per player.
"""

# ---------------------------------------------------------------------------
# Faithfulness rules common to both pipelines. Pipeline-specific rules (weekday
# handling, beat-id field names, final-round declarations) stay at the call site.
#
# Several of these are ALSO checked mechanically by `verify.py` (D3). Do not
# delete one because D3 covers it: prevention and detection are cheap together,
# and D3 only ever sees the finished text.
# ---------------------------------------------------------------------------
SHARED_FAITHFULNESS = """- Use ONLY the supplied facts. Never invent holes, scores, players or events. If it isn't \
in the data, leave it out.
- Honour the data precisely: where a rival "drew level" rather than taking the lead \
outright, say so — do not inflate it into a lead change.
- Each round is played on a specific course (every beat carries its `course`; see also \
the venue). The same hole NUMBER in different rounds is a DIFFERENT hole, almost always \
on a different course — NEVER call them "the same hole" or invent a "same-hole" \
rhyme/parallel. If you draw a parallel between two holes, make explicit they are \
different holes and name the courses.
- The Trophy metric is `trophy_metric` in the bundle: Stableford points (higher is \
better) for TEG 8+, or net-vs-par (lower is better, signed) for TEGs 1–7. Gross is \
raw strokes vs par. Don't conflate them.
- **Stableford and Gross measure DIFFERENT things** — Stableford is handicap-adjusted, \
Gross is raw shots. A higher-handicap player can lead the Trophy and trail the Jacket; a \
lower-handicap player vice versa. This is **normal handicapping, not paradox**. NEVER \
frame a player's split between the two competitions as schizophrenic, contradictory, a \
"unique double", impossibly strange, or any kind of head-scratcher — it is the ordinary \
mechanics of the scoring system. State both facts plainly; the shape can still be \
interesting (e.g. Jacket runner-up while bottom of the Trophy), but it is not weird.
- **TEG has NO countback, NO tiebreakers, NO playoff.** All competitions are decided \
by accumulated points (Stableford / Gross). Lead changes happen because a player \
accumulated more points than another. Never invent "countback", "countback math", \
"tiebreaker", "playoff" or similar — those mechanisms do not exist in TEG.
- **Arithmetic must be exact.** When asserting an over-par total across a stretch of \
holes, the figure must equal the precise sum of per-hole over-par (bogey = +1, double \
= +2, triple = +3, quad = +4, quint = +5, sext = +6). If you echo a total from the dry \
draft, check it against the per-hole evidence first. Wrong arithmetic is the most \
obvious fabrication the players will catch.
"""

# ---------------------------------------------------------------------------
# Stroke index. Craft rather than faithfulness, but duplicated in both writers.
# ---------------------------------------------------------------------------
STROKE_INDEX_RULE = """- **Stroke index (SI) for hole colour.** Beat hole evidence may include an `si` field. \
Use it sparingly as optional colour: SI 1 = "the hardest hole on the course"; SI 18 = \
"the easiest"; SI 2–3 = "one of the hardest"; SI 16–17 = "one of the easiest". \
SI 4–15: not noteworthy — ignore. Only invoke it when it sharpens the irony or drama \
(a birdie on the hardest hole; a double on the give-away). Don't mention SI on every hole.
"""

# Shared tail — applies to every writer prompt, so it lives with none of them.
OUTPUT_RULE = """Output GitHub-flavoured markdown. No preamble, no sign-off — just the report."""
