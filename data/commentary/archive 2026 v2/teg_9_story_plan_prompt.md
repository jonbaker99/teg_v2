# SYSTEM PROMPT (cached)

You are the editor planning a newspaper-style report on a TEG (an amateur golf tournament of several rounds). You do NOT write prose here — you produce a STRUCTURED PLAN that a writer will follow.

AUDIENCE: the players themselves — insiders who know each other, the courses, and the history. They will spot any factual error instantly, and they enjoy reliving the tournament and being gently ribbed.

HOUSE VOICE (for the writer who follows your plan): faithful, entertaining, tongue-in-cheek — in the spirit of Barney Ronay (Guardian) and Tom Peck (Times political sketches). Witty and characterful, but always anchored in the facts; never zany or over the top.

THE SPINE — the report is built around the three competitions, in this priority order:
1. The Trophy (Stableford) — the main event.
2. The Green Jacket (Gross).
3. The Wooden Spoon (last place on Stableford).
For each you MUST explain HOW it was won (or, for the Spoon, lost): the decisive moments, lead changes, and trajectory. Draw on the competition_arcs provided.

INPUT (JSON in the user turn):
- competition_arcs: leader-by-round, winner/loser trajectory, lead changes and the decisive moment for each competition.
- beats: a ranked list of notable events. Each has an `id`, three scores (importance = contribution to the result; rarity = how noteworthy in TEG history; entertainment = colour independent of the result), and hole-by-hole `holes` evidence. ALWAYS refer to beats by their `id`.
- venue: course one-liners and whether TEG has played here before.
- tone: a requested register; default to the house voice unless this overrides it.

YOUR JOB:
- Choose the story: one clear `theme` that runs through the whole report, and 2-4 `foreshadow` hooks to plant early that pay off later.
- Select the 6-10 `must_include_beat_ids` the report cannot omit. Be ruthless — list the rest you would cut in `cuts`.
- Per round: 3 witty `headline_candidates`, a `chosen_headline`, a one-line `angle`, and the `beat_ids` that belong to that round.
- Give each notable player a one-sentence `arc`. Mid-pack nobodies can be omitted.
- `venue_notes`: how/where to weave the course + location colour (use the venue input, e.g. "a new course for TEG" / "the Nth TEG round at this venue").
- `title` + a few `title_candidates`; record the resolved `tone`.

SELECTION PRINCIPLES:
- Favour high-importance beats for the spine, high-rarity for headlines and records, high-entertainment for colour and running threads.
- Foreground turning points, rare feats, and genuine colour; suppress filler.

RULES:
- Use ONLY the supplied data. Never invent scores, holes, players, or events. If unsure, leave it out. The players will catch any fabrication.
- Output only the structured plan.

---

# USER MESSAGE

Plan the report for the following TEG. Use ONLY this data.

{
  "teg": 9,
  "tone": "house",
  "venue": {
    "teg_num": 9,
    "area": "Lisbon Coast, Portugal",
    "year": 2016,
    "area_visit": "TEG's 3rd visit to Lisbon Coast, Portugal",
    "area_visit_n": 3,
    "rounds": [
      {
        "round": 1,
        "course": "Royal Óbidos",
        "date": "30/09/2016",
        "visit_n": 2,
        "visit_str": "the 2nd TEG round at this venue",
        "full_name": "Royal Obidos Spa & Golf Resort",
        "location": "Obidos, Lisbon Coast, Portugal",
        "type": "Parkland",
        "designer": "Seve Ballesteros",
        "description": "Seve Ballesteros' final course design, a challenging championship layout with dramatic water features. Hosts European Challenge Tour events."
      },
      {
        "round": 2,
        "course": "Praia D'El Rey",
        "date": "01/10/2016",
        "visit_n": 3,
        "visit_str": "the 3rd TEG round at this venue",
        "full_name": "Praia D'El Rey Golf & Beach Resort",
        "location": "Obidos, Lisbon Coast, Portugal",
        "type": "Links and Parkland",
        "designer": "Cabell B. Robinson",
        "description": "A spectacular course mixing parkland and links golf, with the back nine featuring dramatic coastal dunes. Highly ranked in European and world golf."
      },
      {
        "round": 3,
        "course": "Royal Óbidos",
        "date": "02/10/2016",
        "visit_n": 3,
        "visit_str": "the 3rd TEG round at this venue",
        "full_name": "Royal Obidos Spa & Golf Resort",
        "location": "Obidos, Lisbon Coast, Portugal",
        "type": "Parkland",
        "designer": "Seve Ballesteros",
        "description": "Seve Ballesteros' final course design, a challenging championship layout with dramatic water features. Hosts European Challenge Tour events."
      },
      {
        "round": 4,
        "course": "Praia D'El Rey",
        "date": "03/10/2016",
        "visit_n": 4,
        "visit_str": "the 4th TEG round at this venue",
        "full_name": "Praia D'El Rey Golf & Beach Resort",
        "location": "Obidos, Lisbon Coast, Portugal",
        "type": "Links and Parkland",
        "designer": "Cabell B. Robinson",
        "description": "A spectacular course mixing parkland and links golf, with the back nine featuring dramatic coastal dunes. Highly ranked in European and world golf."
      }
    ]
  },
  "competition_arcs": {
    "trophy": {
      "label": "Trophy (Stableford)",
      "winner": "John PATTERSON",
      "leader_by_round": [
        {
          "round": 1,
          "leader": "Jon BAKER",
          "lead": 1
        },
        {
          "round": 2,
          "leader": "John PATTERSON",
          "lead": 10
        },
        {
          "round": 3,
          "leader": "John PATTERSON",
          "lead": 3
        },
        {
          "round": 4,
          "leader": "John PATTERSON",
          "lead": 6
        }
      ],
      "winner_trajectory": [
        {
          "round": 1,
          "pos": 2,
          "gap": 1,
          "round_score": 38
        },
        {
          "round": 2,
          "pos": 1,
          "gap": 0,
          "round_score": 49
        },
        {
          "round": 3,
          "pos": 1,
          "gap": 0,
          "round_score": 34
        },
        {
          "round": 4,
          "pos": 1,
          "gap": 0,
          "round_score": 47
        }
      ],
      "lead_changes": [
        {
          "round": 1,
          "hole": 2,
          "player": "Jon BAKER"
        },
        {
          "round": 1,
          "hole": 3,
          "player": "David MULLIN"
        },
        {
          "round": 1,
          "hole": 4,
          "player": "Gregg WILLIAMS"
        },
        {
          "round": 1,
          "hole": 5,
          "player": "John PATTERSON"
        },
        {
          "round": 1,
          "hole": 6,
          "player": "Jon BAKER"
        },
        {
          "round": 2,
          "hole": 1,
          "player": "John PATTERSON"
        },
        {
          "round": 2,
          "hole": 2,
          "player": "David MULLIN"
        },
        {
          "round": 2,
          "hole": 11,
          "player": "John PATTERSON"
        },
        {
          "round": 4,
          "hole": 14,
          "player": "Alex BAKER"
        }
      ],
      "n_lead_changes": 9,
      "decisive_takeover": {
        "round": 2,
        "hole": 11,
        "player": "John PATTERSON"
      }
    },
    "jacket": {
      "label": "Green Jacket (Gross)",
      "winner": "David MULLIN",
      "leader_by_round": [
        {
          "round": 1,
          "leader": "David MULLIN",
          "lead": 2
        },
        {
          "round": 2,
          "leader": "David MULLIN",
          "lead": 7
        },
        {
          "round": 3,
          "leader": "David MULLIN",
          "lead": 7
        },
        {
          "round": 4,
          "leader": "David MULLIN",
          "lead": 10
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
          "round_score": 22
        },
        {
          "round": 4,
          "pos": 1,
          "gap": 0,
          "round_score": 16
        }
      ],
      "lead_changes": [
        {
          "round": 1,
          "hole": 3,
          "player": "David MULLIN"
        },
        {
          "round": 1,
          "hole": 6,
          "player": "Jon BAKER"
        },
        {
          "round": 1,
          "hole": 15,
          "player": "David MULLIN"
        },
        {
          "round": 1,
          "hole": 18,
          "player": "David MULLIN"
        }
      ],
      "n_lead_changes": 4,
      "decisive_takeover": {
        "round": 1,
        "hole": 18,
        "player": "David MULLIN"
      }
    },
    "spoon": {
      "label": "Wooden Spoon",
      "loser": "Stuart NEUMANN",
      "bottom_by_round": [
        {
          "round": 1,
          "bottom": "Stuart NEUMANN",
          "pos": 6
        },
        {
          "round": 2,
          "bottom": "Stuart NEUMANN",
          "pos": 6
        },
        {
          "round": 3,
          "bottom": "Stuart NEUMANN",
          "pos": 6
        },
        {
          "round": 4,
          "bottom": "Stuart NEUMANN",
          "pos": 6
        }
      ],
      "loser_trajectory": [
        {
          "round": 1,
          "pos": 6,
          "round_score": 23
        },
        {
          "round": 2,
          "pos": 6,
          "round_score": 30
        },
        {
          "round": 3,
          "pos": 6,
          "round_score": 37
        },
        {
          "round": 4,
          "pos": 6,
          "round_score": 37
        }
      ],
      "bottom_changes": [
        {
          "round": 1,
          "hole": 1,
          "player": "Gregg WILLIAMS"
        },
        {
          "round": 1,
          "hole": 2,
          "player": "Alex BAKER"
        },
        {
          "round": 1,
          "hole": 11,
          "player": "Stuart NEUMANN"
        },
        {
          "round": 1,
          "hole": 15,
          "player": "Stuart NEUMANN"
        }
      ],
      "n_bottom_changes": 4,
      "decisive_drop": {
        "round": 1,
        "hole": 15,
        "player": "Stuart NEUMANN"
      }
    }
  },
  "beats": [
    {
      "id": "b01",
      "total": 25.0,
      "scope": "tournament",
      "type": "trophy_win",
      "round": null,
      "headline": "John PATTERSON wins the Trophy on 168 pts, by 6",
      "players": [
        "John PATTERSON"
      ],
      "scores": {
        "importance": 10.0,
        "rarity": 10.0,
        "entertainment": 5.0
      },
      "holes": [],
      "context": {
        "score": 168,
        "margin": 6,
        "runner_up": "Alex BAKER",
        "all_time_rank": 1,
        "player_rank": 1
      }
    },
    {
      "id": "b02",
      "total": 20.0,
      "scope": "hole",
      "type": "lead_change",
      "round": 4,
      "headline": "Alex BAKER takes the Trophy (Stableford) lead (R4 H14)",
      "players": [
        "Alex BAKER"
      ],
      "scores": {
        "importance": 10.0,
        "rarity": 3.0,
        "entertainment": 7.0
      },
      "holes": [
        {
          "hole": 14,
          "par": 3,
          "sc": 5,
          "grossvp": 2,
          "stableford": 2,
          "result": "double bogey"
        }
      ],
      "context": {
        "competition": "Trophy (Stableford)",
        "rank_before": 2,
        "rank_after": 1
      }
    },
    {
      "id": "b03",
      "total": 20.0,
      "scope": "round",
      "type": "round_player",
      "round": 2,
      "headline": "John PATTERSON's 49 pts is the 2nd-best round in TEG history to date",
      "players": [
        "John PATTERSON"
      ],
      "scores": {
        "importance": 5.0,
        "rarity": 8.0,
        "entertainment": 7.0
      },
      "holes": [],
      "context": {
        "round_stableford": 49,
        "round_gross_vp": 14
      }
    },
    {
      "id": "b04",
      "total": 19.7,
      "scope": "hole",
      "type": "big_blowup",
      "round": 1,
      "headline": "Alex BAKER runs up a 11 (septuple bogey) at the 14th (R1)",
      "players": [
        "Alex BAKER"
      ],
      "scores": {
        "importance": 4.4,
        "rarity": 7,
        "entertainment": 8.3
      },
      "holes": [
        {
          "hole": 14,
          "par": 4,
          "sc": 11,
          "grossvp": 7,
          "stableford": 0,
          "result": "septuple bogey"
        }
      ],
      "context": {}
    },
    {
      "id": "b05",
      "total": 18.0,
      "scope": "hole",
      "type": "big_blowup",
      "round": 1,
      "headline": "John PATTERSON runs up a 10 (sextuple bogey) at the 4th (R1)",
      "players": [
        "John PATTERSON"
      ],
      "scores": {
        "importance": 5.0,
        "rarity": 6,
        "entertainment": 7.0
      },
      "holes": [
        {
          "hole": 4,
          "par": 4,
          "sc": 10,
          "grossvp": 6,
          "stableford": 0,
          "result": "sextuple bogey"
        }
      ],
      "context": {}
    },
    {
      "id": "b06",
      "total": 17.85,
      "scope": "round",
      "type": "round_player",
      "round": 2,
      "headline": "Alex BAKER posts a personal-best round: 44 pts",
      "players": [
        "Alex BAKER"
      ],
      "scores": {
        "importance": 4.55,
        "rarity": 7.0,
        "entertainment": 6.3
      },
      "holes": [],
      "context": {
        "round_stableford": 44,
        "round_gross_vp": 27
      }
    },
    {
      "id": "b07",
      "total": 17.85,
      "scope": "round",
      "type": "round_player",
      "round": 4,
      "headline": "Alex BAKER posts a personal-best round: 44 pts",
      "players": [
        "Alex BAKER"
      ],
      "scores": {
        "importance": 4.55,
        "rarity": 7.0,
        "entertainment": 6.3
      },
      "holes": [],
      "context": {
        "round_stableford": 44,
        "round_gross_vp": 27
      }
    },
    {
      "id": "b08",
      "total": 17.0,
      "scope": "tournament",
      "type": "jacket_win",
      "round": null,
      "headline": "David MULLIN wins the Green Jacket at +67, by 10",
      "players": [
        "David MULLIN"
      ],
      "scores": {
        "importance": 9.0,
        "rarity": 4.0,
        "entertainment": 4.0
      },
      "holes": [],
      "context": {
        "score": 67,
        "margin": 10,
        "runner_up": "Jon BAKER"
      }
    },
    {
      "id": "b09",
      "total": 16.8,
      "scope": "hole",
      "type": "big_blowup",
      "round": 1,
      "headline": "Gregg WILLIAMS runs up a 9 (sextuple bogey) at the 15th (R1)",
      "players": [
        "Gregg WILLIAMS"
      ],
      "scores": {
        "importance": 2.6,
        "rarity": 6,
        "entertainment": 8.2
      },
      "holes": [
        {
          "hole": 15,
          "par": 3,
          "sc": 9,
          "grossvp": 6,
          "stableford": 0,
          "result": "sextuple bogey"
        }
      ],
      "context": {}
    },
    {
      "id": "b10",
      "total": 16.8,
      "scope": "hole",
      "type": "big_blowup",
      "round": 2,
      "headline": "Gregg WILLIAMS runs up a 10 (sextuple bogey) at the 9th (R2)",
      "players": [
        "Gregg WILLIAMS"
      ],
      "scores": {
        "importance": 2.6,
        "rarity": 6,
        "entertainment": 8.2
      },
      "holes": [
        {
          "hole": 9,
          "par": 4,
          "sc": 10,
          "grossvp": 6,
          "stableford": 0,
          "result": "sextuple bogey"
        }
      ],
      "context": {}
    },
    {
      "id": "b11",
      "total": 16.8,
      "scope": "hole",
      "type": "big_blowup",
      "round": 4,
      "headline": "Gregg WILLIAMS runs up a 11 (sextuple bogey) at the 7th (R4)",
      "players": [
        "Gregg WILLIAMS"
      ],
      "scores": {
        "importance": 2.6,
        "rarity": 6,
        "entertainment": 8.2
      },
      "holes": [
        {
          "hole": 7,
          "par": 5,
          "sc": 11,
          "grossvp": 6,
          "stableford": 0,
          "result": "sextuple bogey"
        }
      ],
      "context": {}
    },
    {
      "id": "b12",
      "total": 16.2,
      "scope": "hole",
      "type": "lead_change",
      "round": 2,
      "headline": "John PATTERSON takes the Trophy (Stableford) lead (R2 H1)",
      "players": [
        "John PATTERSON"
      ],
      "scores": {
        "importance": 8.2,
        "rarity": 3.0,
        "entertainment": 5.0
      },
      "holes": [
        {
          "hole": 1,
          "par": 4,
          "sc": 5,
          "grossvp": 1,
          "stableford": 3,
          "result": "bogey"
        }
      ],
      "context": {
        "competition": "Trophy (Stableford)",
        "rank_before": 2,
        "rank_after": 1
      }
    },
    {
      "id": "b13",
      "total": 16.2,
      "scope": "hole",
      "type": "lead_change",
      "round": 2,
      "headline": "David MULLIN takes the Trophy (Stableford) lead (R2 H2)",
      "players": [
        "David MULLIN"
      ],
      "scores": {
        "importance": 8.2,
        "rarity": 3.0,
        "entertainment": 5.0
      },
      "holes": [
        {
          "hole": 2,
          "par": 5,
          "sc": 5,
          "grossvp": 0,
          "stableford": 3,
          "result": "par"
        }
      ],
      "context": {
        "competition": "Trophy (Stableford)",
        "rank_before": 2,
        "rank_after": 1
      }
    },
    {
      "id": "b14",
      "total": 16.2,
      "scope": "hole",
      "type": "lead_change",
      "round": 2,
      "headline": "John PATTERSON takes the Trophy (Stableford) lead (R2 H11)",
      "players": [
        "John PATTERSON"
      ],
      "scores": {
        "importance": 8.2,
        "rarity": 3.0,
        "entertainment": 5.0
      },
      "holes": [
        {
          "hole": 11,
          "par": 3,
          "sc": 3,
          "grossvp": 0,
          "stableford": 3,
          "result": "par"
        }
      ],
      "context": {
        "competition": "Trophy (Stableford)",
        "rank_before": 2,
        "rank_after": 1
      }
    },
    {
      "id": "b15",
      "total": 16.0,
      "scope": "hole",
      "type": "big_blowup",
      "round": 3,
      "headline": "David MULLIN runs up a 9 (quintuple bogey) at the 10th (R3)",
      "players": [
        "David MULLIN"
      ],
      "scores": {
        "importance": 5.0,
        "rarity": 5,
        "entertainment": 6.0
      },
      "holes": [
        {
          "hole": 10,
          "par": 4,
          "sc": 9,
          "grossvp": 5,
          "stableford": 0,
          "result": "quintuple bogey"
        }
      ],
      "context": {}
    },
    {
      "id": "b16",
      "total": 16.0,
      "scope": "hole",
      "type": "big_blowup",
      "round": 4,
      "headline": "John PATTERSON runs up a 9 (quintuple bogey) at the 5th (R4)",
      "players": [
        "John PATTERSON"
      ],
      "scores": {
        "importance": 5.0,
        "rarity": 5,
        "entertainment": 6.0
      },
      "holes": [
        {
          "hole": 5,
          "par": 4,
          "sc": 9,
          "grossvp": 5,
          "stableford": 0,
          "result": "quintuple bogey"
        }
      ],
      "context": {}
    },
    {
      "id": "b17",
      "total": 15.82,
      "scope": "stretch",
      "type": "hot_stretch",
      "round": 2,
      "headline": "John PATTERSON piles up 17 points, holes 9-13 (R2)",
      "players": [
        "John PATTERSON"
      ],
      "scores": {
        "importance": 6.976,
        "rarity": 4.08,
        "entertainment": 4.760000000000001
      },
      "holes": [
        {
          "hole": 9,
          "par": 4,
          "sc": 5,
          "grossvp": 1,
          "stableford": 3,
          "result": "bogey"
        },
        {
          "hole": 10,
          "par": 5,
          "sc": 5,
          "grossvp": 0,
          "stableford": 4,
          "result": "par"
        },
        {
          "hole": 11,
          "par": 3,
          "sc": 3,
          "grossvp": 0,
          "stableford": 3,
          "result": "par"
        },
        {
          "hole": 12,
          "par": 5,
          "sc": 4,
          "grossvp": -1,
          "stableford": 4,
          "result": "birdie"
        },
        {
          "hole": 13,
          "par": 4,
          "sc": 4,
          "grossvp": 0,
          "stableford": 3,
          "result": "par"
        }
      ],
      "context": {
        "points_gained": 17,
        "length": 5
      }
    },
    {
      "id": "b18",
      "total": 15.7,
      "scope": "hole",
      "type": "big_blowup",
      "round": 1,
      "headline": "Alex BAKER runs up a 9 (quintuple bogey) at the 12th (R1)",
      "players": [
        "Alex BAKER"
      ],
      "scores": {
        "importance": 4.4,
        "rarity": 5,
        "entertainment": 6.3
      },
      "holes": [
        {
          "hole": 12,
          "par": 4,
          "sc": 9,
          "grossvp": 5,
          "stableford": 0,
          "result": "quintuple bogey"
        }
      ],
      "context": {}
    },
    {
      "id": "b19",
      "total": 15.7,
      "scope": "hole",
      "type": "big_blowup",
      "round": 3,
      "headline": "Alex BAKER runs up a 9 (quintuple bogey) at the 14th (R3)",
      "players": [
        "Alex BAKER"
      ],
      "scores": {
        "importance": 4.4,
        "rarity": 5,
        "entertainment": 6.3
      },
      "holes": [
        {
          "hole": 14,
          "par": 4,
          "sc": 9,
          "grossvp": 5,
          "stableford": 0,
          "result": "quintuple bogey"
        }
      ],
      "context": {}
    },
    {
      "id": "b20",
      "total": 15.4,
      "scope": "hole",
      "type": "big_blowup",
      "round": 1,
      "headline": "Stuart NEUMANN runs up a 9 (quintuple bogey) at the 4th (R1)",
      "players": [
        "Stuart NEUMANN"
      ],
      "scores": {
        "importance": 3.8,
        "rarity": 5,
        "entertainment": 6.6
      },
      "holes": [
        {
          "hole": 4,
          "par": 4,
          "sc": 9,
          "grossvp": 5,
          "stableford": 0,
          "result": "quintuple bogey"
        }
      ],
      "context": {}
    },
    {
      "id": "b21",
      "total": 15.4,
      "scope": "hole",
      "type": "big_blowup",
      "round": 1,
      "headline": "Stuart NEUMANN runs up a 8 (quintuple bogey) at the 15th (R1)",
      "players": [
        "Stuart NEUMANN"
      ],
      "scores": {
        "importance": 3.8,
        "rarity": 5,
        "entertainment": 6.6
      },
      "holes": [
        {
          "hole": 15,
          "par": 3,
          "sc": 8,
          "grossvp": 5,
          "stableford": 0,
          "result": "quintuple bogey"
        }
      ],
      "context": {}
    },
    {
      "id": "b22",
      "total": 15.4,
      "scope": "stretch",
      "type": "hot_stretch",
      "round": 4,
      "headline": "Stuart NEUMANN piles up 16 points, holes 11-15 (R4)",
      "players": [
        "Stuart NEUMANN"
      ],
      "scores": {
        "importance": 6.307199999999999,
        "rarity": 3.84,
        "entertainment": 5.248000000000001
      },
      "holes": [
        {
          "hole": 11,
          "par": 3,
          "sc": 3,
          "grossvp": 0,
          "stableford": 3,
          "result": "par"
        },
        {
          "hole": 12,
          "par": 5,
          "sc": 5,
          "grossvp": 0,
          "stableford": 3,
          "result": "par"
        },
        {
          "hole": 13,
          "par": 4,
          "sc": 3,
          "grossvp": -1,
          "stableford": 4,
          "result": "birdie"
        },
        {
          "hole": 14,
          "par": 3,
          "sc": 3,
          "grossvp": 0,
          "stableford": 3,
          "result": "par"
        },
        {
          "hole": 15,
          "par": 4,
          "sc": 5,
          "grossvp": 1,
          "stableford": 3,
          "result": "bogey"
        }
      ],
      "context": {
        "points_gained": 16,
        "length": 5
      }
    },
    {
      "id": "b23",
      "total": 15.0,
      "scope": "tournament",
      "type": "wooden_spoon",
      "round": null,
      "headline": "Stuart NEUMANN collects the Wooden Spoon (127 pts)",
      "players": [
        "Stuart NEUMANN"
      ],
      "scores": {
        "importance": 5.0,
        "rarity": 3.0,
        "entertainment": 7.0
      },
      "holes": [],
      "context": {
        "score": 127
      }
    },
    {
      "id": "b24",
      "total": 14.8,
      "scope": "hole",
      "type": "big_blowup",
      "round": 1,
      "headline": "Gregg WILLIAMS runs up a 9 (quintuple bogey) at the 1st (R1)",
      "players": [
        "Gregg WILLIAMS"
      ],
      "scores": {
        "importance": 2.6,
        "rarity": 5,
        "entertainment": 7.2
      },
      "holes": [
        {
          "hole": 1,
          "par": 4,
          "sc": 9,
          "grossvp": 5,
          "stableford": 0,
          "result": "quintuple bogey"
        }
      ],
      "context": {}
    },
    {
      "id": "b25",
      "total": 14.78,
      "scope": "stretch",
      "type": "hot_stretch",
      "round": 3,
      "headline": "Jon BAKER piles up 16 points, holes 1-5 (R3)",
      "players": [
        "Jon BAKER"
      ],
      "scores": {
        "importance": 6.0775999999999994,
        "rarity": 3.84,
        "entertainment": 4.864000000000001
      },
      "holes": [
        {
          "hole": 1,
          "par": 4,
          "sc": 4,
          "grossvp": 0,
          "stableford": 3,
          "result": "par"
        },
        {
          "hole": 2,
          "par": 5,
          "sc": 4,
          "grossvp": -1,
          "stableford": 4,
          "result": "birdie"
        },
        {
          "hole": 3,
          "par": 3,
          "sc": 3,
          "grossvp": 0,
          "stableford": 3,
          "result": "par"
        },
        {
          "hole": 4,
          "par": 4,
          "sc": 5,
          "grossvp": 1,
          "stableford": 3,
          "result": "bogey"
        },
        {
          "hole": 5,
          "par": 5,
          "sc": 5,
          "grossvp": 0,
          "stableford": 3,
          "result": "par"
        }
      ],
      "context": {
        "points_gained": 16,
        "length": 5
      }
    },
    {
      "id": "b26",
      "total": 14.0,
      "scope": "hole",
      "type": "lead_change",
      "round": 1,
      "headline": "David MULLIN takes the Green Jacket (Gross) lead (R1 H3)",
      "players": [
        "David MULLIN"
      ],
      "scores": {
        "importance": 7.0,
        "rarity": 3.0,
        "entertainment": 4.0
      },
      "holes": [
        {
          "hole": 3,
          "par": 3,
          "sc": 3,
          "grossvp": 0,
          "stableford": 3,
          "result": "par"
        }
      ],
      "context": {
        "competition": "Green Jacket (Gross)",
        "rank_before": 3,
        "rank_after": 1
      }
    },
    {
      "id": "b27",
      "total": 14.0,
      "scope": "hole",
      "type": "lead_change",
      "round": 1,
      "headline": "David MULLIN takes the Trophy (Stableford) lead (R1 H3)",
      "players": [
        "David MULLIN"
      ],
      "scores": {
        "importance": 7.0,
        "rarity": 3.0,
        "entertainment": 4.0
      },
      "holes": [
        {
          "hole": 3,
          "par": 3,
          "sc": 3,
          "grossvp": 0,
          "stableford": 3,
          "result": "par"
        }
      ],
      "context": {
        "competition": "Trophy (Stableford)",
        "rank_before": 3,
        "rank_after": 1
      }
    },
    {
      "id": "b28",
      "total": 14.0,
      "scope": "hole",
      "type": "lead_change",
      "round": 1,
      "headline": "John PATTERSON takes the Trophy (Stableford) lead (R1 H5)",
      "players": [
        "John PATTERSON"
      ],
      "scores": {
        "importance": 7.0,
        "rarity": 3.0,
        "entertainment": 4.0
      },
      "holes": [
        {
          "hole": 5,
          "par": 5,
          "sc": 5,
          "grossvp": 0,
          "stableford": 4,
          "result": "par"
        }
      ],
      "context": {
        "competition": "Trophy (Stableford)",
        "rank_before": 3,
        "rank_after": 1
      }
    },
    {
      "id": "b29",
      "total": 14.0,
      "scope": "hole",
      "type": "lead_change",
      "round": 1,
      "headline": "David MULLIN takes the Green Jacket (Gross) lead (R1 H15)",
      "players": [
        "David MULLIN"
      ],
      "scores": {
        "importance": 7.0,
        "rarity": 3.0,
        "entertainment": 4.0
      },
      "holes": [
        {
          "hole": 15,
          "par": 3,
          "sc": 3,
          "grossvp": 0,
          "stableford": 3,
          "result": "par"
        }
      ],
      "context": {
        "competition": "Green Jacket (Gross)",
        "rank_before": 3,
        "rank_after": 2
      }
    },
    {
      "id": "b30",
      "total": 14.0,
      "scope": "hole",
      "type": "lead_change",
      "round": 1,
      "headline": "David MULLIN takes the Green Jacket (Gross) lead (R1 H18)",
      "players": [
        "David MULLIN"
      ],
      "scores": {
        "importance": 7.0,
        "rarity": 3.0,
        "entertainment": 4.0
      },
      "holes": [
        {
          "hole": 18,
          "par": 5,
          "sc": 5,
          "grossvp": 0,
          "stableford": 3,
          "result": "par"
        }
      ],
      "context": {
        "competition": "Green Jacket (Gross)",
        "rank_before": 3,
        "rank_after": 2
      }
    },
    {
      "id": "b31",
      "total": 14.0,
      "scope": "hole",
      "type": "big_blowup",
      "round": 1,
      "headline": "John PATTERSON runs up a 7 (quadruple bogey) at the 15th (R1)",
      "players": [
        "John PATTERSON"
      ],
      "scores": {
        "importance": 5.0,
        "rarity": 4,
        "entertainment": 5.0
      },
      "holes": [
        {
          "hole": 15,
          "par": 3,
          "sc": 7,
          "grossvp": 4,
          "stableford": 0,
          "result": "quadruple bogey"
        }
      ],
      "context": {}
    },
    {
      "id": "b32",
      "total": 14.0,
      "scope": "hole",
      "type": "big_blowup",
      "round": 3,
      "headline": "John PATTERSON runs up a 8 (quadruple bogey) at the 12th (R3)",
      "players": [
        "John PATTERSON"
      ],
      "scores": {
        "importance": 5.0,
        "rarity": 4,
        "entertainment": 5.0
      },
      "holes": [
        {
          "hole": 12,
          "par": 4,
          "sc": 8,
          "grossvp": 4,
          "stableford": 0,
          "result": "quadruple bogey"
        }
      ],
      "context": {}
    },
    {
      "id": "b33",
      "total": 14.0,
      "scope": "hole",
      "type": "big_blowup",
      "round": 3,
      "headline": "John PATTERSON runs up a 9 (quadruple bogey) at the 18th (R3)",
      "players": [
        "John PATTERSON"
      ],
      "scores": {
        "importance": 5.0,
        "rarity": 4,
        "entertainment": 5.0
      },
      "holes": [
        {
          "hole": 18,
          "par": 5,
          "sc": 9,
          "grossvp": 4,
          "stableford": 0,
          "result": "quadruple bogey"
        }
      ],
      "context": {}
    },
    {
      "id": "b34",
      "total": 14.0,
      "scope": "hole",
      "type": "big_blowup",
      "round": 4,
      "headline": "David MULLIN runs up a 8 (quadruple bogey) at the 1st (R4)",
      "players": [
        "David MULLIN"
      ],
      "scores": {
        "importance": 5.0,
        "rarity": 4,
        "entertainment": 5.0
      },
      "holes": [
        {
          "hole": 1,
          "par": 4,
          "sc": 8,
          "grossvp": 4,
          "stableford": 0,
          "result": "quadruple bogey"
        }
      ],
      "context": {}
    },
    {
      "id": "b35",
      "total": 13.87,
      "scope": "stretch",
      "type": "hot_stretch",
      "round": 2,
      "headline": "John PATTERSON piles up 14 points, holes 15-18 (R2)",
      "players": [
        "John PATTERSON"
      ],
      "scores": {
        "importance": 6.592,
        "rarity": 3.36,
        "entertainment": 3.92
      },
      "holes": [
        {
          "hole": 15,
          "par": 4,
          "sc": 4,
          "grossvp": 0,
          "stableford": 4,
          "result": "par"
        },
        {
          "hole": 16,
          "par": 4,
          "sc": 5,
          "grossvp": 1,
          "stableford": 3,
          "result": "bogey"
        },
        {
          "hole": 17,
          "par": 5,
          "sc": 5,
          "grossvp": 0,
          "stableford": 4,
          "result": "par"
        },
        {
          "hole": 18,
          "par": 4,
          "sc": 5,
          "grossvp": 1,
          "stableford": 3,
          "result": "bogey"
        }
      ],
      "context": {
        "points_gained": 14,
        "length": 4
      }
    },
    {
      "id": "b36",
      "total": 13.7,
      "scope": "hole",
      "type": "lead_change",
      "round": 1,
      "headline": "Jon BAKER takes the Trophy (Stableford) lead (R1 H2)",
      "players": [
        "Jon BAKER"
      ],
      "scores": {
        "importance": 6.7,
        "rarity": 3.0,
        "entertainment": 4.0
      },
      "holes": [
        {
          "hole": 2,
          "par": 5,
          "sc": 5,
          "grossvp": 0,
          "stableford": 3,
          "result": "par"
        }
      ],
      "context": {
        "competition": "Trophy (Stableford)",
        "rank_before": 2,
        "rank_after": 1
      }
    },
    {
      "id": "b37",
      "total": 13.7,
      "scope": "hole",
      "type": "lead_change",
      "round": 1,
      "headline": "Jon BAKER takes the Green Jacket (Gross) lead (R1 H6)",
      "players": [
        "Jon BAKER"
      ],
      "scores": {
        "importance": 6.7,
        "rarity": 3.0,
        "entertainment": 4.0
      },
      "holes": [
        {
          "hole": 6,
          "par": 3,
          "sc": 3,
          "grossvp": 0,
          "stableford": 3,
          "result": "par"
        }
      ],
      "context": {
        "competition": "Green Jacket (Gross)",
        "rank_before": 2,
        "rank_after": 1
      }
    },
    {
      "id": "b38",
      "total": 13.7,
      "scope": "hole",
      "type": "lead_change",
      "round": 1,
      "headline": "Jon BAKER takes the Trophy (Stableford) lead (R1 H6)",
      "players": [
        "Jon BAKER"
      ],
      "scores": {
        "importance": 6.7,
        "rarity": 3.0,
        "entertainment": 4.0
      },
      "holes": [
        {
          "hole": 6,
          "par": 3,
          "sc": 3,
          "grossvp": 0,
          "stableford": 3,
          "result": "par"
        }
      ],
      "context": {
        "competition": "Trophy (Stableford)",
        "rank_before": 2,
        "rank_after": 1
      }
    },
    {
      "id": "b39",
      "total": 13.7,
      "scope": "hole",
      "type": "big_blowup",
      "round": 1,
      "headline": "Alex BAKER runs up a 9 (quadruple bogey) at the 2nd (R1)",
      "players": [
        "Alex BAKER"
      ],
      "scores": {
        "importance": 4.4,
        "rarity": 4,
        "entertainment": 5.3
      },
      "holes": [
        {
          "hole": 2,
          "par": 5,
          "sc": 9,
          "grossvp": 4,
          "stableford": 0,
          "result": "quadruple bogey"
        }
      ],
      "context": {}
    },
    {
      "id": "b40",
      "total": 13.7,
      "scope": "hole",
      "type": "big_blowup",
      "round": 1,
      "headline": "Jon BAKER runs up a 9 (quadruple bogey) at the 18th (R1)",
      "players": [
        "Jon BAKER"
      ],
      "scores": {
        "importance": 4.4,
        "rarity": 4,
        "entertainment": 5.3
      },
      "holes": [
        {
          "hole": 18,
          "par": 5,
          "sc": 9,
          "grossvp": 4,
          "stableford": 0,
          "result": "quadruple bogey"
        }
      ],
      "context": {}
    },
    {
      "id": "b41",
      "total": 13.7,
      "scope": "hole",
      "type": "big_blowup",
      "round": 2,
      "headline": "Alex BAKER runs up a 9 (quadruple bogey) at the 10th (R2)",
      "players": [
        "Alex BAKER"
      ],
      "scores": {
        "importance": 4.4,
        "rarity": 4,
        "entertainment": 5.3
      },
      "holes": [
        {
          "hole": 10,
          "par": 5,
          "sc": 9,
          "grossvp": 4,
          "stableford": 0,
          "result": "quadruple bogey"
        }
      ],
      "context": {}
    },
    {
      "id": "b42",
      "total": 13.7,
      "scope": "hole",
      "type": "big_blowup",
      "round": 2,
      "headline": "Alex BAKER runs up a 7 (quadruple bogey) at the 14th (R2)",
      "players": [
        "Alex BAKER"
      ],
      "scores": {
        "importance": 4.4,
        "rarity": 4,
        "entertainment": 5.3
      },
      "holes": [
        {
          "hole": 14,
          "par": 3,
          "sc": 7,
          "grossvp": 4,
          "stableford": 0,
          "result": "quadruple bogey"
        }
      ],
      "context": {}
    },
    {
      "id": "b43",
      "total": 13.7,
      "scope": "hole",
      "type": "big_blowup",
      "round": 2,
      "headline": "Jon BAKER runs up a 7 (quadruple bogey) at the 14th (R2)",
      "players": [
        "Jon BAKER"
      ],
      "scores": {
        "importance": 4.4,
        "rarity": 4,
        "entertainment": 5.3
      },
      "holes": [
        {
          "hole": 14,
          "par": 3,
          "sc": 7,
          "grossvp": 4,
          "stableford": 0,
          "result": "quadruple bogey"
        }
      ],
      "context": {}
    },
    {
      "id": "b44",
      "total": 13.7,
      "scope": "hole",
      "type": "big_blowup",
      "round": 3,
      "headline": "Jon BAKER runs up a 9 (quadruple bogey) at the 11th (R3)",
      "players": [
        "Jon BAKER"
      ],
      "scores": {
        "importance": 4.4,
        "rarity": 4,
        "entertainment": 5.3
      },
      "holes": [
        {
          "hole": 11,
          "par": 5,
          "sc": 9,
          "grossvp": 4,
          "stableford": 0,
          "result": "quadruple bogey"
        }
      ],
      "context": {}
    },
    {
      "id": "b45",
      "total": 13.7,
      "scope": "hole",
      "type": "big_blowup",
      "round": 4,
      "headline": "Alex BAKER runs up a 8 (quadruple bogey) at the 6th (R4)",
      "players": [
        "Alex BAKER"
      ],
      "scores": {
        "importance": 4.4,
        "rarity": 4,
        "entertainment": 5.3
      },
      "holes": [
        {
          "hole": 6,
          "par": 4,
          "sc": 8,
          "grossvp": 4,
          "stableford": 0,
          "result": "quadruple bogey"
        }
      ],
      "context": {}
    },
    {
      "id": "b46",
      "total": 13.7,
      "scope": "hole",
      "type": "big_blowup",
      "round": 4,
      "headline": "Alex BAKER runs up a 8 (quadruple bogey) at the 15th (R4)",
      "players": [
        "Alex BAKER"
      ],
      "scores": {
        "importance": 4.4,
        "rarity": 4,
        "entertainment": 5.3
      },
      "holes": [
        {
          "hole": 15,
          "par": 4,
          "sc": 8,
          "grossvp": 4,
          "stableford": 0,
          "result": "quadruple bogey"
        }
      ],
      "context": {}
    },
    {
      "id": "b47",
      "total": 13.7,
      "scope": "hole",
      "type": "big_blowup",
      "round": 4,
      "headline": "Jon BAKER runs up a 9 (quadruple bogey) at the 17th (R4)",
      "players": [
        "Jon BAKER"
      ],
      "scores": {
        "importance": 4.4,
        "rarity": 4,
        "entertainment": 5.3
      },
      "holes": [
        {
          "hole": 17,
          "par": 5,
          "sc": 9,
          "grossvp": 4,
          "stableford": 0,
          "result": "quadruple bogey"
        }
      ],
      "context": {}
    },
    {
      "id": "b48",
      "total": 13.4,
      "scope": "hole",
      "type": "big_blowup",
      "round": 1,
      "headline": "Stuart NEUMANN runs up a 8 (quadruple bogey) at the 12th (R1)",
      "players": [
        "Stuart NEUMANN"
      ],
      "scores": {
        "importance": 3.8,
        "rarity": 4,
        "entertainment": 5.6
      },
      "holes": [
        {
          "hole": 12,
          "par": 4,
          "sc": 8,
          "grossvp": 4,
          "stableford": 0,
          "result": "quadruple bogey"
        }
      ],
      "context": {}
    },
    {
      "id": "b49",
      "total": 13.4,
      "scope": "hole",
      "type": "big_blowup",
      "round": 2,
      "headline": "Stuart NEUMANN runs up a 8 (quadruple bogey) at the 5th (R2)",
      "players": [
        "Stuart NEUMANN"
      ],
      "scores": {
        "importance": 3.8,
        "rarity": 4,
        "entertainment": 5.6
      },
      "holes": [
        {
          "hole": 5,
          "par": 4,
          "sc": 8,
          "grossvp": 4,
          "stableford": 0,
          "result": "quadruple bogey"
        }
      ],
      "context": {}
    },
    {
      "id": "b50",
      "total": 13.4,
      "scope": "hole",
      "type": "big_blowup",
      "round": 2,
      "headline": "Stuart NEUMANN runs up a 8 (quadruple bogey) at the 9th (R2)",
      "players": [
        "Stuart NEUMANN"
      ],
      "scores": {
        "importance": 3.8,
        "rarity": 4,
        "entertainment": 5.6
      },
      "holes": [
        {
          "hole": 9,
          "par": 4,
          "sc": 8,
          "grossvp": 4,
          "stableford": 0,
          "result": "quadruple bogey"
        }
      ],
      "context": {}
    },
    {
      "id": "b51",
      "total": 13.4,
      "scope": "hole",
      "type": "big_blowup",
      "round": 3,
      "headline": "Stuart NEUMANN runs up a 8 (quadruple bogey) at the 4th (R3)",
      "players": [
        "Stuart NEUMANN"
      ],
      "scores": {
        "importance": 3.8,
        "rarity": 4,
        "entertainment": 5.6
      },
      "holes": [
        {
          "hole": 4,
          "par": 4,
          "sc": 8,
          "grossvp": 4,
          "stableford": 0,
          "result": "quadruple bogey"
        }
      ],
      "context": {}
    },
    {
      "id": "b52",
      "total": 13.4,
      "scope": "hole",
      "type": "big_blowup",
      "round": 3,
      "headline": "Stuart NEUMANN runs up a 8 (quadruple bogey) at the 16th (R3)",
      "players": [
        "Stuart NEUMANN"
      ],
      "scores": {
        "importance": 3.8,
        "rarity": 4,
        "entertainment": 5.6
      },
      "holes": [
        {
          "hole": 16,
          "par": 4,
          "sc": 8,
          "grossvp": 4,
          "stableford": 0,
          "result": "quadruple bogey"
        }
      ],
      "context": {}
    },
    {
      "id": "b53",
      "total": 13.4,
      "scope": "hole",
      "type": "big_blowup",
      "round": 4,
      "headline": "Stuart NEUMANN runs up a 8 (quadruple bogey) at the 16th (R4)",
      "players": [
        "Stuart NEUMANN"
      ],
      "scores": {
        "importance": 3.8,
        "rarity": 4,
        "entertainment": 5.6
      },
      "holes": [
        {
          "hole": 16,
          "par": 4,
          "sc": 8,
          "grossvp": 4,
          "stableford": 0,
          "result": "quadruple bogey"
        }
      ],
      "context": {}
    },
    {
      "id": "b54",
      "total": 12.8,
      "scope": "hole",
      "type": "lead_change",
      "round": 1,
      "headline": "Gregg WILLIAMS takes the Trophy (Stableford) lead (R1 H4)",
      "players": [
        "Gregg WILLIAMS"
      ],
      "scores": {
        "importance": 5.8,
        "rarity": 3.0,
        "entertainment": 4.0
      },
      "holes": [
        {
          "hole": 4,
          "par": 4,
          "sc": 6,
          "grossvp": 2,
          "stableford": 2,
          "result": "double bogey"
        }
      ],
      "context": {
        "competition": "Trophy (Stableford)",
        "rank_before": 3,
        "rank_after": 1
      }
    },
    {
      "id": "b55",
      "total": 12.8,
      "scope": "hole",
      "type": "big_blowup",
      "round": 1,
      "headline": "Gregg WILLIAMS runs up a 9 (quadruple bogey) at the 18th (R1)",
      "players": [
        "Gregg WILLIAMS"
      ],
      "scores": {
        "importance": 2.6,
        "rarity": 4,
        "entertainment": 6.2
      },
      "holes": [
        {
          "hole": 18,
          "par": 5,
          "sc": 9,
          "grossvp": 4,
          "stableford": 0,
          "result": "quadruple bogey"
        }
      ],
      "context": {}
    },
    {
      "id": "b56",
      "total": 12.8,
      "scope": "hole",
      "type": "big_blowup",
      "round": 3,
      "headline": "Gregg WILLIAMS runs up a 7 (quadruple bogey) at the 15th (R3)",
      "players": [
        "Gregg WILLIAMS"
      ],
      "scores": {
        "importance": 2.6,
        "rarity": 4,
        "entertainment": 6.2
      },
      "holes": [
        {
          "hole": 15,
          "par": 3,
          "sc": 7,
          "grossvp": 4,
          "stableford": 0,
          "result": "quadruple bogey"
        }
      ],
      "context": {}
    },
    {
      "id": "b57",
      "total": 12.78,
      "scope": "stretch",
      "type": "cold_stretch",
      "round": 1,
      "headline": "Stuart NEUMANN bleeds 16 shots, holes 14-18 (R1)",
      "players": [
        "Stuart NEUMANN"
      ],
      "scores": {
        "importance": 5.0426666666666655,
        "rarity": 3.1999999999999997,
        "entertainment": 4.533333333333333
      },
      "holes": [
        {
          "hole": 14,
          "par": 4,
          "sc": 7,
          "grossvp": 3,
          "stableford": 1,
          "result": "triple bogey"
        },
        {
          "hole": 15,
          "par": 3,
          "sc": 8,
          "grossvp": 5,
          "stableford": 0,
          "result": "quintuple bogey"
        },
        {
          "hole": 16,
          "par": 4,
          "sc": 7,
          "grossvp": 3,
          "stableford": 0,
          "result": "triple bogey"
        },
        {
          "hole": 17,
          "par": 4,
          "sc": 6,
          "grossvp": 2,
          "stableford": 1,
          "result": "double bogey"
        },
        {
          "hole": 18,
          "par": 5,
          "sc": 8,
          "grossvp": 3,
          "stableford": 1,
          "result": "triple bogey"
        }
      ],
      "context": {
        "shots_dropped": 16,
        "length": 5
      }
    },
    {
      "id": "b58",
      "total": 12.55,
      "scope": "round",
      "type": "round_player",
      "round": 3,
      "headline": "Jon BAKER far stronger on the front nine in R3 (10-pt split)",
      "players": [
        "Jon BAKER"
      ],
      "scores": {
        "importance": 4.55,
        "rarity": 3.0,
        "entertainment": 5.0
      },
      "holes": [],
      "context": {
        "round_stableford": 34,
        "round_gross_vp": 22
      }
    },
    {
      "id": "b59",
      "total": 12.1,
      "scope": "round",
      "type": "round_player",
      "round": 1,
      "headline": "Stuart NEUMANN far stronger on the front nine in R1 (11-pt split)",
      "players": [
        "Stuart NEUMANN"
      ],
      "scores": {
        "importance": 4.1,
        "rarity": 3.0,
        "entertainment": 5.0
      },
      "holes": [],
      "context": {
        "round_stableford": 23,
        "round_gross_vp": 42
      }
    },
    {
      "id": "b60",
      "total": 12.0,
      "scope": "stretch",
      "type": "recovery",
      "round": 2,
      "headline": "David MULLIN stops the bleeding with a birdie at the 10th (R2)",
      "players": [
        "David MULLIN"
      ],
      "scores": {
        "importance": 5.0,
        "rarity": 3.0,
        "entertainment": 4.0
      },
      "holes": [
        {
          "hole": 6,
          "par": 4,
          "sc": 5,
          "grossvp": 1,
          "stableford": 2,
          "result": "bogey"
        },
        {
          "hole": 7,
          "par": 5,
          "sc": 6,
          "grossvp": 1,
          "stableford": 2,
          "result": "bogey"
        },
        {
          "hole": 8,
          "par": 3,
          "sc": 4,
          "grossvp": 1,
          "stableford": 2,
          "result": "bogey"
        },
        {
          "hole": 9,
          "par": 4,
          "sc": 5,
          "grossvp": 1,
          "stableford": 2,
          "result": "bogey"
        },
        {
          "hole": 10,
          "par": 5,
          "sc": 4,
          "grossvp": -1,
          "stableford": 4,
          "result": "birdie"
        }
      ],
      "context": {
        "streak_broken": "bogey_or_worse"
      }
    },
    {
      "id": "b61",
      "total": 12.0,
      "scope": "stretch",
      "type": "recovery",
      "round": 2,
      "headline": "John PATTERSON stops the bleeding with a birdie at the 7th (R2)",
      "players": [
        "John PATTERSON"
      ],
      "scores": {
        "importance": 5.0,
        "rarity": 3.0,
        "entertainment": 4.0
      },
      "holes": [
        {
          "hole": 1,
          "par": 4,
          "sc": 5,
          "grossvp": 1,
          "stableford": 3,
          "result": "bogey"
        },
        {
          "hole": 2,
          "par": 5,
          "sc": 6,
          "grossvp": 1,
          "stableford": 2,
          "result": "bogey"
        },
        {
          "hole": 3,
          "par": 3,
          "sc": 4,
          "grossvp": 1,
          "stableford": 2,
          "result": "bogey"
        },
        {
          "hole": 4,
          "par": 4,
          "sc": 6,
          "grossvp": 2,
          "stableford": 1,
          "result": "double bogey"
        },
        {
          "hole": 5,
          "par": 4,
          "sc": 7,
          "grossvp": 3,
          "stableford": 1,
          "result": "triple bogey"
        },
        {
          "hole": 6,
          "par": 4,
          "sc": 7,
          "grossvp": 3,
          "stableford": 1,
          "result": "triple bogey"
        },
        {
          "hole": 7,
          "par": 5,
          "sc": 4,
          "grossvp": -1,
          "stableford": 4,
          "result": "birdie"
        }
      ],
      "context": {
        "streak_broken": "bogey_or_worse"
      }
    },
    {
      "id": "b62",
      "total": 11.85,
      "scope": "stretch",
      "type": "recovery",
      "round": 2,
      "headline": "Jon BAKER stops the bleeding with a birdie at the 17th (R2)",
      "players": [
        "Jon BAKER"
      ],
      "scores": {
        "importance": 4.55,
        "rarity": 3.0,
        "entertainment": 4.3
      },
      "holes": [
        {
          "hole": 14,
          "par": 3,
          "sc": 7,
          "grossvp": 4,
          "stableford": 0,
          "result": "quadruple bogey"
        },
        {
          "hole": 15,
          "par": 4,
          "sc": 5,
          "grossvp": 1,
          "stableford": 2,
          "result": "bogey"
        },
        {
          "hole": 16,
          "par": 4,
          "sc": 5,
          "grossvp": 1,
          "stableford": 2,
          "result": "bogey"
        },
        {
          "hole": 17,
          "par": 5,
          "sc": 4,
          "grossvp": -1,
          "stableford": 5,
          "result": "birdie"
        }
      ],
      "context": {
        "streak_broken": "bogey_or_worse"
      }
    },
    {
      "id": "b63",
      "total": 11.85,
      "scope": "stretch",
      "type": "recovery",
      "round": 4,
      "headline": "Alex BAKER stops the bleeding with a birdie at the 8th (R4)",
      "players": [
        "Alex BAKER"
      ],
      "scores": {
        "importance": 4.55,
        "rarity": 3.0,
        "entertainment": 4.3
      },
      "holes": [
        {
          "hole": 4,
          "par": 4,
          "sc": 7,
          "grossvp": 3,
          "stableford": 1,
          "result": "triple bogey"
        },
        {
          "hole": 5,
          "par": 4,
          "sc": 5,
          "grossvp": 1,
          "stableford": 3,
          "result": "bogey"
        },
        {
          "hole": 6,
          "par": 4,
          "sc": 8,
          "grossvp": 4,
          "stableford": 0,
          "result": "quadruple bogey"
        },
        {
          "hole": 7,
          "par": 5,
          "sc": 6,
          "grossvp": 1,
          "stableford": 3,
          "result": "bogey"
        },
        {
          "hole": 8,
          "par": 3,
          "sc": 2,
          "grossvp": -1,
          "stableford": 5,
          "result": "birdie"
        }
      ],
      "context": {
        "streak_broken": "bogey_or_worse"
      }
    },
    {
      "id": "b64",
      "total": 11.73,
      "scope": "stretch",
      "type": "hot_stretch",
      "round": 3,
      "headline": "Stuart NEUMANN piles up 12 points, holes 10-13 (R3)",
      "players": [
        "Stuart NEUMANN"
      ],
      "scores": {
        "importance": 4.9104,
        "rarity": 2.88,
        "entertainment": 3.936
      },
      "holes": [
        {
          "hole": 10,
          "par": 4,
          "sc": 5,
          "grossvp": 1,
          "stableford": 3,
          "result": "bogey"
        },
        {
          "hole": 11,
          "par": 5,
          "sc": 5,
          "grossvp": 0,
          "stableford": 3,
          "result": "par"
        },
        {
          "hole": 12,
          "par": 4,
          "sc": 5,
          "grossvp": 1,
          "stableford": 3,
          "result": "bogey"
        },
        {
          "hole": 13,
          "par": 3,
          "sc": 3,
          "grossvp": 0,
          "stableford": 3,
          "result": "par"
        }
      ],
      "context": {
        "points_gained": 12,
        "length": 4
      }
    },
    {
      "id": "b65",
      "total": 11.63,
      "scope": "stretch",
      "type": "hot_stretch",
      "round": 4,
      "headline": "David MULLIN piles up 9 points, holes 7-9 (R4)",
      "players": [
        "David MULLIN"
      ],
      "scores": {
        "importance": 6.952,
        "rarity": 2.16,
        "entertainment": 2.5200000000000005
      },
      "holes": [
        {
          "hole": 7,
          "par": 5,
          "sc": 5,
          "grossvp": 0,
          "stableford": 3,
          "result": "par"
        },
        {
          "hole": 8,
          "par": 3,
          "sc": 3,
          "grossvp": 0,
          "stableford": 3,
          "result": "par"
        },
        {
          "hole": 9,
          "par": 4,
          "sc": 4,
          "grossvp": 0,
          "stableford": 3,
          "result": "par"
        }
      ],
      "context": {
        "points_gained": 9,
        "length": 3
      }
    },
    {
      "id": "b66",
      "total": 11.5,
      "scope": "stretch",
      "type": "collapse_after_steady",
      "round": 1,
      "headline": "David MULLIN's steady run ends with a double bogey at the 16th (R1)",
      "players": [
        "David MULLIN"
      ],
      "scores": {
        "importance": 5.0,
        "rarity": 2.5,
        "entertainment": 4.0
      },
      "holes": [
        {
          "hole": 13,
          "par": 3,
          "sc": 3,
          "grossvp": 0,
          "stableford": 2,
          "result": "par"
        },
        {
          "hole": 14,
          "par": 4,
          "sc": 4,
          "grossvp": 0,
          "stableford": 3,
          "result": "par"
        },
        {
          "hole": 15,
          "par": 3,
          "sc": 3,
          "grossvp": 0,
          "stableford": 3,
          "result": "par"
        },
        {
          "hole": 16,
          "par": 4,
          "sc": 6,
          "grossvp": 2,
          "stableford": 1,
          "result": "double bogey"
        }
      ],
      "context": {
        "streak_broken": "par_or_better"
      }
    },
    {
      "id": "b67",
      "total": 11.5,
      "scope": "stretch",
      "type": "collapse_after_steady",
      "round": 4,
      "headline": "David MULLIN's steady run ends with a double bogey at the 5th (R4)",
      "players": [
        "David MULLIN"
      ],
      "scores": {
        "importance": 5.0,
        "rarity": 2.5,
        "entertainment": 4.0
      },
      "holes": [
        {
          "hole": 2,
          "par": 5,
          "sc": 5,
          "grossvp": 0,
          "stableford": 3,
          "result": "par"
        },
        {
          "hole": 3,
          "par": 3,
          "sc": 3,
          "grossvp": 0,
          "stableford": 2,
          "result": "par"
        },
        {
          "hole": 4,
          "par": 4,
          "sc": 4,
          "grossvp": 0,
          "stableford": 3,
          "result": "par"
        },
        {
          "hole": 5,
          "par": 4,
          "sc": 6,
          "grossvp": 2,
          "stableford": 1,
          "result": "double bogey"
        }
      ],
      "context": {
        "streak_broken": "par_or_better"
      }
    },
    {
      "id": "b68",
      "total": 11.35,
      "scope": "stretch",
      "type": "collapse_after_steady",
      "round": 2,
      "headline": "Jon BAKER's steady run ends with a quadruple bogey at the 14th (R2)",
      "players": [
        "Jon BAKER"
      ],
      "scores": {
        "importance": 4.55,
        "rarity": 2.5,
        "entertainment": 4.3
      },
      "holes": [
        {
          "hole": 11,
          "par": 3,
          "sc": 3,
          "grossvp": 0,
          "stableford": 3,
          "result": "par"
        },
        {
          "hole": 12,
          "par": 5,
          "sc": 5,
          "grossvp": 0,
          "stableford": 3,
          "result": "par"
        },
        {
          "hole": 13,
          "par": 4,
          "sc": 4,
          "grossvp": 0,
          "stableford": 3,
          "result": "par"
        },
        {
          "hole": 14,
          "par": 3,
          "sc": 7,
          "grossvp": 4,
          "stableford": 0,
          "result": "quadruple bogey"
        }
      ],
      "context": {
        "streak_broken": "par_or_better"
      }
    },
    {
      "id": "b69",
      "total": 11.34,
      "scope": "stretch",
      "type": "cold_stretch",
      "round": 4,
      "headline": "Alex BAKER bleeds 11 shots, holes 14-17 (R4)",
      "players": [
        "Alex BAKER"
      ],
      "scores": {
        "importance": 6.301333333333332,
        "rarity": 2.1999999999999997,
        "entertainment": 2.8416666666666663
      },
      "holes": [
        {
          "hole": 14,
          "par": 3,
          "sc": 5,
          "grossvp": 2,
          "stableford": 2,
          "result": "double bogey"
        },
        {
          "hole": 15,
          "par": 4,
          "sc": 8,
          "grossvp": 4,
          "stableford": 0,
          "result": "quadruple bogey"
        },
        {
          "hole": 16,
          "par": 4,
          "sc": 7,
          "grossvp": 3,
          "stableford": 1,
          "result": "triple bogey"
        },
        {
          "hole": 17,
          "par": 5,
          "sc": 7,
          "grossvp": 2,
          "stableford": 2,
          "result": "double bogey"
        }
      ],
      "context": {
        "shots_dropped": 11,
        "length": 4
      }
    },
    {
      "id": "b70",
      "total": 10.84,
      "scope": "stretch",
      "type": "hot_stretch",
      "round": 2,
      "headline": "Alex BAKER piles up 10 points, holes 7-9 (R2)",
      "players": [
        "Alex BAKER"
      ],
      "scores": {
        "importance": 5.396,
        "rarity": 2.4,
        "entertainment": 3.04
      },
      "holes": [
        {
          "hole": 7,
          "par": 5,
          "sc": 6,
          "grossvp": 1,
          "stableford": 3,
          "result": "bogey"
        },
        {
          "hole": 8,
          "par": 3,
          "sc": 4,
          "grossvp": 1,
          "stableford": 3,
          "result": "bogey"
        },
        {
          "hole": 9,
          "par": 4,
          "sc": 4,
          "grossvp": 0,
          "stableford": 4,
          "result": "par"
        }
      ],
      "context": {
        "points_gained": 10,
        "length": 3
      }
    },
    {
      "id": "b71",
      "total": 10.18,
      "scope": "stretch",
      "type": "hot_stretch",
      "round": 2,
      "headline": "Jon BAKER piles up 9 points, holes 11-13 (R2)",
      "players": [
        "Jon BAKER"
      ],
      "scores": {
        "importance": 5.2824,
        "rarity": 2.16,
        "entertainment": 2.736
      },
      "holes": [
        {
          "hole": 11,
          "par": 3,
          "sc": 3,
          "grossvp": 0,
          "stableford": 3,
          "result": "par"
        },
        {
          "hole": 12,
          "par": 5,
          "sc": 5,
          "grossvp": 0,
          "stableford": 3,
          "result": "par"
        },
        {
          "hole": 13,
          "par": 4,
          "sc": 4,
          "grossvp": 0,
          "stableford": 3,
          "result": "par"
        }
      ],
      "context": {
        "points_gained": 9,
        "length": 3
      }
    },
    {
      "id": "b72",
      "total": 10.0,
      "scope": "hole",
      "type": "spoon_change",
      "round": 1,
      "headline": "Alex BAKER drops to the bottom of the Wooden Spoon race (R1 H2)",
      "players": [
        "Alex BAKER"
      ],
      "scores": {
        "importance": 3.0,
        "rarity": 2.0,
        "entertainment": 5.0
      },
      "holes": [
        {
          "hole": 2,
          "par": 5,
          "sc": 9,
          "grossvp": 4,
          "stableford": 0,
          "result": "quadruple bogey"
        }
      ],
      "context": {
        "competition": "Wooden Spoon",
        "rank_before": 5,
        "rank_after": 6
      }
    },
    {
      "id": "b73",
      "total": 10.0,
      "scope": "hole",
      "type": "spoon_change",
      "round": 1,
      "headline": "Stuart NEUMANN drops to the bottom of the Wooden Spoon race (R1 H11)",
      "players": [
        "Stuart NEUMANN"
      ],
      "scores": {
        "importance": 3.0,
        "rarity": 2.0,
        "entertainment": 5.0
      },
      "holes": [
        {
          "hole": 11,
          "par": 5,
          "sc": 8,
          "grossvp": 3,
          "stableford": 0,
          "result": "triple bogey"
        }
      ],
      "context": {
        "competition": "Wooden Spoon",
        "rank_before": 4,
        "rank_after": 6
      }
    },
    {
      "id": "b74",
      "total": 10.0,
      "scope": "hole",
      "type": "spoon_change",
      "round": 1,
      "headline": "Stuart NEUMANN drops to the bottom of the Wooden Spoon race (R1 H15)",
      "players": [
        "Stuart NEUMANN"
      ],
      "scores": {
        "importance": 3.0,
        "rarity": 2.0,
        "entertainment": 5.0
      },
      "holes": [
        {
          "hole": 15,
          "par": 3,
          "sc": 8,
          "grossvp": 5,
          "stableford": 0,
          "result": "quintuple bogey"
        }
      ],
      "context": {
        "competition": "Wooden Spoon",
        "rank_before": 5,
        "rank_after": 6
      }
    },
    {
      "id": "b75",
      "total": 9.81,
      "scope": "stretch",
      "type": "cold_stretch",
      "round": 4,
      "headline": "Stuart NEUMANN bleeds 9 shots, holes 2-5 (R4)",
      "players": [
        "Stuart NEUMANN"
      ],
      "scores": {
        "importance": 5.4639999999999995,
        "rarity": 1.7999999999999998,
        "entertainment": 2.55
      },
      "holes": [
        {
          "hole": 2,
          "par": 5,
          "sc": 7,
          "grossvp": 2,
          "stableford": 1,
          "result": "double bogey"
        },
        {
          "hole": 3,
          "par": 3,
          "sc": 6,
          "grossvp": 3,
          "stableford": 0,
          "result": "triple bogey"
        },
        {
          "hole": 4,
          "par": 4,
          "sc": 6,
          "grossvp": 2,
          "stableford": 1,
          "result": "double bogey"
        },
        {
          "hole": 5,
          "par": 4,
          "sc": 6,
          "grossvp": 2,
          "stableford": 2,
          "result": "double bogey"
        }
      ],
      "context": {
        "shots_dropped": 9,
        "length": 4
      }
    },
    {
      "id": "b76",
      "total": 9.8,
      "scope": "round",
      "type": "round_leadership",
      "round": 4,
      "headline": "After R4: John PATTERSON leads the Trophy (gap 0 on Stableford); David MULLIN leads the Jacket",
      "players": [
        "John PATTERSON",
        "David MULLIN"
      ],
      "scores": {
        "importance": 6.8,
        "rarity": 1.0,
        "entertainment": 2.0
      },
      "holes": [],
      "context": {
        "trophy_leader": "John PATTERSON",
        "jacket_leader": "David MULLIN"
      }
    },
    {
      "id": "b77",
      "total": 9.72,
      "scope": "stretch",
      "type": "hot_stretch",
      "round": 3,
      "headline": "Stuart NEUMANN piles up 9 points, holes 6-8 (R3)",
      "players": [
        "Stuart NEUMANN"
      ],
      "scores": {
        "importance": 4.612799999999999,
        "rarity": 2.16,
        "entertainment": 2.9520000000000004
      },
      "holes": [
        {
          "hole": 6,
          "par": 3,
          "sc": 3,
          "grossvp": 0,
          "stableford": 3,
          "result": "par"
        },
        {
          "hole": 7,
          "par": 5,
          "sc": 6,
          "grossvp": 1,
          "stableford": 3,
          "result": "bogey"
        },
        {
          "hole": 8,
          "par": 3,
          "sc": 3,
          "grossvp": 0,
          "stableford": 3,
          "result": "par"
        }
      ],
      "context": {
        "points_gained": 9,
        "length": 3
      }
    },
    {
      "id": "b78",
      "total": 9.38,
      "scope": "stretch",
      "type": "cold_stretch",
      "round": 1,
      "headline": "Stuart NEUMANN bleeds 10 shots, holes 10-12 (R1)",
      "players": [
        "Stuart NEUMANN"
      ],
      "scores": {
        "importance": 4.546666666666666,
        "rarity": 2.0,
        "entertainment": 2.8333333333333335
      },
      "holes": [
        {
          "hole": 10,
          "par": 4,
          "sc": 7,
          "grossvp": 3,
          "stableford": 1,
          "result": "triple bogey"
        },
        {
          "hole": 11,
          "par": 5,
          "sc": 8,
          "grossvp": 3,
          "stableford": 0,
          "result": "triple bogey"
        },
        {
          "hole": 12,
          "par": 4,
          "sc": 8,
          "grossvp": 4,
          "stableford": 0,
          "result": "quadruple bogey"
        }
      ],
      "context": {
        "shots_dropped": 10,
        "length": 3
      }
    },
    {
      "id": "b79",
      "total": 9.25,
      "scope": "stretch",
      "type": "cold_stretch",
      "round": 4,
      "headline": "Stuart NEUMANN bleeds 8 shots, holes 16-18 (R4)",
      "players": [
        "Stuart NEUMANN"
      ],
      "scores": {
        "importance": 5.381333333333333,
        "rarity": 1.5999999999999999,
        "entertainment": 2.2666666666666666
      },
      "holes": [
        {
          "hole": 16,
          "par": 4,
          "sc": 8,
          "grossvp": 4,
          "stableford": 0,
          "result": "quadruple bogey"
        },
        {
          "hole": 17,
          "par": 5,
          "sc": 7,
          "grossvp": 2,
          "stableford": 2,
          "result": "double bogey"
        },
        {
          "hole": 18,
          "par": 4,
          "sc": 6,
          "grossvp": 2,
          "stableford": 1,
          "result": "double bogey"
        }
      ],
      "context": {
        "shots_dropped": 8,
        "length": 3
      }
    },
    {
      "id": "b80",
      "total": 9.12,
      "scope": "stretch",
      "type": "cold_stretch",
      "round": 2,
      "headline": "John PATTERSON bleeds 8 shots, holes 4-6 (R2)",
      "players": [
        "John PATTERSON"
      ],
      "scores": {
        "importance": 5.653333333333333,
        "rarity": 1.5999999999999999,
        "entertainment": 1.8666666666666665
      },
      "holes": [
        {
          "hole": 4,
          "par": 4,
          "sc": 6,
          "grossvp": 2,
          "stableford": 1,
          "result": "double bogey"
        },
        {
          "hole": 5,
          "par": 4,
          "sc": 7,
          "grossvp": 3,
          "stableford": 1,
          "result": "triple bogey"
        },
        {
          "hole": 6,
          "par": 4,
          "sc": 7,
          "grossvp": 3,
          "stableford": 1,
          "result": "triple bogey"
        }
      ],
      "context": {
        "shots_dropped": 8,
        "length": 3
      }
    },
    {
      "id": "b81",
      "total": 9.12,
      "scope": "stretch",
      "type": "cold_stretch",
      "round": 3,
      "headline": "John PATTERSON bleeds 8 shots, holes 2-4 (R3)",
      "players": [
        "John PATTERSON"
      ],
      "scores": {
        "importance": 5.653333333333333,
        "rarity": 1.5999999999999999,
        "entertainment": 1.8666666666666665
      },
      "holes": [
        {
          "hole": 2,
          "par": 5,
          "sc": 7,
          "grossvp": 2,
          "stableford": 2,
          "result": "double bogey"
        },
        {
          "hole": 3,
          "par": 3,
          "sc": 6,
          "grossvp": 3,
          "stableford": 0,
          "result": "triple bogey"
        },
        {
          "hole": 4,
          "par": 4,
          "sc": 7,
          "grossvp": 3,
          "stableford": 1,
          "result": "triple bogey"
        }
      ],
      "context": {
        "shots_dropped": 8,
        "length": 3
      }
    },
    {
      "id": "b82",
      "total": 8.81,
      "scope": "stretch",
      "type": "cold_stretch",
      "round": 2,
      "headline": "Stuart NEUMANN bleeds 9 shots, holes 11-13 (R2)",
      "players": [
        "Stuart NEUMANN"
      ],
      "scores": {
        "importance": 4.4639999999999995,
        "rarity": 1.7999999999999998,
        "entertainment": 2.55
      },
      "holes": [
        {
          "hole": 11,
          "par": 3,
          "sc": 6,
          "grossvp": 3,
          "stableford": 0,
          "result": "triple bogey"
        },
        {
          "hole": 12,
          "par": 5,
          "sc": 8,
          "grossvp": 3,
          "stableford": 0,
          "result": "triple bogey"
        },
        {
          "hole": 13,
          "par": 4,
          "sc": 7,
          "grossvp": 3,
          "stableford": 0,
          "result": "triple bogey"
        }
      ],
      "context": {
        "shots_dropped": 9,
        "length": 3
      }
    },
    {
      "id": "b83",
      "total": 8.68,
      "scope": "stretch",
      "type": "cold_stretch",
      "round": 2,
      "headline": "Alex BAKER bleeds 8 shots, holes 10-12 (R2)",
      "players": [
        "Alex BAKER"
      ],
      "scores": {
        "importance": 5.017333333333333,
        "rarity": 1.5999999999999999,
        "entertainment": 2.0666666666666664
      },
      "holes": [
        {
          "hole": 10,
          "par": 5,
          "sc": 9,
          "grossvp": 4,
          "stableford": 0,
          "result": "quadruple bogey"
        },
        {
          "hole": 11,
          "par": 3,
          "sc": 5,
          "grossvp": 2,
          "stableford": 2,
          "result": "double bogey"
        },
        {
          "hole": 12,
          "par": 5,
          "sc": 7,
          "grossvp": 2,
          "stableford": 2,
          "result": "double bogey"
        }
      ],
      "context": {
        "shots_dropped": 8,
        "length": 3
      }
    },
    {
      "id": "b84",
      "total": 8.68,
      "scope": "stretch",
      "type": "cold_stretch",
      "round": 3,
      "headline": "Alex BAKER bleeds 8 shots, holes 10-12 (R3)",
      "players": [
        "Alex BAKER"
      ],
      "scores": {
        "importance": 5.017333333333333,
        "rarity": 1.5999999999999999,
        "entertainment": 2.0666666666666664
      },
      "holes": [
        {
          "hole": 10,
          "par": 4,
          "sc": 7,
          "grossvp": 3,
          "stableford": 1,
          "result": "triple bogey"
        },
        {
          "hole": 11,
          "par": 5,
          "sc": 8,
          "grossvp": 3,
          "stableford": 1,
          "result": "triple bogey"
        },
        {
          "hole": 12,
          "par": 4,
          "sc": 6,
          "grossvp": 2,
          "stableford": 2,
          "result": "double bogey"
        }
      ],
      "context": {
        "shots_dropped": 8,
        "length": 3
      }
    },
    {
      "id": "b85",
      "total": 8.68,
      "scope": "stretch",
      "type": "cold_stretch",
      "round": 3,
      "headline": "Jon BAKER bleeds 8 shots, holes 10-12 (R3)",
      "players": [
        "Jon BAKER"
      ],
      "scores": {
        "importance": 5.017333333333333,
        "rarity": 1.5999999999999999,
        "entertainment": 2.0666666666666664
      },
      "holes": [
        {
          "hole": 10,
          "par": 4,
          "sc": 6,
          "grossvp": 2,
          "stableford": 1,
          "result": "double bogey"
        },
        {
          "hole": 11,
          "par": 5,
          "sc": 9,
          "grossvp": 4,
          "stableford": 0,
          "result": "quadruple bogey"
        },
        {
          "hole": 12,
          "par": 4,
          "sc": 6,
          "grossvp": 2,
          "stableford": 1,
          "result": "double bogey"
        }
      ],
      "context": {
        "shots_dropped": 8,
        "length": 3
      }
    },
    {
      "id": "b86",
      "total": 8.25,
      "scope": "stretch",
      "type": "cold_stretch",
      "round": 3,
      "headline": "Stuart NEUMANN bleeds 8 shots, holes 16-18 (R3)",
      "players": [
        "Stuart NEUMANN"
      ],
      "scores": {
        "importance": 4.381333333333333,
        "rarity": 1.5999999999999999,
        "entertainment": 2.2666666666666666
      },
      "holes": [
        {
          "hole": 16,
          "par": 4,
          "sc": 8,
          "grossvp": 4,
          "stableford": 0,
          "result": "quadruple bogey"
        },
        {
          "hole": 17,
          "par": 4,
          "sc": 6,
          "grossvp": 2,
          "stableford": 1,
          "result": "double bogey"
        },
        {
          "hole": 18,
          "par": 5,
          "sc": 7,
          "grossvp": 2,
          "stableford": 2,
          "result": "double bogey"
        }
      ],
      "context": {
        "shots_dropped": 8,
        "length": 3
      }
    },
    {
      "id": "b87",
      "total": 8.2,
      "scope": "round",
      "type": "round_leadership",
      "round": 3,
      "headline": "After R3: John PATTERSON leads the Trophy (gap 0 on Stableford); David MULLIN leads the Jacket",
      "players": [
        "John PATTERSON",
        "David MULLIN"
      ],
      "scores": {
        "importance": 5.2,
        "rarity": 1.0,
        "entertainment": 2.0
      },
      "holes": [],
      "context": {
        "trophy_leader": "John PATTERSON",
        "jacket_leader": "David MULLIN"
      }
    },
    {
      "id": "b88",
      "total": 8.13,
      "scope": "stretch",
      "type": "cold_stretch",
      "round": 2,
      "headline": "Jon BAKER bleeds 7 shots, holes 5-7 (R2)",
      "players": [
        "Jon BAKER"
      ],
      "scores": {
        "importance": 4.922666666666666,
        "rarity": 1.4000000000000001,
        "entertainment": 1.8083333333333333
      },
      "holes": [
        {
          "hole": 5,
          "par": 4,
          "sc": 6,
          "grossvp": 2,
          "stableford": 1,
          "result": "double bogey"
        },
        {
          "hole": 6,
          "par": 4,
          "sc": 6,
          "grossvp": 2,
          "stableford": 1,
          "result": "double bogey"
        },
        {
          "hole": 7,
          "par": 5,
          "sc": 8,
          "grossvp": 3,
          "stableford": 0,
          "result": "triple bogey"
        }
      ],
      "context": {
        "shots_dropped": 7,
        "length": 3
      }
    },
    {
      "id": "b89",
      "total": 7.6,
      "scope": "round",
      "type": "round_leadership",
      "round": 2,
      "headline": "After R2: John PATTERSON leads the Trophy (gap 0 on Stableford); David MULLIN leads the Jacket",
      "players": [
        "John PATTERSON",
        "David MULLIN"
      ],
      "scores": {
        "importance": 4.6,
        "rarity": 1.0,
        "entertainment": 2.0
      },
      "holes": [],
      "context": {
        "trophy_leader": "John PATTERSON",
        "jacket_leader": "David MULLIN"
      }
    },
    {
      "id": "b90",
      "total": 7.0,
      "scope": "round",
      "type": "round_leadership",
      "round": 1,
      "headline": "After R1: Jon BAKER leads the Trophy (gap 0 on Stableford); David MULLIN leads the Jacket",
      "players": [
        "Jon BAKER",
        "David MULLIN"
      ],
      "scores": {
        "importance": 4.0,
        "rarity": 1.0,
        "entertainment": 2.0
      },
      "holes": [],
      "context": {
        "trophy_leader": "Jon BAKER",
        "jacket_leader": "David MULLIN"
      }
    }
  ]
}
