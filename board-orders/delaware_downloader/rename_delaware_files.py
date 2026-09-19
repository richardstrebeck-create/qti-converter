"""
rename_delaware_files.py: rename the hand-saved Delaware order PDFs to the
project's file names.

The Salesforce viewer saves each order under the board's own file name
("15-Hicks-Joseph-Discipline-2009.pdf", "Boykin - 2022.pdf"). The rest of
the project expects "Lastname, Firstname PC-0000043 2009 - Disciplinary
Order 2009.pdf", which is the name manifest.csv assigns to each document.
This script matches every PDF in the state folder to its manifest row and
renames it. Run it AFTER Foxit OCR (OCR in place keeps the name, so the
order does not matter, but do not run it while Foxit has a file open).

Usage (from this folder):
    py rename_delaware_files.py            # dry run: print the plan, change nothing
    py rename_delaware_files.py --apply    # rename for real

Matching: exact on the manifest's document_name for the "15-..." files;
a short table below for the six documents whose viewer name differs from
the manifest's document_name. Anything unmatched is listed and left alone.
"""

import csv
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent            # ...\state_data\Delaware\downloader
STATE_FOLDER = HERE.parent                         # ...\state_data\Delaware
MANIFEST = HERE / "manifest.csv"

# Viewer file name -> manifest document_name, for documents the viewer saves
# under a different name than the one DELPROS lists.
ALIASES = {
    "Boykin - 2022.pdf": "Boykin, Yvonne CA_2022",
    "Boykin 2023.pdf": "Boykin, Yvonne BO_2023",
    "Hicks, Joseph_2021.pdf": "Hicks, Joseph CA 2021",
    "Land, Lorraine 2023_Redacted.pdf": "Land, Lorraine BO_2023",
    "2 Corrected EmSusp Land, Lorraine - 2020.pdf": "Land. Lorraine BO_2020",
    "Land, Lorraine_CA - 2020.pdf": "Land, Lorraine CA_2020",
}


def norm(s: str) -> str:
    s = re.sub(r"\.pdf$", "", s, flags=re.I)
    return re.sub(r"[^a-z0-9]+", "", s.lower())


def main() -> int:
    apply = "--apply" in sys.argv
    if not MANIFEST.exists():
        print(f"manifest.csv not found at {MANIFEST}; run download_delaware_orders.py --list-only first")
        return 1
    rows = [r for r in csv.DictReader(MANIFEST.open(encoding="utf-8", newline="")) if r.get("url")]
    by_doc = {norm(r["document_name"]): r["filename"] for r in rows}
    targets = set(r["filename"] for r in rows)

    pdfs = sorted(p for p in STATE_FOLDER.glob("*.pdf"))
    plan, done, unmatched = [], [], []
    for p in pdfs:
        if p.name in targets:
            done.append(p.name)
            continue
        key = norm(ALIASES.get(p.name, p.name))
        target = by_doc.get(key)
        if target:
            plan.append((p, STATE_FOLDER / target))
        else:
            unmatched.append(p.name)

    print(f"{len(pdfs)} PDFs in {STATE_FOLDER}")
    print(f"  already named correctly: {len(done)}")
    print(f"  to rename:               {len(plan)}")
    print(f"  unmatched (left alone):  {len(unmatched)}")
    for src, dst in plan:
        print(f"    {src.name}\n      -> {dst.name}")
    for name in unmatched:
        print(f"    ? {name}")
    missing = targets - set(done) - {dst.name for _, dst in plan}
    if missing:
        print(f"\n{len(missing)} manifest document(s) not found in the folder:")
        for m in sorted(missing):
            print(f"    - {m}")

    if not apply:
        print("\nDry run. Add --apply to rename.")
        return 0
    n = 0
    for src, dst in plan:
        if dst.exists():
            print(f"  SKIP {src.name}: target already exists")
            continue
        src.rename(dst)
        n += 1
    print(f"\nRenamed {n} file(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
