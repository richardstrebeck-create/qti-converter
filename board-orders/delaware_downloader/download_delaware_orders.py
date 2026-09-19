"""
Delaware Board of Mental Health and Chemical Dependency Professionals order
downloader (Professional Counselors of Mental Health).

Delaware keeps two public systems that between them give the full picture
(verified 2026-09-19):

  pass 1  index    https://data.delaware.gov/api/views/dz6p-akeq/rows.csv?accessType=DOWNLOAD
          the Open Data Portal's "Disciplinary Actions for Professional and
          Occupational Licensees": one row per action for every Division of
          Professional Regulation (DPR) licensee. Columns include License
          Type, License_no, disciplinary_action, disp_start, disp_end. Rows
          with License Type "Professional Counselor of Mental Health" are
          the counselors. This is the INDEX: who has an action, which kind,
          when. It has no document links.
  pass 2  DELPROS  https://delpros.delaware.gov/OH_VerifyLicense
          the license-verification site (Salesforce). Its search runs
          through Visualforce JavaScript remoting (POST /apexremote); the
          per-method CSRF and authorization tokens are printed in the page
          and are reused for the run. For each counselor license number the
          script calls findLicensesForOwner (by license number), takes the
          Mental Health license record, then getSubmissionList on that
          record's id, which returns the licensee's Board Order documents:
          a name, a description ("Consent Agreement", "Disciplinary Order
          2016", "Board Order") and a public Salesforce content-delivery
          link. This is the DOCUMENT list.
  pass 3  the documents themselves.

The catch, and why pass 3 is usually a short by-hand step: the delivery
links are Salesforce "content delivery" pages, not files. Opening one in a
browser shows the PDF with a Download button, but the bytes are fetched by
a Lightning component after the page runs JavaScript, so a plain HTTP
client (this script) cannot pull the file. The script therefore does two
things in pass 3:

  * it TRIES a direct download of each link; if Delaware ever serves the
    file directly it is saved and checked to start with %PDF;
  * for every link that comes back as the viewer page instead of a file
    (the normal case), it writes the document to manifest.csv with its
    delivery URL and marks it "manual" in download_log.csv, and it builds
    manual_downloads.html in the state folder: a page of the delivery
    links grouped by licensee. Open that file, click each link, and use
    the browser's Download button to save the PDF into the state folder
    under the name manifest.csv gives it. About 38 files on 2026-09-19.

Counselors whose action is in the open-data index but who have no record
in DELPROS (old licenses that predate the system) are kept as index-only
rows, the same way the Colorado downloader keeps roster actions with no
document. Chemical Dependency Professional and Marriage and Family
Therapist rows under the same board are recorded as dropped, with the
reason, and never fetched.

Built to mirror the Oklahoma, Texas and Colorado downloaders: same flags,
same manifest and log layout, same filename convention.

Usage (from this folder):
    py download_delaware_orders.py                 # index, DELPROS document list, then pass 3
    py download_delaware_orders.py --list-only     # build manifest.csv only
    py download_delaware_orders.py --max-downloads N
    py download_delaware_orders.py --text-check    # count downloaded PDFs with a text layer (PyMuPDF)
    py download_delaware_orders.py --skip-index    # reuse the CSV already in downloader\\index\\

Needs: requests and beautifulsoup4 (py -m pip install requests beautifulsoup4).
PyMuPDF only for --text-check.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import html
import json
import re
import sys
import time
from pathlib import Path

import requests

# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #

CSV_URL = "https://data.delaware.gov/api/views/dz6p-akeq/rows.csv?accessType=DOWNLOAD"
DELPROS_FORM_URL = "https://delpros.delaware.gov/OH_VerifyLicense"
DELPROS_REMOTE_URL = "https://delpros.delaware.gov/apexremote"
CONTROLLER = "OH_VerifyLicenseCtlr"

# Open-data "License Type" values under the Mental Health board and what to
# do with each. Only the counselor is kept.
COUNSELOR_TYPE = "Professional Counselor of Mental Health"
DROP_TYPES = {
    "Chemical Dependency Professional": "chemical dependency professional (LCDP), same board, not a counselor",
    "Marriage and Family Therapist": "marriage and family therapist (LMFT), same board, not a counselor",
}

# The remoting search field order, taken from the page's getSearchFields().
SEARCH_FIELDS = [
    "firstName", "lastName", "middleName", "contactAlias", "board", "licenseType",
    "licenseNumber", "city", "state", "county", "businessBoard", "businessLicenseType",
    "businessLicenseNumber", "businessCity", "businessState", "businessCounty",
    "businessName", "dbafileld", "searchType",
]

HERE = Path(__file__).resolve().parent           # ...\state_data\Delaware\downloader
STATE_FOLDER = HERE.parent                        # ...\state_data\Delaware
INDEX_DIR = HERE / "index"
MANIFEST_PATH = HERE / "manifest.csv"
LOG_PATH = HERE / "download_log.csv"
MANUAL_HTML = STATE_FOLDER / "manual_downloads.html"

PAUSE_SECONDS = 1.5
RETRIES = 3
TIMEOUT = 90
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

ILLEGAL_FILENAME = re.compile(r'[\\/:*?"<>|]+')
US_DATE = re.compile(r"^(\d{1,2})/(\d{1,2})/(\d{4})$")
YEAR = re.compile(r"(19|20)\d{2}")

session = requests.Session()
session.headers.update(HEADERS)


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #

def fetch(url, *, method="GET", data=None, params=None, json_body=None, binary=False,
          timeout=TIMEOUT, extra_headers=None):
    last = None
    for attempt in range(1, RETRIES + 1):
        try:
            resp = session.request(method, url, data=data, params=params, json=json_body,
                                   timeout=timeout, headers=extra_headers)
            resp.raise_for_status()
            return resp.content if binary else resp.text
        except Exception as exc:  # noqa: BLE001
            last = exc
            if attempt < RETRIES:
                time.sleep(PAUSE_SECONDS * attempt)
    raise RuntimeError(f"{url}: {last}")


def iso_date(us):
    m = US_DATE.match((us or "").strip())
    if not m:
        return (us or "").strip()
    mm, dd, yyyy = m.groups()
    try:
        return dt.date(int(yyyy), int(mm), int(dd)).isoformat()
    except ValueError:
        return us.strip()


def nice_case(s):
    s = (s or "").strip()
    return " ".join(w.title() if (w.isupper() or w.islower()) else w for w in s.split())


def split_name(combined, last_fallback="", first_fallback=""):
    """The open-data 'Combined Name' is 'LAST,FIRST MIDDLE'."""
    if combined and "," in combined:
        last, rest = combined.split(",", 1)
        return nice_case(last.strip()), nice_case(rest.strip())
    return nice_case(last_fallback), nice_case(first_fallback)


# --------------------------------------------------------------------------- #
# Pass 1: open-data index
# --------------------------------------------------------------------------- #

def load_index(skip_index=False):
    INDEX_DIR.mkdir(exist_ok=True)
    csv_path = INDEX_DIR / "disciplinary_actions.csv"
    if not (skip_index and csv_path.exists()):
        data = fetch(CSV_URL, binary=True, timeout=300)
        csv_path.write_bytes(data)
    text = csv_path.read_text(encoding="utf-8-sig", errors="replace")
    rows = list(csv.DictReader(text.splitlines()))
    counselors = {}   # license number -> {name parts, actions[]}
    dropped = []
    for r in rows:
        r = {(k or "").strip(): (v or "").strip() for k, v in r.items()}
        lt = r.get("License Type", "")
        lic = r.get("License_no", "")
        if lt == COUNSELOR_TYPE:
            last, first = split_name(r.get("Combined Name", ""), r.get("Last Name", ""), r.get("First Name", ""))
            p = counselors.setdefault(lic, {"last": last, "first": first, "actions": []})
            p["actions"].append({
                "action": r.get("disciplinary_action", ""),
                "start": iso_date(r.get("disp_start", "")),
                "end": iso_date(r.get("disp_end", "")),
            })
        elif lt in DROP_TYPES:
            dropped.append((lic, r.get("Combined Name", ""), lt))
    return counselors, dropped


# --------------------------------------------------------------------------- #
# Pass 2: DELPROS document list (Visualforce remoting)
# --------------------------------------------------------------------------- #

class Delpros:
    def __init__(self):
        html_text = fetch(DELPROS_FORM_URL)
        marker = "Visualforce.remoting.Manager.add(new $VFRM.RemotingProviderImpl("
        i = html_text.find(marker)
        if i < 0:
            raise RuntimeError("DELPROS page has no remoting descriptor; the site may have changed")
        tail = html_text[i + len(marker):]
        blob = tail[:tail.find("));")]
        blob = blob[:blob.rfind("}") + 1]
        desc = json.loads(blob)
        self.vid = desc["vf"]["vid"]
        self.methods = {m["name"]: m for m in desc["actions"][CONTROLLER]["ms"]}
        self.tid = 1

    def call(self, method, data):
        m = self.methods[method]
        self.tid += 1
        payload = {
            "action": CONTROLLER, "method": method, "data": data, "type": "rpc", "tid": self.tid,
            "ctx": {"csrf": m["csrf"], "vid": self.vid, "ns": "", "ver": 46, "authorization": m["authorization"]},
        }
        time.sleep(PAUSE_SECONDS)
        out = fetch(DELPROS_REMOTE_URL, method="POST", json_body=payload,
                    extra_headers={"Referer": DELPROS_FORM_URL, "Content-Type": "application/json"})
        arr = json.loads(out)
        return arr[0] if arr else {}

    def documents_for(self, license_number):
        """Return (found_record, [documents]) for one counselor license number."""
        fields = {k: "" for k in SEARCH_FIELDS}
        fields["licenseNumber"] = license_number
        fields["searchType"] = "individual"
        res = self.call("findLicensesForOwner", [fields])
        recs = [x for x in res.get("result", []) if isinstance(x, dict) and "license" in x]
        mh = [x for x in recs if x.get("Board") == "Mental Health"
              and x.get("license", {}).get("Name") == license_number]
        docs = []
        for m in mh:
            subs = self.call("getSubmissionList", [m["license"]["Id"]])
            for d in (subs.get("result", []) if isinstance(subs, dict) else []):
                docs.append({
                    "doc_name": d.get("Name", ""),
                    "description": d.get("MUSW__Description__c", ""),
                    "url": d.get("MUSW__Link__c", ""),
                })
        return bool(mh), docs


# --------------------------------------------------------------------------- #
# Build manifest rows
# --------------------------------------------------------------------------- #

def doc_year(doc):
    for field in (doc["description"], doc["doc_name"]):
        m = YEAR.search(field or "")
        if m:
            return m.group(0)
    return ""


def slug(text, n=40):
    text = re.sub(r"\.pdf$", "", (text or "").strip(), flags=re.I)
    text = ILLEGAL_FILENAME.sub("", text)
    return text[:n].strip()


def build_rows(counselors, delpros, dropped):
    rows = []
    for lic, p in counselors.items():
        actions = p["actions"]
        action_label = " | ".join(a["action"] for a in actions if a["action"])
        start = " | ".join(a["start"] for a in actions if a["start"])
        end = " | ".join(a["end"] for a in actions if a["end"])
        found, docs = delpros.documents_for(lic)
        if not docs:
            rows.append({
                "last_name": p["last"], "first_name": p["first"], "license_number": lic,
                "license_type": COUNSELOR_TYPE, "action": action_label,
                "start_date": start, "end_date": end, "document_name": "",
                "description": "", "url": "", "filename": "",
                "category": "counselor", "flags": "index only, no document in DELPROS" if not found
                else "record in DELPROS but no board-order document attached",
            })
            continue
        for d in docs:
            rows.append({
                "last_name": p["last"], "first_name": p["first"], "license_number": lic,
                "license_type": COUNSELOR_TYPE, "action": action_label,
                "start_date": start, "end_date": end,
                "document_name": d["doc_name"], "description": d["description"],
                "url": d["url"], "filename": "", "category": "counselor", "flags": "",
            })
    for lic, name, lt in dropped:
        last, first = split_name(name)
        rows.append({
            "last_name": last, "first_name": first, "license_number": lic,
            "license_type": lt, "action": "", "start_date": "", "end_date": "",
            "document_name": "", "description": "", "url": "", "filename": "",
            "category": "drop", "flags": DROP_TYPES[lt],
        })
    rows.sort(key=lambda r: (r["category"] != "counselor", r["last_name"].lower(),
                             r["first_name"].lower(), r["start_date"]))
    assign_filenames(rows)
    return rows


def assign_filenames(rows):
    seen = {}
    for r in rows:
        if not r["url"]:
            continue
        name = f"{r['last_name']}, {r['first_name']}".strip(", ").strip() or "UNKNOWN"
        year = doc_year({"description": r["description"], "doc_name": r["document_name"]}) or (r["start_date"][:4] if r["start_date"] else "")
        desc = slug(r["description"] or r["document_name"])
        base = ILLEGAL_FILENAME.sub("", " ".join(x for x in (f"{name} {r['license_number']}", year, "- " + desc if desc else "") if x)).strip()
        n = seen.get(base, 0) + 1
        seen[base] = n
        r["filename"] = f"{base}.pdf" if n == 1 else f"{base} ({n}).pdf"


# --------------------------------------------------------------------------- #
# Manifest, manual page, downloads
# --------------------------------------------------------------------------- #

MANIFEST_FIELDS = ["last_name", "first_name", "license_number", "license_type", "action",
                   "start_date", "end_date", "document_name", "description", "url",
                   "filename", "category", "flags"]


def write_manifest(rows):
    with MANIFEST_PATH.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=MANIFEST_FIELDS)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in MANIFEST_FIELDS})


def write_manual_page(rows):
    jobs = [r for r in rows if r["url"]]
    by_person = {}
    for r in jobs:
        by_person.setdefault((r["last_name"], r["first_name"], r["license_number"]), []).append(r)
    parts = [
        "<!doctype html><html><head><meta charset='utf-8'>",
        "<title>Delaware counselor board orders - manual download list</title>",
        "<style>body{font-family:Segoe UI,Arial,sans-serif;margin:2em;max-width:60em}"
        "h1{font-size:1.3em}li{margin:.3em 0}code{background:#eee;padding:0 .3em}"
        ".person{margin:1em 0 .3em;font-weight:bold}</style></head><body>",
        "<h1>Delaware counselor board orders</h1>",
        f"<p>{len(jobs)} documents for {len(by_person)} licensees. For each link: click it, "
        "wait for the Salesforce viewer, use its Download button, and save the file into this "
        "folder under the name shown in <code>parentheses</code>.</p>",
    ]
    for (last, first, lic), docs in sorted(by_person.items()):
        parts.append(f"<div class='person'>{html.escape(last)}, {html.escape(first)} &mdash; {html.escape(lic)}</div><ul>")
        for r in docs:
            parts.append(
                f"<li><a href='{html.escape(r['url'])}' target='_blank'>{html.escape(r['description'] or r['document_name'] or 'document')}</a> "
                f"&rarr; save as <code>{html.escape(r['filename'])}</code></li>"
            )
        parts.append("</ul>")
    parts.append("</body></html>")
    MANUAL_HTML.write_text("\n".join(parts), encoding="utf-8")


def try_download(rows, limit=0):
    STATE_FOLDER.mkdir(parents=True, exist_ok=True)
    jobs = [r for r in rows if r["url"] and r["filename"]]
    if limit:
        jobs = jobs[:limit]
    ok = manual = skipped = 0
    with LOG_PATH.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["filename", "status", "official_url", "message"])
        w.writeheader()
        for i, r in enumerate(jobs, 1):
            target = STATE_FOLDER / r["filename"]
            if target.exists() and target.stat().st_size > 0:
                skipped += 1
                w.writerow({"filename": r["filename"], "status": "Already downloaded",
                            "official_url": r["url"], "message": ""})
                print(f"[{i}/{len(jobs)}] skip  {r['filename']}")
                continue
            data = b""
            try:
                data = fetch(r["url"], binary=True)
            except Exception as exc:  # noqa: BLE001
                data = b""
            if data.startswith(b"%PDF"):
                target.write_bytes(data)
                ok += 1
                w.writerow({"filename": r["filename"], "status": "Downloaded",
                            "official_url": r["url"], "message": f"{len(data)} bytes"})
                print(f"[{i}/{len(jobs)}] saved {r['filename']}")
            else:
                manual += 1
                w.writerow({"filename": r["filename"], "status": "MANUAL",
                            "official_url": r["url"],
                            "message": "Salesforce delivery viewer; save by hand from manual_downloads.html"})
                print(f"[{i}/{len(jobs)}] manual {r['filename']}")
            fh.flush()
            time.sleep(PAUSE_SECONDS)
    print(f"\nDone. Downloaded {ok}, to save by hand {manual}, already present {skipped}.")
    if manual:
        print(f"Open {MANUAL_HTML} and save the {manual} remaining files by hand.")
    return ok, manual, skipped


# --------------------------------------------------------------------------- #
# --text-check
# --------------------------------------------------------------------------- #

def text_check(min_chars=200):
    try:
        import pymupdf
    except ImportError:
        try:
            import fitz as pymupdf
        except ImportError:
            print("PyMuPDF is not installed; run  py -m pip install pymupdf")
            return 1
    pdfs = sorted(STATE_FOLDER.glob("*.pdf"))
    if not pdfs:
        print(f"No PDFs found in {STATE_FOLDER}")
        return 1
    with_text = without = unreadable = 0
    scans = []
    for p in pdfs:
        try:
            with pymupdf.open(p) as doc:
                chars = sum(len(pg.get_text()) for pg in doc)
        except Exception:  # noqa: BLE001
            unreadable += 1
            continue
        if chars >= min_chars:
            with_text += 1
        else:
            without += 1
            scans.append(p.name)
    print(f"\nText-layer check of {len(pdfs)} PDF(s) (threshold {min_chars} chars):")
    print(f"  with a text layer: {with_text}")
    print(f"  image only (OCR):  {without}")
    print(f"  unreadable:        {unreadable}")
    for n in scans:
        print(f"    OCR: {n}")
    return 0


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #

def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--list-only", action="store_true", help="build manifest.csv and manual_downloads.html, download nothing")
    ap.add_argument("--skip-index", action="store_true", help="reuse the CSV already in downloader\\index\\")
    ap.add_argument("--max-downloads", type=int, default=0, help="stop pass 3 after this many documents")
    ap.add_argument("--text-check", action="store_true", help="count downloaded PDFs with a text layer (PyMuPDF), then exit")
    args = ap.parse_args(argv)

    if args.text_check:
        return text_check()

    print(f"Delaware DPR (open-data index + DELPROS documents) -> {STATE_FOLDER}")
    print("Pass 1: open-data disciplinary-actions CSV")
    counselors, dropped = load_index(skip_index=args.skip_index)
    n_actions = sum(len(p["actions"]) for p in counselors.values())
    print(f"  {len(counselors)} counselors with an action ({n_actions} action rows); "
          f"{len(dropped)} other Mental Health board rows dropped")

    print("Pass 2: DELPROS board-order documents per counselor")
    try:
        delpros = Delpros()
    except Exception as exc:  # noqa: BLE001
        raise SystemExit(f"Could not read the DELPROS page: {exc}\nCheck that {DELPROS_FORM_URL} opens in a browser.")
    rows = build_rows(counselors, delpros, dropped)
    write_manifest(rows)
    write_manual_page(rows)

    docs = [r for r in rows if r["url"]]
    people = {r["license_number"] for r in docs}
    indexonly = [r for r in rows if r["category"] == "counselor" and not r["url"]]
    print(f"\nManifest written: {MANIFEST_PATH}")
    print(f"  {len(docs)} board-order documents for {len(people)} counselors")
    print(f"  {len(indexonly)} counselors are index-only (no document in DELPROS)")
    print(f"  {sum(1 for r in rows if r['category']=='drop')} other-profession rows dropped")
    print(f"  manual download page: {MANUAL_HTML}")

    if args.list_only:
        return 0

    print("\nPass 3: fetching documents (Salesforce delivery links are usually browser-only)\n")
    try_download(rows, limit=args.max_downloads)
    return 0


if __name__ == "__main__":
    sys.exit(main())
