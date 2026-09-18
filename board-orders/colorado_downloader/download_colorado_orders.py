"""
Colorado State Board of Licensed Professional Counselor Examiners order
downloader (Licensed Professional Counselors).

Colorado's Division of Professions and Occupations (DORA DPO) keeps three
things online, and this script uses two of them (verified 2026-09-18):

  pass 1  roster   https://apps2.colorado.gov/dora/licensing/Lookup/GenerateRoster.aspx
          "Download a Licensee/Discipline List". An ASP.NET form: tick the
          license types, press Continue, then fetch the generated file from
          Lookup/FileDownload.aspx?Idnt=<roster id>&Type=Comma. The CSV lists
          every licensee of the type (about 20,000 LPCs) and repeats the row
          for each public action: Case Number, Program Action, Discipline
          Effective Date, Discipline Complete Date. This is the INDEX: who
          has an action, which case, when. It has no document links.
  pass 2  DDMS     https://www.dora.state.co.us/pls/real/DDMS_Search_GUI.DPO_Search_Form
          the "DPO Public Documents System" (an Oracle PL/SQL site). One
          search with State Board = PROFESSIONAL COUNSELORS and nothing else
          returns every public document filed under the counselor board
          (898 on 2026-09-18) as one HTML table: barcode, name, license type,
          license number, effective date, document type and a direct
          download link (DDMS_documents_api.download?p_file=...). The link
          works with a plain GET, no session, no CAPTCHA. Each document is
          matched to the roster by license number and effective date so the
          manifest row also carries the roster's case number and action.
  pass 3  download every counselor document into the state folder.

Why not the per-licensee lookup: apps.colorado.gov (the address the board
page links to) sits behind an AWS WAF "Human Verification" CAPTCHA, and the
search form on apps2.colorado.gov has its own CAPTCHA box. The per-credential
detail page (Lookup/PrintLicenseDetails.aspx?cred=..&contact=..) does open on
apps2 without a CAPTCHA, but it lists only barcode numbers and sends the
reader to DDMS for the file. DDMS answers the whole board in one query, so
the detail pages are not needed at all.

Files land in the state folder one level above this script, named
    "Kosley, Lisa Marie LPC.0011765 2026-05-11.pdf"
(DORA's own license format, then the document's effective date). A second
document with the same name, license and date becomes "... (2).pdf".
Files already present are skipped, so the script can be re-run safely.
Every outcome goes to download_log.csv.

Usage (from this folder):
    py download_colorado_orders.py                      # rosters, DDMS index, then download counselor documents
    py download_colorado_orders.py --list-only          # build manifest.csv only, download nothing
    py download_colorado_orders.py --include-candidates # also download LPCC (candidate) documents
    py download_colorado_orders.py --skip-roster        # reuse the roster CSVs already in downloader\rosters\
    py download_colorado_orders.py --max-downloads N    # stop pass 3 after N files (for a sample run)
    py download_colorado_orders.py --text-check         # after downloading: count PDFs with a text layer
                                                        # (needs PyMuPDF: py -m pip install pymupdf)
    py download_colorado_orders.py --debug-html         # also save the raw pages under downloader\debug\

Needs: requests and beautifulsoup4 (py -m pip install requests beautifulsoup4).
PyMuPDF only for --text-check.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import re
import sys
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup

# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #

ROSTER_HOST = "https://apps2.colorado.gov"
ROSTER_FORM_URL = ROSTER_HOST + "/dora/licensing/Lookup/GenerateRoster.aspx"
ROSTER_FILE_URL = ROSTER_HOST + "/dora/licensing/Lookup/FileDownload.aspx"
# Roster license-type codes to request. LPC and LPP (provisional LPC) are
# counselors; LPCC (candidate) is downloaded only with --include-candidates.
ROSTER_CODES = {
    "LPC": "counselor",
    "LPP": "counselor",
    "LPCC": "candidate",
}

DDMS_BASE = "https://www.dora.state.co.us/pls/real/"
DDMS_FORM_URL = DDMS_BASE + "DDMS_Search_GUI.DPO_Search_Form"
# The leading "!" is Oracle's flexible-parameter mode; without it the site
# just shows the empty form again.
DDMS_SEARCH_URL = DDMS_BASE + "!DDMS_Search_GUI.Process_DPO_Search_Form"
DDMS_BOARD = "PROFESSIONAL COUNSELORS"

HERE = Path(__file__).resolve().parent            # ...\state_data\Colorado\downloader
STATE_FOLDER = HERE.parent                         # ...\state_data\Colorado
ROSTER_DIR = HERE / "rosters"
MANIFEST_PATH = HERE / "manifest.csv"
LOG_PATH = HERE / "download_log.csv"
DEBUG_DIR = HERE / "debug"

PAUSE_SECONDS = 1.5
RETRIES = 3
TIMEOUT = 180
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,application/pdf,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

# DDMS "License Type" values seen under the counselor board (2026-09-18) and
# what to do with each. Anything not listed goes to "review" rather than
# being guessed.
LICENSE_TYPE_MAP = {
    "LICENSED PROFESSIONAL COUNSELOR": ("counselor", "LPC", "LPC"),
    "PROVISIONAL LICENSED PROFESSIONAL COUNSELOR": ("counselor", "provisional LPC", "LPP"),
    "MIL SPOUSE - LICENSED PROFESSIONAL COUNSELOR": ("counselor", "LPC (military spouse)", "MSLPC"),
    "MIL SPOUSE - PROVISIONAL LICENSED PROFESSIONAL COUNSELOR": ("counselor", "provisional LPC (military spouse)", "LPP"),
    "LICENSED PROFESSIONAL COUNSELOR CANDIDATE": ("candidate", "LPC Candidate (pre-licensure); downloaded only with --include-candidates", "LPCC"),
    "MIL SPOUSE - LICENSED PROFESSIONAL COUNSELOR CANDIDATE": ("candidate", "LPC Candidate (military spouse); downloaded only with --include-candidates", "MSLPCC"),
    "UNLICENSED PRACTICE": ("drop", "unlicensed practice (cease and desist against a non-licensee)", ""),
    "LICENSED ADDICTION COUNSELOR": ("drop", "addiction counselor (LAC)", "ACD"),
    "CERTIFIED ADDICTION COUNSELOR I": ("drop", "addiction counselor (CAC I)", ""),
    "CERTIFIED ADDICTION COUNSELOR II": ("drop", "addiction counselor (CAC II)", ""),
    "CERTIFIED ADDICTION COUNSELOR III": ("drop", "addiction counselor (CAC III)", ""),
    "REGISTERED PSYCHOTHERAPIST": ("drop", "registered psychotherapist (NLC)", "NLC"),
    "UNLICENSED PSYCHOTHERAPIST": ("drop", "unlicensed psychotherapist (NLC)", "NLC"),
    "LICENSED CLINICAL SOCIAL WORKER": ("drop", "social work (LCSW)", "CSW"),
    "LICENSED SOCIAL WORKER": ("drop", "social work (LSW)", "LSW"),
    "MARRIAGE AND FAMILY THERAPIST": ("drop", "marriage and family therapy (MFT)", "MFT"),
    "PSYCHOLOGIST": ("drop", "psychology (PSY)", "PSY"),
}

# DDMS "Document Type" values that are not board actions.
DOCTYPE_DROP = {
    "HPPP-REFUSAL OF MALPRACTICE INSURANCE": "not a board action (malpractice insurance refusal report)",
}
DOCTYPE_REVIEW = {
    "APPLICATION / SUPPORTING DOCUMENTS": "document type is application material, not an order; check by hand",
}

ILLEGAL_FILENAME = re.compile(r'[\\/:*?"<>|]+')
US_DATE = re.compile(r"^(\d{1,2})/(\d{1,2})/(\d{4})$")

session = requests.Session()
session.headers.update(HEADERS)


# --------------------------------------------------------------------------- #
# Fetching
# --------------------------------------------------------------------------- #

def fetch(url: str, *, method: str = "GET", data: dict | None = None, params: dict | None = None,
          binary: bool = False, timeout: int = TIMEOUT):
    """GET or POST with retries. Returns text (or bytes when binary=True)."""
    last_err = None
    for attempt in range(1, RETRIES + 1):
        try:
            resp = session.request(method, url, data=data, params=params, timeout=timeout)
            resp.raise_for_status()
            return resp.content if binary else resp.text
        except Exception as exc:  # noqa: BLE001
            last_err = exc
            if attempt < RETRIES:
                time.sleep(PAUSE_SECONDS * attempt)
    raise RuntimeError(f"{url}: {last_err}")


def save_debug(name: str, data: str | bytes) -> None:
    DEBUG_DIR.mkdir(exist_ok=True)
    p = DEBUG_DIR / name
    if isinstance(data, bytes):
        p.write_bytes(data)
    else:
        p.write_text(data, encoding="utf-8")


def iso_date(us: str) -> str:
    """'05/11/2026' -> '2026-05-11'; anything else comes back unchanged (or '')."""
    m = US_DATE.match((us or "").strip())
    if not m:
        return (us or "").strip()
    mm, dd, yyyy = m.groups()
    try:
        return dt.date(int(yyyy), int(mm), int(dd)).isoformat()
    except ValueError:
        return us.strip()


def nice_case(s: str) -> str:
    """Title-case words written in all caps or all lower; keep 'McCoy', 'DeValk' as written.
    DDMS prints 'NULL' for an empty middle or business name."""
    s = (s or "").strip()
    if s.upper() == "NULL":
        return ""
    return " ".join(w.title() if (w.isupper() or w.islower()) else w for w in s.split())


# --------------------------------------------------------------------------- #
# Pass 1: rosters (the index)
# --------------------------------------------------------------------------- #

def roster_checkboxes(form_html: str) -> dict[str, str]:
    """{license code: checkbox field name} for every license type on the roster form.
    Each checkbox is followed by text like 'LPC - Licensed Professional Counselor - All Statuses'."""
    found: dict[str, str] = {}
    for m in re.finditer(
        r'<input[^>]*type="checkbox"[^>]*name="([^"]*ckbRoster\d+)"[^>]*>\s*(?:</span>)?\s*([A-Z]{2,6}) - ',
        form_html,
    ):
        found.setdefault(m.group(2), m.group(1))
    return found


def request_rosters(codes: list[str], debug: bool = False) -> dict[str, Path]:
    """Ask the roster generator for the given license types and save each CSV
    under downloader\\rosters\\<code>.csv. Returns {code: path}."""
    ROSTER_DIR.mkdir(exist_ok=True)
    form_html = fetch(ROSTER_FORM_URL)
    if debug:
        save_debug("roster_form.html", form_html)
    boxes = roster_checkboxes(form_html)
    missing = [c for c in codes if c not in boxes]
    if missing:
        raise RuntimeError(
            f"roster form has no checkbox for {', '.join(missing)}; found {len(boxes)} license types. "
            "Open the form in a browser and compare with ROSTER_CODES."
        )
    soup = BeautifulSoup(form_html, "html.parser")
    post = {i["name"]: i.get("value", "") for i in soup.find_all("input", type="hidden") if i.get("name")}
    for c in codes:
        post[boxes[c]] = "on"
    post["ctl00$MainContentPlaceHolder$btnRosterContinue"] = "Continue"
    time.sleep(PAUSE_SECONDS)
    listing = fetch(ROSTER_FORM_URL, method="POST", data=post)
    if debug:
        save_debug("roster_listing.html", listing)
    # The reply is DownloadRoster.aspx: one row per generated roster with a
    # Download button carrying RosterIdnt="<id>" and a cell naming the roster.
    ids: dict[str, str] = {}
    lsoup = BeautifulSoup(listing, "html.parser")
    for btn in lsoup.find_all("input", attrs={"rosteridnt": True}):
        tr = btn.find_parent("tr")
        text = tr.get_text(" ", strip=True) if tr else ""
        m = re.search(r"\b([A-Z]{2,6}) - ", text)
        if m and m.group(1) in codes:
            ids.setdefault(m.group(1), btn["rosteridnt"])
    if not ids:
        raise RuntimeError("the roster listing page shows no generated roster; the form may have changed")
    paths: dict[str, Path] = {}
    for c in codes:
        if c not in ids:
            print(f"  WARNING: no roster came back for {c}")
            continue
        time.sleep(PAUSE_SECONDS)
        data = fetch(ROSTER_FILE_URL, params={"Idnt": ids[c], "Type": "Comma"}, binary=True, timeout=600)
        if data[:200].lstrip().lower().startswith(b"<!doctype") or b"<html" in data[:500].lower():
            raise RuntimeError(f"roster {c} came back as a web page, not a CSV")
        p = ROSTER_DIR / f"{c}.csv"
        p.write_bytes(data)
        paths[c] = p
        print(f"  roster {c}: {len(data):,} bytes -> {p.name}")
    return paths


def read_roster(path: Path, code: str) -> tuple[dict[str, dict], int, int]:
    """Parse one roster CSV. Returns ({license number: licensee}, rows, licensees).
    A licensee holds name parts, status, and one action per (case, action, dates) row."""
    people: dict[str, dict] = {}
    n_rows = 0
    with path.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
        for raw in csv.DictReader(fh):
            row = {(k or "").strip(): (v or "").strip() for k, v in raw.items() if k is not None}
            n_rows += 1
            lic = row.get("License Number", "")
            if not lic:
                continue
            p = people.setdefault(lic, {
                "code": code,
                "last": row.get("Last Name", ""),
                "first": row.get("First Name", ""),
                "middle": row.get("Middle Name", ""),
                "status": row.get("License Status Description", ""),
                "first_issued": iso_date(row.get("License First Issue Date", "")),
                "actions": [],
            })
            if row.get("Case Number") or row.get("Program Action"):
                a = {
                    "case": row.get("Case Number", ""),
                    "action": row.get("Program Action", ""),
                    "effective": iso_date(row.get("Discipline Effective Date", "")),
                    "end": iso_date(row.get("Discipline Complete Date", "")),
                }
                if a not in p["actions"]:
                    p["actions"].append(a)
    return people, n_rows, len(people)


# --------------------------------------------------------------------------- #
# Pass 2: DDMS document index
# --------------------------------------------------------------------------- #

DDMS_COLUMNS = ["barcode", "last", "first", "middle", "business", "board",
                "license_type", "license_number", "effective", "doctype"]


def ddms_board_documents(debug: bool = False) -> list[dict]:
    """Every document DDMS files under the counselor board, from one search."""
    fetch(DDMS_FORM_URL)          # be a normal visitor: load the form first
    time.sleep(PAUSE_SECONDS)
    post = {
        "p_last_name": "", "p_first_name": "", "p_middle_name": "", "p_entity_name": "",
        "p_board_name": DDMS_BOARD, "p_license_type": "", "p_license_number": "",
        "p_barcode": "", "p_effective_date": "", "p_operation": "Search",
    }
    html = fetch(DDMS_SEARCH_URL, method="POST", data=post, timeout=600)
    if debug:
        save_debug("ddms_board.html", html)
    soup = BeautifulSoup(html, "html.parser")
    docs: list[dict] = []
    for a in soup.find_all("a", href=re.compile(r"DDMS_documents_api\.download", re.I)):
        tr = a.find_parent("tr")
        if tr is None:
            continue
        cells = [td.get_text(" ", strip=True) for td in tr.find_all("td", recursive=False)]
        if len(cells) != len(DDMS_COLUMNS):
            print(f"  WARNING: skipped a result row with {len(cells)} cells: {cells[:3]}")
            continue
        d = dict(zip(DDMS_COLUMNS, cells))
        d["url"] = requests.compat.urljoin(DDMS_BASE, a["href"])
        d["source_filename"] = a["href"].split("/")[-1]
        docs.append(d)
    m = re.search(r"Query returned (\d+) document records", soup.get_text(" "))
    reported = int(m.group(1)) if m else -1
    print(f"  DDMS reports {reported} document records; parsed {len(docs)} download links")
    if reported > 0 and len(docs) < reported:
        print("  WARNING: fewer links parsed than DDMS reported; the result layout may have changed")
    return docs


def classify_doc(d: dict) -> tuple[str, str, str]:
    """(category, note, roster code) for a DDMS row."""
    lt = d["license_type"].strip().upper()
    if lt in LICENSE_TYPE_MAP:
        cat, note, code = LICENSE_TYPE_MAP[lt]
    elif not lt:
        cat, note, code = "review", "no license type on the DDMS row", ""
    else:
        cat, note, code = "review", f"unknown license type: {d['license_type']}", ""
    dtp = d["doctype"].strip().upper()
    if cat in ("counselor", "candidate"):
        if dtp in DOCTYPE_DROP:
            cat, note = "drop", DOCTYPE_DROP[dtp]
        elif dtp in DOCTYPE_REVIEW:
            cat, note = "review", DOCTYPE_REVIEW[dtp]
    return cat, note, code


def license_key(code: str, number: str) -> str:
    """DORA's printed license format: 'LPC.0011765'. Plain number when the type is unknown."""
    number = (number or "").strip()
    if not number:
        return ""
    if code and number.isdigit():
        return f"{code}.{int(number):07d}"
    return number


def build_rows(docs: list[dict], rosters: dict[str, dict[str, dict]]) -> list[dict]:
    """One manifest row per DDMS document, joined to the roster, plus one
    'index only' row per roster licensee with actions but no document."""
    rows: list[dict] = []
    seen_lic: set[tuple[str, str]] = set()
    for d in docs:
        cat, note, code = classify_doc(d)
        flags: list[str] = []
        lic = d["license_number"]
        person = rosters.get(code, {}).get(lic) if code else None
        if person is None and lic:
            # The same number may sit on another roster (an LPCC who became an LPC keeps a new number,
            # but the DDMS row may still say candidate); look the number up everywhere as a fallback.
            for rc, people in rosters.items():
                if lic in people:
                    person, code = people[lic], rc
                    if cat == "review" and not d["license_type"].strip():
                        # DDMS left the license type blank, but the number is on a roster: trust the roster.
                        cat = ROSTER_CODES.get(rc, "review")
                        note = f"license type blank in DDMS; number is on the {rc} roster"
                    else:
                        flags.append(f"license number found on the {rc} roster (DDMS says {d['license_type'] or 'no license type'})")
                    break
        if person:
            last, first, middle = person["last"], person["first"], person["middle"]
            status = person["status"]
            hits = [a for a in person["actions"] if a["effective"] == iso_date(d["effective"])]
            if not hits and person["actions"]:
                flags.append("effective date matches no roster action")
            elif not person["actions"]:
                flags.append("roster shows no public action for this licensee")
            case = " | ".join(a["case"] for a in hits if a["case"])
            action = " | ".join(a["action"] for a in hits if a["action"])
            end = " | ".join(a["end"] for a in hits if a["end"])
            seen_lic.add((code, lic))
        else:
            last, first, middle = nice_case(d["last"]), nice_case(d["first"]), nice_case(d["middle"])
            status = ""
            case = action = end = ""
            if lic:
                flags.append("license number not on any roster")
            else:
                flags.append("no license number on the DDMS row")
        if not d["effective"]:
            flags.append("no effective date")
        rows.append({
            "last_name": last,
            "first_name": " ".join(x for x in (first, middle) if x).strip(),
            "license_number": license_key(code, lic),
            "license_type": d["license_type"],
            "license_status": status,
            "case_number": case,
            "action": action,
            "effective_date": iso_date(d["effective"]),
            "end_date": end,
            "document_type": d["doctype"],
            "barcode": d["barcode"],
            "source_filename": d["source_filename"],
            "url": d["url"],
            "filename": "",
            "category": cat,
            "note": note,
            "flags": "; ".join(flags),
            "business_name": nice_case(d["business"]),
        })
    # Roster licensees with public actions but nothing in DDMS: keep them as index-only rows.
    for code, people in rosters.items():
        cat = ROSTER_CODES.get(code, "review")
        for lic, p in people.items():
            if not p["actions"] or (code, lic) in seen_lic:
                continue
            for a in p["actions"]:
                rows.append({
                    "last_name": p["last"],
                    "first_name": " ".join(x for x in (p["first"], p["middle"]) if x).strip(),
                    "license_number": license_key(code, lic),
                    "license_type": code,
                    "license_status": p["status"],
                    "case_number": a["case"],
                    "action": a["action"],
                    "effective_date": a["effective"],
                    "end_date": a["end"],
                    "document_type": "",
                    "barcode": "",
                    "source_filename": "",
                    "url": "",
                    "filename": "",
                    "category": cat,
                    "note": "roster action with no document in DDMS",
                    "flags": "index only, no document",
                    "business_name": "",
                })
    rows.sort(key=lambda r: (r["last_name"].lower(), r["first_name"].lower(), r["effective_date"], r["barcode"]))
    return rows


def assign_filenames(rows: list[dict]) -> None:
    """'Kosley, Lisa Marie LPC.0011765 2026-05-11.pdf'; a later collision gets ' (2)', ' (3)'."""
    seen: dict[str, int] = {}
    for r in rows:
        if not r["url"] or r["category"] == "drop":
            r["filename"] = ""
            continue
        name_part = f"{r['last_name']}, {r['first_name']}".strip(", ").strip() or (r["business_name"] or "UNKNOWN")
        key = r["license_number"] or r["barcode"]
        date = r["effective_date"] if re.match(r"^\d{4}-\d{2}-\d{2}$", r["effective_date"]) else "undated"
        base = ILLEGAL_FILENAME.sub("", " ".join(p for p in (name_part, key, date) if p)).strip()
        n = seen.get(base, 0) + 1
        seen[base] = n
        r["filename"] = f"{base}.pdf" if n == 1 else f"{base} ({n}).pdf"


# --------------------------------------------------------------------------- #
# Manifest, log, download
# --------------------------------------------------------------------------- #

MANIFEST_FIELDS = [
    "last_name", "first_name", "license_number", "license_type", "license_status",
    "case_number", "action", "effective_date", "end_date", "document_type",
    "barcode", "source_filename", "url", "filename", "category", "note", "flags", "business_name",
]


def write_manifest(rows: list[dict]) -> None:
    with MANIFEST_PATH.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=MANIFEST_FIELDS)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in MANIFEST_FIELDS})


def log_row(writer, filename: str, status: str, url: str, message: str = "") -> None:
    writer.writerow({"filename": filename, "status": status, "official_url": url, "message": message})


def download_all(rows: list[dict], limit: int = 0) -> tuple[int, int, int]:
    STATE_FOLDER.mkdir(parents=True, exist_ok=True)
    ok = skipped = failed = 0
    jobs = [r for r in rows if r["filename"] and r["url"]]
    if limit:
        jobs = jobs[:limit]
    total = len(jobs)
    with LOG_PATH.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=["filename", "status", "official_url", "message"])
        writer.writeheader()
        for i, r in enumerate(jobs, 1):
            filename, url = r["filename"], r["url"]
            target = STATE_FOLDER / filename
            if target.exists() and target.stat().st_size > 0:
                skipped += 1
                log_row(writer, filename, "Already downloaded", url)
                print(f"[{i}/{total}] skip  {filename}")
                continue
            try:
                data = fetch(url, binary=True, timeout=600)
                if not data.startswith(b"%PDF"):
                    raise RuntimeError("response is not a PDF (probably an HTML error page)")
                target.write_bytes(data)
                ok += 1
                log_row(writer, filename, "Downloaded", url, f"{len(data)} bytes")
                print(f"[{i}/{total}] saved {filename} ({len(data):,} bytes)")
            except Exception as exc:  # noqa: BLE001
                failed += 1
                log_row(writer, filename, "FAILED", url, str(exc))
                print(f"[{i}/{total}] FAIL  {filename}: {exc}")
            fh.flush()
            time.sleep(PAUSE_SECONDS)
    print(f"\nDone. Downloaded {ok}, already present {skipped}, failed {failed}. Log: {LOG_PATH}")
    return ok, skipped, failed


# --------------------------------------------------------------------------- #
# --text-check: how many downloaded PDFs carry a text layer
# --------------------------------------------------------------------------- #

def text_check(min_chars: int = 200) -> int:
    try:
        import pymupdf  # PyMuPDF >= 1.24
    except ImportError:
        try:
            import fitz as pymupdf  # older PyMuPDF
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

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--list-only", action="store_true", help="build manifest.csv, download nothing")
    ap.add_argument("--include-candidates", action="store_true", help="also download LPCC (candidate) documents")
    ap.add_argument("--skip-roster", action="store_true", help="reuse the roster CSVs already in downloader\\rosters\\")
    ap.add_argument("--max-downloads", type=int, default=0, help="stop pass 3 after this many files (sample run)")
    ap.add_argument("--text-check", action="store_true", help="count downloaded PDFs with a text layer (PyMuPDF), then exit")
    ap.add_argument("--debug-html", action="store_true", help="save the raw pages under downloader\\debug\\")
    args = ap.parse_args(argv)

    if args.text_check:
        return text_check()

    print(f"Colorado DORA DPO (roster + DDMS public documents) -> {STATE_FOLDER}")
    codes = list(ROSTER_CODES)
    print(f"Pass 1: rosters for {', '.join(codes)}")
    paths: dict[str, Path] = {}
    if args.skip_roster:
        for c in codes:
            p = ROSTER_DIR / f"{c}.csv"
            if p.exists():
                paths[c] = p
            else:
                print(f"  no saved roster for {c} ({p}); it will be fetched")
    missing = [c for c in codes if c not in paths]
    if missing:
        try:
            paths.update(request_rosters(missing, debug=args.debug_html))
        except Exception as exc:  # noqa: BLE001
            raise SystemExit(
                f"Could not download the roster: {exc}\n"
                f"Check that {ROSTER_FORM_URL} opens in a browser. If it does and the script still fails,\n"
                "the form may have changed; see README.txt."
            ) from exc
    rosters: dict[str, dict[str, dict]] = {}
    for c, p in paths.items():
        people, n_rows, n_people = read_roster(p, c)
        rosters[c] = people
        with_actions = sum(1 for x in people.values() if x["actions"])
        n_actions = sum(len(x["actions"]) for x in people.values())
        print(f"  {c}: {n_rows:,} rows, {n_people:,} licensees, {with_actions} with a public action ({n_actions} action rows)")

    print("Pass 2: DDMS public documents for the counselor board")
    try:
        docs = ddms_board_documents(debug=args.debug_html)
    except Exception as exc:  # noqa: BLE001
        raise SystemExit(
            f"Could not read the DDMS document list: {exc}\n"
            f"Check that {DDMS_FORM_URL} opens in a browser (pick State Board = Professional Counselors, Search)."
        ) from exc
    if not docs:
        print("DDMS returned no documents at all. The site or its result layout may have changed.")
        return 1

    rows = build_rows(docs, rosters)
    assign_filenames(rows)
    write_manifest(rows)

    print(f"\nManifest written: {MANIFEST_PATH}")
    for cat in ("counselor", "candidate", "review", "drop"):
        sub = [r for r in rows if r["category"] == cat]
        with_doc = [r for r in sub if r["url"]]
        lic = {r["license_number"] or r["barcode"] for r in with_doc}
        print(f"  {cat:<10} {len(with_doc)} documents for {len(lic)} licensees; {len(sub) - len(with_doc)} index-only rows")
    dated = sorted(r["effective_date"] for r in rows if r["url"] and re.match(r"^\d{4}", r["effective_date"]))
    if dated:
        print(f"  document effective dates {dated[0]} to {dated[-1]}")

    if args.list_only:
        return 0

    wanted = {"counselor"}
    if args.include_candidates:
        wanted.add("candidate")
    jobs = [r for r in rows if r["category"] in wanted and r["filename"]]
    print(f"\nPass 3: downloading {len(jobs) if not args.max_downloads else min(len(jobs), args.max_downloads)} PDF(s) into {STATE_FOLDER}\n")
    download_all(jobs, limit=args.max_downloads)
    return 0


if __name__ == "__main__":
    sys.exit(main())
