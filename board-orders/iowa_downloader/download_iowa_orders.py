"""
Iowa Board of Behavioral Health Professionals order downloader (LMHC only).

Iowa's Department of Inspections, Appeals and Licensing (DIAL) publishes board
actions as a dated list at https://dial.iowa.gov/i-need/board-actions, one page
per action (or per posting date), each linking the order documents (statement
of charges, settlement agreement, final order, emergency order). The list gives
names, cities and case numbers but not the licence type, and since 2024-07-01
the board also covers social workers, psychologists and behaviour analysts
(before that, the Board of Behavioral Science covered LMHC and LMFT only).

So this script works in three passes:

  1. CRAWL    the board-actions list (following pagination) and open every
              action page; keep pages that mention the behavioural health /
              behavioural science board or a counselling licence.
  2. DOWNLOAD every PDF linked from a kept page into
                 state_data\Iowa\_all_behavioral_health\
  3. CLASSIFY each PDF by reading its first pages: LMHC / mental health
              counselor orders are copied into  state_data\Iowa\  as
              "Lastname, Firstname <case>.pdf"; other professions stay in the
              holding folder; scans with no text go to  state_data\Iowa\review\
              for OCR, then  py download_iowa_orders.py --reclassify

Everything found is written to manifest.csv (one row per PDF) and
actions.csv (one row per action page).

Usage (from this folder):
    py download_iowa_orders.py                 # crawl, download, classify
    py download_iowa_orders.py --list-only     # crawl only, write actions.csv
    py download_iowa_orders.py --reclassify    # re-run pass 3 only (after OCR)
    py download_iowa_orders.py --max-pages 20  # limit list pagination (default 300)
"""

from __future__ import annotations

import argparse
import csv
import re
import shutil
import sys
import time
from pathlib import Path
from urllib.parse import urljoin, urlparse, unquote, parse_qs

import requests
from bs4 import BeautifulSoup

SITE = "https://dial.iowa.gov"
LIST_PATH = "/i-need/board-actions"
PDF_HOSTS = ("dial.iowa.gov", "documents.iowa.gov", "hhs.iowa.gov", "idph.iowa.gov", "www.dial.iowa.gov")

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
}
PAGES_TO_READ = 3
MIN_TEXT_CHARS = 200

# An action page is worth downloading if it mentions the counselling board or licence.
BOARD_WORDS = re.compile(
    r"behavioral health professionals|behavioral science|mental health counsel|\bLMHC\b|"
    r"marriage and family|\bLMFT\b",
    re.I,
)
COUNSELOR = re.compile(r"mental health counsel|\bLMHC\b|\bTLMHC\b", re.I)
OTHER_RULES = [
    (re.compile(r"marriage and family|marriage & family|\bLMFT\b|\bTLMFT\b", re.I), "marriage & family therapy"),
    (re.compile(r"social work|\bLISW\b|\bLMSW\b|\bLBSW\b", re.I), "social work"),
    (re.compile(r"psycholog", re.I), "psychology"),
    (re.compile(r"behavior analy|\bBCBA\b|\bLBA\b", re.I), "behavior analysis"),
    (re.compile(r"applicant", re.I), "applicant"),
]
CASE_NO = re.compile(r"\b(\d{2}-\d{2,4}(?:-\d{1,4})?|[A-Z]{2,4}-?\d{2}-\d{2,4})\b")
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
# Pass 1: crawl the list and the action pages
# --------------------------------------------------------------------------- #

def action_links_on(html: str) -> tuple[list[tuple[str, str]], str | None]:
    """Return ([(action_url, list_text)], next_page_url) for one list page."""
    soup = BeautifulSoup(html, "html.parser")
    actions: list[tuple[str, str]] = []
    seen = set()
    next_url = None
    for a in soup.find_all("a", href=True):
        url = urljoin(SITE, a["href"])
        p = urlparse(url)
        if p.netloc and p.netloc not in PDF_HOSTS:
            continue
        path = p.path.rstrip("/")
        if path.startswith(LIST_PATH + "/") and not path.lower().endswith(".pdf"):
            if url in seen:
                continue
            seen.add(url)
            container = a
            for parent in a.parents:
                if parent.name in ("tr", "li", "article", "div"):
                    container = parent
                    break
            actions.append((url, clean_text(container.get_text(" ", strip=True))[:300]))
        elif path == LIST_PATH and "page" in parse_qs(p.query):
            rel = (a.get("rel") or [])
            label = clean_text(a.get_text()).lower()
            if "next" in rel or label in ("next", "next ›", "›", "next page", "next >", ">"):
                next_url = url
    return actions, next_url


def pdf_links_on(html: str, base: str) -> list[tuple[str, str]]:
    soup = BeautifulSoup(html, "html.parser")
    out, seen = [], set()
    for a in soup.find_all("a", href=True):
        url = urljoin(base, a["href"])
        p = urlparse(url)
        if p.path.lower().endswith(".pdf") and (p.netloc in PDF_HOSTS or p.netloc.endswith("iowa.gov")):
            if url not in seen:
                seen.add(url)
                out.append((url, clean_text(a.get_text(" ", strip=True))))
    return out


def crawl(max_pages: int, debug: bool) -> list[dict]:
    url = urljoin(SITE, LIST_PATH)
    actions: list[dict] = []
    seen_actions = set()
    for page_no in range(1, max_pages + 1):
        try:
            html = fetch(url)
        except Exception as exc:  # noqa: BLE001
            print(f"  WARNING list page {page_no} failed: {exc}")
            break
        found, next_url = action_links_on(html)
        new = [(u, t) for u, t in found if u not in seen_actions]
        print(f"  list page {page_no:>3}: {len(found)} action links ({len(new)} new)")
        if debug or (page_no == 1 and not found):
            DEBUG_DIR.mkdir(exist_ok=True)
            (DEBUG_DIR / f"list_page_{page_no}.html").write_text(html, encoding="utf-8")
        for action_url, list_text in new:
            seen_actions.add(action_url)
            actions.append({"action_url": action_url, "list_text": list_text})
        if not next_url or not new:
            break
        url = next_url
        time.sleep(PAUSE_SECONDS)

    print(f"\nOpening {len(actions)} action page(s) to find documents...")
    for i, act in enumerate(actions, 1):
        time.sleep(PAUSE_SECONDS)
        try:
            html = fetch(act["action_url"])
        except Exception as exc:  # noqa: BLE001
            act.update(page_text="", relevant="error", pdf_urls="", pdf_labels="", note=str(exc))
            continue
        soup = BeautifulSoup(html, "html.parser")
        main = soup.find("main") or soup.find("article") or soup
        text = clean_text(main.get_text(" ", strip=True))
        title = clean_text(soup.title.get_text()) if soup.title else ""
        pdfs = pdf_links_on(html, act["action_url"])
        relevant = bool(BOARD_WORDS.search(text + " " + act["list_text"]))
        act.update(
            title=title,
            page_text=text[:1500],
            relevant="yes" if relevant else "no",
            pdf_urls=" | ".join(u for u, _ in pdfs),
            pdf_labels=" | ".join(l for _, l in pdfs),
            note="" if pdfs else "no PDF links on page",
        )
        if i % 25 == 0:
            print(f"  ... {i}/{len(actions)}")
    return actions


ACTION_FIELDS = ["action_url", "title", "list_text", "relevant", "pdf_urls", "pdf_labels", "note", "page_text"]


def write_actions(actions: list[dict]) -> None:
    with ACTIONS_PATH.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=ACTION_FIELDS, extrasaction="ignore")
        w.writeheader()
        w.writerows(actions)


# --------------------------------------------------------------------------- #
# Pass 2: download every PDF from relevant action pages
# --------------------------------------------------------------------------- #

def slug(s: str, n: int = 60) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "-", s).strip("-")[:n]


def download_pdfs(actions: list[dict]) -> dict[str, dict]:
    """Returns {local_filename: {action, pdf_url, label}}."""
    ALL_FOLDER.mkdir(parents=True, exist_ok=True)
    jobs = []
    for act in actions:
        if act.get("relevant") != "yes" or not act.get("pdf_urls"):
            continue
        urls = act["pdf_urls"].split(" | ")
        labels = act["pdf_labels"].split(" | ") if act.get("pdf_labels") else [""] * len(urls)
        action_slug = slug(urlparse(act["action_url"]).path.rsplit("/", 1)[-1])
        for u, label in zip(urls, labels):
            local = f"{action_slug}__{slug(unquote(Path(urlparse(u).path).stem))}.pdf"
            jobs.append((local, u, label, act))
    index: dict[str, dict] = {}
    with LOG_PATH.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=["filename", "status", "official_url", "message"])
        writer.writeheader()
        total, ok, skipped, failed = len(jobs), 0, 0, 0
        for i, (local, u, label, act) in enumerate(jobs, 1):
            index[local] = {"action": act, "pdf_url": u, "label": label}
            target = ALL_FOLDER / local
            row = {"filename": local, "official_url": u, "message": ""}
            if target.exists() and target.stat().st_size > 0:
                skipped += 1
                writer.writerow({**row, "status": "Already downloaded"})
                continue
            try:
                data = fetch(u, binary=True)
                if not data.startswith(b"%PDF"):
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


def classify_text(text: str) -> tuple[str, str]:
    if len(text.strip()) < MIN_TEXT_CHARS:
        return "review", "no text layer (scan) - OCR then --reclassify"
    if COUNSELOR.search(text):
        return "counselor", ""
    for pattern, label in OTHER_RULES:
        if pattern.search(text):
            return "drop", label
    return "review", "profession not found in first pages"


def name_from(list_text: str, page_text: str, pdf_body: str) -> tuple[str, str]:
    """Try 'Firstname Lastname, City' from the list, then 'In the matter of ...' from the PDF."""
    for src in (list_text, page_text):
        m = re.match(r"\s*(?:\d{1,2}/\d{1,2}/\d{2,4}\s+|[A-Z][a-z]{2,8} \d{1,2}, \d{4}\s+)?([A-Z][A-Za-z'\-\.]+(?: [A-Z][A-Za-z'\-\.]+){1,3}),", src or "")
        if m:
            tokens = m.group(1).split()
            return tokens[-1], " ".join(tokens[:-1])
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
]


def classify_all(index: dict[str, dict] | None) -> None:
    STATE_FOLDER.mkdir(parents=True, exist_ok=True)
    index = index or {}
    # If we are reclassifying without a fresh crawl, rebuild what we can from the old manifest.
    if not index and MANIFEST_PATH.exists():
        with MANIFEST_PATH.open(encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                index[r["source_file"]] = {
                    "action": {"action_url": r.get("action_url", ""), "list_text": "", "page_text": ""},
                    "pdf_url": r.get("official_url", ""),
                    "label": r.get("doc_label", ""),
                }
    sources = {p.name: p for p in ALL_FOLDER.glob("*.pdf")}
    if REVIEW_FOLDER.exists():
        for p in REVIEW_FOLDER.glob("*.pdf"):
            sources[p.name] = p
    rows, seen, counts = [], {}, {}
    for name in sorted(sources):
        src = sources[name]
        meta = index.get(name, {"action": {}, "pdf_url": "", "label": ""})
        act = meta["action"]
        try:
            body = pdf_text(src)
        except Exception as exc:  # noqa: BLE001
            body = ""
            category, note = "review", f"could not read PDF: {exc}"
        else:
            category, note = classify_text(body)
        last, first = name_from(act.get("list_text", ""), act.get("page_text", ""), body)
        case = case_from(act.get("list_text", ""), act.get("page_text", ""), body[:3000])
        filename = ""
        if category == "counselor":
            name_part = f"{last}, {first}".strip(", ").strip() or src.stem
            key = case or slug(meta.get("label") or src.stem, 40)
            base = ILLEGAL_FILENAME.sub("", f"{name_part} {key}").strip()
            n = seen.get(base, 0) + 1
            seen[base] = n
            filename = f"{base}.pdf" if n == 1 else f"{base} ({n}).pdf"
            dest = STATE_FOLDER / filename
            if not dest.exists():
                shutil.copy2(src, dest)
        elif category == "review" and "scan" in note:
            REVIEW_FOLDER.mkdir(exist_ok=True)
            if not (REVIEW_FOLDER / name).exists():
                shutil.copy2(src, REVIEW_FOLDER / name)
        counts[category] = counts.get(category, 0) + 1
        rows.append(
            {
                "source_file": name,
                "official_url": meta.get("pdf_url", ""),
                "action_url": act.get("action_url", ""),
                "doc_label": meta.get("label", ""),
                "last_name": last,
                "first_name": first,
                "case_number": case,
                "category": category,
                "category_note": note,
                "text_chars": len(body.strip()),
                "filename": filename,
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
    ap.add_argument("--list-only", action="store_true", help="crawl and write actions.csv, download nothing")
    ap.add_argument("--reclassify", action="store_true", help="skip crawl/download; re-run classification")
    ap.add_argument("--max-pages", type=int, default=300, help="maximum list pages to follow")
    ap.add_argument("--debug-html", action="store_true", help="save every list page under downloader\\debug\\")
    args = ap.parse_args(argv)

    print(f"Iowa DIAL board actions -> {STATE_FOLDER}")
    if args.reclassify:
        classify_all(None)
        return 0

    actions = crawl(args.max_pages, args.debug_html)
    if not actions:
        print(f"\nNo action links found on the list page. Its HTML is under {DEBUG_DIR}; compare with the live site.")
        return 1
    write_actions(actions)
    relevant = [a for a in actions if a.get("relevant") == "yes"]
    with_pdf = [a for a in relevant if a.get("pdf_urls")]
    print(f"\nactions.csv written: {len(actions)} action pages, {len(relevant)} counselling-board related, "
          f"{len(with_pdf)} with PDF links")
    if args.list_only:
        return 0
    index = download_pdfs(actions)
    classify_all(index)
    return 0


if __name__ == "__main__":
    sys.exit(main())
