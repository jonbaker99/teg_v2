# Live TEGBot and finalise lock: plan

Temporary working doc. Delete or fold into `STATUS.md` once the work ships. Fixes dry run 4 snags 27–29 (`TEST_TOURNAMENT_ISSUES.md`).

## The three fixes, in shipping order

1. **The entry page locks when the admin taps Finalise** (snag 29). Small, webapp only. Ships first and alone.
2. **TEGBot reads the live win chances** (snag 27). Same numbers as the Live tab on `/simulation`.
3. **TEGBot answers "what does X need to win"** (snag 28). Targets in gross first, then points.

4. **Mid-round chances from live scores.** Chances, standings and targets include holes entered so far.

**Deadline:** code freeze is 8 October; TEG 19 is 10–13 October. Fix 1 must make the freeze. Fixes 2 and 3 should. Anything that slips waits until after TEG 19.

## Branch and delivery

- Restart `claude/gifted-clarke-72n0ye` from `main`. Close the dry run 4 PR (jonbaker99/teg_v2#177) unmerged first.
- Only docs carry over from dry run 4: this plan and the issue log entries. `DRY_RUN_4.md` is dropped.
- One PR, fix 1 committed first (see Fix 4's note).
- Each PR gets a Railway preview and a short dry run before merge.

## Who does what

- **Lead (Opus):** this plan, the interfaces below, review of every worker diff, and Git.
- **Workers (Sonnet, via the Agent tool with `model: sonnet`):** one per workstream, with the file ownership listed. They don't commit.
- **Review (Opus, `code-reviewer` agent):** a fresh-context review of each PR's combined diff before push.

## Fix 1: lock the entry page as soon as finalise starts

### Why the lock comes late

The entry page only locks when the poll returns `status: "finalized"`. The registry flips to finalized in the last step of `finalize_live_round` (`teg_analysis/analysis/live_round.py`), after the ~40 s cache rebuild and the GitHub commit. Meanwhile the server already rejects score writes for that round with a 409. The page drops a 409 silently (`flushPending` treats every 4xx as done), so a score typed in that window is lost without warning.

### Change

- **Server: report a "finalizing" status.** In `api_poll_scores` (`webapp/routes/live_round.py`), when `finalize_jobs.is_active(finalize_jobs.read_status(token))`, return `status: "finalizing"`. Do the same for the initial page render (`live_round_page`) and the live leaderboard API. `claim()` writes the status file the moment the admin taps Finalise, so this is near-instant. No change to `teg_analysis/`.
- **If finalise fails**, the job status becomes `error` and the poll returns `active` again. The page unlocks and shows "Finalise didn't complete, scores are open again".
- **Entry page (`live_round_entry.html`): a clear locked state.**
  - On `finalizing` or `finalized`: add a `round-locked` class to the page. Grey the grid and totals (reduced opacity, `pointer-events: none`), hide the keypad, disable voice.
  - Show a centred card over the greyed page: "Round complete". Subline: "Scores locked. Publishing results…" while finalizing, then "Results are in" with a **Leaderboard** button.
  - Keep polling while `finalizing` (today `applyStatus` stops polling for any non-active status). Stop once `finalized`, `cancelled` or `deleted`.
  - If this phone still has unsaved scores when the lock arrives, say so on the card: "2 scores from this phone weren't saved. Tell the admin." List hole and player.
  - Players and admins see the same lock. The site strip's Review & finalise link stays for admins.
- **Live leaderboard page:** show "Finalising…" in its status banner for `finalizing`.

### Files (worker A)

`webapp/routes/live_round.py`, `webapp/templates/live_round_entry.html`, `webapp/templates/live_round_leaderboard.html`, `tests/test_live_round_routes.py`.

### Checks

- Route test: poll returns `finalizing` while a claimed job is active, `finalized` after, `active` after an error.
- `python -m pytest tests/test_live_round_routes.py tests/test_finalize_jobs.py tests/test_live_round.py`.
- Preview: two phones on the entry page; admin taps Finalise; both lock within one poll (3.5 s); then "Results are in".

## Fix 2: TEGBot reads the live win chances

### What's wrong today

- During a TEG, `get_predictions` simulates the in-progress TEG **from scratch**. It ignores the rounds already played, so mid-tournament it gives pre-tournament odds. That's a wrong answer, not just a gap.
- The Live tab's numbers are built inside a webapp route (`_live_context` in `webapp/routes/simulation.py`), so TEGBot can't reach them.

### Change

- **One source for live chances.** Add `live_prediction(seed=1) -> dict` in `webapp/routes/simulation.py`, next to `default_prediction`. It reuses `_live_state` and `_live_point`, so TEGBot and the Live tab give identical numbers and share the cache. `_live_context` calls it for its table rows. Returns plain data:
  - `teg_num`, `rounds_done`, `rounds_total`, `simulations`.
  - Per player: name, position now (net and gross, ties shared), banked Stableford (or net vs par) and gross vs par, Trophy % and Jacket % now, change since the last round in percentage points, expected gross vs par per remaining round (`mean`).
  - Add **Wooden Spoon %**. `win_probs_at` already has the net totals; add a `spoon` measure there (lowest net), so the Live tab can show it later.
  - Raises `ValueError` when no TEG is in progress.
- **TEGBot tool `get_live_win_chances`** (`teg_analysis/chatbot/tools.py`). `ChatData` gains a `live_predictions` callable, wired in `webapp/routes/tegbot.py`. The tool adds a definition and notes like `get_predictions` does, and links `/simulation?tab=live`.
- **`get_predictions` during a TEG:** refuse with "TEG N is in progress; use get_live_win_chances". This removes the wrong answer.
- **Prompt (`teg_analysis/chatbot/prompt.py`):** when a TEG is in progress (the prompt already lists TEG status), "who will win / chances / odds / favourite" goes to `get_live_win_chances`. Pre-tournament still uses `get_predictions`.
- **Deep dive:** add a `live` command to `teg-simulation`'s `scripts/sim.py` that prints the same table. Update its `SKILL.md`. Why-questions mid-TEG ("why did X's chance drop?") can then quote it with the round scores.

### Files (worker B)

`webapp/routes/simulation.py`, `teg_analysis/analysis/win_probability.py` (spoon only), `teg_analysis/chatbot/tools.py`, `teg_analysis/chatbot/prompt.py`, `webapp/routes/tegbot.py`, `teg_analysis/chatbot/toolkit/skills/teg-simulation/`, `tests/test_tegbot.py`, `tests/test_tegbot_toolkit.py`, `tests/test_simulation_routes.py`, `tests/test_win_probability.py`.

## Fix 3: "what does X need to win"

### The question it answers

"If everyone keeps scoring the way they have so far, what does Player B need over the remaining rounds to win the Trophy or the Jacket?" Answer gross first: "B needs about 168 gross over the last two rounds, about 84 a round. That's at least 71 Stableford points."

### Method

New UI-agnostic module `teg_analysis/analysis/live_scenarios.py`. One public function:

`what_it_takes(state, player, competition, rivals="same_pace") -> dict`

- **Rival projection.** For each rival, project a final total.
  - `same_pace` (default, matches Jon's framing): banked total plus their per-hole average so far, times the holes left.
  - `expected`: banked total plus the model's expected remaining score (the `mean` column from `win_probs_at`).
- **Target.** Trophy: beat the best rival projection by one point to win outright; equal it to tie. Jacket: one stroke fewer than the best rival's projected gross.
- **Stableford to gross.** On the remaining scorecards with the player's handicap: gross ≈ par + strokes received + 2 × holes − points. Exact unless a hole scores 0 points, so answers say "about". A round with no scorecard uses par 72 and strokes = handicap.
- **Reality check.** Compare the needed score per round with the player's own rounds: their best ever, and how often they've done it in their last 3 TEGs. "B has shot 84 or better in 3 of their last 12 rounds."
- **Already out of reach.** If even the player's best-ever rounds can't reach the target, say so.
- **Optional, if time allows:** the model's view. Among simulations where B wins, B's median remaining score. Needs `win_probs_at` to return totals on request.

Returns per-round and total targets in gross and points, the rival projections used, the leader's projection, and the reality-check facts. No prose.

### TEGBot wiring

- Tool `get_what_it_takes(player, competition, rivals)`, in `tools.py`.
- Prompt rule: lead with gross ("about 84 a round"), then points. Name the rival assumption in one line. Never compute the target by hand.
- `sim.py need` command for Deep dive, for variants like "what if A only plays to handicap".

### Files

Worker C builds the module and its tests (`teg_analysis/analysis/live_scenarios.py`, `tests/test_live_scenarios.py`) in parallel with B. Worker B wires the tool and prompt once both land. The lead fixes the interface first: `TegState` in, plain dict out.

### Checks

- Unit tests on a small fixture TEG: same-pace projection, ties, the gross conversion (including a 0-point hole), a round with no scorecard, and an out-of-reach player.
- `python -m pytest tests/test_live_scenarios.py tests/test_tegbot.py tests/test_tegbot_toolkit.py tests/test_win_probability.py tests/test_simulation_routes.py`.
- `python scripts/check_python_compat.py` before push.

## Dry run 5 on the PR preview

Set up a dummy TEG on the preview (not TEG 50: test TEG 50 is excluded from live chances). Then:

1. **Round 1, before any finalise.** Go live, enter a few holes on two phones (players on different holes). Check the Live tab shows "Now: round 1 in progress" with Thru, and ask TEGBot "who's winning?" and "who'll win the Trophy?". Both must reflect the holes entered.
2. **Finalise lock.** Keep a phone on the entry page, tap Finalise on another. The phone greys out within ~4 s with "Publishing results…", then "Results are in". Type a score just after the tap and check it's listed on the card.
3. **Round 2 mid-round.** Ask TEGBot: "What does X need to win the Trophy?", "...the Jacket?", "If Y keeps playing like this, what does X need to shoot?", "Who's most likely to get the Spoon?", "How much did X's chance change since round 1?". Targets must lead with gross ("about 84 a round"), then points.
4. **Final round, first group finished.** Ask about a finished player: TEGBot must call it a clubhouse position, not a win.
5. Numbers in TEGBot must match the Live tab.

## Docs, in the same PRs

- `STATUS.md`: an entry per PR.
- `webapp/README.md`: the `finalizing` status and locked entry page; TEGBot's live tool.
- `teg_analysis/README.md` and `CLAUDE.md` Architecture: add `live_scenarios` to the `analysis/` list.
- `TEST_TOURNAMENT_ISSUES.md`: mark 27–29 fixed.
- Delete this file once PR 2 merges.

## Fix 4: mid-round chances from live scores (decided 5 October: build now)

Today the chances, and so TEGBot, move only after a round is **finalised**. During a round, "who's winning right now" gets last night's answer.

- **Staged holes as banked holes.** `live_round.staged_holes(teg_num)` returns the active live round's entered holes, scored by the same transform as the live leaderboard.
- **Engine (lead-written).** `win_probability.snapshot(state, staged)` gives each player's banked totals and remaining holes; players can be on different holes. `win_probs_live(state, staged)` simulates the whole current round, then writes each player's actual holes over the simulated ones, so every player keeps their own position. Form uses each player's own holes played. `win_probs_at` is unchanged, so the backtest stands.
- **Webapp.** The Live tab's table shows the "now" chances while a round has scores, cached per staging sequence number. The hole-by-hole chart still steps through finalised rounds.
- **TEGBot and Fix 3** read the same snapshot, so chances, standings and targets all include the holes entered so far.

PR delivery: one PR on the restarted branch, fix 1 committed first so it can be split out if the rest slips the freeze.
