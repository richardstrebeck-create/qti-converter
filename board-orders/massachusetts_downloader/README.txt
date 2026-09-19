MASSACHUSETTS LMHC SANCTION-LIST BUILDER

Massachusetts is an INDEX-only state for this project. It does NOT post board
order documents online. Its "Check a Health License" site
(https://checkahealthlicense.mass.gov/) shows, per licensee, the license
status and a "Compliance Actions & Fines" summary: the action type
(Revocation, Suspension, Probation, Surrender) with start and end dates, but
not the order itself. To get the actual orders you must file a Public Records
Act request with the Bureau of Health Professions Licensure
(PublicRecordsAdmin@MassMail.State.MA.US), referencing the license numbers or
profile URLs in the list this tool builds.

WHAT THE TOOL DOES

build_ma_lmhc_list.py reads the site's public REST API and writes the list of
sanctioned Licensed Mental Health Counselors (LMHC):

  ma_lmhc_sanctioned.csv   one row per sanctioned LMHC: license number, name,
                           city, current status, category (Disciplinary /
                           Surrender / Non-disciplinary), an action summary,
                           the revoked / suspended / surrendered dates, and
                           the profile URL.

The API (verified 2026-09-19, no CAPTCHA, no login):
  config   https://checkahealthlicense.mass.gov/environments/environment.json
           -> https://healthprofessionlicensing-api.mass.gov/api-public
  search   POST /api-public/search with licenseMetaId 35 (Licensed Mental
           Health Counselor License) and searchType BY_LICENSEE_NAME. Each row
           carries computedStatus and the action dates.

A single search caps at 10,000 rows and Massachusetts has 16,192 LMHCs, so the
tool searches each last-name letter a-z (the match is "contains", so the union
covers everyone) and de-duplicates by id.

HOW SANCTIONED IS DECIDED (from the BHPL status definitions)

  Disciplinary : Revoked; Suspension and "Suspension, Expired"; "Stayed
                 Suspension"; Probation and "Probation, Expired"; and any
                 record carrying a past revoked or suspended date even if the
                 license is now Current, Expired or Deceased.
  Surrender    : "Surrendered" or a surrender date with no suspension or
                 revocation. Surrender can be disciplinary (to resolve a case)
                 or a voluntary agreement not to practice; the status does not
                 say which, so these are listed and flagged for you to verify.
  Non-disciplinary : "Non-Disciplinary Restriction" and "Non-Disciplinary
                 Condition" are listed but are NOT sanctions.
  Clean statuses (Current, Expired, Deceased, Retired) with no action are
  dropped.

HOW TO RUN

1. Install once:  py -m pip install requests
2. Double-click Run_MA_LMHC_List.cmd (or:  py build_ma_lmhc_list.py).
   It makes 26 requests (about a minute) and writes ma_lmhc_sanctioned.csv.
   Add --all-lmhc to also write ma_lmhc_all.csv (every LMHC, for cross-checks).

VERIFIED 2026-09-19 (live)
  16,192 LMHC total. 99 with a sanction signal: 77 Disciplinary, 17 Surrender,
  5 Non-disciplinary. By current status: Surrendered 48, Revoked 18, Current 9
  (past action, now active), Suspension Expired 7, Probation 5, Non-Disciplinary
  Restriction 3, Probation Expired 2, Non-Disciplinary Condition 2, Expired 2,
  Deceased 2, Stayed Suspension 1. Spot-checked against the site: LMHC10203
  (Michele L Davis, Wilmington) shows Probation with Revoked 2025-05-26 and
  Suspended 2026-04-08 to 2026-05-16, matching the profile page.

WHAT THIS DOES NOT COVER
  The order documents (Consent Agreement, Final Decision and Order). Not posted
  online anywhere; Public Records Act request only. The Licensed Supervised
  Mental Health Counselor (type 255, the pre-licensure tier) and the other
  Allied Mental Health license types (LMFT 34, rehabilitation counselor 36,
  educational psychologist 33, behavior analysts 30/32) are out of scope; change
  LMHC_TYPE_ID in the script to collect one of those.

Official sources:
https://checkahealthlicense.mass.gov/search                                      (license lookup, filter by status)
https://www.mass.gov/info-details/bureau-of-health-professions-licensure-license-status-definitions  (status definitions)
https://www.mass.gov/how-to/request-public-records-from-the-bureau-of-health-professions-licensure    (records request)
