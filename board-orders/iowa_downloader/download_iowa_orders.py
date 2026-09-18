"""
Iowa Board of Behavioral Health Professionals order downloader (LMHC only).

Where the orders really are (verified live 2026-09-18):

  * https://dial.iowa.gov/i-need/board-actions is ONE page with an accordion
    per board. The Behavioral Health section lists only the last two years of
    "Notice of Board Action" e-mail bulletins (GovDelivery), each naming the
    licensees and case numbers; the bulletins link every document to
    documents.iowa.gov. There are no per-action pages and no pagination.
  * https://documents.iowa.gov is the state's document search. Its search
    API (POST /home/search) returns every "Public Discipline Documents" file
    filed under "Behavioral Health Professionals, Board of" (about 800 files
    on 2026-09-18, including the pre-2024 Board of Behavioral Science
    archive, bulk-uploaded 2023-10-30), with the licensee's last name, first
    name, city and state as metadata. Each file downloads from
    /home/download/<id>. This script uses that index.

The index does not say the licence type, and since 2024-07-01 the board also
covers social workers, psychologists and behaviour analysts (before that, the
Board of Behavioral Science covered LMHC and LMFT only). So the script works
in three passes:

  1. CRAWL    the documents.iowa.gov index (200 records per request) and
              write one row per document to actions.csv.
  2. DOWNLOAD every document into  state_data\\Iowa\\_all_behavioral_health\\
              as "<id>__<document name>.pdf"  (two Word files exist; they are
              saved with their own extension and sent to review).
  3. CLASSIFY each PDF by reading its first pages: LMHC / mental health
              counselor orders are copied into  state_data\\Iowa\\  as
              "Lastname, Firstname <case>.pdf"; other professions stay in the
              holding folder; scans with no text go to  state_data\\Iowa\\review\\
              for OCR, then  py download_iowa_orders.py --reclassify

Everything found is written to manifest.csv (one row per file) and
actions.csv (one row per index record).

Usage (from this folder):
    py download_iowa_orders.py                 # crawl, download, classify
    py download_iowa_orders.py --list-only     # crawl only, write actions.csv
    py download_iowa_orders.py --reclassify    # re-run pass 3 only (after OCR)
    py download_iowa_orders.py --max-pages 2   # limit index pages (200 records each; default 300)
"""

from __future__ import annotations

import argparse
import csv
import re
import shutil
import sys
import time
from pathlib import Path
from urllib.parse import unquote

import requests

SITE = "https://documents.iowa.gov"
SEARCH_URL = f"{SITE}/home/search"
DOWNLOAD_URL = f"{SITE}/home/download/"
DIAL_LIST = "https://dial.iowa.gov/i-need/board-actions"      # informational only
# Search category for DIAL boards and the attribute ids used by the index (from
# documents.iowa.gov/home/searchfields/10328504 on 2026-09-18).
CATEGORY_ID = "10328504"
ATTR = {
    "board": "10328504_2", "category": "10328504_3", "other_name": "10328504_4",
    "last": "10328504_6", "first": "10328504_7", "middle": "10328504_8", "business": "10328504_9",
    "order_no": "10328504_10", "state": "10328504_11", "city": "10328504_12",
    "organization": "10405082_2", "archived": "10405082_4",
}
BOARD_NAME = "Behavioral Health Professionals, Board of"
DOC_CATEGORY = "Public Discipline Documents"
PAGE_SIZE = 200

HERE = Path(__file__).resolve().parent
STATE_FOLDER = HERE.parent
ALL_FOLDER = STATE_FOLDER / "_all_behavioral_health"
REVIEW_FOLDER = STATE_FOLDER / "review"
ACTIONS_PATH = HERE / "actions.csv"
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
    "X-Requested-With": "XMLHttpRequest",
    "Referer": SITE + "/",
}
PAGES_TO_READ = 3
MIN_TEXT_CHARS = 200
MIN_ALPHA_RATIO = 0.5      # share of letters in the extracted text below which it is treated as unreadable

COUNSELOR = re.compile(r"mental health counsel|\bLMHC\b|\bTLMHC\b|\bLMHC-T\b", re.I)
OTHER_RULES = [
    (re.compile(r"marital and family|marriage and family|marriage & family|\bLMFT\b|\bTLMFT\b", re.I), "marriage & family therapy"),
    (re.compile(r"social work|\bLISW\b|\bLMSW\b|\bLBSW\b", re.I), "social work"),
    (re.compile(r"psycholog", re.I), "psychology"),
    (re.compile(r"behavior analy|\bBCBA\b|\bLBA\b", re.I), "behavior analysis"),
    (re.compile(r"applicant|application for licens", re.I), "applicant"),
]
# Profession words as they appear in Iowa order headers and licence sentences:
# "RE: Mental Health Counselor License of", "issued mental health counselor license no.",
# "BEFORE THE BOARD OF SOCIAL WORK", "BEFORE THE IOWA BOARD OF PSYCHOLOGY".
PROFESSION_WORDS = [
    (re.compile(r"mental health counsel", re.I), "counselor"),
    (re.compile(r"marital and family|marriage and family|marriage & family", re.I), "marriage & family therapy"),
    (re.compile(r"social work", re.I), "social work"),
    (re.compile(r"psycholog", re.I), "psychology"),
    (re.compile(r"behavior analy", re.I), "behavior analysis"),
]
HEADER_RE = re.compile(r"\bRE:\s*(.{0,60}?)\s+Licen[sc]e", re.I | re.S)
BOARD_RE = re.compile(r"BEFORE THE (?:IOWA )?BOARD OF (SOCIAL WORK|PSYCHOLOGY|BEHAVIORAL SCIENCE|MARITAL AND FAMILY THERAPY)", re.I)
LICENSE_SENTENCE = re.compile(r"issued (?:an? |Iowa |the )?(?:[A-Za-z]+ ){0,3}?(mental health counsel\w*|marital and family therap\w*|marriage and family therap\w*|social work\w*|psycholog\w*|behavior analy\w*)[^.]{0,40}licen[sc]e", re.I)
FULL_DOC_PAGES = 15        # pages to read when the first pages do not name a profession

# 23-0052, 2025-0478, 26DBBH0003
CASE_NO = re.compile(r"\b(\d{2,4}-\d{3,4}|\d{2}DBBH\d{4})\b")
IN_THE_MATTER = re.compile(r"IN THE MATTER OF[:\s]+(?:THE\s+)?(?:LICENSE\s+OF\s+)?([A-Z][A-Za-z'\-\. ]{2,60}?)[,\n]", re.I)
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


# --------------------------------------------------------------------------- #
# Pass 1: crawl the documents.iowa.gov index
# --------------------------------------------------------------------------- #

def search_page(start: int, length: int) -> dict:
    """One page of the index, ordered oldest upload first. Returns the raw JSON."""
    criteria = [f"Attr_{ATTR['board']}:='{BOARD_NAME}'", f"Attr_{ATTR['category']}:='{DOC_CATEGORY}'"]
    form = {
        "draw": "1", "start": str(start), "length": str(length),
        "categoryId": CATEGORY_ID, "keywords": "",
        "query": " && ".join(f"({c})" for c in criteria),
        "order[0][column]": "create_date", "order[0][dir]": "asc",
    }
    for i, c in enumerate(criteria):
        form[f"criteria[{i}]"] = c
    last_err = None
    for attempt in range(1, RETRIES + 1):
        try:
            resp = session.post(SEARCH_URL, data=form, timeout=TIMEOUT)
            resp.raise_for_status()
            return resp.json()
        except Exception as exc:  # noqa: BLE001
            last_err = exc
            if attempt < RETRIES:
                time.sleep(PAUSE_SECONDS * attempt)
    raise RuntimeError(f"search start={start}: {last_err}")


def record_to_action(rec: dict) -> dict:
    a = rec.get("attributes") or {}
    doc_id = str(rec.get("id", ""))
    name = clean_text(rec.get("name", ""))
    last = clean_text(a.get(f"Attr_{ATTR['last']}", ""))
    first = clean_text(a.get(f"Attr_{ATTR['first']}", ""))
    city = clean_text(a.get(f"Attr_{ATTR['city']}", ""))
    state = clean_text(a.get(f"Attr_{ATTR['state']}", ""))
    mime = rec.get("mime_type") or ""
    ext = ".pdf" if "pdf" in mime else (".docx" if "wordprocessingml" in mime else "")
    is_pdf = ext == ".pdf"
    return {
        "action_url": f"{SITE}/#document={doc_id}",
        "title": name,
        "list_text": ", ".join(p for p in (f"{first} {last}".strip(), city, state) if p),
        "relevant": "yes" if is_pdf else "no",
        "pdf_urls": DOWNLOAD_URL + doc_id,
        "pdf_labels": name,
        "note": "" if is_pdf else f"not a PDF ({mime or 'unknown type'})",
        "page_text": clean_text(rec.get("short_summary", ""))[:1500],
        "doc_id": doc_id,
        "last_name": last,
        "first_name": first,
        "city": city,
        "state": state,
        "upload_date": rec.get("create_date", ""),
        "mime_type": mime,
        "size": rec.get("size_formatted", ""),
        "archived": a.get(f"Attr_{ATTR['archived']}", ""),
        "case_number": case_from(name),
        "ext": ext,
    }


def crawl(max_pages: int, debug: bool) -> list[dict]:
    try:
        session.get(SITE + "/", timeout=TIMEOUT)            # sets the site cookie
    except Exception as exc:  # noqa: BLE001
        print(f"  WARNING could not open {SITE}: {exc}")
    actions: list[dict] = []
    seen: set[str] = set()
    start, total = 0, None
    for page_no in range(1, max_pages + 1):
        try:
            data = search_page(start, PAGE_SIZE)
        except Exception as exc:  # noqa: BLE001
            print(f"  WARNING index page {page_no} failed: {exc}")
            break
        rows = data.get("data") or []
        total = data.get("recordsFiltered", data.get("recordsTotal"))
        if debug or (page_no == 1 and not rows):
            DEBUG_DIR.mkdir(exist_ok=True)
            import json
            (DEBUG_DIR / f"index_page_{page_no}.json").write_text(json.dumps(data, indent=1), encoding="utf-8")
        new = 0
        for rec in rows:
            act = record_to_action(rec)
            if act["doc_id"] in seen:
                continue
            seen.add(act["doc_id"])
            actions.append(act)
            new += 1
        print(f"  index page {page_no:>3}: {len(rows)} records ({new} new, {len(actions)} so far, index says {total})")
        if len(rows) < PAGE_SIZE or (total is not None and len(actions) >= int(total)):
            break
        start += PAGE_SIZE
        time.sleep(PAUSE_SECONDS)
    return actions


ACTION_FIELDS = [
    "action_url", "title", "list_text", "relevant", "pdf_urls", "pdf_labels", "note", "page_text",
    "doc_id", "last_name", "first_name", "city", "state", "upload_date", "mime_type", "size", "archived",
    "case_number",
]


def write_actions(actions: list[dict]) -> None:
    with ACTIONS_PATH.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=ACTION_FIELDS, extrasaction="ignore")
        w.writeheader()
        w.writerows(actions)


def read_actions() -> list[dict]:
    if not ACTIONS_PATH.exists():
        return []
    with ACTIONS_PATH.open(encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    for r in rows:
        r["ext"] = ".pdf" if "pdf" in (r.get("mime_type") or "") else (".docx" if "wordprocessingml" in (r.get("mime_type") or "") else "")
    return rows


# --------------------------------------------------------------------------- #
# Pass 2: download every document
# --------------------------------------------------------------------------- #

def slug(s: str, n: int = 60) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "-", s).strip("-")[:n]


def local_name(act: dict) -> str:
    stem = Path(act["title"]).stem if act["title"].lower().endswith((".pdf", ".docx")) else act["title"]
    ext = act.get("ext") or ".pdf"
    return f"{act['doc_id']}__{slug(stem)}{ext}"


def download_pdfs(actions: list[dict]) -> dict[str, dict]:
    """Returns {local_filename: action}."""
    ALL_FOLDER.mkdir(parents=True, exist_ok=True)
    jobs = [(local_name(a), a) for a in actions if a.get("pdf_urls")]
    index: dict[str, dict] = {}
    with LOG_PATH.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=["filename", "status", "official_url", "message"])
        writer.writeheader()
        total, ok, skipped, failed = len(jobs), 0, 0, 0
        for i, (local, act) in enumerate(jobs, 1):
            index[local] = act
            u = act["pdf_urls"]
            target = ALL_FOLDER / local
            row = {"filename": local, "official_url": u, "message": ""}
            if target.exists() and target.stat().st_size > 0:
                skipped += 1
                writer.writerow({**row, "status": "Already downloaded"})
                continue
            try:
                data = fetch(u, binary=True)
                if local.endswith(".pdf") and not data.startswith(b"%PDF"):
                    raise RuntimeError("response is not a PDF")
                target.write_bytes(data)
                ok += 1
                writer.writerow({**row, "status": "Downloaded", "message": f"{len(data)} bytes"})
                print(f"[{i}/{total}] saved {local} ({len(data):,} bytes)")
            except Exception as exc:  # noqa: BLE001
                failed += 1
                writer.writerow({**row, "status": "FAILED", "message": str(exc)})
                print(f"[{i}/{total}] FAIL  {local}: {exc}")
            fh.flush()
            time.sleep(PAUSE_SECONDS)
    print(f"\nPass 2 done. Downloaded {ok}, already present {skipped}, failed {failed}. Log: {LOG_PATH}")
    return index


# --------------------------------------------------------------------------- #
# Pass 3: classify each PDF by its text
# --------------------------------------------------------------------------- #

def pdf_text(path: Path, pages: int = PAGES_TO_READ) -> str:
    try:
        import fitz  # PyMuPDF
    except ImportError as exc:  # pragma: no cover
        raise SystemExit("PyMuPDF is required for classification: py -m pip install pymupdf") from exc
    out = []
    with fitz.open(path) as doc:
        for i, page in enumerate(doc):
            if i >= pages:
                break
            out.append(page.get_text())
    return "\n".join(out)


def text_is_readable(text: str) -> bool:
    """False for a text layer that is really glyph codes (Type3 fonts with no Unicode map)."""
    t = text.strip()
    if not t:
        return False
    letters = sum(c.isalpha() for c in t)
    return letters / len(t) >= MIN_ALPHA_RATIO


def profession_in(text: str) -> str:
    for pattern, label in PROFESSION_WORDS:
        if pattern.search(text or ""):
            return label
    return ""


def header_profession(text: str) -> str:
    """Profession from the caption: 'RE: Social Work License of ...' or 'BEFORE THE BOARD OF PSYCHOLOGY'."""
    head = text[:1200]
    m = HEADER_RE.search(head)
    if m:
        prof = profession_in(m.group(1))
        if prof:
            return prof
    m = BOARD_RE.search(head)
    if m:
        board = m.group(1).lower()
        if board == "social work":
            return "social work"
        if board == "psychology":
            return "psychology"
        if board == "marital and family therapy":
            return "marriage & family therapy"
    return ""


def body_profession(text: str) -> str:
    """Profession from the licence sentence ('Respondent was issued mental health counselor license no. ...'),
    else the first profession word anywhere in the text."""
    m = LICENSE_SENTENCE.search(text or "")
    if m:
        prof = profession_in(m.group(1))
        if prof:
            return prof
    if COUNSELOR.search(text or ""):
        return "counselor"
    for pattern, label in OTHER_RULES:
        if pattern.search(text or ""):
            return label
    return ""


def classify_text(text: str) -> tuple[str, str]:
    if len(text.strip()) < MIN_TEXT_CHARS:
        return "review", "no text layer (scan) - OCR then --reclassify"
    if not text_is_readable(text):
        return "review", "text layer unreadable (Type3 font, no Unicode map) - OCR then --reclassify"
    head = header_profession(text)
    body = body_profession(text)
    if head and body and head != body:
        return "review", f"header says {head}, body says {body}"
    prof = head or body
    if not prof:
        return "review", "profession not found in first pages"
    if prof == "counselor":
        return "counselor", "" if head else "profession from body text only"
    return "drop", prof


def classify_file(path: Path) -> tuple[str, str, str]:
    """Read the first pages; if they do not settle the profession, read the whole document (up to FULL_DOC_PAGES)."""
    body = pdf_text(path)
    category, note = classify_text(body)
    if category == "review" and note.startswith("profession not found"):
        more = pdf_text(path, FULL_DOC_PAGES)
        if len(more) > len(body):
            category, note = classify_text(more)
            if category != "review":
                note = (note + "; " if note else "") + "profession found after page 3"
            body = more
    return category, note, body


def name_from(act: dict, pdf_body: str) -> tuple[str, str]:
    """Index metadata first (Last Name / First Name fields), then 'In the matter of ...' from the PDF."""
    if act.get("last_name"):
        return act["last_name"], act.get("first_name", "")
    m = IN_THE_MATTER.search(pdf_body or "")
    if m:
        tokens = clean_text(m.group(1)).split()
        if len(tokens) >= 2:
            return tokens[-1].title(), " ".join(t.title() for t in tokens[:-1])
    return "", ""


def case_from(*texts: str) -> str:
    for t in texts:
        m = CASE_NO.search(t or "")
        if m:
            return m.group(1)
    return ""


MANIFEST_FIELDS = [
    "source_file", "official_url", "action_url", "doc_label", "last_name", "first_name",
    "case_number", "category", "category_note", "text_chars", "filename",
    "doc_id", "city", "state", "upload_date",
]


def classify_all(index: dict[str, dict] | None) -> None:
    STATE_FOLDER.mkdir(parents=True, exist_ok=True)
    index = index or {}
    if not index:
        # Reclassify without a fresh crawl: rebuild the metadata from actions.csv.
        for act in read_actions():
            index[local_name(act)] = act
    sources = {p.name: p for p in ALL_FOLDER.glob("*.*") if p.suffix.lower() in (".pdf", ".docx")}
    if REVIEW_FOLDER.exists():
        for p in REVIEW_FOLDER.glob("*.pdf"):
            sources[p.name] = p
    rows, seen, counts = [], {}, {}
    for name in sorted(sources):
        src = sources[name]
        act = index.get(name, {})
        if src.suffix.lower() != ".pdf":
            body = ""
            category, note = "review", "not a PDF (Word document) - convert or request the PDF"
        else:
            try:
                category, note, body = classify_file(src)
            except Exception as exc:  # noqa: BLE001
                body = ""
                category, note = "review", f"could not read PDF: {exc}"
        last, first = name_from(act, body)
        case = act.get("case_number") or case_from(act.get("title", ""), body[:3000])
        filename = ""
        if category == "counselor":
            name_part = f"{last}, {first}".strip(", ").strip() or src.stem
            key = case or slug(Path(act.get("title", "")).stem or src.stem, 40)
            base = ILLEGAL_FILENAME.sub("", f"{name_part} {key}").strip()
            n = seen.get(base, 0) + 1
            seen[base] = n
            filename = f"{base}.pdf" if n == 1 else f"{base} ({n}).pdf"
            dest = STATE_FOLDER / filename
            if not dest.exists():
                shutil.copy2(src, dest)
        elif category == "review" and "OCR" in note:
            REVIEW_FOLDER.mkdir(exist_ok=True)
            if not (REVIEW_FOLDER / name).exists():
                shutil.copy2(src, REVIEW_FOLDER / name)
        counts[category] = counts.get(category, 0) + 1
        rows.append(
            {
                "source_file": name,
                "official_url": act.get("pdf_urls", ""),
                "action_url": act.get("action_url", ""),
                "doc_label": act.get("title", ""),
                "last_name": last,
                "first_name": first,
                "case_number": case,
                "category": category,
                "category_note": note,
                "text_chars": len(body.strip()),
                "filename": filename,
                "doc_id": act.get("doc_id", ""),
                "city": act.get("city", ""),
                "state": act.get("state", ""),
                "upload_date": act.get("upload_date", ""),
            }
        )
    with MANIFEST_PATH.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=MANIFEST_FIELDS)
        w.writeheader()
        w.writerows(rows)
    print(f"\nPass 3 done. Manifest: {MANIFEST_PATH}\n  " + ", ".join(f"{k}: {v}" for k, v in sorted(counts.items())))
    if counts.get("review"):
        print(f"  Review items are in {REVIEW_FOLDER} (OCR them, then run --reclassify).")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--list-only", action="store_true", help="crawl the index and write actions.csv, download nothing")
    ap.add_argument("--reclassify", action="store_true", help="skip crawl/download; re-run classification")
    ap.add_argument("--max-pages", type=int, default=300, help="maximum index pages to read (200 records each)")
    ap.add_argument("--debug-html", action="store_true", help="save every index page (JSON) under downloader\\debug\\")
    args = ap.parse_args(argv)

    print(f"Iowa board discipline documents (documents.iowa.gov, {BOARD_NAME}) -> {STATE_FOLDER}")
    if args.reclassify:
        classify_all(None)
        return 0

    actions = crawl(args.max_pages, args.debug_html)
    if not actions:
        print(f"\nNo records came back from the index. The raw response is under {DEBUG_DIR}; compare with the site.")
        return 1
    write_actions(actions)
    pdfs = [a for a in actions if a.get("relevant") == "yes"]
    def _key(d: str):
        m = re.match(r"(\d{1,2})/(\d{1,2})/(\d{4})", d)
        return (int(m.group(3)), int(m.group(1)), int(m.group(2))) if m else (0, 0, 0)
    dates = sorted((a["upload_date"] for a in actions if a.get("upload_date")), key=_key)
    print(f"\nactions.csv written: {len(actions)} documents, {len(pdfs)} PDFs, "
          f"{len(actions) - len(pdfs)} other file types; upload dates {dates[0] if dates else '?'} to {dates[-1] if dates else '?'}")
    if args.list_only:
        return 0
    index = download_pdfs(actions)
    classify_all(index)
    return 0


if __name__ == "__main__":
    sys.exit(main())
