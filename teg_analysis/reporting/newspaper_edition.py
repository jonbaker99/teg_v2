"""Deterministic parser: storyline-first report artefacts -> newspaper edition
dict, plus a server-side renderer for the desktop layout.

UI-agnostic (no frontend imports) so both `scripts/build_newspaper_edition.py`
(local prototype regeneration) and `webapp/routes/report_preview.py` (the live
preview page) can import it. Reads go through `teg_analysis.io.read_text_file`
— volume-then-GitHub aware on Railway, never the raw filesystem.

Moved from `scripts/build_newspaper_edition.py` (see that file's history for
the parser's origin) when the newspaper layout was wired into the webapp as a
preview page. Only the two file reads changed; the parsing logic is untouched.

Two source files per TEG:

    data/commentary/teg_N_storyline_plan.json
    data/commentary/teg_N_report_storylinefirst_styled.md

`build_edition(teg)` returns one "edition" dict (schema: see the fields built
in `build_edition`). Only TEGs with storyline-first artefacts have one —
whichever `available_tegs()` finds.

`render_desktop_html(edition, rail="s2")` renders the desktop layout: a lead
article plus sub-articles packed into full-width rows by `plan_rows` (see
that function's docstring). This used to dispatch through three named
"arrangements" (E1/E2/E3), ported 1:1 from `webapp/report_layout_prototypes/
composite.html`'s JS; that system produced broken layouts whenever the
leftover sub-article count didn't divide evenly into rows of 3, so it was
replaced (2026-09-11) by explicit row packing that never leaves a partial
row. The prototype is retained only as frozen historical reference — see
that folder's README — and is not kept in sync with this module. The `rail`
parameter (S1/S2, from `elements.html`'s `railVariants()`) is not in the
prototype and only exists here.
"""

from __future__ import annotations

import html
import json
import re
from functools import lru_cache
from typing import Any, NamedTuple

from teg_analysis.io import read_file, read_text_file

COMMENTARY_DIR = "data/commentary"
COMPLETED_TEGS_CSV = "data/completed_tegs.csv"


class ArticleFilter(NamedTuple):
    """Which stories make the paper. A presentation choice, applied last.

    Every plan carries three MANDATORY storylines — trophy, jacket, spoon —
    populated "regardless of how good you judge them to be", plus 0-3 discovered
    ones. The three competitions are always printed: a report that never says who
    won the Jacket has a hole in it, however dull that week's Jacket was. This
    filter applies to the DISCOVERED stories only — the ones the editor chose to
    add, and so the ones worth second-guessing.

    Deliberately applied at edition-build time, not earlier. The plan, the draft
    and the voiced report all still contain every storyline; filtering here means
    a dropped story is still on disk, still in the styled markdown, and comes back
    by changing a threshold rather than by regenerating anything.

    Fields:
        min_compelling / min_humour: floors on each score.
        match: "all" requires both floors, "any" requires either.
        min_combined: a rescue path — an article clears the filter if
            compelling + humour reaches this, whatever `match` says. Lets a
            9-humour/5-compelling piece survive a compelling floor of 7.

    The default keeps everything, so behaviour is unchanged until a caller opts in.
    """

    min_compelling: int = 0
    min_humour: int = 0
    match: str = "all"
    min_combined: int = 0

    def keeps(self, article: dict[str, Any]) -> bool:
        compelling = article.get("compelling") or 0
        humour = article.get("humour") or 0
        if self.min_combined and compelling + humour >= self.min_combined:
            return True
        hits_compelling = compelling >= self.min_compelling
        hits_humour = humour >= self.min_humour
        return hits_compelling or hits_humour if self.match == "any" else (
            hits_compelling and hits_humour)

    def describe(self) -> str:
        if self == ArticleFilter():
            return "no filter (every story printed)"
        joiner = " or " if self.match == "any" else " and "
        parts = joiner.join((f"compelling>={self.min_compelling}",
                             f"humour>={self.min_humour}"))
        if self.min_combined:
            parts += f", or combined>={self.min_combined}"
        return parts


KEEP_EVERYTHING = ArticleFilter()

#: The policy every caller gets unless it passes its own — the webapp preview
#: route included. Change this one constant to change what the paper prints
#: everywhere; the CLI flags on `scripts/build_newspaper_edition` exist to try a
#: policy before committing to it here.
DEFAULT_ARTICLE_FILTER = KEEP_EVERYTHING


#: The three competitions. Their storylines are mandatory in the plan — the
#: editor writes one each "regardless of how good you judge them to be" — and
#: they are mandatory on the page for the same reason: a tournament report that
#: does not say who won the Jacket has a hole in it, however dull that week's
#: Jacket was. Only discovered stories (SIDEBAR) are filterable.
COMPETITION_KICKERS = ("TROPHY", "GREEN JACKET", "WOODEN SPOON")


def is_competition_article(article: dict[str, Any]) -> bool:
    """Whether this article carries one of the three mandatory competitions.

    Substring, not equality: a merged cross-cut article joins its kickers with
    " & " ("WOODEN SPOON & SIDEBAR"), and one carrying a competition is still
    mandatory. Same test `_choose_second_story` uses to find the Jacket.
    """
    return any(k in article.get("kicker", "") for k in COMPETITION_KICKERS)


def filter_articles(articles: list[dict[str, Any]],
                    article_filter: ArticleFilter) -> tuple[list, list]:
    """Split `articles` into (kept, dropped).

    Trophy, Green Jacket and Wooden Spoon are always kept, whatever they score.
    The filter exists to thin the *discovered* stories, which are the ones the
    editor chose to add; the competitions are the report's spine, and the lead is
    one of them, which `render_desktop_html` requires anyway.
    """
    kept, dropped = [], []
    for a in articles:
        keep = a.get("is_lead") or is_competition_article(a) or article_filter.keeps(a)
        (kept if keep else dropped).append(a)
    return kept, dropped


def artefact_paths(teg: int) -> tuple[str, str]:
    """The two files an edition is built from, for `teg`."""
    return (f"{COMMENTARY_DIR}/teg_{teg}_report_storylinefirst_styled.md",
            f"{COMMENTARY_DIR}/teg_{teg}_storyline_plan.json")


@lru_cache(maxsize=None)
def has_edition(teg: int) -> bool:
    """Whether `teg` has both storyline-first artefacts, so `build_edition` can run."""
    for path in artefact_paths(teg):
        try:
            read_text_file(path)
        except Exception:      # noqa: BLE001 - missing, unreadable, or GitHub 404
            return False
    return True


@lru_cache(maxsize=1)
def available_tegs() -> tuple[int, ...]:
    """TEGs with storyline-first artefacts, discovered rather than hardcoded.

    Was a hardcoded `AVAILABLE_TEGS = (14, 16, 18)`, which meant generating a
    report for a new TEG silently failed to reach the preview page until someone
    remembered to edit this file.

    Candidates come from `completed_tegs.csv` rather than a directory scan,
    because there is no volume-aware directory listing on Railway — the same
    reason `webapp/routes/reports.py` drives its dropdown that way. Each
    candidate is then probed for both artefacts.

    Probing a *missing* file costs a GitHub round-trip on Railway (`read_text_file`
    caches hits to the volume but not misses), hence the `lru_cache` on both this
    and `has_edition`. Call `clear_edition_caches()` after generating new
    artefacts in a long-lived process; a fresh CLI run starts cold anyway.
    """
    try:
        completed = read_file(COMPLETED_TEGS_CSV)
        candidates = sorted(int(n) for n in completed["TEGNum"].astype(int).unique())
    except Exception:          # noqa: BLE001 - no CSV, unreadable, unexpected shape
        return ()
    return tuple(t for t in candidates if has_edition(t))


def clear_edition_caches() -> None:
    """Drop memoised artefact discovery, so newly generated reports are seen."""
    has_edition.cache_clear()
    available_tegs.cache_clear()

# Priority order for combining kickers on a merged (" / "-joined) heading.
_KICKER_PRIORITY = ["TROPHY", "GREEN JACKET", "WOODEN SPOON", "SIDEBAR"]


def _strip_html(text: str) -> str:
    """Strip tags, collapse whitespace. Good enough for the small fixed set of
    inline tags this pipeline emits (<strong>, <span>, <p>)."""
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _parse_dateline(md: str) -> dict[str, str]:
    m = re.search(r'<p class="dateline">(.*?)</p>', md)
    if not m:
        raise ValueError("dateline not found")
    parts = [p.strip() for p in m.group(1).split("|")]
    if len(parts) != 3:
        raise ValueError(f"dateline did not split into 3 parts: {parts!r}")
    teg, venue, year = parts
    return {"teg": teg, "venue": venue, "year": year}


def _parse_title(md: str) -> str:
    m = re.search(r"^#\s+(.+?)\s*\{\.report-title\}\s*$", md, re.MULTILINE)
    if not m:
        raise ValueError("title not found")
    return m.group(1).strip()


def _parse_results(md: str) -> list[dict[str, Any]]:
    m = re.search(
        r'<section class="callout at-a-glance-box">(.*?)</section>', md, re.DOTALL
    )
    if not m:
        raise ValueError("at-a-glance results block not found")
    block = m.group(1)
    results = []
    for p_html in re.findall(r"<p\b[^>]*>(.*?)</p>", block, re.DOTALL):
        if "at-a-glance-title" in p_html:
            continue
        label_m = re.search(r"<strong>(.*?):</strong>", p_html)
        if not label_m:
            continue
        label = _strip_html(label_m.group(1))
        value = _strip_html(p_html[label_m.end():])
        results.append(
            {
                "label": label,
                "value": value,
                "lead": 'class="trophy-winner"' in p_html,
            }
        )
    if len(results) != 3:
        raise ValueError(f"expected 3 results lines, got {len(results)}: {results!r}")
    if not any(r["lead"] for r in results):
        raise ValueError("no result line flagged as lead (trophy-winner)")
    return results


def _split_body_sections(md: str) -> tuple[list[tuple[str, str]], str]:
    """Split the document on top-level `## ` headings. Returns
    (article_sections, appendix_markdown) where article_sections is a list of
    (heading, content) pairs preceding "## Standings by round", and
    appendix_markdown is the raw text from "## Standings by round" onward."""
    heading_re = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)
    matches = list(heading_re.finditer(md))
    if not matches:
        raise ValueError("no ## headings found")

    sections: list[tuple[str, str, int]] = []  # heading, content, start_of_heading
    for i, m in enumerate(matches):
        heading = m.group(1).strip()
        content_start = m.end()
        content_end = matches[i + 1].start() if i + 1 < len(matches) else len(md)
        content = md[content_start:content_end]
        sections.append((heading, content, m.start()))

    appendix_start = None
    for heading, content, start in sections:
        if heading == "Standings by round":
            appendix_start = start
            break
    if appendix_start is None:
        raise ValueError("'## Standings by round' heading not found")

    article_sections = [
        (heading, content) for heading, content, start in sections if start < appendix_start
    ]
    appendix_md = md[appendix_start:]
    return article_sections, appendix_md


def _parse_paragraphs(content: str) -> tuple[str | None, list[str]]:
    """Given the raw content under a ## heading, extract the optional **bold**
    mini-headline (first non-blank line, if it is exactly a bold span) and the
    remaining paragraphs (blank-line separated, HTML stripped)."""
    blocks = [b.strip() for b in re.split(r"\n\s*\n", content.strip()) if b.strip()]
    bold_headline = None
    if blocks:
        bold_m = re.fullmatch(r"\*\*(.+?)\*\*", blocks[0])
        if bold_m:
            bold_headline = bold_m.group(1).strip()
            blocks = blocks[1:]
    paragraphs = [_strip_html(b) for b in blocks]
    return bold_headline, paragraphs


_TRAILING_STOPWORDS = {
    "a", "an", "and", "at", "by", "for", "from", "his", "her", "their", "in",
    "into", "of", "on", "or", "the", "to", "with",
}


def _derive_headline(heading: str) -> str:
    """Cut a section heading down to a headline-length phrase.

    Cuts at the first of —, :, or , that leaves at least MIN_WORDS words, so a
    heading like "Jon Baker, defending Trophy champion, collects the Wooden
    Spoon..." yields "Jon Baker, defending Trophy champion" rather than the bare
    name. Falls back to the first MAX_WORDS words. A merged (' / '-joined)
    heading is cut to its first storyline first.

    The derived text is still weaker than a written headline — see
    `webapp/report_layout_prototypes/README.md` → "Still to do". This only
    stops the weakness reading as a parser bug on the page.
    """
    MIN_WORDS, MAX_WORDS, FULL_WORDS = 4, 10, 14
    heading = heading.split(" / ")[0].strip()
    cuts = sorted(
        pos for ch in ("—", ":", ",") for pos in [heading.find(ch)] if pos != -1
    )
    for pos in cuts:
        candidate = heading[:pos].strip()
        if len(candidate.split()) >= MIN_WORDS:
            return candidate
    words = heading.split()
    if len(words) <= FULL_WORDS:
        return heading
    words = words[:MAX_WORDS]
    while len(words) > MIN_WORDS and words[-1].lower() in _TRAILING_STOPWORDS:
        words.pop()
    return " ".join(words)


def _choose_headline(bold_headline: str | None, heading: str) -> str:
    """Prefer the writer's bold mini-header, but only at headline length.

    The draft writer emits it for roughly half of sections and it is the best
    text available when it fits (2-9 words). Longer than that it is a second
    standfirst, not a headline, so derive instead.
    """
    if bold_headline and 2 <= len(bold_headline.split()) <= 9:
        return bold_headline
    return _derive_headline(heading)


def _choose_standfirst(headline: str, heading: str) -> str:
    """Drop the standfirst when it would only restate the headline.

    A derived headline is a prefix of its own heading, so printing both repeats
    the same line. Keep the heading only where the part beyond the headline
    carries real extra information (MIN_EXTRA words or more).
    """
    MIN_EXTRA = 8
    if not heading.lower().startswith(headline.lower()):
        return heading
    remainder = heading[len(headline):].strip(" ,:—-")
    return heading if len(remainder.split()) >= MIN_EXTRA else ""


def _plan_headline(matches: list[tuple[str, dict[str, Any]]]) -> str | None:
    """The real `chosen_headline`(s) from the plan, joined for a merged
    (' / ') heading. `None` when any matched storyline predates the field
    (`story_plan.py`, 2026-09-06) — the caller falls back to `_derive_headline`."""
    headlines = [s.get("chosen_headline") for _, s in matches]
    if not all(headlines):
        return None
    return " & ".join(headlines)


def _plan_standfirst(matches: list[tuple[str, dict[str, Any]]]) -> str:
    standfirsts = [s.get("standfirst") for _, s in matches if s.get("standfirst")]
    return " ".join(standfirsts)


# ---------------------------------------------------------------------------
# Matching a report section back to the plan storyline it was written from.
#
# THE ANCHOR IS THE KEY; the heading is only a fallback. Exact subject equality
# was the whole mechanism until 2026-09-10 and it broke repeatedly, because it
# made a PROSE STRING the join between two artefacts written by different
# passes at different times:
#
#   - PR #95 regenerated the plans with fresh `subject` text but not the
#     reports, so every heading stopped matching. It was patched by editing the
#     styled markdown by hand — a fix living only in a DERIVED file, which the
#     next `style_report` duly destroyed.
#   - The voice pass is told to leave headings alone and does not always comply.
#
# Fuzzy matching was tried and rejected: measured against ground truth on TEGs
# 14 and 16, every metric (fragment overlap, Jaccard, Dice, candidate overlap)
# put TEG 14's "Alex Baker and the 16th hole" section on the DAVID MULLIN
# trophy storyline, because a long subject string absorbs any short heading's
# words. A wrong match is worse than no match: it drives the kicker and the
# layout scores.
#
# So the section carries its own identity. `_ANCHOR_RE` reads
# `<!-- storyline: trophy -->` (or `d1,spoon` for a merged section) from the
# line under the heading. Reports written before anchors existed fall back to
# exact subject matching, and a section that resolves by neither route is
# DEGRADED rather than fatal — see `_degraded_storyline`. A preview page that
# renders four articles correctly and one plainly beats one that 500s.
_ANCHOR_RE = re.compile(r"<!--\s*storyline:\s*([a-z0-9,\s]+?)\s*-->", re.IGNORECASE)


def _slot_by_key(key: str, plan: dict[str, Any]) -> tuple[str, dict[str, Any]] | None:
    """Resolve one anchor key. `trophy` / `jacket` / `spoon`, or `dN` for the
    Nth discovered storyline. Returns None for a key the plan cannot satisfy —
    an anchor pointing past the end of a regenerated plan degrades like a
    missing one rather than raising."""
    key = key.strip().lower()
    fixed = {"trophy": ("TROPHY", "trophy_storyline"),
             "jacket": ("GREEN JACKET", "jacket_storyline"),
             "spoon": ("WOODEN SPOON", "spoon_storyline")}
    if key in fixed:
        kicker, field = fixed[key]
        return kicker, plan[field]
    if key.startswith("d") and key[1:].isdigit():
        discovered = plan["discovered_storylines"]
        idx = int(key[1:])
        if idx < len(discovered):
            return "SIDEBAR", discovered[idx]
    return None


def _anchor_matches(content: str, plan: dict[str, Any]
                    ) -> list[tuple[str, dict[str, Any]]] | None:
    """The storylines named by this section's anchor, or None if it has none
    (or none that resolve)."""
    m = _ANCHOR_RE.search(content)
    if not m:
        return None
    matches = [_slot_by_key(k, plan) for k in m.group(1).split(",") if k.strip()]
    if not matches or not all(matches):
        return None
    return matches  # type: ignore[return-value]


def _match_storyline(subject: str, plan: dict[str, Any]) -> tuple[str, dict[str, Any]] | None:
    """Match a heading fragment (post ' / ' split) to its plan slot by exact
    subject string. Returns (kicker, storyline_dict), or None if nothing matches."""
    if plan["trophy_storyline"]["subject"] == subject:
        return "TROPHY", plan["trophy_storyline"]
    if plan["jacket_storyline"]["subject"] == subject:
        return "GREEN JACKET", plan["jacket_storyline"]
    if plan["spoon_storyline"]["subject"] == subject:
        return "WOODEN SPOON", plan["spoon_storyline"]
    for storyline in plan["discovered_storylines"]:
        if storyline["subject"] == subject:
            return "SIDEBAR", storyline
    return None


def _degraded_storyline(heading: str) -> tuple[str, dict[str, Any]]:
    """Stand-in for a section that resolves to no plan storyline.

    Keeps the section's own prose and heading, which are the parts a reader
    actually sees, and gives up only the plan-side extras: the kicker becomes
    SIDEBAR and the layout scores go to zero, so an unmatched section is never
    promoted to the lead on scores it does not have.
    """
    return "SIDEBAR", {"subject": heading, "chosen_headline": "", "standfirst": "",
                       "compelling_score": 0, "humour_score": 0}


def _resolve_section(heading: str, content: str, plan: dict[str, Any]
                     ) -> list[tuple[str, dict[str, Any]]]:
    anchored = _anchor_matches(content, plan)
    if anchored:
        return anchored
    fragments = [f.strip() for f in heading.split(" / ")]
    matched = [_match_storyline(f, plan) for f in fragments]
    if all(matched):
        return matched  # type: ignore[return-value]
    print(f"[newspaper_edition] WARNING: section has no storyline anchor and its "
          f"heading matches no plan subject; rendering it plainly: {heading[:80]!r}")
    return [_degraded_storyline(heading)]


def derive_descriptor(storyline: dict, kicker: str) -> str:
    """Deterministic fallback for `descriptor` when the plan predates the field
    (all 17 TEGs as of 2026-09). Matches the storyline's own text against the
    TEG's actual player field; no venue/course matching (too unreliable without
    an LLM judgement call) -- falls back to the bare kicker rather than guessing
    wrong. See prompts.DESCRIPTOR_RULE for the rule this approximates.
    """
    if kicker == "TROPHY":
        return "TROPHY"

    from teg_analysis.core.players import get_player_dict

    display_names = {
        " ".join(part.capitalize() if part.isupper() else part for part in raw.split())
        for raw in get_player_dict().values()
    }

    def _names_in(text: str) -> list[tuple[int, str]]:
        lower_text = text.lower()
        return sorted(
            (idx, name)
            for name in display_names
            for idx in [lower_text.find(name.lower())]
            if idx != -1
        )

    if "GREEN JACKET" in kicker or "WOODEN SPOON" in kicker:
        headline = storyline.get("chosen_headline", "")
        if _names_in(headline):
            # Already unambiguous -- the winner/loser is named in the headline.
            return kicker
        # Not in the headline. This deterministic path has no separate concept
        # of who the actual jacket/spoon winner IS, so it cannot confirm a name
        # found only in `subject` is really the winner -- but `subject` is an
        # editor-written label that in practice centres on that player, so a
        # single unambiguous name found there is a reasonable signal. Anything
        # less clean (zero or multiple names) falls back to the bare kicker
        # rather than guessing wrong.
        subject_names = _names_in(storyline.get("subject", ""))
        if len(subject_names) == 1:
            return f"{kicker} | {subject_names[0][1].upper()}"
        return kicker

    if kicker != "SIDEBAR":
        return kicker

    text = f"{storyline.get('chosen_headline', '')} {storyline.get('subject', '')}"
    found = _names_in(text)
    names = [name.upper() for _, name in found]
    if len(names) == 1:
        return names[0]
    if len(names) == 2:
        return " | ".join(names)
    return "SIDEBAR"


def _parse_articles(
    article_sections: list[tuple[str, str]], plan: dict[str, Any]
) -> list[dict[str, Any]]:
    articles = []
    for heading, content in article_sections:
        matches = _resolve_section(heading, content, plan)
        content = _ANCHOR_RE.sub("", content)

        kickers = sorted(
            {k for k, _ in matches}, key=lambda k: _KICKER_PRIORITY.index(k)
        )
        kicker = " & ".join(kickers)

        # Prefer an explicit editor-authored `descriptor` (prompts.DESCRIPTOR_RULE);
        # fall back to the deterministic approximation for plans written before
        # the field existed. Joined the same way `kickers` are, deduplicating
        # when a merged section's storylines resolve to the identical descriptor.
        descriptors = []
        for k, s in matches:
            d = s.get("descriptor") or derive_descriptor(s, k)
            if d not in descriptors:
                descriptors.append(d)
        descriptor = " & ".join(descriptors)

        compelling = max(s["compelling_score"] for _, s in matches)
        humour = max(s["humour_score"] for _, s in matches)

        bold_headline, paragraphs = _parse_paragraphs(content)
        plan_headline = _plan_headline(matches)
        if plan_headline:
            headline = plan_headline
            standfirst = _plan_standfirst(matches)
        else:
            # Artefact predates the headline/standfirst fields (story_plan.py,
            # 2026-09-06) — derive, same as before.
            headline = _choose_headline(bold_headline, heading)
            standfirst = _choose_standfirst(headline, heading)
        words = sum(len(p.split()) for p in paragraphs)

        articles.append(
            {
                "kicker": kicker,
                "descriptor": descriptor,
                "headline": headline,
                "standfirst": standfirst,
                "paragraphs": paragraphs,
                "words": words,
                "compelling": compelling,
                "humour": humour,
                "is_lead": kicker == "TROPHY",
            }
        )

    # The Trophy section leads. Where it cannot be identified — a degraded
    # section, or a plan/report pair that has drifted — the strongest article
    # leads instead. An edition that leads on the wrong story is a worse layout;
    # an edition that raises here is no page at all.
    leads = [a for a in articles if a["is_lead"]]
    if len(leads) != 1:
        print(f"[newspaper_edition] WARNING: expected exactly 1 TROPHY lead article, "
              f"got {len(leads)}; leading on the strongest article instead.")
        articles.sort(key=lambda a: (-a["compelling"], -a["humour"]))
        for a in articles:
            a["is_lead"] = False
        articles[0]["is_lead"] = True
        leads = [articles[0]]

    lead = leads[0]
    sub_articles = [a for a in articles if not a["is_lead"]]
    sub_articles.sort(key=lambda a: (-a["compelling"], -a["humour"]))
    return [lead] + sub_articles


_DASH_QUALIFIER_RE = re.compile(r"\s([—–])\s")
_TRAILING_PAREN_RE = re.compile(r"(\([^()]*\))\s*$")


def split_value_qualifier(value: str) -> tuple[str, str]:
    """Split an at-a-glance result value into (value_name, value_qual).

    The value carries two shapes in real data: a short parenthetical
    ("David Mullin (3rd Trophy)") and a long em-dash aside ("Alex Baker —
    169 pts, by 8 from John Patterson"). Splits at whichever separator
    occurs first in the string:

    - an em-dash/en-dash surrounded by spaces, or
    - the final parenthetical, when it runs to the end of the string.
      `[^()]*` (not `.*`) keeps this to the LAST parenthetical: greedy
      `.*` matched from an earlier "(" all the way to the closing ")",
      so "Player (Jr) wins (1st Trophy)" split at "(Jr)" and swallowed
      "wins" into the qualifier. Parentheses that are not at the end are
      left alone either way.

    Neither present -> value_qual is "" and value_name is the whole string.
    `value_qual` keeps its separator (the dash, or the parens) verbatim.
    """
    dash_m = _DASH_QUALIFIER_RE.search(value)
    paren_m = _TRAILING_PAREN_RE.search(value)
    starts = [m.start(1) for m in (dash_m, paren_m) if m]
    if not starts:
        return value, ""
    split_at = min(starts)
    return value[:split_at].rstrip(), value[split_at:].rstrip()


_STANDING_ENTRY_RE = re.compile(r"([A-Z]{2})\s+([+-]?\d+)")


def _player_name(code: str) -> str:
    """Code -> display name. players.csv stores the surname in caps; the report
    prose does not, so title-case it to match."""
    from teg_analysis.core.players import get_player_dict

    raw = get_player_dict().get(code)
    if not raw:
        return code
    return " ".join(part.capitalize() if part.isupper() else part for part in raw.split())


def _add_runners_up(results: list[dict[str, Any]], standings: list[dict[str, Any]]) -> None:
    """Attach the near-miss to each at-a-glance line, from the final standings.

    Trophy and Green Jacket take second place; the Wooden Spoon is decided on
    the Trophy metric, so its near-miss is second from last on that table.
    """
    if not standings:
        return
    final = standings[-1]
    trophy = _STANDING_ENTRY_RE.findall(final["trophy"])
    jacket = _STANDING_ENTRY_RE.findall(final["jacket"])

    def line(entry: tuple[str, str] | None, label: str) -> str:
        """Name only. The score was dropped 2026-09-10: in the rail it is a bare
        number with no scale attached, and the full table is two inches below
        it in the appendix."""
        if not entry:
            return ""
        return f"{label}: {_player_name(entry[0])}"

    by_label = {
        "Trophy Winner": line(trophy[1] if len(trophy) > 1 else None, "Runner-up"),
        "Green Jacket": line(jacket[1] if len(jacket) > 1 else None, "Runner-up"),
        "Wooden Spoon": line(trophy[-2] if len(trophy) > 1 else None, "Next above"),
    }
    for r in results:
        r["runner_up"] = by_label.get(r["label"], "")


def _add_value_split(results: list[dict[str, Any]]) -> None:
    """Add `value_name`/`value_qual` (see `split_value_qualifier`) to each
    at-a-glance line, leaving the original `value` untouched — `editions.json`
    is also read by the frozen prototype HTML files via `r.value`."""
    for r in results:
        r["value_name"], r["value_qual"] = split_value_qualifier(r["value"])


def _parse_standings(appendix_md: str) -> list[dict[str, Any]]:
    rounds = re.findall(
        r"\*\*End of Round (\d+)\*\*\s*"
        r'<p class="standings"><span class="standings-header">Trophy Standings:</span>\s*(.*?)</p>\s*'
        r'<p class="standings"><span class="standings-header">Green Jacket Standings:</span>\s*(.*?)</p>',
        appendix_md,
        re.DOTALL,
    )
    if not rounds:
        raise ValueError("no round standings parsed")
    return [
        {"round": int(rnd), "trophy": trophy.strip(), "jacket": jacket.strip()}
        for rnd, trophy, jacket in rounds
    ]


def _parse_records(appendix_md: str) -> list[dict[str, str]]:
    records = []
    for div_html in re.findall(r"<div class=\"records\">(.*?)</div>", appendix_md, re.DOTALL):
        header_m = re.search(r'<p class="records-header">(.*?)</p>', div_html)
        category = _strip_html(header_m.group(1)).rstrip(":") if header_m else "Records"
        for li in re.findall(r"<li>(.*?)</li>", div_html, re.DOTALL):
            records.append({"category": category, "text": _strip_html(li)})
    return records


#: Keys `build_edition` returns for the caller's benefit rather than the page's.
#: Stripped before the edition is serialised — otherwise every prototype page and
#: every mobile payload would carry the full text of stories deliberately not
#: shown, which is both wasteful and confusing to anyone reading the JSON.
_NON_PAGE_KEYS = ("dropped_articles",)


def for_page(edition: dict[str, Any]) -> dict[str, Any]:
    """The edition as the page needs it — internal bookkeeping removed.

    Use at every serialisation boundary: `editions.json`, and the JSON embedded
    for the mobile renderer.
    """
    return {k: v for k, v in edition.items() if k not in _NON_PAGE_KEYS}


def build_edition(teg: int,
                  article_filter: ArticleFilter | None = None) -> dict[str, Any]:
    """Read the two source artefacts for `teg` and return one edition dict.

    Raises FileNotFoundError (via `read_text_file`) if either artefact is
    missing — callers should only call this for `teg in available_tegs()`.

    `article_filter` decides which stories are printed; `None` uses
    `DEFAULT_ARTICLE_FILTER`, which prints all of them. Dropped ones are returned under `"dropped_articles"` rather than
    discarded, so the caller can say what it left out. Nothing on disk changes.
    """
    md_path, plan_path = artefact_paths(teg)
    md = read_text_file(md_path)
    plan = json.loads(read_text_file(plan_path))

    article_sections, appendix_md = _split_body_sections(md)

    results = _parse_results(md)
    standings = _parse_standings(appendix_md)
    _add_runners_up(results, standings)
    _add_value_split(results)

    articles, dropped = filter_articles(
        _parse_articles(article_sections, plan),
        DEFAULT_ARTICLE_FILTER if article_filter is None else article_filter)
    return {
        "teg": teg,
        "title": _parse_title(md),
        "dateline": _parse_dateline(md),
        "results": results,
        "articles": articles,
        "dropped_articles": dropped,
        "standings": standings,
        "records": _parse_records(appendix_md),
    }


# ---------------------------------------------------------------------------
# Desktop renderer.
# ---------------------------------------------------------------------------

CLEAR_MARGIN = 2


def _esc(s: Any) -> str:
    return html.escape("" if s is None else str(s), quote=True)


def _bold_spans(text: str) -> str:
    return re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", _esc(text))


def _paragraphs_html(paragraphs: list[str]) -> str:
    return "".join(f"<p>{_bold_spans(p)}</p>" for p in paragraphs)


def _masthead_html(edition: dict[str, Any]) -> str:
    # "The TEG" (2026-09-11): a fake newspaper name read as a gimmick. The
    # masthead now names the actual tournament ("TEG 16"); the dateline moves
    # to venue/year only, since the TEG number no longer needs repeating there.
    d = edition["dateline"]
    return (
        '<header class="masthead"><div class="mh-row">'
        f'<span class="wordmark">{_esc(d["teg"])}</span>'
        f'<span class="dateline">{_esc(d["venue"])} &middot; {_esc(d["year"])}</span>'
        '</div><div class="mh-rule"></div></header>'
    )


def _lead_head_html(lead: dict[str, Any]) -> str:
    standfirst = f'<p class="lead-standfirst">{_esc(lead["standfirst"])}</p>' if lead["standfirst"] else ""
    return (
        f'<p class="kicker">{_esc(lead.get("descriptor") or lead["kicker"])}</p>'
        f'<h1 class="lead-headline">{_esc(lead["headline"])}</h1>'
        f"{standfirst}"
    )


def _lead_body_html(lead: dict[str, Any]) -> str:
    return f'<div class="lead-body">{_paragraphs_html(lead["paragraphs"])}</div>'


def _result_items_html(edition: dict[str, Any]) -> str:
    """The three at-a-glance result lines, value with the runner-up under it.
    Shared by the S2 rail's R5 box and S1's full-width R3 strip — the two rail
    variants differ in where the list sits, not in what it contains."""
    items = []
    for r in edition["results"]:
        cls = " r-lead" if r["lead"] else ""
        runner = f'<span class="r-runner">{_esc(r["runner_up"])}</span>' if r.get("runner_up") else ""
        qual = f' <span class="r-qual">{_esc(r["value_qual"])}</span>' if r.get("value_qual") else ""
        items.append(
            f'<li class="r-item{cls}"><span class="r-label">{_esc(r["label"])}</span>'
            f'<span class="r-vals"><span class="r-value">{_esc(r["value_name"])}{qual}</span>{runner}</span></li>'
        )
    return "".join(items)


# Standings entries carry the round's own score in brackets ("SN 156 (R4: 43)").
# That belongs in the appendix table, where there is room for it and a reader is
# reconstructing the tournament. The rail is the compact summary, so it shows
# cumulative totals only.
_ROUND_SCORE_BRACKET_RE = re.compile(r"\s*\(R\d+:[^)]*\)")


def _totals_only(standings_row: str) -> str:
    return _ROUND_SCORE_BRACKET_RE.sub("", standings_row)


def _rail_html(edition: dict[str, Any]) -> str:
    items = _result_items_html(edition)
    last = edition["standings"][-1]
    return (
        '<aside class="rail">'
        f'<div class="r5"><p class="r5-title">At a glance</p><ul class="r-list">{items}</ul></div>'
        '<div class="rail-standings">'
        f'<p class="sb-lab">Final &middot; Trophy</p><p class="sb-row">{_esc(_totals_only(last["trophy"]))}</p>'
        f'<p class="sb-lab">Final &middot; Green Jacket</p><p class="sb-row">{_esc(_totals_only(last["jacket"]))}</p>'
        "</div></aside>"
    )


def _results_strip_html(edition: dict[str, Any]) -> str:
    """S1's full-width results strip (`.r3`) — the same result lines as the
    S2 rail's R5 box, laid out in a row instead of a column."""
    return f'<div class="r3"><ul class="r-list">{_result_items_html(edition)}</ul></div>'


def _sub_card_html(a: dict[str, Any]) -> str:
    standfirst = f'<p class="sub-standfirst">{_esc(a["standfirst"])}</p>' if a["standfirst"] else ""
    return (
        '<article class="sub-card">'
        f'<p class="kicker">{_esc(a.get("descriptor") or a["kicker"])}</p>'
        f'<h2 class="sub-headline">{_esc(a["headline"])}</h2>'
        f"{standfirst}"
        f'<div class="sub-body">{_paragraphs_html(a["paragraphs"])}</div></article>'
    )


def _appendix_html(edition: dict[str, Any]) -> str:
    # The cumulative/round-score standings tables were dropped 2026-09-11: they
    # duplicate the round-by-round and leaderboard views shown better elsewhere
    # in the app. `edition["standings"]` is still parsed and kept — the rail's
    # "Final" Trophy/Green Jacket lines (`_rail_html`) still read it.
    #
    # Given a kicker + headline + standfirst treatment (2026-09-11, prototyped
    # against TEG 4/17/18 as the heavy/light cases) instead of a lone eyebrow
    # label, so it reads as a section on the page rather than an afterthought.
    # Categories flow through ruled CSS columns (`.apx-flow`) instead of a
    # fixed 2-up grid, so 2 categories and 4 don't force the same split.
    by: dict[str, list[str]] = {}
    order: list[str] = []
    for r in edition["records"]:
        if r["category"] not in by:
            by[r["category"]] = []
            order.append(r["category"])
        by[r["category"]].append(r["text"])
    groups = "".join(
        f'<div class="apx-grp"><p class="apx-cat">{_esc(c)}</p><ul class="apx-list">'
        + "".join(f"<li>{_esc(t)}</li>" for t in by[c])
        + "</ul></div>"
        for c in order
    )
    return (
        '<section class="appendix">'
        '<p class="kicker">Records &amp; Personal Bests</p>'
        f'<h3 class="apx-hl">Notable achievements: {_esc(edition["dateline"]["teg"])}</h3>'
        '<p class="apx-standfirst">Every personal best, worst and rare feat this edition produced.</p>'
        f'<div class="apx-flow">{groups}</div>'
        "</section>"
    )


def _choose_second_story(subs: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not subs:
        return None
    jacket = next((a for a in subs if "GREEN JACKET" in a["kicker"]), None)
    if jacket is None:
        return subs[0]
    top = subs[0]
    if top is not jacket and top["compelling"] - jacket["compelling"] >= CLEAR_MARGIN:
        return top
    return jacket


#: Chunk sizes for what's left after taking groups of 3, keyed by remainder
#: count. A size-1 tail here only happens when exactly one sub-article is
#: left over with nothing to pair it with.
_TAIL_CHUNKS: dict[int, list[int]] = {0: [], 1: [1], 2: [2], 3: [3], 4: [2, 2]}


def _chunk_remaining(rest: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
    """Pack `rest` (already sorted by word count descending) into rows of 3,
    with the tail adjusted per `_TAIL_CHUNKS` so no row of size 1 is ever
    produced by leftover count."""
    rows: list[list[dict[str, Any]]] = []
    i = 0
    n = len(rest)
    while n - i > 4:
        rows.append(rest[i:i + 3])
        i += 3
    sizes = _TAIL_CHUNKS[n - i]
    tail = rest[i:]
    j = 0
    for size in sizes:
        rows.append(tail[j:j + size])
        j += size
    return rows


def plan_rows(subs: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
    """Pack sub-articles into display rows of 1, 2 or 3 items each, so a CSS
    grid row is always exactly as wide as the items in it — never a partial
    row with empty trailing cells, and never two stories stacked in one
    column.

    The first row is the promoted "second lead" (see `_choose_second_story`),
    alone, full width — unless there is no clear standout, in which case it
    becomes the first item of a 2-row instead (a size-1 row is reserved for a
    genuine standout).

    The rest are packed greedily into rows of 3, except the tail is adjusted
    so no row of size 1 is ever produced by leftover count: e.g. 4 remaining
    -> [2, 2], not [3, 1]. 1 remaining (with no promoted story at all) is the
    only case that legitimately produces a lone final row.

    Within the packed rows (not the promoted row), articles are sorted by
    word count descending before chunking, so each row groups similar-length
    stories together and finishes at roughly the same visual height, reducing
    blank space under short stories sitting next to long ones.
    """
    if not subs:
        return []
    promoted = _choose_second_story(subs)
    rest = sorted((a for a in subs if a is not promoted), key=lambda a: -a["words"])
    return [[promoted]] + _chunk_remaining(rest)


def _subs_rows_html(rows: list[list[dict[str, Any]]]) -> str:
    parts = []
    for i, row in enumerate(rows):
        cards = "".join(_sub_card_html(a) for a in row)
        parts.append(f'<div class="subs-row cols-{len(row)}">{cards}</div>')
        if i < len(rows) - 1:
            parts.append('<div class="thin-rule"></div>')
    return "".join(parts)


def _main_html(edition: dict[str, Any], lead: dict[str, Any], rail: str) -> str:
    """`.lead-head` plus the results/lead-body block, which differs by rail:
    S2 puts the results (and final standings) in an `<aside>` beside the lead
    body; S1 drops the aside and renders the results as a full-width strip
    above a full-width, 3-column lead body instead."""
    head = f'<div class="lead-head">{_lead_head_html(lead)}</div>'
    if rail == "s1":
        return (
            head
            + _results_strip_html(edition)
            + f'<div class="main-split">{_lead_body_html(lead)}</div>'
        )
    return head + f'<div class="main-split">{_lead_body_html(lead)}{_rail_html(edition)}</div>'


def render_desktop_html(edition: dict[str, Any], rail: str = "s2") -> str:
    """Render the `.paper` inner HTML for the desktop layout.

    `rail` is "s2" (default — results + final standings beside the lead) or
    "s1" (no rail — results as a full-width strip, standings only in the
    appendix); see `webapp/report_layout_prototypes/elements.html`'s
    `railVariants()`.
    """
    lead = next(a for a in edition["articles"] if a["is_lead"])
    subs = [a for a in edition["articles"] if not a["is_lead"]]
    rows = plan_rows(subs)
    return (
        _masthead_html(edition)
        + _main_html(edition, lead, rail)
        + '<div class="deck-rule"></div>'
        + _subs_rows_html(rows)
        + _appendix_html(edition)
    )
