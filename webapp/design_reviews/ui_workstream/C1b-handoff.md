# C1b — Clean Editorial Precision: revision addendum

Captured 2026-09-20. Base: `809b97d` (C1's own commit — spec, mockups, screenshots, no app code). Worktree: `/Users/jon/projects/teg/worktrees/ui-c1b`; branch: `claude/ui-c1b`. Tree was clean at entry.

This is an **addendum to [`C1-handoff.md`](C1-handoff.md)**, not a rewrite. It records the owner's per-decision review of C1's proposal — 14 keep, 2 cut, 1 modify — and revises only what that review changed. Every keep item in `C1-handoff.md` (§2 type scale, §3 two heading levels, §4 spacing/rule/radius, §6 control patterns except where noted, §7 the two F6a follow-ups, §9–12) **stands as written and is not relitigated here.** C1b is specification and prototype only — **no application CSS or template was touched.** One Sonnet agent performed screenshot capture and the checks in §5; the lead (Opus for planning, executing as Sonnet — flagged, see the model note in the session) owned every design decision.

**Owner's final picks, after reviewing all four mocked comparisons — all four now signed off, nothing open:** leader row → **L2** (the lead recommended L1; owner preferred L2's tint look — the lead flagged and then fixed a real flaw L2 shipped with, see §2); focus ring → **F3** (owner's stated preference, though "don't really mind" between the three); segmented control → **approved as mocked**, no change; compact action → **owner couldn't judge it without seeing the "before"**, so it was rebuilt with real before/after pairs (§4) — the resulting change is modest (a rounded pill becomes a square action; an indicator recolours) and the owner signed off on the lead's `.action` recommendation on that basis.

**This closes the open-decision list.** C1b is ready to feed C3 directly — no further critique pass (C2) is required unless the owner wants one for a reason other than these four items, all of which are now resolved.

---

## 1. White content card — restored, not redesigned

**What was wrong:** both of C1's mockups set `--bg-panel` equal to `--bg-outer` (light mode), silently flattening production's white `.main-content` card onto the grey page background. This was never a decision in C1's written spec — §1's problem table doesn't mention the content card at all. It was a mockup construction defect, not a proposal the owner cut. **Fix: revert to production's white card, no design exploration needed.**

Production values, confirmed by reading `clean-page.css` and `clean-layered.css` directly:

| | Clean Page (`clean-page.css:22-31`) | Clean Layered (`clean-layered.css`) |
|---|---|---|
| Card background | `#ffffff` | `.data-card` white, `.main-content` transparent over the `#f5f3f0` panel |
| Radius | `0.25rem` (4px) | `.data-card`: `0.25rem` |
| Shadow | `0 1px 4px rgba(0,0,0,0.08)` | `.data-card`: `0 1px 2px rgba(90,70,50,0.08), 0 4px 14px rgba(90,70,50,0.13)` |
| Side padding | `2.5rem` (40px) | n/a (padding lives on `.data-card`, `0px 12px`) |

Dark mode needed **no revert** — `dark.css:88-91` already sets `.main-content`/`.page-panel` to the same near-black as the page (`#16150f`), so C1's flat dark mockup was already correct there.

**Mockup implementation:** a new `.content-card` wrapper, reading a new token `--bg-content` (distinct from `--bg-panel`, which stays the outer/panel role from §4 of C1). Clean Page light → `#ffffff` + `--r-1` + `--shadow-card`. Clean Layered light → `transparent` (production keeps depth at the `.data-card` level in Layered, not a second card level — matching that, not inventing a fourth surface). Dark, both layouts → same value as `--bg-panel`.

**One deliberate deviation, flagged, not silent:** side padding is `var(--sp-6)` (32px), not production's literal `40px` — 40px isn't a step on C1's 4px ramp (`--sp-6: 32px`, `--sp-7: 48px`), and inserting an eighth step to match one literal value defeats the point of the ramp. This is an 8px tightening, visible at 1280px only (both mockup screenshots show it). If the owner wants pixel-exact 40px preserved, `--sp-6` should be used as-is and this flagged difference accepted, or a route-scoped override added in C3 — not a change to the shared ramp.

Supersedes: `C1-handoff.md` §8's mockup description (files now carry `--bg-content`) and the general layout-surfaces list in §1 (which described the problem, not this token).

---

## 2. Leader row — owner selected L2: two-step green tint, fixed

**The bug, unchanged from C1's own finding (`C1-handoff.md` §1):** `--table-hover-bg` and `--table-toprank-bg` are both `#F3F7F3` in production (`clean.css:46,48`) — the leader row and a hovered row are pixel-identical. C1's fix was a new hue, `--sand`. **The owner rejected introducing a new warm-neutral hue.** Three green-family alternatives were built and screenshotted side by side in `mockups/c1b-leader-row.html`.

| | Treatment | Verdict |
|---|---|---|
| L1 | No fill. 3px `--green` inset-left rule + player name weight 600 + Total in `--green`. | Lead's recommendation (different visual channel from hover, can never collide). **Not selected** — owner preferred L2's tint look. |
| **L2 — owner selected** | Two-step green tint: leader `#E4EFE4` / dark `#1f3320`, hover stays `#F3F7F3` / dark `#1b2a1d`. | **Shipped with a real flaw when first mocked**, found and fixed before being carried into the page mockups — see below. |
| L3 | No fill; 2px `--ink` rule under the leader row + bold Total. | Rejected: reads as "end of a group" (a header-underline convention already used elsewhere), not "this is the leader." |

**The flaw L2 shipped with, and the fix:** hovering the leader row itself either held the same flat tint or — if a generic `tr:hover` rule won the CSS cascade — could go visibly *lighter*, the opposite of emphasis, and fragile outdoors/in dark mode either way. **Fixed**, not shipped as originally mocked: the leader row gets its own `:hover` rule with a third, deeper tint (`--leader-tint-hover: #C9E0C9` light / `#2c4a2d` dark), scoped with higher CSS specificity than the generic row-hover rule so it always wins regardless of source order. Verified in-browser: resting `rgb(228, 239, 228)` → hovered `rgb(201, 224, 201)`, a deliberate deepening, not a flatten or lighten.

**Consequence for the token set:** `--sand` is **removed**, replaced by `--leader-tint`/`--leader-tint-hover` — a like-for-like swap in role (both are "leader row background"), not an addition to the palette C1 proposed.

**Not relitigated:** E1 (Editorial Golf, later in the roadmap) may reintroduce a warm surface as a deliberate experiment. That is a different question — a stylistic direction — from fixing this bug, and doesn't need warmth to do it.

Supersedes: `C1-handoff.md` §5's `--sand` row and "Consequence" paragraph, and §10's C5 leader-row line (now: "leader row → L2 two-step green tint with a dedicated hover-deepen rule").

---

## 3. Focus ring — owner selected F3: `--ink`, no new hue

**The bug, unchanged from C1's own finding (`C1-handoff.md` §1):** a global `:where(a,button,select,input):focus-visible { outline: 2px solid var(--accent) }` (`ui-polish.css:9-12`) plus four `--select-focus-ring` overrides in `base-vars.css` all resolve to green — keyboard focus is visually identical to "selected." C1's fix was a new hue, `--focus: #1a6fd4` (blue). **The owner's instinct was not to introduce another colour**, and asked for alternatives to be mocked.

The case that actually matters is not a plain unfocused control — it's **focus landing on the segment that is already selected and already green** (Net/Gross, any `.segmented` option). That's exactly what `mockups/c1b-focus-ring.html` tests, side by side, for all three:

| | Treatment | Verdict |
|---|---|---|
| F1 | Green 2px ring, `outline-offset: 3px`, background-coloured 1px halo pushing it fully clear of the box. | Rejected: still green. On the selected segment it reads as "more selected," not "keyboard is here" — the collision is unresolved, only pushed outward. |
| F2 | Green 2px **dashed**, offset 2px. | Rejected: the dash texture helps distinguish it from a solid underline, but it's the identical hue to "selected" — weakest exactly on the case that matters. |
| **F3 — owner selected** | **`--ink` 2px solid, offset 2px.** Rule becomes: *selection is green, focus is ink.* | Adopted — matched the lead's recommendation; owner noted a mild preference for it but said they "don't really mind" between the three. Introduces no new hue — reuses the existing `--ink` primary-text token, already defined for both modes. Reads clearly against a green-tinted selected segment in both light and dark, the one case F1/F2 fail. |

`--focus` **stays as a token name** — nothing that consumes `var(--focus)` needs to change — its value becomes `var(--ink)` in both light and dark blocks (previously `#1a6fd4` / `#5b9bde`).

Supersedes: `C1-handoff.md` §5's `--focus` row and the focus sentence in §6 ("`--focus` must render visibly distinct from `--green`" — now satisfied by reusing `--ink` rather than adding a fourth semantic hue).

---

## 4. The two mockups built for sign-off

### Segmented control — `mockups/c1b-segmented.html`

The owner said "show me a mockup first." Built as **before/after pairs on real measures**, not a swatch: today's `.scale-switch` (binary switch geometry) or `.pill-group` beside the proposed `.segmented`, for four actual site measures — Net/Gross (Leaderboard), Round view/TEG total (Scoring), Count/% (Scoring heatmap), and the three-option Metric row (Player Rankings) — each pair captioned with why the "before" pattern is the wrong semantic fit (switch implies on/off; pill shape collides with round/player navigation pills; hand-rolled JS duplicated per page). **Approved as mocked, no change requested.**

### Compact action — `mockups/c1b-compact-action.html`

The owner said "I'm not sure what it means." **First pass showed only the "after"** — three real `.action` instances headed by the grammar line:

> **Tabs** = which view · **Segmented** = which measure · **Action** = do or reveal something

**The owner correctly pushed back**: without a "before," it wasn't possible to judge what was actually changing (unlike the segmented mockup, which showed both). Rebuilt with genuine before/after pairs, using production's real markup and CSS values read directly from `base-vars.css`/`mobile.css`/`latest_round.html`, not approximated:

1. **Standings rank toggle** — **no before/after shown**, because there isn't one: `.rank-toggle` is already the `.action` pattern (F1/F6 already fixed its 28px/44px sizing and green +/− glyph). Shown once for completeness rather than silently omitted or faked into a comparison that doesn't exist.
2. **Retry after a failed load** — **before**: production's actual `.pill` (`latest_round.html:390`, `className = 'pill'`) — rounded-full, bordered, the identical shape used for round-number navigation and Net/Gross measure pills. **After**: `.action` — square geometry, green border/text, no fill, reading as "do this" rather than "navigate to this."
3. **History cell disclosure** — reproduced faithfully, not redesigned: the entire row is the click target (`button.teg-cell`, no chrome of its own), with a small +/− indicator in a separate narrow column shown only below 641px (`mobile.css:1114-1129`). Before/after differ only in the indicator's colour — production's literal un-tokenised `#999999` versus `--green`, matching the other two `.action` instances. **A related gap is flagged, not fixed**: that indicator column is `display: none` on desktop (`base-vars.css:288-289`), so above 641px the only affordance that a History row is clickable is `cursor: pointer` — out of scope here since it's a functional gap, not a token-consistency question, but worth a decision before C4 implements.

Both mockups keep the two-tier hit-area rule (44px touch / 28px desktop) and the F3 ink focus ring from §3.

---

## 5. Screenshot manifest and checks

Per the owner's confirmed scope: full 24-shot matrix on the two revised page mockups (unchanged from C1's own coverage — needed because the content-card and leader-row/focus changes touch every combination); reduced 4-shot matrix (390/1280 × light/dark, Clean Page geometry only — these four mockups have no `layout` concept) on the four new comparison mockups.

```
webapp/design_reviews/ui_workstream/
  C1b-handoff.md
  mockups/
    c1-standings.html        ← revised: --bg-content, L2 leader row (fixed), F3 focus
    c1-analysis.html         ← revised: --bg-content, F3 focus
    c1b-segmented.html       ← new: before/after, 4 real measures — approved as mocked
    c1b-compact-action.html  ← new: grammar rule + 3 real instances, before/after using production's actual .pill/.teg-cell values
    c1b-leader-row.html      ← new: L1/L2/L3 side by side; records the decision (L2 selected, L1/L3 not carried forward)
    c1b-focus-ring.html      ← new: F1/F2/F3 side by side, incl. focus-on-selected-segment case
  screenshots/C1b/
    standings-{390,768,1280}-{light,dark}-{page,layered}.png     (12)
    analysis-{390,768,1280}-{light,dark}-{page,layered}.png      (12)
    segmented-{390,1280}-{light,dark}.png                        (4)
    compact-action-{390,1280}-{light,dark}.png                   (4)
    leader-row-{390,1280}-{light,dark}.png                       (4)
    focus-ring-{390,1280}-{light,dark}.png                       (4)
```

**40 PNGs total.** Captured with Playwright Chromium (throwaway venv, same reason as C1: this checkout's interpreter doesn't carry `requirements-dev.txt`'s pin), viewport height 844px, `file://` URLs, `networkidle` + 200ms settle before each capture.

### Checks run

- **No page-level overflow** at all 40 captures: `document.documentElement.scrollWidth <= clientWidth` (1px tolerance) asserted in-browser. **0 failures.**
- **Two-tier hit-area contract**: every `.action`, `.seg-option`, `.tab-underline`, `summary` bounding box ≥44px at ≤640px, ≥28px at ≥641px — re-run because the content-card wrapper changes the box model C1 measured against. **First pass found a real bug** (the same class F6 and C1's own first pass caught): `c1b-focus-ring.html` and `c1b-segmented.html` were built without the phone 44px override for `.seg-option`/`.tab-underline` that the two page mockups and `c1b-compact-action.html`/`c1b-leader-row.html` already carry — measured 29–31px at 390px width (42 individual element failures across those two files). Fixed both, re-captured. **Second pass: 0 failures.**
- **Leader ≠ hover, at rest**: on `c1-standings.html`, light/page/1280px, the leader row's `.col-total` computed `background-color` is `rgb(228, 239, 228)` (`--leader-tint`) and a hovered non-leader row's is `rgb(243, 247, 243)` (`--hover-bg`). **Distinct — confirmed.**
- **Leader intensifies on hover, not just holds or lightens** — the specific flaw L2 shipped with (§2): hovering the leader row itself moves it from `rgb(228, 239, 228)` (rest) to `rgb(201, 224, 201)` (hovered) — measurably deeper, verified directly in-browser, not just asserted. **Confirmed fixed.**
- **Evidence integrity**: all 40 PNG md5s distinct. **0 duplicates.**

All checks run directly (not delegated) after the capture subagent hit the account's session rate limit mid-task (see Handoff note below) — the lead ran the same Playwright script itself in the existing throwaway venv rather than re-queue the delegation. Re-run a second time after the owner's decisions changed the leader-row and compact-action mockups; results above are from that final pass.

### Not run

- `python scripts/check_css_comments.py` — no `.css` file touched.
- `pytest` — no application code touched; per `CLAUDE.md`'s blast-radius rule, no suite is warranted for a docs/prototype-only chat.
- Local markdown link check — this document's only internal link (`C1-handoff.md`) is a sibling file already known to exist.

---

## 6. Risks and open items

- **The `--sp-6` vs literal-40px padding deviation (§1)** is a judgement call, not fully resolved — flagged for the owner rather than silently picked. C3 should confirm which the foundation actually uses before implementing.
- **`--sand` is removed, replaced by `--leader-tint`/`--leader-tint-hover`.** Any later chat (E1 Editorial Golf) that wants a warm surface again starts from zero, not from a dormant token.
- **L2's specificity fix is load-bearing, not cosmetic.** `.standings-table tr.is-leader:hover td` must stay a higher-specificity selector than the generic `.standings-table tr:hover td` (3 classes vs. 2) — if C3 refactors this into a different selector shape, it must re-verify the leader row still wins on hover, or the original flaw returns.
- **F3's `--ink` reuse means `--focus` and `--ink` are the same colour**, not independent tokens with a coincidental value. If a future component needs to distinguish "this text is ink" from "this element has focus" via CSS alone (not just semantics), that aliasing is worth revisiting — not a problem today since nothing needs both simultaneously.
- **The History desktop indicator gap (§4) is a real, separately-flagged finding**, not a C1b design decision — it needs an explicit owner call (add the indicator above 641px, or leave `cursor: pointer` as the only affordance) before C4 touches that template.
- **All of C1's own risks (`C1-handoff.md` §12) still apply unchanged** — the two-level heading correction, the `--ink-muted` contrast change, `.scale-switch`'s shared use by the genuinely-binary Latest Round toggle, `base-vars.css` declaring zero custom properties, the `.pp-tab` double-toggle risk, the three independent hand-rolled active-state JS implementations, the Tailwind Play CDN source-order gotcha, mockup data fidelity, and the dead `ts-*` blocks needing an explicit owner nod before deletion.
- **This session's Playwright was again a throwaway local install**, not the repo's pinned `requirements-dev.txt` version — sufficient for static-prototype captures; C3 onward should use the repo's own pinned setup for application-page screenshots.

---

## Handoff

Base `809b97d`. **All four decisions signed off by the owner (2026-09-20)** — leader row L2 (fixed), focus ring F3, segmented control as mocked, compact action as mocked. This chat's resulting commit becomes the base for **C3 directly**; no further critique pass is required for these items. No push, merge, or deploy performed.

**Delegation note:** screenshot capture and verification were assigned to a Sonnet subagent per the roadmap's "lower-cost agents for value/selector inventory only" rule. It installed Playwright and Chromium successfully but was terminated by the account's session rate limit before writing the capture script. The lead ran the same script directly in the venv the subagent had already provisioned, found and fixed the hit-area bug described above, and re-ran to a clean pass — no design decision was delegated, only the mechanical capture/check step that a strong lead does not need to own itself.
