"""
Oklahoma State Board of Behavioral Health Licensure order downloader
(Licensed Professional Counselors).

The board's public register (a Thentia Cloud app at
https://obbhl.us.thentiacloud.net/webs/obbhl/register/) shows a "Public
Notices" section on each disciplined licensee's profile. Each notice has a
one-line summary, an effective date and, for most notices from 2021 on (and a
few back to 2010), the signed order as a PDF attachment. The register's own REST calls answer plain
HTTP GET requests with JSON (verified 2026-09-18), so no browser is needed:

  pass 1  search   rest/public/profile/search/?keyword=&skip=<n>&take=<n>&disciplined=true
          lists every disciplined licensee of every profession (186 on
          2026-09-18: 144 LPC, 11 LPC Candidate, 23 LMFT, 8 LBP). LPCs are
          "counselor", LPC Candidates are "candidate" (kept separately,
          downloaded only with --include-candidates), LMFT and LBP are "drop".
  pass 2  profile  rest/public/profile/get/?id=<id>
          for every counselor (and candidate) returns the publicNotices list.
          One manifest.csv row is written per notice. Notices without an
          attachment (the pre-2021 history) stay in the manifest, flagged
          "index only, no document".
  pass 3  download rest/public/annotation/download/index.php?id=<attachment id>&entity=<effi_entity>
          for every attachment on a counselor notice. Both values come from
          the attachment object; effi_entity is a per-file signed token, so
          the link works without a login.

Files land in the state folder one level above this script, named
    "Lastname, Firstname LPC04898 2023-04-07.pdf"
(license number, then the notice's effective date). A second attachment on
the same notice becomes "... (2).pdf". Files already present are skipped, so
the script can be re-run safely. Every outcome goes to download_log.csv.

Usage (from this folder):
    py download_oklahoma_orders.py                      # list, then download counselor orders
    py download_oklahoma_orders.py --list-only          # build manifest.csv only, download nothing
    py download_oklahoma_orders.py --include-candidates # also download LPC Candidate orders
    py download_oklahoma_orders.py --text-check         # after downloading: count PDFs with a text layer
                                                        # (needs PyMuPDF: py -m pip install pymupdf)
    py download_oklahoma_orders.py --debug-json         # also save the raw JSON replies under downloader\debug\

Needs: requests   (py -m pip install requests). PyMuPDF only for --text-check.
"""

from __future__ import annotations

import argparse
import csv
import html
import json
import re
import sys
import time
from pathlib import Path
from urllib.parse import quote

import requests

# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #

BASE_URL = "https://obbhl.us.thentiacloud.net"
SEARCH_URL = BASE_URL + "/rest/public/profile/search/"
PROFILE_URL = BASE_URL + "/rest/public/profile/get/"
DOWNLOAD_URL = BASE_URL + "/rest/public/annotation/download/index.php"
REGISTER_PAGE = BASE_URL + "/webs/obbhl/register/"
PAGE_SIZE = 2000          # the search call accepts take=2000; page with skip until a short page

HERE = Path(__file__).resolve().parent            # ...\state_data\Oklahoma\downloader
STATE_FOLDER = HERE.parent                         # ...\state_data\Oklahoma
MANIFEST_PATH = HERE / "manifest.csv"
LOG_PATH = HERE / "download_log.csv"
DEBUG_DIR = HERE / "debug"

PAUSE_SECONDS = 1.5
RETRIES = 3
TIMEOUT = 90
# The register answers 403 to a bare script user agent; a browser user agent is accepted.
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, application/pdf, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": REGISTER_PAGE,
}

# registrationCategory values seen on the disciplined list (2026-09-18) and what
# to do with each. Anything not listed goes to "review" rather than being guessed.
CATEGORY_MAP = {
    "Licensed Professional Counselor (LPC)": ("counselor", "LPC"),
    "LPC Candidate": ("candidate", "LPC Candidate (pre-licensure); downloaded only with --include-candidates"),
    "Licensed Marital and Family Therapist (LMFT)": ("drop", "marriage & family therapy (LMFT)"),
    "Licensed Behavioral Practitioner (LBP)": ("drop", "behavioral practitioner (LBP)"),
    "Licensed Alcohol and Drug Counselor (LADC)": ("drop", "alcohol & drug counseling (LADC)"),
}

# Case numbers appear in attachment file names, e.g. "Allmon, Natasha_2025-LPC-738_Consent Order.pdf".
CASE_PATTERN = re.compile(r"\b(\d{2,4}-[A-Z]{2,5}-\d{1,5}[A-Za-z]?)\b")
DATE_PATTERN = re.compile(r"^(\d{4})-(\d{2})-(\d{2})")
ILLEGAL_FILENAME = re.compile(r'[\\/:*?"<>|]+')
TAG_PATTERN = re.compile(r"<[^>]+>")

session = requests.Session()
session.headers.update(HEADERS)


# --------------------------------------------------------------------------- #
# Fetching
# --------------------------------------------------------------------------- #

def fetch(url: str, params: dict | None = None, binary: bool = False):
    """GET with retries. Returns parsed JSON (or bytes when binary=True)."""
    last_err = None
    for attempt in range(1, RETRIES + 1):
        try:
            resp = session.get(url, params=params, timeout=TIMEOUT)
            resp.raise_for_status()
            if binary:
                return resp.content
            return resp.json()
        except Exception as exc:  # noqa: BLE001
            last_err = exc
            if attempt < RETRIES:
                time.sleep(PAUSE_SECONDS * attempt)
    raise RuntimeError(f"{url}: {last_err}")


def save_debug(name: str, data) -> None:
    DEBUG_DIR.mkdir(exist_ok=True)
    (DEBUG_DIR / name).write_text(json.dumps(data, indent=1), encoding="utf-8")


# --------------------------------------------------------------------------- #
# Pass 1: list every disciplined licensee
# --------------------------------------------------------------------------- #

def list_disciplined(debug: bool = False) -> list[dict]:
    """Every record the register tags as disciplined, all professions, paged with skip/take."""
    records: list[dict] = []
    skip = 0
    page_no = 0
    while True:
        params = {"keyword": "", "skip": skip, "take": PAGE_SIZE, "disciplined": "true", "lang": "en-US"}
        data = fetch(SEARCH_URL, params=params)
        page_no += 1
        if debug:
            save_debug(f"search_page{page_no}.json", data)
        if str(data.get("errorCode", "0")) not in ("0", ""):
            raise RuntimeError(f"search returned errorCode {data.get('errorCode')}: {data.get('errorMessage')}")
        page = data.get("result") or []
        records.extend(page)
        print(f"  search page {page_no}: {len(page)} records (resultCount {data.get('resultCount')})")
        if len(page) < PAGE_SIZE:
            break
        skip += PAGE_SIZE
        time.sleep(PAUSE_SECONDS)
    # De-duplicate on profile id in case the server pages inconsistently.
    unique: dict[str, dict] = {}
    for r in records:
        unique.setdefault(r.get("id") or f"noid-{len(unique)}", r)
    return list(unique.values())


def classify(record: dict) -> tuple[str, str]:
    cat = (record.get("registrationCategory") or "").strip()
    if cat in CATEGORY_MAP:
        return CATEGORY_MAP[cat]
    if not cat:
        return ("review", "no registrationCategory on the search record")
    return ("review", f"unknown registration category: {cat}")


# --------------------------------------------------------------------------- #
# Pass 2: profiles and notices
# --------------------------------------------------------------------------- #

def strip_html(s: str) -> str:
    text = TAG_PATTERN.sub(" ", s or "")
    text = html.unescape(text).replace("\xa0", " ")
    return re.sub(r"\s+", " ", text).strip()


def nice_case(s: str) -> str:
    """Title-case words written in all caps or all lower; keep 'McCoy', 'DeValk' as written."""
    return " ".join(w.title() if (w.isupper() or w.islower()) else w for w in (s or "").split())


def name_parts(record: dict) -> tuple[str, str]:
    last = nice_case((record.get("lastName") or "").strip())
    first = nice_case((record.get("firstName") or "").strip())
    middle = (record.get("middleName") or "").strip()
    if middle:
        first = f"{first} {nice_case(middle)}".strip()
    return last, first


def license_number(record: dict) -> str:
    """The register prints 'N/A' for people who never held a license number (mostly candidates)."""
    v = (record.get("registrationNumber") or "").strip()
    return "" if v.upper() in ("N/A", "NA", "NONE") else v


def case_number_from(*texts: str) -> str:
    for t in texts:
        m = CASE_PATTERN.search(t or "")
        if m:
            return m.group(1)
    return ""


def attachment_url(att: dict) -> str:
    """The register's own download pattern; both values are URL-encoded because the
    signed token contains '$', '.' and '/'."""
    return f"{DOWNLOAD_URL}?id={quote(att.get('id') or '', safe='')}&entity={quote(att.get('effi_entity') or '', safe='')}"


def get_profile(profile_id: str, debug: bool = False) -> dict:
    data = fetch(PROFILE_URL, params={"id": profile_id, "lang": "en-US"})
    if debug:
        save_debug(f"profile_{profile_id}.json", data)
    # The profile call returns the licensee object itself; tolerate a wrapper too.
    if isinstance(data, dict) and "result" in data and isinstance(data["result"], dict):
        data = data["result"]
    return data


def notice_rows(record: dict, profile: dict | None, category: str, note: str) -> list[dict]:
    """One manifest row per public notice (or one placeholder row when there is none)."""
    last, first = name_parts(record)
    base = {
        "last_name": last,
        "first_name": first,
        "license_number": license_number(record),
        "registration_category": record.get("registrationCategory") or "",
        "status": record.get("registrationStatus") or "",
        "city": record.get("city") or "",
        "profile_id": record.get("id") or "",
        "category": category,
        "note": note,
    }
    rows: list[dict] = []
    notices = (profile or {}).get("publicNotices") or []
    if profile is None:
        rows.append({**base, "notice_type": "", "effective_date": "", "completion_date": "", "summary": "",
                     "attachment_count": 0, "attachment_names": "", "download_urls": "", "filenames": "",
                     "case_number": "", "flags": "profile not fetched"})
        return rows
    if not notices:
        rows.append({**base, "notice_type": "", "effective_date": "", "completion_date": "", "summary": "",
                     "attachment_count": 0, "attachment_names": "", "download_urls": "", "filenames": "",
                     "case_number": "", "flags": "disciplined flag set but profile lists no public notice"})
        return rows
    for n in notices:
        atts = [a for a in (n.get("attachments") or []) if a.get("id")]
        names = [a.get("tc_filename") or a.get("tc_name") or "" for a in atts]
        flags = []
        if not atts:
            flags.append("index only, no document")
        non_pdf = [a for a in atts if (a.get("tc_content_type") or "").lower() not in ("", "application/pdf")]
        if non_pdf:
            flags.append("attachment is not application/pdf: " + ", ".join(a.get("tc_content_type") or "?" for a in non_pdf))
        eff = (n.get("effectiveDate") or "").strip()
        if DATE_PATTERN.match(eff):
            eff = eff[:10]          # older notices carry a full timestamp ("1989-10-19T06:00:00.000Z")
        else:
            flags.append("no effective date")
        rows.append({
            **base,
            "notice_type": n.get("noticeType") or "",
            "effective_date": eff,
            "completion_date": n.get("completionDate") or "",
            "summary": strip_html(n.get("summary") or ""),
            "attachment_count": len(atts),
            "attachment_names": " | ".join(names),
            "download_urls": " | ".join(attachment_url(a) for a in atts),
            "filenames": "",
            "case_number": case_number_from(*names, strip_html(n.get("summary") or "")),
            "flags": "; ".join(flags),
        })
    return rows


def assign_filenames(rows: list[dict]) -> None:
    """'Lastname, Firstname LPC04898 2023-04-07.pdf'; a second attachment on the same
    notice (or any later collision) gets ' (2)', ' (3)'."""
    seen: dict[str, int] = {}
    for r in rows:
        if r["category"] == "drop" or not r["attachment_count"]:
            r["filenames"] = ""
            continue
        name_part = f"{r['last_name']}, {r['first_name']}".strip(", ").strip() or "UNKNOWN"
        key = r["license_number"] or r["case_number"]
        if not key:
            r["flags"] = "; ".join(f for f in (r["flags"], "no license or case number") if f)
        date = r["effective_date"][:10] if DATE_PATTERN.match(r["effective_date"]) else "undated"
        base = ILLEGAL_FILENAME.sub("", " ".join(p for p in (name_part, key, date) if p)).strip()
        names = []
        for _ in range(int(r["attachment_count"])):
            n = seen.get(base, 0) + 1
            seen[base] = n
            names.append(f"{base}.pdf" if n == 1 else f"{base} ({n}).pdf")
        r["filenames"] = " | ".join(names)


# --------------------------------------------------------------------------- #
# Manifest, log, download
# --------------------------------------------------------------------------- #

MANIFEST_FIELDS = [
    "last_name", "first_name", "license_number", "registration_category", "status",
    "notice_type", "effective_date", "summary", "attachment_count", "attachment_names",
    "download_urls", "filenames", "category", "note", "flags",
    "case_number", "completion_date", "city", "profile_id",
]


def write_manifest(rows: list[dict]) -> None:
    with MANIFEST_PATH.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=MANIFEST_FIELDS)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in MANIFEST_FIELDS})


def log_row(writer, filename: str, status: str, url: str, message: str = "") -> None:
    writer.writerow({"filename": filename, "status": status, "official_url": url, "message": message})


def download_jobs(rows: list[dict]) -> list[tuple[str, str, str]]:
    """[(filename, url, licensee)] for every attachment on the given rows."""
    jobs = []
    for r in rows:
        files = [f for f in r["filenames"].split(" | ") if f]
        urls = [u for u in r["download_urls"].split(" | ") if u]
        for f, u in zip(files, urls):
            jobs.append((f, u, f"{r['last_name']}, {r['first_name']}"))
    return jobs


def download_all(jobs: list[tuple[str, str, str]]) -> tuple[int, int, int]:
    STATE_FOLDER.mkdir(parents=True, exist_ok=True)
    ok = skipped = failed = 0
    with LOG_PATH.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=["filename", "status", "official_url", "message"])
        writer.writeheader()
        total = len(jobs)
        for i, (filename, url, _who) in enumerate(jobs, 1):
            target = STATE_FOLDER / filename
            if target.exists() and target.stat().st_size > 0:
                skipped += 1
                log_row(writer, filename, "Already downloaded", url)
                print(f"[{i}/{total}] skip  {filename}")
                continue
            try:
                data = fetch(url, binary=True)
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
    ap.add_argument("--include-candidates", action="store_true", help="also download LPC Candidate orders")
    ap.add_argument("--text-check", action="store_true", help="count downloaded PDFs with a text layer (PyMuPDF), then exit")
    ap.add_argument("--debug-json", action="store_true", help="save every JSON reply under downloader\\debug\\")
    args = ap.parse_args(argv)

    if args.text_check:
        return text_check()

    print(f"Oklahoma OBBHL register (Thentia) -> {STATE_FOLDER}")
    print("Pass 1: listing disciplined licensees")
    try:
        records = list_disciplined(debug=args.debug_json)
    except Exception as exc:  # noqa: BLE001
        raise SystemExit(
            f"Could not read the register search: {exc}\n"
            f"Check that {REGISTER_PAGE} opens in a browser. If it does and the script still fails,\n"
            "the register may have started refusing scripted requests; see README.txt."
        ) from exc
    if not records:
        print("The disciplined search returned no records at all. The register or its API may have changed.")
        return 1

    counts: dict[str, int] = {}
    for r in records:
        r["_category"], r["_note"] = classify(r)
        counts[r["_category"]] = counts.get(r["_category"], 0) + 1
    print(f"  {len(records)} disciplined licensees: " + ", ".join(f"{k} {v}" for k, v in sorted(counts.items())))

    print("Pass 2: reading profiles and public notices")
    rows: list[dict] = []
    to_fetch = [r for r in records if r["_category"] in ("counselor", "candidate", "review")]
    for i, r in enumerate(records, 1):
        if r["_category"] == "drop":
            rows.extend(notice_rows(r, None, "drop", r["_note"]))
            continue
        time.sleep(PAUSE_SECONDS)
        try:
            profile = get_profile(r["id"], debug=args.debug_json)
        except Exception as exc:  # noqa: BLE001
            print(f"  [{i}/{len(records)}] FAIL profile {r.get('lastName')}, {r.get('firstName')}: {exc}")
            rows.extend(notice_rows(r, None, r["_category"], f"{r['_note']}; profile fetch failed: {exc}"))
            continue
        found = notice_rows(r, profile, r["_category"], r["_note"])
        n_att = sum(int(x["attachment_count"]) for x in found)
        print(f"  [{i}/{len(records)}] {r.get('lastName')}, {r.get('firstName')} ({license_number(r) or 'no license number'}): "
              f"{len(found)} notice(s), {n_att} attachment(s)")
        rows.extend(found)

    rows.sort(key=lambda x: (x["last_name"].lower(), x["first_name"].lower(), x["effective_date"]))
    assign_filenames(rows)
    write_manifest(rows)

    def tally(cat: str) -> tuple[int, int, int]:
        sub = [x for x in rows if x["category"] == cat and x["notice_type"]]
        return (len({x["profile_id"] for x in sub}), len(sub), sum(int(x["attachment_count"]) for x in sub))

    print(f"\nManifest written: {MANIFEST_PATH}")
    for cat in ("counselor", "candidate", "review"):
        lic, notices, atts = tally(cat)
        if lic or cat == "counselor":
            print(f"  {cat:<10} {lic} licensees, {notices} notices, {atts} attachments")
    print(f"  {'drop':<10} {sum(1 for x in rows if x['category'] == 'drop')} licensees (not fetched)")
    index_only = sum(1 for x in rows if x["category"] == "counselor" and "index only" in x["flags"])
    print(f"  counselor notices without a document (index only): {index_only}")

    if args.list_only:
        return 0

    wanted = {"counselor"}
    if args.include_candidates:
        wanted.add("candidate")
    jobs = download_jobs([x for x in rows if x["category"] in wanted and x["filenames"]])
    print(f"\nPass 3: downloading {len(jobs)} PDF(s) into {STATE_FOLDER}\n")
    download_all(jobs)
    return 0


if __name__ == "__main__":
    sys.exit(main())
