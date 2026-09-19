"""
rename_california_files.py: identify and rename the California BBS order PDFs
for a fixed list of Licensed Professional Clinical Counselors (LPCC).

You saved order PDFs into state_data\\California\\ by hand from the DCA
License Search and ran OCR on them. This tool reads the OCR text of each
PDF, matches it to one of the 29 LPCCs in the TARGETS list below (by license
number first, then by name), and renames the matched files to the project's
convention:

    Lastname, Firstname LPCC <number> <effective date>.pdf
    e.g.  Osborn, Bruce Eugene LPCC 7272 2023-05-10.pdf

Files that do not match any target, or that match more than one, are left
alone and listed so you can look at them. Nothing is renamed until you add
--apply; the default is a dry run that only prints the plan and writes
rename_plan.csv next to this script.

Put this file (and Run_Rename_California.cmd) INTO the same folder as the
PDFs, state_data\\California\\, and double-click the .cmd. It renames the
PDFs sitting beside it.

Usage (from the California folder):
    py rename_california_files.py            # dry run: print the plan, change nothing
    py rename_california_files.py --apply    # rename for real
    py rename_california_files.py --folder "C:\\path\\to\\pdfs"   # act on another folder

Needs PyMuPDF:  py -m pip install pymupdf
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from pathlib import Path

# (license_number, last, first, [name variants]) for the 29 LPCCs of interest.
# Matching uses the license number first; the name variants are the backup and
# the source of the file name. Last/first were split by hand; a "?" marks a
# last name that was a judgement call (see the note in the printed output).
TARGETS = [
    (7272,  "Osborn",      "Bruce Eugene",       ["Bruce Eugene Osborn"]),
    (2145,  "Magalong",    "Stefanie Lynn",      ["Stefanie Lynn Magalong"]),
    (671,   "Smith",       "Willa Ann",          ["Willa Ann Smith"]),
    (997,   "Ryan",        "Nga Caroline Tran",  ["Nga Caroline Tran Ryan", "Nga Caroline Ryan", "Nga Tran Ryan"]),  # last name ?
    (1100,  "Herrera",     "Kathryn Christine",  ["Kathryn Christine Herrera"]),
    (591,   "Fox",         "Felita Walker",      ["Felita Walker Fox", "Felita Fox"]),
    (477,   "Bixler",      "Marcella",           ["Marcella Bixler"]),
    (847,   "Gold",        "Rebecca",            ["Rebecca Gold"]),
    (7873,  "Lopez",       "Tabitha Ann",        ["Tabitha Ann Lopez"]),
    (8332,  "Ingalls",     "Amanda A",           ["Amanda A Ingalls", "Amanda A. Ingalls", "Amanda Ann Ingalls-Brunzell", "Amanda Ann Ingalls Brunzell", "Amanda Ingalls"]),
    (7615,  "Powers",      "Michelle Lianne",    ["Michelle Lianne Powers"]),
    (7673,  "Swinney",     "Hannah Ruth",        ["Hannah Ruth Swinney"]),
    (11300, "Redstone",    "Phoenix Kase",       ["Phoenix Kase Redstone"]),
    (11316, "Ceja",        "Eduardo Alejandro",  ["Eduardo Alejandro Ceja"]),
    (11320, "Blair",       "Andrew Robert",      ["Andrew Robert Blair"]),
    (11429, "Churn",       "Ayana Kena",         ["Ayana Kena Churn"]),
    (1920,  "Mackie",      "Keri Lynn",          ["Keri Lynn Mackie"]),
    (7805,  "Gosling",     "Meaghan Leigh",      ["Meaghan Leigh Gosling"]),
    (6557,  "Navarro",     "Juan Carlos",        ["Juan Carlos Navarro"]),
    (13464, "Matisek",     "Katherine Elizabeth",["Katherine Elizabeth Matisek"]),
    (4583,  "Mc Donald",   "Sean Bartley",       ["Sean Bartley Mc Donald", "Sean Bartley McDonald", "Sean McDonald"]),
    (6998,  "Hook",        "Andrew John",        ["Andrew John Hook"]),
    (12854, "Weigel",      "Christy Lynn",       ["Christy Lynn Weigel"]),
    (13967, "Schmitt",     "Evelyn Beatriz",     ["Evelyn Beatriz Schmitt"]),
    (14022, "Wang",        "Wen-Chi",            ["Wen-Chi Wang", "Wen Chi Wang"]),
    (14259, "Hollenbaugh", "Mary Louise",        ["Mary Louise Hollenbaugh"]),
    (828,   "Lam",         "Gabriel",            ["Gabriel Lam"]),
    (498,   "Au",          "Susan W. S.",        ["Susan W. S. Au", "Susan W S Au", "Susan Au"]),
    (14756, "Woodson",     "Kyle Emir",          ["Kyle Emir Woodson"]),
    # Licensed LPCCs found in the saved orders but not on the original 29-name
    # list (the BBS name index missed Thorpe and Still, and showed Alvarez as
    # accusation-only though his case later resolved). Added 2026-09-19.
    (1067,  "Alvarez",     "Guillermo Jesus",    ["Guillermo Jesus Alvarez", "Guillermo Alvarez"]),
    (240,   "Thorpe",      "Kevin Scott",        ["Kevin Scott Thorpe", "Kevin Thorpe"]),
    (None,  "Still",       "Elizabeth Marie",    ["Elizabeth Marie Still", "Elizabeth Still"]),  # LPCC number not yet known; matched by name
]

ILLEGAL = re.compile(r'[\\/:*?"<>|]+')
MONTHS = ("january february march april may june july august september october "
          "november december").split()
MONTH_IX = {m: i + 1 for i, m in enumerate(MONTHS)}


def norm(s):
    return re.sub(r"[^a-z0-9]+", "", (s or "").lower())


def license_hit(text, number):
    """True if the LPCC license number appears next to an LPCC marker."""
    if number is None:
        return False
    n = str(number)
    # LPCC ... number   (e.g. "LPCC 7272", "LPCC No. 7272", "LPCC# 7272")
    if re.search(r"LPCC\D{0,15}0*" + n + r"\b", text):
        return True
    # number ... LPCC   (e.g. "7272, LPCC", "No. 7272 LPCC")
    if re.search(r"\b0*" + n + r"\D{0,15}LPCC", text):
        return True
    # "Licensed Professional Clinical Counselor" then the number within 60 chars
    if re.search(r"Licensed Professional Clinical Counselor.{0,60}?\b0*" + n + r"\b", text, re.S):
        return True
    return False


def name_hit(ntext, variants):
    for v in variants:
        nv = norm(v)
        if nv and nv in ntext:
            return True
        toks = [t for t in re.split(r"\s+", v) if t]
        if len(toks) >= 2:
            fl = norm(toks[0] + toks[-1])          # first + last, middle dropped
            if fl and fl in ntext:
                return True
    return False


DATE_PATTERNS = [
    (re.compile(r"\b(" + "|".join(MONTHS) + r")\s+(\d{1,2}),?\s+(\d{4})\b", re.I), "mdy_word"),
    (re.compile(r"\b(\d{1,2})/(\d{1,2})/(\d{4})\b"), "mdy_num"),
    (re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b"), "ymd"),
]


def all_dates(text):
    out = []
    for rx, kind in DATE_PATTERNS:
        for m in rx.finditer(text):
            try:
                if kind == "mdy_word":
                    mo = MONTH_IX[m.group(1).lower()]; d = int(m.group(2)); y = int(m.group(3))
                elif kind == "mdy_num":
                    mo = int(m.group(1)); d = int(m.group(2)); y = int(m.group(3))
                else:
                    y = int(m.group(1)); mo = int(m.group(2)); d = int(m.group(3))
                if 1990 <= y <= 2035 and 1 <= mo <= 12 and 1 <= d <= 31:
                    out.append((y, mo, d, m.start()))
            except (ValueError, KeyError):
                continue
    return out


def effective_date(text):
    """Best-effort: the 'effective' date, else 'Dated:', else the latest date, else ''."""
    low = text.lower()
    for cue in ("effective", "dated", "it is so ordered"):
        i = low.find(cue)
        while i != -1:
            window = text[i:i + 120]
            ds = all_dates(window)
            if ds:
                y, mo, d, _ = ds[0]
                return f"{y:04d}-{mo:02d}-{d:02d}"
            i = low.find(cue, i + 1)
    ds = all_dates(text)
    if ds:
        y, mo, d, _ = max(ds)
        return f"{y:04d}-{mo:02d}-{d:02d}"
    return ""


def read_text(path):
    try:
        import pymupdf
    except ImportError:
        try:
            import fitz as pymupdf
        except ImportError:
            print("PyMuPDF is not installed; run  py -m pip install pymupdf")
            sys.exit(1)
    try:
        with pymupdf.open(path) as doc:
            return "".join(pg.get_text() for pg in doc)
    except Exception as exc:  # noqa: BLE001
        return f"__UNREADABLE__ {exc}"


def match_target(text):
    """Return (target, how) or (None, reason)."""
    ntext = norm(text)
    lic = [t for t in TARGETS if license_hit(text, t[0])]
    nam = [t for t in TARGETS if name_hit(ntext, t[3])]
    if len(lic) == 1:
        t = lic[0]
        how = "license+name" if t in nam else "license"
        return t, how
    if len(lic) > 1:
        return None, "multiple license numbers matched: " + ", ".join(str(t[0]) for t in lic)
    if len(nam) == 1:
        return nam[0], "name only (no license number found)"
    if len(nam) > 1:
        return None, "multiple names matched: " + ", ".join(t[1] for t in nam)
    return None, "no target license number or name found"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true", help="rename for real (default is a dry run)")
    ap.add_argument("--folder", default="", help="folder holding the PDFs (default: this script's folder)")
    ap.add_argument("--move-nonlpcc", action="store_true", help="on --apply, move the left-alone (non-LPCC) PDFs into a _not_LPCC subfolder")
    args = ap.parse_args(argv)

    folder = Path(args.folder).resolve() if args.folder else Path(__file__).resolve().parent
    pdfs = sorted(folder.glob("*.pdf"))
    if not pdfs:
        print(f"No PDFs found in {folder}")
        return 1
    print(f"{len(pdfs)} PDF(s) in {folder}\n")

    plan = []          # (src, new_name, person_key, how, date)
    unmatched = []     # (name, reason)
    unmatched_paths = []
    used = {}
    plan_rows = []
    for p in pdfs:
        text = read_text(p)
        if text.startswith("__UNREADABLE__"):
            unmatched.append((p.name, text)); unmatched_paths.append(p); continue
        t, how = match_target(text)
        if not t:
            unmatched.append((p.name, how)); unmatched_paths.append(p)
            plan_rows.append({"current": p.name, "match": "", "how": how, "date": "", "new_name": ""})
            continue
        number, last, first, _ = t
        date = effective_date(text) or "undated"
        lickey = f"LPCC {number}" if number is not None else "LPCC"
        base = ILLEGAL.sub("", f"{last}, {first} {lickey} {date}").strip()
        k = used.get(base, 0) + 1
        used[base] = k
        new_name = f"{base}.pdf" if k == 1 else f"{base} ({k}).pdf"
        plan.append((p, new_name, lickey, how, date))
        plan_rows.append({"current": p.name, "match": f"{lickey} {first} {last}",
                          "how": how, "date": date, "new_name": new_name})

    print(f"Matched to a target: {len(plan)}")
    print(f"Left alone:          {len(unmatched)}\n")
    for src, new_name, key, how, date in plan:
        print(f"  {src.name}\n    -> {new_name}   [{key}, {how}]")
    if unmatched:
        print("\nLeft alone (look at these by hand):")
        for name, reason in unmatched:
            print(f"  ? {name}   ({reason})")

    found = {key for _, _, key, _, _ in plan}
    missing = [f"{('LPCC '+str(t[0])) if t[0] is not None else 'LPCC'} {t[2]} {t[1]}" for t in TARGETS
               if (('LPCC '+str(t[0])) if t[0] is not None else 'LPCC') not in found]
    if missing:
        print(f"\n{len(missing)} of the 29 targets have no PDF in the folder:")
        for m in missing:
            print(f"  - {m}")

    plan_csv = (Path(args.folder).resolve() if args.folder else Path(__file__).resolve().parent) / "rename_plan.csv"
    with plan_csv.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["current", "match", "how", "date", "new_name"])
        w.writeheader()
        w.writerows(plan_rows)
    print(f"\nPlan written to {plan_csv}")

    if not args.apply:
        print("\nDry run. Check the plan above (and rename_plan.csv), then run with --apply to rename.")
        return 0

    if args.move_nonlpcc and unmatched_paths:
        out = folder / "_not_LPCC"
        out.mkdir(exist_ok=True)
        moved = 0
        for up in unmatched_paths:
            dest = out / up.name
            if not dest.exists():
                up.rename(dest); moved += 1
        print(f"Moved {moved} non-LPCC file(s) into {out}")
    n = 0
    for src, new_name, *_ in plan:
        dst = src.with_name(new_name)
        if dst.exists() and dst != src:
            print(f"  SKIP {src.name}: {new_name} already exists")
            continue
        src.rename(dst)
        n += 1
    print(f"\nRenamed {n} file(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
