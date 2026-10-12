"""
Antar - the period a question names
===================================
One place that turns the time words in a question into a date window.

The offline router used to understand exactly one thing about time: a four-digit year.
Everything else an officer writes was either reduced to that year or lost:

    "thefts in March 2023"          -> all of 2023
    "from January to March 2023"    -> all of 2023
    "murders on 15 August 2023"     -> all of 2023
    "kidnapping cases since 2020"   -> 2020 only
    "murder cases before 2019"      -> 2019 only (the opposite of what was asked)
    "thefts in the last 2 years"    -> every year on record, and the 2 became a row limit

Each of those returned a confident, tagged answer to a different question. `find_span`
reads the window that was actually asked for; nothing here guesses - a phrase it cannot
read returns None, and `mentions_time` lets the caller tell the officer that a period was
named and not applied.
"""
from __future__ import annotations

import calendar
import re
from dataclasses import dataclass
from datetime import date, timedelta

_MONTHS = {"jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6, "jul": 7, "aug": 8,
           "sep": 9, "oct": 10, "nov": 11, "dec": 12}
_M = (r"(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|june?|july?|aug(?:ust)?|"
      r"sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)")
# A year standing on its own: not part of an FIR number (104/2028), a plate (KA-02-M-2028),
# a decimal or a time ("2030 hrs").
_Y = r"(?<![\w/.-])(20\d\d)(?![\w/]|-\w*[a-z])(?!\s*(?:hrs?|hours)\b)"
_SEP = r"\s*(?:to|and|-|–|—|through|thru|till|until|upto|up to)\s*"
_ORD = {"first": 1, "1st": 1, "second": 2, "2nd": 2, "third": 3, "3rd": 3, "fourth": 4, "4th": 4}
_ACT_BEFORE = re.compile(r"\bact,?\s*(?:of\s*)?$", re.I)      # "Information Technology Act 2000"

# Words that compare two periods rather than span them: "2022 vs 2023" is not "2022 to 2023".
COMPARE_RE = re.compile(r"\b(compare|comparison|compared|vs\.?|versus|against|growth|growing|grew|"
                        r"change[ds]?|increase[ds]?|decrease[ds]?|rise|rose|fell|fall|difference)\b", re.I)

# Time that has not happened yet, said without a date.
FUTURE_RE = re.compile(r"\b(tomorrow|day after tomorrow|next\s+(?:year|month|week|quarter|decade|"
                       r"\d+\s+(?:days?|weeks?|months?|years?))|coming\s+(?:year|months?|weeks?|days?)|"
                       r"upcoming\s+(?:year|months?|weeks?)|in the future)\b", re.I)

# Relative periods the router already resolves by keyword (heuristics._PERIOD_WORDS).
_RELATIVE_RE = re.compile(r"\b(today|yesterday|this (?:week|month|year|quarter)|last (?:week|month|year|quarter)|"
                          r"previous (?:week|month|year|quarter)|past (?:week|month|year)|year to date|"
                          r"so far this year|(?:last|past|previous)\s+\d+\s+(?:hours?|days?|weeks?|months?|years?)|"
                          r"day before yesterday)\b", re.I)


@dataclass(frozen=True)
class Span:
    date_from: str          # ISO, inclusive
    date_to: str            # ISO, inclusive
    kind: str               # day | month | months | quarter | half | year | years | since | before | after | last_n
    label: str              # how the answer names it: "in March 2023"
    phrase: str             # the words in the question it was read from


def _mnum(word: str) -> int:
    return _MONTHS[word[:3].lower()]


def _mname(m: int) -> str:
    return calendar.month_name[m]


def _last(y: int, m: int) -> int:
    return calendar.monthrange(y, m)[1]


def _iso(y: int, m: int, d: int) -> str:
    return date(y, m, d).isoformat()


def _back_months(d: date, n: int) -> date:
    y, m = d.year, d.month - n
    while m <= 0:
        y, m = y - 1, m + 12
    return date(y, m, min(d.day, _last(y, m)))


def _quarter(y: int, q: int, phrase: str, prefix: str = "") -> Span:
    m0 = 3 * (q - 1) + 1
    return Span(_iso(y, m0, 1), _iso(y, m0 + 2, _last(y, m0 + 2)), "quarter",
                f"in Q{q} {y}, {_mname(m0)} to {_mname(m0 + 2)}" if not prefix
                else f"{prefix}, {_mname(m0)} to {_mname(m0 + 2)} {y}", phrase)


def find_span(text: str, today: date, first_year: int = 2016) -> Span | None:
    """The date window a question names, or None when it names none this can read.

    Most specific first: a day, then a run of months, a quarter, a half-year, a month, a run
    of years, an open-ended "since / before / after", a count of days-weeks-months-years
    back from today, a bare month, and last a single year.
    """
    t = " ".join((text or "").replace("’", "'").split())
    low = t.lower()

    def ok_year(m: re.Match, group: int | str = 1) -> bool:
        return not _ACT_BEFORE.search(low[:m.start(group)])

    # ── a single day ──
    if (m := re.search(r"(?<![\w/.-])(20\d\d)-(\d{2})-(\d{2})(?![\w-])", low)):
        try:
            d = date(int(m[1]), int(m[2]), int(m[3]))
            return Span(d.isoformat(), d.isoformat(), "day", f"on {d.day} {d.strftime('%b %Y')}", m[0])
        except ValueError:
            pass
    if (m := re.search(r"(?<![\w/.-])(\d{1,2})[/.-](\d{1,2})[/.-](20\d\d)(?![\w/-])", low)):
        try:                                     # day first, as dates are written in India
            d = date(int(m[3]), int(m[2]), int(m[1]))
            return Span(d.isoformat(), d.isoformat(), "day", f"on {d.day} {d.strftime('%b %Y')}", m[0])
        except ValueError:
            pass
    for pat, gd, gm, gy in ((rf"\b(\d{{1,2}})(?:st|nd|rd|th)?\s+(?:of\s+)?{_M}\.?,?\s+(20\d\d)\b", 1, 2, 3),
                            (rf"\b{_M}\.?\s+(\d{{1,2}})(?:st|nd|rd|th)?,?\s+(20\d\d)\b", 2, 1, 3)):
        if (m := re.search(pat, low)):
            try:
                d = date(int(m[gy]), _mnum(m[gm]), int(m[gd]))
                return Span(d.isoformat(), d.isoformat(), "day", f"on {d.day} {d.strftime('%b %Y')}", m[0])
            except ValueError:
                pass

    # ── a run of months in one year: "January to March 2023" ──
    if (m := re.search(rf"\b{_M}\.?{_SEP}{_M}\.?,?\s+(?:of\s+)?(20\d\d)\b", low)):
        a, b, y = _mnum(m[1]), _mnum(m[2]), int(m[3])
        if a <= b:
            return Span(_iso(y, a, 1), _iso(y, b, _last(y, b)), "months",
                        f"from {_mname(a)} to {_mname(b)} {y}", m[0])

    # ── a quarter ──
    if (m := re.search(r"\bq([1-4])\s*(?:of\s+|,\s*|-\s*)?(20\d\d)\b", low)) or \
            (m := re.search(r"\b(first|second|third|fourth|1st|2nd|3rd|4th)\s+quarter\s+(?:of\s+)?(20\d\d)\b", low)):
        q = int(m[1]) if m[1].isdigit() else _ORD[m[1]]
        return _quarter(int(m[2]), q, m[0])
    if (m := re.search(r"\b(last|previous|this|current)\s+quarter\b", low)):
        q = (today.month - 1) // 3 + 1
        y = today.year
        if m[1] in ("last", "previous"):
            q, y = (4, y - 1) if q == 1 else (q - 1, y)
            return _quarter(y, q, m[0], prefix="in the last quarter")
        return _quarter(y, q, m[0], prefix="in this quarter")

    # ── a half-year ──
    if (m := re.search(r"\b(first|second|1st|2nd)\s+half\s+(?:of\s+)?(20\d\d)\b", low)) or \
            (m := re.search(r"\bh([12])\s*(?:of\s+|-\s*)?(20\d\d)\b", low)):
        h = int(m[1]) if m[1].isdigit() else _ORD[m[1]]
        y = int(m[2])
        return (Span(_iso(y, 1, 1), _iso(y, 6, 30), "half", f"in the first half of {y}", m[0]) if h == 1
                else Span(_iso(y, 7, 1), _iso(y, 12, 31), "half", f"in the second half of {y}", m[0]))

    # ── a month of a year: "March 2023" ──
    if (m := re.search(rf"\b{_M}\.?,?\s+(?:of\s+)?(20\d\d)\b", low)):
        mo, y = _mnum(m[1]), int(m[2])
        return Span(_iso(y, mo, 1), _iso(y, mo, _last(y, mo)), "month", f"in {_mname(mo)} {y}", m[0])

    # ── a festival of a year: "during Dasara 2023" ──
    if (m := re.search(r"\b(dasara|dussehra|dasehra|deepavali|diwali|ganesha chaturthi|ganesh chaturthi|"
                       r"ugadi|sankranti|ramzan|ramadan|eid)\s+(?:of\s+)?(20\d\d)\b", low)):
        try:
            from app.services import events as _ev
            key = {"dasara": "dasara", "dussehra": "dasara", "dasehra": "dasara", "deepavali": "deepavali",
                   "diwali": "deepavali", "ganesha chaturthi": "ganesha", "ganesh chaturthi": "ganesha",
                   "ugadi": "ugadi", "sankranti": "sankranti", "ramzan": "ramzan", "ramadan": "ramzan",
                   "eid": "ramzan"}[m[1]]
            e = _ev.EVENTS[key]
            anchor = next((d for d in _ev.occurrences(key) if d.year == int(m[2])), None)
            if anchor:
                a, b = anchor - timedelta(days=e.before), anchor + timedelta(days=e.after)
                return Span(a.isoformat(), b.isoformat(), "event",
                            f"during {e.name} {anchor.year}, {a.day} {a.strftime('%b')} to {b.day} {b.strftime('%b')}", m[0])
        except Exception:
            pass

    # ── a run of years: "between 2021 and 2023", "2019-2021" ──
    if (m := re.search(rf"\b(?:between|from|during|in|over|for)?\s*(20\d\d){_SEP}(20\d\d)\b", low)):
        a, b = int(m[1]), int(m[2])
        if a < b and ok_year(m, 1):
            return Span(_iso(a, 1, 1), _iso(b, 12, 31), "years", f"from {a} to {b}", m[0].strip())

    # ── open-ended ──
    if (m := re.search(r"\b(?:since|from)\s+(20\d\d)\s+onwards?\b", low)) or \
            (m := re.search(r"\bsince\s+(20\d\d)\b", low)) or (m := re.search(r"\b(20\d\d)\s+onwards?\b", low)):
        y = int(m[1])
        return Span(_iso(y, 1, 1), today.isoformat(), "since", f"since {y}", m[0])
    if (m := re.search(r"\bafter\s+(20\d\d)\b", low)):
        y = int(m[1])
        return Span(_iso(y + 1, 1, 1), today.isoformat(), "after", f"after {y}", m[0])
    if (m := re.search(r"\b(?:before|prior to|earlier than)\s+(20\d\d)\b", low)):
        y = int(m[1])
        return Span(_iso(first_year, 1, 1), _iso(y - 1, 12, 31), "before", f"before {y}", m[0])
    if (m := re.search(r"\b(?:until|till|up to|upto|through|by the end of)\s+(20\d\d)\b", low)):
        y = int(m[1])
        return Span(_iso(first_year, 1, 1), _iso(y, 12, 31), "before", f"up to the end of {y}", m[0])

    # ── counted back from today: "the last 2 years", "past 10 days" ──
    if (m := re.search(r"\b(?:last|past|previous)\s+(\d{1,3})\s+(day|week|month|year)s?\b", low)):
        n, unit = int(m[1]), m[2]
        if n >= 1:
            start = (today - timedelta(days=n) if unit == "day" else today - timedelta(weeks=n) if unit == "week"
                     else _back_months(today, n) if unit == "month" else _back_months(today, 12 * n))
            return Span(start.isoformat(), today.isoformat(), "last_n",
                        f"in the last {n} {unit}{'' if n == 1 else 's'}", m[0])

    # ── a month with no year: the latest one that has happened ──
    if (m := re.search(rf"\b(?:in|during|for|of)\s+{_M}\b(?!\s*,?\s*\d)", low)):
        mo = _mnum(m[1])
        y = today.year if mo <= today.month else today.year - 1
        return Span(_iso(y, mo, 1), _iso(y, mo, _last(y, mo)), "month",
                    f"in {_mname(mo)} {y}, the latest {_mname(mo)} on record", m[0])

    # ── "in '23" ──
    if (m := re.search(r"(?:\bin|\bof|\bfor|\bduring)\s+'(\d\d)\b", low)):
        y = 2000 + int(m[1])
        return Span(_iso(y, 1, 1), _iso(y, 12, 31), "year", f"in {y}", m[0])

    # ── a single year ──
    for m in re.finditer(_Y, low):
        if ok_year(m, 1):
            y = int(m[1])
            return Span(_iso(y, 1, 1), _iso(y, 12, 31), "year", f"in {y}", m[0])
    return None


def mentions_time(text: str, today: date, first_year: int = 2016) -> str | None:
    """The time phrase in a question, whether or not it could be turned into a window."""
    sp = find_span(text, today, first_year)
    if sp:
        return sp.phrase.strip()
    low = (text or "").lower()
    m = _RELATIVE_RE.search(low) or FUTURE_RE.search(low)
    return m.group(0) if m else None
