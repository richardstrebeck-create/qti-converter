"""
Vermont Office of Professional Regulation decision downloader (LCMHC only).

Vermont posts every conduct decision for the Board of Allied Mental Health
Practitioners as an individual PDF in one SharePoint folder:

    https://outside.vermont.gov/dept/sos/office_professional_regulation/
        conduct_decisions/allied_mental_health/

That folder mixes Licensed Clinical Mental Health Counselors with marriage and
family therapists, psychoanalysts and non-licensed psychotherapists, and the
file names (lastname_firstname_docket_NNNN.pdf) do not say which is which.
So this script works in two passes:

  1. LIST + DOWNLOAD  every PDF in the folder into
        state_data\Vermont\_all_allied_mental_health\
     (skipping files already present).
  2. CLASSIFY  each PDF by reading its first pages: decisions that name a
     "Licensed Clinical Mental Health Counselor" / LCMHC are copied into
        state_data\Vermont\   as  "Lastname, Firstname docket NNNN.pdf";
     other professions stay in _all_allied_mental_health only;
     PDFs with no text layer (older scans) are copied to
        state_data\Vermont\review\   for Foxit OCR, after which
        py download_vermont_orders.py --reclassify   sorts them.

Folder listing tries the SharePoint REST endpoint first and falls back to
the AllItems.aspx page; both are unverified from the machine this was
written on (see README).

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
# Candidate SharePoint web roots for the REST API, most specific first.
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

COUNSELOR = re.compile(r"clinical mental health counsel|\bLCMHC\b|mental health counselor", re.I)
OTHER_RULES = [
    (re.compile(r"marriage and family|marriage & family|\bLMFT\b", re.I), "marriage & family therapy"),
    (re.compile(r"psychoanalyst", re.I), "psychoanalyst"),
    (re.compile(r"non-?licensed psychotherapist|roster(ed)? psychotherapist|psychotherapist", re.I),
     "non-licensed psychotherapist"),
    (re.compile(r"applicant", re.I), "applicant"),
]
DOCKET = re.compile(r"docket[_\- ]*([A-Za-z]{0,2}\d{4,8}(?:[_\-]\d{4,8})*)", re.I)
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

def list_via_rest() -> list[str]:
    """SharePoint REST: GetFolderByServerRelativeUrl(...)/Files. Returns server-relative PDF paths."""
    for root in WEB_ROOTS:
        api = f"{SITE}{root}/_api/web/GetFolderByServerRelativeUrl('{quote(FOLDER)}')/Files?$select=Name,ServerRelativeUrl&$top=5000"
        try:
            text = fetch(api, headers={"Accept": "application/json;odata=nometadata"})
            data = json.loads(text)
            items = data.get("value") or data.get("d", {}).get("results") or []
            paths = [it["ServerRelativeUrl"] for it in items if it.get("Name", "").lower().endswith(".pdf")]
            if paths:
                print(f"  folder listed via REST ({root or '/'}): {len(paths)} PDFs")
                return paths
        except Exception as exc:  # noqa: BLE001
            print(f"  REST listing failed at {root or '/'}: {str(exc)[:90]}")
    return []


def list_via_html() -> list[str]:
    """Fallback: scrape every .pdf link under the folder from the AllItems view page."""
    candidates = [
        f"{SITE}/dept/sos/office_professional_regulation/forms/allitems.aspx?RootFolder={quote(FOLDER)}",
        f"{SITE}/dept/sos/office_professional_regulation/Forms/AllItems.aspx?RootFolder={quote(FOLDER)}",
        f"{SITE}{FOLDER}/Forms/AllItems.aspx",
        f"{SITE}{FOLDER}/",
    ]
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
        # SharePoint often embeds the listing as JSON inside a script tag.
        for m in re.finditer(r'"FileRef"\s*:\s*"([^"]+\.pdf)"', html, re.I):
            found.add(unquote(m.group(1)))
        if found:
            print(f"  folder listed via HTML page: {len(found)} PDFs")
            return sorted(found)
        DEBUG_DIR.mkdir(exist_ok=True)
        (DEBUG_DIR / ("listing_" + re.sub(r"\W+", "_", url)[-60:] + ".html")).write_text(html, encoding="utf-8")
    return []


def list_folder() -> list[str]:
    return list_via_rest() or list_via_html()


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


def classify_pdf(path: Path) -> tuple[str, str, int]:
    """Return (category, note, chars): counselor / drop / review."""
    try:
        text = pdf_text(path)
    except Exception as exc:  # noqa: BLE001
        return "review", f"could not read PDF: {exc}", 0
    chars = len(text.strip())
    if chars < MIN_TEXT_CHARS:
        return "review", "no text layer (scan) - OCR then --reclassify", chars
    if COUNSELOR.search(text):
        return "counselor", "", chars
    for pattern, label in OTHER_RULES:
        if pattern.search(text):
            return "drop", label, chars
    return "review", "profession not found in first pages", chars


def name_from_filename(stem: str) -> tuple[str, str, str]:
    """'reed_luce_mary_docket_mh020903' -> ('Reed Luce', 'Mary', 'mh020903')."""
    s = unquote(stem)
    docket = ""
    m = DOCKET.search(s)
    if m:
        docket = m.group(1).replace("_", "-")
        s = s[: m.start()]
    tokens = [t for t in re.split(r"[_\-\s]+", s) if t and not t.isdigit()]
    if not tokens:
        return "", "", docket
    if len(tokens) == 1:
        return tokens[0].title(), "", docket
    # Vermont files put the surname first; a two-word surname shows up as three tokens.
    if len(tokens) >= 3:
        return " ".join(t.title() for t in tokens[:-1]), tokens[-1].title(), docket
    return tokens[0].title(), tokens[1].title(), docket


def target_filename(stem: str, seen: dict[str, int]) -> str:
    last, first, docket = name_from_filename(stem)
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
    "category", "category_note", "text_chars", "filename",
]


def write_manifest(rows: list[dict]) -> None:
    with MANIFEST_PATH.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=MANIFEST_FIELDS)
        w.writeheader()
        w.writerows(rows)


def download_all(paths: list[str]) -> None:
    ALL_FOLDER.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=["filename", "status", "official_url", "message"])
        writer.writeheader()
        total, ok, skipped, failed = len(paths), 0, 0, 0
        for i, rel in enumerate(paths, 1):
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


def classify_all() -> list[dict]:
    STATE_FOLDER.mkdir(parents=True, exist_ok=True)
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
        category, note, chars = classify_pdf(src)
        last, first, docket = name_from_filename(src.stem)
        filename = ""
        if category == "counselor":
            filename = target_filename(src.stem, seen)
            dest = STATE_FOLDER / filename
            if not dest.exists():
                shutil.copy2(src, dest)
        elif category == "review" and "scan" in note:
            REVIEW_FOLDER.mkdir(exist_ok=True)
            dest = REVIEW_FOLDER / name
            if not dest.exists():
                shutil.copy2(src, dest)
        counts[category] = counts.get(category, 0) + 1
        rows.append(
            {
                "source_file": name,
                "official_url": SITE + quote(f"{FOLDER}/{name}"),
                "last_name": last,
                "first_name": first,
                "docket": docket,
                "category": category,
                "category_note": note,
                "text_chars": chars,
                "filename": filename,
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
        paths = list_folder()
        if not paths:
            print(
                "\nCould not list the decisions folder by REST or by page scrape.\n"
                f"Any listing page fetched was saved under {DEBUG_DIR}. Open the folder in a browser,\n"
                "and if the site has changed, update FOLDER / WEB_ROOTS / list_via_html() candidates."
            )
            return 1
        if args.list_only:
            rows = []
            for rel in paths:
                last, first, docket = name_from_filename(Path(rel).stem)
                rows.append(
                    {"source_file": unquote(Path(rel).name), "official_url": SITE + quote(rel),
                     "last_name": last, "first_name": first, "docket": docket,
                     "category": "not downloaded", "category_note": "", "text_chars": "", "filename": ""}
                )
            write_manifest(rows)
            print(f"Manifest written with {len(rows)} PDFs: {MANIFEST_PATH}")
            return 0
        download_all(paths)
    classify_all()
    return 0


if __name__ == "__main__":
    sys.exit(main())
