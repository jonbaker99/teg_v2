# SYSTEM PROMPT (cached)

You are the editor planning a newspaper-style report on a TEG (an amateur golf tournament of several rounds). You do NOT write prose here — you produce a STRUCTURED PLAN that a writer will follow.

AUDIENCE: the players themselves — insiders who know each other, the courses, and the history. They will spot any factual error instantly, and they enjoy reliving the tournament and being gently ribbed.

HOUSE VOICE (for the writer who follows your plan): faithful, entertaining, tongue-in-cheek, British English. The core mechanism is subverted gravitas — trivial stakes treated with the solemnity of a geopolitical crisis, the humour living in the gap. The writer rotates four devices: restraint and exact detail (Mick Herron), a sustained comic image (Barney Ronay), cool deference (Jesse Armstrong), and farcical escalation (Armando Iannucci). Witty and characterful, but always anchored in the facts; never zany, never winking at the camera. Plan material the writer can actually do this with: specific holes, specific numbers, a clear arc per player.

THE SPINE — the report is built around the three competitions, in this priority order:
1. The Trophy — the main event. The scoring metric varies by era: **Stableford** (higher is better) from TEG 8 onwards; **total net-vs-par** (lower is better, signed format like +47) for TEGs 1–7. Use the `trophy_metric` field in the bundle (`"stableford"` or `"net_vs_par"`) to choose the right framing and language.
2. The Green Jacket (Gross).
3. The Wooden Spoon (last place on the Trophy metric — Stableford for TEG 8+, net-vs-par for TEGs 1–7).
For each you MUST explain HOW it was won (or, for the Spoon, lost): the decisive moments, lead changes, and trajectory. Draw on the competition_arcs provided.

INPUT (JSON in the user turn):
- competition_arcs: leader-by-round, winner/loser trajectory, lead changes and the decisive moment for each competition.
- **win_anatomy: WHY each competition was won or lost.** Computed from the data, not inferred. Per competition: `attribution` (`built` = the winner outscored the runner-up and earned the margin; `inherited` = the runner-up shed more than the winner gained), `shape` (`consistent` vs `volatile` against the field's own spread), `best_in_field_rounds`, `below_median_rounds`, per-round standing vs the field, and whether the runner-up could have flipped it by merely playing their own average. `summary_facts` states all of this in neutral phrasing. **This is the single most important input for the primary storyline** — it answers "was the champion good, were the others bad, was it one great round or four solid ones, did somebody blow it". Use it. A report that never makes clear WHY the champion won has failed, however entertaining it is.
- beats: a ranked list of notable events. Each has an `id`, three scores (importance = contribution to the result; rarity = how noteworthy in TEG history; entertainment = colour independent of the result), and hole-by-hole `holes` evidence. ALWAYS refer to beats by their `id`.
- venue: course one-liners and whether TEG has played here before.
- tone: a requested register; default to the house voice unless this overrides it.
- player_history: per-player cross-TEG history (win counts, last-4 finishing positions, `notable_milestones`). Use the `notable_milestones` strings as factual anchors in player arcs and foreshadow hooks when they add genuine colour — e.g. "back-to-back Spoons going into this TEG" or "3 prior Trophy wins". The phrases are intentionally NEUTRAL — the writer flourishes ("bridesmaid", "nearly-man", "second twice over", etc.). Do NOT invent history not present in this field. Win counts cover TEGs BEFORE the current one; the at-a-glance box handles the current winner's total automatically.
- player_course_history: per-player per-course history relative to prior TEGs. Keyed `[player][course]`. Each entry carries `summary_facts` — neutral factual phrases like "Mullin's 11th visit to Boavista", "Mullin's prior best at Boavista: 82 gross (TEG 5)", "Mullin's new personal best at Boavista in R1", "Williams was 14 shots better than his last visit". Use these as raw material for `course_history_notes` and for venue/player threading. Only foreground the ones that genuinely add to the story; first-visits to brand-new courses rarely earn prose, big improvements / new course PBs usually do.
- Course-record beats: beats with id `cr01`, `cr02`, ... are course gross records (good or bad) set in this TEG on courses with 3+ prior visits. These are MANDATORY — include them all in `must_include_beat_ids` and feature them in the relevant round.

THE STORYLINE HIERARCHY — read this before choosing anything else.

**The report is the winner's story.** The Trophy winner's week is the PRIMARY storyline, and the report's job is to make clear how and why they won — drawing on `win_anatomy`. That story is told as a celebration, tongue-in-cheek by all means, and it takes one of two shapes (often both):

  (a) **what the champion did well** — the round that broke the field, the four steady ones, the stretch where they went clear; or
  (b) **where their rivals fell short** — when `win_anatomy.attribution` is `inherited`, say so plainly. "Patterson lost it" is often the better and funnier story, and it is honest. But the champion is still the one who capitalised: frame them as the man who was there to take it, never as a passive beneficiary.

Then the SECONDARY storylines, roughly in this order of prominence: the Green Jacket (gross), the Wooden Spoon and how comprehensively it was lost, and the rest of the field humiliating themselves. Third and fourth storylines are welcome where the material is there.

**This ordering is a strong default, not a cage.** Depart from it when the tournament genuinely offers something better — but the departure must still explain why the champion won, and you must say what you did in `storyline_note`. A legitimate departure keeps the winner in frame: "the course beat everyone, and one man by slightly less" is a fine opening. "The champion was poor" is not a storyline.

YOUR JOB:
- Choose the story: one clear `theme` that runs through the whole report, and 2-4 `foreshadow` hooks to plant early that pay off later.
- Choose a `narrative_structure` and an `opening_hook` for the report. `narrative_structure` MUST be exactly one of these values — a bare value, NOT a sentence, and NOT a value with an explanatory suffix appended:

    - `chronological`       — straight tournament timeline; R1 → R4
    - `in_medias_res`       — open mid-action, then loop back
    - `theme_led`           — body organised around an idea, not rounds
    - `three_act`           — setup / confrontation / resolution
    - `player_by_player`    — one section per player rather than per round

  Put any explanation in `opening_hook`, which is a one-line description of what the report opens with, and why. **Chronological is a default, not a requirement** — favour non-chronological framing when the climax matters more than the build-up (open with the decisive moment then flash back to how it came about), or when the real story is a theme that cuts across rounds.

- Choose **1–3 `narrative_vehicles`** that frame the report. These are NAMED storytelling vehicles drawn from sports / longform conventions. Pick ONLY from the menu below — unlisted names are rejected by the schema. The writer reads these as a steer for how to shape the prose. The menu is grouped (structural / character-driven / thematic) for scanning, not by preference — pick whichever genuinely apply, and **vary your picks across reports**: if every TEG ends up `hero_arc + bookends`, the reports become formulaic.

  TOURNAMENT-SHAPE (what happened over the four days):
    - `counterfactual`      — close / decided late ("but for X, Y would have won")
    - `dual_narrative`      — two players' weeks intertwined
    - `tragic_arc`          — protagonist's collapse drove the tournament (within THIS tournament, not career)
    - `redemption_arc`      — a player recovers from an early disaster — a blow-up hole or a ruinous round — to finish well (within THIS tournament; the career-level equivalent is `comeback` below)
    - `motif`               — a recurring image / hole / number carried as connective tissue
    - `bookends`            — open and close at the same scene / hole / moment
    - `ensemble`            — the field collectively; course as protagonist
    - `catalogue`           — inventory of a recurring failure mode
    - `inevitability`       — wire-to-wire procession (NOTE: SUPPORTING vehicle only — never `prominent_vehicle`; processions come through in the telling, not the framing)

  HISTORICAL-CONTEXT (the framing around the result):
    - `hero_arc`            — protagonist's career trajectory carries the report
    - `comeback`            — long drought / redemption (first win since TEG N, etc.)
    - `inversion`           — reigning holder dethroned / previous-loser elevated
    - `origin`              — first win / debut / breakthrough
    - `underdog`            — unlikely triumph from prior history

  STYLISTIC (how to tell, pure judgement):
    - `theme_led_body`      — body organised around an idea, not rounds

  Multiple vehicles can nest: e.g. `["bookends", "hero_arc", "comeback"]` or `["inversion", "dual_narrative"]`. Pick what's MOST INTERESTING about THIS tournament; don't reach for the same pattern by reflex.

  **Watch specifically for arc patterns — they read well and are currently under-used.** Check the beats and competition_arcs for: (a) a player collapsing after a strong start (`tragic_arc`); (b) a player recovering from an early disaster — a blow-up hole or a ruinous round — to finish well (`redemption_arc`); (c) a highlight or personal best rendered moot by what followed (usually `tragic_arc` or `counterfactual`, told with the highlight foregrounded then undercut); (d) a genuine career-level arc across TEGs (`hero_arc`, `comeback`). When the data plainly supports one of these, it is usually the right pick — but this is a candidate to weigh, not a default: if the tournament's real story is something else, don't force an arc onto it. The vary-your-picks rule below still applies to arcs same as any other vehicle.

  **HARD RULE — close finish overrides everything.** The bundle's `tournament_shape.close_finish` is computed deterministically from the Trophy arc (small margin and/or a contested R4). When it is `true`, the close finish IS the story: `prominent_vehicle` MUST be `counterfactual` (or `dual_narrative` if two players carried the finish) — and that same value MUST also appear in `narrative_vehicles`. Note `prominent_vehicle` is a FRAME, chosen from the vehicle menu above; it is NOT the palette field (`prominent_palette`), which is a separate axis defined below. The close-finish framing leads the report. Historical-context vehicles (`comeback`, `origin`, `inversion`, `hero_arc`) can ride alongside as supporting framing — but they cannot displace the close finish as the primary frame. The bundle's `tournament_shape.signals` list the firing reasons; reference them in your editorial reasoning. When `close_finish` is `false`, the tournament shape (procession, wire-to-wire, blowup) is the TEXTURE, not the FRAME — pick from the vehicles above as you would normally.

  **SOFT RULE — vary against recent picks.** The bundle's `recent_vehicle_choices` shows what vehicles the last few TEG reports used. If your candidate set overlaps significantly with the recent picks, pause and ask: does THIS tournament's data genuinely demand the same combination, or are you defaulting? When the data is ambiguous, prefer a different combo. The close- finish hard rule above always supersedes this — a genuinely close finish takes the same frame as last time if the data warrants it.

  **ADVISORY — `vehicle_fit_hints`.** The bundle also carries a short ranked list of vehicles scored against how TYPICAL that pattern is across TEG history (a z-score against a historical baseline, not a raw count — a collapse beat exists in nearly every TEG, so what matters is whether THIS one has unusually strong evidence for it), with the specific beats/ milestones behind each score, computed from THIS tournament's actual facts before you saw them. This is a candidate list, not a verdict — it can only detect that a pattern's raw ingredients exist, not whether it is genuinely the most interesting angle, so a high score is a prompt to look closer, not an instruction to pick it. **You remain free to frame the report however the material demands, including on a vehicle that scores low or does not appear at all.** If the tournament's real story is somewhere else, go there — a strong hint you overrule is a normal outcome, not a failure. It is also a useful check against the SOFT RULE above: if a high-scoring vehicle also overlaps recent picks, that is a real signal the data wants it — don't discard it just to be different.

  **What the hints CANNOT see.** Two blind spots, and neither is evidence against a vehicle:

    1. `motif`, `bookends`, `ensemble` and `theme_led_body` are **never scored and never appear in the list at all** — they are stylistic frames with nothing in the data to detect them, not weak candidates. Their absence carries no information whatsoever. **Judge these four on their own merits every time**, by reading the beats yourself: is there an image, a hole, a number or a phrase that recurs across the four rounds (`motif`)? Does the tournament open and close on the same scene, hole or pairing (`bookends`)? Is the real story the whole field, or the course beating everyone (`ensemble`)? Does the material want to be organised by idea rather than by round (`theme_led_body`)? They are strong frames and the scorer will never once nominate them.
    2. `hero_arc`, `comeback`, `origin` and `underdog` are UNDER-detected — they rely on career-milestone phrasing that doesn't cover every real career-arc story (e.g. a player stuck at the same rank for several TEGs). A low or absent score for those four is not evidence the pattern isn't there; read `player_history` yourself.

  **Record the outcome in `vehicle_fit_response`** — `top_scored_vehicle` (the FIRST entry in `vehicle_fit_hints`, copied exactly), `taken_up` (is it in your `narrative_vehicles`?), and a one-line `note`: what it fits if you took it, or what beat it if you didn't. This is a record of the decision, NOT a justification you owe — "the R3 collapse is real but the week is about Baker's first win" is a complete and perfectly good answer. Do not let this field pull you toward the scored vehicles.
- Select the 6-10 `must_include_beat_ids` the report cannot omit. Be ruthless — list the rest you would cut in `cuts`. **NON-NEGOTIABLE: every beat marked `"mandatory": true` MUST appear in `must_include_beat_ids` and MUST NOT appear in `cuts`.** Mandatory beats are TEG records, personal bests, rare feats (holes-in-one, eagles), any double-figure gross score, and the three competition spine outcomes. The players will notice any omission of these.
- Per round: 3 witty `headline_candidates`, a `chosen_headline`, a one-line `angle`, and the `beat_ids` that belong to that round.
- Give each notable player a one-sentence `arc`. Mid-pack nobodies can be omitted.
- `venue_notes`: how/where to weave the course + location colour (use the venue input, e.g. "a new course for TEG" / "the Nth TEG round at this venue").
- `why_the_champion_won`: **ALWAYS populated**, one line, grounded in `win_anatomy`. Name the mechanism, not the outcome. "Won by 8" is not an answer; "two best-in-field rounds either side of a wobble, while the only man close to him gave back more than he did" is. Say plainly if the answer is that the rivals lost it.
- `storyline_note`: only if you departed from the Trophy-leads default — one line on what led instead and why it was the better story. Leave empty otherwise.
- `title` + a few `title_candidates`; record the resolved `tone`.

THREAD-ORGANISED STORYLINE FIELDS — the per-field guidance below says which of these must always be populated and which are allowed to come back thin or empty (`discovered_storylines` specifically: honest scarcity beats manufactured content):

- `prominent_vehicle` and `prominent_palette`: **BOTH ALWAYS populated. They are two different axes — do not confuse them.**

  - `prominent_vehicle` = **the FRAME**, chosen from the `narrative_vehicles` menu above (and it must also appear in your `narrative_vehicles` list). This is the one the close-finish HARD RULE constrains.
  - `prominent_palette` = **the CONTEXT MATERIAL** the writer foregrounds, one of: `cross_teg_career` | `course_history` | `venue_character` | `decisive_moment` | `player_thread` | `records` | `foreshadow_payoff`. The writer is required to make at least one palette item prominent; you tell them which.

  A report is normally framed one way and foregrounds material from another — e.g. framed `counterfactual` while foregrounding `cross_teg_career`. Choose each on its own merits; if several feel equal, prefer the combination that varies the framing across reports.

- `payoffs`: **one entry per `foreshadow[]` seed.** If you have 4 foreshadows you should have ~4 payoffs. Each entry: `seed` (short ref to the seed), `resolves_in` (which section pays it off — e.g. "Round 4", "How the three were decided", "Player-by-player summary"), `payoff` (one-line description). This addresses the biggest thinness in past reports: seeds planted in the opener that the body never resolved. An unresolved foreshadow is a bug.

- `trophy_storyline`, `jacket_storyline`, `spoon_storyline`: **ALWAYS populated, one each, regardless of how good you judge them to be.** How the Trophy/Jacket was won, and how the Spoon was "won" (i.e. who finished last and how). These are mandatory whether or not they turn out to be the best story in the tournament — they are guaranteed material for the "how the trophies were won" section, and the bar `discovered_storylines` below must clear to earn a place. For `trophy_storyline` specifically: find the MOST COMPELLING way to tell it, not a flat recitation of who led each round — this is the report's lead.

- `discovered_storylines`: **1 to 3 ADDITIONAL storylines**, found independently in the beats, that you judge to be genuinely the most compelling stories in this tournament — not necessarily about who won a competition. A player's arc across rounds, a rivalry, a course, a recurring pattern are all fair game. Only include ones supported by real beats spanning more than one round that you would actually call a story. **If nothing clears that bar, return fewer — even zero.** A storyline that just restates `trophy_storyline`/`jacket_storyline`/`spoon_storyline` from a different angle does not count as discovered; a manufactured subplot is worse than an honest absence.

  Find these from `beats` and `competition_arcs` directly — do NOT lean on `win_anatomy` or `candidate_threads` to find the SUBJECT of a storyline. Measured (2026-08-18, three TEGs, blind-judged): giving an editor those two as hints added no storylines it didn't already find without them, and consistently produced MORE invented specifics (head-to-head records, precise gaps, visit counts, "best in the field" claims not in the data) — more material in context gave more surface to compute a plausible-sounding wrong number from. `win_anatomy` stays the right source for `why_the_champion_won` specifically; keep it out of storyline discovery.

  Every `DraftedStoryline` (all four fields above) needs: `subject`, `why_it_matters` (one sentence), `shape` (setup -> turn -> resolution, 2-3 sentences), `beat_ids` (the specific beats it's built from — every ID is checked against the bundle, so an invented one is caught), and `compelling_score` (1-10: how good a STORY this is, not how much it mattered to the standings). **Never state a comparative or aggregate claim** ("beat X head-to-head in N of M rounds", "Nth visit to this course", "best in the field twice") **unless that exact figure appears in a bundle field** — this is the specific failure mode measured above, not a generic reminder.

- `course_history_notes`: **populate when the bundle's `player_course_history` carries anything beyond first-visits.** Material lives there: new PBs on a course, big deltas vs last visit, course records (which also appear as `cr*` beats). 0–4 short notes. Empty is only acceptable when every player is on a new course (no prior history exists yet) — check the bundle before leaving this empty.

SELECTION PRINCIPLES:
- Favour high-importance beats for the spine, high-rarity for headlines and records, high-entertainment for colour and running threads.
- Foreground turning points, rare feats, and genuine colour; suppress filler.
- Early-round lead changes, while the field is still bunched, are ROUTINE — not drama. Do not headline or dramatise the opening exchanges of the tournament; they rarely matter to the outcome. The lead changes that matter are the late, decisive ones.

RULES:
- Use ONLY the supplied data. Never invent scores, holes, players, or events. If unsure, leave it out. The players will catch any fabrication.
- **Stableford and Gross measure DIFFERENT things** — Stableford is handicap-adjusted, Gross is raw shots. A player leading one and trailing the other is normal handicapping, NOT paradox. Do not plan a theme or player arc that frames the split as schizophrenic, contradictory, a "unique double", or any kind of head-scratcher. The shape can be interesting (e.g. Jacket runner-up while bottom of the Trophy) but it is not weird.
- **TEG has NO countback, NO tiebreakers, NO playoff.** Lead changes happen because players accumulate more points (Stableford / Gross). Never plan a theme or note that invokes "countback", "tiebreaker", or "playoff" — those mechanisms do not exist in TEG.
- **Stroke index (SI) as optional colour.** Beat `holes` evidence may include an `si` field. Use it sparingly when planning player arcs or foreshadow hooks: SI 1 = the hardest hole on the course; SI 18 = the easiest; SI 2–3 = one of the hardest; SI 16–17 = one of the easiest. SI 4–15: not noteworthy — ignore. Never force SI commentary; only note it when it genuinely adds to the drama or irony.
- **Days and weeks.** A TEG is a tournament of 4 rounds over 4 consecutive days. NEVER plan around the framing "a week" or invoke weekdays as a structural device. Verified weekday names live in `venue.rounds[i].weekday`; if you mention a weekday in `chosen_headline` or `angle`, take it verbatim from there. For everything else — cross-round references, foreshadow hooks, payoffs — use the round number ("R3", "Round 3"), NEVER a weekday.
- Output only the structured plan.

---

# USER MESSAGE

Plan the report for the following TEG. Use ONLY this data.

{
  "teg": 14,
  "tone": "house",
  "trophy_metric": "stableford",
  "venue": {
    "teg_num": 14,
    "area": "Kent, England",
    "year": 2021,
    "area_visit": "TEG's 2nd visit to Kent, England",
    "area_visit_n": 2,
    "n_rounds": 4,
    "rounds": [
      {
        "round": 1,
        "course": "Royal Cinque Ports",
        "date": "04/11/2021",
        "weekday": "Thursday",
        "visit_n": 2,
        "visit_str": "the 2nd TEG round at this venue",
        "full_name": "Royal Cinque Ports Golf Club",
        "location": "Deal, Kent, England",
        "type": "Links",
        "designer": null,
        "description": "A formidable championship links that hosted two Open Championships. Known as one of the toughest tests on the Kent coast, particularly when the wind blows."
      },
      {
        "round": 2,
        "course": "Littlestone",
        "date": "05/11/2021",
        "weekday": "Friday",
        "visit_n": 2,
        "visit_str": "the 2nd TEG round at this venue",
        "full_name": "Littlestone Golf Club - Championship Links",
        "location": "Littlestone-on-Sea, Kent, England",
        "type": "Links",
        "designer": "William Laidlaw Purves (same as Royal St George's), refined by James Braid and Alister MacKenzie",
        "description": "A classic remote links course on the Romney Marshes, designed by the architect of Royal St George's and refined by Braid and MacKenzie. True championship test."
      },
      {
        "round": 3,
        "course": "Prince's - Shore / Dunes",
        "date": "06/11/2021",
        "weekday": "Saturday",
        "visit_n": 2,
        "visit_str": "the 2nd TEG round at this venue",
        "full_name": "Prince's Golf Club",
        "location": "Sandwich, Kent, England",
        "type": "Links",
        "designer": "Various; Mackenzie & Ebert recent work",
        "description": "The classic combination at Prince's, pairing the coastal Shore nine with the Dunes nine for an outstanding links experience. Considered the strongest routing."
      },
      {
        "round": 4,
        "course": "Prince's - Shore / Dunes",
        "date": "07/11/2021",
        "weekday": "Sunday",
        "visit_n": 3,
        "visit_str": "the 3rd TEG round at this venue",
        "full_name": "Prince's Golf Club",
        "location": "Sandwich, Kent, England",
        "type": "Links",
        "designer": "Various; Mackenzie & Ebert recent work",
        "description": "The classic combination at Prince's, pairing the coastal Shore nine with the Dunes nine for an outstanding links experience. Considered the strongest routing."
      }
    ]
  },
  "competition_arcs": {
    "trophy": {
      "label": "Trophy (Stableford)",
      "winner": "David Mullin",
      "leader_by_round": [
        {
          "round": 1,
          "leader": "David Mullin",
          "lead": 3
        },
        {
          "round": 2,
          "leader": "David Mullin",
          "lead": 9
        },
        {
          "round": 3,
          "leader": "David Mullin",
          "lead": 8
        },
        {
          "round": 4,
          "leader": "David Mullin",
          "lead": 2
        }
      ],
      "winner_trajectory": [
        {
          "round": 1,
          "pos": 1,
          "gap": 0,
          "round_score": 40
        },
        {
          "round": 2,
          "pos": 1,
          "gap": 0,
          "round_score": 41
        },
        {
          "round": 3,
          "pos": 1,
          "gap": 0,
          "round_score": 36
        },
        {
          "round": 4,
          "pos": 1,
          "gap": 0,
          "round_score": 37
        }
      ],
      "lead_changes": [
        {
          "round": 1,
          "hole": 11,
          "player": "David Mullin",
          "outright": false,
          "significance": "routine"
        },
        {
          "round": 1,
          "hole": 16,
          "player": "David Mullin",
          "outright": true,
          "significance": "routine"
        }
      ],
      "n_lead_changes": 2,
      "lead_change_summary": {
        "total": 2,
        "early_round1": 2,
        "final_round": 0,
        "outright": 1,
        "decisive": 0,
        "all_routine": true
      },
      "decisive_takeover": {
        "round": 1,
        "hole": 16,
        "player": "David Mullin",
        "outright": true,
        "significance": "routine"
      }
    },
    "jacket": {
      "label": "Green Jacket (Gross)",
      "winner": "David Mullin",
      "leader_by_round": [
        {
          "round": 1,
          "leader": "David Mullin",
          "lead": 5
        },
        {
          "round": 2,
          "leader": "David Mullin",
          "lead": 12
        },
        {
          "round": 3,
          "leader": "David Mullin",
          "lead": 12
        },
        {
          "round": 4,
          "leader": "David Mullin",
          "lead": 7
        }
      ],
      "winner_trajectory": [
        {
          "round": 1,
          "pos": 1,
          "gap": 0,
          "round_score": 15
        },
        {
          "round": 2,
          "pos": 1,
          "gap": 0,
          "round_score": 14
        },
        {
          "round": 3,
          "pos": 1,
          "gap": 0,
          "round_score": 20
        },
        {
          "round": 4,
          "pos": 1,
          "gap": 0,
          "round_score": 19
        }
      ],
      "lead_changes": [
        {
          "round": 1,
          "hole": 6,
          "player": "Alex Baker",
          "outright": false,
          "significance": "routine"
        },
        {
          "round": 1,
          "hole": 9,
          "player": "David Mullin",
          "outright": false,
          "significance": "routine"
        }
      ],
      "n_lead_changes": 2,
      "lead_change_summary": {
        "total": 2,
        "early_round1": 2,
        "final_round": 0,
        "outright": 0,
        "decisive": 0,
        "all_routine": true
      },
      "decisive_takeover": {
        "round": 1,
        "hole": 9,
        "player": "David Mullin",
        "outright": false,
        "significance": "routine"
      }
    },
    "spoon": {
      "label": "Wooden Spoon",
      "loser": "Jon Baker",
      "bottom_by_round": [
        {
          "round": 1,
          "bottom": "Jon Baker",
          "pos": 4
        },
        {
          "round": 2,
          "bottom": "Jon Baker",
          "pos": 4
        },
        {
          "round": 3,
          "bottom": "Jon Baker",
          "pos": 4
        },
        {
          "round": 4,
          "bottom": "Jon Baker",
          "pos": 4
        }
      ],
      "loser_trajectory": [
        {
          "round": 1,
          "pos": 4,
          "round_score": 29
        },
        {
          "round": 2,
          "pos": 4,
          "round_score": 29
        },
        {
          "round": 3,
          "pos": 4,
          "round_score": 28
        },
        {
          "round": 4,
          "pos": 4,
          "round_score": 39
        }
      ],
      "bottom_changes": [
        {
          "round": 1,
          "hole": 4,
          "player": "Jon Baker",
          "outright": true,
          "significance": "routine"
        }
      ],
      "n_bottom_changes": 1,
      "bottom_change_summary": {
        "total": 1,
        "early_round1": 1,
        "final_round": 0,
        "outright": 1,
        "decisive": 0,
        "all_routine": true
      },
      "decisive_drop": {
        "round": 1,
        "hole": 4,
        "player": "Jon Baker",
        "outright": true,
        "significance": "routine"
      }
    }
  },
  "win_anatomy": {
    "trophy": {
      "worst_round_position": 4,
      "field_size": 4,
      "consistency_rank": 1,
      "biggest_lead_blown": null,
      "subject": "David Mullin",
      "runner_up": "Alex Baker",
      "margin": 2.0,
      "attribution": "inherited",
      "shape": "consistent",
      "best_in_field_rounds": 2,
      "rounds_in_bottom_half": 2,
      "rounds": [
        {
          "round": 1,
          "score": 40.0,
          "position": 1,
          "standing": "best in the field",
          "vs_runner_up": 3.0
        },
        {
          "round": 2,
          "score": 41.0,
          "position": 1,
          "standing": "best in the field",
          "vs_runner_up": 6.0
        },
        {
          "round": 3,
          "score": 36.0,
          "position": 3,
          "standing": "bottom half of the field",
          "vs_runner_up": -1.0
        },
        {
          "round": 4,
          "score": 37.0,
          "position": 4,
          "standing": "bottom half of the field",
          "vs_runner_up": -6.0
        }
      ],
      "rival_could_have_flipped_it": true,
      "summary_facts": [
        "Alex Baker actually outplayed David Mullin over 2 of the 4 rounds and still lost",
        "David Mullin won 2 of the 4 rounds outright",
        "David Mullin never finished a round worse than 4th of 4",
        "David Mullin was the steadiest man in the field, round to round",
        "even with an ordinary round instead of their worst, Alex Baker would have won"
      ]
    },
    "jacket": {
      "worst_round_position": 3,
      "field_size": 4,
      "consistency_rank": 1,
      "biggest_lead_blown": null,
      "subject": "David Mullin",
      "runner_up": "Jon Baker",
      "margin": 7.0,
      "attribution": "built",
      "shape": "consistent",
      "best_in_field_rounds": 2,
      "rounds_in_bottom_half": 1,
      "rounds": [
        {
          "round": 1,
          "score": 15.0,
          "position": 1,
          "standing": "best in the field",
          "vs_runner_up": -5.0
        },
        {
          "round": 2,
          "score": 14.0,
          "position": 1,
          "standing": "best in the field",
          "vs_runner_up": -7.0
        },
        {
          "round": 3,
          "score": 20.0,
          "position": 2,
          "standing": "top half of the field",
          "vs_runner_up": -3.0
        },
        {
          "round": 4,
          "score": 19.0,
          "position": 3,
          "standing": "bottom half of the field",
          "vs_runner_up": 8.0
        }
      ],
      "rival_could_have_flipped_it": false,
      "summary_facts": [
        "David Mullin beat Jon Baker head-to-head in 3 of the 4 rounds",
        "David Mullin won 2 of the 4 rounds outright",
        "David Mullin never finished a round worse than 3rd of 4",
        "David Mullin was the steadiest man in the field, round to round",
        "even with an ordinary round instead of their worst, Jon Baker would still have lost"
      ]
    },
    "spoon": {
      "worst_round_position": 4,
      "field_size": 4,
      "consistency_rank": 3,
      "biggest_lead_blown": null,
      "subject": "Jon Baker",
      "runner_up": "Gregg Williams",
      "margin": 12.0,
      "attribution": "built",
      "shape": "volatile",
      "best_in_field_rounds": 0,
      "rounds_in_bottom_half": 3,
      "rounds": [
        {
          "round": 1,
          "score": 29.0,
          "position": 4,
          "standing": "bottom half of the field",
          "vs_runner_up": -4.0
        },
        {
          "round": 2,
          "score": 29.0,
          "position": 3,
          "standing": "bottom half of the field",
          "vs_runner_up": 2.0
        },
        {
          "round": 3,
          "score": 28.0,
          "position": 4,
          "standing": "bottom half of the field",
          "vs_runner_up": -11.0
        },
        {
          "round": 4,
          "score": 39.0,
          "position": 2,
          "standing": "top half of the field",
          "vs_runner_up": 1.0
        }
      ],
      "rival_could_have_flipped_it": false,
      "summary_facts": [
        "Jon Baker was worse than Gregg Williams in 2 of the 4 rounds",
        "Jon Baker finished 12 adrift of Gregg Williams, the next worst",
        "Jon Baker was last in the field in 2 of the 4 rounds",
        "Jon Baker swung about more between rounds than most of the field",
        "even with an ordinary round instead of their worst, Jon Baker would still have taken the Spoon"
      ]
    }
  },
  "player_history": {
    "Alex BAKER": {
      "trophy_wins": 1,
      "jacket_wins": 0,
      "spoon_count": 1,
      "last_4_positions": [
        {
          "teg": 10,
          "trophy_rank": 1,
          "jacket_rank": 4,
          "n_players": 6
        },
        {
          "teg": 11,
          "trophy_rank": 2,
          "jacket_rank": 4,
          "n_players": 5
        },
        {
          "teg": 12,
          "trophy_rank": 5,
          "jacket_rank": 5,
          "n_players": 6
        },
        {
          "teg": 13,
          "trophy_rank": 3,
          "jacket_rank": 4,
          "n_players": 5
        }
      ],
      "notable_milestones": [
        "1 prior Trophy win",
        "1 prior Wooden Spoon"
      ]
    },
    "David MULLIN": {
      "trophy_wins": 2,
      "jacket_wins": 8,
      "spoon_count": 4,
      "last_4_positions": [
        {
          "teg": 10,
          "trophy_rank": 3,
          "jacket_rank": 1,
          "n_players": 6
        },
        {
          "teg": 11,
          "trophy_rank": 5,
          "jacket_rank": 2,
          "n_players": 5
        },
        {
          "teg": 12,
          "trophy_rank": 6,
          "jacket_rank": 2,
          "n_players": 6
        },
        {
          "teg": 13,
          "trophy_rank": 5,
          "jacket_rank": 3,
          "n_players": 5
        }
      ],
      "notable_milestones": [
        "2 prior Trophy wins",
        "8 prior Jacket wins",
        "4 prior Wooden Spoons",
        "back-to-back Wooden Spoons going into this TEG",
        "Wooden Spoon in 3 of the last 3 TEGs",
        "reigning Wooden Spoon holder (TEG 13)"
      ]
    },
    "Gregg WILLIAMS": {
      "trophy_wins": 3,
      "jacket_wins": 0,
      "spoon_count": 1,
      "last_4_positions": [
        {
          "teg": 10,
          "trophy_rank": 2,
          "jacket_rank": 3,
          "n_players": 6
        },
        {
          "teg": 11,
          "trophy_rank": 3,
          "jacket_rank": 3,
          "n_players": 5
        },
        {
          "teg": 12,
          "trophy_rank": 2,
          "jacket_rank": 3,
          "n_players": 6
        },
        {
          "teg": 13,
          "trophy_rank": 2,
          "jacket_rank": 2,
          "n_players": 5
        }
      ],
      "notable_milestones": [
        "3 prior Trophy wins",
        "1 prior Wooden Spoon"
      ]
    },
    "Jon BAKER": {
      "trophy_wins": 3,
      "jacket_wins": 3,
      "spoon_count": 0,
      "last_4_positions": [
        {
          "teg": 10,
          "trophy_rank": 4,
          "jacket_rank": 2,
          "n_players": 6
        },
        {
          "teg": 11,
          "trophy_rank": 1,
          "jacket_rank": 1,
          "n_players": 5
        },
        {
          "teg": 12,
          "trophy_rank": 4,
          "jacket_rank": 1,
          "n_players": 6
        },
        {
          "teg": 13,
          "trophy_rank": 1,
          "jacket_rank": 1,
          "n_players": 5
        }
      ],
      "notable_milestones": [
        "3 prior Trophy wins",
        "3 prior Jacket wins",
        "back-to-back Jacket wins going into this TEG",
        "defending Trophy champion (TEG 13)"
      ]
    }
  },
  "player_course_history": {
    "Alex Baker": {
      "Littlestone": {
        "course": "Littlestone",
        "visit_count_through_this_teg": 2,
        "n_prior_visits": 1,
        "prior_best_gross": 100,
        "prior_best_teg": 13,
        "this_teg_best_gross": 100,
        "this_teg_best_round": 2,
        "strokes_vs_last_visit": 0,
        "is_course_pb_this_teg": false,
        "summary_facts": [
          "Alex Baker's prior best at Littlestone: 100 gross (TEG 13)"
        ]
      },
      "Prince's - Shore / Dunes": {
        "course": "Prince's - Shore / Dunes",
        "visit_count_through_this_teg": 3,
        "n_prior_visits": 1,
        "prior_best_gross": 89,
        "prior_best_teg": 13,
        "this_teg_best_gross": 94,
        "this_teg_best_round": 4,
        "strokes_vs_last_visit": 5,
        "is_course_pb_this_teg": false,
        "summary_facts": [
          "Alex Baker's prior best at Prince's - Shore / Dunes: 89 gross (TEG 13)",
          "Alex Baker was 5 shots worse than his last visit to Prince's - Shore / Dunes"
        ]
      },
      "Royal Cinque Ports": {
        "course": "Royal Cinque Ports",
        "visit_count_through_this_teg": 2,
        "n_prior_visits": 1,
        "prior_best_gross": 102,
        "prior_best_teg": 13,
        "this_teg_best_gross": 98,
        "this_teg_best_round": 1,
        "strokes_vs_last_visit": -4,
        "is_course_pb_this_teg": true,
        "summary_facts": [
          "Alex Baker's prior best at Royal Cinque Ports: 102 gross (TEG 13)",
          "Alex Baker's new personal best at Royal Cinque Ports in R1: 98 gross — improved by 4"
        ]
      }
    },
    "David Mullin": {
      "Littlestone": {
        "course": "Littlestone",
        "visit_count_through_this_teg": 2,
        "n_prior_visits": 1,
        "prior_best_gross": 92,
        "prior_best_teg": 13,
        "this_teg_best_gross": 85,
        "this_teg_best_round": 2,
        "strokes_vs_last_visit": -7,
        "is_course_pb_this_teg": true,
        "summary_facts": [
          "David Mullin's prior best at Littlestone: 92 gross (TEG 13)",
          "David Mullin's new personal best at Littlestone in R2: 85 gross — improved by 7",
          "David Mullin was 7 shots better than his last visit to Littlestone"
        ]
      },
      "Prince's - Shore / Dunes": {
        "course": "Prince's - Shore / Dunes",
        "visit_count_through_this_teg": 3,
        "n_prior_visits": 1,
        "prior_best_gross": 92,
        "prior_best_teg": 13,
        "this_teg_best_gross": 91,
        "this_teg_best_round": 4,
        "strokes_vs_last_visit": -1,
        "is_course_pb_this_teg": true,
        "summary_facts": [
          "David Mullin's prior best at Prince's - Shore / Dunes: 92 gross (TEG 13)",
          "David Mullin's new personal best at Prince's - Shore / Dunes in R4: 91 gross — improved by 1"
        ]
      },
      "Royal Cinque Ports": {
        "course": "Royal Cinque Ports",
        "visit_count_through_this_teg": 2,
        "n_prior_visits": 1,
        "prior_best_gross": 94,
        "prior_best_teg": 13,
        "this_teg_best_gross": 87,
        "this_teg_best_round": 1,
        "strokes_vs_last_visit": -7,
        "is_course_pb_this_teg": true,
        "summary_facts": [
          "David Mullin's prior best at Royal Cinque Ports: 94 gross (TEG 13)",
          "David Mullin's new personal best at Royal Cinque Ports in R1: 87 gross — improved by 7",
          "David Mullin was 7 shots better than his last visit to Royal Cinque Ports"
        ]
      }
    },
    "Gregg Williams": {
      "Littlestone": {
        "course": "Littlestone",
        "visit_count_through_this_teg": 2,
        "n_prior_visits": 1,
        "prior_best_gross": 86,
        "prior_best_teg": 13,
        "this_teg_best_gross": 97,
        "this_teg_best_round": 2,
        "strokes_vs_last_visit": 11,
        "is_course_pb_this_teg": false,
        "summary_facts": [
          "Gregg Williams's prior best at Littlestone: 86 gross (TEG 13)",
          "Gregg Williams was 11 shots worse than his last visit to Littlestone"
        ]
      },
      "Prince's - Shore / Dunes": {
        "course": "Prince's - Shore / Dunes",
        "visit_count_through_this_teg": 3,
        "n_prior_visits": 1,
        "prior_best_gross": 89,
        "prior_best_teg": 13,
        "this_teg_best_gross": 86,
        "this_teg_best_round": 3,
        "strokes_vs_last_visit": -3,
        "is_course_pb_this_teg": true,
        "summary_facts": [
          "Gregg Williams's prior best at Prince's - Shore / Dunes: 89 gross (TEG 13)",
          "Gregg Williams's new personal best at Prince's - Shore / Dunes in R3: 86 gross — improved by 3"
        ]
      },
      "Royal Cinque Ports": {
        "course": "Royal Cinque Ports",
        "visit_count_through_this_teg": 2,
        "n_prior_visits": 1,
        "prior_best_gross": 94,
        "prior_best_teg": 13,
        "this_teg_best_gross": 93,
        "this_teg_best_round": 1,
        "strokes_vs_last_visit": -1,
        "is_course_pb_this_teg": true,
        "summary_facts": [
          "Gregg Williams's prior best at Royal Cinque Ports: 94 gross (TEG 13)",
          "Gregg Williams's new personal best at Royal Cinque Ports in R1: 93 gross — improved by 1"
        ]
      }
    },
    "Jon Baker": {
      "Littlestone": {
        "course": "Littlestone",
        "visit_count_through_this_teg": 2,
        "n_prior_visits": 1,
        "prior_best_gross": 79,
        "prior_best_teg": 13,
        "this_teg_best_gross": 92,
        "this_teg_best_round": 2,
        "strokes_vs_last_visit": 13,
        "is_course_pb_this_teg": false,
        "summary_facts": [
          "Jon Baker's prior best at Littlestone: 79 gross (TEG 13)",
          "Jon Baker was 13 shots worse than his last visit to Littlestone"
        ]
      },
      "Prince's - Shore / Dunes": {
        "course": "Prince's - Shore / Dunes",
        "visit_count_through_this_teg": 3,
        "n_prior_visits": 1,
        "prior_best_gross": 85,
        "prior_best_teg": 13,
        "this_teg_best_gross": 83,
        "this_teg_best_round": 4,
        "strokes_vs_last_visit": -2,
        "is_course_pb_this_teg": true,
        "summary_facts": [
          "Jon Baker's prior best at Prince's - Shore / Dunes: 85 gross (TEG 13)",
          "Jon Baker's new personal best at Prince's - Shore / Dunes in R4: 83 gross — improved by 2"
        ]
      },
      "Royal Cinque Ports": {
        "course": "Royal Cinque Ports",
        "visit_count_through_this_teg": 2,
        "n_prior_visits": 1,
        "prior_best_gross": 85,
        "prior_best_teg": 13,
        "this_teg_best_gross": 92,
        "this_teg_best_round": 1,
        "strokes_vs_last_visit": 7,
        "is_course_pb_this_teg": false,
        "summary_facts": [
          "Jon Baker's prior best at Royal Cinque Ports: 85 gross (TEG 13)",
          "Jon Baker was 7 shots worse than his last visit to Royal Cinque Ports"
        ]
      }
    }
  },
  "player_relationships": [
    {
      "players": [
        "Alex Baker",
        "Jon Baker"
      ],
      "relationship": "brothers"
    }
  ],
  "tournament_shape": {
    "close_finish": true,
    "signals": [
      "final margin 2 ≤ 4 (decisive finish was close)"
    ],
    "final_margin": 2,
    "trophy_metric": "stableford"
  },
  "recent_vehicle_choices": [
    {
      "teg": 11,
      "vehicles": [
        "dual_narrative",
        "comeback",
        "motif"
      ],
      "structure": "in_medias_res",
      "title": "Baker v Baker: Jon Takes the Lot"
    },
    {
      "teg": 12,
      "vehicles": [
        "dual_narrative",
        "tragic_arc",
        "catalogue"
      ],
      "structure": "three_act",
      "title": "Twelve, Ten, Ten: Patterson Wins the Ugly Way"
    },
    {
      "teg": 13,
      "vehicles": [
        "hero_arc",
        "ensemble",
        "inevitability"
      ],
      "structure": "in_medias_res",
      "title": "Fifty, and Never Headed"
    }
  ],
  "vehicle_fit_hints": [
    {
      "vehicle": "underdog",
      "raw": 16.0,
      "z": 2.96,
      "baseline_mean": 4.18,
      "reasons": [
        "David MULLIN: 4 prior Wooden Spoons — now the Trophy winner",
        "David MULLIN: back-to-back Wooden Spoons going into this TEG — now the Trophy winner",
        "David MULLIN: Wooden Spoon in 3 of the last 3 TEGs — now the Trophy winner"
      ]
    },
    {
      "vehicle": "inevitability",
      "raw": 10.0,
      "z": 1.92,
      "baseline_mean": 4.41,
      "reasons": [
        "Trophy led wire-to-wire, no lead changes after R1",
        "Green Jacket led wire-to-wire, no lead changes after R1"
      ]
    },
    {
      "vehicle": "counterfactual",
      "raw": 6.0,
      "z": 1.55,
      "baseline_mean": 1.76,
      "reasons": [
        "close finish: final margin 2 ≤ 4 (decisive finish was close)"
      ]
    },
    {
      "vehicle": "redemption_arc",
      "raw": 22.2,
      "z": 0.55,
      "baseline_mean": 15.93,
      "reasons": [
        "b22: Jon Baker follows a poor R3 with a strong R4",
        "b55 (R2): David Mullin stops the bleeding with a birdie at the 7th (R2)",
        "b68 (R2): David Mullin stops the bleeding with a birdie at the 18th (R2)"
      ]
    },
    {
      "vehicle": "inversion",
      "raw": 4.0,
      "z": -0.23,
      "baseline_mean": 4.49,
      "reasons": [
        "Jon BAKER: defending Trophy champion (TEG 13) but did not repeat"
      ]
    }
  ],
  "candidate_threads": [
    {
      "subject_type": "course",
      "subject": "Prince's - Shore / Dunes",
      "round_span": [
        3,
        4
      ],
      "entertainment_sum": 119.3,
      "rarity_max": 6,
      "independent_of_trophy": true,
      "score": 73.7,
      "beat_ids": [
        "b01",
        "b03",
        "b04",
        "b05",
        "b06",
        "b07",
        "b09",
        "b10",
        "b11",
        "b12",
        "b13",
        "b14",
        "b15",
        "b16",
        "b17",
        "b18",
        "b19",
        "b20",
        "b21",
        "b22",
        "b23",
        "b24",
        "b26",
        "b27",
        "b28",
        "b29",
        "b34",
        "b35",
        "b36",
        "b37",
        "b38",
        "b40",
        "b42",
        "b43",
        "b44",
        "b45",
        "b46",
        "b50",
        "b51",
        "b52",
        "b56",
        "b61"
      ],
      "headlines": [
        "Alex Baker runs up a 10 (sextuple bogey) at the 16th (R4)",
        "Jon Baker goes 5 holes without dropping a gross shot, 11-15 (R4)",
        "David Mullin runs up a 8 (quadruple bogey) at the 10th (R4)",
        "Jon Baker piles up 14 points, holes 12-15 (R4)",
        "Alex Baker's steady run ends with a sextuple bogey at the 16th (R4)",
        "Jon Baker's steady run ends with a double bogey at the 16th (R4)",
        "Alex Baker piles up 11 points, holes 13-15 (R4)",
        "David Mullin far stronger on the back nine in R3 (10-pt split)",
        "Alex Baker's steady run ends with a double bogey at the 4th (R4)",
        "Alex Baker runs up a 8 (quadruple bogey) at the 10th (R3)",
        "Alex Baker goes 3 holes without dropping a gross shot, 13-15 (R4)",
        "David Mullin runs up a 9 (quadruple bogey) at the 8th (R3)",
        "David Mullin piles up 13 points, holes 15-18 (R3)",
        "Jon Baker's steady run ends with a triple bogey at the 17th (R3)",
        "Gregg Williams closes to 8 off the Green Jacket lead after trailing by 18 at one point",
        "Gregg Williams goes 2 holes without dropping a gross shot, 14-15 (R4)",
        "Jon Baker closes to 7 off the Green Jacket lead after trailing by 15 at one point",
        "Alex Baker closes to 2 off the Trophy lead after trailing by 9 at one point",
        "Alex Baker piles up 10 points, holes 1-3 (R4)",
        "Jon Baker follows a poor R3 with a strong R4",
        "Gregg Williams's steady run ends with a triple bogey at the 12th (R3)",
        "David Mullin goes 4 holes without dropping a gross shot, 15-18 (R3)",
        "Jon Baker goes 2 holes without dropping a gross shot, 5-6 (R4)",
        "Alex Baker goes 3 holes without dropping a gross shot, 1-3 (R4)",
        "Alex Baker goes 2 holes without dropping a gross shot, 6-7 (R4)",
        "Gregg Williams goes 2 holes without dropping a gross shot, 5-6 (R4)",
        "Gregg Williams piles up 9 points, holes 9-11 (R3)",
        "Jon Baker goes 3 holes without dropping a gross shot, 14-16 (R3)",
        "Gregg Williams goes 2 holes without dropping a gross shot, 2-3 (R4)",
        "After R3: David Mullin leads the Trophy (gap 0 on Stableford); David Mullin leads the Jacket",
        "Gregg Williams goes 3 holes without dropping a gross shot, 9-11 (R3)",
        "Gregg Williams goes 2 holes without dropping a gross shot, 15-16 (R3)",
        "After R4: David Mullin leads the Trophy (gap 0 on Stableford); David Mullin leads the Jacket",
        "Gregg Williams follows a poor R2 with a strong R3",
        "Jon Baker runs up a 8 (quadruple bogey) at the 18th (R4)",
        "Jon Baker goes 2 holes without dropping a gross shot, 8-9 (R3)",
        "David Mullin goes 2 holes without dropping a gross shot, 2-3 (R4)",
        "Alex Baker bleeds 6 shots, holes 1-3 (R3)",
        "Gregg Williams goes 2 holes without dropping a gross shot, 2-3 (R3)",
        "Alex Baker goes 2 holes without dropping a gross shot, 11-12 (R3)",
        "Jon Baker runs up a 8 (quadruple bogey) at the 13th (R3)",
        "David Mullin goes 2 holes without dropping a gross shot, 4-5 (R3)"
      ]
    },
    {
      "subject_type": "player",
      "subject": "Alex Baker",
      "round_span": [
        1,
        2,
        3,
        4
      ],
      "entertainment_sum": 67.9,
      "rarity_max": 6,
      "independent_of_trophy": true,
      "score": 53.9,
      "beat_ids": [
        "b01",
        "b06",
        "b09",
        "b11",
        "b12",
        "b13",
        "b20",
        "b21",
        "b25",
        "b27",
        "b28",
        "b30",
        "b33",
        "b39",
        "b47",
        "b50",
        "b52",
        "b54",
        "b69",
        "b72"
      ],
      "headlines": [
        "Alex Baker runs up a 10 (sextuple bogey) at the 16th (R4)",
        "Alex Baker's steady run ends with a sextuple bogey at the 16th (R4)",
        "Alex Baker piles up 11 points, holes 13-15 (R4)",
        "Alex Baker's steady run ends with a double bogey at the 4th (R4)",
        "Alex Baker runs up a 8 (quadruple bogey) at the 10th (R3)",
        "Alex Baker goes 3 holes without dropping a gross shot, 13-15 (R4)",
        "Alex Baker closes to 2 off the Trophy lead after trailing by 9 at one point",
        "Alex Baker piles up 10 points, holes 1-3 (R4)",
        "Alex Baker runs up a 10 (quintuple bogey) at the 16th (R1)",
        "Alex Baker goes 3 holes without dropping a gross shot, 1-3 (R4)",
        "Alex Baker goes 2 holes without dropping a gross shot, 6-7 (R4)",
        "Alex Baker runs up a 8 (quadruple bogey) at the 8th (R2)",
        "Alex Baker runs up a 9 (quadruple bogey) at the 5th (R2)",
        "Alex Baker runs up a 8 (quadruple bogey) at the 11th (R1)",
        "Alex Baker bleeds 12 shots, holes 2-5 (R2)",
        "Alex Baker bleeds 6 shots, holes 1-3 (R3)",
        "Alex Baker goes 2 holes without dropping a gross shot, 11-12 (R3)",
        "Alex Baker goes 4 holes without a net par, 2-5 (R2)",
        "Alex Baker bleeds 6 shots, holes 3-5 (R1)",
        "Alex Baker draws level for the Green Jacket (Gross) lead (R1 H6)"
      ]
    },
    {
      "subject_type": "player",
      "subject": "David Mullin",
      "round_span": [
        1,
        2,
        3,
        4
      ],
      "entertainment_sum": 68.3,
      "rarity_max": 4,
      "independent_of_trophy": true,
      "score": 52.2,
      "beat_ids": [
        "b04",
        "b10",
        "b14",
        "b15",
        "b24",
        "b37",
        "b37",
        "b42",
        "b42",
        "b46",
        "b48",
        "b49",
        "b53",
        "b53",
        "b55",
        "b57",
        "b60",
        "b61",
        "b62",
        "b64",
        "b65",
        "b67",
        "b67",
        "b68",
        "b70",
        "b73",
        "b74"
      ],
      "headlines": [
        "David Mullin runs up a 8 (quadruple bogey) at the 10th (R4)",
        "David Mullin far stronger on the back nine in R3 (10-pt split)",
        "David Mullin runs up a 9 (quadruple bogey) at the 8th (R3)",
        "David Mullin piles up 13 points, holes 15-18 (R3)",
        "David Mullin goes 4 holes without dropping a gross shot, 15-18 (R3)",
        "After R3: David Mullin leads the Trophy (gap 0 on Stableford); David Mullin leads the Jacket",
        "After R3: David Mullin leads the Trophy (gap 0 on Stableford); David Mullin leads the Jacket",
        "After R4: David Mullin leads the Trophy (gap 0 on Stableford); David Mullin leads the Jacket",
        "After R4: David Mullin leads the Trophy (gap 0 on Stableford); David Mullin leads the Jacket",
        "David Mullin goes 2 holes without dropping a gross shot, 2-3 (R4)",
        "David Mullin piles up 13 points, holes 9-12 (R1)",
        "David Mullin's steady run ends with a double bogey at the 13th (R1)",
        "After R2: David Mullin leads the Trophy (gap 0 on Stableford); David Mullin leads the Jacket",
        "After R2: David Mullin leads the Trophy (gap 0 on Stableford); David Mullin leads the Jacket",
        "David Mullin stops the bleeding with a birdie at the 7th (R2)",
        "David Mullin goes 4 holes without dropping a gross shot, 9-12 (R1)",
        "David Mullin goes 2 holes without dropping a gross shot, 7-8 (R2)",
        "David Mullin goes 2 holes without dropping a gross shot, 4-5 (R3)",
        "David Mullin goes 2 holes without dropping a gross shot, 10-11 (R2)",
        "David Mullin goes 2 holes without dropping a gross shot, 13-14 (R2)",
        "David Mullin goes 2 holes without dropping a gross shot, 15-16 (R1)",
        "After R1: David Mullin leads the Trophy (gap 0 on Stableford); David Mullin leads the Jacket",
        "After R1: David Mullin leads the Trophy (gap 0 on Stableford); David Mullin leads the Jacket",
        "David Mullin stops the bleeding with a birdie at the 18th (R2)",
        "David Mullin takes the Trophy (Stableford) lead (R1 H16)",
        "David Mullin draws level for the Trophy (Stableford) lead (R1 H11)",
        "David Mullin draws level for the Green Jacket (Gross) lead (R1 H9)"
      ]
    },
    {
      "subject_type": "player",
      "subject": "Jon Baker",
      "round_span": [
        1,
        2,
        3,
        4
      ],
      "entertainment_sum": 49.8,
      "rarity_max": 4,
      "independent_of_trophy": true,
      "score": 42.9,
      "beat_ids": [
        "b03",
        "b05",
        "b07",
        "b16",
        "b19",
        "b22",
        "b26",
        "b35",
        "b44",
        "b45",
        "b56",
        "b58",
        "b59",
        "b63",
        "b66",
        "b71"
      ],
      "headlines": [
        "Jon Baker goes 5 holes without dropping a gross shot, 11-15 (R4)",
        "Jon Baker piles up 14 points, holes 12-15 (R4)",
        "Jon Baker's steady run ends with a double bogey at the 16th (R4)",
        "Jon Baker's steady run ends with a triple bogey at the 17th (R3)",
        "Jon Baker closes to 7 off the Green Jacket lead after trailing by 15 at one point",
        "Jon Baker follows a poor R3 with a strong R4",
        "Jon Baker goes 2 holes without dropping a gross shot, 5-6 (R4)",
        "Jon Baker goes 3 holes without dropping a gross shot, 14-16 (R3)",
        "Jon Baker runs up a 8 (quadruple bogey) at the 18th (R4)",
        "Jon Baker goes 2 holes without dropping a gross shot, 8-9 (R3)",
        "Jon Baker runs up a 8 (quadruple bogey) at the 13th (R3)",
        "Jon Baker goes 2 holes without dropping a gross shot, 14-15 (R2)",
        "Jon Baker piles up 9 points, holes 11-13 (R1)",
        "Jon Baker goes 3 holes without dropping a gross shot, 11-13 (R1)",
        "Jon Baker goes 5 holes without a net par, 2-6 (R1)",
        "Jon Baker drops to the bottom of the Wooden Spoon race (R1 H4)"
      ]
    },
    {
      "subject_type": "player",
      "subject": "Gregg Williams",
      "round_span": [
        1,
        3,
        4
      ],
      "entertainment_sum": 29.0,
      "rarity_max": 7.0,
      "independent_of_trophy": true,
      "score": 32.5,
      "beat_ids": [
        "b17",
        "b18",
        "b23",
        "b29",
        "b31",
        "b34",
        "b36",
        "b38",
        "b40",
        "b41",
        "b43",
        "b51"
      ],
      "headlines": [
        "Gregg Williams closes to 8 off the Green Jacket lead after trailing by 18 at one point",
        "Gregg Williams goes 2 holes without dropping a gross shot, 14-15 (R4)",
        "Gregg Williams's steady run ends with a triple bogey at the 12th (R3)",
        "Gregg Williams goes 2 holes without dropping a gross shot, 5-6 (R4)",
        "Gregg Williams posts a personal-best Gross total: +76",
        "Gregg Williams piles up 9 points, holes 9-11 (R3)",
        "Gregg Williams goes 2 holes without dropping a gross shot, 2-3 (R4)",
        "Gregg Williams goes 3 holes without dropping a gross shot, 9-11 (R3)",
        "Gregg Williams goes 2 holes without dropping a gross shot, 15-16 (R3)",
        "Gregg Williams runs up a 9 (quadruple bogey) at the 3rd (R1)",
        "Gregg Williams follows a poor R2 with a strong R3",
        "Gregg Williams goes 2 holes without dropping a gross shot, 2-3 (R3)"
      ]
    },
    {
      "subject_type": "failure_mode",
      "subject": "Alex Baker",
      "round_span": [
        1,
        2,
        3,
        4
      ],
      "entertainment_sum": 17.6,
      "rarity_max": 2.5,
      "independent_of_trophy": true,
      "score": 25.3,
      "beat_ids": [
        "b06",
        "b11",
        "b47",
        "b50",
        "b54",
        "b69"
      ],
      "headlines": [
        "Alex Baker's steady run ends with a sextuple bogey at the 16th (R4)",
        "Alex Baker's steady run ends with a double bogey at the 4th (R4)",
        "Alex Baker bleeds 12 shots, holes 2-5 (R2)",
        "Alex Baker bleeds 6 shots, holes 1-3 (R3)",
        "Alex Baker goes 4 holes without a net par, 2-5 (R2)",
        "Alex Baker bleeds 6 shots, holes 3-5 (R1)"
      ]
    },
    {
      "subject_type": "failure_mode",
      "subject": "Jon Baker",
      "round_span": [
        1,
        3,
        4
      ],
      "entertainment_sum": 12.4,
      "rarity_max": 2.5,
      "independent_of_trophy": true,
      "score": 19.7,
      "beat_ids": [
        "b07",
        "b16",
        "b66"
      ],
      "headlines": [
        "Jon Baker's steady run ends with a double bogey at the 16th (R4)",
        "Jon Baker's steady run ends with a triple bogey at the 17th (R3)",
        "Jon Baker goes 5 holes without a net par, 2-6 (R1)"
      ]
    }
  ],
  "beats": [
    {
      "id": "b01",
      "total": 31.62,
      "scope": "hole",
      "type": "big_blowup",
      "round": 4,
      "course": "Prince's - Shore / Dunes",
      "headline": "Alex Baker runs up a 10 (sextuple bogey) at the 16th (R4)",
      "players": [
        "Alex Baker"
      ],
      "scores": {
        "importance": 9.76,
        "rarity": 6,
        "entertainment": 7.3
      },
      "mandatory": true,
      "holes": [
        {
          "hole": 16,
          "par": 4,
          "sc": 10,
          "grossvp": 6,
          "result": "sextuple bogey",
          "stableford": 0,
          "si": 17
        }
      ],
      "context": {
        "is_player_par_worst": false,
        "is_teg_par_worst": false,
        "importance_legacy": 4.4,
        "impact_metric": "stableford"
      }
    },
    {
      "id": "b02",
      "total": 28.2,
      "scope": "tournament",
      "type": "trophy_win",
      "round": null,
      "course": null,
      "headline": "David Mullin wins the Trophy on 154 pts, by 2",
      "players": [
        "David Mullin"
      ],
      "scores": {
        "importance": 10.0,
        "rarity": 4.0,
        "entertainment": 5.0
      },
      "mandatory": true,
      "holes": [],
      "context": {
        "score": 154,
        "margin": 2,
        "trophy_metric": "stableford",
        "runner_up": "Alex Baker",
        "all_time_rank": 16,
        "player_rank": 3
      }
    },
    {
      "id": "b03",
      "total": 26.54,
      "scope": "stretch",
      "type": "hot_stretch_gross",
      "round": 4,
      "course": "Prince's - Shore / Dunes",
      "headline": "Jon Baker goes 5 holes without dropping a gross shot, 11-15 (R4)",
      "players": [
        "Jon Baker"
      ],
      "scores": {
        "importance": 9.64,
        "rarity": 3.8499999999999996,
        "entertainment": 4.18
      },
      "mandatory": false,
      "holes": [
        {
          "hole": 11,
          "par": 3,
          "sc": 3,
          "grossvp": 0,
          "result": "par",
          "stableford": 2,
          "si": 15
        },
        {
          "hole": 12,
          "par": 5,
          "sc": 4,
          "grossvp": -1,
          "result": "birdie",
          "stableford": 4,
          "si": 13
        },
        {
          "hole": 13,
          "par": 4,
          "sc": 3,
          "grossvp": -1,
          "result": "birdie",
          "stableford": 4,
          "si": 1
        },
        {
          "hole": 14,
          "par": 4,
          "sc": 4,
          "grossvp": 0,
          "result": "par",
          "stableford": 3,
          "si": 5
        },
        {
          "hole": 15,
          "par": 5,
          "sc": 5,
          "grossvp": 0,
          "result": "par",
          "stableford": 3,
          "si": 9
        }
      ],
      "context": {
        "shots_gained": 2,
        "length": 5,
        "importance_legacy": 6.82,
        "impact_metric": "stableford"
      }
    },
    {
      "id": "b04",
      "total": 26.32,
      "scope": "hole",
      "type": "big_blowup",
      "round": 4,
      "course": "Prince's - Shore / Dunes",
      "headline": "David Mullin runs up a 8 (quadruple bogey) at the 10th (R4)",
      "players": [
        "David Mullin"
      ],
      "scores": {
        "importance": 9.06,
        "rarity": 4,
        "entertainment": 5.0
      },
      "mandatory": false,
      "holes": [
        {
          "hole": 10,
          "par": 4,
          "sc": 8,
          "grossvp": 4,
          "result": "quadruple bogey",
          "stableford": 0,
          "si": 3
        }
      ],
      "context": {
        "is_player_par_worst": false,
        "is_teg_par_worst": false,
        "importance_legacy": 5.0,
        "impact_metric": "stableford"
      }
    },
    {
      "id": "b05",
      "total": 26.22,
      "scope": "stretch",
      "type": "hot_stretch_net",
      "round": 4,
      "course": "Prince's - Shore / Dunes",
      "headline": "Jon Baker piles up 14 points, holes 12-15 (R4)",
      "players": [
        "Jon Baker"
      ],
      "scores": {
        "importance": 9.64,
        "rarity": 3.36,
        "entertainment": 4.255999999999999
      },
      "mandatory": false,
      "holes": [
        {
          "hole": 12,
          "par": 5,
          "sc": 4,
          "grossvp": -1,
          "result": "birdie",
          "stableford": 4,
          "si": 13
        },
        {
          "hole": 13,
          "par": 4,
          "sc": 3,
          "grossvp": -1,
          "result": "birdie",
          "stableford": 4,
          "si": 1
        },
        {
          "hole": 14,
          "par": 4,
          "sc": 4,
          "grossvp": 0,
          "result": "par",
          "stableford": 3,
          "si": 5
        },
        {
          "hole": 15,
          "par": 5,
          "sc": 5,
          "grossvp": 0,
          "result": "par",
          "stableford": 3,
          "si": 9
        }
      ],
      "context": {
        "points_gained": 14,
        "metric": "stableford",
        "length": 4,
        "importance_legacy": 6.85,
        "impact_metric": "stableford"
      }
    },
    {
      "id": "b06",
      "total": 25.82,
      "scope": "stretch",
      "type": "collapse_after_steady",
      "round": 4,
      "course": "Prince's - Shore / Dunes",
      "headline": "Alex Baker's steady run ends with a sextuple bogey at the 16th (R4)",
      "players": [
        "Alex Baker"
      ],
      "scores": {
        "importance": 9.76,
        "rarity": 2.5,
        "entertainment": 4.3
      },
      "mandatory": false,
      "holes": [
        {
          "hole": 13,
          "par": 4,
          "sc": 4,
          "grossvp": 0,
          "result": "par",
          "stableford": 4,
          "si": 1
        },
        {
          "hole": 14,
          "par": 4,
          "sc": 4,
          "grossvp": 0,
          "result": "par",
          "stableford": 4,
          "si": 5
        },
        {
          "hole": 15,
          "par": 5,
          "sc": 5,
          "grossvp": 0,
          "result": "par",
          "stableford": 3,
          "si": 9
        },
        {
          "hole": 16,
          "par": 4,
          "sc": 10,
          "grossvp": 6,
          "result": "sextuple bogey",
          "stableford": 0,
          "si": 17
        }
      ],
      "context": {
        "streak_broken": "par_or_better",
        "importance_legacy": 4.55,
        "impact_metric": "stableford"
      }
    },
    {
      "id": "b07",
      "total": 25.82,
      "scope": "stretch",
      "type": "collapse_after_steady",
      "round": 4,
      "course": "Prince's - Shore / Dunes",
      "headline": "Jon Baker's steady run ends with a double bogey at the 16th (R4)",
      "players": [
        "Jon Baker"
      ],
      "scores": {
        "importance": 9.76,
        "rarity": 2.5,
        "entertainment": 4.3
      },
      "mandatory": false,
      "holes": [
        {
          "hole": 11,
          "par": 3,
          "sc": 3,
          "grossvp": 0,
          "result": "par",
          "stableford": 2,
          "si": 15
        },
        {
          "hole": 12,
          "par": 5,
          "sc": 4,
          "grossvp": -1,
          "result": "birdie",
          "stableford": 4,
          "si": 13
        },
        {
          "hole": 13,
          "par": 4,
          "sc": 3,
          "grossvp": -1,
          "result": "birdie",
          "stableford": 4,
          "si": 1
        },
        {
          "hole": 14,
          "par": 4,
          "sc": 4,
          "grossvp": 0,
          "result": "par",
          "stableford": 3,
          "si": 5
        },
        {
          "hole": 15,
          "par": 5,
          "sc": 5,
          "grossvp": 0,
          "result": "par",
          "stableford": 3,
          "si": 9
        },
        {
          "hole": 16,
          "par": 4,
          "sc": 6,
          "grossvp": 2,
          "result": "double bogey",
          "stableford": 0,
          "si": 17
        }
      ],
      "context": {
        "streak_broken": "par_or_better",
        "importance_legacy": 4.55,
        "impact_metric": "stableford"
      }
    },
    {
      "id": "b08",
      "total": 25.2,
      "scope": "tournament",
      "type": "jacket_win",
      "round": null,
      "course": null,
      "headline": "David Mullin wins the Green Jacket at +68, by 7",
      "players": [
        "David Mullin"
      ],
      "scores": {
        "importance": 9.0,
        "rarity": 4.0,
        "entertainment": 4.0
      },
      "mandatory": true,
      "holes": [],
      "context": {
        "score": 68,
        "margin": 7,
        "runner_up": "Jon Baker",
        "all_time_rank": 6,
        "player_rank": 4,
        "metric": "gross"
      }
    },
    {
      "id": "b09",
      "total": 24.74,
      "scope": "stretch",
      "type": "hot_stretch_net",
      "round": 4,
      "course": "Prince's - Shore / Dunes",
      "headline": "Alex Baker piles up 11 points, holes 13-15 (R4)",
      "players": [
        "Alex Baker"
      ],
      "scores": {
        "importance": 9.64,
        "rarity": 2.64,
        "entertainment": 3.3440000000000003
      },
      "mandatory": false,
      "holes": [
        {
          "hole": 13,
          "par": 4,
          "sc": 4,
          "grossvp": 0,
          "result": "par",
          "stableford": 4,
          "si": 1
        },
        {
          "hole": 14,
          "par": 4,
          "sc": 4,
          "grossvp": 0,
          "result": "par",
          "stableford": 4,
          "si": 5
        },
        {
          "hole": 15,
          "par": 5,
          "sc": 5,
          "grossvp": 0,
          "result": "par",
          "stableford": 3,
          "si": 9
        }
      ],
      "context": {
        "points_gained": 11,
        "metric": "stableford",
        "length": 3,
        "importance_legacy": 6.51,
        "impact_metric": "stableford"
      }
    },
    {
      "id": "b10",
      "total": 23.34,
      "scope": "round",
      "type": "round_player",
      "round": 3,
      "course": "Prince's - Shore / Dunes",
      "headline": "David Mullin far stronger on the back nine in R3 (10-pt split)",
      "players": [
        "David Mullin"
      ],
      "scores": {
        "importance": 7.97,
        "rarity": 3.0,
        "entertainment": 5.0
      },
      "mandatory": false,
      "holes": [],
      "context": {
        "round_score": 36,
        "round_gross_vp": 20,
        "trophy_metric": "stableford",
        "round_stableford": 36,
        "importance_legacy": 5.0,
        "impact_metric": "stableford"
      }
    },
    {
      "id": "b11",
      "total": 23.08,
      "scope": "stretch",
      "type": "collapse_after_steady",
      "round": 4,
      "course": "Prince's - Shore / Dunes",
      "headline": "Alex Baker's steady run ends with a double bogey at the 4th (R4)",
      "players": [
        "Alex Baker"
      ],
      "scores": {
        "importance": 8.39,
        "rarity": 2.5,
        "entertainment": 4.3
      },
      "mandatory": false,
      "holes": [
        {
          "hole": 1,
          "par": 4,
          "sc": 4,
          "grossvp": 0,
          "result": "par",
          "stableford": 4,
          "si": 6
        },
        {
          "hole": 2,
          "par": 5,
          "sc": 5,
          "grossvp": 0,
          "result": "par",
          "stableford": 3,
          "si": 12
        },
        {
          "hole": 3,
          "par": 3,
          "sc": 3,
          "grossvp": 0,
          "result": "par",
          "stableford": 3,
          "si": 16
        },
        {
          "hole": 4,
          "par": 4,
          "sc": 6,
          "grossvp": 2,
          "result": "double bogey",
          "stableford": 2,
          "si": 4
        }
      ],
      "context": {
        "streak_broken": "par_or_better",
        "importance_legacy": 4.55,
        "impact_metric": "stableford"
      }
    },
    {
      "id": "b12",
      "total": 22.88,
      "scope": "hole",
      "type": "big_blowup",
      "round": 3,
      "course": "Prince's - Shore / Dunes",
      "headline": "Alex Baker runs up a 8 (quadruple bogey) at the 10th (R3)",
      "players": [
        "Alex Baker"
      ],
      "scores": {
        "importance": 7.19,
        "rarity": 4,
        "entertainment": 5.3
      },
      "mandatory": false,
      "holes": [
        {
          "hole": 10,
          "par": 4,
          "sc": 8,
          "grossvp": 4,
          "result": "quadruple bogey",
          "stableford": 0,
          "si": 3
        }
      ],
      "context": {
        "is_player_par_worst": false,
        "is_teg_par_worst": false,
        "importance_legacy": 4.4,
        "impact_metric": "stableford"
      }
    },
    {
      "id": "b13",
      "total": 22.84,
      "scope": "stretch",
      "type": "hot_stretch_gross",
      "round": 4,
      "course": "Prince's - Shore / Dunes",
      "headline": "Alex Baker goes 3 holes without dropping a gross shot, 13-15 (R4)",
      "players": [
        "Alex Baker"
      ],
      "scores": {
        "importance": 9.64,
        "rarity": 1.89,
        "entertainment": 2.052
      },
      "mandatory": false,
      "holes": [
        {
          "hole": 13,
          "par": 4,
          "sc": 4,
          "grossvp": 0,
          "result": "par",
          "stableford": 4,
          "si": 1
        },
        {
          "hole": 14,
          "par": 4,
          "sc": 4,
          "grossvp": 0,
          "result": "par",
          "stableford": 4,
          "si": 5
        },
        {
          "hole": 15,
          "par": 5,
          "sc": 5,
          "grossvp": 0,
          "result": "par",
          "stableford": 3,
          "si": 9
        }
      ],
      "context": {
        "shots_gained": 0,
        "length": 3,
        "importance_legacy": 6.03,
        "impact_metric": "stableford"
      }
    },
    {
      "id": "b14",
      "total": 22.2,
      "scope": "hole",
      "type": "big_blowup",
      "round": 3,
      "course": "Prince's - Shore / Dunes",
      "headline": "David Mullin runs up a 9 (quadruple bogey) at the 8th (R3)",
      "players": [
        "David Mullin"
      ],
      "scores": {
        "importance": 7.0,
        "rarity": 4,
        "entertainment": 5.0
      },
      "mandatory": false,
      "holes": [
        {
          "hole": 8,
          "par": 5,
          "sc": 9,
          "grossvp": 4,
          "result": "quadruple bogey",
          "stableford": 0,
          "si": 8
        }
      ],
      "context": {
        "is_player_par_worst": false,
        "is_teg_par_worst": false,
        "importance_legacy": 5.0,
        "impact_metric": "stableford"
      }
    },
    {
      "id": "b15",
      "total": 22.08,
      "scope": "stretch",
      "type": "hot_stretch_net",
      "round": 3,
      "course": "Prince's - Shore / Dunes",
      "headline": "David Mullin piles up 13 points, holes 15-18 (R3)",
      "players": [
        "David Mullin"
      ],
      "scores": {
        "importance": 7.97,
        "rarity": 3.12,
        "entertainment": 3.6400000000000006
      },
      "mandatory": false,
      "holes": [
        {
          "hole": 15,
          "par": 5,
          "sc": 5,
          "grossvp": 0,
          "result": "par",
          "stableford": 3,
          "si": 9
        },
        {
          "hole": 16,
          "par": 4,
          "sc": 4,
          "grossvp": 0,
          "result": "par",
          "stableford": 3,
          "si": 17
        },
        {
          "hole": 17,
          "par": 3,
          "sc": 3,
          "grossvp": 0,
          "result": "par",
          "stableford": 3,
          "si": 11
        },
        {
          "hole": 18,
          "par": 4,
          "sc": 3,
          "grossvp": -1,
          "result": "birdie",
          "stableford": 4,
          "si": 7
        }
      ],
      "context": {
        "points_gained": 13,
        "metric": "stableford",
        "length": 4,
        "importance_legacy": 6.46,
        "impact_metric": "stableford"
      }
    },
    {
      "id": "b16",
      "total": 22.04,
      "scope": "stretch",
      "type": "collapse_after_steady",
      "round": 3,
      "course": "Prince's - Shore / Dunes",
      "headline": "Jon Baker's steady run ends with a triple bogey at the 17th (R3)",
      "players": [
        "Jon Baker"
      ],
      "scores": {
        "importance": 7.87,
        "rarity": 2.5,
        "entertainment": 4.3
      },
      "mandatory": false,
      "holes": [
        {
          "hole": 14,
          "par": 4,
          "sc": 4,
          "grossvp": 0,
          "result": "par",
          "stableford": 3,
          "si": 5
        },
        {
          "hole": 15,
          "par": 5,
          "sc": 5,
          "grossvp": 0,
          "result": "par",
          "stableford": 3,
          "si": 9
        },
        {
          "hole": 16,
          "par": 4,
          "sc": 4,
          "grossvp": 0,
          "result": "par",
          "stableford": 2,
          "si": 17
        },
        {
          "hole": 17,
          "par": 3,
          "sc": 6,
          "grossvp": 3,
          "result": "triple bogey",
          "stableford": 0,
          "si": 11
        }
      ],
      "context": {
        "streak_broken": "par_or_better",
        "importance_legacy": 4.55,
        "impact_metric": "stableford"
      }
    },
    {
      "id": "b17",
      "total": 21.94,
      "scope": "tournament",
      "type": "gap_closed",
      "round": 4,
      "course": "Prince's - Shore / Dunes",
      "headline": "Gregg Williams closes to 8 off the Green Jacket lead after trailing by 18 at one point",
      "players": [
        "Gregg Williams"
      ],
      "scores": {
        "importance": 10.0,
        "rarity": 0.8,
        "entertainment": 1.3
      },
      "mandatory": false,
      "holes": [],
      "context": {
        "competition": "Green Jacket",
        "max_gap": 18,
        "final_gap": 8,
        "closed": 10,
        "importance_legacy": 3.24,
        "impact_metric": "stableford"
      }
    },
    {
      "id": "b18",
      "total": 21.76,
      "scope": "stretch",
      "type": "hot_stretch_gross",
      "round": 4,
      "course": "Prince's - Shore / Dunes",
      "headline": "Gregg Williams goes 2 holes without dropping a gross shot, 14-15 (R4)",
      "players": [
        "Gregg Williams"
      ],
      "scores": {
        "importance": 9.64,
        "rarity": 1.26,
        "entertainment": 1.4760000000000002
      },
      "mandatory": false,
      "holes": [
        {
          "hole": 14,
          "par": 4,
          "sc": 4,
          "grossvp": 0,
          "result": "par",
          "stableford": 3,
          "si": 5
        },
        {
          "hole": 15,
          "par": 5,
          "sc": 5,
          "grossvp": 0,
          "result": "par",
          "stableford": 3,
          "si": 9
        }
      ],
      "context": {
        "shots_gained": 0,
        "length": 2,
        "importance_legacy": 5.17,
        "impact_metric": "stableford"
      }
    },
    {
      "id": "b19",
      "total": 21.7,
      "scope": "tournament",
      "type": "gap_closed",
      "round": 4,
      "course": "Prince's - Shore / Dunes",
      "headline": "Jon Baker closes to 7 off the Green Jacket lead after trailing by 15 at one point",
      "players": [
        "Jon Baker"
      ],
      "scores": {
        "importance": 10.0,
        "rarity": 0.7,
        "entertainment": 1.1400000000000001
      },
      "mandatory": false,
      "holes": [],
      "context": {
        "competition": "Green Jacket",
        "max_gap": 15,
        "final_gap": 7,
        "closed": 8,
        "importance_legacy": 3.24,
        "impact_metric": "stableford"
      }
    },
    {
      "id": "b20",
      "total": 21.58,
      "scope": "tournament",
      "type": "gap_closed",
      "round": 4,
      "course": "Prince's - Shore / Dunes",
      "headline": "Alex Baker closes to 2 off the Trophy lead after trailing by 9 at one point",
      "players": [
        "Alex Baker"
      ],
      "scores": {
        "importance": 10.0,
        "rarity": 0.65,
        "entertainment": 1.06
      },
      "mandatory": false,
      "holes": [],
      "context": {
        "competition": "Trophy",
        "max_gap": 9,
        "final_gap": 2,
        "closed": 7,
        "importance_legacy": 3.04,
        "impact_metric": "stableford"
      }
    },
    {
      "id": "b21",
      "total": 21.52,
      "scope": "stretch",
      "type": "hot_stretch_net",
      "round": 4,
      "course": "Prince's - Shore / Dunes",
      "headline": "Alex Baker piles up 10 points, holes 1-3 (R4)",
      "players": [
        "Alex Baker"
      ],
      "scores": {
        "importance": 8.28,
        "rarity": 2.4,
        "entertainment": 3.04
      },
      "mandatory": false,
      "holes": [
        {
          "hole": 1,
          "par": 4,
          "sc": 4,
          "grossvp": 0,
          "result": "par",
          "stableford": 4,
          "si": 6
        },
        {
          "hole": 2,
          "par": 5,
          "sc": 5,
          "grossvp": 0,
          "result": "par",
          "stableford": 3,
          "si": 12
        },
        {
          "hole": 3,
          "par": 3,
          "sc": 3,
          "grossvp": 0,
          "result": "par",
          "stableford": 3,
          "si": 16
        }
      ],
      "context": {
        "points_gained": 10,
        "metric": "stableford",
        "length": 3,
        "importance_legacy": 6.4,
        "impact_metric": "stableford"
      }
    },
    {
      "id": "b22",
      "total": 21.48,
      "scope": "round",
      "type": "round_swing",
      "round": 4,
      "course": "Prince's - Shore / Dunes",
      "headline": "Jon Baker follows a poor R3 with a strong R4",
      "players": [
        "Jon Baker"
      ],
      "scores": {
        "importance": 10.0,
        "rarity": 0.74,
        "entertainment": 0.8872500000000001
      },
      "mandatory": false,
      "holes": [],
      "context": {
        "direction": "up",
        "delta": 11,
        "prev_round": 3,
        "prev_score": 28,
        "curr_score": 39,
        "importance_legacy": 4.36,
        "impact_metric": "stableford"
      }
    },
    {
      "id": "b23",
      "total": 21.34,
      "scope": "stretch",
      "type": "collapse_after_steady",
      "round": 3,
      "course": "Prince's - Shore / Dunes",
      "headline": "Gregg Williams's steady run ends with a triple bogey at the 12th (R3)",
      "players": [
        "Gregg Williams"
      ],
      "scores": {
        "importance": 7.37,
        "rarity": 2.5,
        "entertainment": 4.6
      },
      "mandatory": false,
      "holes": [
        {
          "hole": 9,
          "par": 4,
          "sc": 4,
          "grossvp": 0,
          "result": "par",
          "stableford": 3,
          "si": 10
        },
        {
          "hole": 10,
          "par": 4,
          "sc": 4,
          "grossvp": 0,
          "result": "par",
          "stableford": 3,
          "si": 3
        },
        {
          "hole": 11,
          "par": 3,
          "sc": 3,
          "grossvp": 0,
          "result": "par",
          "stableford": 3,
          "si": 15
        },
        {
          "hole": 12,
          "par": 5,
          "sc": 8,
          "grossvp": 3,
          "result": "triple bogey",
          "stableford": 0,
          "si": 13
        }
      ],
      "context": {
        "streak_broken": "par_or_better",
        "importance_legacy": 4.1,
        "impact_metric": "stableford"
      }
    },
    {
      "id": "b24",
      "total": 21.11,
      "scope": "stretch",
      "type": "hot_stretch_gross",
      "round": 3,
      "course": "Prince's - Shore / Dunes",
      "headline": "David Mullin goes 4 holes without dropping a gross shot, 15-18 (R3)",
      "players": [
        "David Mullin"
      ],
      "scores": {
        "importance": 7.97,
        "rarity": 2.8699999999999997,
        "entertainment": 2.87
      },
      "mandatory": false,
      "holes": [
        {
          "hole": 15,
          "par": 5,
          "sc": 5,
          "grossvp": 0,
          "result": "par",
          "stableford": 3,
          "si": 9
        },
        {
          "hole": 16,
          "par": 4,
          "sc": 4,
          "grossvp": 0,
          "result": "par",
          "stableford": 3,
          "si": 17
        },
        {
          "hole": 17,
          "par": 3,
          "sc": 3,
          "grossvp": 0,
          "result": "par",
          "stableford": 3,
          "si": 11
        },
        {
          "hole": 18,
          "par": 4,
          "sc": 3,
          "grossvp": -1,
          "result": "birdie",
          "stableford": 4,
          "si": 7
        }
      ],
      "context": {
        "shots_gained": 1,
        "length": 4,
        "importance_legacy": 6.11,
        "impact_metric": "stableford"
      }
    },
    {
      "id": "b25",
      "total": 20.3,
      "scope": "hole",
      "type": "big_blowup",
      "round": 1,
      "course": "Royal Cinque Ports",
      "headline": "Alex Baker runs up a 10 (quintuple bogey) at the 16th (R1)",
      "players": [
        "Alex Baker"
      ],
      "scores": {
        "importance": 5.0,
        "rarity": 5,
        "entertainment": 6.3
      },
      "mandatory": true,
      "holes": [
        {
          "hole": 16,
          "par": 5,
          "sc": 10,
          "grossvp": 5,
          "result": "quintuple bogey",
          "stableford": 0,
          "si": 7
        }
      ],
      "context": {
        "is_player_par_worst": false,
        "is_teg_par_worst": false,
        "importance_legacy": 4.4,
        "impact_metric": "stableford"
      }
    },
    {
      "id": "b26",
      "total": 20.26,
      "scope": "stretch",
      "type": "hot_stretch_gross",
      "round": 4,
      "course": "Prince's - Shore / Dunes",
      "headline": "Jon Baker goes 2 holes without dropping a gross shot, 5-6 (R4)",
      "players": [
        "Jon Baker"
      ],
      "scores": {
        "importance": 8.61,
        "rarity": 1.6099999999999999,
        "entertainment": 1.7479999999999998
      },
      "mandatory": false,
      "holes": [
        {
          "hole": 5,
          "par": 3,
          "sc": 3,
          "grossvp": 0,
          "result": "par",
          "stableford": 2,
          "si": 18
        },
        {
          "hole": 6,
          "par": 4,
          "sc": 3,
          "grossvp": -1,
          "result": "birdie",
          "stableford": 3,
          "si": 14
        }
      ],
      "context": {
        "shots_gained": 1,
        "length": 2,
        "importance_legacy": 5.91,
        "impact_metric": "stableford"
      }
    },
    {
      "id": "b27",
      "total": 20.12,
      "scope": "stretch",
      "type": "hot_stretch_gross",
      "round": 4,
      "course": "Prince's - Shore / Dunes",
      "headline": "Alex Baker goes 3 holes without dropping a gross shot, 1-3 (R4)",
      "players": [
        "Alex Baker"
      ],
      "scores": {
        "importance": 8.28,
        "rarity": 1.89,
        "entertainment": 2.052
      },
      "mandatory": false,
      "holes": [
        {
          "hole": 1,
          "par": 4,
          "sc": 4,
          "grossvp": 0,
          "result": "par",
          "stableford": 4,
          "si": 6
        },
        {
          "hole": 2,
          "par": 5,
          "sc": 5,
          "grossvp": 0,
          "result": "par",
          "stableford": 3,
          "si": 12
        },
        {
          "hole": 3,
          "par": 3,
          "sc": 3,
          "grossvp": 0,
          "result": "par",
          "stableford": 3,
          "si": 16
        }
      ],
      "context": {
        "shots_gained": 0,
        "length": 3,
        "importance_legacy": 6.03,
        "impact_metric": "stableford"
      }
    },
    {
      "id": "b28",
      "total": 19.82,
      "scope": "stretch",
      "type": "hot_stretch_gross",
      "round": 4,
      "course": "Prince's - Shore / Dunes",
      "headline": "Alex Baker goes 2 holes without dropping a gross shot, 6-7 (R4)",
      "players": [
        "Alex Baker"
      ],
      "scores": {
        "importance": 8.72,
        "rarity": 1.26,
        "entertainment": 1.368
      },
      "mandatory": false,
      "holes": [
        {
          "hole": 6,
          "par": 4,
          "sc": 4,
          "grossvp": 0,
          "result": "par",
          "stableford": 3,
          "si": 14
        },
        {
          "hole": 7,
          "par": 4,
          "sc": 4,
          "grossvp": 0,
          "result": "par",
          "stableford": 4,
          "si": 2
        }
      ],
      "context": {
        "shots_gained": 0,
        "length": 2,
        "importance_legacy": 5.77,
        "impact_metric": "stableford"
      }
    },
    {
      "id": "b29",
      "total": 19.7,
      "scope": "stretch",
      "type": "hot_stretch_gross",
      "round": 4,
      "course": "Prince's - Shore / Dunes",
      "headline": "Gregg Williams goes 2 holes without dropping a gross shot, 5-6 (R4)",
      "players": [
        "Gregg Williams"
      ],
      "scores": {
        "importance": 8.61,
        "rarity": 1.26,
        "entertainment": 1.4760000000000002
      },
      "mandatory": false,
      "holes": [
        {
          "hole": 5,
          "par": 3,
          "sc": 3,
          "grossvp": 0,
          "result": "par",
          "stableford": 2,
          "si": 18
        },
        {
          "hole": 6,
          "par": 4,
          "sc": 4,
          "grossvp": 0,
          "result": "par",
          "stableford": 3,
          "si": 14
        }
      ],
      "context": {
        "shots_gained": 0,
        "length": 2,
        "importance_legacy": 5.17,
        "impact_metric": "stableford"
      }
    },
    {
      "id": "b30",
      "total": 19.66,
      "scope": "hole",
      "type": "big_blowup",
      "round": 2,
      "course": "Littlestone",
      "headline": "Alex Baker runs up a 8 (quadruple bogey) at the 8th (R2)",
      "players": [
        "Alex Baker"
      ],
      "scores": {
        "importance": 5.58,
        "rarity": 4,
        "entertainment": 5.3
      },
      "mandatory": false,
      "holes": [
        {
          "hole": 8,
          "par": 4,
          "sc": 8,
          "grossvp": 4,
          "result": "quadruple bogey",
          "stableford": 0,
          "si": 12
        }
      ],
      "context": {
        "is_player_par_worst": false,
        "is_teg_par_worst": false,
        "importance_legacy": 4.4,
        "impact_metric": "stableford"
      }
    },
    {
      "id": "b31",
      "total": 19.6,
      "scope": "tournament",
      "type": "jacket_pb",
      "round": null,
      "course": null,
      "headline": "Gregg Williams posts a personal-best Gross total: +76",
      "players": [
        "Gregg Williams"
      ],
      "scores": {
        "importance": 5.0,
        "rarity": 7.0,
        "entertainment": 4.0
      },
      "mandatory": true,
      "holes": [],
      "context": {
        "score": 76,
        "player_rank": 1,
        "metric": "gross"
      }
    },
    {
      "id": "b32",
      "total": 19.4,
      "scope": "tournament",
      "type": "wooden_spoon",
      "round": null,
      "course": null,
      "headline": "Jon Baker collects the Wooden Spoon (125 pts)",
      "players": [
        "Jon Baker"
      ],
      "scores": {
        "importance": 5.0,
        "rarity": 3.0,
        "entertainment": 7.0
      },
      "mandatory": true,
      "holes": [],
      "context": {
        "score": 125,
        "trophy_metric": "stableford"
      }
    },
    {
      "id": "b33",
      "total": 19.28,
      "scope": "hole",
      "type": "big_blowup",
      "round": 2,
      "course": "Littlestone",
      "headline": "Alex Baker runs up a 9 (quadruple bogey) at the 5th (R2)",
      "players": [
        "Alex Baker"
      ],
      "scores": {
        "importance": 5.39,
        "rarity": 4,
        "entertainment": 5.3
      },
      "mandatory": false,
      "holes": [
        {
          "hole": 5,
          "par": 5,
          "sc": 9,
          "grossvp": 4,
          "result": "quadruple bogey",
          "stableford": 0,
          "si": 16
        }
      ],
      "context": {
        "is_player_par_worst": false,
        "is_teg_par_worst": false,
        "importance_legacy": 4.4,
        "impact_metric": "stableford"
      }
    },
    {
      "id": "b34",
      "total": 19.24,
      "scope": "stretch",
      "type": "hot_stretch_net",
      "round": 3,
      "course": "Prince's - Shore / Dunes",
      "headline": "Gregg Williams piles up 9 points, holes 9-11 (R3)",
      "players": [
        "Gregg Williams"
      ],
      "scores": {
        "importance": 7.28,
        "rarity": 2.16,
        "entertainment": 2.9520000000000004
      },
      "mandatory": false,
      "holes": [
        {
          "hole": 9,
          "par": 4,
          "sc": 4,
          "grossvp": 0,
          "result": "par",
          "stableford": 3,
          "si": 10
        },
        {
          "hole": 10,
          "par": 4,
          "sc": 4,
          "grossvp": 0,
          "result": "par",
          "stableford": 3,
          "si": 3
        },
        {
          "hole": 11,
          "par": 3,
          "sc": 3,
          "grossvp": 0,
          "result": "par",
          "stableford": 3,
          "si": 15
        }
      ],
      "context": {
        "points_gained": 9,
        "metric": "stableford",
        "length": 3,
        "importance_legacy": 4.61,
        "impact_metric": "stableford"
      }
    },
    {
      "id": "b35",
      "total": 19.1,
      "scope": "stretch",
      "type": "hot_stretch_gross",
      "round": 3,
      "course": "Prince's - Shore / Dunes",
      "headline": "Jon Baker goes 3 holes without dropping a gross shot, 14-16 (R3)",
      "players": [
        "Jon Baker"
      ],
      "scores": {
        "importance": 7.77,
        "rarity": 1.89,
        "entertainment": 2.052
      },
      "mandatory": false,
      "holes": [
        {
          "hole": 14,
          "par": 4,
          "sc": 4,
          "grossvp": 0,
          "result": "par",
          "stableford": 3,
          "si": 5
        },
        {
          "hole": 15,
          "par": 5,
          "sc": 5,
          "grossvp": 0,
          "result": "par",
          "stableford": 3,
          "si": 9
        },
        {
          "hole": 16,
          "par": 4,
          "sc": 4,
          "grossvp": 0,
          "result": "par",
          "stableford": 2,
          "si": 17
        }
      ],
      "context": {
        "shots_gained": 0,
        "length": 3,
        "importance_legacy": 5.03,
        "impact_metric": "stableford"
      }
    },
    {
      "id": "b36",
      "total": 19.04,
      "scope": "stretch",
      "type": "hot_stretch_gross",
      "round": 4,
      "course": "Prince's - Shore / Dunes",
      "headline": "Gregg Williams goes 2 holes without dropping a gross shot, 2-3 (R4)",
      "players": [
        "Gregg Williams"
      ],
      "scores": {
        "importance": 8.28,
        "rarity": 1.26,
        "entertainment": 1.4760000000000002
      },
      "mandatory": false,
      "holes": [
        {
          "hole": 2,
          "par": 5,
          "sc": 5,
          "grossvp": 0,
          "result": "par",
          "stableford": 3,
          "si": 12
        },
        {
          "hole": 3,
          "par": 3,
          "sc": 3,
          "grossvp": 0,
          "result": "par",
          "stableford": 3,
          "si": 16
        }
      ],
      "context": {
        "shots_gained": 0,
        "length": 2,
        "importance_legacy": 5.17,
        "impact_metric": "stableford"
      }
    },
    {
      "id": "b37",
      "total": 18.74,
      "scope": "round",
      "type": "round_leadership",
      "round": 3,
      "course": "Prince's - Shore / Dunes",
      "headline": "After R3: David Mullin leads the Trophy (gap 0 on Stableford); David Mullin leads the Jacket",
      "players": [
        "David Mullin",
        "David Mullin"
      ],
      "scores": {
        "importance": 7.97,
        "rarity": 1.0,
        "entertainment": 2.0
      },
      "mandatory": false,
      "holes": [],
      "context": {
        "trophy_leader": "David Mullin",
        "jacket_leader": "David Mullin",
        "importance_legacy": 5.2,
        "impact_metric": "stableford"
      }
    },
    {
      "id": "b38",
      "total": 18.29,
      "scope": "stretch",
      "type": "hot_stretch_gross",
      "round": 3,
      "course": "Prince's - Shore / Dunes",
      "headline": "Gregg Williams goes 3 holes without dropping a gross shot, 9-11 (R3)",
      "players": [
        "Gregg Williams"
      ],
      "scores": {
        "importance": 7.28,
        "rarity": 1.89,
        "entertainment": 2.2140000000000004
      },
      "mandatory": false,
      "holes": [
        {
          "hole": 9,
          "par": 4,
          "sc": 4,
          "grossvp": 0,
          "result": "par",
          "stableford": 3,
          "si": 10
        },
        {
          "hole": 10,
          "par": 4,
          "sc": 4,
          "grossvp": 0,
          "result": "par",
          "stableford": 3,
          "si": 3
        },
        {
          "hole": 11,
          "par": 3,
          "sc": 3,
          "grossvp": 0,
          "result": "par",
          "stableford": 3,
          "si": 15
        }
      ],
      "context": {
        "shots_gained": 0,
        "length": 3,
        "importance_legacy": 4.39,
        "impact_metric": "stableford"
      }
    },
    {
      "id": "b39",
      "total": 18.04,
      "scope": "hole",
      "type": "big_blowup",
      "round": 1,
      "course": "Royal Cinque Ports",
      "headline": "Alex Baker runs up a 8 (quadruple bogey) at the 11th (R1)",
      "players": [
        "Alex Baker"
      ],
      "scores": {
        "importance": 4.77,
        "rarity": 4,
        "entertainment": 5.3
      },
      "mandatory": false,
      "holes": [
        {
          "hole": 11,
          "par": 4,
          "sc": 8,
          "grossvp": 4,
          "result": "quadruple bogey",
          "stableford": 0,
          "si": 3
        }
      ],
      "context": {
        "is_player_par_worst": false,
        "is_teg_par_worst": false,
        "importance_legacy": 4.4,
        "impact_metric": "stableford"
      }
    },
    {
      "id": "b40",
      "total": 18.02,
      "scope": "stretch",
      "type": "hot_stretch_gross",
      "round": 3,
      "course": "Prince's - Shore / Dunes",
      "headline": "Gregg Williams goes 2 holes without dropping a gross shot, 15-16 (R3)",
      "players": [
        "Gregg Williams"
      ],
      "scores": {
        "importance": 7.77,
        "rarity": 1.26,
        "entertainment": 1.4760000000000002
      },
      "mandatory": false,
      "holes": [
        {
          "hole": 15,
          "par": 5,
          "sc": 5,
          "grossvp": 0,
          "result": "par",
          "stableford": 3,
          "si": 9
        },
        {
          "hole": 16,
          "par": 4,
          "sc": 4,
          "grossvp": 0,
          "result": "par",
          "stableford": 3,
          "si": 17
        }
      ],
      "context": {
        "shots_gained": 0,
        "length": 2,
        "importance_legacy": 4.17,
        "impact_metric": "stableford"
      }
    },
    {
      "id": "b41",
      "total": 17.86,
      "scope": "hole",
      "type": "big_blowup",
      "round": 1,
      "course": "Royal Cinque Ports",
      "headline": "Gregg Williams runs up a 9 (quadruple bogey) at the 3rd (R1)",
      "players": [
        "Gregg Williams"
      ],
      "scores": {
        "importance": 4.53,
        "rarity": 4,
        "entertainment": 5.6
      },
      "mandatory": false,
      "holes": [
        {
          "hole": 3,
          "par": 5,
          "sc": 9,
          "grossvp": 4,
          "result": "quadruple bogey",
          "stableford": 0,
          "si": 4
        }
      ],
      "context": {
        "is_player_par_worst": false,
        "is_teg_par_worst": false,
        "importance_legacy": 3.8,
        "impact_metric": "stableford"
      }
    },
    {
      "id": "b42",
      "total": 17.8,
      "scope": "round",
      "type": "round_leadership",
      "round": 4,
      "course": "Prince's - Shore / Dunes",
      "headline": "After R4: David Mullin leads the Trophy (gap 0 on Stableford); David Mullin leads the Jacket",
      "players": [
        "David Mullin",
        "David Mullin"
      ],
      "scores": {
        "importance": 7.5,
        "rarity": 1.0,
        "entertainment": 2.0
      },
      "mandatory": false,
      "holes": [],
      "context": {
        "trophy_leader": "David Mullin",
        "jacket_leader": "David Mullin",
        "importance_legacy": 6.8,
        "impact_metric": "stableford"
      }
    },
    {
      "id": "b43",
      "total": 17.54,
      "scope": "round",
      "type": "round_swing",
      "round": 3,
      "course": "Prince's - Shore / Dunes",
      "headline": "Gregg Williams follows a poor R2 with a strong R3",
      "players": [
        "Gregg Williams"
      ],
      "scores": {
        "importance": 7.97,
        "rarity": 0.78,
        "entertainment": 0.9790000000000002
      },
      "mandatory": false,
      "holes": [],
      "context": {
        "direction": "up",
        "delta": 12,
        "prev_round": 2,
        "prev_score": 27,
        "curr_score": 39,
        "importance_legacy": 3.1,
        "impact_metric": "stableford"
      }
    },
    {
      "id": "b44",
      "total": 16.96,
      "scope": "hole",
      "type": "big_blowup",
      "round": 4,
      "course": "Prince's - Shore / Dunes",
      "headline": "Jon Baker runs up a 8 (quadruple bogey) at the 18th (R4)",
      "players": [
        "Jon Baker"
      ],
      "scores": {
        "importance": 4.23,
        "rarity": 4,
        "entertainment": 5.3
      },
      "mandatory": false,
      "holes": [
        {
          "hole": 18,
          "par": 4,
          "sc": 8,
          "grossvp": 4,
          "result": "quadruple bogey",
          "stableford": 0,
          "si": 7
        }
      ],
      "context": {
        "is_player_par_worst": false,
        "is_teg_par_worst": false,
        "importance_legacy": 4.4,
        "impact_metric": "stableford"
      }
    },
    {
      "id": "b45",
      "total": 16.56,
      "scope": "stretch",
      "type": "hot_stretch_gross",
      "round": 3,
      "course": "Prince's - Shore / Dunes",
      "headline": "Jon Baker goes 2 holes without dropping a gross shot, 8-9 (R3)",
      "players": [
        "Jon Baker"
      ],
      "scores": {
        "importance": 7.09,
        "rarity": 1.26,
        "entertainment": 1.368
      },
      "mandatory": false,
      "holes": [
        {
          "hole": 8,
          "par": 5,
          "sc": 5,
          "grossvp": 0,
          "result": "par",
          "stableford": 3,
          "si": 8
        },
        {
          "hole": 9,
          "par": 4,
          "sc": 4,
          "grossvp": 0,
          "result": "par",
          "stableford": 3,
          "si": 10
        }
      ],
      "context": {
        "shots_gained": 0,
        "length": 2,
        "importance_legacy": 4.77,
        "impact_metric": "stableford"
      }
    },
    {
      "id": "b46",
      "total": 16.53,
      "scope": "stretch",
      "type": "hot_stretch_gross",
      "round": 4,
      "course": "Prince's - Shore / Dunes",
      "headline": "David Mullin goes 2 holes without dropping a gross shot, 2-3 (R4)",
      "players": [
        "David Mullin"
      ],
      "scores": {
        "importance": 7.13,
        "rarity": 1.26,
        "entertainment": 1.2600000000000002
      },
      "mandatory": false,
      "holes": [
        {
          "hole": 2,
          "par": 5,
          "sc": 5,
          "grossvp": 0,
          "result": "par",
          "stableford": 3,
          "si": 12
        },
        {
          "hole": 3,
          "par": 3,
          "sc": 3,
          "grossvp": 0,
          "result": "par",
          "stableford": 3,
          "si": 16
        }
      ],
      "context": {
        "shots_gained": 0,
        "length": 2,
        "importance_legacy": 6.38,
        "impact_metric": "stableford"
      }
    },
    {
      "id": "b47",
      "total": 15.8,
      "scope": "stretch",
      "type": "cold_stretch_gross",
      "round": 2,
      "course": "Littlestone",
      "headline": "Alex Baker bleeds 12 shots, holes 2-5 (R2)",
      "players": [
        "Alex Baker"
      ],
      "scores": {
        "importance": 5.39,
        "rarity": 2.4,
        "entertainment": 3.0999999999999996
      },
      "mandatory": false,
      "holes": [
        {
          "hole": 2,
          "par": 4,
          "sc": 7,
          "grossvp": 3,
          "result": "triple bogey",
          "stableford": 1,
          "si": 4
        },
        {
          "hole": 3,
          "par": 4,
          "sc": 6,
          "grossvp": 2,
          "result": "double bogey",
          "stableford": 1,
          "si": 10
        },
        {
          "hole": 4,
          "par": 4,
          "sc": 7,
          "grossvp": 3,
          "result": "triple bogey",
          "stableford": 1,
          "si": 2
        },
        {
          "hole": 5,
          "par": 5,
          "sc": 9,
          "grossvp": 4,
          "result": "quadruple bogey",
          "stableford": 0,
          "si": 16
        }
      ],
      "context": {
        "shots_dropped": 12,
        "length": 4,
        "importance_legacy": 5.4,
        "impact_metric": "stableford"
      }
    },
    {
      "id": "b48",
      "total": 15.76,
      "scope": "stretch",
      "type": "hot_stretch_net",
      "round": 1,
      "course": "Royal Cinque Ports",
      "headline": "David Mullin piles up 13 points, holes 9-12 (R1)",
      "players": [
        "David Mullin"
      ],
      "scores": {
        "importance": 4.81,
        "rarity": 3.12,
        "entertainment": 3.6400000000000006
      },
      "mandatory": false,
      "holes": [
        {
          "hole": 9,
          "par": 4,
          "sc": 4,
          "grossvp": 0,
          "result": "par",
          "stableford": 3,
          "si": 10
        },
        {
          "hole": 10,
          "par": 4,
          "sc": 3,
          "grossvp": -1,
          "result": "birdie",
          "stableford": 4,
          "si": 11
        },
        {
          "hole": 11,
          "par": 4,
          "sc": 4,
          "grossvp": 0,
          "result": "par",
          "stableford": 3,
          "si": 3
        },
        {
          "hole": 12,
          "par": 4,
          "sc": 4,
          "grossvp": 0,
          "result": "par",
          "stableford": 3,
          "si": 13
        }
      ],
      "context": {
        "points_gained": 13,
        "metric": "stableford",
        "length": 4,
        "importance_legacy": 6.46,
        "impact_metric": "stableford"
      }
    },
    {
      "id": "b49",
      "total": 15.72,
      "scope": "stretch",
      "type": "collapse_after_steady",
      "round": 1,
      "course": "Royal Cinque Ports",
      "headline": "David Mullin's steady run ends with a double bogey at the 13th (R1)",
      "players": [
        "David Mullin"
      ],
      "scores": {
        "importance": 4.86,
        "rarity": 2.5,
        "entertainment": 4.0
      },
      "mandatory": false,
      "holes": [
        {
          "hole": 9,
          "par": 4,
          "sc": 4,
          "grossvp": 0,
          "result": "par",
          "stableford": 3,
          "si": 10
        },
        {
          "hole": 10,
          "par": 4,
          "sc": 3,
          "grossvp": -1,
          "result": "birdie",
          "stableford": 4,
          "si": 11
        },
        {
          "hole": 11,
          "par": 4,
          "sc": 4,
          "grossvp": 0,
          "result": "par",
          "stableford": 3,
          "si": 3
        },
        {
          "hole": 12,
          "par": 4,
          "sc": 4,
          "grossvp": 0,
          "result": "par",
          "stableford": 3,
          "si": 13
        },
        {
          "hole": 13,
          "par": 4,
          "sc": 6,
          "grossvp": 2,
          "result": "double bogey",
          "stableford": 1,
          "si": 5
        }
      ],
      "context": {
        "streak_broken": "par_or_better",
        "importance_legacy": 5.0,
        "impact_metric": "stableford"
      }
    },
    {
      "id": "b50",
      "total": 15.63,
      "scope": "stretch",
      "type": "cold_stretch_gross",
      "round": 3,
      "course": "Prince's - Shore / Dunes",
      "headline": "Alex Baker bleeds 6 shots, holes 1-3 (R3)",
      "players": [
        "Alex Baker"
      ],
      "scores": {
        "importance": 6.56,
        "rarity": 1.2,
        "entertainment": 1.5499999999999998
      },
      "mandatory": false,
      "holes": [
        {
          "hole": 1,
          "par": 4,
          "sc": 6,
          "grossvp": 2,
          "result": "double bogey",
          "stableford": 2,
          "si": 6
        },
        {
          "hole": 2,
          "par": 5,
          "sc": 7,
          "grossvp": 2,
          "result": "double bogey",
          "stableford": 1,
          "si": 12
        },
        {
          "hole": 3,
          "par": 3,
          "sc": 5,
          "grossvp": 2,
          "result": "double bogey",
          "stableford": 1,
          "si": 16
        }
      ],
      "context": {
        "shots_dropped": 6,
        "length": 3,
        "importance_legacy": 4.83,
        "impact_metric": "stableford"
      }
    },
    {
      "id": "cr01",
      "total": 10.0,
      "scope": "round",
      "type": "course_record_low",
      "round": 4,
      "course": "Prince's - Shore / Dunes",
      "headline": "new Prince's - Shore / Dunes course record: 83 gross by Jon Baker in R4, beating the prior record of 85 (across 5 prior visits)",
      "players": [
        "Jon Baker"
      ],
      "scores": {
        "importance": 10.0,
        "rarity": 10.0,
        "entertainment": 7.0
      },
      "mandatory": true,
      "holes": [],
      "context": {
        "gross": 83,
        "prior_record": 85,
        "n_prior_visits": 5,
        "summary_fact": "new Prince's - Shore / Dunes course record: 83 gross by Jon Baker in R4, beating the prior record of 85 (across 5 prior visits)"
      }
    }
  ]
}
