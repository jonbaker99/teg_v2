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
currently `AVAILABLE_TEGS`.

`render_desktop_html(edition, rail="s2")` ports the desktop composite's JS
(E1/E2 "auto" composition, fill "f1") to Python 1:1 — see
`webapp/report_layout_prototypes/composite.html`'s `render()`/`renderE1`/
`renderE2`. It is a straight port so it stays trivially comparable to the
prototype if the prototype changes. E3 (a third arrangement, added for the
`/teg-reports-preview` switch matrix — see that route's docstring) and the
`rail` parameter (S1/S2, from `elements.html`'s `railVariants()`) are not in
the prototype and only exist here.
"""

from __future__ import annotations

import html
import json
import re
import statistics
from typing import Any

from teg_analysis.io import read_text_file

COMMENTARY_DIR = "data/commentary"

AVAILABLE_TEGS = (14, 16, 18)

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


def _match_storyline(subject: str, plan: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    """Match a heading fragment (post ' / ' split) to its plan slot by exact
    subject string. Returns (kicker, storyline_dict)."""
    if plan["trophy_storyline"]["subject"] == subject:
        return "TROPHY", plan["trophy_storyline"]
    if plan["jacket_storyline"]["subject"] == subject:
        return "GREEN JACKET", plan["jacket_storyline"]
    if plan["spoon_storyline"]["subject"] == subject:
        return "WOODEN SPOON", plan["spoon_storyline"]
    for storyline in plan["discovered_storylines"]:
        if storyline["subject"] == subject:
            return "SIDEBAR", storyline
    raise ValueError(f"heading fragment did not match any plan subject: {subject!r}")


def _parse_articles(
    article_sections: list[tuple[str, str]], plan: dict[str, Any]
) -> list[dict[str, Any]]:
    articles = []
    for heading, content in article_sections:
        fragments = [f.strip() for f in heading.split(" / ")]
        matches = [_match_storyline(f, plan) for f in fragments]

        kickers = sorted(
            {k for k, _ in matches}, key=lambda k: _KICKER_PRIORITY.index(k)
        )
        kicker = " & ".join(kickers)
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
                "headline": headline,
                "standfirst": standfirst,
                "paragraphs": paragraphs,
                "words": words,
                "compelling": compelling,
                "humour": humour,
                "is_lead": kicker == "TROPHY",
            }
        )

    leads = [a for a in articles if a["is_lead"]]
    if len(leads) != 1:
        raise ValueError(f"expected exactly 1 TROPHY lead article, got {len(leads)}")

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
        if not entry:
            return ""
        return f"{label}: {_player_name(entry[0])} ({entry[1]})"

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


def build_edition(teg: int) -> dict[str, Any]:
    """Read the two source artefacts for `teg` and return one edition dict.

    Raises FileNotFoundError (via `read_text_file`) if either artefact is
    missing — callers should only call this for `teg in AVAILABLE_TEGS`.
    """
    md = read_text_file(f"{COMMENTARY_DIR}/teg_{teg}_report_storylinefirst_styled.md")
    plan = json.loads(read_text_file(f"{COMMENTARY_DIR}/teg_{teg}_storyline_plan.json"))

    article_sections, appendix_md = _split_body_sections(md)

    results = _parse_results(md)
    standings = _parse_standings(appendix_md)
    _add_runners_up(results, standings)
    _add_value_split(results)

    return {
        "teg": teg,
        "title": _parse_title(md),
        "dateline": _parse_dateline(md),
        "results": results,
        "articles": _parse_articles(article_sections, plan),
        "standings": standings,
        "records": _parse_records(appendix_md),
    }


# ---------------------------------------------------------------------------
# Desktop renderer — a 1:1 port of composite.html's JS (arrangement "auto",
# fill "f1"). See that file's `render()`, `renderE1`, `renderE2`,
# `chooseArrangement`, `chooseSecondStory`.
# ---------------------------------------------------------------------------

E2_MIN_ARTICLES = 5
CLEAR_MARGIN = 2

# E3 (long sub-story full width, after a 2-up row) fires when there are
# exactly 3 sub-articles and the longest is at least this many times the
# median of the other two's word counts. Measured on the three real editions
# (longest ÷ median-of-rest):
#   TEG 16: 430 / 273 / 250 words -> 1.64
#   TEG 18: 409 / 247 / 225 words -> 1.73
#   TEG 14: 289 / 249 / 232 / 220 words -> 1.20 (5 articles -> E2 regardless)
# 1.4 sits clear of TEG 14's 1.20 and well under TEG 16/18's ratios.
LONG_STORY_RATIO = 1.4


def _esc(s: Any) -> str:
    return html.escape("" if s is None else str(s), quote=True)


def _bold_spans(text: str) -> str:
    return re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", _esc(text))


def _paragraphs_html(paragraphs: list[str]) -> str:
    return "".join(f"<p>{_bold_spans(p)}</p>" for p in paragraphs)


def _masthead_html(edition: dict[str, Any]) -> str:
    d = edition["dateline"]
    return (
        '<header class="masthead"><div class="mh-row">'
        '<span class="wordmark">The TEG</span>'
        f'<span class="dateline">{_esc(d["teg"])} &middot; {_esc(d["venue"])} &middot; {_esc(d["year"])}</span>'
        '</div><div class="mh-rule"></div></header>'
    )


def _lead_head_html(lead: dict[str, Any]) -> str:
    standfirst = f'<p class="lead-standfirst">{_esc(lead["standfirst"])}</p>' if lead["standfirst"] else ""
    return (
        f'<p class="kicker">{_esc(lead["kicker"])}</p>'
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


def _rail_html(edition: dict[str, Any]) -> str:
    items = _result_items_html(edition)
    last = edition["standings"][-1]
    return (
        '<aside class="rail">'
        f'<div class="r5"><p class="r5-title">At a glance</p><ul class="r-list">{items}</ul></div>'
        '<div class="rail-standings">'
        f'<p class="sb-lab">Final &middot; Trophy</p><p class="sb-row">{_esc(last["trophy"])}</p>'
        f'<p class="sb-lab">Final &middot; Green Jacket</p><p class="sb-row">{_esc(last["jacket"])}</p>'
        "</div></aside>"
    )


def _results_strip_html(edition: dict[str, Any]) -> str:
    """S1's full-width results strip (`.r3`) — the same result lines as the
    S2 rail's R5 box, laid out in a row instead of a column."""
    return f'<div class="r3"><ul class="r-list">{_result_items_html(edition)}</ul></div>'


def _sub_card_html(a: dict[str, Any], extra: str = "") -> str:
    standfirst = f'<p class="sub-standfirst">{_esc(a["standfirst"])}</p>' if a["standfirst"] else ""
    cls = f" {extra}" if extra else ""
    return (
        f'<article class="sub-card{cls}">'
        f'<p class="kicker">{_esc(a["kicker"])}</p>'
        f'<h2 class="sub-headline">{_esc(a["headline"])}</h2>'
        f"{standfirst}"
        f'<div class="sub-body">{_paragraphs_html(a["paragraphs"])}</div></article>'
    )


def _appendix_html(edition: dict[str, Any]) -> str:
    rows = "".join(
        f'<tr><td>R{s["round"]}</td><td>{_esc(s["trophy"])}</td><td>{_esc(s["jacket"])}</td></tr>'
        for s in edition["standings"]
    )
    by: dict[str, list[str]] = {}
    order: list[str] = []
    for r in edition["records"]:
        if r["category"] not in by:
            by[r["category"]] = []
            order.append(r["category"])
        by[r["category"]].append(r["text"])
    recs = "".join(
        f'<div class="recs-group"><p class="recs-cat">{_esc(c)}</p><ul class="recs">'
        + "".join(f"<li>{_esc(t)}</li>" for t in by[c])
        + "</ul></div>"
        for c in order
    )
    return (
        '<section class="appendix">'
        '<div class="apx-standings"><h3 class="apx-h">Standings by round</h3>'
        '<div class="table-scroll"><table class="stab">'
        "<thead><tr><th>Rd</th><th>Trophy</th><th>Green Jacket</th></tr></thead>"
        f"<tbody>{rows}</tbody></table></div></div>"
        f'<div><h3 class="apx-h">Personal bests &amp; records</h3><div class="apx-records">{recs}</div></div>'
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


def choose_arrangement(edition: dict[str, Any]) -> str:
    """"e1" (classic front), "e2" (second lead) or "e3" (2-up row + a long
    sub-story full width) — the CSS class the caller puts on the `.paper`
    element, since the E1/E2/E3 rules are keyed on it."""
    articles = edition["articles"]
    if len(articles) >= E2_MIN_ARTICLES:
        return "e2"
    subs = [a for a in articles if not a["is_lead"]]
    if len(subs) == 3:
        by_words = sorted(a["words"] for a in subs)
        longest = by_words[-1]
        median_rest = statistics.median(by_words[:-1])
        if median_rest and longest >= LONG_STORY_RATIO * median_rest:
            return "e3"
    return "e1"


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


def _render_e1(
    edition: dict[str, Any], lead: dict[str, Any], subs: list[dict[str, Any]], rail: str = "s2"
) -> str:
    row = "".join(_sub_card_html(a) for a in subs[:3])
    overflow = "".join(_sub_card_html(a, "wide") for a in subs[3:])
    return (
        _masthead_html(edition)
        + _main_html(edition, lead, rail)
        + '<div class="deck-rule"></div>'
        + f'<div class="subs">{row}{overflow}</div>'
        + _appendix_html(edition)
    )


def _render_e2(
    edition: dict[str, Any], lead: dict[str, Any], subs: list[dict[str, Any]], rail: str = "s2"
) -> str:
    second = _choose_second_story(subs)
    rest = "".join(_sub_card_html(a) for a in subs if a is not second)
    second_html = _sub_card_html(second, "second") if second else ""
    rest_block = f'<div class="thin-rule"></div><div class="subs">{rest}</div>' if rest else ""
    return (
        _masthead_html(edition)
        + _main_html(edition, lead, rail)
        + '<div class="deck-rule"></div>'
        + f'<div class="second-lead">{second_html}</div>'
        + rest_block
        + _appendix_html(edition)
    )


def _render_e3(
    edition: dict[str, Any], lead: dict[str, Any], subs: list[dict[str, Any]], rail: str = "s2"
) -> str:
    """Two shorter subs in a 2-up row (existing compelling/humour order
    preserved), then the longest sub full width, after the row."""
    long_story = max(subs, key=lambda a: a["words"])
    shorter = [a for a in subs if a is not long_story]
    row = "".join(_sub_card_html(a) for a in shorter)
    long_html = _sub_card_html(long_story, "long")
    return (
        _masthead_html(edition)
        + _main_html(edition, lead, rail)
        + '<div class="deck-rule"></div>'
        + f'<div class="subs">{row}</div>'
        + '<div class="thin-rule"></div>'
        + f'<div class="long-lead">{long_html}</div>'
        + _appendix_html(edition)
    )


_RENDERERS = {"e1": _render_e1, "e2": _render_e2, "e3": _render_e3}


def render_desktop_html(edition: dict[str, Any], rail: str = "s2") -> str:
    """Render the `.paper` inner HTML for the desktop composite (auto/f1).

    `rail` is "s2" (default — results + final standings beside the lead) or
    "s1" (no rail — results as a full-width strip, standings only in the
    appendix); see `webapp/report_layout_prototypes/elements.html`'s
    `railVariants()`.
    """
    lead = next(a for a in edition["articles"] if a["is_lead"])
    subs = [a for a in edition["articles"] if not a["is_lead"]]
    arrangement = choose_arrangement(edition)
    renderer = _RENDERERS[arrangement]
    return renderer(edition, lead, subs, rail)
