"""
build_ma_lmhc_list.py: list the sanctioned Licensed Mental Health Counselors
(LMHC) in Massachusetts from the state's public license-verification API.

Massachusetts does NOT post board-order documents online. Its "Check a Health
License" site (https://checkahealthlicense.mass.gov/) shows, per licensee, the
license status and a "Compliance Actions & Fines" summary: the action type
(Revocation, Suspension, Probation, Surrender) and its start and end dates,
but not the order itself. The order documents are obtainable only by a
Public Records Act request to the Bureau of Health Professions Licensure
(PublicRecordsAdmin@MassMail.State.MA.US).

This script collects that INDEX. The site is an Angular app backed by a
public REST API (verified 2026-09-19):

  config   https://checkahealthlicense.mass.gov/environments/environment.json
           -> apiBaseUrl https://healthprofessionlicensing-api.mass.gov/api-public
  search   POST {apiBaseUrl}/search
           body {"licenseBoard":"BOARD_OF_REGISTRATION_OF_ALLIED_MENTAL_HEALTH_AND_HUMAN_SERVICES_PROFESSIONS",
                 "licenseMetaId":35, "firstName":"", "lastName":"<letter>",
                 "searchType":"BY_LICENSEE_NAME"}
           -> {"results":{"data":[...], "totalDataCount":N}}. Each row carries
           licenseNumber, name, city, computedStatus, and the action dates
           revokedDate, suspendedStartDate/EndDate, surrenderedDate.
  profile  {apiBaseUrl}/search/licenses/{id}  (one licensee; not needed here)

License type 35 is "Licensed Mental Health Counselor License". A single
search caps at 10,000 rows and Massachusetts has more LMHCs than that, so the
script searches each last-name letter a-z (the match is "contains", so the
union of all 26 covers everyone) and de-duplicates by id.

Sanctioned is decided from computedStatus and the action dates, using the
BHPL status definitions:
  Disciplinary  : Revoked, Suspension (incl. "Suspension, Expired"),
                  "Stayed Suspension", Probation (incl. "Probation, Expired"),
                  and any row with a revokedDate or suspendedStartDate.
  Surrender     : "Surrendered" or a surrenderedDate. Surrender may be
                  disciplinary (in lieu of / to resolve discipline) or a
                  voluntary agreement not to practice; the status alone does
                  not say which, so these are listed and flagged.
  Non-disciplinary (listed, not counted as a sanction): "Non-Disciplinary
                  Restriction", "Non-Disciplinary Condition".
Clean administrative statuses (Current, Expired, Deceased, Retired) are
dropped unless the row also carries a past action date.

Output: ma_lmhc_sanctioned.csv (one row per sanctioned LMHC) and a printed
summary. Nothing here is a board order; it is the index of who was
sanctioned, what kind, and when.

Usage (from this folder):
    py build_ma_lmhc_list.py
    py build_ma_lmhc_list.py --all-lmhc   # also write ma_lmhc_all.csv (every LMHC)

Needs: requests (py -m pip install requests).
"""

from __future__ import annotations

import argparse
import csv
import string
import sys
import time
from pathlib import Path

import requests

API = "https://healthprofessionlicensing-api.mass.gov/api-public"
BOARD = "BOARD_OF_REGISTRATION_OF_ALLIED_MENTAL_HEALTH_AND_HUMAN_SERVICES_PROFESSIONS"
LMHC_TYPE_ID = 35
PROFILE_URL = "https://checkahealthlicense.mass.gov/profiles/{id}"

HERE = Path(__file__).resolve().parent
SANCTIONED_CSV = HERE / "ma_lmhc_sanctioned.csv"
ALL_CSV = HERE / "ma_lmhc_all.csv"

PAUSE = 1.5
TIMEOUT = 90
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Content-Type": "application/json",
    "Accept": "application/json",
    "Origin": "https://checkahealthlicense.mass.gov",
    "Referer": "https://checkahealthlicense.mass.gov/",
}

DISCIPLINARY_STATUS = {
    "Revoked", "Suspension, Expired", "Suspended", "Stayed Suspension",
    "Probation", "Probation, Expired",
}
SURRENDER_STATUS = {"Surrendered"}
NONDISC_STATUS = {"Non-Disciplinary Restriction", "Non-Disciplinary Condition"}

session = requests.Session()
session.headers.update(HEADERS)


def search_letter(letter):
    body = {"licenseBoard": BOARD, "licenseMetaId": LMHC_TYPE_ID,
            "firstName": "", "lastName": letter, "searchType": "BY_LICENSEE_NAME"}
    for attempt in range(1, 4):
        try:
            r = session.post(API + "/search", json=body, timeout=TIMEOUT)
            r.raise_for_status()
            return r.json()["results"]["data"]
        except Exception as exc:  # noqa: BLE001
            if attempt == 3:
                raise RuntimeError(f"search '{letter}': {exc}")
            time.sleep(PAUSE * attempt)
    return []


def enumerate_lmhc():
    records = {}
    capped = []
    for ch in string.ascii_lowercase:
        data = search_letter(ch)
        if len(data) >= 10000:
            capped.append(ch)
        for x in data:
            records[x["id"]] = x
        print(f"  '{ch}': {len(data):>5} rows, union {len(records)}")
        time.sleep(PAUSE)
    if capped:
        print(f"  WARNING: letters {capped} hit the 10,000 cap; some names may be missing. "
              "Narrow those with two-letter queries if completeness matters.")
    return list(records.values())


def datepart(s):
    return (s or "")[:10]


def classify(rec):
    cs = (rec.get("computedStatus") or "").strip()
    has_rev = bool(rec.get("revokedDate"))
    has_susp = bool(rec.get("suspendedStartDate"))
    has_surr = bool(rec.get("surrenderedDate"))
    if cs in DISCIPLINARY_STATUS or has_rev or has_susp:
        if cs in SURRENDER_STATUS and not (has_rev or has_susp):
            return "Surrender"
        return "Disciplinary"
    if cs in SURRENDER_STATUS or has_surr:
        return "Surrender"
    if cs in NONDISC_STATUS:
        return "Non-disciplinary"
    return ""


def action_summary(rec):
    parts = []
    if rec.get("revokedDate"):
        parts.append(f"Revoked {datepart(rec['revokedDate'])}")
    if rec.get("suspendedStartDate"):
        span = datepart(rec["suspendedStartDate"])
        if rec.get("suspendedEndDate"):
            span += " to " + datepart(rec["suspendedEndDate"])
        parts.append(f"Suspended {span}")
    if rec.get("surrenderedDate"):
        parts.append(f"Surrendered {datepart(rec['surrenderedDate'])}")
    cs = (rec.get("computedStatus") or "")
    if "Probation" in cs and not parts:
        parts.append(cs)
    if not parts and cs:
        parts.append(cs)
    return "; ".join(parts)


FIELDS = ["license_number", "last_name", "first_name", "middle_initial", "city",
          "computed_status", "category", "action_summary",
          "revoked_date", "suspended_start", "suspended_end", "surrendered_date",
          "profile_url"]


def row_for(rec, category):
    return {
        "license_number": rec.get("licenseNumber", ""),
        "last_name": rec.get("lastName") or "",
        "first_name": rec.get("firstName") or "",
        "middle_initial": rec.get("middleInitial") or "",
        "city": rec.get("mailingCity") or rec.get("computedAddress") or "",
        "computed_status": rec.get("computedStatus") or "",
        "category": category,
        "action_summary": action_summary(rec),
        "revoked_date": datepart(rec.get("revokedDate")),
        "suspended_start": datepart(rec.get("suspendedStartDate")),
        "suspended_end": datepart(rec.get("suspendedEndDate")),
        "surrendered_date": datepart(rec.get("surrenderedDate")),
        "profile_url": PROFILE_URL.format(id=rec.get("id")),
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--all-lmhc", action="store_true", help="also write ma_lmhc_all.csv (every LMHC)")
    args = ap.parse_args(argv)

    print("Massachusetts LMHC (license type 35) from the public license API")
    print("Enumerating by last-name letter (union of a-z):")
    recs = enumerate_lmhc()
    print(f"\nTotal distinct LMHC records: {len(recs)}")

    rows = []
    for rec in recs:
        cat = classify(rec)
        if cat:
            rows.append(row_for(rec, cat))
    rows.sort(key=lambda r: (r["last_name"].lower(), r["first_name"].lower()))

    with SANCTIONED_CSV.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)

    from collections import Counter
    by_cat = Counter(r["category"] for r in rows)
    by_status = Counter(r["computed_status"] for r in rows)
    print(f"\nSanctioned LMHC written to {SANCTIONED_CSV}: {len(rows)}")
    for c in ("Disciplinary", "Surrender", "Non-disciplinary"):
        print(f"  {c:18} {by_cat.get(c, 0)}")
    print("  by current status:")
    for k, v in by_status.most_common():
        print(f"    {k:28} {v}")

    if args.all_lmhc:
        with ALL_CSV.open("w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=FIELDS)
            w.writeheader()
            for rec in sorted(recs, key=lambda x: ((x.get("lastName") or "").lower(),)):
                w.writerow(row_for(rec, classify(rec) or "none"))
        print(f"\nAll {len(recs)} LMHC written to {ALL_CSV}")

    print("\nNOTE: this is the INDEX (who, what action, when). Massachusetts does not")
    print("post the order documents; request them from the Bureau of Health Professions")
    print("Licensure (PublicRecordsAdmin@MassMail.State.MA.US) using the profile URLs above.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
