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
- player_history: per-player cross-TEG history (win counts, last-4 finishing positions, `notable_milestones`). Use the `notable_milestones` strings as factual anchors in storyline `why_it_matters`/`shape` when they add genuine colour — e.g. "back-to-back Spoons going into this TEG" or "3 prior Trophy wins". The phrases are intentionally NEUTRAL — the writer flourishes ("bridesmaid", "nearly-man", "second twice over", etc.). Do NOT invent history not present in this field. Win counts cover TEGs BEFORE the current one; the at-a-glance box handles the current winner's total automatically.
- player_course_history: per-player per-course history relative to prior TEGs. Keyed `[player][course]`. Each entry carries `summary_facts` — neutral factual phrases like "Mullin's 11th visit to Boavista", "Mullin's prior best at Boavista: 82 gross (TEG 5)", "Mullin's new personal best at Boavista in R1", "Williams was 14 shots better than his last visit". Only foreground the ones that genuinely add to the story; first-visits to brand-new courses rarely earn prose, big improvements / new course PBs usually do.
- Beats with id `cr*` (course record), `sr*` (streak record) or `sc*` (score-count record) are all-time TEG records set in THIS tournament. These are MANDATORY — see the coverage rule below.

THE STORYLINE HIERARCHY — read this before choosing anything else.

**The report is the winner's story.** The Trophy winner's week is the PRIMARY storyline, and the report's job is to make clear how and why they won — drawing on `win_anatomy`. That story is told as a celebration, tongue-in-cheek by all means, and it takes one of two shapes (often both):

  (a) **what the champion did well** — the round that broke the field, the four steady ones, the stretch where they went clear; or
  (b) **where their rivals fell short** — when `win_anatomy.attribution` is `inherited`, say so plainly. "Patterson lost it" is often the better and funnier story, and it is honest. But the champion is still the one who capitalised: frame them as the man who was there to take it, never as a passive beneficiary.

Then the SECONDARY storylines, roughly in this order of prominence: the Green Jacket (gross), the Wooden Spoon and how comprehensively it was lost, and the rest of the field humiliating themselves. Third and fourth storylines are welcome where the material is there.

**This ordering is a strong default, not a cage.** Depart from it when the tournament genuinely offers something better — but the departure must still explain why the champion won, and you must say what you did in `storyline_note`. A legitimate departure keeps the winner in frame: "the course beat everyone, and one man by slightly less" is a fine opening. "The champion was poor" is not a storyline.

YOUR JOB:
- Choose the story: one clear `theme` that runs through the whole report.
- Choose an `opening_hook` — a one-line description of what the report opens with, and why. Favour non-chronological framing when the climax matters more than the build-up, or when the real story is a theme that cuts across rounds.

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
- `why_the_champion_won`: **ALWAYS populated**, one line, grounded in `win_anatomy`. Name the mechanism, not the outcome. "Won by 8" is not an answer; "two best-in-field rounds either side of a wobble, while the only man close to him gave back more than he did" is. Say plainly if the answer is that the rivals lost it.
- `storyline_note`: only if you departed from the Trophy-leads default — one line on what led instead and why it was the better story. Leave empty otherwise.
- `title` + a few `title_candidates`; record the resolved `tone`.

- `prominent_vehicle` and `prominent_palette`: **BOTH ALWAYS populated. They are two different axes — do not confuse them.**

  - `prominent_vehicle` = **the FRAME**, chosen from the `narrative_vehicles` menu above (and it must also appear in your `narrative_vehicles` list). This is the one the close-finish HARD RULE constrains.
  - `prominent_palette` = **the CONTEXT MATERIAL** the writer foregrounds, one of: `cross_teg_career` | `course_history` | `venue_character` | `decisive_moment` | `player_thread` | `records` | `foreshadow_payoff`. The writer is required to make at least one palette item prominent; you tell them which.

  A report is normally framed one way and foregrounds material from another — e.g. framed `counterfactual` while foregrounding `cross_teg_career`. Choose each on its own merits; if several feel equal, prefer the combination that varies the framing across reports.

- `trophy_storyline`, `jacket_storyline`, `spoon_storyline`: **ALWAYS populated, one each, regardless of how good you judge them to be.** How the Trophy/Jacket was won, and how the Spoon was "won" (i.e. who finished last and how). These are mandatory whether or not they turn out to be the best story in the tournament — they are guaranteed material for the "how the trophies were won" section, and the bar `discovered_storylines` below must clear to earn a place. For `trophy_storyline` specifically: find the MOST COMPELLING way to tell it, not a flat recitation of who led each round — this is the report's lead.

- `discovered_storylines`: **1 to 3 ADDITIONAL storylines**, found independently in the beats, that you judge to be genuinely the most compelling stories in this tournament — not necessarily about who won a competition. A player's arc across rounds, a rivalry, a course, a recurring pattern are all fair game. Only include ones supported by real beats spanning more than one round that you would actually call a story. **If nothing clears that bar, return fewer — even zero.** A storyline that just restates `trophy_storyline`/`jacket_storyline`/`spoon_storyline` from a different angle does not count as discovered; a manufactured subplot is worse than an honest absence.

  **The quality bar is real entertainment value, not mere eligibility.** "Spans 2+ rounds and has beats" is the eligibility floor, not the bar. Before including a storyline, check it actually delivers on at least one of: humour, intrigue (a question the reader wants answered), drama (real stakes, a turn), or importance (genuinely shaped the tournament). A storyline that is technically grounded but flat — competent golf, no texture — does not clear the bar even if it is the only candidate you found. Score every storyline's `humour_score` honestly; do not inflate it because a section needs filling.

  **Records are legitimate storyline SUBJECTS, not just facts to mention.** A `cr*` (course record), `sr*` (streak record), or `sc*` (score-count record) mandatory beat can anchor its own discovered storyline when the material supports it — "Anatomy of a TEG record" (the round or stretch that produced it, what surrounded it) is a good shape for one. Don't treat these beats as filler that just needs a mention somewhere; if one is the most interesting thing that happened, let it lead.

  **At least one storyline in the report — trophy/jacket/spoon or discovered — should bring genuine humour**, scored `humour_score` >= 7. This is usually the Spoon story (disaster is funnier than triumph) or a discovered catalogue-of-failure storyline, but use whichever one the material actually supports. Do not force humour onto a storyline that doesn't have it; find the one that does.

  Find these from `beats` and `competition_arcs` directly — do NOT lean on `win_anatomy` or `candidate_threads` to find the SUBJECT of a storyline. Measured (2026-08-18, three TEGs, blind-judged): giving an editor those two as hints added no storylines it didn't already find without them, and consistently produced MORE invented specifics (head-to-head records, precise gaps, visit counts, "best in the field" claims not in the data) — more material in context gave more surface to compute a plausible-sounding wrong number from. `win_anatomy` stays the right source for `why_the_champion_won` specifically; keep it out of storyline discovery.

  Every `DraftedStoryline` needs: `subject`, `why_it_matters` (one sentence), `shape` (setup -> turn -> resolution, 2-3 sentences), `beat_ids` (the specific beats it's built from — every ID is checked against the bundle, so an invented one is caught), `compelling_score` (1-10: how good a STORY this is, not how much it mattered to the standings), and `humour_score` (1-10: how genuinely FUNNY this storyline is to tell — score it honestly, most storylines are not funny and should score low). **Never state a comparative or aggregate claim** ("beat X head-to-head in N of M rounds", "Nth visit to this course", "best in the field twice") **unless that exact figure appears in a bundle field** — this is the specific failure mode measured above, not a generic reminder.

- `body_fallback`: **"none" is the default and the common case** — the trophy/jacket/ spoon anatomy stories stand alone as the report's spine, with `discovered_storylines` adding 0-3 more. Use `"player_by_player"` or `"round_by_round"` ONLY when `discovered_storylines` is empty or thin (fewer than you'd like, none clearing the quality bar above) but there is still real material worth surfacing beyond the bare three anatomy stories. These two fallbacks sit at the SAME tier as each other and BELOW the discovered-storylines approach — never choose a fallback over a storyline that actually clears the bar.
  - `"player_by_player"`: one section per notable player's tournament, built from their own beats. Choose this when several players each had a real week worth telling but their stories don't share a throughline.
  - `"round_by_round"`: one section per round, chronological. This should be RARE — only when the material genuinely resists any other organisation (no throughline, no player's week coheres on its own). Prefer `"player_by_player"` when in doubt.

- **MANDATORY BEAT COVERAGE.** Every beat marked `"mandatory": true` in the bundle (course/streak/score-count records, personal bests, rare feats, any double-figure gross score, and the three competition spine outcomes) MUST appear in the `beat_ids` of at least one storyline — `trophy_storyline`, `jacket_storyline`, `spoon_storyline`, or a `discovered_storyline`. There is no separate must-include list in this schema: coverage is checked directly against your storylines' `beat_ids`, so a mandatory beat that fits nowhere else still belongs in whichever storyline is closest to it.

SELECTION PRINCIPLES:
- Favour high-importance beats for the spine, high-rarity for headlines and records, high-entertainment for colour and running threads.
- Foreground turning points, rare feats, and genuine colour; suppress filler.
- Early-round lead changes, while the field is still bunched, are ROUTINE — not drama. Do not headline or dramatise the opening exchanges of the tournament; they rarely matter to the outcome. The lead changes that matter are the late, decisive ones.

RULES:
- Use ONLY the supplied data. Never invent scores, holes, players, or events. If unsure, leave it out. The players will catch any fabrication.
- **Stableford and Gross measure DIFFERENT things** — Stableford is handicap-adjusted, Gross is raw shots. A player leading one and trailing the other is normal handicapping, NOT paradox. Do not plan a theme or player arc that frames the split as schizophrenic, contradictory, a "unique double", or any kind of head-scratcher. The shape can be interesting (e.g. Jacket runner-up while bottom of the Trophy) but it is not weird.
- **TEG has NO countback, NO tiebreakers, NO playoff.** Lead changes happen because players accumulate more points (Stableford / Gross). Never plan a theme or note that invokes "countback", "tiebreaker", or "playoff" — those mechanisms do not exist in TEG.
- **Stroke index (SI) as optional colour.** Beat `holes` evidence may include an `si` field. Use it sparingly when planning storylines: SI 1 = the hardest hole on the course; SI 18 = the easiest; SI 2–3 = one of the hardest; SI 16–17 = one of the easiest. SI 4–15: not noteworthy — ignore. Never force SI commentary; only note it when it genuinely adds to the drama or irony.
- **Days and weeks.** A TEG is a tournament of 4 rounds over 4 consecutive days. NEVER plan around the framing "a week" or invoke weekdays as a structural device. Verified weekday names live in `venue.rounds[i].weekday`; if you mention a weekday in a storyline, take it verbatim from `venue.rounds[i].weekday`. For everything else — cross-storyline references — use the round number ("R3", "Round 3"), NEVER a weekday.
- Output only the structured plan.

---

# USER MESSAGE

Plan the report for the following TEG. Use ONLY this data.

{
  "teg": 16,
  "tone": "house",
  "trophy_metric": "stableford",
  "venue": {
    "teg_num": 16,
    "area": "Lisbon Coast, Portugal",
    "year": 2023,
    "area_visit": "TEG's 5th visit to Lisbon Coast, Portugal",
    "area_visit_n": 5,
    "n_rounds": 4,
    "rounds": [
      {
        "round": 1,
        "course": "Oitavos Dunes",
        "date": "07/10/2023",
        "weekday": "Saturday",
        "visit_n": 3,
        "visit_str": "the 3rd TEG round at this venue",
        "full_name": "Oitavos Dunes Natural Links Golf",
        "location": "Cascais, Lisbon Coast, Portugal",
        "type": "Links",
        "designer": "Arthur Hills",
        "description": "Portugal's premier golf course, a pure links design along the rugged Atlantic coast. Features natural dunes and has hosted multiple Portuguese Opens."
      },
      {
        "round": 2,
        "course": "Troia",
        "date": "08/10/2023",
        "weekday": "Sunday",
        "visit_n": 1,
        "visit_str": "a new course for TEG",
        "full_name": "Troia Golf Championship Course",
        "location": "Troia Peninsula, Setubal, Portugal",
        "type": "Championship Course",
        "designer": "Robert Trent Jones Sr.",
        "description": "A prestigious Robert Trent Jones Sr. design on the Troia Peninsula. Consistently ranked among Europe's finest courses, featuring RTJ's signature strategic design."
      },
      {
        "round": 3,
        "course": "Penha Longa",
        "date": "09/10/2023",
        "weekday": "Monday",
        "visit_n": 3,
        "visit_str": "the 3rd TEG round at this venue",
        "full_name": "The Ritz-Carlton Penha Longa - Atlantic Course",
        "location": "Sintra, Lisbon Coast, Portugal",
        "type": "Mountain Parkland",
        "designer": "Robert Trent Jones Jr.",
        "description": "A dramatic mountain course in the Sintra hills, known for its steep terrain and breathtaking coastal views. Considered one of Portugal's most challenging layouts."
      },
      {
        "round": 4,
        "course": "Estoril",
        "date": "10/10/2023",
        "weekday": "Tuesday",
        "visit_n": 2,
        "visit_str": "the 2nd TEG round at this venue",
        "full_name": "Estoril Golf Club",
        "location": "Estoril, Cascais, Portugal",
        "type": "Parkland",
        "designer": "Mackenzie Ross (redesign 1936)",
        "description": "Portugal's first golf club, a shorter classic parkland course emphasizing accuracy and course management. Charming tree-lined layout redesigned by Mackenzie Ross."
      }
    ]
  },
  "competition_arcs": {
    "trophy": {
      "label": "Trophy (Stableford)",
      "winner": "Stuart Neumann",
      "leader_by_round": [
        {
          "round": 1,
          "leader": "Stuart Neumann",
          "lead": 5
        },
        {
          "round": 2,
          "leader": "Stuart Neumann",
          "lead": 7
        },
        {
          "round": 3,
          "leader": "Stuart Neumann",
          "lead": 12
        },
        {
          "round": 4,
          "leader": "Stuart Neumann",
          "lead": 13
        }
      ],
      "winner_trajectory": [
        {
          "round": 1,
          "pos": 1,
          "gap": 0,
          "round_score": 39
        },
        {
          "round": 2,
          "pos": 1,
          "gap": 0,
          "round_score": 35
        },
        {
          "round": 3,
          "pos": 1,
          "gap": 0,
          "round_score": 39
        },
        {
          "round": 4,
          "pos": 1,
          "gap": 0,
          "round_score": 43
        }
      ],
      "lead_changes": [
        {
          "round": 1,
          "hole": 4,
          "player": "Gregg Williams",
          "outright": false,
          "significance": "routine"
        },
        {
          "round": 1,
          "hole": 5,
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
      "decisive_takeover": null
    },
    "jacket": {
      "label": "Green Jacket (Gross)",
      "winner": "Gregg Williams",
      "leader_by_round": [
        {
          "round": 1,
          "leader": "Gregg Williams",
          "lead": 3
        },
        {
          "round": 2,
          "leader": "Gregg Williams",
          "lead": 4
        },
        {
          "round": 3,
          "leader": "Gregg Williams",
          "lead": 14
        },
        {
          "round": 4,
          "leader": "Gregg Williams",
          "lead": 16
        }
      ],
      "winner_trajectory": [
        {
          "round": 1,
          "pos": 1,
          "gap": 0,
          "round_score": 18
        },
        {
          "round": 2,
          "pos": 1,
          "gap": 0,
          "round_score": 22
        },
        {
          "round": 3,
          "pos": 1,
          "gap": 0,
          "round_score": 15
        },
        {
          "round": 4,
          "pos": 1,
          "gap": 0,
          "round_score": 11
        }
      ],
      "lead_changes": [
        {
          "round": 1,
          "hole": 6,
          "player": "David Mullin",
          "outright": false,
          "significance": "routine"
        },
        {
          "round": 2,
          "hole": 11,
          "player": "Jon Baker",
          "outright": false,
          "significance": "routine"
        },
        {
          "round": 2,
          "hole": 14,
          "player": "Jon Baker",
          "outright": false,
          "significance": "routine"
        }
      ],
      "n_lead_changes": 3,
      "lead_change_summary": {
        "total": 3,
        "early_round1": 1,
        "final_round": 0,
        "outright": 0,
        "decisive": 0,
        "all_routine": true
      },
      "decisive_takeover": null
    },
    "spoon": {
      "label": "Wooden Spoon",
      "loser": "Alex Baker",
      "bottom_by_round": [
        {
          "round": 1,
          "bottom": "Alex Baker",
          "pos": 5
        },
        {
          "round": 2,
          "bottom": "Alex Baker",
          "pos": 5
        },
        {
          "round": 3,
          "bottom": "Alex Baker",
          "pos": 5
        },
        {
          "round": 4,
          "bottom": "Alex Baker",
          "pos": 5
        }
      ],
      "loser_trajectory": [
        {
          "round": 1,
          "pos": 5,
          "round_score": 29
        },
        {
          "round": 2,
          "pos": 5,
          "round_score": 32
        },
        {
          "round": 3,
          "pos": 5,
          "round_score": 33
        },
        {
          "round": 4,
          "pos": 5,
          "round_score": 33
        }
      ],
      "bottom_changes": [
        {
          "round": 1,
          "hole": 1,
          "player": "Alex Baker",
          "outright": true,
          "significance": "routine"
        },
        {
          "round": 1,
          "hole": 10,
          "player": "David Mullin",
          "outright": true,
          "significance": "routine"
        },
        {
          "round": 1,
          "hole": 11,
          "player": "Alex Baker",
          "outright": true,
          "significance": "routine"
        },
        {
          "round": 1,
          "hole": 13,
          "player": "David Mullin",
          "outright": true,
          "significance": "routine"
        },
        {
          "round": 1,
          "hole": 15,
          "player": "Alex Baker",
          "outright": true,
          "significance": "routine"
        },
        {
          "round": 2,
          "hole": 13,
          "player": "Alex Baker",
          "outright": true,
          "significance": "notable"
        }
      ],
      "n_bottom_changes": 6,
      "bottom_change_summary": {
        "total": 6,
        "early_round1": 5,
        "final_round": 0,
        "outright": 6,
        "decisive": 0,
        "all_routine": false
      },
      "decisive_drop": {
        "round": 2,
        "hole": 13,
        "player": "Alex Baker",
        "outright": true,
        "significance": "notable"
      }
    }
  },
  "win_anatomy": {
    "trophy": {
      "worst_round_position": 2,
      "field_size": 5,
      "consistency_rank": 3,
      "biggest_lead_blown": null,
      "subject": "Stuart Neumann",
      "runner_up": "Gregg Williams",
      "margin": 13.0,
      "attribution": "built",
      "shape": "volatile",
      "best_in_field_rounds": 3,
      "rounds_in_bottom_half": 0,
      "rounds": [
        {
          "round": 1,
          "score": 39.0,
          "position": 1,
          "standing": "best in the field",
          "vs_runner_up": 5.0
        },
        {
          "round": 2,
          "score": 35.0,
          "position": 1,
          "standing": "best in the field",
          "vs_runner_up": 5.0
        },
        {
          "round": 3,
          "score": 39.0,
          "position": 1,
          "standing": "best in the field",
          "vs_runner_up": 2.0
        },
        {
          "round": 4,
          "score": 43.0,
          "position": 2,
          "standing": "top half of the field",
          "vs_runner_up": 1.0
        }
      ],
      "rival_could_have_flipped_it": false,
      "summary_facts": [
        "Stuart Neumann beat Gregg Williams head-to-head in 4 of the 4 rounds",
        "Stuart Neumann won 3 of the 4 rounds outright",
        "Stuart Neumann never finished a round worse than 2nd of 5",
        "Stuart Neumann swung about more between rounds than most of the field",
        "even with an ordinary round instead of their worst, Gregg Williams would still have lost"
      ]
    },
    "jacket": {
      "worst_round_position": 2,
      "field_size": 5,
      "consistency_rank": 4,
      "biggest_lead_blown": null,
      "subject": "Gregg Williams",
      "runner_up": "David Mullin",
      "margin": 16.0,
      "attribution": "built",
      "shape": "volatile",
      "best_in_field_rounds": 4,
      "rounds_in_bottom_half": 0,
      "rounds": [
        {
          "round": 1,
          "score": 18.0,
          "position": 1,
          "standing": "best in the field",
          "vs_runner_up": -5.0
        },
        {
          "round": 2,
          "score": 22.0,
          "position": 2,
          "standing": "best in the field",
          "vs_runner_up": 0.0
        },
        {
          "round": 3,
          "score": 15.0,
          "position": 1,
          "standing": "best in the field",
          "vs_runner_up": -11.0
        },
        {
          "round": 4,
          "score": 11.0,
          "position": 2,
          "standing": "best in the field",
          "vs_runner_up": 0.0
        }
      ],
      "rival_could_have_flipped_it": false,
      "summary_facts": [
        "Gregg Williams beat David Mullin head-to-head in 2 of the 4 rounds",
        "Gregg Williams won 4 of the 4 rounds outright",
        "Gregg Williams never finished a round worse than 2nd of 5",
        "Gregg Williams swung about more between rounds than most of the field",
        "even with an ordinary round instead of their worst, David Mullin would still have lost"
      ]
    },
    "spoon": {
      "worst_round_position": 5,
      "field_size": 5,
      "consistency_rank": 2,
      "biggest_lead_blown": null,
      "subject": "Alex Baker",
      "runner_up": "Jon Baker",
      "margin": 4.0,
      "attribution": "built",
      "shape": "consistent",
      "best_in_field_rounds": 0,
      "rounds_in_bottom_half": 4,
      "rounds": [
        {
          "round": 1,
          "score": 29.0,
          "position": 5,
          "standing": "bottom half of the field",
          "vs_runner_up": -5.0
        },
        {
          "round": 2,
          "score": 32.0,
          "position": 3,
          "standing": "bottom half of the field",
          "vs_runner_up": 0.0
        },
        {
          "round": 3,
          "score": 33.0,
          "position": 3,
          "standing": "bottom half of the field",
          "vs_runner_up": 0.0
        },
        {
          "round": 4,
          "score": 33.0,
          "position": 4,
          "standing": "bottom half of the field",
          "vs_runner_up": 1.0
        }
      ],
      "rival_could_have_flipped_it": false,
      "summary_facts": [
        "Alex Baker was worse than Jon Baker in 1 of the 4 rounds",
        "Alex Baker finished 4 adrift of Jon Baker, the next worst",
        "Alex Baker was last in the field in 1 of the 4 rounds",
        "Alex Baker was steadier round to round than most of the field",
        "even with an ordinary round instead of their worst, Alex Baker would still have taken the Spoon"
      ]
    }
  },
  "player_history": {
    "Alex BAKER": {
      "trophy_wins": 1,
      "jacket_wins": 0,
      "spoon_count": 2,
      "last_4_positions": [
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
        },
        {
          "teg": 14,
          "trophy_rank": 2,
          "jacket_rank": 4,
          "n_players": 4
        },
        {
          "teg": 15,
          "trophy_rank": 6,
          "jacket_rank": 6,
          "n_players": 6
        }
      ],
      "notable_milestones": [
        "1 prior Trophy win",
        "2 prior Wooden Spoons",
        "reigning Wooden Spoon holder (TEG 15)"
      ]
    },
    "David MULLIN": {
      "trophy_wins": 3,
      "jacket_wins": 9,
      "spoon_count": 4,
      "last_4_positions": [
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
        },
        {
          "teg": 14,
          "trophy_rank": 1,
          "jacket_rank": 1,
          "n_players": 4
        },
        {
          "teg": 15,
          "trophy_rank": 5,
          "jacket_rank": 3,
          "n_players": 6
        }
      ],
      "notable_milestones": [
        "3 prior Trophy wins",
        "9 prior Jacket wins",
        "4 prior Wooden Spoons"
      ]
    },
    "Gregg WILLIAMS": {
      "trophy_wins": 4,
      "jacket_wins": 1,
      "spoon_count": 1,
      "last_4_positions": [
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
        },
        {
          "teg": 14,
          "trophy_rank": 3,
          "jacket_rank": 3,
          "n_players": 4
        },
        {
          "teg": 15,
          "trophy_rank": 1,
          "jacket_rank": 1,
          "n_players": 6
        }
      ],
      "notable_milestones": [
        "4 prior Trophy wins",
        "1 prior Jacket win",
        "1 prior Wooden Spoon",
        "defending Trophy champion (TEG 15)"
      ]
    },
    "Jon BAKER": {
      "trophy_wins": 3,
      "jacket_wins": 3,
      "spoon_count": 1,
      "last_4_positions": [
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
        },
        {
          "teg": 14,
          "trophy_rank": 4,
          "jacket_rank": 2,
          "n_players": 4
        },
        {
          "teg": 15,
          "trophy_rank": 4,
          "jacket_rank": 2,
          "n_players": 6
        }
      ],
      "notable_milestones": [
        "3 prior Trophy wins",
        "3 prior Jacket wins",
        "1 prior Wooden Spoon"
      ]
    },
    "Stuart NEUMANN": {
      "trophy_wins": 0,
      "jacket_wins": 0,
      "spoon_count": 2,
      "last_4_positions": [
        {
          "teg": 9,
          "trophy_rank": 6,
          "jacket_rank": 5,
          "n_players": 6
        },
        {
          "teg": 10,
          "trophy_rank": 5,
          "jacket_rank": 5,
          "n_players": 6
        },
        {
          "teg": 12,
          "trophy_rank": 3,
          "jacket_rank": 6,
          "n_players": 6
        },
        {
          "teg": 15,
          "trophy_rank": 2,
          "jacket_rank": 5,
          "n_players": 6
        }
      ],
      "notable_milestones": [
        "2 prior Wooden Spoons"
      ]
    }
  },
  "player_course_history": {
    "Alex Baker": {
      "Estoril": {
        "course": "Estoril",
        "visit_count_through_this_teg": 2,
        "n_prior_visits": 1,
        "prior_best_gross": 99,
        "prior_best_teg": 15,
        "this_teg_best_gross": 107,
        "this_teg_best_round": 4,
        "strokes_vs_last_visit": 8,
        "is_course_pb_this_teg": false,
        "summary_facts": [
          "Alex Baker's prior best at Estoril: 99 gross (TEG 15)",
          "Alex Baker was 8 shots worse than his last visit to Estoril"
        ]
      },
      "Oitavos Dunes": {
        "course": "Oitavos Dunes",
        "visit_count_through_this_teg": 3,
        "n_prior_visits": 2,
        "prior_best_gross": 103,
        "prior_best_teg": 15,
        "this_teg_best_gross": 113,
        "this_teg_best_round": 1,
        "strokes_vs_last_visit": 10,
        "is_course_pb_this_teg": false,
        "summary_facts": [
          "Alex Baker's 3rd visit to Oitavos Dunes",
          "Alex Baker's prior best at Oitavos Dunes: 103 gross (TEG 15)",
          "Alex Baker was 10 shots worse than his last visit to Oitavos Dunes"
        ]
      },
      "Penha Longa": {
        "course": "Penha Longa",
        "visit_count_through_this_teg": 3,
        "n_prior_visits": 2,
        "prior_best_gross": 106,
        "prior_best_teg": 8,
        "this_teg_best_gross": 106,
        "this_teg_best_round": 3,
        "strokes_vs_last_visit": 0,
        "is_course_pb_this_teg": false,
        "summary_facts": [
          "Alex Baker's 3rd visit to Penha Longa",
          "Alex Baker's prior best at Penha Longa: 106 gross (TEG 8)"
        ]
      },
      "Troia": {
        "course": "Troia",
        "visit_count_through_this_teg": 1,
        "n_prior_visits": 0,
        "prior_best_gross": null,
        "prior_best_teg": null,
        "this_teg_best_gross": 106,
        "this_teg_best_round": 2,
        "strokes_vs_last_visit": null,
        "is_course_pb_this_teg": false,
        "summary_facts": [
          "Alex Baker's first visit to Troia"
        ]
      }
    },
    "David Mullin": {
      "Estoril": {
        "course": "Estoril",
        "visit_count_through_this_teg": 2,
        "n_prior_visits": 1,
        "prior_best_gross": 94,
        "prior_best_teg": 15,
        "this_teg_best_gross": 80,
        "this_teg_best_round": 4,
        "strokes_vs_last_visit": -14,
        "is_course_pb_this_teg": true,
        "summary_facts": [
          "David Mullin's prior best at Estoril: 94 gross (TEG 15)",
          "David Mullin's new personal best at Estoril in R4: 80 gross — improved by 14",
          "David Mullin was 14 shots better than his last visit to Estoril"
        ]
      },
      "Oitavos Dunes": {
        "course": "Oitavos Dunes",
        "visit_count_through_this_teg": 3,
        "n_prior_visits": 2,
        "prior_best_gross": 88,
        "prior_best_teg": 8,
        "this_teg_best_gross": 94,
        "this_teg_best_round": 1,
        "strokes_vs_last_visit": -10,
        "is_course_pb_this_teg": false,
        "summary_facts": [
          "David Mullin's 3rd visit to Oitavos Dunes",
          "David Mullin's prior best at Oitavos Dunes: 88 gross (TEG 8)",
          "David Mullin was 10 shots better than his last visit to Oitavos Dunes"
        ]
      },
      "Penha Longa": {
        "course": "Penha Longa",
        "visit_count_through_this_teg": 3,
        "n_prior_visits": 2,
        "prior_best_gross": 85,
        "prior_best_teg": 15,
        "this_teg_best_gross": 98,
        "this_teg_best_round": 3,
        "strokes_vs_last_visit": 13,
        "is_course_pb_this_teg": false,
        "summary_facts": [
          "David Mullin's 3rd visit to Penha Longa",
          "David Mullin's prior best at Penha Longa: 85 gross (TEG 15)",
          "David Mullin was 13 shots worse than his last visit to Penha Longa"
        ]
      },
      "Troia": {
        "course": "Troia",
        "visit_count_through_this_teg": 1,
        "n_prior_visits": 0,
        "prior_best_gross": null,
        "prior_best_teg": null,
        "this_teg_best_gross": 94,
        "this_teg_best_round": 2,
        "strokes_vs_last_visit": null,
        "is_course_pb_this_teg": false,
        "summary_facts": [
          "David Mullin's first visit to Troia"
        ]
      }
    },
    "Gregg Williams": {
      "Estoril": {
        "course": "Estoril",
        "visit_count_through_this_teg": 2,
        "n_prior_visits": 1,
        "prior_best_gross": 86,
        "prior_best_teg": 15,
        "this_teg_best_gross": 80,
        "this_teg_best_round": 4,
        "strokes_vs_last_visit": -6,
        "is_course_pb_this_teg": true,
        "summary_facts": [
          "Gregg Williams's prior best at Estoril: 86 gross (TEG 15)",
          "Gregg Williams's new personal best at Estoril in R4: 80 gross — improved by 6",
          "Gregg Williams was 6 shots better than his last visit to Estoril"
        ]
      },
      "Oitavos Dunes": {
        "course": "Oitavos Dunes",
        "visit_count_through_this_teg": 3,
        "n_prior_visits": 2,
        "prior_best_gross": 91,
        "prior_best_teg": 15,
        "this_teg_best_gross": 89,
        "this_teg_best_round": 1,
        "strokes_vs_last_visit": -2,
        "is_course_pb_this_teg": true,
        "summary_facts": [
          "Gregg Williams's 3rd visit to Oitavos Dunes",
          "Gregg Williams's prior best at Oitavos Dunes: 91 gross (TEG 15)",
          "Gregg Williams's new personal best at Oitavos Dunes in R1: 89 gross — improved by 2"
        ]
      },
      "Penha Longa": {
        "course": "Penha Longa",
        "visit_count_through_this_teg": 3,
        "n_prior_visits": 2,
        "prior_best_gross": 82,
        "prior_best_teg": 15,
        "this_teg_best_gross": 87,
        "this_teg_best_round": 3,
        "strokes_vs_last_visit": 5,
        "is_course_pb_this_teg": false,
        "summary_facts": [
          "Gregg Williams's 3rd visit to Penha Longa",
          "Gregg Williams's prior best at Penha Longa: 82 gross (TEG 15)",
          "Gregg Williams was 5 shots worse than his last visit to Penha Longa"
        ]
      },
      "Troia": {
        "course": "Troia",
        "visit_count_through_this_teg": 1,
        "n_prior_visits": 0,
        "prior_best_gross": null,
        "prior_best_teg": null,
        "this_teg_best_gross": 94,
        "this_teg_best_round": 2,
        "strokes_vs_last_visit": null,
        "is_course_pb_this_teg": false,
        "summary_facts": [
          "Gregg Williams's first visit to Troia"
        ]
      }
    },
    "Jon Baker": {
      "Estoril": {
        "course": "Estoril",
        "visit_count_through_this_teg": 2,
        "n_prior_visits": 1,
        "prior_best_gross": 96,
        "prior_best_teg": 15,
        "this_teg_best_gross": 93,
        "this_teg_best_round": 4,
        "strokes_vs_last_visit": -3,
        "is_course_pb_this_teg": true,
        "summary_facts": [
          "Jon Baker's prior best at Estoril: 96 gross (TEG 15)",
          "Jon Baker's new personal best at Estoril in R4: 93 gross — improved by 3"
        ]
      },
      "Oitavos Dunes": {
        "course": "Oitavos Dunes",
        "visit_count_through_this_teg": 3,
        "n_prior_visits": 2,
        "prior_best_gross": 94,
        "prior_best_teg": 15,
        "this_teg_best_gross": 92,
        "this_teg_best_round": 1,
        "strokes_vs_last_visit": -2,
        "is_course_pb_this_teg": true,
        "summary_facts": [
          "Jon Baker's 3rd visit to Oitavos Dunes",
          "Jon Baker's prior best at Oitavos Dunes: 94 gross (TEG 15)",
          "Jon Baker's new personal best at Oitavos Dunes in R1: 92 gross — improved by 2"
        ]
      },
      "Penha Longa": {
        "course": "Penha Longa",
        "visit_count_through_this_teg": 3,
        "n_prior_visits": 2,
        "prior_best_gross": 85,
        "prior_best_teg": 15,
        "this_teg_best_gross": 97,
        "this_teg_best_round": 3,
        "strokes_vs_last_visit": 12,
        "is_course_pb_this_teg": false,
        "summary_facts": [
          "Jon Baker's 3rd visit to Penha Longa",
          "Jon Baker's prior best at Penha Longa: 85 gross (TEG 15)",
          "Jon Baker was 12 shots worse than his last visit to Penha Longa"
        ]
      },
      "Troia": {
        "course": "Troia",
        "visit_count_through_this_teg": 1,
        "n_prior_visits": 0,
        "prior_best_gross": null,
        "prior_best_teg": null,
        "this_teg_best_gross": 95,
        "this_teg_best_round": 2,
        "strokes_vs_last_visit": null,
        "is_course_pb_this_teg": false,
        "summary_facts": [
          "Jon Baker's first visit to Troia"
        ]
      }
    },
    "Stuart Neumann": {
      "Estoril": {
        "course": "Estoril",
        "visit_count_through_this_teg": 2,
        "n_prior_visits": 1,
        "prior_best_gross": 106,
        "prior_best_teg": 15,
        "this_teg_best_gross": 92,
        "this_teg_best_round": 4,
        "strokes_vs_last_visit": -14,
        "is_course_pb_this_teg": true,
        "summary_facts": [
          "Stuart Neumann's prior best at Estoril: 106 gross (TEG 15)",
          "Stuart Neumann's new personal best at Estoril in R4: 92 gross — improved by 14",
          "Stuart Neumann was 14 shots better than his last visit to Estoril"
        ]
      },
      "Oitavos Dunes": {
        "course": "Oitavos Dunes",
        "visit_count_through_this_teg": 3,
        "n_prior_visits": 2,
        "prior_best_gross": 95,
        "prior_best_teg": 8,
        "this_teg_best_gross": 97,
        "this_teg_best_round": 1,
        "strokes_vs_last_visit": -2,
        "is_course_pb_this_teg": false,
        "summary_facts": [
          "Stuart Neumann's 3rd visit to Oitavos Dunes",
          "Stuart Neumann's prior best at Oitavos Dunes: 95 gross (TEG 8)"
        ]
      },
      "Penha Longa": {
        "course": "Penha Longa",
        "visit_count_through_this_teg": 3,
        "n_prior_visits": 2,
        "prior_best_gross": 92,
        "prior_best_teg": 15,
        "this_teg_best_gross": 98,
        "this_teg_best_round": 3,
        "strokes_vs_last_visit": 6,
        "is_course_pb_this_teg": false,
        "summary_facts": [
          "Stuart Neumann's 3rd visit to Penha Longa",
          "Stuart Neumann's prior best at Penha Longa: 92 gross (TEG 15)",
          "Stuart Neumann was 6 shots worse than his last visit to Penha Longa"
        ]
      },
      "Troia": {
        "course": "Troia",
        "visit_count_through_this_teg": 1,
        "n_prior_visits": 0,
        "prior_best_gross": null,
        "prior_best_teg": null,
        "this_teg_best_gross": 102,
        "this_teg_best_round": 2,
        "strokes_vs_last_visit": null,
        "is_course_pb_this_teg": false,
        "summary_facts": [
          "Stuart Neumann's first visit to Troia"
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
    "close_finish": false,
    "signals": [],
    "final_margin": 13,
    "trophy_metric": "stableford"
  },
  "recent_vehicle_choices": [
    {
      "teg": 13,
      "vehicles": [
        "hero_arc",
        "ensemble",
        "inevitability"
      ],
      "structure": "in_medias_res",
      "title": "Fifty, and Never Headed"
    },
    {
      "teg": 14,
      "vehicles": [
        "counterfactual",
        "inversion",
        "motif"
      ],
      "structure": "three_act",
      "title": "Mullin Banks It at Deal, Spends It at Sandwich"
    },
    {
      "teg": 15,
      "vehicles": [
        "origin",
        "inversion",
        "catalogue"
      ],
      "structure": "three_act",
      "title": "The Jacket Finally Fits: Williams Takes the Lot on the Lisbon Coast"
    }
  ],
  "vehicle_fit_hints": [
    {
      "vehicle": "catalogue",
      "raw": 14.0,
      "z": 1.65,
      "baseline_mean": 5.76,
      "reasons": [
        "Gregg Williams: 3 separate blow-up/collapse beats",
        "Alex Baker: 7 separate blow-up/collapse beats"
      ]
    },
    {
      "vehicle": "origin",
      "raw": 6.0,
      "z": 1.55,
      "baseline_mean": 1.76,
      "reasons": [
        "Stuart NEUMANN: first-ever Trophy win"
      ]
    },
    {
      "vehicle": "tragic_arc",
      "raw": 40.4,
      "z": 0.97,
      "baseline_mean": 26.11,
      "reasons": [
        "b06 (R4): Gregg Williams's steady run ends with a double bogey at the 9th (R4)",
        "b19 (R3): Alex Baker bleeds 12 shots, holes 11-14 (R3)",
        "b30 (R4): Alex Baker bleeds 14 shots, holes 5-10 (R4)"
      ]
    },
    {
      "vehicle": "inevitability",
      "raw": 5.0,
      "z": 0.2,
      "baseline_mean": 4.41,
      "reasons": [
        "Trophy led wire-to-wire, no lead changes after R1"
      ]
    },
    {
      "vehicle": "underdog",
      "raw": 4.0,
      "z": -0.04,
      "baseline_mean": 4.18,
      "reasons": [
        "Stuart NEUMANN: 2 prior Wooden Spoons — now the Trophy winner"
      ]
    }
  ],
  "candidate_threads": [
    {
      "subject_type": "player",
      "subject": "Alex Baker",
      "round_span": [
        1,
        2,
        3,
        4
      ],
      "entertainment_sum": 114.3,
      "rarity_max": 7,
      "independent_of_trophy": true,
      "score": 78.1,
      "beat_ids": [
        "b09",
        "b19",
        "b26",
        "b30",
        "b31",
        "b32",
        "b33",
        "b37",
        "b38",
        "b39",
        "b44",
        "b47",
        "b49",
        "b51",
        "b52",
        "b54",
        "b55",
        "b58",
        "b60",
        "b62",
        "b66",
        "b71",
        "b77",
        "b83",
        "b85"
      ],
      "headlines": [
        "Alex Baker runs up a 11 (septuple bogey) at the 12th (R4)",
        "Alex Baker bleeds 12 shots, holes 11-14 (R3)",
        "Alex Baker goes 3 holes without a net par, 12-14 (R3)",
        "Alex Baker bleeds 14 shots, holes 5-10 (R4)",
        "Alex Baker goes 3 holes without a net par, 5-7 (R4)",
        "Alex Baker runs up a 9 (quintuple bogey) at the 1st (R4)",
        "Alex Baker bleeds 13 shots, holes 13-17 (R2)",
        "Alex Baker runs up a 10 (sextuple bogey) at the 17th (R1)",
        "Alex Baker runs up a 9 (quadruple bogey) at the 6th (R4)",
        "Alex Baker runs up a 8 (quadruple bogey) at the 3rd (R4)",
        "Alex Baker runs up a 9 (quadruple bogey) at the 12th (R3)",
        "Alex Baker runs up a 9 (quintuple bogey) at the 11th (R1)",
        "Alex Baker runs up a 9 (quintuple bogey) at the 1st (R1)",
        "Alex Baker bleeds 11 shots, holes 2-6 (R3)",
        "Alex Baker goes 4 holes without a net par, 3-6 (R3)",
        "Alex Baker stops the bleeding with a birdie at the 10th (R2)",
        "Alex Baker goes 3 holes without a net par, 13-15 (R2)",
        "Alex Baker bleeds 11 shots, holes 16-18 (R1)",
        "Alex Baker runs up a 9 (quadruple bogey) at the 7th (R1)",
        "Alex Baker drops to the bottom of the Wooden Spoon race (R2 H13)",
        "Alex Baker goes 3 holes without a net par, 16-18 (R1)",
        "Alex Baker drops to the bottom of the Wooden Spoon race (R1 H11)",
        "Alex Baker bleeds 13 shots, holes 4-9 (R2)",
        "Alex Baker drops to the bottom of the Wooden Spoon race (R1 H15)",
        "Alex Baker bleeds 7 shots, holes 3-5 (R1)"
      ]
    },
    {
      "subject_type": "player",
      "subject": "Stuart Neumann",
      "round_span": [
        1,
        2,
        3,
        4
      ],
      "entertainment_sum": 50.7,
      "rarity_max": 5,
      "independent_of_trophy": true,
      "score": 44.4,
      "beat_ids": [
        "b08",
        "b28",
        "b43",
        "b46",
        "b59",
        "b68",
        "b70",
        "b72",
        "b74",
        "b75",
        "b78",
        "b79",
        "b80",
        "b81",
        "b86",
        "b87"
      ],
      "headlines": [
        "After R4: Stuart Neumann leads the Trophy (gap 0 on Stableford); Gregg Williams leads the Jacket",
        "After R3: Stuart Neumann leads the Trophy (gap 0 on Stableford); Gregg Williams leads the Jacket",
        "After R2: Stuart Neumann leads the Trophy (gap 0 on Stableford); Gregg Williams leads the Jacket",
        "Stuart Neumann runs up a 9 (quintuple bogey) at the 8th (R4)",
        "After R1: Stuart Neumann leads the Trophy (gap 0 on Stableford); Gregg Williams leads the Jacket",
        "Stuart Neumann runs up a 8 (quadruple bogey) at the 14th (R3)",
        "Stuart Neumann runs up a 8 (quadruple bogey) at the 1st (R3)",
        "Stuart Neumann runs up a 8 (quadruple bogey) at the 16th (R2)",
        "Stuart Neumann bleeds 9 shots, holes 7-9 (R4)",
        "Stuart Neumann piles up 11 points, holes 10-12 (R2)",
        "Stuart Neumann's steady run ends with a triple bogey at the 13th (R2)",
        "Stuart Neumann goes 3 holes without dropping a gross shot, 10-12 (R2)",
        "Stuart Neumann stops the bleeding with a birdie at the 10th (R2)",
        "Stuart Neumann piles up 9 points, holes 4-6 (R4)",
        "Stuart Neumann piles up 9 points, holes 1-3 (R1)",
        "Stuart Neumann goes 2 holes without dropping a gross shot, 3-4 (R3)"
      ]
    },
    {
      "subject_type": "player",
      "subject": "Gregg Williams",
      "round_span": [
        1,
        2,
        3,
        4
      ],
      "entertainment_sum": 52.1,
      "rarity_max": 4,
      "independent_of_trophy": true,
      "score": 44.0,
      "beat_ids": [
        "b03",
        "b06",
        "b08",
        "b11",
        "b12",
        "b15",
        "b16",
        "b17",
        "b18",
        "b20",
        "b23",
        "b25",
        "b28",
        "b35",
        "b41",
        "b43",
        "b45",
        "b48",
        "b50",
        "b53",
        "b59",
        "b64",
        "b69",
        "b90"
      ],
      "headlines": [
        "Gregg Williams runs up a 8 (quadruple bogey) at the 14th (R4)",
        "Gregg Williams's steady run ends with a double bogey at the 9th (R4)",
        "After R4: Stuart Neumann leads the Trophy (gap 0 on Stableford); Gregg Williams leads the Jacket",
        "Gregg Williams piles up 9 points, holes 6-8 (R4)",
        "Gregg Williams goes 2 holes without dropping a gross shot, 15-16 (R4)",
        "Gregg Williams goes 2 holes without dropping a gross shot, 12-13 (R4)",
        "Gregg Williams goes 3 holes without dropping a gross shot, 6-8 (R4)",
        "Gregg Williams piles up 9 points, holes 2-4 (R4)",
        "Gregg Williams goes 5 holes without dropping a gross shot, 11-15 (R3)",
        "Gregg Williams goes 3 holes without dropping a gross shot, 2-4 (R4)",
        "Gregg Williams piles up 9 points, holes 13-15 (R3)",
        "Gregg Williams stops the bleeding with a birdie at the 5th (R3)",
        "After R3: Stuart Neumann leads the Trophy (gap 0 on Stableford); Gregg Williams leads the Jacket",
        "Gregg Williams goes 3 holes without a net par, 6-8 (R3)",
        "Gregg Williams goes 4 holes without a net par, 8-11 (R2)",
        "After R2: Stuart Neumann leads the Trophy (gap 0 on Stableford); Gregg Williams leads the Jacket",
        "Gregg Williams goes 2 holes without dropping a gross shot, 1-2 (R3)",
        "Gregg Williams goes 3 holes without a net par, 13-15 (R2)",
        "Gregg Williams bleeds 6 shots, holes 13-15 (R2)",
        "Gregg Williams bleeds 6 shots, holes 9-11 (R2)",
        "After R1: Stuart Neumann leads the Trophy (gap 0 on Stableford); Gregg Williams leads the Jacket",
        "Gregg Williams goes 2 holes without dropping a gross shot, 15-16 (R1)",
        "Gregg Williams goes 2 holes without dropping a gross shot, 2-3 (R1)",
        "Gregg Williams draws level for the Trophy (Stableford) lead (R1 H4)"
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
      "entertainment_sum": 47.1,
      "rarity_max": 5,
      "independent_of_trophy": true,
      "score": 42.6,
      "beat_ids": [
        "b21",
        "b27",
        "b34",
        "b36",
        "b42",
        "b56",
        "b57",
        "b61",
        "b63",
        "b67",
        "b73",
        "b76",
        "b82",
        "b88"
      ],
      "headlines": [
        "Jon Baker bleeds 11 shots, holes 11-13 (R3)",
        "Jon Baker goes 3 holes without a net par, 11-13 (R3)",
        "Jon Baker runs up a 10 (quintuple bogey) at the 12th (R3)",
        "Jon Baker runs up a 8 (quadruple bogey) at the 11th (R4)",
        "Jon Baker runs up a 8 (quadruple bogey) at the 13th (R3)",
        "Jon Baker piles up 9 points, holes 14-16 (R1)",
        "Jon Baker's steady run ends with a double bogey at the 17th (R1)",
        "Jon Baker goes 2 holes without dropping a gross shot, 9-10 (R2)",
        "Jon Baker goes 3 holes without dropping a gross shot, 14-16 (R1)",
        "Jon Baker goes 2 holes without dropping a gross shot, 17-18 (R3)",
        "Jon Baker stops the bleeding with a birdie at the 10th (R4)",
        "Jon Baker goes 2 holes without dropping a gross shot, 4-5 (R3)",
        "Jon Baker draws level for the Green Jacket (Gross) lead (R2 H14)",
        "Jon Baker draws level for the Green Jacket (Gross) lead (R2 H11)"
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
      "entertainment_sum": 35.5,
      "rarity_max": 2.8,
      "independent_of_trophy": true,
      "score": 34.5,
      "beat_ids": [
        "b19",
        "b26",
        "b30",
        "b31",
        "b33",
        "b51",
        "b52",
        "b55",
        "b58",
        "b66",
        "b77",
        "b85"
      ],
      "headlines": [
        "Alex Baker bleeds 12 shots, holes 11-14 (R3)",
        "Alex Baker goes 3 holes without a net par, 12-14 (R3)",
        "Alex Baker bleeds 14 shots, holes 5-10 (R4)",
        "Alex Baker goes 3 holes without a net par, 5-7 (R4)",
        "Alex Baker bleeds 13 shots, holes 13-17 (R2)",
        "Alex Baker bleeds 11 shots, holes 2-6 (R3)",
        "Alex Baker goes 4 holes without a net par, 3-6 (R3)",
        "Alex Baker goes 3 holes without a net par, 13-15 (R2)",
        "Alex Baker bleeds 11 shots, holes 16-18 (R1)",
        "Alex Baker goes 3 holes without a net par, 16-18 (R1)",
        "Alex Baker bleeds 13 shots, holes 4-9 (R2)",
        "Alex Baker bleeds 7 shots, holes 3-5 (R1)"
      ]
    },
    {
      "subject_type": "player",
      "subject": "David Mullin",
      "round_span": [
        1,
        3,
        4
      ],
      "entertainment_sum": 31.6,
      "rarity_max": 4,
      "independent_of_trophy": true,
      "score": 30.8,
      "beat_ids": [
        "b04",
        "b05",
        "b07",
        "b10",
        "b13",
        "b14",
        "b22",
        "b29",
        "b40",
        "b65",
        "b84",
        "b89"
      ],
      "headlines": [
        "David Mullin stops the bleeding with a birdie at the 7th (R4)",
        "David Mullin runs up a 8 (quadruple bogey) at the 16th (R3)",
        "David Mullin piles up 9 points, holes 11-13 (R4)",
        "David Mullin goes 2 holes without dropping a gross shot, 16-17 (R4)",
        "David Mullin follows a poor R3 with a strong R4",
        "David Mullin goes 2 holes without dropping a gross shot, 12-13 (R4)",
        "David Mullin goes 2 holes without dropping a gross shot, 2-3 (R4)",
        "David Mullin goes 2 holes without dropping a gross shot, 17-18 (R3)",
        "David Mullin drops to the bottom of the Wooden Spoon race (R1 H10)",
        "David Mullin draws level for the Trophy (Stableford) lead (R1 H5)",
        "David Mullin drops to the bottom of the Wooden Spoon race (R1 H13)",
        "David Mullin draws level for the Green Jacket (Gross) lead (R1 H6)"
      ]
    },
    {
      "subject_type": "failure_mode",
      "subject": "Gregg Williams",
      "round_span": [
        2,
        3,
        4
      ],
      "entertainment_sum": 13.1,
      "rarity_max": 2.5,
      "independent_of_trophy": true,
      "score": 20.1,
      "beat_ids": [
        "b06",
        "b35",
        "b41",
        "b48",
        "b50",
        "b53"
      ],
      "headlines": [
        "Gregg Williams's steady run ends with a double bogey at the 9th (R4)",
        "Gregg Williams goes 3 holes without a net par, 6-8 (R3)",
        "Gregg Williams goes 4 holes without a net par, 8-11 (R2)",
        "Gregg Williams goes 3 holes without a net par, 13-15 (R2)",
        "Gregg Williams bleeds 6 shots, holes 13-15 (R2)",
        "Gregg Williams bleeds 6 shots, holes 9-11 (R2)"
      ]
    },
    {
      "subject_type": "failure_mode",
      "subject": "Jon Baker",
      "round_span": [
        1,
        3
      ],
      "entertainment_sum": 10.5,
      "rarity_max": 2.5,
      "independent_of_trophy": true,
      "score": 15.8,
      "beat_ids": [
        "b21",
        "b27",
        "b57"
      ],
      "headlines": [
        "Jon Baker bleeds 11 shots, holes 11-13 (R3)",
        "Jon Baker goes 3 holes without a net par, 11-13 (R3)",
        "Jon Baker's steady run ends with a double bogey at the 17th (R1)"
      ]
    }
  ],
  "beats": [
    {
      "id": "b01",
      "total": 28.2,
      "scope": "tournament",
      "type": "trophy_win",
      "round": null,
      "course": null,
      "headline": "Stuart Neumann wins the Trophy on 156 pts, by 13",
      "players": [
        "Stuart Neumann"
      ],
      "scores": {
        "importance": 10.0,
        "rarity": 4.0,
        "entertainment": 5.0
      },
      "mandatory": true,
      "holes": [],
      "context": {
        "score": 156,
        "margin": 13,
        "trophy_metric": "stableford",
        "runner_up": "Gregg Williams",
        "all_time_rank": 16,
        "player_rank": 2
      }
    },
    {
      "id": "b02",
      "total": 27.6,
      "scope": "tournament",
      "type": "jacket_win",
      "round": null,
      "course": null,
      "headline": "Gregg Williams wins the Green Jacket at +66, by 16",
      "players": [
        "Gregg Williams"
      ],
      "scores": {
        "importance": 9.0,
        "rarity": 7.0,
        "entertainment": 4.0
      },
      "mandatory": true,
      "holes": [],
      "context": {
        "score": 66,
        "margin": 16,
        "runner_up": "David Mullin",
        "all_time_rank": 5,
        "player_rank": 1,
        "metric": "gross"
      }
    },
    {
      "id": "b03",
      "total": 27.24,
      "scope": "hole",
      "type": "big_blowup",
      "round": 4,
      "course": "Estoril",
      "headline": "Gregg Williams runs up a 8 (quadruple bogey) at the 14th (R4)",
      "players": [
        "Gregg Williams"
      ],
      "scores": {
        "importance": 9.52,
        "rarity": 4,
        "entertainment": 5.0
      },
      "mandatory": false,
      "holes": [
        {
          "hole": 14,
          "par": 4,
          "sc": 8,
          "grossvp": 4,
          "result": "quadruple bogey",
          "stableford": 0,
          "si": 4
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
      "id": "b04",
      "total": 24.14,
      "scope": "stretch",
      "type": "recovery",
      "round": 4,
      "course": "Estoril",
      "headline": "David Mullin stops the bleeding with a birdie at the 7th (R4)",
      "players": [
        "David Mullin"
      ],
      "scores": {
        "importance": 8.72,
        "rarity": 3.0,
        "entertainment": 4.3
      },
      "mandatory": false,
      "holes": [
        {
          "hole": 4,
          "par": 3,
          "sc": 4,
          "grossvp": 1,
          "result": "bogey",
          "stableford": 2,
          "si": 9
        },
        {
          "hole": 5,
          "par": 3,
          "sc": 4,
          "grossvp": 1,
          "result": "bogey",
          "stableford": 2,
          "si": 17
        },
        {
          "hole": 6,
          "par": 5,
          "sc": 7,
          "grossvp": 2,
          "result": "double bogey",
          "stableford": 1,
          "si": 3
        },
        {
          "hole": 7,
          "par": 4,
          "sc": 3,
          "grossvp": -1,
          "result": "birdie",
          "stableford": 4,
          "si": 15
        }
      ],
      "context": {
        "streak_broken": "bogey_or_worse",
        "importance_legacy": 4.55,
        "impact_metric": "stableford"
      }
    },
    {
      "id": "b05",
      "total": 24.04,
      "scope": "hole",
      "type": "big_blowup",
      "round": 3,
      "course": "Penha Longa",
      "headline": "David Mullin runs up a 8 (quadruple bogey) at the 16th (R3)",
      "players": [
        "David Mullin"
      ],
      "scores": {
        "importance": 7.77,
        "rarity": 4,
        "entertainment": 5.3
      },
      "mandatory": false,
      "holes": [
        {
          "hole": 16,
          "par": 4,
          "sc": 8,
          "grossvp": 4,
          "result": "quadruple bogey",
          "stableford": 0,
          "si": 1
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
      "id": "b06",
      "total": 23.88,
      "scope": "stretch",
      "type": "collapse_after_steady",
      "round": 4,
      "course": "Estoril",
      "headline": "Gregg Williams's steady run ends with a double bogey at the 9th (R4)",
      "players": [
        "Gregg Williams"
      ],
      "scores": {
        "importance": 8.94,
        "rarity": 2.5,
        "entertainment": 4.0
      },
      "mandatory": false,
      "holes": [
        {
          "hole": 6,
          "par": 5,
          "sc": 5,
          "grossvp": 0,
          "result": "par",
          "stableford": 3,
          "si": 3
        },
        {
          "hole": 7,
          "par": 4,
          "sc": 4,
          "grossvp": 0,
          "result": "par",
          "stableford": 3,
          "si": 15
        },
        {
          "hole": 8,
          "par": 4,
          "sc": 4,
          "grossvp": 0,
          "result": "par",
          "stableford": 3,
          "si": 1
        },
        {
          "hole": 9,
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
      "id": "b07",
      "total": 23.26,
      "scope": "stretch",
      "type": "hot_stretch_net",
      "round": 4,
      "course": "Estoril",
      "headline": "David Mullin piles up 9 points, holes 11-13 (R4)",
      "players": [
        "David Mullin"
      ],
      "scores": {
        "importance": 9.4,
        "rarity": 2.16,
        "entertainment": 2.736
      },
      "mandatory": false,
      "holes": [
        {
          "hole": 11,
          "par": 4,
          "sc": 5,
          "grossvp": 1,
          "result": "bogey",
          "stableford": 3,
          "si": 2
        },
        {
          "hole": 12,
          "par": 4,
          "sc": 4,
          "grossvp": 0,
          "result": "par",
          "stableford": 3,
          "si": 6
        },
        {
          "hole": 13,
          "par": 3,
          "sc": 3,
          "grossvp": 0,
          "result": "par",
          "stableford": 3,
          "si": 14
        }
      ],
      "context": {
        "points_gained": 9,
        "metric": "stableford",
        "length": 3,
        "importance_legacy": 6.28,
        "impact_metric": "stableford"
      }
    },
    {
      "id": "b08",
      "total": 22.8,
      "scope": "round",
      "type": "round_leadership",
      "round": 4,
      "course": "Estoril",
      "headline": "After R4: Stuart Neumann leads the Trophy (gap 0 on Stableford); Gregg Williams leads the Jacket",
      "players": [
        "Stuart Neumann",
        "Gregg Williams"
      ],
      "scores": {
        "importance": 10.0,
        "rarity": 1.0,
        "entertainment": 2.0
      },
      "mandatory": false,
      "holes": [],
      "context": {
        "trophy_leader": "Stuart Neumann",
        "jacket_leader": "Gregg Williams",
        "importance_legacy": 6.8,
        "impact_metric": "stableford"
      }
    },
    {
      "id": "b09",
      "total": 22.38,
      "scope": "hole",
      "type": "big_blowup",
      "round": 4,
      "course": "Estoril",
      "headline": "Alex Baker runs up a 11 (septuple bogey) at the 12th (R4)",
      "players": [
        "Alex Baker"
      ],
      "scores": {
        "importance": 4.09,
        "rarity": 7,
        "entertainment": 8.6
      },
      "mandatory": true,
      "holes": [
        {
          "hole": 12,
          "par": 4,
          "sc": 11,
          "grossvp": 7,
          "result": "septuple bogey",
          "stableford": 0,
          "si": 6
        }
      ],
      "context": {
        "is_player_par_worst": true,
        "is_teg_par_worst": false,
        "importance_legacy": 3.8,
        "impact_metric": "stableford"
      }
    },
    {
      "id": "b10",
      "total": 22.14,
      "scope": "stretch",
      "type": "hot_stretch_gross",
      "round": 4,
      "course": "Estoril",
      "headline": "David Mullin goes 2 holes without dropping a gross shot, 16-17 (R4)",
      "players": [
        "David Mullin"
      ],
      "scores": {
        "importance": 9.88,
        "rarity": 1.26,
        "entertainment": 1.368
      },
      "mandatory": false,
      "holes": [
        {
          "hole": 16,
          "par": 3,
          "sc": 3,
          "grossvp": 0,
          "result": "par",
          "stableford": 3,
          "si": 8
        },
        {
          "hole": 17,
          "par": 4,
          "sc": 4,
          "grossvp": 0,
          "result": "par",
          "stableford": 3,
          "si": 18
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
      "id": "b11",
      "total": 21.91,
      "scope": "stretch",
      "type": "hot_stretch_net",
      "round": 4,
      "course": "Estoril",
      "headline": "Gregg Williams piles up 9 points, holes 6-8 (R4)",
      "players": [
        "Gregg Williams"
      ],
      "scores": {
        "importance": 8.83,
        "rarity": 2.16,
        "entertainment": 2.5200000000000005
      },
      "mandatory": false,
      "holes": [
        {
          "hole": 6,
          "par": 5,
          "sc": 5,
          "grossvp": 0,
          "result": "par",
          "stableford": 3,
          "si": 3
        },
        {
          "hole": 7,
          "par": 4,
          "sc": 4,
          "grossvp": 0,
          "result": "par",
          "stableford": 3,
          "si": 15
        },
        {
          "hole": 8,
          "par": 4,
          "sc": 4,
          "grossvp": 0,
          "result": "par",
          "stableford": 3,
          "si": 1
        }
      ],
      "context": {
        "points_gained": 9,
        "metric": "stableford",
        "length": 3,
        "importance_legacy": 6.95,
        "impact_metric": "stableford"
      }
    },
    {
      "id": "b12",
      "total": 21.79,
      "scope": "stretch",
      "type": "hot_stretch_gross",
      "round": 4,
      "course": "Estoril",
      "headline": "Gregg Williams goes 2 holes without dropping a gross shot, 15-16 (R4)",
      "players": [
        "Gregg Williams"
      ],
      "scores": {
        "importance": 9.76,
        "rarity": 1.26,
        "entertainment": 1.2600000000000002
      },
      "mandatory": false,
      "holes": [
        {
          "hole": 15,
          "par": 4,
          "sc": 4,
          "grossvp": 0,
          "result": "par",
          "stableford": 3,
          "si": 12
        },
        {
          "hole": 16,
          "par": 3,
          "sc": 3,
          "grossvp": 0,
          "result": "par",
          "stableford": 3,
          "si": 8
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
      "id": "b13",
      "total": 21.78,
      "scope": "round",
      "type": "round_swing",
      "round": 4,
      "course": "Estoril",
      "headline": "David Mullin follows a poor R3 with a strong R4",
      "players": [
        "David Mullin"
      ],
      "scores": {
        "importance": 10.0,
        "rarity": 0.8999999999999999,
        "entertainment": 1.0562500000000001
      },
      "mandatory": false,
      "holes": [],
      "context": {
        "direction": "up",
        "delta": 15,
        "prev_round": 3,
        "prev_score": 30,
        "curr_score": 45,
        "importance_legacy": 4.85,
        "impact_metric": "stableford"
      }
    },
    {
      "id": "b14",
      "total": 21.18,
      "scope": "stretch",
      "type": "hot_stretch_gross",
      "round": 4,
      "course": "Estoril",
      "headline": "David Mullin goes 2 holes without dropping a gross shot, 12-13 (R4)",
      "players": [
        "David Mullin"
      ],
      "scores": {
        "importance": 9.4,
        "rarity": 1.26,
        "entertainment": 1.368
      },
      "mandatory": false,
      "holes": [
        {
          "hole": 12,
          "par": 4,
          "sc": 4,
          "grossvp": 0,
          "result": "par",
          "stableford": 3,
          "si": 6
        },
        {
          "hole": 13,
          "par": 3,
          "sc": 3,
          "grossvp": 0,
          "result": "par",
          "stableford": 3,
          "si": 14
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
      "id": "b15",
      "total": 21.07,
      "scope": "stretch",
      "type": "hot_stretch_gross",
      "round": 4,
      "course": "Estoril",
      "headline": "Gregg Williams goes 2 holes without dropping a gross shot, 12-13 (R4)",
      "players": [
        "Gregg Williams"
      ],
      "scores": {
        "importance": 9.4,
        "rarity": 1.26,
        "entertainment": 1.2600000000000002
      },
      "mandatory": false,
      "holes": [
        {
          "hole": 12,
          "par": 4,
          "sc": 4,
          "grossvp": 0,
          "result": "par",
          "stableford": 3,
          "si": 6
        },
        {
          "hole": 13,
          "par": 3,
          "sc": 3,
          "grossvp": 0,
          "result": "par",
          "stableford": 3,
          "si": 14
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
      "id": "b16",
      "total": 21.06,
      "scope": "stretch",
      "type": "hot_stretch_gross",
      "round": 4,
      "course": "Estoril",
      "headline": "Gregg Williams goes 3 holes without dropping a gross shot, 6-8 (R4)",
      "players": [
        "Gregg Williams"
      ],
      "scores": {
        "importance": 8.83,
        "rarity": 1.89,
        "entertainment": 1.8900000000000003
      },
      "mandatory": false,
      "holes": [
        {
          "hole": 6,
          "par": 5,
          "sc": 5,
          "grossvp": 0,
          "result": "par",
          "stableford": 3,
          "si": 3
        },
        {
          "hole": 7,
          "par": 4,
          "sc": 4,
          "grossvp": 0,
          "result": "par",
          "stableford": 3,
          "si": 15
        },
        {
          "hole": 8,
          "par": 4,
          "sc": 4,
          "grossvp": 0,
          "result": "par",
          "stableford": 3,
          "si": 1
        }
      ],
      "context": {
        "shots_gained": 0,
        "length": 3,
        "importance_legacy": 6.66,
        "impact_metric": "stableford"
      }
    },
    {
      "id": "b17",
      "total": 21.03,
      "scope": "stretch",
      "type": "hot_stretch_net",
      "round": 4,
      "course": "Estoril",
      "headline": "Gregg Williams piles up 9 points, holes 2-4 (R4)",
      "players": [
        "Gregg Williams"
      ],
      "scores": {
        "importance": 8.39,
        "rarity": 2.16,
        "entertainment": 2.5200000000000005
      },
      "mandatory": false,
      "holes": [
        {
          "hole": 2,
          "par": 3,
          "sc": 3,
          "grossvp": 0,
          "result": "par",
          "stableford": 3,
          "si": 11
        },
        {
          "hole": 3,
          "par": 4,
          "sc": 4,
          "grossvp": 0,
          "result": "par",
          "stableford": 3,
          "si": 13
        },
        {
          "hole": 4,
          "par": 3,
          "sc": 3,
          "grossvp": 0,
          "result": "par",
          "stableford": 3,
          "si": 9
        }
      ],
      "context": {
        "points_gained": 9,
        "metric": "stableford",
        "length": 3,
        "importance_legacy": 6.95,
        "impact_metric": "stableford"
      }
    },
    {
      "id": "b18",
      "total": 21.01,
      "scope": "stretch",
      "type": "hot_stretch_gross",
      "round": 3,
      "course": "Penha Longa",
      "headline": "Gregg Williams goes 5 holes without dropping a gross shot, 11-15 (R3)",
      "players": [
        "Gregg Williams"
      ],
      "scores": {
        "importance": 7.67,
        "rarity": 3.15,
        "entertainment": 3.1500000000000004
      },
      "mandatory": false,
      "holes": [
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
          "par": 5,
          "sc": 5,
          "grossvp": 0,
          "result": "par",
          "stableford": 2,
          "si": 17
        },
        {
          "hole": 13,
          "par": 4,
          "sc": 4,
          "grossvp": 0,
          "result": "par",
          "stableford": 3,
          "si": 13
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
          "par": 3,
          "sc": 3,
          "grossvp": 0,
          "result": "par",
          "stableford": 3,
          "si": 11
        }
      ],
      "context": {
        "shots_gained": 0,
        "length": 5,
        "importance_legacy": 6.24,
        "impact_metric": "stableford"
      }
    },
    {
      "id": "b19",
      "total": 20.46,
      "scope": "stretch",
      "type": "cold_stretch_gross",
      "round": 3,
      "course": "Penha Longa",
      "headline": "Alex Baker bleeds 12 shots, holes 11-14 (R3)",
      "players": [
        "Alex Baker"
      ],
      "scores": {
        "importance": 7.57,
        "rarity": 2.4,
        "entertainment": 3.4
      },
      "mandatory": false,
      "holes": [
        {
          "hole": 11,
          "par": 4,
          "sc": 6,
          "grossvp": 2,
          "result": "double bogey",
          "stableford": 2,
          "si": 3
        },
        {
          "hole": 12,
          "par": 5,
          "sc": 9,
          "grossvp": 4,
          "result": "quadruple bogey",
          "stableford": 0,
          "si": 17
        },
        {
          "hole": 13,
          "par": 4,
          "sc": 7,
          "grossvp": 3,
          "result": "triple bogey",
          "stableford": 0,
          "si": 13
        },
        {
          "hole": 14,
          "par": 4,
          "sc": 7,
          "grossvp": 3,
          "result": "triple bogey",
          "stableford": 1,
          "si": 5
        }
      ],
      "context": {
        "shots_dropped": 12,
        "length": 4,
        "importance_legacy": 4.71,
        "impact_metric": "stableford"
      }
    },
    {
      "id": "b20",
      "total": 20.18,
      "scope": "stretch",
      "type": "hot_stretch_gross",
      "round": 4,
      "course": "Estoril",
      "headline": "Gregg Williams goes 3 holes without dropping a gross shot, 2-4 (R4)",
      "players": [
        "Gregg Williams"
      ],
      "scores": {
        "importance": 8.39,
        "rarity": 1.89,
        "entertainment": 1.8900000000000003
      },
      "mandatory": false,
      "holes": [
        {
          "hole": 2,
          "par": 3,
          "sc": 3,
          "grossvp": 0,
          "result": "par",
          "stableford": 3,
          "si": 11
        },
        {
          "hole": 3,
          "par": 4,
          "sc": 4,
          "grossvp": 0,
          "result": "par",
          "stableford": 3,
          "si": 13
        },
        {
          "hole": 4,
          "par": 3,
          "sc": 3,
          "grossvp": 0,
          "result": "par",
          "stableford": 3,
          "si": 9
        }
      ],
      "context": {
        "shots_gained": 0,
        "length": 3,
        "importance_legacy": 6.66,
        "impact_metric": "stableford"
      }
    },
    {
      "id": "b21",
      "total": 19.82,
      "scope": "stretch",
      "type": "cold_stretch_gross",
      "round": 3,
      "course": "Penha Longa",
      "headline": "Jon Baker bleeds 11 shots, holes 11-13 (R3)",
      "players": [
        "Jon Baker"
      ],
      "scores": {
        "importance": 7.47,
        "rarity": 2.1999999999999997,
        "entertainment": 3.1166666666666663
      },
      "mandatory": false,
      "holes": [
        {
          "hole": 11,
          "par": 4,
          "sc": 6,
          "grossvp": 2,
          "result": "double bogey",
          "stableford": 1,
          "si": 3
        },
        {
          "hole": 12,
          "par": 5,
          "sc": 10,
          "grossvp": 5,
          "result": "quintuple bogey",
          "stableford": 0,
          "si": 17
        },
        {
          "hole": 13,
          "par": 4,
          "sc": 8,
          "grossvp": 4,
          "result": "quadruple bogey",
          "stableford": 0,
          "si": 13
        }
      ],
      "context": {
        "shots_dropped": 11,
        "length": 3,
        "importance_legacy": 4.63,
        "impact_metric": "stableford"
      }
    },
    {
      "id": "b22",
      "total": 19.6,
      "scope": "stretch",
      "type": "hot_stretch_gross",
      "round": 4,
      "course": "Estoril",
      "headline": "David Mullin goes 2 holes without dropping a gross shot, 2-3 (R4)",
      "players": [
        "David Mullin"
      ],
      "scores": {
        "importance": 8.28,
        "rarity": 1.6099999999999999,
        "entertainment": 1.7479999999999998
      },
      "mandatory": false,
      "holes": [
        {
          "hole": 2,
          "par": 3,
          "sc": 2,
          "grossvp": -1,
          "result": "birdie",
          "stableford": 4,
          "si": 11
        },
        {
          "hole": 3,
          "par": 4,
          "sc": 4,
          "grossvp": 0,
          "result": "par",
          "stableford": 3,
          "si": 13
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
      "id": "b23",
      "total": 19.59,
      "scope": "stretch",
      "type": "hot_stretch_net",
      "round": 3,
      "course": "Penha Longa",
      "headline": "Gregg Williams piles up 9 points, holes 13-15 (R3)",
      "players": [
        "Gregg Williams"
      ],
      "scores": {
        "importance": 7.67,
        "rarity": 2.16,
        "entertainment": 2.5200000000000005
      },
      "mandatory": false,
      "holes": [
        {
          "hole": 13,
          "par": 4,
          "sc": 4,
          "grossvp": 0,
          "result": "par",
          "stableford": 3,
          "si": 13
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
          "par": 3,
          "sc": 3,
          "grossvp": 0,
          "result": "par",
          "stableford": 3,
          "si": 11
        }
      ],
      "context": {
        "points_gained": 9,
        "metric": "stableford",
        "length": 3,
        "importance_legacy": 5.95,
        "impact_metric": "stableford"
      }
    },
    {
      "id": "b24",
      "total": 19.4,
      "scope": "tournament",
      "type": "wooden_spoon",
      "round": null,
      "course": null,
      "headline": "Alex Baker collects the Wooden Spoon (127 pts)",
      "players": [
        "Alex Baker"
      ],
      "scores": {
        "importance": 5.0,
        "rarity": 3.0,
        "entertainment": 7.0
      },
      "mandatory": true,
      "holes": [],
      "context": {
        "score": 127,
        "trophy_metric": "stableford"
      }
    },
    {
      "id": "b25",
      "total": 19.3,
      "scope": "stretch",
      "type": "recovery",
      "round": 3,
      "course": "Penha Longa",
      "headline": "Gregg Williams stops the bleeding with a birdie at the 5th (R3)",
      "players": [
        "Gregg Williams"
      ],
      "scores": {
        "importance": 6.45,
        "rarity": 3.0,
        "entertainment": 4.0
      },
      "mandatory": false,
      "holes": [
        {
          "hole": 3,
          "par": 4,
          "sc": 7,
          "grossvp": 3,
          "result": "triple bogey",
          "stableford": 0,
          "si": 16
        },
        {
          "hole": 4,
          "par": 4,
          "sc": 6,
          "grossvp": 2,
          "result": "double bogey",
          "stableford": 1,
          "si": 2
        },
        {
          "hole": 5,
          "par": 3,
          "sc": 2,
          "grossvp": -1,
          "result": "birdie",
          "stableford": 4,
          "si": 14
        }
      ],
      "context": {
        "streak_broken": "bogey_or_worse",
        "importance_legacy": 5.0,
        "impact_metric": "stableford"
      }
    },
    {
      "id": "b26",
      "total": 19.29,
      "scope": "stretch",
      "type": "cold_stretch_net",
      "round": 3,
      "course": "Penha Longa",
      "headline": "Alex Baker goes 3 holes without a net par, 12-14 (R3)",
      "players": [
        "Alex Baker"
      ],
      "scores": {
        "importance": 7.57,
        "rarity": 1.7,
        "entertainment": 2.7880000000000003
      },
      "mandatory": false,
      "holes": [
        {
          "hole": 12,
          "par": 5,
          "sc": 9,
          "grossvp": 4,
          "result": "quadruple bogey",
          "stableford": 0,
          "si": 17
        },
        {
          "hole": 13,
          "par": 4,
          "sc": 7,
          "grossvp": 3,
          "result": "triple bogey",
          "stableford": 0,
          "si": 13
        },
        {
          "hole": 14,
          "par": 4,
          "sc": 7,
          "grossvp": 3,
          "result": "triple bogey",
          "stableford": 1,
          "si": 5
        }
      ],
      "context": {
        "shortfall": 5,
        "length": 3,
        "importance_legacy": 3.72,
        "impact_metric": "stableford"
      }
    },
    {
      "id": "b27",
      "total": 19.09,
      "scope": "stretch",
      "type": "cold_stretch_net",
      "round": 3,
      "course": "Penha Longa",
      "headline": "Jon Baker goes 3 holes without a net par, 11-13 (R3)",
      "players": [
        "Jon Baker"
      ],
      "scores": {
        "importance": 7.47,
        "rarity": 1.7,
        "entertainment": 2.7880000000000003
      },
      "mandatory": false,
      "holes": [
        {
          "hole": 11,
          "par": 4,
          "sc": 6,
          "grossvp": 2,
          "result": "double bogey",
          "stableford": 1,
          "si": 3
        },
        {
          "hole": 12,
          "par": 5,
          "sc": 10,
          "grossvp": 5,
          "result": "quintuple bogey",
          "stableford": 0,
          "si": 17
        },
        {
          "hole": 13,
          "par": 4,
          "sc": 8,
          "grossvp": 4,
          "result": "quadruple bogey",
          "stableford": 0,
          "si": 13
        }
      ],
      "context": {
        "shortfall": 5,
        "length": 3,
        "importance_legacy": 3.72,
        "impact_metric": "stableford"
      }
    },
    {
      "id": "b28",
      "total": 18.74,
      "scope": "round",
      "type": "round_leadership",
      "round": 3,
      "course": "Penha Longa",
      "headline": "After R3: Stuart Neumann leads the Trophy (gap 0 on Stableford); Gregg Williams leads the Jacket",
      "players": [
        "Stuart Neumann",
        "Gregg Williams"
      ],
      "scores": {
        "importance": 7.97,
        "rarity": 1.0,
        "entertainment": 2.0
      },
      "mandatory": false,
      "holes": [],
      "context": {
        "trophy_leader": "Stuart Neumann",
        "jacket_leader": "Gregg Williams",
        "importance_legacy": 5.2,
        "impact_metric": "stableford"
      }
    },
    {
      "id": "b29",
      "total": 18.32,
      "scope": "stretch",
      "type": "hot_stretch_gross",
      "round": 3,
      "course": "Penha Longa",
      "headline": "David Mullin goes 2 holes without dropping a gross shot, 17-18 (R3)",
      "players": [
        "David Mullin"
      ],
      "scores": {
        "importance": 7.97,
        "rarity": 1.26,
        "entertainment": 1.368
      },
      "mandatory": false,
      "holes": [
        {
          "hole": 17,
          "par": 3,
          "sc": 3,
          "grossvp": 0,
          "result": "par",
          "stableford": 3,
          "si": 7
        },
        {
          "hole": 18,
          "par": 5,
          "sc": 5,
          "grossvp": 0,
          "result": "par",
          "stableford": 3,
          "si": 15
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
      "id": "b30",
      "total": 17.91,
      "scope": "stretch",
      "type": "cold_stretch_gross",
      "round": 4,
      "course": "Estoril",
      "headline": "Alex Baker bleeds 14 shots, holes 5-10 (R4)",
      "players": [
        "Alex Baker"
      ],
      "scores": {
        "importance": 5.85,
        "rarity": 2.8000000000000003,
        "entertainment": 3.966666666666667
      },
      "mandatory": false,
      "holes": [
        {
          "hole": 5,
          "par": 3,
          "sc": 5,
          "grossvp": 2,
          "result": "double bogey",
          "stableford": 1,
          "si": 17
        },
        {
          "hole": 6,
          "par": 5,
          "sc": 9,
          "grossvp": 4,
          "result": "quadruple bogey",
          "stableford": 0,
          "si": 3
        },
        {
          "hole": 7,
          "par": 4,
          "sc": 6,
          "grossvp": 2,
          "result": "double bogey",
          "stableford": 1,
          "si": 15
        },
        {
          "hole": 8,
          "par": 4,
          "sc": 6,
          "grossvp": 2,
          "result": "double bogey",
          "stableford": 2,
          "si": 1
        },
        {
          "hole": 9,
          "par": 4,
          "sc": 6,
          "grossvp": 2,
          "result": "double bogey",
          "stableford": 2,
          "si": 5
        },
        {
          "hole": 10,
          "par": 5,
          "sc": 7,
          "grossvp": 2,
          "result": "double bogey",
          "stableford": 2,
          "si": 10
        }
      ],
      "context": {
        "shots_dropped": 14,
        "length": 6,
        "importance_legacy": 5.88,
        "impact_metric": "stableford"
      }
    },
    {
      "id": "b31",
      "total": 17.88,
      "scope": "stretch",
      "type": "cold_stretch_net",
      "round": 4,
      "course": "Estoril",
      "headline": "Alex Baker goes 3 holes without a net par, 5-7 (R4)",
      "players": [
        "Alex Baker"
      ],
      "scores": {
        "importance": 7.17,
        "rarity": 1.45,
        "entertainment": 2.378
      },
      "mandatory": false,
      "holes": [
        {
          "hole": 5,
          "par": 3,
          "sc": 5,
          "grossvp": 2,
          "result": "double bogey",
          "stableford": 1,
          "si": 17
        },
        {
          "hole": 6,
          "par": 5,
          "sc": 9,
          "grossvp": 4,
          "result": "quadruple bogey",
          "stableford": 0,
          "si": 3
        },
        {
          "hole": 7,
          "par": 4,
          "sc": 6,
          "grossvp": 2,
          "result": "double bogey",
          "stableford": 1,
          "si": 15
        }
      ],
      "context": {
        "shortfall": 4,
        "length": 3,
        "importance_legacy": 4.72,
        "impact_metric": "stableford"
      }
    },
    {
      "id": "b32",
      "total": 17.72,
      "scope": "hole",
      "type": "big_blowup",
      "round": 4,
      "course": "Estoril",
      "headline": "Alex Baker runs up a 9 (quintuple bogey) at the 1st (R4)",
      "players": [
        "Alex Baker"
      ],
      "scores": {
        "importance": 3.56,
        "rarity": 5,
        "entertainment": 6.6
      },
      "mandatory": false,
      "holes": [
        {
          "hole": 1,
          "par": 4,
          "sc": 9,
          "grossvp": 5,
          "result": "quintuple bogey",
          "stableford": 0,
          "si": 7
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
      "id": "b33",
      "total": 17.66,
      "scope": "stretch",
      "type": "cold_stretch_gross",
      "round": 2,
      "course": "Troia",
      "headline": "Alex Baker bleeds 13 shots, holes 13-17 (R2)",
      "players": [
        "Alex Baker"
      ],
      "scores": {
        "importance": 5.95,
        "rarity": 2.5999999999999996,
        "entertainment": 3.683333333333333
      },
      "mandatory": false,
      "holes": [
        {
          "hole": 13,
          "par": 4,
          "sc": 7,
          "grossvp": 3,
          "result": "triple bogey",
          "stableford": 0,
          "si": 14
        },
        {
          "hole": 14,
          "par": 5,
          "sc": 8,
          "grossvp": 3,
          "result": "triple bogey",
          "stableford": 1,
          "si": 4
        },
        {
          "hole": 15,
          "par": 4,
          "sc": 7,
          "grossvp": 3,
          "result": "triple bogey",
          "stableford": 1,
          "si": 2
        },
        {
          "hole": 16,
          "par": 4,
          "sc": 6,
          "grossvp": 2,
          "result": "double bogey",
          "stableford": 2,
          "si": 10
        },
        {
          "hole": 17,
          "par": 3,
          "sc": 5,
          "grossvp": 2,
          "result": "double bogey",
          "stableford": 1,
          "si": 16
        }
      ],
      "context": {
        "shots_dropped": 13,
        "length": 5,
        "importance_legacy": 4.79,
        "impact_metric": "stableford"
      }
    },
    {
      "id": "b34",
      "total": 17.3,
      "scope": "hole",
      "type": "big_blowup",
      "round": 3,
      "course": "Penha Longa",
      "headline": "Jon Baker runs up a 10 (quintuple bogey) at the 12th (R3)",
      "players": [
        "Jon Baker"
      ],
      "scores": {
        "importance": 3.35,
        "rarity": 5,
        "entertainment": 6.6
      },
      "mandatory": true,
      "holes": [
        {
          "hole": 12,
          "par": 5,
          "sc": 10,
          "grossvp": 5,
          "result": "quintuple bogey",
          "stableford": 0,
          "si": 17
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
      "id": "b35",
      "total": 17.19,
      "scope": "stretch",
      "type": "cold_stretch_net",
      "round": 3,
      "course": "Penha Longa",
      "headline": "Gregg Williams goes 3 holes without a net par, 6-8 (R3)",
      "players": [
        "Gregg Williams"
      ],
      "scores": {
        "importance": 7.0,
        "rarity": 1.45,
        "entertainment": 2.0300000000000002
      },
      "mandatory": false,
      "holes": [
        {
          "hole": 6,
          "par": 5,
          "sc": 6,
          "grossvp": 1,
          "result": "bogey",
          "stableford": 1,
          "si": 18
        },
        {
          "hole": 7,
          "par": 3,
          "sc": 6,
          "grossvp": 3,
          "result": "triple bogey",
          "stableford": 0,
          "si": 4
        },
        {
          "hole": 8,
          "par": 5,
          "sc": 7,
          "grossvp": 2,
          "result": "double bogey",
          "stableford": 1,
          "si": 6
        }
      ],
      "context": {
        "shortfall": 4,
        "length": 3,
        "importance_legacy": 4.8,
        "impact_metric": "stableford"
      }
    },
    {
      "id": "b36",
      "total": 17.14,
      "scope": "hole",
      "type": "big_blowup",
      "round": 4,
      "course": "Estoril",
      "headline": "Jon Baker runs up a 8 (quadruple bogey) at the 11th (R4)",
      "players": [
        "Jon Baker"
      ],
      "scores": {
        "importance": 4.17,
        "rarity": 4,
        "entertainment": 5.6
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
          "si": 2
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
      "id": "b37",
      "total": 16.86,
      "scope": "hole",
      "type": "big_blowup",
      "round": 1,
      "course": "Oitavos Dunes",
      "headline": "Alex Baker runs up a 10 (sextuple bogey) at the 17th (R1)",
      "players": [
        "Alex Baker"
      ],
      "scores": {
        "importance": 2.23,
        "rarity": 6,
        "entertainment": 7.6
      },
      "mandatory": true,
      "holes": [
        {
          "hole": 17,
          "par": 4,
          "sc": 10,
          "grossvp": 6,
          "result": "sextuple bogey",
          "stableford": 0,
          "si": 8
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
      "id": "b38",
      "total": 16.4,
      "scope": "hole",
      "type": "big_blowup",
      "round": 4,
      "course": "Estoril",
      "headline": "Alex Baker runs up a 9 (quadruple bogey) at the 6th (R4)",
      "players": [
        "Alex Baker"
      ],
      "scores": {
        "importance": 3.8,
        "rarity": 4,
        "entertainment": 5.6
      },
      "mandatory": false,
      "holes": [
        {
          "hole": 6,
          "par": 5,
          "sc": 9,
          "grossvp": 4,
          "result": "quadruple bogey",
          "stableford": 0,
          "si": 3
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
      "id": "b39",
      "total": 16.1,
      "scope": "hole",
      "type": "big_blowup",
      "round": 4,
      "course": "Estoril",
      "headline": "Alex Baker runs up a 8 (quadruple bogey) at the 3rd (R4)",
      "players": [
        "Alex Baker"
      ],
      "scores": {
        "importance": 3.65,
        "rarity": 4,
        "entertainment": 5.6
      },
      "mandatory": false,
      "holes": [
        {
          "hole": 3,
          "par": 4,
          "sc": 8,
          "grossvp": 4,
          "result": "quadruple bogey",
          "stableford": 0,
          "si": 13
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
      "id": "b40",
      "total": 16.06,
      "scope": "hole",
      "type": "spoon_change",
      "round": 1,
      "course": "Oitavos Dunes",
      "headline": "David Mullin drops to the bottom of the Wooden Spoon race (R1 H10)",
      "players": [
        "David Mullin"
      ],
      "scores": {
        "importance": 4.73,
        "rarity": 2.0,
        "entertainment": 5.0
      },
      "mandatory": false,
      "holes": [
        {
          "hole": 10,
          "par": 4,
          "sc": 7,
          "grossvp": 3,
          "result": "triple bogey",
          "stableford": 0,
          "si": 4
        }
      ],
      "context": {
        "competition": "Wooden Spoon",
        "rank_before": 2,
        "rank_after": 5,
        "importance_legacy": 3.0,
        "impact_metric": "stableford"
      }
    },
    {
      "id": "b41",
      "total": 15.63,
      "scope": "stretch",
      "type": "cold_stretch_net",
      "round": 2,
      "course": "Troia",
      "headline": "Gregg Williams goes 4 holes without a net par, 8-11 (R2)",
      "players": [
        "Gregg Williams"
      ],
      "scores": {
        "importance": 5.78,
        "rarity": 1.85,
        "entertainment": 2.5900000000000003
      },
      "mandatory": false,
      "holes": [
        {
          "hole": 8,
          "par": 4,
          "sc": 5,
          "grossvp": 1,
          "result": "bogey",
          "stableford": 1,
          "si": 17
        },
        {
          "hole": 9,
          "par": 4,
          "sc": 6,
          "grossvp": 2,
          "result": "double bogey",
          "stableford": 1,
          "si": 5
        },
        {
          "hole": 10,
          "par": 4,
          "sc": 6,
          "grossvp": 2,
          "result": "double bogey",
          "stableford": 1,
          "si": 12
        },
        {
          "hole": 11,
          "par": 3,
          "sc": 5,
          "grossvp": 2,
          "result": "double bogey",
          "stableford": 0,
          "si": 18
        }
      ],
      "context": {
        "shortfall": 5,
        "length": 4,
        "importance_legacy": 4.8,
        "impact_metric": "stableford"
      }
    },
    {
      "id": "b42",
      "total": 15.6,
      "scope": "hole",
      "type": "big_blowup",
      "round": 3,
      "course": "Penha Longa",
      "headline": "Jon Baker runs up a 8 (quadruple bogey) at the 13th (R3)",
      "players": [
        "Jon Baker"
      ],
      "scores": {
        "importance": 3.4,
        "rarity": 4,
        "entertainment": 5.6
      },
      "mandatory": false,
      "holes": [
        {
          "hole": 13,
          "par": 4,
          "sc": 8,
          "grossvp": 4,
          "result": "quadruple bogey",
          "stableford": 0,
          "si": 13
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
      "id": "b43",
      "total": 15.42,
      "scope": "round",
      "type": "round_leadership",
      "round": 2,
      "course": "Troia",
      "headline": "After R2: Stuart Neumann leads the Trophy (gap 0 on Stableford); Gregg Williams leads the Jacket",
      "players": [
        "Stuart Neumann",
        "Gregg Williams"
      ],
      "scores": {
        "importance": 6.31,
        "rarity": 1.0,
        "entertainment": 2.0
      },
      "mandatory": false,
      "holes": [],
      "context": {
        "trophy_leader": "Stuart Neumann",
        "jacket_leader": "Gregg Williams",
        "importance_legacy": 4.6,
        "impact_metric": "stableford"
      }
    },
    {
      "id": "b44",
      "total": 15.3,
      "scope": "hole",
      "type": "big_blowup",
      "round": 3,
      "course": "Penha Longa",
      "headline": "Alex Baker runs up a 9 (quadruple bogey) at the 12th (R3)",
      "players": [
        "Alex Baker"
      ],
      "scores": {
        "importance": 3.25,
        "rarity": 4,
        "entertainment": 5.6
      },
      "mandatory": false,
      "holes": [
        {
          "hole": 12,
          "par": 5,
          "sc": 9,
          "grossvp": 4,
          "result": "quadruple bogey",
          "stableford": 0,
          "si": 17
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
      "id": "b45",
      "total": 15.23,
      "scope": "stretch",
      "type": "hot_stretch_gross",
      "round": 3,
      "course": "Penha Longa",
      "headline": "Gregg Williams goes 2 holes without dropping a gross shot, 1-2 (R3)",
      "players": [
        "Gregg Williams"
      ],
      "scores": {
        "importance": 6.48,
        "rarity": 1.26,
        "entertainment": 1.2600000000000002
      },
      "mandatory": false,
      "holes": [
        {
          "hole": 1,
          "par": 4,
          "sc": 4,
          "grossvp": 0,
          "result": "par",
          "stableford": 3,
          "si": 10
        },
        {
          "hole": 2,
          "par": 4,
          "sc": 4,
          "grossvp": 0,
          "result": "par",
          "stableford": 3,
          "si": 8
        }
      ],
      "context": {
        "shots_gained": 0,
        "length": 2,
        "importance_legacy": 5.38,
        "impact_metric": "stableford"
      }
    },
    {
      "id": "b46",
      "total": 15.22,
      "scope": "hole",
      "type": "big_blowup",
      "round": 4,
      "course": "Estoril",
      "headline": "Stuart Neumann runs up a 9 (quintuple bogey) at the 8th (R4)",
      "players": [
        "Stuart Neumann"
      ],
      "scores": {
        "importance": 2.61,
        "rarity": 5,
        "entertainment": 6.0
      },
      "mandatory": false,
      "holes": [
        {
          "hole": 8,
          "par": 4,
          "sc": 9,
          "grossvp": 5,
          "result": "quintuple bogey",
          "stableford": 0,
          "si": 1
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
      "id": "b47",
      "total": 14.8,
      "scope": "hole",
      "type": "big_blowup",
      "round": 1,
      "course": "Oitavos Dunes",
      "headline": "Alex Baker runs up a 9 (quintuple bogey) at the 11th (R1)",
      "players": [
        "Alex Baker"
      ],
      "scores": {
        "importance": 2.1,
        "rarity": 5,
        "entertainment": 6.6
      },
      "mandatory": false,
      "holes": [
        {
          "hole": 11,
          "par": 4,
          "sc": 9,
          "grossvp": 5,
          "result": "quintuple bogey",
          "stableford": 0,
          "si": 14
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
      "id": "b48",
      "total": 14.8,
      "scope": "stretch",
      "type": "cold_stretch_net",
      "round": 2,
      "course": "Troia",
      "headline": "Gregg Williams goes 3 holes without a net par, 13-15 (R2)",
      "players": [
        "Gregg Williams"
      ],
      "scores": {
        "importance": 6.08,
        "rarity": 1.2,
        "entertainment": 1.6800000000000002
      },
      "mandatory": false,
      "holes": [
        {
          "hole": 13,
          "par": 4,
          "sc": 6,
          "grossvp": 2,
          "result": "double bogey",
          "stableford": 1,
          "si": 14
        },
        {
          "hole": 14,
          "par": 5,
          "sc": 7,
          "grossvp": 2,
          "result": "double bogey",
          "stableford": 1,
          "si": 4
        },
        {
          "hole": 15,
          "par": 4,
          "sc": 6,
          "grossvp": 2,
          "result": "double bogey",
          "stableford": 1,
          "si": 2
        }
      ],
      "context": {
        "shortfall": 3,
        "length": 3,
        "importance_legacy": 4.8,
        "impact_metric": "stableford"
      }
    },
    {
      "id": "b49",
      "total": 14.58,
      "scope": "hole",
      "type": "big_blowup",
      "round": 1,
      "course": "Oitavos Dunes",
      "headline": "Alex Baker runs up a 9 (quintuple bogey) at the 1st (R1)",
      "players": [
        "Alex Baker"
      ],
      "scores": {
        "importance": 1.99,
        "rarity": 5,
        "entertainment": 6.6
      },
      "mandatory": false,
      "holes": [
        {
          "hole": 1,
          "par": 4,
          "sc": 9,
          "grossvp": 5,
          "result": "quintuple bogey",
          "stableford": 0,
          "si": 5
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
      "id": "b50",
      "total": 14.52,
      "scope": "stretch",
      "type": "cold_stretch_gross",
      "round": 2,
      "course": "Troia",
      "headline": "Gregg Williams bleeds 6 shots, holes 13-15 (R2)",
      "players": [
        "Gregg Williams"
      ],
      "scores": {
        "importance": 6.08,
        "rarity": 1.2,
        "entertainment": 1.4
      },
      "mandatory": false,
      "holes": [
        {
          "hole": 13,
          "par": 4,
          "sc": 6,
          "grossvp": 2,
          "result": "double bogey",
          "stableford": 1,
          "si": 14
        },
        {
          "hole": 14,
          "par": 5,
          "sc": 7,
          "grossvp": 2,
          "result": "double bogey",
          "stableford": 1,
          "si": 4
        },
        {
          "hole": 15,
          "par": 4,
          "sc": 6,
          "grossvp": 2,
          "result": "double bogey",
          "stableford": 1,
          "si": 2
        }
      ],
      "context": {
        "shots_dropped": 6,
        "length": 3,
        "importance_legacy": 5.44,
        "impact_metric": "stableford"
      }
    },
    {
      "id": "cr01",
      "total": 10.0,
      "scope": "round",
      "type": "course_record_low",
      "round": 4,
      "course": "Estoril",
      "headline": "new Estoril course record: 80 gross by David Mullin in R4, beating the prior record of 86 (across 6 prior visits)",
      "players": [
        "David Mullin"
      ],
      "scores": {
        "importance": 10.0,
        "rarity": 10.0,
        "entertainment": 7.0
      },
      "mandatory": true,
      "holes": [],
      "context": {
        "gross": 80,
        "prior_record": 86,
        "n_prior_visits": 6,
        "summary_fact": "new Estoril course record: 80 gross by David Mullin in R4, beating the prior record of 86 (across 6 prior visits)"
      }
    },
    {
      "id": "cr02",
      "total": 10.0,
      "scope": "round",
      "type": "course_record_high",
      "round": 4,
      "course": "Estoril",
      "headline": "new Estoril course-worst: 107 gross by Alex Baker in R4, exceeding the prior worst of 106 (across 6 prior visits)",
      "players": [
        "Alex Baker"
      ],
      "scores": {
        "importance": 10.0,
        "rarity": 10.0,
        "entertainment": 7.0
      },
      "mandatory": true,
      "holes": [],
      "context": {
        "gross": 107,
        "prior_record": 106,
        "n_prior_visits": 6,
        "summary_fact": "new Estoril course-worst: 107 gross by Alex Baker in R4, exceeding the prior worst of 106 (across 6 prior visits)"
      }
    },
    {
      "id": "cr03",
      "total": 10.0,
      "scope": "round",
      "type": "course_record_high",
      "round": 1,
      "course": "Oitavos Dunes",
      "headline": "new Oitavos Dunes course-worst: 113 gross by Alex Baker in R1, exceeding the prior worst of 111 (across 12 prior visits)",
      "players": [
        "Alex Baker"
      ],
      "scores": {
        "importance": 10.0,
        "rarity": 10.0,
        "entertainment": 7.0
      },
      "mandatory": true,
      "holes": [],
      "context": {
        "gross": 113,
        "prior_record": 111,
        "n_prior_visits": 12,
        "summary_fact": "new Oitavos Dunes course-worst: 113 gross by Alex Baker in R1, exceeding the prior worst of 111 (across 12 prior visits)"
      }
    }
  ]
}
