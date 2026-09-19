"""
check_ocr_status.py: which board-order PDFs still need OCR?

Walks every folder under a root (default: the state_data folder next to
this script, or the folder given on the command line), opens each PDF
with PyMuPDF and counts the characters of real text inside. A file with
fewer than 200 characters across all its pages is an image-only scan that
Foxit has not OCR'd yet.

Prints one line per folder (files, with text, image-only, unreadable) and
writes ocr_status.csv next to this script with one row per PDF, so the
image-only list can be sorted or filtered in Excel.

Usage (from this folder):
    py check_ocr_status.py
    py check_ocr_status.py "C:\path\to\state_data\qti-converter-board-orders-data"
    py check_ocr_status.py --list          # also print every image-only file name

Needs PyMuPDF:  py -m pip install pymupdf
"""

import csv
import sys
from pathlib import Path

MIN_CHARS = 200


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    show_list = "--list" in sys.argv
    root = Path(args[0]) if args else Path(__file__).resolve().parent / "state_data"
    if not root.is_dir():
        print(f"Folder not found: {root}")
        return 1
    try:
        import pymupdf
    except ImportError:
        try:
            import fitz as pymupdf
        except ImportError:
            print("PyMuPDF is not installed. Run:  py -m pip install pymupdf")
            return 1

    pdfs = sorted(root.rglob("*.pdf"))
    if not pdfs:
        print(f"No PDFs under {root}")
        return 1
    print(f"Checking {len(pdfs):,} PDFs under {root}\n")

    rows = []
    per_folder: dict[Path, dict[str, int]] = {}
    for i, p in enumerate(pdfs, 1):
        folder = p.parent.relative_to(root)
        tally = per_folder.setdefault(folder, {"files": 0, "text": 0, "image": 0, "unreadable": 0})
        tally["files"] += 1
        try:
            with pymupdf.open(p) as doc:
                pages = doc.page_count
                chars = sum(len(page.get_text()) for page in doc)
            status = "text" if chars >= MIN_CHARS else "image"
        except Exception as exc:  # noqa: BLE001
            pages, chars, status = 0, 0, "unreadable"
            print(f"  UNREADABLE {p.relative_to(root)}: {exc}")
        tally[status] += 1
        rows.append({"folder": str(folder), "file": p.name, "pages": pages, "chars": chars, "status": status})
        if i % 200 == 0:
            print(f"  ... {i:,} of {len(pdfs):,}")

    print(f"\n{'Folder':<45} {'Files':>6} {'Text':>6} {'Image':>6} {'Bad':>4}")
    print("-" * 70)
    tot = {"files": 0, "text": 0, "image": 0, "unreadable": 0}
    for folder in sorted(per_folder):
        t = per_folder[folder]
        for k in tot:
            tot[k] += t[k]
        name = str(folder) if str(folder) != "." else "(root)"
        flag = "  <- needs OCR" if t["image"] else ""
        print(f"{name:<45} {t['files']:>6} {t['text']:>6} {t['image']:>6} {t['unreadable']:>4}{flag}")
    print("-" * 70)
    print(f"{'TOTAL':<45} {tot['files']:>6} {tot['text']:>6} {tot['image']:>6} {tot['unreadable']:>4}")

    if show_list:
        print("\nImage-only files (no text layer yet):")
        for r in rows:
            if r["status"] == "image":
                print(f"  {r['folder']}\\{r['file']}")

    out = Path(__file__).resolve().parent / "ocr_status.csv"
    with out.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["folder", "file", "pages", "chars", "status"])
        w.writeheader()
        w.writerows(rows)
    print(f"\nPer-file detail written to {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
