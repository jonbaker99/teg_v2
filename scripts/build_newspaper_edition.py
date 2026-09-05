"""Deterministic parser: storyline-first report artefacts -> newspaper edition JSON.

Prototype-only tool for `webapp/report_layout_prototypes/` (see PLAN.md there).
No LLM call, no pipeline change. Reads, per TEG:

    data/commentary/teg_N_storyline_plan.json
    data/commentary/teg_N_report_storylinefirst_styled.md

and emits one "edition" dict (schema documented in PLAN.md). Run directly to
regenerate `webapp/report_layout_prototypes/editions.json`:

    python -m scripts.build_newspaper_edition

Also importable — `build_edition(teg)` returns a single edition dict, used by
the prototype-generation step to inline the same data into the HTML.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
COMMENTARY_DIR = REPO_ROOT / "data" / "commentary"
OUTPUT_PATH = REPO_ROOT / "webapp" / "report_layout_prototypes" / "editions.json"

TEGS = (14, 16, 18)

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

    The derived text is still weaker than a written headline — that remains the
    trial's finding (see PLAN.md). This only stops the weakness reading as a
    parser bug on the page.
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
    md_path = COMMENTARY_DIR / f"teg_{teg}_report_storylinefirst_styled.md"
    plan_path = COMMENTARY_DIR / f"teg_{teg}_storyline_plan.json"
    md = md_path.read_text(encoding="utf-8")
    plan = json.loads(plan_path.read_text(encoding="utf-8"))

    article_sections, appendix_md = _split_body_sections(md)

    edition = {
        "teg": teg,
        "title": _parse_title(md),
        "dateline": _parse_dateline(md),
        "results": _parse_results(md),
        "articles": _parse_articles(article_sections, plan),
        "standings": _parse_standings(appendix_md),
        "records": _parse_records(appendix_md),
    }
    return edition


def main() -> None:
    editions = [build_edition(teg) for teg in TEGS]
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(editions, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {OUTPUT_PATH} ({len(editions)} editions)")
    for edition in editions:
        print(f"\nTEG {edition['teg']}: {edition['title']}")
        print(f"  dateline: {edition['dateline']}")
        print(f"  results: {[r['label'] for r in edition['results']]}")
        for a in edition["articles"]:
            print(
                f"  [{a['kicker']}] {a['headline']!r} "
                f"(lead={a['is_lead']}, words={a['words']}, "
                f"compelling={a['compelling']}, humour={a['humour']})"
            )
        print(f"  standings rounds: {[s['round'] for s in edition['standings']]}")
        print(f"  records: {len(edition['records'])}")


if __name__ == "__main__":
    main()
