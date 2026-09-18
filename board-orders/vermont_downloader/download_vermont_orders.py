"""
Vermont Office of Professional Regulation decision downloader (LCMHC only).

Vermont posts every conduct decision for the Board of Allied Mental Health
Practitioners as an individual PDF in one SharePoint folder:

    https://outside.vermont.gov/dept/sos/office_professional_regulation/
        conduct_decisions/allied_mental_health/

That folder mixes Licensed Clinical Mental Health Counselors with marriage and
family therapists, psychoanalysts and non-licensed psychotherapists, and the
file names do not say which is which. So this script works in two passes:

  1. LIST + DOWNLOAD  every PDF in the folder into
        state_data\\Vermont\\_all_allied_mental_health\\
     (skipping files already present).
  2. CLASSIFY  each PDF by reading its first pages: decisions that name a
     "Licensed Clinical Mental Health Counselor" / LCMHC are copied into
        state_data\\Vermont\\   as  "Lastname, Firstname docket 2025-105.pdf";
     other professions stay in _all_allied_mental_health only;
     PDFs with no text layer (older scans) are copied to
        state_data\\Vermont\\review\\   for Foxit OCR, after which
        py download_vermont_orders.py --reclassify   sorts them.

Folder listing (verified live 2026-09-18): the SharePoint REST API answers
401/404 to anonymous callers, so the script reads the folder's "All
Documents" view page, which embeds the file list as JSON (WPQ1ListData),
30 files per page, and follows the page's NextHref until the end.

File names (verified live 2026-09-18) come in three shapes:
    2025-105_Ashley_MacDonald_Signed_Order.pdf         docket(s), First Last, document type
    2025-38_gould_adam_signed_order.pdf                docket(s), Last First, document type
    albergate-scott-docket-2018-20.pdf                 Last First, "docket", docket   (pre-2019 style)
The first two cannot be told apart from the name alone, so pass 2 reads the
"In re:" line of the PDF and corrects the name order.

Usage (from this folder):
    py download_vermont_orders.py                 # list, download, classify
    py download_vermont_orders.py --list-only     # write manifest.csv only
    py download_vermont_orders.py --reclassify    # re-run pass 2 only (after OCR)
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import shutil
import sys
import time
from pathlib import Path
from urllib.parse import urljoin, urlparse, unquote, quote

import requests
from bs4 import BeautifulSoup

SITE = "https://outside.vermont.gov"
FOLDER = "/dept/sos/office_professional_regulation/conduct_decisions/allied_mental_health"
# The document library's "All Documents" view. The folder is passed as RootFolder.
ALLITEMS_PAGE = "/dept/sos/office_professional_regulation/Forms/AllItems.aspx"
# Candidate SharePoint web roots for the REST API, most specific first. As of
# 2026-09 none of them answers anonymously; kept as a cheap first attempt.
WEB_ROOTS = [
    "/dept/sos/office_professional_regulation",
    "/dept/sos",
    "",
]

HERE = Path(__file__).resolve().parent
STATE_FOLDER = HERE.parent
ALL_FOLDER = STATE_FOLDER / "_all_allied_mental_health"
REVIEW_FOLDER = STATE_FOLDER / "review"
MANIFEST_PATH = HERE / "manifest.csv"
LOG_PATH = HERE / "download_log.csv"
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
PAGES_TO_READ = 3          # how many pages of each PDF to scan for the profession
MIN_TEXT_CHARS = 200       # fewer than this on the first pages = treat as a scan
MAX_LIST_PAGES = 200       # safety stop for the folder paging

COUNSELOR = re.compile(r"clinical mental health counsel|\bLCMHC\b|mental health counselor", re.I)
OTHER_RULES = [
    (re.compile(r"marriage and family|marriage & family|\bLMFT\b", re.I), "marriage & family therapy"),
    (re.compile(r"psychoanalyst", re.I), "psychoanalyst"),
    (re.compile(r"non-?licensed psychotherapist|roster(ed)? psychotherapist|psychotherapist", re.I),
     "non-licensed psychotherapist"),
    (re.compile(r"applicant", re.I), "applicant"),
]
# "In re: Ashley MacDonald" / "IN RE: ASHLEY MACDONALD, License No. ..." on the first page.
IN_RE = re.compile(r"\bIn\s+re:?\s*(?:the\s+)?(?:license\s+of\s+)?([A-Z][A-Za-z'\-\.]+(?:\s+[A-Z][A-Za-z'\-\.]+){1,4})", re.I)

# Docket numbers: 2025-105, 2023-161 & 2024-188, 2022-201-to-203-2023-79, 2023-73-139-2c-2022-244-to-248
DOCKET_TOKEN = re.compile(r"(?<!\d)(\d{4})-(\d{1,4})(?!\d)")
DOCKET_OLD = re.compile(r"docket[_\- ]*([A-Za-z]{0,4}\d{4,8}(?:[_\-]\d{1,8})*)", re.I)
DOC_TYPE_WORDS = {
    "signed", "order", "orders", "stipulation", "default", "summary", "suspension", "modification",
    "preliminary", "denial", "ss", "and", "of", "license", "decision", "final", "consent", "agreement",
    "amended", "corrected", "reinstatement", "dismissal", "hearing", "unsigned", "unprofessional",
    "conduct", "to", "the", "re", "amh", "copy", "decision", "notice", "settlement",
}
ILLEGAL_FILENAME = re.compile(r'[\\/:*?"<>|]+')

session = requests.Session()
session.headers.update(HEADERS)


def fetch(url: str, binary: bool = False, headers: dict | None = None):
    last_err = None
    for attempt in range(1, RETRIES + 1):
        try:
            resp = session.get(url, timeout=TIMEOUT, headers=headers or {})
            resp.raise_for_status()
            return resp.content if binary else resp.text
        except Exception as exc:  # noqa: BLE001
            last_err = exc
            if attempt < RETRIES:
                time.sleep(PAUSE_SECONDS * attempt)
    raise RuntimeError(f"{url}: {last_err}")


# --------------------------------------------------------------------------- #
# Pass 1a: list the folder
# --------------------------------------------------------------------------- #

def list_via_rest() -> list[dict]:
    """SharePoint REST: GetFolderByServerRelativeUrl(...)/Files. Returns [{'path', 'modified'}]."""
    for root in WEB_ROOTS:
        api = (f"{SITE}{root}/_api/web/GetFolderByServerRelativeUrl('{quote(FOLDER)}')/Files"
               f"?$select=Name,ServerRelativeUrl,TimeLastModified&$top=5000")
        try:
            resp = session.get(api, timeout=TIMEOUT, headers={"Accept": "application/json;odata=nometadata"})
            if resp.status_code != 200:
                continue
            data = json.loads(resp.text)
            items = data.get("value") or data.get("d", {}).get("results") or []
            files = [{"path": it["ServerRelativeUrl"], "modified": it.get("TimeLastModified", "")}
                     for it in items if it.get("Name", "").lower().endswith(".pdf")]
            if files:
                print(f"  folder listed via REST ({root or '/'}): {len(files)} PDFs")
                return files
        except Exception:  # noqa: BLE001
            continue
    return []


def listdata_from_page(html: str) -> dict | None:
    """The JSON that SharePoint embeds in a list view page: 'var WPQ<n>ListData = {...};'."""
    m = re.search(r"var\s+WPQ\d+ListData\s*=\s*", html)
    if not m:
        return None
    try:
        data, _ = json.JSONDecoder().raw_decode(html[m.end():])
        return data
    except ValueError:
        return None


def list_via_allitems() -> list[dict]:
    """Read the folder's All Documents view page by page (30 files per page)."""
    url = f"{SITE}{ALLITEMS_PAGE}?RootFolder={quote(FOLDER)}"
    files: list[dict] = []
    seen: set[str] = set()
    for page_no in range(1, MAX_LIST_PAGES + 1):
        try:
            html = fetch(url)
        except Exception as exc:  # noqa: BLE001
            print(f"  listing page {page_no} failed: {str(exc)[:100]}")
            break
        data = listdata_from_page(html)
        if data is None:
            DEBUG_DIR.mkdir(exist_ok=True)
            (DEBUG_DIR / f"listing_page_{page_no}.html").write_text(html, encoding="utf-8")
            print(f"  listing page {page_no}: no embedded file list (saved under {DEBUG_DIR})")
            break
        rows = data.get("Row", [])
        new = 0
        for r in rows:
            if str(r.get("FSObjType", "0")) != "0":       # 1 = sub-folder
                continue
            ref = r.get("FileRef") or ""
            if not ref.lower().endswith(".pdf") or ref in seen:
                continue
            seen.add(ref)
            files.append({"path": ref, "modified": r.get("Modified", ""), "size": r.get("File_x0020_Size", "")})
            new += 1
        print(f"  listing page {page_no}: {len(rows)} rows, {new} new PDFs (total {len(files)})")
        nxt = data.get("NextHref")
        if not nxt or not rows:
            break
        url = f"{SITE}{ALLITEMS_PAGE}{nxt}" if nxt.startswith("?") else urljoin(SITE + ALLITEMS_PAGE, nxt)
        time.sleep(PAUSE_SECONDS)
    if files:
        print(f"  folder listed via All Documents page: {len(files)} PDFs")
    return files


def list_via_html() -> list[dict]:
    """Last resort: scrape any .pdf link under the folder from a directly fetched page."""
    candidates = [f"{SITE}{FOLDER}/Forms/AllItems.aspx", f"{SITE}{FOLDER}/"]
    for url in candidates:
        try:
            html = fetch(url)
        except Exception as exc:  # noqa: BLE001
            print(f"  HTML listing failed: {url} ({str(exc)[:80]})")
            continue
        found = set()
        soup = BeautifulSoup(html, "html.parser")
        for a in soup.find_all("a", href=True):
            path = urlparse(urljoin(SITE, a["href"])).path
            if path.lower().startswith(FOLDER.lower() + "/") and path.lower().endswith(".pdf"):
                found.add(unquote(path))
        for m in re.finditer(r'"FileRef"\s*:\s*"([^"]+\.pdf)"', html, re.I):
            found.add(unquote(m.group(1)))
        if found:
            print(f"  folder listed via HTML page: {len(found)} PDFs")
            return [{"path": p, "modified": ""} for p in sorted(found)]
    return []


def list_folder() -> list[dict]:
    return list_via_rest() or list_via_allitems() or list_via_html()


# --------------------------------------------------------------------------- #
# Pass 2: classify a PDF by its text
# --------------------------------------------------------------------------- #

def pdf_text(path: Path, pages: int = PAGES_TO_READ) -> str:
    try:
        import fitz  # PyMuPDF
    except ImportError as exc:  # pragma: no cover
        raise SystemExit("PyMuPDF is required for classification: py -m pip install pymupdf") from exc
    text = []
    with fitz.open(path) as doc:
        for i, page in enumerate(doc):
            if i >= pages:
                break
            text.append(page.get_text())
    return "\n".join(text)


def classify_text(text: str) -> tuple[str, str, int]:
    """Return (category, note, chars): counselor / drop / review."""
    chars = len(text.strip())
    if chars < MIN_TEXT_CHARS:
        return "review", "no text layer (scan) - OCR then --reclassify", chars
    if COUNSELOR.search(text):
        return "counselor", "", chars
    for pattern, label in OTHER_RULES:
        if pattern.search(text):
            return "drop", label, chars
    return "review", "profession not found in first pages", chars


def classify_pdf(path: Path) -> tuple[str, str, int, str]:
    """Return (category, note, chars, text)."""
    try:
        text = pdf_text(path)
    except Exception as exc:  # noqa: BLE001
        return "review", f"could not read PDF: {exc}", 0, ""
    category, note, chars = classify_text(text)
    return category, note, chars, text


def name_from_pdf(text: str) -> tuple[str, str]:
    """'In re: Ashley MacDonald' on the first page -> ('MacDonald', 'Ashley')."""
    m = IN_RE.search(text or "")
    if not m:
        return "", ""
    tokens = [t.strip(",.") for t in m.group(1).split()]
    tokens = [t for t in tokens if t.lower() not in ("license", "no", "no.", "lcmhc", "lmft", "of")]
    if len(tokens) < 2:
        return "", ""
    return tokens[-1].title() if tokens[-1].isupper() else tokens[-1], " ".join(
        t.title() if t.isupper() else t for t in tokens[:-1])


# --------------------------------------------------------------------------- #
# File-name parsing
# --------------------------------------------------------------------------- #

def dockets_from(stem: str) -> tuple[str, str]:
    """Return (docket_list, primary_docket). '2023-161 & 2024-188 joshua_stumpff_order' -> ('2023-161; 2024-188', '2023-161')."""
    s = unquote(stem)
    m = DOCKET_OLD.search(s)
    if m and not DOCKET_TOKEN.search(s[: m.start()]):
        d = m.group(1).replace("_", "-")
        return d, d
    found = [f"{y}-{n}" for y, n in DOCKET_TOKEN.findall(s)]
    if not found:
        return "", ""
    # "2022-201-to-203" and "2022-262-263": extra bare numbers after a docket belong to the same year.
    head = s[: s.find(found[-1]) + len(found[-1])] if found else s
    extras = re.findall(r"(?:-|_|\s|to|&|and)+(\d{1,4})(?![\d-])", s[len(head):len(head) + 40]) if head else []
    year = found[-1].split("-")[0]
    for e in extras:
        if re.match(r"^\d{1,4}$", e) and f"{year}-{e}" not in found:
            found.append(f"{year}-{e}")
    return "; ".join(found), found[0]


def name_from_filename(stem: str) -> tuple[str, str, str, str]:
    """
    Return (last, first, docket, note).
      'albergate-scott-docket-2018-20'        -> ('Albergate', 'Scott', '2018-20', 'name-first file')
      '2025-105_Ashley_ MacDonald_Signed_Order' -> ('MacDonald', 'Ashley', '2025-105', 'docket-first file: name order assumed First Last')
    """
    s = unquote(stem).strip()
    dockets, primary = dockets_from(s)
    old = DOCKET_OLD.search(s)
    if old and not DOCKET_TOKEN.search(s[: old.start()]):
        # name-first style: everything before "docket"
        name_part = s[: old.start()]
        tokens = [t for t in re.split(r"[_\-\s]+", name_part) if t and t.lower() not in DOC_TYPE_WORDS]
        if not tokens:
            return "", "", primary, "name not parsed"
        if len(tokens) == 1:
            return tokens[0].title(), "", primary, "name-first file"
        return tokens[0].title(), " ".join(t.title() for t in tokens[1:]), primary, "name-first file"

    # docket-first style: strip every docket token and the joining words, keep the name words
    rest = s
    for y, n in DOCKET_TOKEN.findall(s):
        rest = rest.replace(f"{y}-{n}", " ")
    rest = re.sub(r"\b(to|&|and)\b", " ", rest, flags=re.I)
    tokens = [t for t in re.split(r"[_\-\s&,]+", rest) if t]
    tokens = [t for t in tokens if not t.isdigit() and not re.fullmatch(r"\d+[a-z]", t.lower())
              and t.lower() not in DOC_TYPE_WORDS and not re.fullmatch(r"\(\d+\)", t)]
    if not tokens:
        return "", "", primary, "name not parsed"
    if len(tokens) == 1:
        return tokens[0].title(), "", primary, "docket-first file: single name token"
    first = " ".join(t if not t.islower() else t.title() for t in tokens[:-1])
    last = tokens[-1] if not tokens[-1].islower() else tokens[-1].title()
    return last, first, primary, "docket-first file: name order assumed First Last"


def make_target_name(last: str, first: str, docket: str, stem: str, seen: dict[str, int]) -> str:
    name_part = f"{last}, {first}".strip(", ").strip() or stem
    key = f"docket {docket}" if docket else stem
    base = ILLEGAL_FILENAME.sub("", f"{name_part} {key}").strip()
    n = seen.get(base, 0) + 1
    seen[base] = n
    return f"{base}.pdf" if n == 1 else f"{base} ({n}).pdf"


# --------------------------------------------------------------------------- #
# Manifest and log
# --------------------------------------------------------------------------- #

MANIFEST_FIELDS = [
    "source_file", "official_url", "last_name", "first_name", "docket",
    "category", "category_note", "text_chars", "filename", "modified", "dockets_all",
]


def write_manifest(rows: list[dict]) -> None:
    with MANIFEST_PATH.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=MANIFEST_FIELDS, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def download_all(files: list[dict]) -> None:
    ALL_FOLDER.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=["filename", "status", "official_url", "message"])
        writer.writeheader()
        total, ok, skipped, failed = len(files), 0, 0, 0
        for i, f in enumerate(files, 1):
            rel = f["path"]
            url = SITE + quote(rel)
            fname = unquote(Path(rel).name)
            target = ALL_FOLDER / fname
            row = {"filename": fname, "official_url": url, "message": ""}
            if target.exists() and target.stat().st_size > 0:
                skipped += 1
                writer.writerow({**row, "status": "Already downloaded"})
                continue
            try:
                data = fetch(url, binary=True)
                if not data.startswith(b"%PDF"):
                    raise RuntimeError("response is not a PDF")
                target.write_bytes(data)
                ok += 1
                writer.writerow({**row, "status": "Downloaded", "message": f"{len(data)} bytes"})
                print(f"[{i}/{total}] saved {fname} ({len(data):,} bytes)")
            except Exception as exc:  # noqa: BLE001
                failed += 1
                writer.writerow({**row, "status": "FAILED", "message": str(exc)})
                print(f"[{i}/{total}] FAIL  {fname}: {exc}")
            fh.flush()
            time.sleep(PAUSE_SECONDS)
    print(f"\nPass 1 done. Downloaded {ok}, already present {skipped}, failed {failed}. Log: {LOG_PATH}")


def load_listing_meta() -> dict[str, dict]:
    """Modified dates etc. from an earlier manifest, for --reclassify runs."""
    meta = {}
    if MANIFEST_PATH.exists():
        with MANIFEST_PATH.open(encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                meta[r["source_file"]] = r
    return meta


def classify_all(listing: dict[str, dict] | None = None) -> list[dict]:
    STATE_FOLDER.mkdir(parents=True, exist_ok=True)
    listing = listing or load_listing_meta()
    rows: list[dict] = []
    seen: dict[str, int] = {}
    counts: dict[str, int] = {}
    # Files the user OCR'd in review\ take precedence over the raw copy.
    sources = {p.name: p for p in ALL_FOLDER.glob("*.pdf")}
    if REVIEW_FOLDER.exists():
        for p in REVIEW_FOLDER.glob("*.pdf"):
            sources[p.name] = p
    for name in sorted(sources):
        src = sources[name]
        category, note, chars, text = classify_pdf(src)
        last, first, docket, name_note = name_from_filename(src.stem)
        dockets_all, _ = dockets_from(src.stem)
        pdf_last, pdf_first = name_from_pdf(text)
        if pdf_last:
            if {pdf_last.lower(), pdf_first.lower().split()[0] if pdf_first else ""} & {last.lower(), first.lower().split()[0] if first else ""}:
                # Same two names: trust the PDF's order, keep the fuller first name.
                if pdf_last.lower() != last.lower():
                    last, first = pdf_last, pdf_first
                    name_note = "name order corrected from PDF"
                else:
                    name_note = "name confirmed by PDF"
            else:
                name_note = f"PDF names {pdf_first} {pdf_last}; file name says {first} {last}"
        filename = ""
        if category == "counselor":
            filename = make_target_name(last, first, docket, src.stem, seen)
            dest = STATE_FOLDER / filename
            if not dest.exists():
                shutil.copy2(src, dest)
        elif category == "review" and "scan" in note:
            REVIEW_FOLDER.mkdir(exist_ok=True)
            dest = REVIEW_FOLDER / name
            if not dest.exists():
                shutil.copy2(src, dest)
        counts[category] = counts.get(category, 0) + 1
        note_full = "; ".join(p for p in (note, name_note) if p)
        rows.append(
            {
                "source_file": name,
                "official_url": SITE + quote(f"{FOLDER}/{name}"),
                "last_name": last,
                "first_name": first,
                "docket": docket,
                "category": category,
                "category_note": note_full,
                "text_chars": chars,
                "filename": filename,
                "modified": (listing.get(name) or {}).get("modified", ""),
                "dockets_all": dockets_all,
            }
        )
    write_manifest(rows)
    print(f"\nPass 2 done. Manifest: {MANIFEST_PATH}\n  " + ", ".join(f"{k}: {v}" for k, v in sorted(counts.items())))
    if counts.get("review"):
        print(f"  Review items are in {REVIEW_FOLDER} (OCR them, then run --reclassify).")
    return rows


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--list-only", action="store_true", help="list the folder and write manifest.csv, download nothing")
    ap.add_argument("--reclassify", action="store_true", help="skip listing/downloading; re-run the text classification")
    args = ap.parse_args(argv)

    print(f"Vermont OPR allied mental health decisions -> {STATE_FOLDER}")
    if not args.reclassify:
        files = list_folder()
        if not files:
            print(
                "\nCould not list the decisions folder by REST, by the All Documents page or by page scrape.\n"
                f"Any listing page fetched was saved under {DEBUG_DIR}. Open the folder in a browser,\n"
                "and if the site has changed, update FOLDER / ALLITEMS_PAGE at the top of the script."
            )
            return 1
        listing = {unquote(Path(f["path"]).name): f for f in files}
        if args.list_only:
            rows = []
            for f in files:
                stem = Path(unquote(f["path"])).stem
                last, first, docket, name_note = name_from_filename(stem)
                dockets_all, _ = dockets_from(stem)
                rows.append(
                    {"source_file": unquote(Path(f["path"]).name), "official_url": SITE + quote(f["path"]),
                     "last_name": last, "first_name": first, "docket": docket,
                     "category": "not downloaded", "category_note": name_note, "text_chars": "",
                     "filename": "", "modified": f.get("modified", ""), "dockets_all": dockets_all}
                )
            write_manifest(rows)
            print(f"Manifest written with {len(rows)} PDFs: {MANIFEST_PATH}")
            return 0
        download_all(files)
        classify_all(listing)
        return 0
    classify_all()
    return 0


if __name__ == "__main__":
    sys.exit(main())
