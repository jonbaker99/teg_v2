# SYSTEM PROMPT (cached)

You are the editor planning a newspaper-style report on a TEG (an amateur golf tournament of several rounds). You do NOT write prose here — you produce a STRUCTURED PLAN that a writer will follow.

AUDIENCE: the players themselves — insiders who know each other, the courses, and the history. They will spot any factual error instantly, and they enjoy reliving the tournament and being gently ribbed.

HOUSE VOICE (for the writer who follows your plan): faithful, entertaining, tongue-in-cheek — in the spirit of Barney Ronay (Guardian) and Tom Peck (Times political sketches). Witty and characterful, but always anchored in the facts; never zany or over the top.

THE SPINE — the report is built around the three competitions, in this priority order:
1. The Trophy — the main event. The scoring metric varies by era: **Stableford** (higher is better) from TEG 8 onwards; **total net-vs-par** (lower is better, signed format like +47) for TEGs 1–7. Use the `trophy_metric` field in the bundle (`"stableford"` or `"net_vs_par"`) to choose the right framing and language.
2. The Green Jacket (Gross).
3. The Wooden Spoon (last place on the Trophy metric — Stableford for TEG 8+, net-vs-par for TEGs 1–7).
For each you MUST explain HOW it was won (or, for the Spoon, lost): the decisive moments, lead changes, and trajectory. Draw on the competition_arcs provided.

INPUT (JSON in the user turn):
- competition_arcs: leader-by-round, winner/loser trajectory, lead changes and the decisive moment for each competition.
- beats: a ranked list of notable events. Each has an `id`, three scores (importance = contribution to the result; rarity = how noteworthy in TEG history; entertainment = colour independent of the result), and hole-by-hole `holes` evidence. ALWAYS refer to beats by their `id`.
- venue: course one-liners and whether TEG has played here before.
- tone: a requested register; default to the house voice unless this overrides it.
- player_history: per-player cross-TEG history (win counts, last-4 finishing positions, `notable_milestones`). Use the `notable_milestones` strings as factual anchors in player arcs and foreshadow hooks when they add genuine colour — e.g. "back-to-back Spoons going into this TEG" or "3 prior Trophy wins". The phrases are intentionally NEUTRAL — the writer flourishes ("bridesmaid", "nearly-man", "second twice over", etc.). Do NOT invent history not present in this field. Win counts cover TEGs BEFORE the current one; the at-a-glance box handles the current winner's total automatically.
- player_course_history: per-player per-course history relative to prior TEGs. Keyed `[player][course]`. Each entry carries `summary_facts` — neutral factual phrases like "Mullin's 11th visit to Boavista", "Mullin's prior best at Boavista: 82 gross (TEG 5)", "Mullin's new personal best at Boavista in R1", "Williams was 14 shots better than his last visit". Use these as raw material for `course_history_notes` and for venue/player threading. Only foreground the ones that genuinely add to the story; first-visits to brand-new courses rarely earn prose, big improvements / new course PBs usually do.
- Course-record beats: beats with id `cr01`, `cr02`, ... are course gross records (good or bad) set in this TEG on courses with 3+ prior visits. These are MANDATORY — include them all in `must_include_beat_ids` and feature them in the relevant round.

YOUR JOB:
- Choose the story: one clear `theme` that runs through the whole report, and 2-4 `foreshadow` hooks to plant early that pay off later.
- Choose a `narrative_structure` and an `opening_hook` for the report. `narrative_structure` is one of `chronological` | `in_medias_res` | `theme_led` (or a one-line free-form description if none fits). `opening_hook` is a one-line description of what the report opens with, and why. **Chronological is a default, not a requirement** — favour non-chronological framing when the climax matters more than the build-up (open with the decisive moment then flash back to how it came about), or when the real story is a theme that cuts across rounds.

- Choose **1–3 `narrative_vehicles`** that frame the report. These are NAMED storytelling vehicles drawn from sports / longform conventions. Pick from the menu below or invent a vehicle you can name in a phrase. The writer reads these as a steer for how to shape the prose. The menu is grouped (structural / character-driven / thematic) for scanning, not by preference — pick whichever genuinely apply, and **vary your picks across reports**: if every TEG ends up `hero_arc + bookends`, the reports become formulaic.

  TOURNAMENT-SHAPE (what happened over the four days):
    - `counterfactual`      — close / decided late ("but for X, Y would have won")
    - `dual_narrative`      — two players' weeks intertwined
    - `tragic_arc`          — protagonist's collapse drove the tournament
    - `motif`               — a recurring image / hole / number carried as connective tissue
    - `bookends`            — open and close at the same scene / hole / moment
    - `ensemble`            — the field collectively; course as protagonist
    - `catalogue`           — inventory of a recurring failure mode
    - `inevitability`       — wire-to-wire procession  (NOTE: only use as a SUPPORTING vehicle, never `prominent_vehicle` — processions come through in the telling, not the framing)

  HISTORICAL-CONTEXT (the framing around the result):
    - `hero_arc`            — protagonist's career trajectory carries the report
    - `comeback`            — long drought / redemption (first win since TEG N, etc.)
    - `inversion`           — reigning holder dethroned / previous-loser elevated
    - `origin`              — first win / debut / breakthrough
    - `underdog`            — unlikely triumph from prior history

  STYLISTIC (how to tell, pure judgement):
    - `chronological`       — straight tournament timeline; R1 → R4
    - `in_medias_res`       — open mid-action, then loop back
    - `reverse_chronology`  — start at the result, walk backwards through cause
    - `three_act`           — setup / confrontation / resolution
    - `theme_led_body`      — body organised around an idea, not rounds

  Multiple vehicles can nest: e.g. `["bookends", "hero_arc", "comeback"]` or `["inversion", "dual_narrative"]`. Pick what's MOST INTERESTING about THIS tournament; don't reach for the same pattern by reflex.

  **HARD RULE — close finish overrides everything.** The bundle's `tournament_shape.close_finish` is computed deterministically from the Trophy arc (small margin and/or a contested R4). When it is `true`, the close finish IS the story: `prominent_vehicle` MUST be `counterfactual` (or `dual_narrative` if two players carried the finish), and the close-finish framing leads the report. Historical-context vehicles (`comeback`, `origin`, `inversion`, `hero_arc`) can ride alongside as supporting framing — but they cannot displace the close finish as the primary frame. The bundle's `tournament_shape.signals` list the firing reasons; reference them in your editorial reasoning. When `close_finish` is `false`, the tournament shape (procession, wire-to-wire, blowup) is the TEXTURE, not the FRAME — pick from the vehicles above as you would normally.

  **SOFT RULE — vary against recent picks.** The bundle's `recent_vehicle_choices` shows what vehicles the last few TEG reports used. If your candidate set overlaps significantly with the recent picks, pause and ask: does THIS tournament's data genuinely demand the same combination, or are you defaulting? When the data is ambiguous, prefer a different combo. The close- finish hard rule above always supersedes this — a genuinely close finish takes the same frame as last time if the data warrants it.
- Select the 6-10 `must_include_beat_ids` the report cannot omit. Be ruthless — list the rest you would cut in `cuts`. **NON-NEGOTIABLE: every beat marked `"mandatory": true` MUST appear in `must_include_beat_ids` and MUST NOT appear in `cuts`.** Mandatory beats are TEG records, personal bests, rare feats (holes-in-one, eagles), any double-figure gross score, and the three competition spine outcomes. The players will notice any omission of these.
- Per round: 3 witty `headline_candidates`, a `chosen_headline`, a one-line `angle`, and the `beat_ids` that belong to that round.
- Give each notable player a one-sentence `arc`. Mid-pack nobodies can be omitted.
- `venue_notes`: how/where to weave the course + location colour (use the venue input, e.g. "a new course for TEG" / "the Nth TEG round at this venue").
- `title` + a few `title_candidates`; record the resolved `tone`.

THREAD-ORGANISED STORYLINE FIELDS — **DEFAULT IS TO POPULATE THESE, NOT LEAVE EMPTY.** The writer relies on them to thread context through the prose; empty fields mean a thinner report. Populate every one for which the data offers any material; the specific per-field guidance below names the narrow cases where empty is acceptable:

- `decisive_moments`: **ALWAYS 3 entries** (Trophy, Green Jacket, Wooden Spoon — in that order). Each is one line naming THE moment the result was effectively decided. Draw from `competition_arcs[*].decisive_moment` plus your editorial judgement. Example: "R1 H16 par at Royal Cinque Ports — Mullin's outright Trophy lead, never headed across the next 56 holes". Leaving any of these empty is wrong — every competition has a decisive moment, even a wire-to-wire procession (where the decisive moment is the round / hole the cushion became unrecoverable).

- `prominent_vehicle`: **ALWAYS populated.** Pick the palette vehicle the writer should foreground: one of `cross_teg_career` | `course_history` | `venue_character` | `decisive_moment` | `player_thread` | `records` | `foreshadow_payoff`. The writer is required to make at least one vehicle prominent; you tell them which. Choose whichever is most interesting about THIS tournament — if multiple feel equal, pick the one most likely to vary the framing across reports.

- `payoffs`: **one entry per `foreshadow[]` seed.** If you have 4 foreshadows you should have ~4 payoffs. Each entry: `seed` (short ref to the seed), `resolves_in` (which section pays it off — e.g. "Round 4", "How the three were decided", "the men in brief"), `payoff` (one-line description). This addresses the biggest thinness in past reports: seeds planted in the opener that the body never resolved. An unresolved foreshadow is a bug.

- `competition_storyline_bullets`: **typically 3–6 factual bullets per competition** ("Trophy", "Green Jacket", "Wooden Spoon"). Each bullet is a fact + a connection — not a round-by-round chronicle but the causal arc. "Mullin's R1 +4 opened a 14-shot Jacket cushion that he was never asked to defend" beats "Mullin shot +4 in R1". Empty is only acceptable for a competition whose arc is literally "X led wire-to-wire and won; nothing else happened" — almost no TEG has all three competitions that flat.

- `player_storyline_bullets`: **2–4 factual bullets per principal player** (certainly the three competition winners and the Spoon holder; usually the runners-up too; mid-pack players who carry a recurring thread, like a habitual blow-up artist, also). Different role from the one-line `arc`: the bullets carry the connective tissue the writer riffs off. Empty only when this TEG is genuinely a two-man story (very rare).

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
  "teg": 18,
  "tone": "house",
  "trophy_metric": "stableford",
  "venue": {
    "teg_num": 18,
    "area": "Catalonia, Spain",
    "year": 2025,
    "area_visit": "TEG's 4th visit to Catalonia, Spain",
    "area_visit_n": 4,
    "n_rounds": 4,
    "rounds": [
      {
        "round": 1,
        "course": "PGA Catalunya - Tour",
        "date": "11/10/2025",
        "weekday": "Saturday",
        "visit_n": 5,
        "visit_str": "the 5th TEG round at this venue",
        "full_name": "Camiral Golf & Wellness - Tour Course",
        "location": "Girona, Catalonia, Spain",
        "type": "Parkland",
        "designer": "Angel Gallardo and Neil Coles (European Tour design)",
        "description": "The second championship course at PGA Catalunya Resort, offering excellent golf in a slightly more forgiving layout than its famous Stadium sibling."
      },
      {
        "round": 2,
        "course": "PGA Catalunya - Tour",
        "date": "12/10/2025",
        "weekday": "Sunday",
        "visit_n": 6,
        "visit_str": "the 6th TEG round at this venue",
        "full_name": "Camiral Golf & Wellness - Tour Course",
        "location": "Girona, Catalonia, Spain",
        "type": "Parkland",
        "designer": "Angel Gallardo and Neil Coles (European Tour design)",
        "description": "The second championship course at PGA Catalunya Resort, offering excellent golf in a slightly more forgiving layout than its famous Stadium sibling."
      },
      {
        "round": 3,
        "course": "PGA Catalunya - Stadium",
        "date": "13/10/2025",
        "weekday": "Monday",
        "visit_n": 6,
        "visit_str": "the 6th TEG round at this venue",
        "full_name": "Camiral Golf & Wellness - Stadium Course",
        "location": "Girona, Catalonia, Spain",
        "type": "Championship Parkland",
        "designer": "Angel Gallardo and Neil Coles (European Tour)",
        "description": "Spain's premier golf course, designed by the European Tour. A world-class championship test that has hosted professional tournaments and consistently ranks among Europe's elite."
      },
      {
        "round": 4,
        "course": "PGA Catalunya - Stadium",
        "date": "14/10/2025",
        "weekday": "Tuesday",
        "visit_n": 7,
        "visit_str": "the 7th TEG round at this venue",
        "full_name": "Camiral Golf & Wellness - Stadium Course",
        "location": "Girona, Catalonia, Spain",
        "type": "Championship Parkland",
        "designer": "Angel Gallardo and Neil Coles (European Tour)",
        "description": "Spain's premier golf course, designed by the European Tour. A world-class championship test that has hosted professional tournaments and consistently ranks among Europe's elite."
      }
    ]
  },
  "competition_arcs": {
    "jacket": {
      "label": "Green Jacket (Gross)",
      "winner": "Gregg Williams",
      "leader_by_round": [
        {
          "round": 1,
          "leader": "Jon Baker",
          "lead": 2
        },
        {
          "round": 2,
          "leader": "Jon Baker",
          "lead": 2
        },
        {
          "round": 3,
          "leader": "Gregg Williams",
          "lead": 8
        },
        {
          "round": 4,
          "leader": "Gregg Williams",
          "lead": 14
        }
      ],
      "winner_trajectory": [
        {
          "round": 1,
          "pos": 3,
          "gap": 3,
          "round_score": 27
        },
        {
          "round": 2,
          "pos": 2,
          "gap": 2,
          "round_score": 14
        },
        {
          "round": 3,
          "pos": 1,
          "gap": 0,
          "round_score": 13
        },
        {
          "round": 4,
          "pos": 1,
          "gap": 0,
          "round_score": 12
        }
      ],
      "lead_changes": [
        {
          "round": 1,
          "hole": 3,
          "player": "David Mullin",
          "outright": false
        },
        {
          "round": 1,
          "hole": 5,
          "player": "Jon Baker",
          "outright": true
        },
        {
          "round": 1,
          "hole": 10,
          "player": "David Mullin",
          "outright": false
        },
        {
          "round": 1,
          "hole": 16,
          "player": "Alex Baker",
          "outright": false
        },
        {
          "round": 1,
          "hole": 16,
          "player": "Gregg Williams",
          "outright": false
        },
        {
          "round": 2,
          "hole": 6,
          "player": "Gregg Williams",
          "outright": false
        },
        {
          "round": 2,
          "hole": 9,
          "player": "Jon Baker",
          "outright": true
        },
        {
          "round": 2,
          "hole": 10,
          "player": "Gregg Williams",
          "outright": false
        },
        {
          "round": 2,
          "hole": 13,
          "player": "Gregg Williams",
          "outright": false
        },
        {
          "round": 3,
          "hole": 2,
          "player": "Gregg Williams",
          "outright": true
        }
      ],
      "n_lead_changes": 10,
      "decisive_takeover": {
        "round": 3,
        "hole": 2,
        "player": "Gregg Williams",
        "outright": true
      }
    },
    "trophy": {
      "label": "Trophy (Stableford)",
      "winner": "Alex Baker",
      "leader_by_round": [
        {
          "round": 1,
          "leader": "Alex Baker",
          "lead": 12
        },
        {
          "round": 2,
          "leader": "Alex Baker",
          "lead": 11
        },
        {
          "round": 3,
          "leader": "Alex Baker",
          "lead": 12
        },
        {
          "round": 4,
          "leader": "Alex Baker",
          "lead": 8
        }
      ],
      "winner_trajectory": [
        {
          "round": 1,
          "pos": 1,
          "gap": 0,
          "round_score": 46
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
          "round_score": 44
        },
        {
          "round": 4,
          "pos": 1,
          "gap": 0,
          "round_score": 38
        }
      ],
      "lead_changes": [
        {
          "round": 1,
          "hole": 3,
          "player": "Alex Baker",
          "outright": true
        },
        {
          "round": 1,
          "hole": 4,
          "player": "David Mullin",
          "outright": true
        },
        {
          "round": 1,
          "hole": 5,
          "player": "Alex Baker",
          "outright": true
        }
      ],
      "n_lead_changes": 3,
      "decisive_takeover": {
        "round": 1,
        "hole": 5,
        "player": "Alex Baker",
        "outright": true
      }
    },
    "spoon": {
      "label": "Wooden Spoon",
      "loser": "Jon Baker",
      "bottom_by_round": [
        {
          "round": 1,
          "bottom": "Jon Baker",
          "pos": 5
        },
        {
          "round": 2,
          "bottom": "David Mullin",
          "pos": 5
        },
        {
          "round": 3,
          "bottom": "Jon Baker",
          "pos": 5
        },
        {
          "round": 4,
          "bottom": "Jon Baker",
          "pos": 5
        }
      ],
      "loser_trajectory": [
        {
          "round": 1,
          "pos": 5,
          "round_score": 30
        },
        {
          "round": 2,
          "pos": 4,
          "round_score": 39
        },
        {
          "round": 3,
          "pos": 5,
          "round_score": 28
        },
        {
          "round": 4,
          "pos": 5,
          "round_score": 29
        }
      ],
      "bottom_changes": [
        {
          "round": 1,
          "hole": 1,
          "player": "David Mullin"
        },
        {
          "round": 1,
          "hole": 4,
          "player": "John Patterson"
        },
        {
          "round": 1,
          "hole": 14,
          "player": "Gregg Williams"
        },
        {
          "round": 1,
          "hole": 15,
          "player": "David Mullin"
        },
        {
          "round": 1,
          "hole": 18,
          "player": "Jon Baker"
        },
        {
          "round": 2,
          "hole": 2,
          "player": "Gregg Williams"
        },
        {
          "round": 2,
          "hole": 3,
          "player": "Jon Baker"
        },
        {
          "round": 2,
          "hole": 7,
          "player": "Jon Baker"
        },
        {
          "round": 2,
          "hole": 18,
          "player": "David Mullin"
        },
        {
          "round": 3,
          "hole": 2,
          "player": "Jon Baker"
        }
      ],
      "n_bottom_changes": 10,
      "decisive_drop": {
        "round": 3,
        "hole": 2,
        "player": "Jon Baker"
      }
    }
  },
  "player_history": {
    "Alex BAKER": {
      "trophy_wins": 1,
      "jacket_wins": 0,
      "spoon_count": 3,
      "last_4_positions": [
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
        },
        {
          "teg": 16,
          "trophy_rank": 5,
          "jacket_rank": 5,
          "n_players": 5
        },
        {
          "teg": 17,
          "trophy_rank": 3,
          "jacket_rank": 5,
          "n_players": 5
        }
      ],
      "notable_milestones": [
        "1 prior Trophy win",
        "3 prior Wooden Spoons",
        "Wooden Spoon in 2 of the last 3 TEGs"
      ]
    },
    "David MULLIN": {
      "trophy_wins": 3,
      "jacket_wins": 9,
      "spoon_count": 4,
      "last_4_positions": [
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
        },
        {
          "teg": 16,
          "trophy_rank": 3,
          "jacket_rank": 2,
          "n_players": 5
        },
        {
          "teg": 17,
          "trophy_rank": 2,
          "jacket_rank": 2,
          "n_players": 5
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
      "jacket_wins": 2,
      "spoon_count": 2,
      "last_4_positions": [
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
        },
        {
          "teg": 16,
          "trophy_rank": 2,
          "jacket_rank": 1,
          "n_players": 5
        },
        {
          "teg": 17,
          "trophy_rank": 5,
          "jacket_rank": 3,
          "n_players": 5
        }
      ],
      "notable_milestones": [
        "4 prior Trophy wins",
        "2 prior Jacket wins",
        "2 prior Wooden Spoons",
        "reigning Wooden Spoon holder (TEG 17)"
      ]
    },
    "John PATTERSON": {
      "trophy_wins": 2,
      "jacket_wins": 0,
      "spoon_count": 1,
      "last_4_positions": [
        {
          "teg": 12,
          "trophy_rank": 1,
          "jacket_rank": 4,
          "n_players": 6
        },
        {
          "teg": 13,
          "trophy_rank": 4,
          "jacket_rank": 5,
          "n_players": 5
        },
        {
          "teg": 15,
          "trophy_rank": 3,
          "jacket_rank": 4,
          "n_players": 6
        },
        {
          "teg": 17,
          "trophy_rank": 4,
          "jacket_rank": 4,
          "n_players": 5
        }
      ],
      "notable_milestones": [
        "2 prior Trophy wins",
        "1 prior Wooden Spoon"
      ]
    },
    "Jon BAKER": {
      "trophy_wins": 4,
      "jacket_wins": 4,
      "spoon_count": 1,
      "last_4_positions": [
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
        },
        {
          "teg": 16,
          "trophy_rank": 4,
          "jacket_rank": 3,
          "n_players": 5
        },
        {
          "teg": 17,
          "trophy_rank": 1,
          "jacket_rank": 1,
          "n_players": 5
        }
      ],
      "notable_milestones": [
        "4 prior Trophy wins",
        "4 prior Jacket wins",
        "1 prior Wooden Spoon",
        "defending Trophy champion (TEG 17)"
      ]
    }
  },
  "player_course_history": {
    "Alex Baker": {
      "PGA Catalunya - Stadium": {
        "course": "PGA Catalunya - Stadium",
        "visit_count_through_this_teg": 6,
        "n_prior_visits": 4,
        "prior_best_gross": 93,
        "prior_best_teg": 12,
        "this_teg_best_gross": 100,
        "this_teg_best_round": 3,
        "strokes_vs_last_visit": 7,
        "is_course_pb_this_teg": false,
        "summary_facts": [
          "Alex Baker's 5th visit to PGA Catalunya - Stadium",
          "Alex Baker's prior best at PGA Catalunya - Stadium: 93 gross (TEG 12)",
          "Alex Baker was 7 shots worse than his last visit to PGA Catalunya - Stadium"
        ]
      },
      "PGA Catalunya - Tour": {
        "course": "PGA Catalunya - Tour",
        "visit_count_through_this_teg": 5,
        "n_prior_visits": 3,
        "prior_best_gross": 92,
        "prior_best_teg": 11,
        "this_teg_best_gross": 98,
        "this_teg_best_round": 1,
        "strokes_vs_last_visit": 2,
        "is_course_pb_this_teg": false,
        "summary_facts": [
          "Alex Baker's 4th visit to PGA Catalunya - Tour",
          "Alex Baker's prior best at PGA Catalunya - Tour: 92 gross (TEG 11)"
        ]
      }
    },
    "David Mullin": {
      "PGA Catalunya - Stadium": {
        "course": "PGA Catalunya - Stadium",
        "visit_count_through_this_teg": 7,
        "n_prior_visits": 5,
        "prior_best_gross": 91,
        "prior_best_teg": 11,
        "this_teg_best_gross": 84,
        "this_teg_best_round": 3,
        "strokes_vs_last_visit": -8,
        "is_course_pb_this_teg": true,
        "summary_facts": [
          "David Mullin's 6th visit to PGA Catalunya - Stadium",
          "David Mullin's prior best at PGA Catalunya - Stadium: 91 gross (TEG 11)",
          "David Mullin's new personal best at PGA Catalunya - Stadium in R3: 84 gross — improved by 7",
          "David Mullin was 8 shots better than his last visit to PGA Catalunya - Stadium"
        ]
      },
      "PGA Catalunya - Tour": {
        "course": "PGA Catalunya - Tour",
        "visit_count_through_this_teg": 6,
        "n_prior_visits": 4,
        "prior_best_gross": 84,
        "prior_best_teg": 12,
        "this_teg_best_gross": 94,
        "this_teg_best_round": 2,
        "strokes_vs_last_visit": 10,
        "is_course_pb_this_teg": false,
        "summary_facts": [
          "David Mullin's 5th visit to PGA Catalunya - Tour",
          "David Mullin's prior best at PGA Catalunya - Tour: 84 gross (TEG 12)",
          "David Mullin was 10 shots worse than his last visit to PGA Catalunya - Tour"
        ]
      }
    },
    "Gregg Williams": {
      "PGA Catalunya - Stadium": {
        "course": "PGA Catalunya - Stadium",
        "visit_count_through_this_teg": 7,
        "n_prior_visits": 5,
        "prior_best_gross": 92,
        "prior_best_teg": 12,
        "this_teg_best_gross": 84,
        "this_teg_best_round": 4,
        "strokes_vs_last_visit": -8,
        "is_course_pb_this_teg": true,
        "summary_facts": [
          "Gregg Williams's 6th visit to PGA Catalunya - Stadium",
          "Gregg Williams's prior best at PGA Catalunya - Stadium: 92 gross (TEG 12)",
          "Gregg Williams's new personal best at PGA Catalunya - Stadium in R4: 84 gross — improved by 8",
          "Gregg Williams was 8 shots better than his last visit to PGA Catalunya - Stadium"
        ]
      },
      "PGA Catalunya - Tour": {
        "course": "PGA Catalunya - Tour",
        "visit_count_through_this_teg": 6,
        "n_prior_visits": 4,
        "prior_best_gross": 84,
        "prior_best_teg": 12,
        "this_teg_best_gross": 86,
        "this_teg_best_round": 2,
        "strokes_vs_last_visit": -2,
        "is_course_pb_this_teg": false,
        "summary_facts": [
          "Gregg Williams's 5th visit to PGA Catalunya - Tour",
          "Gregg Williams's prior best at PGA Catalunya - Tour: 84 gross (TEG 12)"
        ]
      }
    },
    "John Patterson": {
      "PGA Catalunya - Stadium": {
        "course": "PGA Catalunya - Stadium",
        "visit_count_through_this_teg": 6,
        "n_prior_visits": 4,
        "prior_best_gross": 95,
        "prior_best_teg": 12,
        "this_teg_best_gross": 93,
        "this_teg_best_round": 3,
        "strokes_vs_last_visit": -4,
        "is_course_pb_this_teg": true,
        "summary_facts": [
          "John Patterson's 5th visit to PGA Catalunya - Stadium",
          "John Patterson's prior best at PGA Catalunya - Stadium: 95 gross (TEG 12)",
          "John Patterson's new personal best at PGA Catalunya - Stadium in R3: 93 gross — improved by 2"
        ]
      },
      "PGA Catalunya - Tour": {
        "course": "PGA Catalunya - Tour",
        "visit_count_through_this_teg": 5,
        "n_prior_visits": 3,
        "prior_best_gross": 96,
        "prior_best_teg": 12,
        "this_teg_best_gross": 94,
        "this_teg_best_round": 2,
        "strokes_vs_last_visit": -2,
        "is_course_pb_this_teg": true,
        "summary_facts": [
          "John Patterson's 4th visit to PGA Catalunya - Tour",
          "John Patterson's prior best at PGA Catalunya - Tour: 96 gross (TEG 12)",
          "John Patterson's new personal best at PGA Catalunya - Tour in R2: 94 gross — improved by 2"
        ]
      }
    },
    "Jon Baker": {
      "PGA Catalunya - Stadium": {
        "course": "PGA Catalunya - Stadium",
        "visit_count_through_this_teg": 7,
        "n_prior_visits": 5,
        "prior_best_gross": 89,
        "prior_best_teg": 12,
        "this_teg_best_gross": 97,
        "this_teg_best_round": 4,
        "strokes_vs_last_visit": 8,
        "is_course_pb_this_teg": false,
        "summary_facts": [
          "Jon Baker's 6th visit to PGA Catalunya - Stadium",
          "Jon Baker's prior best at PGA Catalunya - Stadium: 89 gross (TEG 12)",
          "Jon Baker was 8 shots worse than his last visit to PGA Catalunya - Stadium"
        ]
      },
      "PGA Catalunya - Tour": {
        "course": "PGA Catalunya - Tour",
        "visit_count_through_this_teg": 6,
        "n_prior_visits": 4,
        "prior_best_gross": 84,
        "prior_best_teg": 11,
        "this_teg_best_gross": 87,
        "this_teg_best_round": 2,
        "strokes_vs_last_visit": -1,
        "is_course_pb_this_teg": false,
        "summary_facts": [
          "Jon Baker's 5th visit to PGA Catalunya - Tour",
          "Jon Baker's prior best at PGA Catalunya - Tour: 84 gross (TEG 11)"
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
    "final_margin": 8,
    "trophy_metric": "stableford"
  },
  "recent_vehicle_choices": [
    {
      "teg": 15,
      "vehicles": [],
      "structure": "in_medias_res",
      "title": "Lisbon Belongs to Gregg"
    },
    {
      "teg": 16,
      "vehicles": [],
      "structure": "theme_led",
      "title": "Three Processions on the Lisbon Coast"
    },
    {
      "teg": 17,
      "vehicles": [
        "three_act",
        "hero_arc",
        "inversion"
      ],
      "structure": "three_act",
      "title": "The Coronation at Óbidos"
    }
  ],
  "beats": [
    {
      "id": "b01",
      "total": 20.0,
      "scope": "tournament",
      "type": "jacket_win",
      "round": null,
      "course": null,
      "headline": "Gregg Williams wins the Green Jacket at +66, by 14",
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
        "margin": 14,
        "runner_up": "David Mullin",
        "all_time_rank": 6,
        "player_rank": 1,
        "metric": "gross"
      }
    },
    {
      "id": "b02",
      "total": 19.0,
      "scope": "tournament",
      "type": "trophy_win",
      "round": null,
      "course": null,
      "headline": "Alex Baker wins the Trophy on 169 pts, by 8",
      "players": [
        "Alex Baker"
      ],
      "scores": {
        "importance": 10.0,
        "rarity": 4.0,
        "entertainment": 5.0
      },
      "mandatory": true,
      "holes": [],
      "context": {
        "score": 169,
        "margin": 8,
        "trophy_metric": "stableford",
        "runner_up": "John Patterson",
        "all_time_rank": 7,
        "player_rank": 2
      }
    },
    {
      "id": "b03",
      "total": 18.41,
      "scope": "stretch",
      "type": "hot_stretch",
      "round": 3,
      "course": "PGA Catalunya - Stadium",
      "headline": "Alex Baker piles up 21 points, holes 11-16 (R3)",
      "players": [
        "Alex Baker"
      ],
      "scores": {
        "importance": 7.4879999999999995,
        "rarity": 5.04,
        "entertainment": 5.880000000000001
      },
      "mandatory": false,
      "holes": [
        {
          "hole": 11,
          "par": 3,
          "sc": 3,
          "grossvp": 0,
          "stableford": 4,
          "result": "par",
          "si": 16
        },
        {
          "hole": 12,
          "par": 5,
          "sc": 6,
          "grossvp": 1,
          "stableford": 3,
          "result": "bogey",
          "si": 14
        },
        {
          "hole": 13,
          "par": 4,
          "sc": 4,
          "grossvp": 0,
          "stableford": 4,
          "result": "par",
          "si": 6
        },
        {
          "hole": 14,
          "par": 4,
          "sc": 4,
          "grossvp": 0,
          "stableford": 4,
          "result": "par",
          "si": 4
        },
        {
          "hole": 15,
          "par": 5,
          "sc": 6,
          "grossvp": 1,
          "stableford": 3,
          "result": "bogey",
          "si": 18
        },
        {
          "hole": 16,
          "par": 3,
          "sc": 4,
          "grossvp": 1,
          "stableford": 3,
          "result": "bogey",
          "si": 10
        }
      ],
      "context": {
        "points_gained": 21,
        "length": 6
      }
    },
    {
      "id": "b04",
      "total": 18.0,
      "scope": "hole",
      "type": "big_blowup",
      "round": 2,
      "course": "PGA Catalunya - Tour",
      "headline": "Alex Baker runs up a 11 (sextuple bogey) at the 18th (R2)",
      "players": [
        "Alex Baker"
      ],
      "scores": {
        "importance": 5.0,
        "rarity": 6,
        "entertainment": 7.0
      },
      "mandatory": true,
      "holes": [
        {
          "hole": 18,
          "par": 5,
          "sc": 11,
          "grossvp": 6,
          "stableford": 0,
          "result": "sextuple bogey",
          "si": 15
        }
      ],
      "context": {
        "is_player_par_worst": true,
        "is_teg_par_worst": false
      }
    },
    {
      "id": "b05",
      "total": 18.0,
      "scope": "hole",
      "type": "big_blowup",
      "round": 4,
      "course": "PGA Catalunya - Stadium",
      "headline": "Alex Baker runs up a 10 (sextuple bogey) at the 14th (R4)",
      "players": [
        "Alex Baker"
      ],
      "scores": {
        "importance": 5.0,
        "rarity": 6,
        "entertainment": 7.0
      },
      "mandatory": true,
      "holes": [
        {
          "hole": 14,
          "par": 4,
          "sc": 10,
          "grossvp": 6,
          "stableford": 0,
          "result": "sextuple bogey",
          "si": 4
        }
      ],
      "context": {
        "is_player_par_worst": false,
        "is_teg_par_worst": false
      }
    },
    {
      "id": "b06",
      "total": 17.7,
      "scope": "hole",
      "type": "big_blowup",
      "round": 1,
      "course": "PGA Catalunya - Tour",
      "headline": "David Mullin runs up a 11 (sextuple bogey) at the 15th (R1)",
      "players": [
        "David Mullin"
      ],
      "scores": {
        "importance": 4.4,
        "rarity": 6,
        "entertainment": 7.3
      },
      "mandatory": true,
      "holes": [
        {
          "hole": 15,
          "par": 5,
          "sc": 11,
          "grossvp": 6,
          "stableford": 0,
          "result": "sextuple bogey",
          "si": 5
        }
      ],
      "context": {
        "is_player_par_worst": true,
        "is_teg_par_worst": false
      }
    },
    {
      "id": "b07",
      "total": 16.43,
      "scope": "stretch",
      "type": "cold_stretch",
      "round": 1,
      "course": "PGA Catalunya - Tour",
      "headline": "John Patterson bleeds 22 shots, holes 3-10 (R1)",
      "players": [
        "John Patterson"
      ],
      "scores": {
        "importance": 6.342666666666666,
        "rarity": 4.3999999999999995,
        "entertainment": 5.683333333333333
      },
      "mandatory": false,
      "holes": [
        {
          "hole": 3,
          "par": 4,
          "sc": 8,
          "grossvp": 4,
          "stableford": 0,
          "result": "quadruple bogey",
          "si": 6
        },
        {
          "hole": 4,
          "par": 4,
          "sc": 7,
          "grossvp": 3,
          "stableford": 1,
          "result": "triple bogey",
          "si": 2
        },
        {
          "hole": 5,
          "par": 5,
          "sc": 7,
          "grossvp": 2,
          "stableford": 1,
          "result": "double bogey",
          "si": 16
        },
        {
          "hole": 6,
          "par": 4,
          "sc": 6,
          "grossvp": 2,
          "stableford": 1,
          "result": "double bogey",
          "si": 12
        },
        {
          "hole": 7,
          "par": 5,
          "sc": 8,
          "grossvp": 3,
          "stableford": 1,
          "result": "triple bogey",
          "si": 8
        },
        {
          "hole": 8,
          "par": 3,
          "sc": 6,
          "grossvp": 3,
          "stableford": 1,
          "result": "triple bogey",
          "si": 4
        },
        {
          "hole": 9,
          "par": 4,
          "sc": 7,
          "grossvp": 3,
          "stableford": 1,
          "result": "triple bogey",
          "si": 10
        },
        {
          "hole": 10,
          "par": 5,
          "sc": 7,
          "grossvp": 2,
          "stableford": 2,
          "result": "double bogey",
          "si": 9
        }
      ],
      "context": {
        "shots_dropped": 22,
        "length": 8
      }
    },
    {
      "id": "b08",
      "total": 16.0,
      "scope": "hole",
      "type": "big_blowup",
      "round": 2,
      "course": "PGA Catalunya - Tour",
      "headline": "Alex Baker runs up a 8 (quintuple bogey) at the 16th (R2)",
      "players": [
        "Alex Baker"
      ],
      "scores": {
        "importance": 5.0,
        "rarity": 5,
        "entertainment": 6.0
      },
      "mandatory": false,
      "holes": [
        {
          "hole": 16,
          "par": 3,
          "sc": 8,
          "grossvp": 5,
          "stableford": 0,
          "result": "quintuple bogey",
          "si": 17
        }
      ],
      "context": {
        "is_player_par_worst": true,
        "is_teg_par_worst": false
      }
    },
    {
      "id": "b09",
      "total": 15.82,
      "scope": "stretch",
      "type": "hot_stretch",
      "round": 1,
      "course": "PGA Catalunya - Tour",
      "headline": "Alex Baker piles up 17 points, holes 8-12 (R1)",
      "players": [
        "Alex Baker"
      ],
      "scores": {
        "importance": 6.976,
        "rarity": 4.08,
        "entertainment": 4.760000000000001
      },
      "mandatory": false,
      "holes": [
        {
          "hole": 8,
          "par": 3,
          "sc": 4,
          "grossvp": 1,
          "stableford": 3,
          "result": "bogey",
          "si": 4
        },
        {
          "hole": 9,
          "par": 4,
          "sc": 5,
          "grossvp": 1,
          "stableford": 3,
          "result": "bogey",
          "si": 10
        },
        {
          "hole": 10,
          "par": 5,
          "sc": 5,
          "grossvp": 0,
          "stableford": 4,
          "result": "par",
          "si": 9
        },
        {
          "hole": 11,
          "par": 3,
          "sc": 3,
          "grossvp": 0,
          "stableford": 4,
          "result": "par",
          "si": 7
        },
        {
          "hole": 12,
          "par": 4,
          "sc": 5,
          "grossvp": 1,
          "stableford": 3,
          "result": "bogey",
          "si": 11
        }
      ],
      "context": {
        "points_gained": 17,
        "length": 5
      }
    },
    {
      "id": "b10",
      "total": 15.4,
      "scope": "hole",
      "type": "big_blowup",
      "round": 3,
      "course": "PGA Catalunya - Stadium",
      "headline": "Jon Baker runs up a 9 (quintuple bogey) at the 4th (R3)",
      "players": [
        "Jon Baker"
      ],
      "scores": {
        "importance": 3.8,
        "rarity": 5,
        "entertainment": 6.6
      },
      "mandatory": false,
      "holes": [
        {
          "hole": 4,
          "par": 4,
          "sc": 9,
          "grossvp": 5,
          "stableford": 0,
          "result": "quintuple bogey",
          "si": 9
        }
      ],
      "context": {
        "is_player_par_worst": false,
        "is_teg_par_worst": false
      }
    },
    {
      "id": "b11",
      "total": 15.0,
      "scope": "tournament",
      "type": "wooden_spoon",
      "round": null,
      "course": null,
      "headline": "Jon Baker collects the Wooden Spoon (126 pts)",
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
        "score": 126,
        "trophy_metric": "stableford"
      }
    },
    {
      "id": "b12",
      "total": 14.9,
      "scope": "hole",
      "type": "lead_change",
      "round": 3,
      "course": "PGA Catalunya - Stadium",
      "headline": "Gregg Williams takes the Green Jacket (Gross) lead (R3 H2)",
      "players": [
        "Gregg Williams"
      ],
      "scores": {
        "importance": 7.9,
        "rarity": 2.0,
        "entertainment": 5.0
      },
      "mandatory": false,
      "holes": [
        {
          "hole": 2,
          "par": 4,
          "sc": 4,
          "grossvp": 0,
          "stableford": 3,
          "result": "par",
          "si": 5
        }
      ],
      "context": {
        "competition": "Green Jacket (Gross)",
        "rank_before": 3,
        "rank_after": 3,
        "lead_type": "outright"
      }
    },
    {
      "id": "b13",
      "total": 14.78,
      "scope": "stretch",
      "type": "hot_stretch",
      "round": 2,
      "course": "PGA Catalunya - Tour",
      "headline": "John Patterson piles up 16 points, holes 11-15 (R2)",
      "players": [
        "John Patterson"
      ],
      "scores": {
        "importance": 6.0775999999999994,
        "rarity": 3.84,
        "entertainment": 4.864000000000001
      },
      "mandatory": false,
      "holes": [
        {
          "hole": 11,
          "par": 3,
          "sc": 3,
          "grossvp": 0,
          "stableford": 4,
          "result": "par",
          "si": 7
        },
        {
          "hole": 12,
          "par": 4,
          "sc": 4,
          "grossvp": 0,
          "stableford": 3,
          "result": "par",
          "si": 11
        },
        {
          "hole": 13,
          "par": 4,
          "sc": 5,
          "grossvp": 1,
          "stableford": 3,
          "result": "bogey",
          "si": 1
        },
        {
          "hole": 14,
          "par": 3,
          "sc": 3,
          "grossvp": 0,
          "stableford": 3,
          "result": "par",
          "si": 13
        },
        {
          "hole": 15,
          "par": 5,
          "sc": 6,
          "grossvp": 1,
          "stableford": 3,
          "result": "bogey",
          "si": 5
        }
      ],
      "context": {
        "points_gained": 16,
        "length": 5
      }
    },
    {
      "id": "b14",
      "total": 14.4,
      "scope": "stretch",
      "type": "hot_stretch",
      "round": 2,
      "course": "PGA Catalunya - Tour",
      "headline": "Jon Baker piles up 16 points, holes 14-18 (R2)",
      "players": [
        "Jon Baker"
      ],
      "scores": {
        "importance": 5.307199999999999,
        "rarity": 3.84,
        "entertainment": 5.248000000000001
      },
      "mandatory": false,
      "holes": [
        {
          "hole": 14,
          "par": 3,
          "sc": 2,
          "grossvp": -1,
          "stableford": 4,
          "result": "birdie",
          "si": 13
        },
        {
          "hole": 15,
          "par": 5,
          "sc": 5,
          "grossvp": 0,
          "stableford": 3,
          "result": "par",
          "si": 5
        },
        {
          "hole": 16,
          "par": 3,
          "sc": 3,
          "grossvp": 0,
          "stableford": 3,
          "result": "par",
          "si": 17
        },
        {
          "hole": 17,
          "par": 4,
          "sc": 4,
          "grossvp": 0,
          "stableford": 3,
          "result": "par",
          "si": 3
        },
        {
          "hole": 18,
          "par": 5,
          "sc": 5,
          "grossvp": 0,
          "stableford": 3,
          "result": "par",
          "si": 15
        }
      ],
      "context": {
        "points_gained": 16,
        "length": 5
      }
    },
    {
      "id": "b15",
      "total": 14.0,
      "scope": "hole",
      "type": "big_blowup",
      "round": 1,
      "course": "PGA Catalunya - Tour",
      "headline": "Alex Baker runs up a 7 (quadruple bogey) at the 2nd (R1)",
      "players": [
        "Alex Baker"
      ],
      "scores": {
        "importance": 5.0,
        "rarity": 4,
        "entertainment": 5.0
      },
      "mandatory": false,
      "holes": [
        {
          "hole": 2,
          "par": 3,
          "sc": 7,
          "grossvp": 4,
          "stableford": 0,
          "result": "quadruple bogey",
          "si": 18
        }
      ],
      "context": {
        "is_player_par_worst": false,
        "is_teg_par_worst": false
      }
    },
    {
      "id": "b16",
      "total": 14.0,
      "scope": "hole",
      "type": "big_blowup",
      "round": 1,
      "course": "PGA Catalunya - Tour",
      "headline": "Alex Baker runs up a 9 (quadruple bogey) at the 18th (R1)",
      "players": [
        "Alex Baker"
      ],
      "scores": {
        "importance": 5.0,
        "rarity": 4,
        "entertainment": 5.0
      },
      "mandatory": false,
      "holes": [
        {
          "hole": 18,
          "par": 5,
          "sc": 9,
          "grossvp": 4,
          "stableford": 0,
          "result": "quadruple bogey",
          "si": 15
        }
      ],
      "context": {
        "is_player_par_worst": false,
        "is_teg_par_worst": false
      }
    },
    {
      "id": "b17",
      "total": 14.0,
      "scope": "hole",
      "type": "big_blowup",
      "round": 1,
      "course": "PGA Catalunya - Tour",
      "headline": "Gregg Williams runs up a 9 (quadruple bogey) at the 7th (R1)",
      "players": [
        "Gregg Williams"
      ],
      "scores": {
        "importance": 5.0,
        "rarity": 4,
        "entertainment": 5.0
      },
      "mandatory": false,
      "holes": [
        {
          "hole": 7,
          "par": 5,
          "sc": 9,
          "grossvp": 4,
          "stableford": 0,
          "result": "quadruple bogey",
          "si": 8
        }
      ],
      "context": {
        "is_player_par_worst": false,
        "is_teg_par_worst": false
      }
    },
    {
      "id": "b18",
      "total": 14.0,
      "scope": "hole",
      "type": "big_blowup",
      "round": 1,
      "course": "PGA Catalunya - Tour",
      "headline": "Gregg Williams runs up a 8 (quadruple bogey) at the 17th (R1)",
      "players": [
        "Gregg Williams"
      ],
      "scores": {
        "importance": 5.0,
        "rarity": 4,
        "entertainment": 5.0
      },
      "mandatory": false,
      "holes": [
        {
          "hole": 17,
          "par": 4,
          "sc": 8,
          "grossvp": 4,
          "stableford": 0,
          "result": "quadruple bogey",
          "si": 3
        }
      ],
      "context": {
        "is_player_par_worst": false,
        "is_teg_par_worst": false
      }
    },
    {
      "id": "b19",
      "total": 14.0,
      "scope": "hole",
      "type": "big_blowup",
      "round": 4,
      "course": "PGA Catalunya - Stadium",
      "headline": "Alex Baker runs up a 8 (quadruple bogey) at the 17th (R4)",
      "players": [
        "Alex Baker"
      ],
      "scores": {
        "importance": 5.0,
        "rarity": 4,
        "entertainment": 5.0
      },
      "mandatory": false,
      "holes": [
        {
          "hole": 17,
          "par": 4,
          "sc": 8,
          "grossvp": 4,
          "stableford": 0,
          "result": "quadruple bogey",
          "si": 8
        }
      ],
      "context": {
        "is_player_par_worst": false,
        "is_teg_par_worst": false
      }
    },
    {
      "id": "b20",
      "total": 13.7,
      "scope": "hole",
      "type": "big_blowup",
      "round": 1,
      "course": "PGA Catalunya - Tour",
      "headline": "David Mullin runs up a 8 (quadruple bogey) at the 6th (R1)",
      "players": [
        "David Mullin"
      ],
      "scores": {
        "importance": 4.4,
        "rarity": 4,
        "entertainment": 5.3
      },
      "mandatory": false,
      "holes": [
        {
          "hole": 6,
          "par": 4,
          "sc": 8,
          "grossvp": 4,
          "stableford": 0,
          "result": "quadruple bogey",
          "si": 12
        }
      ],
      "context": {
        "is_player_par_worst": false,
        "is_teg_par_worst": false
      }
    },
    {
      "id": "b21",
      "total": 13.7,
      "scope": "hole",
      "type": "big_blowup",
      "round": 1,
      "course": "PGA Catalunya - Tour",
      "headline": "John Patterson runs up a 8 (quadruple bogey) at the 3rd (R1)",
      "players": [
        "John Patterson"
      ],
      "scores": {
        "importance": 4.4,
        "rarity": 4,
        "entertainment": 5.3
      },
      "mandatory": false,
      "holes": [
        {
          "hole": 3,
          "par": 4,
          "sc": 8,
          "grossvp": 4,
          "stableford": 0,
          "result": "quadruple bogey",
          "si": 6
        }
      ],
      "context": {
        "is_player_par_worst": false,
        "is_teg_par_worst": false
      }
    },
    {
      "id": "b22",
      "total": 13.7,
      "scope": "hole",
      "type": "big_blowup",
      "round": 2,
      "course": "PGA Catalunya - Tour",
      "headline": "David Mullin runs up a 8 (quadruple bogey) at the 4th (R2)",
      "players": [
        "David Mullin"
      ],
      "scores": {
        "importance": 4.4,
        "rarity": 4,
        "entertainment": 5.3
      },
      "mandatory": false,
      "holes": [
        {
          "hole": 4,
          "par": 4,
          "sc": 8,
          "grossvp": 4,
          "stableford": 0,
          "result": "quadruple bogey",
          "si": 2
        }
      ],
      "context": {
        "is_player_par_worst": false,
        "is_teg_par_worst": false
      }
    },
    {
      "id": "b23",
      "total": 13.7,
      "scope": "hole",
      "type": "big_blowup",
      "round": 2,
      "course": "PGA Catalunya - Tour",
      "headline": "David Mullin runs up a 8 (quadruple bogey) at the 6th (R2)",
      "players": [
        "David Mullin"
      ],
      "scores": {
        "importance": 4.4,
        "rarity": 4,
        "entertainment": 5.3
      },
      "mandatory": false,
      "holes": [
        {
          "hole": 6,
          "par": 4,
          "sc": 8,
          "grossvp": 4,
          "stableford": 0,
          "result": "quadruple bogey",
          "si": 12
        }
      ],
      "context": {
        "is_player_par_worst": false,
        "is_teg_par_worst": false
      }
    },
    {
      "id": "b24",
      "total": 13.7,
      "scope": "hole",
      "type": "big_blowup",
      "round": 2,
      "course": "PGA Catalunya - Tour",
      "headline": "John Patterson runs up a 8 (quadruple bogey) at the 4th (R2)",
      "players": [
        "John Patterson"
      ],
      "scores": {
        "importance": 4.4,
        "rarity": 4,
        "entertainment": 5.3
      },
      "mandatory": false,
      "holes": [
        {
          "hole": 4,
          "par": 4,
          "sc": 8,
          "grossvp": 4,
          "stableford": 0,
          "result": "quadruple bogey",
          "si": 2
        }
      ],
      "context": {
        "is_player_par_worst": false,
        "is_teg_par_worst": false
      }
    },
    {
      "id": "b25",
      "total": 13.22,
      "scope": "stretch",
      "type": "hot_stretch",
      "round": 1,
      "course": "PGA Catalunya - Tour",
      "headline": "Alex Baker piles up 13 points, holes 14-16 (R1)",
      "players": [
        "Alex Baker"
      ],
      "scores": {
        "importance": 6.464,
        "rarity": 3.12,
        "entertainment": 3.6400000000000006
      },
      "mandatory": false,
      "holes": [
        {
          "hole": 14,
          "par": 3,
          "sc": 3,
          "grossvp": 0,
          "stableford": 4,
          "result": "par",
          "si": 13
        },
        {
          "hole": 15,
          "par": 5,
          "sc": 4,
          "grossvp": -1,
          "stableford": 5,
          "result": "birdie",
          "si": 5
        },
        {
          "hole": 16,
          "par": 3,
          "sc": 3,
          "grossvp": 0,
          "stableford": 4,
          "result": "par",
          "si": 17
        }
      ],
      "context": {
        "points_gained": 13,
        "length": 3
      }
    },
    {
      "id": "b26",
      "total": 13.22,
      "scope": "stretch",
      "type": "hot_stretch",
      "round": 2,
      "course": "PGA Catalunya - Tour",
      "headline": "Gregg Williams piles up 13 points, holes 13-16 (R2)",
      "players": [
        "Gregg Williams"
      ],
      "scores": {
        "importance": 6.464,
        "rarity": 3.12,
        "entertainment": 3.6400000000000006
      },
      "mandatory": false,
      "holes": [
        {
          "hole": 13,
          "par": 4,
          "sc": 4,
          "grossvp": 0,
          "stableford": 4,
          "result": "par",
          "si": 1
        },
        {
          "hole": 14,
          "par": 3,
          "sc": 3,
          "grossvp": 0,
          "stableford": 3,
          "result": "par",
          "si": 13
        },
        {
          "hole": 15,
          "par": 5,
          "sc": 5,
          "grossvp": 0,
          "stableford": 3,
          "result": "par",
          "si": 5
        },
        {
          "hole": 16,
          "par": 3,
          "sc": 3,
          "grossvp": 0,
          "stableford": 3,
          "result": "par",
          "si": 17
        }
      ],
      "context": {
        "points_gained": 13,
        "length": 4
      }
    },
    {
      "id": "b27",
      "total": 13.2,
      "scope": "hole",
      "type": "spoon_change",
      "round": 3,
      "course": "PGA Catalunya - Stadium",
      "headline": "Jon Baker drops to the bottom of the Wooden Spoon race (R3 H2)",
      "players": [
        "Jon Baker"
      ],
      "scores": {
        "importance": 4.6,
        "rarity": 2.0,
        "entertainment": 6.6
      },
      "mandatory": false,
      "holes": [
        {
          "hole": 2,
          "par": 4,
          "sc": 7,
          "grossvp": 3,
          "stableford": 0,
          "result": "triple bogey",
          "si": 5
        }
      ],
      "context": {
        "competition": "Wooden Spoon",
        "rank_before": 4,
        "rank_after": 5
      }
    },
    {
      "id": "b28",
      "total": 12.81,
      "scope": "stretch",
      "type": "hot_stretch",
      "round": 1,
      "course": "PGA Catalunya - Tour",
      "headline": "John Patterson piles up 13 points, holes 13-16 (R1)",
      "players": [
        "John Patterson"
      ],
      "scores": {
        "importance": 5.7368,
        "rarity": 3.12,
        "entertainment": 3.9520000000000004
      },
      "mandatory": false,
      "holes": [
        {
          "hole": 13,
          "par": 4,
          "sc": 4,
          "grossvp": 0,
          "stableford": 4,
          "result": "par",
          "si": 1
        },
        {
          "hole": 14,
          "par": 3,
          "sc": 3,
          "grossvp": 0,
          "stableford": 3,
          "result": "par",
          "si": 13
        },
        {
          "hole": 15,
          "par": 5,
          "sc": 6,
          "grossvp": 1,
          "stableford": 3,
          "result": "bogey",
          "si": 5
        },
        {
          "hole": 16,
          "par": 3,
          "sc": 3,
          "grossvp": 0,
          "stableford": 3,
          "result": "par",
          "si": 17
        }
      ],
      "context": {
        "points_gained": 13,
        "length": 4
      }
    },
    {
      "id": "b29",
      "total": 12.58,
      "scope": "stretch",
      "type": "hot_stretch",
      "round": 3,
      "course": "PGA Catalunya - Stadium",
      "headline": "Gregg Williams piles up 12 points, holes 2-5 (R3)",
      "players": [
        "Gregg Williams"
      ],
      "scores": {
        "importance": 6.336,
        "rarity": 2.88,
        "entertainment": 3.3600000000000003
      },
      "mandatory": false,
      "holes": [
        {
          "hole": 2,
          "par": 4,
          "sc": 4,
          "grossvp": 0,
          "stableford": 3,
          "result": "par",
          "si": 5
        },
        {
          "hole": 3,
          "par": 5,
          "sc": 5,
          "grossvp": 0,
          "stableford": 3,
          "result": "par",
          "si": 13
        },
        {
          "hole": 4,
          "par": 4,
          "sc": 4,
          "grossvp": 0,
          "stableford": 3,
          "result": "par",
          "si": 9
        },
        {
          "hole": 5,
          "par": 3,
          "sc": 3,
          "grossvp": 0,
          "stableford": 3,
          "result": "par",
          "si": 7
        }
      ],
      "context": {
        "points_gained": 12,
        "length": 4
      }
    },
    {
      "id": "b30",
      "total": 12.55,
      "scope": "round",
      "type": "round_player",
      "round": 1,
      "course": "PGA Catalunya - Tour",
      "headline": "John Patterson far stronger on the back nine in R1 (14-pt split)",
      "players": [
        "John Patterson"
      ],
      "scores": {
        "importance": 4.55,
        "rarity": 3.0,
        "entertainment": 5.0
      },
      "mandatory": false,
      "holes": [],
      "context": {
        "round_score": 34,
        "round_gross_vp": 30,
        "trophy_metric": "stableford",
        "round_stableford": 34
      }
    },
    {
      "id": "b31",
      "total": 12.0,
      "scope": "stretch",
      "type": "recovery",
      "round": 1,
      "course": "PGA Catalunya - Tour",
      "headline": "Gregg Williams stops the bleeding with a birdie at the 15th (R1)",
      "players": [
        "Gregg Williams"
      ],
      "scores": {
        "importance": 5.0,
        "rarity": 3.0,
        "entertainment": 4.0
      },
      "mandatory": false,
      "holes": [
        {
          "hole": 2,
          "par": 3,
          "sc": 4,
          "grossvp": 1,
          "stableford": 2,
          "result": "bogey",
          "si": 18
        },
        {
          "hole": 3,
          "par": 4,
          "sc": 7,
          "grossvp": 3,
          "stableford": 0,
          "result": "triple bogey",
          "si": 6
        },
        {
          "hole": 4,
          "par": 4,
          "sc": 7,
          "grossvp": 3,
          "stableford": 1,
          "result": "triple bogey",
          "si": 2
        },
        {
          "hole": 5,
          "par": 5,
          "sc": 7,
          "grossvp": 2,
          "stableford": 1,
          "result": "double bogey",
          "si": 16
        },
        {
          "hole": 6,
          "par": 4,
          "sc": 5,
          "grossvp": 1,
          "stableford": 2,
          "result": "bogey",
          "si": 12
        },
        {
          "hole": 7,
          "par": 5,
          "sc": 9,
          "grossvp": 4,
          "stableford": 0,
          "result": "quadruple bogey",
          "si": 8
        },
        {
          "hole": 8,
          "par": 3,
          "sc": 4,
          "grossvp": 1,
          "stableford": 2,
          "result": "bogey",
          "si": 4
        },
        {
          "hole": 9,
          "par": 4,
          "sc": 5,
          "grossvp": 1,
          "stableford": 2,
          "result": "bogey",
          "si": 10
        },
        {
          "hole": 10,
          "par": 5,
          "sc": 6,
          "grossvp": 1,
          "stableford": 2,
          "result": "bogey",
          "si": 9
        },
        {
          "hole": 11,
          "par": 3,
          "sc": 4,
          "grossvp": 1,
          "stableford": 2,
          "result": "bogey",
          "si": 7
        },
        {
          "hole": 12,
          "par": 4,
          "sc": 5,
          "grossvp": 1,
          "stableford": 2,
          "result": "bogey",
          "si": 11
        },
        {
          "hole": 13,
          "par": 4,
          "sc": 5,
          "grossvp": 1,
          "stableford": 3,
          "result": "bogey",
          "si": 1
        },
        {
          "hole": 14,
          "par": 3,
          "sc": 4,
          "grossvp": 1,
          "stableford": 2,
          "result": "bogey",
          "si": 13
        },
        {
          "hole": 15,
          "par": 5,
          "sc": 4,
          "grossvp": -1,
          "stableford": 4,
          "result": "birdie",
          "si": 5
        }
      ],
      "context": {
        "streak_broken": "bogey_or_worse"
      }
    },
    {
      "id": "b32",
      "total": 12.0,
      "scope": "stretch",
      "type": "recovery",
      "round": 2,
      "course": "PGA Catalunya - Tour",
      "headline": "Alex Baker stops the bleeding with a birdie at the 17th (R2)",
      "players": [
        "Alex Baker"
      ],
      "scores": {
        "importance": 5.0,
        "rarity": 3.0,
        "entertainment": 4.0
      },
      "mandatory": false,
      "holes": [
        {
          "hole": 15,
          "par": 5,
          "sc": 7,
          "grossvp": 2,
          "stableford": 2,
          "result": "double bogey",
          "si": 5
        },
        {
          "hole": 16,
          "par": 3,
          "sc": 8,
          "grossvp": 5,
          "stableford": 0,
          "result": "quintuple bogey",
          "si": 17
        },
        {
          "hole": 17,
          "par": 4,
          "sc": 3,
          "grossvp": -1,
          "stableford": 5,
          "result": "birdie",
          "si": 3
        }
      ],
      "context": {
        "streak_broken": "bogey_or_worse"
      }
    },
    {
      "id": "b33",
      "total": 11.85,
      "scope": "stretch",
      "type": "recovery",
      "round": 4,
      "course": "PGA Catalunya - Stadium",
      "headline": "John Patterson stops the bleeding with a birdie at the 17th (R4)",
      "players": [
        "John Patterson"
      ],
      "scores": {
        "importance": 4.55,
        "rarity": 3.0,
        "entertainment": 4.3
      },
      "mandatory": false,
      "holes": [
        {
          "hole": 14,
          "par": 4,
          "sc": 7,
          "grossvp": 3,
          "stableford": 1,
          "result": "triple bogey",
          "si": 4
        },
        {
          "hole": 15,
          "par": 5,
          "sc": 7,
          "grossvp": 2,
          "stableford": 1,
          "result": "double bogey",
          "si": 18
        },
        {
          "hole": 16,
          "par": 3,
          "sc": 4,
          "grossvp": 1,
          "stableford": 3,
          "result": "bogey",
          "si": 10
        },
        {
          "hole": 17,
          "par": 4,
          "sc": 3,
          "grossvp": -1,
          "stableford": 5,
          "result": "birdie",
          "si": 8
        }
      ],
      "context": {
        "streak_broken": "bogey_or_worse"
      }
    },
    {
      "id": "b34",
      "total": 11.7,
      "scope": "stretch",
      "type": "recovery",
      "round": 2,
      "course": "PGA Catalunya - Tour",
      "headline": "Jon Baker stops the bleeding with a birdie at the 14th (R2)",
      "players": [
        "Jon Baker"
      ],
      "scores": {
        "importance": 4.1,
        "rarity": 3.0,
        "entertainment": 4.6
      },
      "mandatory": false,
      "holes": [
        {
          "hole": 12,
          "par": 4,
          "sc": 5,
          "grossvp": 1,
          "stableford": 2,
          "result": "bogey",
          "si": 11
        },
        {
          "hole": 13,
          "par": 4,
          "sc": 5,
          "grossvp": 1,
          "stableford": 2,
          "result": "bogey",
          "si": 1
        },
        {
          "hole": 14,
          "par": 3,
          "sc": 2,
          "grossvp": -1,
          "stableford": 4,
          "result": "birdie",
          "si": 13
        }
      ],
      "context": {
        "streak_broken": "bogey_or_worse"
      }
    },
    {
      "id": "b35",
      "total": 11.7,
      "scope": "stretch",
      "type": "recovery",
      "round": 4,
      "course": "PGA Catalunya - Stadium",
      "headline": "Jon Baker stops the bleeding with a birdie at the 13th (R4)",
      "players": [
        "Jon Baker"
      ],
      "scores": {
        "importance": 4.1,
        "rarity": 3.0,
        "entertainment": 4.6
      },
      "mandatory": false,
      "holes": [
        {
          "hole": 2,
          "par": 4,
          "sc": 6,
          "grossvp": 2,
          "stableford": 1,
          "result": "double bogey",
          "si": 5
        },
        {
          "hole": 3,
          "par": 5,
          "sc": 6,
          "grossvp": 1,
          "stableford": 2,
          "result": "bogey",
          "si": 13
        },
        {
          "hole": 4,
          "par": 4,
          "sc": 6,
          "grossvp": 2,
          "stableford": 1,
          "result": "double bogey",
          "si": 9
        },
        {
          "hole": 5,
          "par": 3,
          "sc": 4,
          "grossvp": 1,
          "stableford": 2,
          "result": "bogey",
          "si": 7
        },
        {
          "hole": 6,
          "par": 4,
          "sc": 5,
          "grossvp": 1,
          "stableford": 2,
          "result": "bogey",
          "si": 11
        },
        {
          "hole": 7,
          "par": 5,
          "sc": 7,
          "grossvp": 2,
          "stableford": 1,
          "result": "double bogey",
          "si": 17
        },
        {
          "hole": 8,
          "par": 3,
          "sc": 5,
          "grossvp": 2,
          "stableford": 1,
          "result": "double bogey",
          "si": 15
        },
        {
          "hole": 9,
          "par": 4,
          "sc": 6,
          "grossvp": 2,
          "stableford": 1,
          "result": "double bogey",
          "si": 1
        },
        {
          "hole": 10,
          "par": 4,
          "sc": 6,
          "grossvp": 2,
          "stableford": 1,
          "result": "double bogey",
          "si": 12
        },
        {
          "hole": 11,
          "par": 3,
          "sc": 5,
          "grossvp": 2,
          "stableford": 1,
          "result": "double bogey",
          "si": 16
        },
        {
          "hole": 12,
          "par": 5,
          "sc": 6,
          "grossvp": 1,
          "stableford": 2,
          "result": "bogey",
          "si": 14
        },
        {
          "hole": 13,
          "par": 4,
          "sc": 3,
          "grossvp": -1,
          "stableford": 4,
          "result": "birdie",
          "si": 6
        }
      ],
      "context": {
        "streak_broken": "bogey_or_worse"
      }
    },
    {
      "id": "b36",
      "total": 11.63,
      "scope": "stretch",
      "type": "hot_stretch",
      "round": 4,
      "course": "PGA Catalunya - Stadium",
      "headline": "Gregg Williams piles up 9 points, holes 8-10 (R4)",
      "players": [
        "Gregg Williams"
      ],
      "scores": {
        "importance": 6.952,
        "rarity": 2.16,
        "entertainment": 2.5200000000000005
      },
      "mandatory": false,
      "holes": [
        {
          "hole": 8,
          "par": 3,
          "sc": 3,
          "grossvp": 0,
          "stableford": 3,
          "result": "par",
          "si": 15
        },
        {
          "hole": 9,
          "par": 4,
          "sc": 5,
          "grossvp": 1,
          "stableford": 3,
          "result": "bogey",
          "si": 1
        },
        {
          "hole": 10,
          "par": 4,
          "sc": 4,
          "grossvp": 0,
          "stableford": 3,
          "result": "par",
          "si": 12
        }
      ],
      "context": {
        "points_gained": 9,
        "length": 3
      }
    },
    {
      "id": "b37",
      "total": 11.6,
      "scope": "hole",
      "type": "spoon_change",
      "round": 2,
      "course": "PGA Catalunya - Tour",
      "headline": "Gregg Williams drops to the bottom of the Wooden Spoon race (R2 H2)",
      "players": [
        "Gregg Williams"
      ],
      "scores": {
        "importance": 3.8,
        "rarity": 2.0,
        "entertainment": 5.8
      },
      "mandatory": false,
      "holes": [
        {
          "hole": 2,
          "par": 3,
          "sc": 4,
          "grossvp": 1,
          "stableford": 2,
          "result": "bogey",
          "si": 18
        }
      ],
      "context": {
        "competition": "Wooden Spoon",
        "rank_before": 4,
        "rank_after": 5
      }
    },
    {
      "id": "b38",
      "total": 11.6,
      "scope": "hole",
      "type": "spoon_change",
      "round": 2,
      "course": "PGA Catalunya - Tour",
      "headline": "Jon Baker drops to the bottom of the Wooden Spoon race (R2 H3)",
      "players": [
        "Jon Baker"
      ],
      "scores": {
        "importance": 3.8,
        "rarity": 2.0,
        "entertainment": 5.8
      },
      "mandatory": false,
      "holes": [
        {
          "hole": 3,
          "par": 4,
          "sc": 6,
          "grossvp": 2,
          "stableford": 1,
          "result": "double bogey",
          "si": 6
        }
      ],
      "context": {
        "competition": "Wooden Spoon",
        "rank_before": 4,
        "rank_after": 5
      }
    },
    {
      "id": "b39",
      "total": 11.6,
      "scope": "hole",
      "type": "spoon_change",
      "round": 2,
      "course": "PGA Catalunya - Tour",
      "headline": "Jon Baker drops to the bottom of the Wooden Spoon race (R2 H7)",
      "players": [
        "Jon Baker"
      ],
      "scores": {
        "importance": 3.8,
        "rarity": 2.0,
        "entertainment": 5.8
      },
      "mandatory": false,
      "holes": [
        {
          "hole": 7,
          "par": 5,
          "sc": 8,
          "grossvp": 3,
          "stableford": 0,
          "result": "triple bogey",
          "si": 8
        }
      ],
      "context": {
        "competition": "Wooden Spoon",
        "rank_before": 4,
        "rank_after": 5
      }
    },
    {
      "id": "b40",
      "total": 11.6,
      "scope": "hole",
      "type": "spoon_change",
      "round": 2,
      "course": "PGA Catalunya - Tour",
      "headline": "David Mullin drops to the bottom of the Wooden Spoon race (R2 H18)",
      "players": [
        "David Mullin"
      ],
      "scores": {
        "importance": 3.8,
        "rarity": 2.0,
        "entertainment": 5.8
      },
      "mandatory": false,
      "holes": [
        {
          "hole": 18,
          "par": 5,
          "sc": 7,
          "grossvp": 2,
          "stableford": 1,
          "result": "double bogey",
          "si": 15
        }
      ],
      "context": {
        "competition": "Wooden Spoon",
        "rank_before": 4,
        "rank_after": 5
      }
    },
    {
      "id": "b41",
      "total": 11.5,
      "scope": "stretch",
      "type": "collapse_after_steady",
      "round": 1,
      "course": "PGA Catalunya - Tour",
      "headline": "Alex Baker's steady run ends with a double bogey at the 17th (R1)",
      "players": [
        "Alex Baker"
      ],
      "scores": {
        "importance": 5.0,
        "rarity": 2.5,
        "entertainment": 4.0
      },
      "mandatory": false,
      "holes": [
        {
          "hole": 14,
          "par": 3,
          "sc": 3,
          "grossvp": 0,
          "stableford": 4,
          "result": "par",
          "si": 13
        },
        {
          "hole": 15,
          "par": 5,
          "sc": 4,
          "grossvp": -1,
          "stableford": 5,
          "result": "birdie",
          "si": 5
        },
        {
          "hole": 16,
          "par": 3,
          "sc": 3,
          "grossvp": 0,
          "stableford": 4,
          "result": "par",
          "si": 17
        },
        {
          "hole": 17,
          "par": 4,
          "sc": 6,
          "grossvp": 2,
          "stableford": 2,
          "result": "double bogey",
          "si": 3
        }
      ],
      "context": {
        "streak_broken": "par_or_better"
      }
    },
    {
      "id": "b42",
      "total": 11.5,
      "scope": "stretch",
      "type": "collapse_after_steady",
      "round": 3,
      "course": "PGA Catalunya - Stadium",
      "headline": "Gregg Williams's steady run ends with a double bogey at the 6th (R3)",
      "players": [
        "Gregg Williams"
      ],
      "scores": {
        "importance": 5.0,
        "rarity": 2.5,
        "entertainment": 4.0
      },
      "mandatory": false,
      "holes": [
        {
          "hole": 2,
          "par": 4,
          "sc": 4,
          "grossvp": 0,
          "stableford": 3,
          "result": "par",
          "si": 5
        },
        {
          "hole": 3,
          "par": 5,
          "sc": 5,
          "grossvp": 0,
          "stableford": 3,
          "result": "par",
          "si": 13
        },
        {
          "hole": 4,
          "par": 4,
          "sc": 4,
          "grossvp": 0,
          "stableford": 3,
          "result": "par",
          "si": 9
        },
        {
          "hole": 5,
          "par": 3,
          "sc": 3,
          "grossvp": 0,
          "stableford": 3,
          "result": "par",
          "si": 7
        },
        {
          "hole": 6,
          "par": 4,
          "sc": 6,
          "grossvp": 2,
          "stableford": 1,
          "result": "double bogey",
          "si": 11
        }
      ],
      "context": {
        "streak_broken": "par_or_better"
      }
    },
    {
      "id": "b43",
      "total": 11.28,
      "scope": "stretch",
      "type": "cold_stretch",
      "round": 3,
      "course": "PGA Catalunya - Stadium",
      "headline": "Alex Baker bleeds 12 shots, holes 6-10 (R3)",
      "players": [
        "Alex Baker"
      ],
      "scores": {
        "importance": 6.08,
        "rarity": 2.4,
        "entertainment": 2.8
      },
      "mandatory": false,
      "holes": [
        {
          "hole": 6,
          "par": 4,
          "sc": 7,
          "grossvp": 3,
          "stableford": 1,
          "result": "triple bogey",
          "si": 11
        },
        {
          "hole": 7,
          "par": 5,
          "sc": 7,
          "grossvp": 2,
          "stableford": 2,
          "result": "double bogey",
          "si": 17
        },
        {
          "hole": 8,
          "par": 3,
          "sc": 5,
          "grossvp": 2,
          "stableford": 2,
          "result": "double bogey",
          "si": 15
        },
        {
          "hole": 9,
          "par": 4,
          "sc": 6,
          "grossvp": 2,
          "stableford": 2,
          "result": "double bogey",
          "si": 1
        },
        {
          "hole": 10,
          "par": 4,
          "sc": 7,
          "grossvp": 3,
          "stableford": 1,
          "result": "triple bogey",
          "si": 12
        }
      ],
      "context": {
        "shots_dropped": 12,
        "length": 5
      }
    },
    {
      "id": "b44",
      "total": 11.18,
      "scope": "stretch",
      "type": "hot_stretch",
      "round": 4,
      "course": "PGA Catalunya - Stadium",
      "headline": "John Patterson piles up 9 points, holes 4-6 (R4)",
      "players": [
        "John Patterson"
      ],
      "scores": {
        "importance": 6.2824,
        "rarity": 2.16,
        "entertainment": 2.736
      },
      "mandatory": false,
      "holes": [
        {
          "hole": 4,
          "par": 4,
          "sc": 5,
          "grossvp": 1,
          "stableford": 3,
          "result": "bogey",
          "si": 9
        },
        {
          "hole": 5,
          "par": 3,
          "sc": 4,
          "grossvp": 1,
          "stableford": 3,
          "result": "bogey",
          "si": 7
        },
        {
          "hole": 6,
          "par": 4,
          "sc": 4,
          "grossvp": 0,
          "stableford": 3,
          "result": "par",
          "si": 11
        }
      ],
      "context": {
        "points_gained": 9,
        "length": 3
      }
    },
    {
      "id": "b45",
      "total": 10.84,
      "scope": "stretch",
      "type": "hot_stretch",
      "round": 3,
      "course": "PGA Catalunya - Stadium",
      "headline": "David Mullin piles up 10 points, holes 8-10 (R3)",
      "players": [
        "David Mullin"
      ],
      "scores": {
        "importance": 5.396,
        "rarity": 2.4,
        "entertainment": 3.04
      },
      "mandatory": false,
      "holes": [
        {
          "hole": 8,
          "par": 3,
          "sc": 3,
          "grossvp": 0,
          "stableford": 3,
          "result": "par",
          "si": 15
        },
        {
          "hole": 9,
          "par": 4,
          "sc": 5,
          "grossvp": 1,
          "stableford": 3,
          "result": "bogey",
          "si": 1
        },
        {
          "hole": 10,
          "par": 4,
          "sc": 3,
          "grossvp": -1,
          "stableford": 4,
          "result": "birdie",
          "si": 12
        }
      ],
      "context": {
        "points_gained": 10,
        "length": 3
      }
    },
    {
      "id": "b46",
      "total": 10.75,
      "scope": "hole",
      "type": "lead_change",
      "round": 2,
      "course": "PGA Catalunya - Tour",
      "headline": "Jon Baker takes the Green Jacket (Gross) lead (R2 H9)",
      "players": [
        "Jon Baker"
      ],
      "scores": {
        "importance": 5.25,
        "rarity": 2.0,
        "entertainment": 3.5
      },
      "mandatory": false,
      "holes": [
        {
          "hole": 9,
          "par": 4,
          "sc": 4,
          "grossvp": 0,
          "stableford": 3,
          "result": "par",
          "si": 10
        }
      ],
      "context": {
        "competition": "Green Jacket (Gross)",
        "rank_before": 5,
        "rank_after": 5,
        "lead_type": "outright"
      }
    },
    {
      "id": "b47",
      "total": 10.63,
      "scope": "stretch",
      "type": "hot_stretch",
      "round": 2,
      "course": "PGA Catalunya - Tour",
      "headline": "Gregg Williams piles up 9 points, holes 3-5 (R2)",
      "players": [
        "Gregg Williams"
      ],
      "scores": {
        "importance": 5.952,
        "rarity": 2.16,
        "entertainment": 2.5200000000000005
      },
      "mandatory": false,
      "holes": [
        {
          "hole": 3,
          "par": 4,
          "sc": 4,
          "grossvp": 0,
          "stableford": 3,
          "result": "par",
          "si": 6
        },
        {
          "hole": 4,
          "par": 4,
          "sc": 5,
          "grossvp": 1,
          "stableford": 3,
          "result": "bogey",
          "si": 2
        },
        {
          "hole": 5,
          "par": 5,
          "sc": 5,
          "grossvp": 0,
          "stableford": 3,
          "result": "par",
          "si": 16
        }
      ],
      "context": {
        "points_gained": 9,
        "length": 3
      }
    },
    {
      "id": "b48",
      "total": 10.38,
      "scope": "stretch",
      "type": "cold_stretch",
      "round": 4,
      "course": "PGA Catalunya - Stadium",
      "headline": "Jon Baker bleeds 10 shots, holes 7-11 (R4)",
      "players": [
        "Jon Baker"
      ],
      "scores": {
        "importance": 5.546666666666666,
        "rarity": 2.0,
        "entertainment": 2.8333333333333335
      },
      "mandatory": false,
      "holes": [
        {
          "hole": 7,
          "par": 5,
          "sc": 7,
          "grossvp": 2,
          "stableford": 1,
          "result": "double bogey",
          "si": 17
        },
        {
          "hole": 8,
          "par": 3,
          "sc": 5,
          "grossvp": 2,
          "stableford": 1,
          "result": "double bogey",
          "si": 15
        },
        {
          "hole": 9,
          "par": 4,
          "sc": 6,
          "grossvp": 2,
          "stableford": 1,
          "result": "double bogey",
          "si": 1
        },
        {
          "hole": 10,
          "par": 4,
          "sc": 6,
          "grossvp": 2,
          "stableford": 1,
          "result": "double bogey",
          "si": 12
        },
        {
          "hole": 11,
          "par": 3,
          "sc": 5,
          "grossvp": 2,
          "stableford": 1,
          "result": "double bogey",
          "si": 16
        }
      ],
      "context": {
        "shots_dropped": 10,
        "length": 5
      }
    },
    {
      "id": "b49",
      "total": 10.34,
      "scope": "stretch",
      "type": "cold_stretch",
      "round": 2,
      "course": "PGA Catalunya - Tour",
      "headline": "David Mullin bleeds 11 shots, holes 4-6 (R2)",
      "players": [
        "David Mullin"
      ],
      "scores": {
        "importance": 5.301333333333332,
        "rarity": 2.1999999999999997,
        "entertainment": 2.8416666666666663
      },
      "mandatory": false,
      "holes": [
        {
          "hole": 4,
          "par": 4,
          "sc": 8,
          "grossvp": 4,
          "stableford": 0,
          "result": "quadruple bogey",
          "si": 2
        },
        {
          "hole": 5,
          "par": 5,
          "sc": 8,
          "grossvp": 3,
          "stableford": 0,
          "result": "triple bogey",
          "si": 16
        },
        {
          "hole": 6,
          "par": 4,
          "sc": 8,
          "grossvp": 4,
          "stableford": 0,
          "result": "quadruple bogey",
          "si": 12
        }
      ],
      "context": {
        "shots_dropped": 11,
        "length": 3
      }
    },
    {
      "id": "b50",
      "total": 10.34,
      "scope": "stretch",
      "type": "cold_stretch",
      "round": 2,
      "course": "PGA Catalunya - Tour",
      "headline": "John Patterson bleeds 11 shots, holes 6-10 (R2)",
      "players": [
        "John Patterson"
      ],
      "scores": {
        "importance": 5.301333333333332,
        "rarity": 2.1999999999999997,
        "entertainment": 2.8416666666666663
      },
      "mandatory": false,
      "holes": [
        {
          "hole": 6,
          "par": 4,
          "sc": 7,
          "grossvp": 3,
          "stableford": 0,
          "result": "triple bogey",
          "si": 12
        },
        {
          "hole": 7,
          "par": 5,
          "sc": 7,
          "grossvp": 2,
          "stableford": 2,
          "result": "double bogey",
          "si": 8
        },
        {
          "hole": 8,
          "par": 3,
          "sc": 5,
          "grossvp": 2,
          "stableford": 2,
          "result": "double bogey",
          "si": 4
        },
        {
          "hole": 9,
          "par": 4,
          "sc": 6,
          "grossvp": 2,
          "stableford": 2,
          "result": "double bogey",
          "si": 10
        },
        {
          "hole": 10,
          "par": 5,
          "sc": 7,
          "grossvp": 2,
          "stableford": 2,
          "result": "double bogey",
          "si": 9
        }
      ],
      "context": {
        "shots_dropped": 11,
        "length": 5
      }
    },
    {
      "id": "b55",
      "total": 10.0,
      "scope": "hole",
      "type": "spoon_change",
      "round": 1,
      "course": "PGA Catalunya - Tour",
      "headline": "David Mullin drops to the bottom of the Wooden Spoon race (R1 H15)",
      "players": [
        "David Mullin"
      ],
      "scores": {
        "importance": 3.0,
        "rarity": 2.0,
        "entertainment": 5.0
      },
      "mandatory": true,
      "holes": [
        {
          "hole": 15,
          "par": 5,
          "sc": 11,
          "grossvp": 6,
          "stableford": 0,
          "result": "sextuple bogey",
          "si": 5
        }
      ],
      "context": {
        "competition": "Wooden Spoon",
        "rank_before": 2,
        "rank_after": 5
      }
    },
    {
      "id": "cr01",
      "total": 10.0,
      "scope": "round",
      "type": "course_record_low",
      "round": 3,
      "course": "PGA Catalunya - Stadium",
      "headline": "new PGA Catalunya - Stadium course record: 84 gross by David Mullin in R3, beating the prior record of 89 (across 27 prior visits)",
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
        "gross": 84,
        "prior_record": 89,
        "n_prior_visits": 27,
        "summary_fact": "new PGA Catalunya - Stadium course record: 84 gross by David Mullin in R3, beating the prior record of 89 (across 27 prior visits)"
      }
    },
    {
      "id": "cr02",
      "total": 10.0,
      "scope": "round",
      "type": "course_record_high",
      "round": 2,
      "course": "PGA Catalunya - Tour",
      "headline": "new PGA Catalunya - Tour course-worst: 106 gross by Alex Baker in R2, exceeding the prior worst of 105 (across 22 prior visits)",
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
        "gross": 106,
        "prior_record": 105,
        "n_prior_visits": 22,
        "summary_fact": "new PGA Catalunya - Tour course-worst: 106 gross by Alex Baker in R2, exceeding the prior worst of 105 (across 22 prior visits)"
      }
    }
  ]
}
