"""
Vermont OPR monthly discipline reports -> LCMHC name list for the decision downloader.

Why this exists. Every conduct decision in the Board of Allied Mental Health
Practitioners folder is an image scan with no text layer, and the file name
does not say which profession the person holds. OPR's monthly discipline
reports are text-native PDFs that list every action across all professions,
one entry per action, with the licence type spelled out. Reading those
reports settles the profession (and the name order) for most decisions from
2019 on without OCR-ing anything.

What it does (three passes):

  1. DISCOVER + DOWNLOAD  every monthly report PDF linked from
        https://sos.vermont.gov/opr/complaints-conduct-discipline/monthly-discipline-reports/
     into  monthly_reports\  next to this script (files already present are
     skipped). Verified live 2026-09-18: the page links all 92 PDFs directly,
     at .../monthly_discipline_reports/YYYY/monthly_discipline_reports_YYYY-MM.pdf.
     If the page ever lists fewer months than expected, the script also
     probes the predictable URL for every month from 2019-01 to today.

  2. PARSE  every report with PyMuPDF into one row per action:
        monthly_actions_all.csv   all professions
        lcmhc_actions.csv         Board of Allied Mental Health rows only
                                  (LCMHC, LMFT, psychoanalyst, non-licensed
                                  psychotherapist), with license_type filled in
                                  so the excluded ones are visible.
     Layouts seen 2019-01 to 2026-08 (all handled):
        2019-2023  "First Last, City, State" at the left, profession in a
                   right-hand column on the same line, "date; action" or
                   "date: action" (2020-2021: sometimes no date) below.
        2024-2025  same, but names printed "Last, First, City, ST".
        2026-      bullet, "Last, First, City, ST", then
                   "Profession License Suspended on 1/13/2026" on one line.

  3. MATCH  the report rows against manifest.csv (the decisions folder
     listing written by download_vermont_orders.py --list-only) by name,
     tolerant of swapped name order, case, punctuation, hyphens, apostrophes,
     middle initials and nicknames, and write name_match.csv with one row per
     folder PDF and a proposed category:
        counselor   the name matches an LCMHC action
        drop        the name matches only another allied-board profession
        unmatched   no usable report row (pre-2019 dockets, or the names differ)
     download_vermont_orders.py reads name_match.csv in its classify pass.

download_vermont_orders.py runs all of this itself as its pass 0, so this
script only needs to be run by hand to redo the name list on its own.

Usage (from this folder):
    py build_vermont_name_list.py               # download new reports, parse, match
    py build_vermont_name_list.py --offline     # parse and match the cached reports only
    py build_vermont_name_list.py --debug       # also write debug\parsed_YYYY-MM.txt per report

Needs: requests, beautifulsoup4, pymupdf   (py -m pip install requests beautifulsoup4 pymupdf)
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import difflib
import re
import sys
import time
import unicodedata
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

INDEX_URL = "https://sos.vermont.gov/opr/complaints-conduct-discipline/monthly-discipline-reports/"
# Predictable file URL, used to probe for months the index page does not link.
FILE_URL = ("https://outside.vermont.gov/dept/sos/office_professional_regulation/"
            "discipline_resources_reports/monthly_discipline_reports/{year}/monthly_discipline_reports_{ym}.pdf")
FIRST_MONTH = (2019, 1)

HERE = Path(__file__).resolve().parent
REPORTS_DIR = HERE / "monthly_reports"
MANIFEST_PATH = HERE / "manifest.csv"
ALL_ACTIONS_PATH = HERE / "monthly_actions_all.csv"
LCMHC_ACTIONS_PATH = HERE / "lcmhc_actions.csv"
NAME_MATCH_PATH = HERE / "name_match.csv"
DEBUG_DIR = HERE / "debug"

PAUSE_SECONDS = 1.5
RETRIES = 3
TIMEOUT = 90
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
}

# --------------------------------------------------------------------------- #
# Layout constants (points; page is 612 wide)
# --------------------------------------------------------------------------- #
RIGHT_COLUMN_X = 250.0     # text starting right of this is the profession column (2019-2025 layout)
ROW_TOLERANCE = 5.0        # words whose vertical midpoints are within this many points are on the same row
PIECE_GAP = 18.0           # a horizontal gap wider than this splits a row into separate pieces
COLUMN_TOLERANCE = 2.0     # a word starting this close to the report's profession column starts a new piece
FOOTNOTE = re.compile(r"^\d\s+[A-Z][a-z]+\s")   # "1 Act 6 and Act 91, emergency legislation ..." at a page foot
ENTRY_GAP = 19.5           # a vertical gap wider than this starts a new entry (lines are ~14-15 apart)
BULLET_CHARS = re.compile(r"[\uE000-\uF8FF•▪●\uF0B7]")

MONTHS = ("January", "February", "March", "April", "May", "June", "July", "August",
          "September", "October", "November", "December")
INTRO_END = re.compile(r"docketclerk|sos\.OPR@|difficulty accessing|Docket Clerk", re.I)
INTRO_START = re.compile(r"took the following actions", re.I)
SKIP_ROW = re.compile(
    r"^(Page\s*\|\s*\d+|\d+ Main Street.*|802-828-\d+.*|Secretary of State|Office of Professional Regulation|"
    r"Monthly Discipline Report|(" + "|".join(MONTHS) + r")\s+\d{4})$", re.I)
DATE_NUMERIC = re.compile(r"(\d{1,2})/(\d{1,2})/+(\d{2,4})")
DATE_WORDY = re.compile(r"(" + "|".join(MONTHS) + r")\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+(\d{4})", re.I)
STARTS_WITH_DATE = re.compile(r"^\s*(\d{1,2}/\d{1,2}/|(" + "|".join(MONTHS) + r")\s+\d{1,2})", re.I)
# Words that begin the action part of a 2026-style "Profession License Suspended on date" line.
# "Licensed" and "Certified" (profession words) do not match "Licenses?" / "Certifications?".
ACTION_START = re.compile(
    r"\b(Licenses?|Certifications?|Registrations?|Conditions?|Case|Applications?|Renewal|Monetary|Civil|"
    r"Administrative|Reprimand\w*|Warned|Warning|Suspen\w*|Revo\w*|Surrender\w*|Condition\w*|Fine|Penalty|"
    r"Voluntar\w*|Petition|Denied|Reinstat\w*|Stipulation|Summary|Probation\w*|Dismiss\w*)\b")
NAME_LIKE = re.compile(r"^[A-Z][^,;:]{0,60},\s*\S")
STATE_NAMES = {
    "alabama": "AL", "alaska": "AK", "arizona": "AZ", "arkansas": "AR", "california": "CA", "colorado": "CO",
    "connecticut": "CT", "delaware": "DE", "florida": "FL", "georgia": "GA", "hawaii": "HI", "idaho": "ID",
    "illinois": "IL", "indiana": "IN", "iowa": "IA", "kansas": "KS", "kentucky": "KY", "louisiana": "LA",
    "maine": "ME", "maryland": "MD", "massachusetts": "MA", "michigan": "MI", "minnesota": "MN",
    "mississippi": "MS", "missouri": "MO", "montana": "MT", "nebraska": "NE", "nevada": "NV",
    "new hampshire": "NH", "new jersey": "NJ", "new mexico": "NM", "new york": "NY", "north carolina": "NC",
    "north dakota": "ND", "ohio": "OH", "oklahoma": "OK", "oregon": "OR", "pennsylvania": "PA",
    "rhode island": "RI", "south carolina": "SC", "south dakota": "SD", "tennessee": "TN", "texas": "TX",
    "utah": "UT", "vermont": "VT", "virginia": "VA", "washington": "WA", "west virginia": "WV",
    "wisconsin": "WI", "wyoming": "WY", "district of columbia": "DC", "puerto rico": "PR",
}
STATE_TAIL = re.compile(
    r"^(?P<city>.*?)[\s,]*\b(?P<state>[A-Z]{2}|" + "|".join(re.escape(s) for s in STATE_NAMES) + r")\.?\s*$", re.I)

# Board of Allied Mental Health Practitioners licence types, in priority order.
ALLIED_RULES = [
    ("LCMHC", re.compile(r"clinical mental health counsel|\bLCMHC\b|mental health counselor", re.I)),
    ("LMFT", re.compile(r"marriage\s*(and|&)\s*family|\bLMFT\b", re.I)),
    ("Psychoanalyst", re.compile(r"psychoanaly", re.I)),
    ("Non-licensed psychotherapist", re.compile(r"psychotherap", re.I)),
]
ALLIED_BOARD = "Board of Allied Mental Health Practitioners"

# Name normalisation for matching
SUFFIXES = {"jr", "sr", "ii", "iii", "iv", "phd", "md", "lcmhc", "lmft", "ma", "ms", "msw", "docket", "dockets"}
NICKNAMES = {
    "bob": "robert", "rob": "robert", "bobby": "robert", "bill": "william", "will": "william", "billy": "william",
    "mike": "michael", "jim": "james", "jimmy": "james", "liz": "elizabeth", "beth": "elizabeth",
    "betsy": "elizabeth", "kate": "katherine", "katie": "katherine", "kathy": "katherine", "cathy": "catherine",
    "chris": "christopher", "matt": "matthew", "dan": "daniel", "danny": "daniel", "tom": "thomas",
    "joe": "joseph", "steve": "steven", "dave": "david", "jen": "jennifer", "jenny": "jennifer",
    "andy": "andrew", "drew": "andrew", "tony": "anthony", "nick": "nicholas", "greg": "gregory",
    "jon": "jonathan", "ben": "benjamin", "sam": "samuel", "alex": "alexander", "pat": "patricia",
    "patty": "patricia", "peggy": "margaret", "meg": "margaret", "sue": "susan", "suzy": "susan",
    "deb": "deborah", "debbie": "deborah", "ed": "edward", "ted": "edward", "rick": "richard",
    "rich": "richard", "dick": "richard", "ron": "ronald", "don": "donald", "ken": "kenneth",
    "tim": "timothy", "becky": "rebecca", "abby": "abigail", "jess": "jessica", "josh": "joshua",
    "jake": "jacob", "zach": "zachary", "nate": "nathan", "fred": "frederick", "larry": "lawrence",
    "terry": "terrence", "jerry": "gerald", "vicky": "victoria", "vicki": "victoria", "ginny": "virginia",
}

session = requests.Session()
session.headers.update(HEADERS)


def fetch(url: str, binary: bool = False):
    last_err = None
    for attempt in range(1, RETRIES + 1):
        try:
            resp = session.get(url, timeout=TIMEOUT)
            if resp.status_code == 404:
                return None
            resp.raise_for_status()
            return resp.content if binary else resp.text
        except Exception as exc:  # noqa: BLE001
            last_err = exc
            if attempt < RETRIES:
                time.sleep(PAUSE_SECONDS * attempt)
    raise RuntimeError(f"{url}: {last_err}")


# --------------------------------------------------------------------------- #
# Pass 1: discover and download the monthly reports
# --------------------------------------------------------------------------- #

def month_range(first: tuple[int, int], last: tuple[int, int]) -> list[str]:
    y, m = first
    out = []
    while (y, m) <= last:
        out.append(f"{y:04d}-{m:02d}")
        m += 1
        if m > 12:
            y, m = y + 1, 1
    return out


def discover_report_urls() -> dict[str, str]:
    """{'2026-08': url} for every monthly report PDF linked from the index page (and its year sub-pages)."""
    found: dict[str, str] = {}
    to_visit = [INDEX_URL]
    visited: set[str] = set()
    while to_visit:
        page = to_visit.pop(0)
        if page in visited:
            continue
        visited.add(page)
        try:
            html = fetch(page)
        except Exception as exc:  # noqa: BLE001
            print(f"  index page failed: {page} ({str(exc)[:100]})")
            continue
        if html is None:
            continue
        soup = BeautifulSoup(html, "html.parser")
        for a in soup.find_all("a", href=True):
            href = urljoin(page, a["href"].strip())
            m = re.search(r"monthly[_\-]discipline[_\-]reports?[_\-](\d{4})-(\d{2})\.pdf", href, re.I)
            if m:
                found.setdefault(f"{m.group(1)}-{m.group(2)}", href)
                continue
            # Year sub-pages, if the site ever splits the list ("2024 reports", ".../monthly-discipline-reports/2023/")
            text = a.get_text(" ", strip=True)
            if ("monthly-discipline-reports" in href.lower() and href.rstrip("/") != INDEX_URL.rstrip("/")
                    and re.search(r"\b20\d\d\b", text + href) and href not in visited and not href.lower().endswith(".pdf")):
                to_visit.append(href)
        time.sleep(PAUSE_SECONDS)
    return found


def download_reports(offline: bool) -> tuple[list[Path], list[str]]:
    """Return (cached report paths, months that could not be found)."""
    REPORTS_DIR.mkdir(exist_ok=True)
    missing: list[str] = []
    if not offline:
        print("Pass 1: monthly discipline reports")
        urls = discover_report_urls()
        print(f"  index page lists {len(urls)} monthly report PDFs"
              + (f" ({min(urls)} to {max(urls)})" if urls else ""))
        today = dt.date.today()
        # The report for a month is posted after the month ends, so expect up to last month.
        last = (today.year, today.month - 1) if today.month > 1 else (today.year - 1, 12)
        expected = month_range(FIRST_MONTH, last)
        downloaded = 0
        for ym in expected:
            target = REPORTS_DIR / f"monthly_discipline_reports_{ym}.pdf"
            if target.exists() and target.stat().st_size > 0:
                continue
            url = urls.get(ym) or FILE_URL.format(year=ym[:4], ym=ym)
            probing = ym not in urls
            try:
                data = fetch(url, binary=True)
            except Exception as exc:  # noqa: BLE001
                print(f"  FAIL {ym}: {str(exc)[:120]}")
                missing.append(ym)
                time.sleep(PAUSE_SECONDS)
                continue
            time.sleep(PAUSE_SECONDS)
            if data is None or not data.startswith(b"%PDF"):
                if not probing:
                    print(f"  FAIL {ym}: linked file is missing or not a PDF ({url})")
                missing.append(ym)
                continue
            target.write_bytes(data)
            downloaded += 1
            print(f"  saved {target.name} ({len(data):,} bytes){' (probed URL, not linked from the page)' if probing else ''}")
        print(f"  downloaded {downloaded} new report(s); {len(list(REPORTS_DIR.glob('*.pdf')))} cached in {REPORTS_DIR}")
    paths = sorted(REPORTS_DIR.glob("monthly_discipline_reports_*.pdf"))
    if not paths:
        raise SystemExit(f"No monthly reports in {REPORTS_DIR}. Run without --offline first.")
    return paths, missing


# --------------------------------------------------------------------------- #
# Pass 2: parse the reports
# --------------------------------------------------------------------------- #

def report_rows(path: Path) -> list[dict]:
    """
    Group the words of every page into visual rows, and each row into pieces
    separated by a wide horizontal gap. Returns [{'page', 'y', 'pieces': [(x0, text), ...]}].
    """
    try:
        import pymupdf  # PyMuPDF >= 1.24
    except ImportError:
        try:
            import fitz as pymupdf  # older PyMuPDF
        except ImportError as exc:  # pragma: no cover
            raise SystemExit("PyMuPDF is required: py -m pip install pymupdf") from exc
    raw_rows: list[tuple[int, float, list]] = []
    with pymupdf.open(path) as doc:
        for page_no, page in enumerate(doc, 1):
            words = [w for w in page.get_text("words") if BULLET_CHARS.sub("", w[4]).strip() or BULLET_CHARS.search(w[4])]
            words.sort(key=lambda w: ((w[1] + w[3]) / 2, w[0]))
            current: list = []
            current_mid = None
            for w in words:
                mid = (w[1] + w[3]) / 2
                if current and abs(mid - current_mid) > ROW_TOLERANCE:
                    raw_rows.append((page_no, min(x[1] for x in current), current))
                    current = []
                if not current:
                    current_mid = mid
                current.append(w)
            if current:
                raw_rows.append((page_no, min(x[1] for x in current), current))
    # The profession column: the most common x where a wide-gap piece starts right of the margin.
    # (Not used for the bulleted 2026 layout, which has no second column.)
    starts: dict[float, int] = {}
    bulleted = any(BULLET_CHARS.search(w[4]) for _, _, words in raw_rows for w in words)
    for _, _, words in ([] if bulleted else raw_rows):
        for p in _split_words(words, None):
            if p[0] >= RIGHT_COLUMN_X:
                starts[round(p[0], 1)] = starts.get(round(p[0], 1), 0) + 1
    column_x = max(starts, key=starts.get) if starts else None
    return [{"page": pg, "y": y, "pieces": [p for p in _split_words(words, column_x) if p[1] or p[2]]}
            for pg, y, words in raw_rows]


def _split_words(words: list, column_x: float | None) -> list[tuple[float, str, bool]]:
    """Split one row's words into pieces at wide gaps and at the profession column."""
    words = sorted(words, key=lambda w: w[0])
    pieces: list[tuple[float, str, bool]] = []
    piece_words: list = []
    for w in words:
        at_column = column_x is not None and abs(w[0] - column_x) <= COLUMN_TOLERANCE
        if piece_words and (w[0] - piece_words[-1][2] > PIECE_GAP or at_column):
            pieces.append(_piece(piece_words))
            piece_words = []
        piece_words.append(w)
    if piece_words:
        pieces.append(_piece(piece_words))
    return pieces


def _piece(words: list) -> tuple[float, str, bool]:
    raw = " ".join(w[4] for w in words)
    bullet = bool(BULLET_CHARS.search(raw))
    text = re.sub(r"\s+", " ", BULLET_CHARS.sub(" ", raw)).strip()
    return words[0][0], text, bullet


def split_entries(rows: list[dict]) -> list[dict]:
    """Group rows into one entry per action. Each entry: name (str), left (list), right (list), bullet (bool)."""
    # Skip the page-1 heading and intro paragraph: everything up to the last intro line.
    first_page = [i for i, r in enumerate(rows) if r["page"] == 1]
    start = 0
    intro_seen = False
    for i in first_page[:25]:
        text = " ".join(p[1] for p in rows[i]["pieces"])
        if INTRO_START.search(text):
            intro_seen = True
        if intro_seen and INTRO_END.search(text):
            start = i + 1
    # 2026 layout: every entry starts with a bullet glyph, and the lines inside an
    # entry are further apart than in the older layouts, so in a bulleted report
    # only a bullet starts a new entry.
    bulleted_report = any(p[2] for r in rows for p in r["pieces"])
    entries: list[dict] = []
    current: dict | None = None
    prev_row: dict | None = None
    footnote_page = 0
    for row in rows[start:]:
        pieces = row["pieces"]
        text_all = " ".join(p[1] for p in pieces)
        if not text_all.strip() or SKIP_ROW.match(text_all.strip()):
            continue
        if FOOTNOTE.match(text_all.strip()):
            footnote_page = row["page"]          # skip the rest of this page
        if row["page"] == footnote_page:
            continue
        left = [p for p in pieces if p[0] < RIGHT_COLUMN_X or bulleted_report]
        right = [p for p in pieces if p[0] >= RIGHT_COLUMN_X and not bulleted_report]
        bullet = any(p[2] for p in pieces)
        left_text = " ".join(p[1] for p in left).strip()
        new_entry = False
        if bullet:
            new_entry = True
        elif bulleted_report:
            new_entry = current is None and bool(left)
        elif current is None:
            new_entry = bool(left)
        elif left:
            page_break = prev_row is not None and row["page"] != prev_row["page"]
            gap = (row["y"] - prev_row["y"]) if prev_row is not None and not page_break else 0.0
            continues_action = STARTS_WITH_DATE.match(left_text) or (
                not NAME_LIKE.match(left_text) and (page_break or ACTION_START.match(left_text)))
            if page_break:
                new_entry = bool(NAME_LIKE.match(left_text)) and not STARTS_WITH_DATE.match(left_text)
            elif gap > ENTRY_GAP:
                new_entry = not (continues_action and not current["left"][1:])
        if new_entry:
            current = {"page": row["page"], "y": row["y"], "left": [], "right": [], "bullet": bullet,
                       "raw": []}
            entries.append(current)
        if current is not None:
            current["left"].extend(p[1] for p in left)
            current["right"].extend(p[1] for p in right)
            current["raw"].append(text_all)
        prev_row = row
    return entries


def parse_date(text: str) -> tuple[str, str]:
    """Return (iso_date, matched_text) for the first date in text, or ('', '')."""
    m = DATE_NUMERIC.search(text)
    if m:
        mo, d, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if y < 100:
            y += 2000
        try:
            return dt.date(y, mo, d).isoformat(), m.group(0)
        except ValueError:
            return "", m.group(0)
    m = DATE_WORDY.search(text)
    if m:
        mo = [x.lower() for x in MONTHS].index(m.group(1).lower()) + 1
        try:
            return dt.date(int(m.group(3)), mo, int(m.group(2))).isoformat(), m.group(0)
        except ValueError:
            return "", m.group(0)
    return "", ""


def split_name_location(text: str) -> tuple[str, str, str, str, str]:
    """
    'Lewis, Gretchen, Derby Line, VT'  -> ('Lewis', 'Gretchen', 'Derby Line', 'VT', 'Last, First')
    'Bridget Coburn, East Montpelier, Vermont' -> ('Coburn', 'Bridget', 'East Montpelier', 'VT', 'First Last')
    """
    tokens = [t.strip() for t in text.split(",")]
    tokens = [t for t in tokens if t]
    if not tokens:
        return "", "", "", "", ""
    head = tokens[0]
    if " " in head or len(tokens) == 1:
        words = head.split()
        last, first = words[-1], " ".join(words[:-1])
        order = "First Last"
        rest = tokens[1:]
    else:
        last = head
        first = tokens[1] if len(tokens) > 1 else ""
        order = "Last, First"
        rest = tokens[2:]
    city, state = "", ""
    if rest:
        tail = ", ".join(rest)
        m = STATE_TAIL.match(tail)
        if m and m.group("state"):
            st = m.group("state")
            state = STATE_NAMES.get(st.lower(), st.upper())
            city = m.group("city").strip(" ,")
        else:
            city = tail
    return last, first, city, state, order


def allied_type(license_text: str) -> str:
    for code, rx in ALLIED_RULES:
        if rx.search(license_text):
            return code
    return ""


def clean_action(text: str, date_text: str) -> str:
    t = text.replace(date_text, " ") if date_text else text
    t = re.sub(r"\s+", " ", t).strip(" ;:,.-")
    t = re.sub(r"\s+(on|effective|was|is|as of)\s*$", "", t, flags=re.I).strip(" ;:,.-")
    return t


def parse_report(path: Path, debug: bool = False) -> tuple[list[dict], list[str]]:
    """Return (rows, warnings) for one monthly report."""
    ym = path.stem[-7:]
    rows = report_rows(path)
    entries = split_entries(rows)
    out: list[dict] = []
    warnings: list[str] = []
    for e in entries:
        left, right = e["left"], e["right"]
        if not left:
            warnings.append(f"{ym}: entry with no left-hand text: {' | '.join(right)}")
            continue
        name_text = left[0]
        # 2020-02 style "Edward Thairu, Essex Jct., VT 2/20/2020": a date on the name line
        name_date_iso, name_date_txt = parse_date(name_text)
        if name_date_txt:
            name_text = name_text.replace(name_date_txt, "").strip(" ,;:")
        if e["bullet"]:
            body = re.sub(r"\s+", " ", " ".join(left[1:] + right)).strip()
            m = ACTION_START.search(body)
            license_text = body[: m.start()].strip(" ,;:-") if m else body
            action_part = body[m.start():] if m else ""
            if not license_text:
                # "Conditions Removed from Registered Nurse License on 3/11/2026"
                m2 = re.search(r"\bfrom\s+(?:the\s+)?(.+?)\s+(License|Certification|Registration|Roster)\b", action_part, re.I)
                if m2:
                    license_text = m2.group(1).strip()
        else:
            license_text = re.sub(r"\s+", " ", " ".join(right)).strip(" ,;:-")
            action_part = " ".join(left[1:])
        date_iso, date_txt = parse_date(action_part)
        if not date_iso and name_date_iso:
            date_iso, date_txt = name_date_iso, ""
        action_text = clean_action(action_part, date_txt)
        last, first, city, state, order = split_name_location(name_text)
        allied = allied_type(license_text)
        note = []
        if not license_text:
            note.append("no profession text")
        if not date_iso:
            note.append("no action date")
        if STARTS_WITH_DATE.match(name_text):
            note.append("entry starts with a date (name missing)")
        out.append({
            "report_month": ym,
            "last_name": last,
            "first_name": first,
            "city": city,
            "state": state,
            "license_type": allied or license_text,
            "action_date": date_iso,
            "action_text": action_text,
            "board": ALLIED_BOARD if allied else "",
            "raw_line": " | ".join(e["raw"]),
            "name_as_printed": name_text,
            "name_order_printed": order,
            "license_type_as_printed": license_text,
            "allied_group": allied,
            "source_report": path.name,
            "page": e["page"],
            "parse_note": "; ".join(note),
        })
    if not out:
        warnings.append(f"{ym}: no entries parsed")
    if debug:
        DEBUG_DIR.mkdir(exist_ok=True)
        lines = [f"{r['last_name']}, {r['first_name']} | {r['city']}, {r['state']} | {r['license_type_as_printed']} | "
                 f"{r['action_date']} | {r['action_text']} | {r['parse_note']}" for r in out]
        (DEBUG_DIR / f"parsed_{ym}.txt").write_text("\n".join(lines), encoding="utf-8")
    return out, warnings


ACTION_FIELDS = ["report_month", "last_name", "first_name", "city", "state", "license_type", "action_date",
                 "action_text", "board", "raw_line", "name_as_printed", "name_order_printed",
                 "license_type_as_printed", "allied_group", "source_report", "page", "parse_note"]


def write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


# --------------------------------------------------------------------------- #
# Pass 3: match against manifest.csv
# --------------------------------------------------------------------------- #

def norm_tokens(text: str) -> list[str]:
    t = unicodedata.normalize("NFKD", text or "")
    t = "".join(c for c in t if not unicodedata.combining(c)).lower()
    t = t.replace("'", "").replace("’", "")
    t = re.sub(r"[^a-z0-9]+", " ", t)
    toks = [x for x in t.split() if len(x) > 1 and x not in SUFFIXES and not any(ch.isdigit() for ch in x)]
    return [NICKNAMES.get(x, x) for x in toks]


def norm_name(text: str) -> str:
    return " ".join(norm_tokens(text))


def name_keys(last: str, first: str) -> dict:
    lt, ft = norm_tokens(last), norm_tokens(first)
    return {"last": " ".join(lt), "first": " ".join(ft), "first1": ft[0] if ft else "",
            "last1": lt[0] if lt else "", "tokens": frozenset(lt + ft), "full": " ".join(sorted(lt + ft))}


def compare(m: dict, r: dict) -> str:
    """Return 'exact name', 'swapped name', 'fuzzy' or ''."""
    if not m["tokens"] or not r["tokens"]:
        return ""
    if m["last"] == r["last"] and m["first"] and m["first"] == r["first"]:
        return "exact name"
    if m["last"] == r["first"] and m["first"] == r["last"] and m["first"]:
        return "swapped name"
    if len(m["tokens"]) >= 2 and m["tokens"] == r["tokens"]:
        return "fuzzy"
    same_last = m["last"] == r["last"] or (m["last1"] and m["last1"] == r["last1"]) or (
        m["last"] and (m["last"] in r["tokens"] or r["last"] in m["tokens"]))
    if same_last and m["first1"] and r["first1"]:
        a, b = m["first1"], r["first1"]
        if a == b or (len(min(a, b, key=len)) >= 3 and (a.startswith(b) or b.startswith(a))) \
                or difflib.SequenceMatcher(None, a, b).ratio() >= 0.8:
            return "fuzzy"
        # "Kornegay, Tasha" in the file name, "Kornegay, Holland Tasha" in the report
        if set(m["first"].split()) & set(r["first"].split()):
            return "fuzzy"
    # Swapped and fuzzy first name ("Kristen" file, "Kristin" report, order unknown)
    if m["last"] == r["first1"] and m["first1"] and difflib.SequenceMatcher(None, m["first1"], r["last"]).ratio() >= 0.8:
        return "fuzzy"
    if len(m["tokens"]) >= 2 and len(r["tokens"]) >= 2 and \
            difflib.SequenceMatcher(None, m["full"], r["full"]).ratio() >= 0.9:
        return "fuzzy"
    return ""


def load_manifest() -> list[dict]:
    if not MANIFEST_PATH.exists():
        return []
    with MANIFEST_PATH.open(encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def dockets_of(row: dict) -> set[str]:
    s = (row.get("dockets_all") or row.get("docket") or "")
    return {d.strip().lower() for d in s.split(";") if d.strip()}


METHOD_ORDER = {"docket": 0, "exact name": 1, "swapped name": 2, "fuzzy": 3}
MATCH_FIELDS = ["source_file", "docket", "matched", "matched_license_type", "matched_action_dates",
                "matched_name_as_printed", "match_method", "proposed_category", "match_note",
                "manifest_name", "report_last_name", "report_first_name", "matched_report_months",
                "matched_action_text", "other_name_matches"]


def match_manifest(actions: list[dict], manifest: list[dict]) -> list[dict]:
    keyed = [(name_keys(a["last_name"], a["first_name"]), a) for a in actions]
    out: list[dict] = []
    for mrow in manifest:
        mk = name_keys(mrow.get("last_name", ""), mrow.get("first_name", ""))
        my_dockets = dockets_of(mrow)
        hits: list[tuple[str, dict]] = []
        for rk, a in keyed:
            method = ""
            a_docket = (a.get("docket") or "").strip().lower()
            if a_docket and a_docket in my_dockets:
                method = "docket"
            else:
                method = compare(mk, rk)
            if method:
                hits.append((method, a))
        hits.sort(key=lambda h: (METHOD_ORDER[h[0]], h[1]["action_date"] or h[1]["report_month"]))
        allied_hits = [h for h in hits if h[1]["allied_group"]]
        other_hits = [h for h in hits if not h[1]["allied_group"]]
        note: list[str] = []
        docket_year = re.match(r"^(20\d\d)-", mrow.get("docket") or "")
        if docket_year and int(docket_year.group(1)) < FIRST_MONTH[0]:
            docket_year = None                     # 2018-20, 2012-503: before the reports begin
        if allied_hits:
            best_method = allied_hits[0][0]
            types = []
            for _, a in allied_hits:
                if a["allied_group"] not in types:
                    types.append(a["allied_group"])
            if "LCMHC" in types:
                category = "counselor"
            else:
                category = "drop"
            if len(types) > 1:
                note.append("several licence types in the reports: " + ", ".join(types))
            if best_method == "fuzzy":
                note.append("fuzzy name match, check")
            if docket_year:
                years = [a["action_date"][:4] for _, a in allied_hits if a["action_date"]]
                if years and max(years) < docket_year.group(1):
                    note.append(f"all matched actions precede docket year {docket_year.group(1)}")
            top = allied_hits[0][1]
            out.append({
                "source_file": mrow["source_file"],
                "docket": mrow.get("docket", ""),
                "matched": "yes",
                "matched_license_type": "; ".join(types),
                "matched_action_dates": "; ".join(dict.fromkeys(a["action_date"] or f"(no date, {a['report_month']})"
                                                                for _, a in allied_hits)),
                "matched_name_as_printed": "; ".join(dict.fromkeys(a["name_as_printed"] for _, a in allied_hits)),
                "match_method": best_method,
                "proposed_category": category,
                "match_note": "; ".join(note),
                "manifest_name": f"{mrow.get('last_name', '')}, {mrow.get('first_name', '')}",
                "report_last_name": top["last_name"],
                "report_first_name": top["first_name"],
                "matched_report_months": "; ".join(dict.fromkeys(a["report_month"] for _, a in allied_hits)),
                "matched_action_text": "; ".join(dict.fromkeys(a["action_text"] for _, a in allied_hits)),
                "other_name_matches": "; ".join(dict.fromkeys(
                    f"{a['name_as_printed']} ({a['license_type']}, {a['report_month']})" for _, a in other_hits)),
            })
        else:
            if other_hits:
                note.append("name matches only non-allied-board rows (" + ", ".join(dict.fromkeys(
                    a["license_type"] for _, a in other_hits)) + "); not used")
            elif docket_year is None:
                note.append(f"pre-{FIRST_MONTH[0]} docket: before the monthly reports begin")
            else:
                note.append("no report row with this name")
            out.append({
                "source_file": mrow["source_file"],
                "docket": mrow.get("docket", ""),
                "matched": "no",
                "matched_license_type": "",
                "matched_action_dates": "",
                "matched_name_as_printed": "",
                "match_method": "",
                "proposed_category": "unmatched",
                "match_note": "; ".join(note),
                "manifest_name": f"{mrow.get('last_name', '')}, {mrow.get('first_name', '')}",
                "report_last_name": "",
                "report_first_name": "",
                "matched_report_months": "",
                "matched_action_text": "",
                "other_name_matches": "; ".join(dict.fromkeys(
                    f"{a['name_as_printed']} ({a['license_type']}, {a['report_month']})" for _, a in other_hits)),
            })
    return out


# --------------------------------------------------------------------------- #

def build(offline: bool = False, debug: bool = False, manifest: list[dict] | None = None,
          manifest_path: Path = MANIFEST_PATH) -> tuple[list[dict], list[dict]]:
    """
    Run the three passes and return (actions, matches). `manifest` is the folder listing to
    match against (rows shaped like manifest.csv); when None it is read from manifest_path.
    download_vermont_orders.py calls this as its pass 0, so one run does everything.
    """
    paths, missing = download_reports(offline)

    print(f"\nPass 2: parsing {len(paths)} reports")
    actions: list[dict] = []
    warnings: list[str] = []
    per_month: dict[str, int] = {}
    for p in paths:
        try:
            rows, warns = parse_report(p, debug=debug)
        except Exception as exc:  # noqa: BLE001
            warnings.append(f"{p.name}: could not parse ({exc})")
            continue
        actions.extend(rows)
        warnings.extend(warns)
        per_month[p.stem[-7:]] = len(rows)
    write_csv(ALL_ACTIONS_PATH, actions, ACTION_FIELDS)
    allied = [a for a in actions if a["allied_group"]]
    write_csv(LCMHC_ACTIONS_PATH, allied, ACTION_FIELDS)
    lcmhc = [a for a in allied if a["allied_group"] == "LCMHC"]
    dates = sorted(a["action_date"] for a in lcmhc if a["action_date"])
    print(f"  {len(actions)} actions in {len(per_month)} reports "
          f"({min(per_month)} to {max(per_month)}); "
          f"{len(allied)} allied mental health rows, of which {len(lcmhc)} LCMHC"
          + (f" ({dates[0]} to {dates[-1]})" if dates else ""))
    by_type: dict[str, int] = {}
    for a in allied:
        by_type[a["allied_group"]] = by_type.get(a["allied_group"], 0) + 1
    print("  allied rows by type: " + ", ".join(f"{k}: {v}" for k, v in sorted(by_type.items())))
    empty = [ym for ym, n in per_month.items() if n == 0]
    if missing:
        print(f"  months not found on the site: {', '.join(missing)}")
    if empty:
        print(f"  reports with no entries parsed: {', '.join(empty)}")
    no_date = sum(1 for a in actions if not a["action_date"])
    no_prof = sum(1 for a in actions if not a["license_type"])
    print(f"  rows without an action date: {no_date}; rows without a profession: {no_prof}")
    for w in warnings[:40]:
        print(f"  warning: {w}")
    print(f"  wrote {ALL_ACTIONS_PATH.name} and {LCMHC_ACTIONS_PATH.name}")

    if manifest is None:
        if not manifest_path.exists():
            print(f"\nPass 3 skipped: {manifest_path} not found. Run download_vermont_orders.py --list-only first.")
            return actions, []
        with manifest_path.open(encoding="utf-8") as fh:
            manifest = list(csv.DictReader(fh))
    print(f"\nPass 3: matching {len(manifest)} folder PDFs")
    matches = match_manifest(actions, manifest)
    write_csv(NAME_MATCH_PATH, matches, MATCH_FIELDS)
    cats: dict[str, int] = {}
    methods: dict[str, int] = {}
    for m in matches:
        cats[m["proposed_category"]] = cats.get(m["proposed_category"], 0) + 1
        if m["match_method"]:
            methods[m["match_method"]] = methods.get(m["match_method"], 0) + 1
    print("  proposed categories: " + ", ".join(f"{k}: {v}" for k, v in sorted(cats.items())))
    print("  match methods: " + (", ".join(f"{k}: {v}" for k, v in sorted(methods.items(), key=lambda kv: METHOD_ORDER[kv[0]])) or "none"))
    fuzzy = [m for m in matches if m["match_method"] == "fuzzy"]
    if fuzzy:
        print(f"  {len(fuzzy)} fuzzy match(es) to eyeball in {NAME_MATCH_PATH.name}:")
        for m in fuzzy:
            print(f"    {m['source_file']}  ->  {m['matched_name_as_printed']}  [{m['matched_license_type']}]")
    print(f"  wrote {NAME_MATCH_PATH}")
    return actions, matches


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--offline", action="store_true", help="do not touch the website; parse the cached reports only")
    ap.add_argument("--debug", action="store_true", help="write one parsed_YYYY-MM.txt per report under debug\\")
    ap.add_argument("--manifest", default=str(MANIFEST_PATH), help="folder listing to match against (default manifest.csv)")
    args = ap.parse_args(argv)
    build(offline=args.offline, debug=args.debug, manifest_path=Path(args.manifest))
    return 0


if __name__ == "__main__":
    sys.exit(main())
