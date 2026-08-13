"""Component D3 — programmatic verification of a finished report against the data.

The pipeline had two assurance mechanisms and needed three:

- **D1, preventive rules** — `WRITER_SYSTEM`'s FAITHFULNESS block asks the model
  not to fabricate. Asking is not enforcing: the TEG 10 R3 arithmetic error was
  written while the arithmetic rule was already in the prompt.
- **D2, deterministic guarantees** — `render.py` injects standings and records so
  those facts bypass the writer entirely. Strong, but only covers what code emits.
- **D3, this module** — checks what the writer *did* produce against the source
  data, after the fact.

Scope is deliberately narrow: only rules that are **mechanically decidable**. Six
of `WRITER_SYSTEM`'s eleven faithfulness absolutes qualify; the rest
("Stableford vs Gross is not a paradox") need semantic judgement and stay in D1.
A check that needs a model to adjudicate does not belong here — it would trade a
false sense of coverage for real complexity.

Every check returns `Finding`s rather than raising. A report that trips one is
still readable; the point is that it can no longer ship *silently*, which is what
happened three times.

    from teg_analysis.reporting.verify import verify_report, format_findings
    findings = verify_report(14)
    print(format_findings(findings))

CLI:  python -m teg_analysis.reporting.verify 14
      python -m teg_analysis.reporting.verify --all
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

OUTPUT_DIR = "data/commentary"

# Words the tournament has no mechanism for. Every one of these traces to a real
# fabrication incident, not a hypothetical.
_BANNED_MECHANISMS = [
    ("countback", r"\bcountback\b"),
    ("tiebreaker", r"\btie[\s-]?break(?:er|ers)?\b"),
    ("playoff", r"\bplay[\s-]?off\b"),
    ("sudden death", r"\bsudden[\s-]death\b"),
]

# A TEG is four consecutive days. "A week" is the recurring slip.
_WEEK_PATTERNS = [
    ("'the week'", r"\bthe week\b"),
    ("'a week'", r"\ba week\b"),
    ("'all week'", r"\ball week\b"),
    ("'this week'", r"\bthis week\b"),
    ("'week-long'", r"\bweek[\s-]long\b"),
]

_WEEKDAYS = ("Monday", "Tuesday", "Wednesday", "Thursday",
             "Friday", "Saturday", "Sunday")

# Internal beat identifiers that must never reach prose.
_BEAT_ID_RE = re.compile(r"\b(?:b\d{2,3}|cr\d{2})\b")

# "five over par", "16 over par", "eight under par through six"
_NUMBER_WORDS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7,
    "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13,
    "fourteen": 14, "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18,
    "nineteen": 19, "twenty": 20, "thirty": 30, "forty": 40, "fifty": 50,
}


# A number, written as digits or words ("16", "five", "twenty five"). Built from
# _NUMBER_WORDS so the pattern and the parser can never drift apart. Anchoring
# the regex to real numerals (rather than any word) stops the match sliding onto
# the preceding word — "He was forty over par" must capture "forty", not "was forty".
_NUM_WORD = "|".join(sorted(_NUMBER_WORDS, key=len, reverse=True))
_NUM = rf"\d+|(?:{_NUM_WORD})(?:[\s-](?:{_NUM_WORD}))?"


@dataclass
class Finding:
    """One verification failure. `rule` is stable; `detail` is human-facing."""
    rule: str
    severity: str                 # 'error' | 'warning'
    detail: str
    excerpt: str = ""

    def __str__(self) -> str:
        tail = f"  …{self.excerpt}…" if self.excerpt else ""
        return f"[{self.severity.upper()}] {self.rule}: {self.detail}{tail}"


@dataclass
class ReportContext:
    """Everything the checks need, loaded once."""
    teg_num: int
    text: str
    players: set = field(default_factory=set)
    venue: dict = field(default_factory=dict)
    round_weekdays: dict = field(default_factory=dict)   # round -> weekday


def _excerpt(text: str, start: int, end: int, pad: int = 45) -> str:
    lo = max(0, start - pad)
    hi = min(len(text), end + pad)
    return text[lo:hi].replace("\n", " ").strip()


def _strip_code_and_tables(text: str) -> str:
    """Remove fenced code and markdown tables.

    The deterministic blocks (standings, records) are D2's output, not the
    writer's prose. Checking them would flag code for its own guarantees.
    """
    text = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
    lines = [ln for ln in text.splitlines() if not ln.lstrip().startswith("|")]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# The mechanical checks
# ---------------------------------------------------------------------------
def check_no_beat_ids(ctx: ReportContext) -> list[Finding]:
    """Internal beat identifiers (b07, cr01) must never appear in prose."""
    out = []
    for m in _BEAT_ID_RE.finditer(ctx.text):
        out.append(Finding(
            "no_beat_ids", "error",
            f"internal beat id {m.group(0)!r} appears in the prose",
            _excerpt(ctx.text, m.start(), m.end())))
    return out


_NEGATION_RE = re.compile(r"\b(no|not|never|without|nor|neither)\b", re.IGNORECASE)


def check_no_invented_mechanisms(ctx: ReportContext) -> list[Finding]:
    """TEG has no countback, tiebreaker or playoff. Naming one is fabrication.

    A *negated* mention ("no countback was required; none ever is") is not a
    fabrication — it is the writer stating the rule correctly. Those are
    downgraded to warnings rather than suppressed: the phrasing is still worth a
    human glance, but it must not read as the same failure as inventing one.
    """
    out = []
    body = _strip_code_and_tables(ctx.text)
    for label, pattern in _BANNED_MECHANISMS:
        for m in re.finditer(pattern, body, flags=re.IGNORECASE):
            lead = body[max(0, m.start() - 40):m.start()]
            negated = bool(_NEGATION_RE.search(lead))
            out.append(Finding(
                "no_invented_mechanisms",
                "warning" if negated else "error",
                (f"{label!r} mentioned but negated — verify the phrasing reads as "
                 f"'this does not exist'" if negated
                 else f"{label!r} does not exist in TEG"),
                _excerpt(body, m.start(), m.end())))
    return out


def check_not_a_week(ctx: ReportContext) -> list[Finding]:
    """A TEG is four consecutive days, never 'a week'."""
    out = []
    body = _strip_code_and_tables(ctx.text)
    for label, pattern in _WEEK_PATTERNS:
        for m in re.finditer(pattern, body, flags=re.IGNORECASE):
            out.append(Finding(
                "not_a_week", "error",
                f"{label} — a TEG is 4 consecutive days",
                _excerpt(body, m.start(), m.end())))
    return out


def check_only_participants(ctx: ReportContext) -> list[Finding]:
    """Only players who actually played this TEG may appear in the prose.

    Compares against the full historical roster, so an unrelated capitalised
    word is never mistaken for a player. Observed failure: a non-participant
    added to the player-by-player summary closing list.
    """
    if not ctx.players:
        return []
    from teg_analysis.core.data_loader import load_all_data
    df = load_all_data(exclude_teg_50=True, exclude_incomplete_tegs=False)
    everyone = {" ".join(w.capitalize() for w in str(p).split())
                for p in df["Player"].unique()}
    outsiders = everyone - ctx.players
    body = _strip_code_and_tables(ctx.text)
    out = []
    for person in sorted(outsiders):
        surname = person.split()[-1]
        # Match the full name, or a bare surname that is unambiguous — a surname
        # shared with a participant (Baker) proves nothing on its own.
        if any(surname == p.split()[-1] for p in ctx.players):
            pattern = re.escape(person)
        else:
            pattern = rf"\b{re.escape(surname)}\b"
        m = re.search(pattern, body)
        if m:
            out.append(Finding(
                "only_participants", "error",
                f"{person} did not play TEG {ctx.teg_num} but appears in the prose",
                _excerpt(body, m.start(), m.end())))
    return out


def check_weekdays(ctx: ReportContext) -> list[Finding]:
    """Weekday names must match `venue.rounds[i].weekday` for this TEG.

    Any weekday not among the TEG's actual round days is invented. This does not
    police *placement* (which round's section a weekday sits in) — that needs
    section attribution and would produce false positives; naming a day the
    tournament never touched is the failure that got caught in the wild.
    """
    if not ctx.round_weekdays:
        return []
    valid = set(ctx.round_weekdays.values())
    body = _strip_code_and_tables(ctx.text)
    out = []
    for day in _WEEKDAYS:
        if day in valid:
            continue
        for m in re.finditer(rf"\b{day}\b", body):
            out.append(Finding(
                "weekdays", "error",
                f"{day} is not a round day of TEG {ctx.teg_num} "
                f"(actual: {', '.join(sorted(valid))})",
                _excerpt(body, m.start(), m.end())))
    return out


def _word_to_int(token: str) -> Optional[int]:
    token = token.strip().lower().replace("-", " ")
    if token.isdigit():
        return int(token)
    if token in _NUMBER_WORDS:
        return _NUMBER_WORDS[token]
    parts = token.split()
    if len(parts) == 2 and parts[0] in _NUMBER_WORDS and parts[1] in _NUMBER_WORDS:
        tens, units = _NUMBER_WORDS[parts[0]], _NUMBER_WORDS[parts[1]]
        if tens >= 20 and units < 10:
            return tens + units
    return None


def check_arithmetic_claims(ctx: ReportContext) -> list[Finding]:
    """Find over/under-par totals asserted across a stretch and re-derive them.

    This is the check the TEG 10 R3 error would have failed. It is deliberately
    conservative: it only fires on claims of the form "<n> over par through
    <m> holes" where BOTH numbers are recoverable, because those are the ones
    that can be checked without guessing which holes the writer meant.

    Reported as warnings, not errors — the parse can misread an unusual phrasing,
    and a false error is worse than a flagged sentence for a human to glance at.
    """
    body = _strip_code_and_tables(ctx.text)
    pattern = re.compile(
        rf"\b({_NUM})\s+(over|under)\s+par\s+"
        rf"(?:through|across|in|over)\s+(?:the\s+)?(?:first\s+|opening\s+)?({_NUM})\b",
        flags=re.IGNORECASE)
    out = []
    for m in pattern.finditer(body):
        total = _word_to_int(m.group(1))
        holes = _word_to_int(m.group(3))
        if total is None or holes is None:
            continue
        if holes < 1 or holes > 18:
            continue
        # A stretch of `holes` holes cannot exceed ~6 shots dropped per hole, nor
        # be under par by more than ~2 per hole. Anything outside that is a
        # transcription or arithmetic failure regardless of which holes are meant.
        if m.group(2).lower() == "over" and total > holes * 6:
            out.append(Finding(
                "arithmetic_claims", "warning",
                f"{total} over par through {holes} holes is not achievable "
                f"(max ~{holes * 6})",
                _excerpt(body, m.start(), m.end())))
        elif m.group(2).lower() == "under" and total > holes * 2:
            out.append(Finding(
                "arithmetic_claims", "warning",
                f"{total} under par through {holes} holes is not achievable "
                f"(max ~{holes * 2})",
                _excerpt(body, m.start(), m.end())))
    return out


def check_swing_claims(ctx: ReportContext) -> list[Finding]:
    """Re-derive 'an N-point swing' where the two endpoints are stated nearby.

    Catches the exact TEG 10 R3 shape: "began five points clear and finished
    eleven adrift. That is a fourteen-point swing" — where 5 + 11 = 16, not 14.
    """
    body = _strip_code_and_tables(ctx.text)
    out = []
    # The unit ("points") is optional on either endpoint: real reports write
    # "five points clear … eleven adrift", dropping the noun the second time.
    sentence_window = re.compile(
        r"([\w-]+)\s+(?:points?\s+)?(clear|ahead|adrift|behind)"
        r"(.{0,240}?)"
        r"([\w-]+)\s+(?:points?\s+)?(clear|ahead|adrift|behind)"
        r"(.{0,160}?)"
        r"([\w-]+)[\s-]point\s+swing",
        flags=re.IGNORECASE | re.DOTALL)
    for m in sentence_window.finditer(body):
        start_val = _word_to_int(m.group(1))
        end_val = _word_to_int(m.group(4))
        claimed = _word_to_int(m.group(7))
        if None in (start_val, end_val, claimed):
            continue
        start_dir = m.group(2).lower() in ("clear", "ahead")
        end_dir = m.group(5).lower() in ("clear", "ahead")
        # Opposite sides of the leader → the swing is the sum; same side → the
        # difference.
        expected = start_val + end_val if start_dir != end_dir else abs(start_val - end_val)
        if claimed != expected:
            out.append(Finding(
                "swing_claims", "error",
                f"stated {claimed}-point swing, but {start_val} "
                f"{'clear' if start_dir else 'adrift'} → {end_val} "
                f"{'clear' if end_dir else 'adrift'} is a {expected}-point swing",
                _excerpt(body, m.start(), m.end(), pad=0)))
    return out


CHECKS = (
    check_no_beat_ids,
    check_no_invented_mechanisms,
    check_not_a_week,
    check_only_participants,
    check_weekdays,
    check_arithmetic_claims,
    check_swing_claims,
)


# ---------------------------------------------------------------------------
# Entry points
# ---------------------------------------------------------------------------
def load_context(teg_num: int, text: Optional[str] = None,
                 round_num: Optional[int] = None) -> ReportContext:
    """Assemble the data each check needs. `text` overrides reading from disk."""
    from teg_analysis.io import read_text_file
    from teg_analysis.core.data_loader import load_all_data
    from teg_analysis.reporting.venue import build_venue_context

    if text is None:
        infix = f"round_{round_num}_" if round_num else ""
        path = f"{OUTPUT_DIR}/teg_{teg_num}_{infix}report_final.md"
        try:
            text = read_text_file(path)
        except Exception:
            with open(path) as f:
                text = f.read()

    df = load_all_data(exclude_teg_50=True, exclude_incomplete_tegs=False)
    players = {" ".join(w.capitalize() for w in str(p).split())
               for p in df[df["TEGNum"] == teg_num]["Player"].unique()}
    try:
        venue = build_venue_context(teg_num)
        weekdays = {r["round"]: r["weekday"] for r in venue.get("rounds", [])
                    if r.get("weekday")}
    except Exception:
        venue, weekdays = {}, {}
    if round_num:
        weekdays = {k: v for k, v in weekdays.items() if k == round_num}
    return ReportContext(teg_num=teg_num, text=text, players=players,
                         venue=venue, round_weekdays=weekdays)


def verify_report(teg_num: int, text: Optional[str] = None,
                  round_num: Optional[int] = None) -> list[Finding]:
    """Run every mechanical check. Returns findings, errors first."""
    ctx = load_context(teg_num, text=text, round_num=round_num)
    findings: list[Finding] = []
    for check in CHECKS:
        findings.extend(check(ctx))
    findings.sort(key=lambda f: (f.severity != "error", f.rule))
    return findings


def format_findings(findings: list[Finding], teg_num: Optional[int] = None) -> str:
    label = f"TEG {teg_num}" if teg_num is not None else "report"
    if not findings:
        return f"✓ {label}: all {len(CHECKS)} mechanical checks passed"
    errors = sum(1 for f in findings if f.severity == "error")
    warnings = len(findings) - errors
    head = f"✗ {label}: {errors} error(s), {warnings} warning(s)"
    return "\n".join([head] + [f"  {f}" for f in findings])


def main(argv: Optional[list] = None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description="Verify TEG report(s) against the data.")
    ap.add_argument("tegs", nargs="*", type=int, help="TEG numbers (default: --all)")
    ap.add_argument("--all", action="store_true", help="verify every published report")
    ap.add_argument("--rounds", action="store_true", help="also verify round reports")
    args = ap.parse_args(argv)

    import glob
    import os

    targets: list[tuple] = []
    if args.all or not args.tegs:
        for path in sorted(glob.glob(f"{OUTPUT_DIR}/teg_*_report_final.md")):
            base = os.path.basename(path)
            m = re.match(r"teg_(\d+)_report_final\.md$", base)
            if m:
                targets.append((int(m.group(1)), None))
        if args.rounds:
            for path in sorted(glob.glob(f"{OUTPUT_DIR}/teg_*_round_*_report_final.md")):
                m = re.match(r"teg_(\d+)_round_(\d+)_report_final\.md$",
                             os.path.basename(path))
                if m:
                    targets.append((int(m.group(1)), int(m.group(2))))
    else:
        targets = [(t, None) for t in args.tegs]

    total_errors = 0
    for teg_num, round_num in sorted(targets, key=lambda t: (t[0], t[1] or 0)):
        label = f"TEG {teg_num}" + (f" R{round_num}" if round_num else "")
        try:
            findings = verify_report(teg_num, round_num=round_num)
        except FileNotFoundError:
            print(f"– {label}: no report_final.md")
            continue
        total_errors += sum(1 for f in findings if f.severity == "error")
        print(format_findings(findings, teg_num=None).replace("report:", f"{label}:")
              .replace("✓ report", f"✓ {label}"))
    return 1 if total_errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
