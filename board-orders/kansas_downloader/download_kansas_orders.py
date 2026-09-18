"""
Kansas BSRB disciplinary-order downloader (Licensed Professional Counselors).

Collects order PDFs for professional counselors (LPC / LCPC) from the Kansas
Behavioral Sciences Regulatory Board's public "Disciplinary Actions" index,
which is split into seven last-name pages (A-C, D-F, G-J, K-M, N-Q, R-V, W-Z).
Every entry found on the index is written to manifest.csv with a category
(counselor / drop / review); only "counselor" entries are downloaded unless
you pass --include-review or --include-all.

Built from the Maryland downloader's behaviour: sequential downloads with a
polite pause, three retries, a real-PDF check, skip-if-present, and a
download_log.csv of every outcome.

Usage (from this folder):
    py download_kansas_orders.py                 # download counselor orders
    py download_kansas_orders.py --list-only     # build manifest.csv only
    py download_kansas_orders.py --include-review
    py download_kansas_orders.py --include-all   # every profession (not needed for the LPC dataset)
    py download_kansas_orders.py --debug-html    # also save the fetched index pages to downloader\debug\
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
import time
from pathlib import Path
from urllib.parse import urljoin, urlparse, unquote

import requests
from bs4 import BeautifulSoup

# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #

BASE_URL = "https://www.ksbsrb.ks.gov"
INDEX_ROOT = "/complaints/disciplinary-actions"
# Letter pages seen in the search index (2026-09). The script also discovers
# any other sub-page linked from the root page, so a renamed page is not lost.
KNOWN_SUBPAGES = ["a-c", "d-f", "g-j", "k-m", "n-q", "r-v", "w-z"]

HERE = Path(__file__).resolve().parent            # ...\state_data\Kansas\downloader
STATE_FOLDER = HERE.parent                         # ...\state_data\Kansas
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
    "Accept": "text/html,application/xhtml+xml,application/pdf;q=0.9,*/*;q=0.8",
}

# Case numbers look like 22-PC-0163 (year, profession code, sequence).
# Very old ones look like 96-0608 (no profession code).
CASE_WITH_CODE = re.compile(r"\b(\d{2})-([A-Za-z]{2,4})-(\d{3,5})\b")
CASE_LEGACY = re.compile(r"\b(\d{2})-(\d{4})\b")

# Profession codes embedded in Kansas case numbers. PC is the one we want.
# Anything not listed here is sent to "review" rather than guessed.
CODE_MAP = {
    "PC": ("counselor", ""),
    "SW": ("drop", "social work"),
    "BS": ("drop", "social work (baccalaureate/BSRB social work code)"),
    "MS": ("drop", "social work (master's)"),
    "CS": ("drop", "social work (clinical)"),
    "MF": ("drop", "marriage & family therapy"),
    "MFT": ("drop", "marriage & family therapy"),
    "AC": ("drop", "addiction counseling"),
    "PS": ("drop", "psychology"),
    "PSY": ("drop", "psychology"),
    "MP": ("drop", "master's level psychology"),
    "MLP": ("drop", "master's level psychology"),
    "BA": ("drop", "behavior analysis"),
}

# Words in the entry text that settle the profession when the code does not.
TEXT_RULES = [
    (re.compile(r"professional counsel|\bLPC\b|\bLCPC\b", re.I), ("counselor", "")),
    (re.compile(r"social work|\bLSCSW\b|\bLMSW\b|\bLBSW\b", re.I), ("drop", "social work")),
    (re.compile(r"marriage|family therap|\bLMFT\b|\bLCMFT\b", re.I), ("drop", "marriage & family therapy")),
    (re.compile(r"addiction|alcohol|drug|\bLAC\b|\bLCAC\b", re.I), ("drop", "addiction counseling")),
    (re.compile(r"psycholog|\bLP\b|\bLMLP\b|\bLCP\b", re.I), ("drop", "psychology")),
    (re.compile(r"behavior analy|\bLBA\b|\bBCBA\b", re.I), ("drop", "behavior analysis")),
]

DOC_WORDS = re.compile(
    r"consent agreement|order|agreement|summary proceeding|revocation|suspension|"
    r"reprimand|censure|probation|surrender|stipulation|final|decision|\.pdf",
    re.I,
)
DATE_PATTERN = re.compile(r"\b\d{1,2}/\d{1,2}/\d{2,4}\b|\b[A-Z][a-z]+ \d{1,2}, \d{4}\b")
ILLEGAL_FILENAME = re.compile(r'[\\/:*?"<>|]+')

session = requests.Session()
session.headers.update(HEADERS)


# --------------------------------------------------------------------------- #
# Fetching
# --------------------------------------------------------------------------- #

def fetch(url: str, binary: bool = False):
    """GET with retries. Returns text (or bytes when binary=True)."""
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


def discover_index_pages(root_html: str) -> list[str]:
    """Known letter pages plus any other sub-page linked from the root page."""
    pages = [INDEX_ROOT + "/" + s for s in KNOWN_SUBPAGES]
    soup = BeautifulSoup(root_html, "html.parser")
    for a in soup.find_all("a", href=True):
        path = urlparse(urljoin(BASE_URL, a["href"])).path.rstrip("/").lower()
        if path.startswith(INDEX_ROOT + "/") and path != INDEX_ROOT and path not in pages:
            if not path.lower().endswith(".pdf"):
                pages.append(path)
    return pages


# --------------------------------------------------------------------------- #
# Parsing one index page into entries
# --------------------------------------------------------------------------- #

def row_container(a):
    """Nearest ancestor that represents one index entry (table row, list item, paragraph)."""
    for parent in a.parents:
        if parent.name in ("tr", "li", "p"):
            return parent
        if parent.name in ("table", "ul", "ol", "body"):
            break
    return a.parent


def clean_text(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip()


def extract_case(*texts: str) -> tuple[str, str]:
    """Return (case_number, code) from the first text that contains one."""
    for t in texts:
        m = CASE_WITH_CODE.search(t or "")
        if m:
            return f"{m.group(1)}-{m.group(2).upper()}-{m.group(3)}", m.group(2).upper()
    for t in texts:
        m = CASE_LEGACY.search(t or "")
        if m:
            return f"{m.group(1)}-{m.group(2)}", ""
    return "", ""


def classify(code: str, text: str) -> tuple[str, str]:
    """Decide counselor / drop / review from the case code, then the entry text."""
    if code in CODE_MAP:
        return CODE_MAP[code]
    for pattern, verdict in TEXT_RULES:
        if pattern.search(text):
            return verdict
    return ("review", "no profession code or keyword found")


PROFESSION_WORDS = re.compile(
    r"\b(licensed|specialist|clinical|professional|master'?s?( level)?|temporary|provisional|"
    r"baccalaureate|addiction|alcohol|drug|marriage|family|social|behavior|behavioral|"
    r"counselor|counseling|worker|therapist|therapy|psychologist|psychology|analyst|"
    r"LPC|LCPC|LMFT|LCMFT|LSCSW|LMSW|LBSW|LAC|LCAC|LP|LMLP|LCP|LBA|BCBA|and)\b",
    re.I,
)


def split_name(text: str) -> tuple[str, str, str]:
    """
    Pull (last, first, raw) out of the entry text. Handles "Last, First ..." and
    "First Last ..." after stripping document words, dates, case numbers and
    profession phrases.
    """
    raw = clean_text(text)
    scrub = CASE_WITH_CODE.sub(" ", raw)
    scrub = CASE_LEGACY.sub(" ", scrub)
    scrub = DATE_PATTERN.sub(" ", scrub)
    # Cut at the first document-type word, a pipe, a dash separator, or a parenthesis.
    cut = re.split(r"\s[-|–]\s|\(|\bPDF\b", scrub, maxsplit=1)[0]
    m = DOC_WORDS.search(cut)
    if m:
        cut = cut[: m.start()]
    cut = PROFESSION_WORDS.sub(" ", cut)
    cut = clean_text(cut).strip(" ,;:-")
    if not cut:
        return "", "", raw
    if "," in cut:
        last, first = [clean_text(p) for p in cut.split(",", 1)]
        first = " ".join(first.split()[:2])   # given name + middle initial at most
        return last.title(), first.title(), raw
    tokens = cut.split()
    if len(tokens) == 1:
        return tokens[0].title(), "", raw
    tokens = tokens[:3]
    return tokens[-1].title(), " ".join(tokens[:-1]).title(), raw


def parse_index_page(page_label: str, html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    entries: list[dict] = []
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        path = urlparse(urljoin(BASE_URL, href)).path
        if not path.lower().endswith(".pdf"):
            continue
        url = urljoin(BASE_URL, href)
        container = row_container(a)
        row_text = clean_text(container.get_text(" ", strip=True))
        link_text = clean_text(a.get_text(" ", strip=True))
        basename = unquote(Path(path).name)

        case_number, code = extract_case(basename, link_text, row_text)
        category, note = classify(code, row_text + " " + link_text)

        # Prefer the first table cell (name column), then the row text without the
        # link label, then the link label itself, then the file name.
        last = first = raw = ""
        if container.name == "tr":
            cells = container.find_all(["td", "th"])
            if cells:
                last, first, raw = split_name(clean_text(cells[0].get_text(" ", strip=True)))
        if not last:
            last, first, raw = split_name(row_text.replace(link_text, " ") if link_text else row_text)
        if not last:
            last, first, raw = split_name(link_text)
        if not last:
            last, first, raw = split_name(basename.rsplit(".", 1)[0].replace("-", " "))

        flags = []
        if not case_number:
            flags.append("no case number")
        if not last:
            flags.append("name not parsed")

        entries.append(
            {
                "index_page": page_label,
                "index_text": row_text,
                "doc_label": link_text,
                "last_name": last,
                "first_name": first,
                "case_number": case_number,
                "code": code,
                "category": category,
                "category_note": note,
                "flags": "; ".join(flags),
                "filename": "",
                "official_url": url,
            }
        )
    return entries


def assign_filenames(entries: list[dict]) -> None:
    """'Lastname, Firstname 22-PC-0163.pdf'; later documents for the same case get ' (2)', ' (3)'."""
    seen: dict[str, int] = {}
    for e in entries:
        if e["category"] == "drop":
            continue
        name_part = f"{e['last_name']}, {e['first_name']}".strip(", ").strip()
        if not name_part:
            name_part = "UNKNOWN"
        key_part = e["case_number"] or unquote(Path(urlparse(e["official_url"]).path).stem)
        base = ILLEGAL_FILENAME.sub("", f"{name_part} {key_part}").strip()
        n = seen.get(base, 0) + 1
        seen[base] = n
        e["filename"] = f"{base}.pdf" if n == 1 else f"{base} ({n}).pdf"


# --------------------------------------------------------------------------- #
# Manifest, log, download
# --------------------------------------------------------------------------- #

MANIFEST_FIELDS = [
    "index_page", "index_text", "doc_label", "last_name", "first_name", "case_number",
    "code", "category", "category_note", "flags", "filename", "official_url",
]


def write_manifest(entries: list[dict]) -> None:
    with MANIFEST_PATH.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=MANIFEST_FIELDS)
        w.writeheader()
        for e in entries:
            w.writerow(e)


def log_row(writer, filename: str, status: str, url: str, message: str = "") -> None:
    writer.writerow({"filename": filename, "status": status, "official_url": url, "message": message})


def download_entries(entries: list[dict]) -> None:
    STATE_FOLDER.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=["filename", "status", "official_url", "message"])
        writer.writeheader()
        total = len(entries)
        ok = skipped = failed = 0
        for i, e in enumerate(entries, 1):
            target = STATE_FOLDER / e["filename"]
            if target.exists() and target.stat().st_size > 0:
                skipped += 1
                log_row(writer, e["filename"], "Already downloaded", e["official_url"])
                print(f"[{i}/{total}] skip  {e['filename']}")
                continue
            try:
                data = fetch(e["official_url"], binary=True)
                if not data.startswith(b"%PDF"):
                    raise RuntimeError("response is not a PDF (probably an HTML error page)")
                target.write_bytes(data)
                ok += 1
                log_row(writer, e["filename"], "Downloaded", e["official_url"], f"{len(data)} bytes")
                print(f"[{i}/{total}] saved {e['filename']} ({len(data):,} bytes)")
            except Exception as exc:  # noqa: BLE001
                failed += 1
                log_row(writer, e["filename"], "FAILED", e["official_url"], str(exc))
                print(f"[{i}/{total}] FAIL  {e['filename']}: {exc}")
            fh.flush()
            time.sleep(PAUSE_SECONDS)
    print(f"\nDone. Downloaded {ok}, already present {skipped}, failed {failed}. Log: {LOG_PATH}")


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--list-only", action="store_true", help="build manifest.csv, download nothing")
    ap.add_argument("--include-review", action="store_true", help="also download 'review' entries")
    ap.add_argument("--include-all", action="store_true", help="download every profession, not just counselors")
    ap.add_argument("--debug-html", action="store_true", help="save each fetched index page under downloader\\debug\\")
    args = ap.parse_args(argv)

    print(f"Kansas BSRB disciplinary actions -> {STATE_FOLDER}")
    root_url = urljoin(BASE_URL, INDEX_ROOT)
    print(f"Reading {root_url}")
    root_html = fetch(root_url)
    pages = discover_index_pages(root_html)
    print(f"Index pages to read: {len(pages)} ({', '.join(p.rsplit('/', 1)[-1] for p in pages)})")

    all_entries: list[dict] = []
    # The root page itself may carry entries too; include it first.
    page_htmls = [(INDEX_ROOT, root_html)]
    for path in pages:
        time.sleep(PAUSE_SECONDS)
        try:
            page_htmls.append((path, fetch(urljoin(BASE_URL, path))))
        except Exception as exc:  # noqa: BLE001
            print(f"  WARNING could not read {path}: {exc}")

    for path, html in page_htmls:
        label = path.rsplit("/", 1)[-1].upper()
        found = parse_index_page(label, html)
        print(f"  {label:<22} {len(found):>4} PDF links")
        all_entries.extend(found)
        if args.debug_html or not found:
            DEBUG_DIR.mkdir(exist_ok=True)
            (DEBUG_DIR / f"{label.lower() or 'root'}.html").write_text(html, encoding="utf-8")

    # De-duplicate identical PDF links that appear on more than one page.
    unique: dict[str, dict] = {}
    for e in all_entries:
        unique.setdefault(e["official_url"], e)
    all_entries = list(unique.values())

    if not all_entries:
        print(
            "\nNo PDF links were found on any index page. The page layout may have changed.\n"
            f"The fetched HTML was saved under {DEBUG_DIR} - open one in a browser and compare it\n"
            "with the live site, then adjust parse_index_page()."
        )
        return 1

    assign_filenames(all_entries)
    write_manifest(all_entries)

    counts = {}
    for e in all_entries:
        counts[e["category"]] = counts.get(e["category"], 0) + 1
    print(f"\nManifest written: {MANIFEST_PATH}")
    print("  " + ", ".join(f"{k}: {v}" for k, v in sorted(counts.items())))

    if args.list_only:
        return 0

    wanted = {"counselor"}
    if args.include_review:
        wanted.add("review")
    if args.include_all:
        wanted.update({"review", "drop"})
        # 'drop' entries have no filename yet; give them one for this run.
        for e in all_entries:
            if e["category"] == "drop":
                e["category"] = "drop (downloaded)"
        assign_filenames(all_entries)
        wanted.add("drop (downloaded)")
    todo = [e for e in all_entries if e["category"] in wanted and e["filename"]]
    print(f"\nDownloading {len(todo)} PDF(s) into {STATE_FOLDER}\n")
    download_entries(todo)
    return 0


if __name__ == "__main__":
    sys.exit(main())
