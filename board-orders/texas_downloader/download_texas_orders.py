"""
Texas Behavioral Health Executive Council (BHEC) agreed-order downloader
(Licensed Professional Counselors).

BHEC does not publish a disciplinary list. Its licensee lookup (the HPC
"datamart") is protected by Google reCAPTCHA Enterprise and refuses scripted
searches. What BHEC does publish, every quarter, is the packet of "Public
Meeting Materials" for each Council meeting, and since October 2021 that
packet has carried a section "Agreed Orders and Dismissals for the
fiscal-quarter" containing the signed Agreed Order of every licensee
disciplined that quarter, sorted by profession (verified 2026-09-18). The
packets are linked from one page and need no login, form or browser:

  pass 0  licensee list   https://www.bhec.texas.gov/csv/LPC.csv
          (every CURRENT LPC and LPC Associate, with a Discpl_Actn flag; used
          only to cross-check names and fill in license numbers)
  pass 1  meeting index   https://bhec.texas.gov/tbhec/important-dates/past-council-meeting-dates/
          one "Agenda & Public Meeting Materials" link per Council meeting
          (October 2021 to date; .zip since January 2023, one big .pdf before)
  pass 2  each packet is downloaded once (25 to 115 MB), then the agreed
          orders are pulled out of it:
          - .zip packets, February 2024 on: one PDF per licensee in a folder
            named LPC / LMFT / PSY / SW  ->  the LPC files are copied out;
          - .zip packets, January to October 2023: one combined PDF per
            profession ("LPC Q3 FY23 Agreed Orders.pdf") with a bookmark per
            licensee  ->  split into one PDF per bookmark (PyMuPDF);
          - .pdf packets, October 2021 to October 2022: the orders are pages
            of the packet, with a bookmark section "3.e ... LPC Agreed Orders"
            and a bookmark per licensee  ->  split the same way. A packet
            with no LPC bookmark section (May 2022) is saved whole to the
            review folder for a manual split.
          LMFT, psychology and social-work orders are never written; each is
          still recorded in manifest.csv with the reason.

Files land in the state folder one level above this script, named
    "Lastname, Firstname FY25Q4 2025-10-14.pdf"
(the fiscal quarter the order belongs to, then the Council meeting date; the
order's own signature date is inside the scan). A second order for the same
person in the same quarter becomes "... (2).pdf". Files already present are
skipped, so the script can be re-run safely. Every outcome goes to
download_log.csv; packet listings are cached in packet_index.json so a
re-run does not download packets whose orders are already on disk.

Usage (from this folder):
    py download_texas_orders.py                  # list, then write the LPC orders
    py download_texas_orders.py --list-only      # build manifest.csv only, write no orders
                                                 # (the packets still have to be downloaded)
    py download_texas_orders.py --keep-packets   # keep the downloaded packets in downloader\packets\
    py download_texas_orders.py --refresh        # ignore packet_index.json and re-read every packet
    py download_texas_orders.py --text-check     # after downloading: count PDFs with a text layer

Needs: requests and PyMuPDF   (py -m pip install requests pymupdf).
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import re
import sys
import time
import zipfile
from datetime import date
from pathlib import Path
from urllib.parse import urljoin

import requests

# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #

MEETINGS_URL = "https://bhec.texas.gov/tbhec/important-dates/past-council-meeting-dates/"
LPC_CSV_URL = "https://www.bhec.texas.gov/csv/LPC.csv"

HERE = Path(__file__).resolve().parent            # ...\state_data\Texas\downloader
STATE_FOLDER = HERE.parent                         # ...\state_data\Texas
REVIEW_FOLDER = STATE_FOLDER / "review"            # unsplit packets and combined files
PACKETS_DIR = HERE / "packets"                     # downloaded packets (deleted unless --keep-packets)
MANIFEST_PATH = HERE / "manifest.csv"
LOG_PATH = HERE / "download_log.csv"
INDEX_PATH = HERE / "packet_index.json"

PAUSE_SECONDS = 1.5
RETRIES = 3
TIMEOUT = 300
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.9",
}

# Profession tokens as they appear in folder names, combined-file names and
# bookmark section titles. Anything else goes to "review" rather than being guessed.
PROFESSION_MAP = {
    "LPC": ("counselor", "LPC"),
    "LMFT": ("drop", "marriage & family therapy (LMFT)"),
    "MFT": ("drop", "marriage & family therapy (MFT)"),
    "PSY": ("drop", "psychology (PSY)"),
    "SW": ("drop", "social work (SW)"),
}

MONTHS = {m: i for i, m in enumerate(
    ["January", "February", "March", "April", "May", "June", "July",
     "August", "September", "October", "November", "December"], 1)}

DATE_TEXT = re.compile(r"\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2}),\s+(\d{4})\b")
PACKET_LINK = re.compile(r'<a[^>]+href="([^"]+\.(?:zip|pdf))"[^>]*>(.*?)</a>', re.I | re.S)
FY_QUARTER = re.compile(r"(?:FY\s?(?:20)?(\d{2})\s*Q(\d))|(?:Q(\d)\s*FY\s?(?:20)?(\d{2}))|(?:FY\s?(?:20)?(\d{2})\s*(\d)(?:st|nd|rd|th)\s*Q)|(?:(\d)(?:st|nd|rd|th)\s*(?:Qtr|Quarter)\s*FY\s?(?:20)?(\d{2}))", re.I)
CASE_NUMBER = re.compile(r"\b(\d{4}-\d{2}-\d{4}|\d{4}-\d{5})\b")
NOISE_WORDS = re.compile(r"\b(AO|Agreed|Order|Orders|Ratified|Executed|Dr|Final|Signed|Copy)\b\.?", re.I)
ILLEGAL_FILENAME = re.compile(r'[\\/:*?"<>|]+')
SUFFIXES = {"JR", "JR.", "SR", "SR.", "II", "III", "IV"}
PARTICLES = {"DE", "DEL", "DELA", "DE LA", "DA", "DI", "DU", "LA", "LE", "VAN", "VON", "ST", "ST.", "MC", "MAC"}

session = requests.Session()
session.headers.update(HEADERS)


# --------------------------------------------------------------------------- #
# Fetching
# --------------------------------------------------------------------------- #

def fetch(url: str, binary: bool = False, stream_to: Path | None = None):
    """GET with retries. Returns text, bytes, or (when stream_to is given) the saved path."""
    last_err = None
    for attempt in range(1, RETRIES + 1):
        try:
            if stream_to is not None:
                tmp = stream_to.with_suffix(stream_to.suffix + ".part")
                with session.get(url, timeout=TIMEOUT, stream=True) as resp:
                    resp.raise_for_status()
                    with tmp.open("wb") as fh:
                        for chunk in resp.iter_content(1 << 20):
                            fh.write(chunk)
                tmp.replace(stream_to)
                return stream_to
            resp = session.get(url, timeout=TIMEOUT)
            resp.raise_for_status()
            return resp.content if binary else resp.text
        except Exception as exc:  # noqa: BLE001
            last_err = exc
            if attempt < RETRIES:
                time.sleep(PAUSE_SECONDS * attempt)
    raise RuntimeError(f"{url}: {last_err}")


# --------------------------------------------------------------------------- #
# Pass 0: current licensee list (name cross-check, license numbers)
# --------------------------------------------------------------------------- #

def load_licensee_list() -> dict:
    """{"by_name": {(LAST, FIRST): [rows]}, "first": Counter, "last": Counter} from BHEC's daily
    LPC.csv. The counters say how often a word is used as a first or a last name among the
    43,000-odd current licensees; they settle the order of file names written 'Howson Heather'.
    Empty dict if the list cannot be read."""
    try:
        text = fetch(LPC_CSV_URL)
    except Exception as exc:  # noqa: BLE001
        print(f"  could not read {LPC_CSV_URL}: {exc}\n  (names will not be cross-checked; license numbers stay blank)")
        return {}
    by_name: dict[tuple[str, str], list[dict]] = {}
    firsts: dict[str, int] = {}
    lasts: dict[str, int] = {}
    for row in csv.DictReader(io.StringIO(text)):
        L = (row.get("LAST_NME") or "").strip().upper()
        F = (row.get("FIRST_NME") or "").strip().upper()
        by_name.setdefault((L, F), []).append(row)
        firsts[F] = firsts.get(F, 0) + 1
        lasts[L] = lasts.get(L, 0) + 1
    print(f"  {sum(len(v) for v in by_name.values()):,} current LPC / LPC Associate records read")
    return {"by_name": by_name, "first": firsts, "last": lasts}


def lookup_licensee(index: dict, last: str, first: str) -> tuple[dict | None, str]:
    """Best match for a name: exact (last, first-word) match; then last name + first-name prefix."""
    if not index or not last:
        return None, ""
    by_name = index["by_name"]
    L = last.upper()
    F = (first.split()[0] if first else "").upper()
    rows = by_name.get((L, F), [])
    if not rows and F:
        rows = [r for (l, f), rs in by_name.items() if l == L and (f.startswith(F) or F.startswith(f)) for r in rs]
    if not rows:
        return None, ""
    people = {r["ENTITY_NBR"] for r in rows}
    if len(people) > 1:
        return None, "several current licensees share this name"
    rows.sort(key=lambda r: 0 if r.get("RANK") == "LPC" else 1)   # prefer the LPC over the LPCA record
    return rows[0], ""


# --------------------------------------------------------------------------- #
# Pass 1: the meeting index page
# --------------------------------------------------------------------------- #

def list_packets(html: str) -> list[dict]:
    """[{meeting_date, url, kind}] for every meeting-materials link, newest first."""
    packets = []
    current_date = ""
    pos = 0
    events = []
    for m in DATE_TEXT.finditer(html):
        events.append((m.start(), "date", m))
    for m in PACKET_LINK.finditer(html):
        events.append((m.start(), "link", m))
    events.sort(key=lambda e: e[0])
    for _, kind, m in events:
        if kind == "date":
            try:
                current_date = date(int(m.group(3)), MONTHS[m.group(1)], int(m.group(2))).isoformat()
            except ValueError:
                pass
            continue
        href, text = m.group(1), re.sub(r"<[^>]+>", "", m.group(2))
        text = re.sub(r"\s+", " ", text.replace("&amp;", "&")).strip()
        if not re.search(r"meeting materials|agenda", text, re.I):
            continue
        if not current_date:
            continue
        url = urljoin(MEETINGS_URL, href)
        packets.append({"meeting_date": current_date, "url": url,
                        "kind": "zip" if url.lower().endswith(".zip") else "pdf",
                        "link_text": text})
    # one packet per URL
    seen = set()
    unique = []
    for p in packets:
        if p["url"] in seen:
            continue
        seen.add(p["url"])
        unique.append(p)
    return unique


# --------------------------------------------------------------------------- #
# Names, quarters, professions
# --------------------------------------------------------------------------- #

def nice_case(s: str) -> str:
    return " ".join(w.title() if (w.isupper() or w.islower()) else w for w in (s or "").split())


def profession_of(*labels: str) -> tuple[str, str, str]:
    """(token, category, note) from folder names, file names or bookmark titles."""
    for label in labels:
        for tok in re.findall(r"[A-Za-z]+", label or ""):
            if tok.upper() in PROFESSION_MAP:
                cat, note = PROFESSION_MAP[tok.upper()]
                return tok.upper(), cat, note
    return "", "review", "profession not marked in the packet; check the order by hand"


def quarter_of(*labels: str) -> str:
    """'FY25Q4' from 'FY2025 Q4 Agreed Orders', 'Q1 FY23 ...', '3.e FY22 Q3 LPC Agreed Orders', '4th Qtr ...'."""
    for label in labels:
        m = FY_QUARTER.search(label or "")
        if m:
            g = m.groups()
            fy = g[0] or g[3] or g[4] or g[7]
            q = g[1] or g[2] or g[5] or g[6]
            return f"FY{fy}Q{q}"
    return ""


def quarter_from_meeting(meeting_date: str) -> str:
    """Fallback when nothing names the quarter: the Council meets about six weeks after
    the quarter ends (FY runs Sep-Aug), so an October meeting reports Q4 of the FY just ended."""
    y, m = int(meeting_date[:4]), int(meeting_date[5:7])
    if m in (9, 10, 11):
        return f"FY{y % 100:02d}Q4"
    if m in (12, 1, 2, 3):
        return f"FY{(y + (1 if m == 12 else 0)) % 100:02d}Q1"
    if m in (4, 5):
        return f"FY{y % 100:02d}Q2"
    return f"FY{y % 100:02d}Q3"


def parse_name(raw: str) -> tuple[str, str, str, list[str]]:
    """(last, first, case_number, flags) from a file name or bookmark such as
    'Joslin, Gene AO', 'AO Lisette Domiteaux', '2024-00100 Agreed Order Megan Humphrey',
    'Mulcahy. Mary', 'Knolle,Mary Anne AO', 'Martin AO'."""
    flags: list[str] = []
    s = re.sub(r"\.pdf$", "", raw.strip(), flags=re.I)
    case = ""
    m = CASE_NUMBER.search(s)
    if m:
        case = m.group(1)
        s = CASE_NUMBER.sub(" ", s)
    s = NOISE_WORDS.sub(" ", s)
    s = re.sub(r"[_\-]{2,}|[()]", " ", s)
    s = re.sub(r"\s+", " ", s).strip(" ,.-_")
    last = first = ""
    if "," in s:
        last, first = [p.strip() for p in s.split(",", 1)]
    else:
        m = re.match(r"^([A-Za-z'\-]{2,})\.\s+(.+)$", s)      # 'Mulcahy. Mary' (a period used as the comma)
        if m:
            last, first = m.group(1), m.group(2)
        else:
            parts = s.split()
            if len(parts) == 1:
                last, first = parts[0], ""
                flags.append("first name missing in the packet")
            elif len(parts) >= 2:
                suffix = ""
                if parts[-1].upper() in SUFFIXES and len(parts) >= 3:
                    suffix = parts.pop()
                last_words = [parts.pop()]
                while len(parts) >= 2 and parts[-1].upper() in PARTICLES:   # 'Frank Del Rio' -> 'Del Rio, Frank'
                    last_words.insert(0, parts.pop())
                last = " ".join(last_words)
                first = " ".join(parts + ([suffix] if suffix else []))
                flags.append("name order assumed First Last")
    return nice_case(last), nice_case(first), case, flags


def cross_check_name(index: dict, last: str, first: str, flags: list[str]) -> tuple[str, str, dict | None]:
    """Fix 'Howson Heather' style file names with the licensee list; return (last, first, csv_row)."""
    row, note = lookup_licensee(index, last, first)
    if row is None and index and "name order assumed First Last" in flags and first and len(first.split()) == 1:
        alt_last, alt_first = first, last
        row2, _ = lookup_licensee(index, alt_last, alt_first)
        if row2 is not None:
            flags.remove("name order assumed First Last")
            flags.append("name order taken from the licensee list")
            return nice_case(alt_last), nice_case(alt_first), row2
        # Neither order is a current licensee: let the 43,000-name list vote on which word is the surname.
        as_written = index["first"].get(first.upper(), 0) + index["last"].get(last.upper(), 0)
        swapped = index["first"].get(last.upper(), 0) + index["last"].get(first.upper(), 0)
        if swapped >= 5 and swapped > 3 * max(as_written, 1):
            flags.remove("name order assumed First Last")
            flags.append("name order inferred from first/last-name frequencies in the licensee list")
            return nice_case(alt_last), nice_case(alt_first), None
    if note:
        flags.append(note)
    return last, first, row


# --------------------------------------------------------------------------- #
# Pass 2: reading a packet
# --------------------------------------------------------------------------- #

def is_combined_file(name: str) -> bool:
    """'LPC Q4 FY23 Agreed Orders.pdf' / 'Q1 FY23 Agreed Orders - LPC.pdf' (one file, many orders)."""
    stem = re.sub(r"\.pdf$", "", name, flags=re.I)
    return bool(re.search(r"\bAgreed Orders\b", stem, re.I)) and profession_of(stem)[0] != ""


def base_row(packet: dict) -> dict:
    return {
        "last_name": "", "first_name": "", "license_number": "", "license_rank": "",
        "csv_discipline_flag": "", "case_number": "", "fiscal_quarter": "",
        "meeting_date": packet["meeting_date"], "profession": "", "category": "", "note": "",
        "source_packet": packet["url"].rsplit("/", 1)[-1], "source_entry": "", "source_pages": "",
        "filename": "", "flags": "", "packet_url": packet["url"],
    }


def toc_ranges(entries: list[tuple[int, str, int]], first_page: int, end_page: int) -> list[tuple[list[str], int, int, str]]:
    """[([titles], first_page, last_page, flag)] (1-based, inclusive) from consecutive bookmarks.
    A bookmark without a page number (-1, seen in one 2023 file) cannot be separated from its
    neighbour: a leading one takes the pages before the next bookmark, any other one is folded
    into the previous bookmark's range and the file is flagged for a manual split."""
    out: list = []
    for i, (_lvl, title, page) in enumerate(entries):
        if page < 1:
            if out:
                titles, a, b, _f = out[-1]
                out[-1] = (titles + [title], a, b, "bookmark without a page number: two orders in one file, split by hand")
            else:
                out.append(([title], first_page, None, "bookmark without a page number: pages inferred"))
            continue
        if out and out[-1][2] is None:
            titles, a, _b, f = out[-1]
            out[-1] = (titles, a, page - 1, f)
        nxt = next((p2 - 1 for _l2, _t2, p2 in entries[i + 1:] if p2 >= 1), end_page)
        out.append(([title], page, min(nxt, end_page), ""))
    if out and out[-1][2] is None:
        titles, a, _b, f = out[-1]
        out[-1] = (titles, a, end_page, f)
    return [(t, a, b, f) for t, a, b, f in out if b >= a]


def rows_from_split(doc, packet: dict, entries, first_page: int, last_page: int, quarter: str,
                    profession: tuple[str, str, str], entry_label: str, index: dict) -> list[dict]:
    """One manifest row per bookmarked order inside a page range of an open PyMuPDF document."""
    tok, cat, note = profession
    rows = []
    for titles, a, b, flag in toc_ranges(entries, first_page, last_page):
        r = base_row(packet)
        last, first, case, flags = parse_name(titles[0])
        csv_row = None
        if cat == "counselor":
            last, first, csv_row = cross_check_name(index, last, first, flags)
        others = []
        for extra in titles[1:]:
            l2, f2, _c2, fl2 = parse_name(extra)
            if cat == "counselor":
                l2, f2, _row2 = cross_check_name(index, l2, f2, fl2)
            others.append(f"{l2}, {f2}".strip(", "))
        if flag:
            flags.append(flag)
        if others:
            flags.append("file also holds the order of " + " and ".join(others))
        r.update({"last_name": last, "first_name": first, "case_number": case, "fiscal_quarter": quarter,
                  "profession": tok, "category": cat, "note": note, "source_entry": entry_label + " > " + " + ".join(titles),
                  "source_pages": f"{a}-{b}", "flags": "; ".join(flags), "_pages": (a, b), "_others": others})
        if csv_row is not None:
            r.update({"license_number": csv_row.get("LIC_NBR", ""), "license_rank": csv_row.get("RANK", ""),
                      "csv_discipline_flag": csv_row.get("DISCPL_ACTN", "")})
        rows.append(r)
    return rows


def read_zip_packet(packet: dict, path: Path, index: dict, pymupdf) -> list[dict]:
    rows: list[dict] = []
    with zipfile.ZipFile(path) as zf:
        names = [n for n in zf.namelist() if not n.endswith("/")]
        for n in names:
            parts = n.split("/")
            if not any(re.search(r"agreed orders", p, re.I) for p in parts[:-1]) or not n.lower().endswith(".pdf"):
                continue
            if parts[-1].startswith("~$"):
                continue
            folder = parts[-2]
            quarter = quarter_of(*parts) or quarter_from_meeting(packet["meeting_date"])
            if is_combined_file(parts[-1]):
                prof = profession_of(parts[-1])
                tok, cat, note = prof
                if cat != "counselor":
                    r = base_row(packet)
                    r.update({"fiscal_quarter": quarter, "profession": tok, "category": cat, "note": note,
                              "source_entry": n, "flags": "combined file for another profession, not read"})
                    rows.append(r)
                    continue
                data = zf.read(n)
                doc = pymupdf.open(stream=data, filetype="pdf")
                entries = [(l, t, p) for l, t, p in doc.get_toc()]
                if not entries:
                    r = base_row(packet)
                    r.update({"fiscal_quarter": quarter, "profession": tok, "category": "review",
                              "note": "combined LPC file without bookmarks; saved whole to review\\ for a manual split",
                              "source_entry": n, "source_pages": f"1-{doc.page_count}", "_zip_entry": n})
                    rows.append(r)
                else:
                    found = rows_from_split(doc, packet, entries, 1, doc.page_count, quarter, prof, n, index)
                    for r in found:
                        r["_zip_entry"] = n
                    rows.extend(found)
                doc.close()
                continue
            # one PDF per licensee
            tok, cat, note = profession_of(folder)
            r = base_row(packet)
            last, first, case, flags = parse_name(parts[-1])
            csv_row = None
            if cat == "counselor":
                last, first, csv_row = cross_check_name(index, last, first, flags)
            r.update({"last_name": last, "first_name": first, "case_number": case, "fiscal_quarter": quarter,
                      "profession": tok, "category": cat, "note": note, "source_entry": n,
                      "flags": "; ".join(flags), "_zip_entry": n})
            if csv_row is not None:
                r.update({"license_number": csv_row.get("LIC_NBR", ""), "license_rank": csv_row.get("RANK", ""),
                          "csv_discipline_flag": csv_row.get("DISCPL_ACTN", "")})
            rows.append(r)
    return rows


def read_pdf_packet(packet: dict, path: Path, index: dict, pymupdf) -> list[dict]:
    rows: list[dict] = []
    doc = pymupdf.open(path)
    toc = doc.get_toc()
    level1 = [(i, t, p) for i, (l, t, p) in enumerate(toc) if l == 1]
    sections = []
    for k, (i, title, page) in enumerate(level1):
        if not re.search(r"agreed orders", title, re.I):
            continue
        prof = profession_of(title)
        end = doc.page_count
        for _j, _t, p2 in level1[k + 1:]:
            if p2 >= 1:
                end = p2 - 1
                break
        if end < page:
            end = doc.page_count
        next_i = level1[k + 1][0] if k + 1 < len(level1) else len(toc)
        children = [(l, t, p) for l, t, p in toc[i + 1:next_i] if l == 2]
        sections.append((title, page, end, prof, children))
    lpc_sections = [s for s in sections if s[3][1] == "counselor"]
    quarter = quarter_of(*(s[0] for s in sections)) or quarter_from_meeting(packet["meeting_date"])
    for title, page, end, prof, children in sections:
        tok, cat, note = prof
        if cat != "counselor":
            r = base_row(packet)
            r.update({"fiscal_quarter": quarter, "profession": tok, "category": cat, "note": note,
                      "source_entry": title, "source_pages": f"{page}-{end}",
                      "flags": f"{len(children)} bookmarked order(s) for another profession, not read"})
            rows.append(r)
            continue
        if not children:
            r = base_row(packet)
            r.update({"fiscal_quarter": quarter, "profession": tok, "category": "review",
                      "note": "LPC section has no per-licensee bookmarks; pages saved to review\\ for a manual split",
                      "source_entry": title, "source_pages": f"{page}-{end}", "_pages": (page, end)})
            rows.append(r)
            continue
        rows.extend(rows_from_split(doc, packet, children, page, end, quarter, prof, title, index))
    if not lpc_sections:
        # The May 2022 packet has the LPC orders as plain pages between the enforcement status
        # report and the first bookmarked (social-work) order. Save that gap, or the whole packet.
        r = base_row(packet)
        child_pages = [p for _t, _p, _e, _pr, ch in sections for _l, _t2, p in ch if p >= 1]
        gap = None
        if child_pages:
            p_first = min(child_pages)
            before = [p for _l, _t, p in toc if 1 <= p < p_first]
            if before and max(before) + 1 <= p_first - 1:
                gap = (max(before) + 1, p_first - 1)
        if gap:
            r.update({"fiscal_quarter": quarter, "profession": "LPC", "category": "review",
                      "note": "no LPC agreed-orders bookmark in this packet; the unbookmarked pages before the first "
                              "bookmarked order are saved to review\\ (LPC orders start with 'IN THE MATTER OF ... "
                              "PROFESSIONAL COUNSELORS'; split by hand)",
                      "source_entry": "(unbookmarked pages)", "source_pages": f"{gap[0]}-{gap[1]}", "_pages": gap})
        else:
            r.update({"fiscal_quarter": quarter, "profession": "LPC", "category": "review",
                      "note": "no LPC agreed-orders bookmark in this packet; whole packet saved to review\\ (find the "
                              "'IN THE MATTER OF ... PROFESSIONAL COUNSELORS' pages by hand)",
                      "source_entry": "(packet)", "source_pages": f"1-{doc.page_count}", "_whole": True})
        rows.append(r)
    doc.close()
    return rows


# --------------------------------------------------------------------------- #
# File names, manifest, log
# --------------------------------------------------------------------------- #

def assign_filenames(rows: list[dict]) -> None:
    """'Lastname, Firstname FY25Q4 2025-10-14.pdf'; the same person twice in a quarter gets ' (2)'.
    Review rows get 'REVIEW <packet or file name>.pdf' in the review folder."""
    seen: dict[str, int] = {}
    for r in rows:
        if r["category"] == "drop":
            r["filename"] = ""
            continue
        if r["category"] == "review" and not r["last_name"]:
            src = r["source_entry"] if not r["source_entry"].startswith("(") else r["source_packet"]
            base = ILLEGAL_FILENAME.sub("", f"REVIEW {r['meeting_date']} {Path(src).stem}").strip()
        else:
            name_part = f"{r['last_name']}, {r['first_name']}".strip(", ").strip() or "UNKNOWN"
            if r.get("_others"):
                name_part = " + ".join([name_part] + list(r["_others"]))
            base = ILLEGAL_FILENAME.sub("", " ".join(p for p in (name_part, r["fiscal_quarter"], r["meeting_date"]) if p)).strip()
        n = seen.get(base, 0) + 1
        seen[base] = n
        r["filename"] = f"{base}.pdf" if n == 1 else f"{base} ({n}).pdf"


MANIFEST_FIELDS = [
    "last_name", "first_name", "license_number", "license_rank", "csv_discipline_flag",
    "case_number", "fiscal_quarter", "meeting_date", "profession", "category", "note",
    "source_packet", "source_entry", "source_pages", "filename", "flags", "packet_url",
]


def write_manifest(rows: list[dict]) -> None:
    with MANIFEST_PATH.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=MANIFEST_FIELDS)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in MANIFEST_FIELDS})


def log_row(writer, filename: str, status: str, url: str, message: str = "") -> None:
    writer.writerow({"filename": filename, "status": status, "official_url": url, "message": message})


def target_of(r: dict) -> Path:
    return (REVIEW_FOLDER if r["category"] == "review" else STATE_FOLDER) / r["filename"]


def official_url(r: dict) -> str:
    u = r["packet_url"]
    if r.get("source_entry") and r["source_entry"] != "(packet)":
        u += "#" + r["source_entry"]
    if r.get("source_pages"):
        u += f" pages {r['source_pages']}"
    return u


# --------------------------------------------------------------------------- #
# Writing the orders out of a packet
# --------------------------------------------------------------------------- #

def write_orders(packet: dict, path: Path, rows: list[dict], writer, pymupdf) -> tuple[int, int, int]:
    ok = skipped = failed = 0
    wanted = [r for r in rows if r["category"] in ("counselor", "review") and r["filename"]]
    if not wanted:
        return 0, 0, 0
    STATE_FOLDER.mkdir(parents=True, exist_ok=True)
    zf = zipfile.ZipFile(path) if packet["kind"] == "zip" else None
    packet_doc = pymupdf.open(path) if packet["kind"] == "pdf" else None
    combined_docs: dict[str, object] = {}
    try:
        for r in wanted:
            target = target_of(r)
            if target.exists() and target.stat().st_size > 0:
                skipped += 1
                log_row(writer, r["filename"], "Already downloaded", official_url(r))
                continue
            try:
                target.parent.mkdir(parents=True, exist_ok=True)
                if r.get("_whole"):
                    data = path.read_bytes()
                elif r.get("_pages"):
                    a, b = r["_pages"]
                    if r.get("_zip_entry"):
                        src = combined_docs.get(r["_zip_entry"])
                        if src is None:
                            src = combined_docs[r["_zip_entry"]] = pymupdf.open(stream=zf.read(r["_zip_entry"]), filetype="pdf")
                    else:
                        src = packet_doc
                    out = pymupdf.open()
                    out.insert_pdf(src, from_page=a - 1, to_page=b - 1)
                    data = out.tobytes(garbage=3, deflate=True)
                    out.close()
                elif r.get("_zip_entry"):
                    data = zf.read(r["_zip_entry"])
                else:
                    raise RuntimeError("nothing to extract for this row")
                if not data.startswith(b"%PDF"):
                    raise RuntimeError("extracted data is not a PDF")
                target.write_bytes(data)
                ok += 1
                log_row(writer, r["filename"], "Downloaded", official_url(r), f"{len(data)} bytes")
                print(f"    saved {target.relative_to(STATE_FOLDER)} ({len(data):,} bytes)")
            except Exception as exc:  # noqa: BLE001
                failed += 1
                log_row(writer, r["filename"], "FAILED", official_url(r), str(exc))
                print(f"    FAIL  {r['filename']}: {exc}")
    finally:
        for d in combined_docs.values():
            d.close()
        if zf:
            zf.close()
        if packet_doc:
            packet_doc.close()
    return ok, skipped, failed


# --------------------------------------------------------------------------- #
# --text-check
# --------------------------------------------------------------------------- #

def text_check(min_chars: int = 200) -> int:
    try:
        import pymupdf
    except ImportError:
        print("PyMuPDF is not installed; run  py -m pip install pymupdf  and try again.")
        return 1
    pdfs = sorted(STATE_FOLDER.glob("*.pdf"))
    if not pdfs:
        print(f"No PDFs found in {STATE_FOLDER}")
        return 1
    with_text, without, unreadable = [], [], []
    for p in pdfs:
        try:
            with pymupdf.open(p) as doc:
                chars = sum(len(page.get_text()) for page in doc)
                pages = doc.page_count
        except Exception as exc:  # noqa: BLE001
            unreadable.append((p.name, str(exc)))
            continue
        (with_text if chars >= min_chars else without).append((p.name, pages, chars))
    print(f"\nText-layer check of {len(pdfs)} PDF(s) in {STATE_FOLDER} (threshold {min_chars} characters):")
    print(f"  with a text layer:    {len(with_text)}")
    print(f"  image only (OCR):     {len(without)}")
    print(f"  unreadable:           {len(unreadable)}")
    if without:
        print("\nImage-only files (run Foxit OCR on these before make_text_sidecars):")
        for name, pages, chars in without:
            print(f"  {name}  ({pages} pages, {chars} chars)")
    for name, err in unreadable:
        print(f"  UNREADABLE {name}: {err}")
    return 0


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #

def load_index() -> dict:
    if INDEX_PATH.exists():
        try:
            return json.loads(INDEX_PATH.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            return {}
    return {}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--list-only", action="store_true", help="build manifest.csv, write no orders")
    ap.add_argument("--keep-packets", action="store_true", help="keep downloaded packets in downloader\\packets\\")
    ap.add_argument("--refresh", action="store_true", help="ignore packet_index.json and re-read every packet")
    ap.add_argument("--text-check", action="store_true", help="count downloaded PDFs with a text layer, then exit")
    args = ap.parse_args(argv)

    if args.text_check:
        return text_check()
    try:
        import pymupdf
    except ImportError:
        try:
            import fitz as pymupdf  # older PyMuPDF
        except ImportError:
            raise SystemExit("PyMuPDF is needed to split the packets: py -m pip install pymupdf")

    print(f"Texas BHEC Council meeting packets -> {STATE_FOLDER}")
    print("Pass 0: reading the current LPC licensee list (name cross-check)")
    index = load_licensee_list()
    time.sleep(PAUSE_SECONDS)

    print("Pass 1: listing Council meeting packets")
    try:
        html = fetch(MEETINGS_URL)
    except Exception as exc:  # noqa: BLE001
        raise SystemExit(f"Could not read {MEETINGS_URL}: {exc}\nCheck that the page opens in a browser.") from exc
    packets = list_packets(html)
    if not packets:
        print("No meeting-materials links found. The page layout may have changed; see README.txt.")
        return 1
    print(f"  {len(packets)} packets, {packets[-1]['meeting_date']} to {packets[0]['meeting_date']}")

    cache = {} if args.refresh else load_index()
    all_rows: list[dict] = []
    totals = [0, 0, 0]
    PACKETS_DIR.mkdir(exist_ok=True)
    with LOG_PATH.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=["filename", "status", "official_url", "message"])
        writer.writeheader()
        for i, packet in enumerate(packets, 1):
            label = f"[{i}/{len(packets)}] {packet['meeting_date']} {packet['url'].rsplit('/', 1)[-1]}"
            cached = cache.get(packet["url"])
            if cached and not args.list_only:
                rows = cached["rows"]
                assign_filenames(rows)
                missing = [r for r in rows if r["category"] in ("counselor", "review") and r["filename"]
                           and not target_of(r).exists()]
                if not missing:
                    print(f"{label}: all {sum(1 for r in rows if r['category'] == 'counselor')} counselor order(s) already on disk, packet not downloaded")
                    for r in rows:
                        if r["filename"]:
                            log_row(writer, r["filename"], "Already downloaded", official_url(r))
                            totals[1] += 1
                    all_rows.extend(rows)
                    continue
            local = PACKETS_DIR / packet["url"].rsplit("/", 1)[-1]
            if not local.exists() or local.stat().st_size == 0:
                print(f"{label}: downloading packet")
                try:
                    time.sleep(PAUSE_SECONDS)
                    fetch(packet["url"], stream_to=local)
                except Exception as exc:  # noqa: BLE001
                    print(f"    FAIL packet: {exc}")
                    log_row(writer, "", "FAILED", packet["url"], f"packet download failed: {exc}")
                    totals[2] += 1
                    continue
            else:
                print(f"{label}: using packet already in {PACKETS_DIR.name}\\")
            try:
                if packet["kind"] == "zip":
                    rows = read_zip_packet(packet, local, index, pymupdf)
                else:
                    rows = read_pdf_packet(packet, local, index, pymupdf)
            except Exception as exc:  # noqa: BLE001
                print(f"    FAIL reading packet: {exc}")
                log_row(writer, "", "FAILED", packet["url"], f"packet could not be read: {exc}")
                totals[2] += 1
                continue
            assign_filenames(rows)
            n_c = sum(1 for r in rows if r["category"] == "counselor")
            n_d = sum(1 for r in rows if r["category"] == "drop")
            n_r = sum(1 for r in rows if r["category"] == "review")
            print(f"    {n_c} counselor order(s), {n_d} other-profession entr(ies) dropped, {n_r} for review")
            if not args.list_only:
                ok, skipped, failed = write_orders(packet, local, rows, writer, pymupdf)
                totals[0] += ok
                totals[1] += skipped
                totals[2] += failed
            cache[packet["url"]] = {"meeting_date": packet["meeting_date"],
                                    "rows": [{k: v for k, v in r.items() if not k.startswith("_") or k in ("_pages", "_zip_entry", "_whole", "_others")} for r in rows]}
            INDEX_PATH.write_text(json.dumps(cache, indent=1), encoding="utf-8")
            all_rows.extend(rows)
            if not args.keep_packets:
                try:
                    local.unlink()
                except OSError:
                    pass
            fh.flush()

    all_rows.sort(key=lambda r: (r["last_name"].lower(), r["first_name"].lower(), r["meeting_date"]))
    write_manifest(all_rows)
    people = {(r["last_name"].lower(), r["first_name"].lower()) for r in all_rows if r["category"] == "counselor"}
    print(f"\nManifest written: {MANIFEST_PATH}")
    print(f"  counselor  {len(people)} people, {sum(1 for r in all_rows if r['category'] == 'counselor')} orders")
    print(f"  review     {sum(1 for r in all_rows if r['category'] == 'review')} file(s) needing a manual split")
    print(f"  drop       {sum(1 for r in all_rows if r['category'] == 'drop')} entries for other professions (not written)")
    if args.list_only:
        print("\n--list-only: no order PDFs were written.")
        return 0
    print(f"\nDone. Written {totals[0]}, already present {totals[1]}, failed {totals[2]}. Log: {LOG_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
