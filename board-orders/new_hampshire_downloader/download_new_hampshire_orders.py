"""
New Hampshire Board of Mental Health Practice order downloader (LCMHC only).

The NH Office of Professional Licensure and Certification posts one page per
year of "Board Actions" for the Board of Mental Health Practice. Each row gives
the licensee's name, license type (LCMHC, LICSW, LCSW, MFT, pastoral
psychotherapist, or unlicensed), license number, action type and date, and
links the document PDF. Only Licensed Clinical Mental Health Counselor rows
are downloaded; every other row is recorded in manifest.csv with the reason.

Note: OPLC keeps documents online for about seven years, so the yearly pages
start around 2017. Re-running the script later will pick up new years.

Usage (from this folder):
    py download_new_hampshire_orders.py                 # download LCMHC orders
    py download_new_hampshire_orders.py --list-only     # build manifest.csv only
    py download_new_hampshire_orders.py --include-review
    py download_new_hampshire_orders.py --debug-html
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import re
import sys
import time
from pathlib import Path
from urllib.parse import urljoin, urlparse, unquote

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.oplc.nh.gov"
ROOT_PATH = "/board-mental-health-practice-actions"
FIRST_YEAR = 2017

HERE = Path(__file__).resolve().parent
STATE_FOLDER = HERE.parent
MANIFEST_PATH = HERE / "manifest.csv"
LOG_PATH = HERE / "download_log.csv"
DEBUG_DIR = HERE / "debug"

PAUSE_SECONDS = 1.5
RETRIES = 3
TIMEOUT = 60
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
}

# License-type words that decide the category. First match wins, so the
# counselor rule is checked before the others.
TEXT_RULES = [
    (re.compile(r"\bLCMHC\b|clinical mental health counsel", re.I), ("counselor", "")),
    (re.compile(r"\bLICSW\b|\bLCSW\b|social work", re.I), ("drop", "social work")),
    (re.compile(r"\bL?MFT\b|marriage|family therap", re.I), ("drop", "marriage & family therapy")),
    (re.compile(r"pastoral", re.I), ("drop", "pastoral psychotherapist")),
    (re.compile(r"unlicensed|non-licensed|no license", re.I), ("drop", "unlicensed / applicant")),
]
LICENSE_NO = re.compile(r"(?:license|lic\.?|#|no\.?)\s*#?\s*(\d{3,6})\b", re.I)
DATE_ANY = re.compile(r"\b(\d{1,2})/(\d{1,2})/(\d{4})\b")
DATE_IN_FILE = re.compile(r"(20\d{2})(\d{2})(\d{2})")
DOC_WORDS = re.compile(
    r"settlement agreement|voluntary surrender|order|agreement|decision|reprimand|"
    r"suspension|revocation|dismissal|probation|\bLCMHC\b|\bLICSW\b|\bLCSW\b|\bMFT\b|license",
    re.I,
)
ILLEGAL_FILENAME = re.compile(r'[\\/:*?"<>|]+')

session = requests.Session()
session.headers.update(HEADERS)


def fetch(url: str, binary: bool = False):
    last_err = None
    for attempt in range(1, RETRIES + 1):
        try:
            resp = session.get(url, timeout=TIMEOUT)
            resp.raise_for_status()
            return resp.content if binary else resp.text
        except Exception as exc:  # noqa: BLE001
            last_err = exc
            if attempt < RETRIES:
                time.sleep(PAUSE_SECONDS * attempt)
    raise RuntimeError(f"{url}: {last_err}")


def clean_text(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip()


def year_pages(root_html: str) -> list[str]:
    """Yearly pages: every year from FIRST_YEAR to now, plus anything the root page links."""
    this_year = dt.date.today().year
    pages = [f"{ROOT_PATH}-{y}" for y in range(FIRST_YEAR, this_year + 1)]
    soup = BeautifulSoup(root_html, "html.parser")
    for a in soup.find_all("a", href=True):
        path = urlparse(urljoin(BASE_URL, a["href"])).path.rstrip("/")
        if path.startswith(ROOT_PATH + "-") and path not in pages:
            pages.append(path)
    return pages


def row_container(a):
    for parent in a.parents:
        if parent.name in ("tr", "li", "p"):
            return parent
        if parent.name in ("table", "ul", "ol", "body"):
            break
    return a.parent


def classify(text: str) -> tuple[str, str]:
    for pattern, verdict in TEXT_RULES:
        if pattern.search(text):
            return verdict
    return ("review", "license type not recognised in row text")


def nice_case(s: str) -> str:
    """Title-case only words written in all caps or all lower; keep 'DeValk', 'McCoy' as written."""
    return " ".join(w.title() if (w.isupper() or w.islower()) else w for w in s.split())


def split_name(text: str) -> tuple[str, str]:
    """'Sara DeValk, LCMHC, License #2564, ...' or 'DeValk, Sara ...' -> (last, first)."""
    t = clean_text(text)
    t = DATE_ANY.sub(" ", t)
    t = LICENSE_NO.sub(" ", t)
    # Cut at the first document/credential word or a separator.
    t = re.split(r"\s[-|–]\s|\(", t, maxsplit=1)[0]
    m = DOC_WORDS.search(t)
    if m:
        t = t[: m.start()]
    t = clean_text(t).strip(" ,;:-#")
    if not t:
        return "", ""
    parts = [p.strip() for p in t.split(",") if p.strip()]
    if len(parts) >= 2 and len(parts[0].split()) == 1:
        # "DeValk, Sara" form
        return nice_case(parts[0]), nice_case(" ".join(parts[1].split()[:2]))
    tokens = parts[0].split()
    if len(tokens) == 1:
        return nice_case(tokens[0]), ""
    tokens = tokens[:4]
    return nice_case(tokens[-1]), nice_case(" ".join(tokens[:-1]))


def parse_year_page(label: str, html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    entries = []
    for a in soup.find_all("a", href=True):
        path = urlparse(urljoin(BASE_URL, a["href"])).path
        if not path.lower().endswith(".pdf"):
            continue
        url = urljoin(BASE_URL, a["href"])
        container = row_container(a)
        row_text = clean_text(container.get_text(" ", strip=True))
        link_text = clean_text(a.get_text(" ", strip=True))
        basename = unquote(Path(path).name)
        category, note = classify(row_text + " " + link_text + " " + basename)

        last = first = ""
        if container.name == "tr":
            cells = container.find_all(["td", "th"])
            if cells:
                last, first = split_name(cells[0].get_text(" ", strip=True))
        if not last:
            last, first = split_name(row_text.replace(link_text, " "))
        if not last:
            last, first = split_name(link_text)

        lic = LICENSE_NO.search(row_text)
        license_no = lic.group(1) if lic else ""
        d = DATE_ANY.search(row_text)
        action_date = f"{d.group(3)}-{int(d.group(1)):02d}-{int(d.group(2)):02d}" if d else ""
        if not action_date:
            f = DATE_IN_FILE.search(basename)
            if f:
                action_date = f"{f.group(1)}-{f.group(2)}-{f.group(3)}"

        flags = []
        if not last:
            flags.append("name not parsed")
        if not action_date:
            flags.append("no date")
        entries.append(
            {
                "index_page": label,
                "index_text": row_text,
                "doc_label": link_text,
                "last_name": last,
                "first_name": first,
                "license_no": license_no,
                "action_date": action_date,
                "category": category,
                "category_note": note,
                "flags": "; ".join(flags),
                "filename": "",
                "official_url": url,
            }
        )
    return entries


def assign_filenames(entries: list[dict]) -> None:
    """'DeValk, Sara LCMHC2564 2023-08-18.pdf'; duplicates get ' (2)'."""
    seen: dict[str, int] = {}
    for e in entries:
        if e["category"] == "drop":
            continue
        name_part = f"{e['last_name']}, {e['first_name']}".strip(", ").strip() or "UNKNOWN"
        key = " ".join(
            p for p in (f"LCMHC{e['license_no']}" if e["license_no"] else "", e["action_date"]) if p
        ) or unquote(Path(urlparse(e["official_url"]).path).stem)
        base = ILLEGAL_FILENAME.sub("", f"{name_part} {key}").strip()
        n = seen.get(base, 0) + 1
        seen[base] = n
        e["filename"] = f"{base}.pdf" if n == 1 else f"{base} ({n}).pdf"


MANIFEST_FIELDS = [
    "index_page", "index_text", "doc_label", "last_name", "first_name", "license_no",
    "action_date", "category", "category_note", "flags", "filename", "official_url",
]


def write_manifest(entries: list[dict]) -> None:
    with MANIFEST_PATH.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=MANIFEST_FIELDS)
        w.writeheader()
        w.writerows(entries)


def download_entries(entries: list[dict]) -> None:
    STATE_FOLDER.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=["filename", "status", "official_url", "message"])
        writer.writeheader()
        total, ok, skipped, failed = len(entries), 0, 0, 0
        for i, e in enumerate(entries, 1):
            target = STATE_FOLDER / e["filename"]
            row = {"filename": e["filename"], "official_url": e["official_url"], "message": ""}
            if target.exists() and target.stat().st_size > 0:
                skipped += 1
                writer.writerow({**row, "status": "Already downloaded"})
                print(f"[{i}/{total}] skip  {e['filename']}")
                continue
            try:
                data = fetch(e["official_url"], binary=True)
                if not data.startswith(b"%PDF"):
                    raise RuntimeError("response is not a PDF")
                target.write_bytes(data)
                ok += 1
                writer.writerow({**row, "status": "Downloaded", "message": f"{len(data)} bytes"})
                print(f"[{i}/{total}] saved {e['filename']} ({len(data):,} bytes)")
            except Exception as exc:  # noqa: BLE001
                failed += 1
                writer.writerow({**row, "status": "FAILED", "message": str(exc)})
                print(f"[{i}/{total}] FAIL  {e['filename']}: {exc}")
            fh.flush()
            time.sleep(PAUSE_SECONDS)
    print(f"\nDone. Downloaded {ok}, already present {skipped}, failed {failed}. Log: {LOG_PATH}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--list-only", action="store_true")
    ap.add_argument("--include-review", action="store_true")
    ap.add_argument("--debug-html", action="store_true")
    args = ap.parse_args(argv)

    print(f"New Hampshire Board of Mental Health Practice actions -> {STATE_FOLDER}")
    root_html = fetch(urljoin(BASE_URL, ROOT_PATH))
    pages = year_pages(root_html)
    page_htmls = [(ROOT_PATH, root_html)]
    for path in pages:
        time.sleep(PAUSE_SECONDS)
        try:
            page_htmls.append((path, fetch(urljoin(BASE_URL, path))))
        except Exception as exc:  # noqa: BLE001
            print(f"  WARNING could not read {path}: {exc}")

    all_entries: list[dict] = []
    for path, html in page_htmls:
        label = path.rsplit("-", 1)[-1] if path != ROOT_PATH else "root"
        found = parse_year_page(label, html)
        print(f"  {label:<6} {len(found):>4} PDF links")
        all_entries.extend(found)
        if args.debug_html or (not found and path != ROOT_PATH):
            DEBUG_DIR.mkdir(exist_ok=True)
            (DEBUG_DIR / f"{label}.html").write_text(html, encoding="utf-8")

    unique: dict[str, dict] = {}
    for e in all_entries:
        unique.setdefault(e["official_url"], e)
    all_entries = list(unique.values())
    if not all_entries:
        print(f"\nNo PDF links found. Fetched pages are under {DEBUG_DIR}; compare with the live site.")
        return 1

    assign_filenames(all_entries)
    write_manifest(all_entries)
    counts: dict[str, int] = {}
    for e in all_entries:
        counts[e["category"]] = counts.get(e["category"], 0) + 1
    print(f"\nManifest written: {MANIFEST_PATH}\n  " + ", ".join(f"{k}: {v}" for k, v in sorted(counts.items())))
    if args.list_only:
        return 0
    wanted = {"counselor"} | ({"review"} if args.include_review else set())
    todo = [e for e in all_entries if e["category"] in wanted]
    print(f"\nDownloading {len(todo)} PDF(s) into {STATE_FOLDER}\n")
    download_entries(todo)
    return 0


if __name__ == "__main__":
    sys.exit(main())
