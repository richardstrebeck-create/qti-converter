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

Page layout (verified 2026-09-18 against the 2025-06 archived copy of the site;
the live site refused automated requests): no table. 2017-2023 pages are a
bulleted list, one <li> per action:
    <strong>Name, MA, LCMHC, License #605</strong><br>
    4/21/2017 - On April 21, 2017, the Board ... approved a <a>Settlement Agreement regarding Name, LCMHC</a>
2024-2025 pages are one paragraph per action:
    <strong>Name, LCSW, License #2343,</strong> <a>Voluntary Surrender, 10/18/2024</a>
The license type sits in the bold name segment, so that segment is classified
first; the link text and file name are only a fallback.

Usage (from this folder):
    py download_new_hampshire_orders.py                 # download LCMHC orders
    py download_new_hampshire_orders.py --list-only     # build manifest.csv only
    py download_new_hampshire_orders.py --include-review
    py download_new_hampshire_orders.py --debug-html
    py download_new_hampshire_orders.py --from-saved debug   # parse pages saved as root.html, 2017.html ...
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
from bs4 import BeautifulSoup, NavigableString, Tag

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
    (re.compile(r"\bLADC\b|\bMLADC\b|alcohol|drug counsel", re.I), ("drop", "alcohol & drug counseling")),
    (re.compile(r"unlicensed|non-licensed|no license", re.I), ("drop", "unlicensed")),
    (re.compile(r"candidate|applicant", re.I), ("drop", "candidate / applicant for licensure")),
]
LICENSE_NO = re.compile(r"(?:license|lic\.?|#|no\.?)\s*#?\s*([A-Z]{0,3}\d{3,6})\b", re.I)
DATE_ANY = re.compile(r"\b(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})\b")
DATE_LONG = re.compile(r"\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2}),\s+(\d{4})\b", re.I)
DATE_IN_FILE = re.compile(r"(20\d{2})(\d{2})(\d{2})")
DOC_WORDS = re.compile(
    r"settlement agreement|voluntary surrender|order|agreement|decision|reprimand|"
    r"suspension|revocation|dismissal|probation|\bLCMHC\b|\bLICSW\b|\bLCSW\b|\bMFT\b|\bLMFT\b|"
    r"\bMA\b|\bMS\b|\bMEd\b|\bM\.Ed\.|\bPhD\b|\bPsyD\b|\bLADC\b|\bMLADC\b|license|unlicensed|candidate|applicant",
    re.I,
)
MONTHS = {m: i for i, m in enumerate(
    ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december"], 1)}
ILLEGAL_FILENAME = re.compile(r'[\\/:*?"<>|]+')
# Prefixes the Wayback Machine adds to links when a page is saved from web.archive.org.
WAYBACK_PREFIX = re.compile(r"(?:https?://web\.archive\.org)?/web/\d{4,14}(?:[a-z]{2}_)?/(?=https?://)")

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
        path = urlparse(urljoin(BASE_URL, WAYBACK_PREFIX.sub("", a["href"]))).path.rstrip("/")
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


SUFFIXES = {"jr", "jr.", "sr", "sr.", "ii", "iii", "iv"}


def split_name(text: str) -> tuple[str, str]:
    """'Sara DeValk, LCMHC, License #2564, ...', 'John E. Briggs, Jr, LCMHC' or 'DeValk, Sara ...' -> (last, first)."""
    t = clean_text(text)
    t = DATE_LONG.sub(" ", t)
    t = DATE_ANY.sub(" ", t)
    t = LICENSE_NO.sub(" ", t)
    # Cut at the first document/credential word or a separator.
    t = re.split(r"\s[-|–—]\s|\(", t, maxsplit=1)[0]
    m = DOC_WORDS.search(t)
    if m:
        t = t[: m.start()]
    t = clean_text(t).strip(" ,;:-#")
    if not t:
        return "", ""
    parts = [p.strip() for p in t.split(",") if p.strip()]
    suffix = ""
    if len(parts) >= 2 and parts[1].lower() in SUFFIXES:
        suffix = parts[1]
        parts = [parts[0]] + parts[2:]
    if len(parts) >= 2 and len(parts[0].split()) == 1:
        # "DeValk, Sara" form
        return nice_case(parts[0]), nice_case(" ".join(parts[1].split()[:2]))
    tokens = parts[0].split()
    if tokens and tokens[-1].lower() in SUFFIXES and len(tokens) > 1:
        suffix = tokens.pop()
    if len(tokens) == 1:
        return nice_case(tokens[0]), ""
    tokens = tokens[:4]
    last = nice_case(tokens[-1]) + (f" {suffix.rstrip('.')}" if suffix else "")
    return last, nice_case(" ".join(tokens[:-1]))


def name_segment(container, a) -> str:
    """The bold name at the start of the entry, else the text before the first <br>, else the text before the link."""
    strong = next((t for t in container.find_all("strong") if clean_text(t.get_text())), None)
    if strong is not None:
        return clean_text(strong.get_text(" ", strip=True))
    parts = []
    for node in container.descendants:
        if isinstance(node, Tag) and (node.name == "br" or node is a):
            break
        if isinstance(node, NavigableString) and a not in node.parents:
            parts.append(str(node))
    return clean_text(" ".join(parts))


def find_date(*texts: str) -> str:
    """First date in the texts as YYYY-MM-DD: 'October 20, 2017', '10/09/2024', '6-28-2024', '1/15/21'."""
    for t in texts:
        m = DATE_LONG.search(t or "")
        if m:
            return f"{m.group(3)}-{MONTHS[m.group(1).lower()]:02d}-{int(m.group(2)):02d}"
    for t in texts:
        m = DATE_ANY.search(t or "")
        if m:
            y = m.group(3)
            y = f"20{y}" if len(y) == 2 else y
            return f"{y}-{int(m.group(1)):02d}-{int(m.group(2)):02d}"
    return ""


def parse_year_page(label: str, html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    entries = []
    for a in soup.find_all("a", href=True):
        href = WAYBACK_PREFIX.sub("", a["href"].strip())
        path = urlparse(urljoin(BASE_URL, href)).path
        if not path.lower().endswith(".pdf"):
            continue
        url = urljoin(BASE_URL, href)
        container = row_container(a)
        row_text = clean_text(container.get_text(" ", strip=True))
        link_text = clean_text(a.get_text(" ", strip=True))
        basename = unquote(Path(path).name)
        # 2025 layout: the whole entry is the link text ("Name, LCSW, License #324, Order of Dismissal, 04/18/2025").
        name_text = name_segment(container, a) or link_text

        # The license type printed next to the name settles the profession; the
        # link text and file name are only consulted when the name segment is silent.
        category, note = classify(name_text) if name_text else ("review", "")
        if category == "review":
            category, note = classify(row_text + " " + link_text + " " + basename)

        last = first = ""
        if container.name == "tr":
            cells = container.find_all(["td", "th"])
            if cells:
                last, first = split_name(cells[0].get_text(" ", strip=True))
        if not last and name_text:
            last, first = split_name(name_text)
        if not last:
            last, first = split_name(row_text.replace(link_text, " "))
        if not last:
            m = re.search(r"regarding\s+(.+)$", link_text, re.I)
            last, first = split_name(m.group(1) if m else link_text)

        lic = LICENSE_NO.search(name_text) or LICENSE_NO.search(row_text)
        license_no = lic.group(1).upper() if lic else ""
        # Date: the link label ("Voluntary Surrender, 10/18/2024") or the sentence
        # ("On October 20, 2017, the Board ...") or the leading short date, else the file name.
        action_date = find_date(link_text, row_text.replace(name_text, " "))
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
                "license_type": name_text,
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
    "license_type",
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
    ap.add_argument("--from-saved", metavar="DIR", help="parse pages saved as root.html, 2017.html ... in DIR instead of fetching")
    args = ap.parse_args(argv)

    print(f"New Hampshire Board of Mental Health Practice actions -> {STATE_FOLDER}")
    if args.from_saved:
        folder = Path(args.from_saved)
        if not folder.is_absolute():
            folder = HERE / folder
        page_htmls = []
        for f in sorted(folder.glob("*.htm*")):
            stem = f.stem.lower()
            path = ROOT_PATH if not stem.isdigit() else f"{ROOT_PATH}-{stem}"
            page_htmls.append((path, f.read_text(encoding="utf-8", errors="replace")))
        if not page_htmls:
            raise SystemExit(f"No .html files found in {folder}")
        print(f"Reading {len(page_htmls)} saved page(s) from {folder}")
    else:
        try:
            root_html = fetch(urljoin(BASE_URL, ROOT_PATH))
        except Exception as exc:  # noqa: BLE001
            raise SystemExit(
                f"Could not read the root page: {exc}\n"
                "If the page opens in your browser, the site is refusing automated requests.\n"
                "Save the root page and each year page as root.html, 2017.html, 2018.html ... into\n"
                f"{DEBUG_DIR} and re-run with  --from-saved debug"
            ) from exc
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
        if args.debug_html or (not found and path != ROOT_PATH and not args.from_saved):
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
