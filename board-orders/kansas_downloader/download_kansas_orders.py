"""
Kansas BSRB disciplinary-order downloader (Licensed Professional Counselors).

Collects order PDFs for professional counselors (LPC / LCPC) from the Kansas
Behavioral Sciences Regulatory Board's public "Disciplinary Actions" index,
which is split into seven last-name pages (A-C, D-F, G-J, K-M, N-Q, R-V, W-Z).
Every entry found on the index is written to manifest.csv with a category
(counselor / drop / review); only "counselor" entries are downloaded unless
you pass --include-review or --include-all.

Page layout (verified 2026-09-18 against the 2026-08-14 copy of the site):
one HTML table per letter page, four columns per row:

    Name - LICENSE NUMBER  |  date(s)  |  city  |  document type + case-number link

The case-number link points at /home/showpublisheddocument/<id>/<ticks>
(no .pdf extension) and returns the PDF. A licensee with several orders has
several dates and several links in the same row. Case numbers carry a
profession code (22-PC-0163: PC = professional counselor, LC = clinical
professional counselor); 1980s-1990s cases (95-0588) have no code, so the
license label in the name column is used first and the code second.

Built from the Maryland downloader's behaviour: sequential downloads with a
polite pause, three retries, a real-PDF check, skip-if-present, and a
download_log.csv of every outcome.

Usage (from this folder):
    py download_kansas_orders.py                 # download counselor orders
    py download_kansas_orders.py --list-only     # build manifest.csv only
    py download_kansas_orders.py --include-review
    py download_kansas_orders.py --include-all   # every profession (not needed for the LPC dataset)
    py download_kansas_orders.py --debug-html    # also save the fetched index pages to downloader\debug\
    py download_kansas_orders.py --from-saved debug   # parse pages saved earlier (root.html, a-c.html, ...)
                                                      # instead of fetching them; use this if the site
                                                      # blocks the script but opens in a browser
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
from bs4 import BeautifulSoup, NavigableString, Tag

# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #

BASE_URL = "https://www.ksbsrb.ks.gov"
INDEX_ROOT = "/complaints/disciplinary-actions"
# Letter pages confirmed 2026-09. The script also discovers any other sub-page
# linked from the root page, so a renamed page is not lost.
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
    "Accept-Language": "en-US,en;q=0.9",
}

# Case numbers look like 22-PC-0163 (year, profession code, sequence); a few are
# 22-MS-012 or 96-0661A. Very old ones look like 96-0608 (no profession code).
CASE_WITH_CODE = re.compile(r"\b(\d{2})-([A-Za-z]{2,4})-(\d{2,5}[A-Za-z]?)\b")
CASE_LEGACY = re.compile(r"\b(\d{2})-(\d{4}[A-Za-z]?)\b")

# Profession codes embedded in Kansas case numbers, decoded from the license
# labels that accompany them on the index (2026-08 copy). PC and LC are the
# counselor codes. Anything not listed here is sent to "review" rather than guessed.
CODE_MAP = {
    "PC": ("counselor", "LPC (code PC)"),
    "LC": ("counselor", "LCPC (code LC)"),
    "SW": ("drop", "social work"),
    "BS": ("drop", "social work (LBSW)"),
    "MS": ("drop", "social work (LMSW)"),
    "CS": ("drop", "social work (LSCSW)"),
    "AS": ("drop", "social work (LASW)"),
    "MF": ("drop", "marriage & family therapy (LMFT)"),
    "CT": ("drop", "marriage & family therapy (LCMFT)"),
    "MFT": ("drop", "marriage & family therapy"),
    "AC": ("drop", "addiction counseling (LAC)"),
    "CA": ("drop", "addiction counseling (LCAC)"),
    "MA": ("drop", "addiction counseling (LMAC)"),
    "RD": ("drop", "addiction counseling (RAODAC)"),
    "LP": ("drop", "psychology (LP)"),
    "PS": ("drop", "psychology"),
    "PSY": ("drop", "psychology"),
    "MP": ("drop", "psychology (LMLP)"),
    "MLP": ("drop", "psychology (LMLP)"),
    "CP": ("drop", "psychology (LCP)"),
    "BA": ("drop", "behavior analysis (LBA)"),
    "APP": ("review", "applicant (code APP)"),
    "NL": ("review", "no license / unlicensed practice (code NL)"),
}

# License labels as they appear in the name column ("Abbey, Leslie - LSCSW 1264").
LABEL_MAP = {
    "LPC": ("counselor", "LPC"),
    "LCPC": ("counselor", "LCPC"),
    "T-LPC": ("counselor", "LPC (temporary)"),
    "LMSW": ("drop", "social work (LMSW)"),
    "LSCSW": ("drop", "social work (LSCSW)"),
    "LBSW": ("drop", "social work (LBSW)"),
    "LASW": ("drop", "social work (LASW)"),
    "LMFT": ("drop", "marriage & family therapy (LMFT)"),
    "LCMFT": ("drop", "marriage & family therapy (LCMFT)"),
    "T-LMFT": ("drop", "marriage & family therapy (temporary)"),
    "LAC": ("drop", "addiction counseling (LAC)"),
    "LCAC": ("drop", "addiction counseling (LCAC)"),
    "LMAC": ("drop", "addiction counseling (LMAC)"),
    "RAODAC": ("drop", "addiction counseling (RAODAC)"),
    "LP": ("drop", "psychology (LP)"),
    "LMLP": ("drop", "psychology (LMLP)"),
    "LCP": ("drop", "psychology (LCP)"),
    "LBA": ("drop", "behavior analysis (LBA)"),
}
LABEL_PATTERN = re.compile(r"\b(T-LPC|T-LMFT|LCPC|LPC|LMSW|LSCSW|LBSW|LASW|LCMFT|LMFT|LCAC|LMAC|LAC|RAODAC|LMLP|LCP|LP|LBA)\b")

# Words in the entry text that settle the profession when neither label nor code does.
TEXT_RULES = [
    (re.compile(r"professional counsel", re.I), ("counselor", "text: professional counselor")),
    (re.compile(r"social work", re.I), ("drop", "social work")),
    (re.compile(r"marriage|family therap", re.I), ("drop", "marriage & family therapy")),
    (re.compile(r"addiction|alcohol|drug", re.I), ("drop", "addiction counseling")),
    (re.compile(r"psycholog", re.I), ("drop", "psychology")),
    (re.compile(r"behavior analy|\bBCBA\b", re.I), ("drop", "behavior analysis")),
    (re.compile(r"unlicensed|no license", re.I), ("review", "unlicensed / no license")),
    (re.compile(r"applicant", re.I), ("review", "applicant")),
]

DATE_PATTERN = re.compile(r"\b(\d{1,2})/(\d{1,2})/(\d{4})\b")
ILLEGAL_FILENAME = re.compile(r'[\\/:*?"<>|]+')
# Prefixes the Wayback Machine adds to links when a page is saved from web.archive.org.
WAYBACK_PREFIX = re.compile(r"(?:https?://web\.archive\.org)?/web/\d{4,14}(?:[a-z]{2}_)?/(?=https?://)")

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
        href = WAYBACK_PREFIX.sub("", a["href"])
        path = urlparse(urljoin(BASE_URL, href)).path.rstrip("/").lower()
        if path.startswith(INDEX_ROOT + "/") and path != INDEX_ROOT and path not in pages:
            if not path.lower().endswith(".pdf"):
                pages.append(path)
    return pages


# --------------------------------------------------------------------------- #
# Parsing one index page into entries
# --------------------------------------------------------------------------- #

def clean_text(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").replace(" ,", ",").strip()


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


def classify(labels: list[str], code: str, text: str) -> tuple[str, str]:
    """
    Decide counselor / drop / review. The license label(s) printed next to the
    name settle it first (a dual licensee holding LPC/LCPC counts as a counselor),
    then the profession code in the case number, then words in the row text.
    """
    verdicts = [LABEL_MAP[l] for l in labels if l in LABEL_MAP]
    if verdicts:
        counselor = [v for v in verdicts if v[0] == "counselor"]
        others = [v for v in verdicts if v[0] != "counselor"]
        if counselor and others:
            return ("counselor", "dual license: " + ", ".join(v[1] for v in verdicts))
        if counselor:
            return counselor[0]
        return ("drop", "; ".join(dict.fromkeys(v[1] for v in others)))
    if code in CODE_MAP:
        return CODE_MAP[code]
    for pattern, verdict in TEXT_RULES:
        if pattern.search(text):
            return verdict
    if code:
        return ("review", f"unknown profession code {code}")
    return ("review", "no license label, code or keyword found")


def nice_case(s: str) -> str:
    """Title-case only words written in all caps or all lower; keep 'DeValk', 'McCoy' as written."""
    return " ".join(w.title() if (w.isupper() or w.islower()) else w for w in s.split())


def split_name(text: str) -> tuple[str, str]:
    """'Abbey, Leslie' / 'Denney Ronald' / 'Bogue-Gilmore, Angela' -> (last, first)."""
    cut = clean_text(text).strip(" ,;:-")
    if not cut:
        return "", ""
    if "," in cut:
        last, first = [clean_text(p) for p in cut.split(",", 1)]
        first = " ".join(first.split()[:3])
        return nice_case(last), nice_case(first)
    tokens = cut.split()
    if len(tokens) == 1:
        return nice_case(tokens[0]), ""
    # "First Last" (rare on this index: a missing comma). Take the last token as surname.
    return nice_case(tokens[-1]), nice_case(" ".join(tokens[:-1]))


def parse_name_cell(cell: Tag) -> tuple[str, str, str, list[str]]:
    """Returns (last, first, license_text, labels) from 'Name - LSCSW 1264' style cells."""
    full = clean_text(cell.get_text(" ", strip=True))
    strong = next((t for t in cell.find_all("strong") if clean_text(t.get_text())), None)
    if strong:
        name_text = clean_text(strong.get_text(" ", strip=True))
        rest = clean_text(full.replace(name_text, " ", 1))
    else:
        parts = re.split(r"\s+[-–—]\s*|\s*[-–—]\s+", full, maxsplit=1)
        name_text, rest = (parts[0], parts[1] if len(parts) > 1 else "")
        if not rest:
            m = LABEL_PATTERN.search(full)
            if m:
                name_text, rest = full[: m.start()], full[m.start():]
    # A label glued to the name without a dash ("Bogue-Gilmore, Angela LCMFT 267").
    m = LABEL_PATTERN.search(name_text)
    if m:
        rest = clean_text(name_text[m.start():] + " " + rest)
        name_text = name_text[: m.start()]
    labels = [l.upper() for l in LABEL_PATTERN.findall(rest)]
    last, first = split_name(name_text.strip(" -–—,"))
    return last, first, rest.strip(" -–—,"), labels


def cell_lines(cell: Tag) -> list[str]:
    """Text of a cell split on <br> tags."""
    lines, cur = [], []
    for node in cell.descendants:
        if isinstance(node, Tag) and node.name == "br":
            lines.append(clean_text(" ".join(cur)))
            cur = []
        elif isinstance(node, NavigableString):
            cur.append(str(node))
    lines.append(clean_text(" ".join(cur)))
    return [l for l in lines if l]


def documents_in_cell(cell: Tag) -> list[tuple[str, str, str]]:
    """[(doc_type_text, link_text, href)] for each link in the documents cell, split on <br>."""
    docs = []
    cur_text: list[str] = []
    cur_link = None
    for node in cell.descendants:
        if isinstance(node, Tag) and node.name == "br":
            if cur_link is not None:
                docs.append((clean_text(" ".join(cur_text)), cur_link[0], cur_link[1]))
            cur_text, cur_link = [], None
        elif isinstance(node, Tag) and node.name == "a" and node.get("href"):
            if cur_link is not None:                      # two links in one line: flush the first
                docs.append((clean_text(" ".join(cur_text)), cur_link[0], cur_link[1]))
                cur_text = []
            cur_link = (clean_text(node.get_text(" ", strip=True)), node["href"].strip())
        elif isinstance(node, NavigableString) and not (node.parent.name == "a"):
            cur_text.append(str(node))
    if cur_link is not None:
        docs.append((clean_text(" ".join(cur_text)), cur_link[0], cur_link[1]))
    return docs


def normalise_url(href: str) -> str:
    href = WAYBACK_PREFIX.sub("", href.strip())
    return urljoin(BASE_URL, href)


def is_document_link(url: str) -> bool:
    path = urlparse(url).path.lower()
    return path.endswith(".pdf") or "/showpublisheddocument/" in path or "/docs/" in path


def parse_index_page(page_label: str, html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    entries: list[dict] = []
    seen_links: set[str] = set()

    for tr in soup.find_all("tr"):
        cells = tr.find_all("td")
        if len(cells) < 2 or not tr.find("a", href=True):
            continue
        last, first, license_text, labels = parse_name_cell(cells[0])
        dates = [d for line in cell_lines(cells[1]) for d in DATE_PATTERN.findall(line)] if len(cells) > 1 else []
        dates = [f"{y}-{int(m):02d}-{int(d):02d}" for m, d, y in dates]
        city = clean_text(cells[2].get_text(" ", strip=True)) if len(cells) > 3 else ""
        doc_cell = cells[-1]
        docs = documents_in_cell(doc_cell)
        row_text = clean_text(tr.get_text(" ", strip=True))

        for i, (doc_type, link_text, href) in enumerate(docs):
            url = normalise_url(href)
            if not is_document_link(url) or url in seen_links:
                continue
            seen_links.add(url)
            basename = unquote(Path(urlparse(url).path).name)
            case_number, code = extract_case(link_text, doc_type, basename)
            category, note = classify(labels, code, row_text)
            if len(dates) == len(docs):
                action_date = dates[i]
            elif len(dates) == 1:
                action_date = dates[0]
            else:
                action_date = dates[0] if dates and i == 0 else ""

            flags = []
            if not case_number:
                flags.append("no case number")
            if not last:
                flags.append("name not parsed")
            if not action_date:
                flags.append("no date")
            if not labels and not code:
                flags.append("no license label")

            entries.append(
                {
                    "index_page": page_label,
                    "index_text": row_text,
                    "doc_label": clean_text(f"{doc_type} {link_text}"),
                    "last_name": last,
                    "first_name": first,
                    "case_number": case_number,
                    "code": code,
                    "category": category,
                    "category_note": note,
                    "flags": "; ".join(flags),
                    "filename": "",
                    "official_url": url,
                    "license": license_text,
                    "action_date": action_date,
                    "city": city,
                }
            )

    # Fallback for a page without the table layout: any document link at all.
    if not entries:
        for a in soup.find_all("a", href=True):
            url = normalise_url(a["href"])
            if not is_document_link(url) or url in seen_links:
                continue
            seen_links.add(url)
            container = a.parent
            for parent in a.parents:
                if parent.name in ("tr", "li", "p"):
                    container = parent
                    break
            row_text = clean_text(container.get_text(" ", strip=True))
            link_text = clean_text(a.get_text(" ", strip=True))
            case_number, code = extract_case(link_text, row_text, unquote(Path(urlparse(url).path).name))
            labels = [l.upper() for l in LABEL_PATTERN.findall(row_text)]
            category, note = classify(labels, code, row_text)
            last, first = split_name(re.split(r"\s+[-–—]\s+", row_text, maxsplit=1)[0])
            entries.append(
                {
                    "index_page": page_label, "index_text": row_text, "doc_label": link_text,
                    "last_name": last, "first_name": first, "case_number": case_number, "code": code,
                    "category": category, "category_note": note, "flags": "layout fallback",
                    "filename": "", "official_url": url, "license": "", "action_date": "", "city": "",
                }
            )
    return entries


def doc_key(e: dict) -> str:
    """Case number, or the site's document id when the link has no case number."""
    if e["case_number"]:
        return e["case_number"]
    path = urlparse(e["official_url"]).path
    m = re.search(r"/showpublisheddocument/(\d+)", path)
    if m:
        return f"doc{m.group(1)}"
    return unquote(Path(path).stem)


def assign_filenames(entries: list[dict]) -> None:
    """'Lastname, Firstname 22-PC-0163.pdf'; later documents for the same case get ' (2)', ' (3)'."""
    seen: dict[str, int] = {}
    for e in entries:
        if e["category"] == "drop":
            continue
        name_part = f"{e['last_name']}, {e['first_name']}".strip(", ").strip()
        if not name_part:
            name_part = "UNKNOWN"
        base = ILLEGAL_FILENAME.sub("", f"{name_part} {doc_key(e)}").strip()
        n = seen.get(base, 0) + 1
        seen[base] = n
        e["filename"] = f"{base}.pdf" if n == 1 else f"{base} ({n}).pdf"


# --------------------------------------------------------------------------- #
# Manifest, log, download
# --------------------------------------------------------------------------- #

MANIFEST_FIELDS = [
    "index_page", "index_text", "doc_label", "last_name", "first_name", "case_number",
    "code", "category", "category_note", "flags", "filename", "official_url",
    "license", "action_date", "city",
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

def load_pages(args) -> list[tuple[str, str]]:
    """[(path, html)] for the root page and every letter page, fetched or read from --from-saved."""
    if args.from_saved:
        folder = Path(args.from_saved)
        if not folder.is_absolute():
            folder = HERE / folder
        pages = []
        for f in sorted(folder.glob("*.htm*")):
            label = f.stem.lower()
            path = INDEX_ROOT if label in ("root", "disciplinary-actions") else f"{INDEX_ROOT}/{label}"
            pages.append((path, f.read_text(encoding="utf-8", errors="replace")))
        if not pages:
            raise SystemExit(f"No .html files found in {folder}")
        print(f"Reading {len(pages)} saved page(s) from {folder}")
        return pages

    root_url = urljoin(BASE_URL, INDEX_ROOT)
    print(f"Reading {root_url}")
    try:
        root_html = fetch(root_url)
    except Exception as exc:  # noqa: BLE001
        raise SystemExit(
            f"Could not read {root_url}: {exc}\n"
            "If the page opens in your browser, the site is refusing automated requests.\n"
            "Save the root page and each letter page (A-C ... W-Z) as root.html, a-c.html, ...\n"
            f"into {DEBUG_DIR} and re-run with  --from-saved debug"
        ) from exc
    pages = discover_index_pages(root_html)
    print(f"Index pages to read: {len(pages)} ({', '.join(p.rsplit('/', 1)[-1] for p in pages)})")
    page_htmls = [(INDEX_ROOT, root_html)]
    for path in pages:
        time.sleep(PAUSE_SECONDS)
        try:
            page_htmls.append((path, fetch(urljoin(BASE_URL, path))))
        except Exception as exc:  # noqa: BLE001
            print(f"  WARNING could not read {path}: {exc}")
    return page_htmls


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--list-only", action="store_true", help="build manifest.csv, download nothing")
    ap.add_argument("--include-review", action="store_true", help="also download 'review' entries")
    ap.add_argument("--include-all", action="store_true", help="download every profession, not just counselors")
    ap.add_argument("--debug-html", action="store_true", help="save each fetched index page under downloader\\debug\\")
    ap.add_argument("--from-saved", metavar="DIR", help="parse index pages saved as root.html, a-c.html ... in DIR instead of fetching")
    args = ap.parse_args(argv)

    print(f"Kansas BSRB disciplinary actions -> {STATE_FOLDER}")
    page_htmls = load_pages(args)

    all_entries: list[dict] = []
    for path, html in page_htmls:
        label = path.rsplit("/", 1)[-1].upper()
        if path == INDEX_ROOT:
            label = "ROOT"
        found = parse_index_page(label, html)
        print(f"  {label:<22} {len(found):>4} document links")
        all_entries.extend(found)
        if args.debug_html or (not found and path != INDEX_ROOT and not args.from_saved):
            DEBUG_DIR.mkdir(exist_ok=True)
            (DEBUG_DIR / f"{label.lower()}.html").write_text(html, encoding="utf-8")

    # De-duplicate identical document links that appear on more than one page.
    unique: dict[str, dict] = {}
    for e in all_entries:
        unique.setdefault(e["official_url"], e)
    all_entries = list(unique.values())

    if not all_entries:
        print(
            "\nNo document links were found on any index page. The page layout may have changed.\n"
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
