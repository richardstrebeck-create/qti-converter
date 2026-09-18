# Colorado verification (2026-09-18)

Companion to `STATE_SURVEY_2026-09-18.md`, which rated Colorado Tier 2
MODERATE from search-engine snippets ("roster export, then per-licensee
ASP.NET lookup"). This pass loaded the live sites from a cloud session with
open network access, paused at least 1.5 seconds between requests, pulled
three sample PDFs (deleted afterwards), then built and ran
`colorado_downloader\`. The survey's two-step picture was right about the
index and wrong about where the documents live: the per-licensee lookup is
behind a CAPTCHA, but DORA's separate "Public Documents System" lists every
counselor-board document in one query with plain download links.

## Summary

| Route | URL | What is really there | Result |
|---|---|---|---|
| Board page | https://dpo.colorado.gov/ProfessionalCounselor | Program info, public notices (Counseling Compact rules), meeting minutes on Google Drive, links to the lookup and roster tools | No actions list, no order links |
| Roster generator | https://apps2.colorado.gov/dora/licensing/Lookup/GenerateRoster.aspx | ASP.NET form, CSV per license type with one extra row per public action (case number, action, effective and end dates) | Works without a browser; the INDEX |
| Per-licensee lookup | https://apps.colorado.gov/dora/licensing/Lookup/LicenseLookup.aspx | Amazon WAF "Human Verification" page on apps.colorado.gov; CAPTCHA box on the apps2 form; per-credential detail page reachable on apps2 but lists barcodes only | Not usable for documents; not needed |
| Open data | https://data.colorado.gov/Regulations/Professional-and-Occupational-Licenses-in-Colorado/7s5z-vewr | Same rows as the roster, API-queryable, plus a per-credential detail link; no document links | Index only (alternative to the roster) |
| DPO Public Documents System (DDMS) | https://www.dora.state.co.us/pls/real/DDMS_Search_GUI.DPO_Search_Form | One search by State Board returns every public document with a direct PDF link | Works; the DOCUMENT source |
| Other official routes | Meeting minutes, Office of Administrative Courts, Colorado Open Records Act | Minutes are 2026 only and carry no orders; OAC posts workers' compensation decisions only; CORA needed for the 19 roster actions with no document | Fallback only |

Rating: **EASY** (moved up from Tier 2 MODERATE). One roster download for
the index, one DDMS query for the document list, then plain PDF downloads.
The cost is OCR: the documents before about 2019 are image scans, and the
full set is about 1.5 GB.

## 1. Board page and enforcement pages

`https://dpo.colorado.gov/ProfessionalCounselor` loads (HTTP 200, Drupal).
Its tabs are Program Information, Public Notice Information (Counseling
Compact rule comments), Meeting Minutes (three 2026 minutes as Google
Drive links, no order documents) and Continuing Professional Competency.
The right-hand column links "Lookup a License/Licensee" and "Download a
Licensee/Discipline List" (both on apps.colorado.gov) and "File a
Complaint". The page text has no "Enforcement", "Board Actions" or
"Disciplinary Actions" section and no newsletter. Guessed addresses
(`/ProfessionalCounselor/BoardActions`, `/ProfessionalCounselor/Enforcement`,
`/ProfessionalCounselor/Discipline`, `/BoardActions`, `/Enforcement`) are all
404. Could not verify any DPO board-actions page for this board; none was
found.

## 2. Roster generator (the index)

`https://apps2.colorado.gov/dora/licensing/lookup/generateroster.aspx`
(Tyler Technologies ASP.NET, 131 KB form). 186 checkboxes grouped by board;
the counselor ones are:

| Checkbox | Roster |
|---|---|
| `ctl00$MainContentPlaceHolder$ckbRoster161` | LPC - Licensed Professional Counselor - All Statuses |
| `ctl00$MainContentPlaceHolder$ckbRoster162` | LPCC - Licensed Professional Counselor Candidate - All Statuses |
| `ctl00$MainContentPlaceHolder$ckbRoster163` | LPP - Provisional LPC - All Statuses |

(Also present: NLC Unlicensed Psychotherapist, ACD/ACA/ACC/ADDC addiction
counselors, MFT/MFP/MFTC, PSY/PSP/PSYC, CSW/LSW/SWC/SWP.) The downloader
finds the boxes by their label text rather than by number.

How the download works, verified with `requests` only:

1. GET the form; POST it back with the hidden ASP.NET fields, the checkbox
   set to `on` and `btnRosterContinue=Continue`. The reply redirects to
   `Lookup/DownloadRoster.aspx`, which lists the generated roster with a
   Download button carrying `RosterIdnt="3712554"` and a format radio
   (Excel, Comma, Tab).
2. The button's JavaScript (`Lookup.js`, `OpenFileDownloadWindow`) just
   opens `Lookup/FileDownload.aspx?Idnt=<id>&Type=Comma`. A GET on that URL
   in the same session returns `text/csv`, 3.4 MB, filename
   `LPC_-_Licensed_Professional_Counselor_-_All_Statuses.csv`.
   (Posting the Download button itself only re-renders the listing page.)

Columns: Last Name, First Name, Middle Name, Suffix, Entity Name, Formatted
Name, Attention, Address Line 1 and 2, City, State, County, Mail Zip Code,
Zip + 4, License Type, Sub Category, License Number, License First Issue
Date, License Last Renewed Date, License Expiration Date, License Status
Description, Specialty, Title, Degree(s), Case Number, Program Action,
Discipline Effective Date, Discipline Complete Date. Licensees with several
actions repeat with one row per case.

LPC roster on 2026-09-18:

| Measure | Value |
|---|---|
| Rows | 20,451 |
| Unique license numbers | 20,098 |
| Statuses | Active 14,849; Expired 4,909; Voluntary Surrender 228; Active - Telehealth ONLY 215; Inactive 94; Revoked 62; Active - With Conditions 44; Surrendered 23; Suspended 22; Active - Restricted 5 |
| Rows with a public action | 910 (557 licensees, 741 case numbers) |
| Action effective dates | 1992-08-30 to 2026-06-17 (about 5 to 30 a year to 2015, 36 to 85 a year since 2016) |
| Action types | CLS Stipulation 292; CLS Letter of Admonition 216; CLS Combined w/other case for action 125; CLS Voluntary Surrender/Relinquishment 92; ID Hearing Formal Complaint/Charges Filed with OAC 45; ITRM Summary Suspension 31; ITRM Stipulation in Abeyance 22; CLS Revocation 21; CLS Cease & Desist Order 20; ITRM Cessation of Practice 17; CLS Final Agency Order 8; CLS Suspension 6; then Stipulation 4, Formal Complaint-Charges with OAC 3, CLS Application Denied 2, CLS Injunction 2, and one each of Voluntary Surrender, ITRM Suspension, CLS Suspension Terminated, Letter of Admonition |

LPP (provisional): 637 rows, 633 licensees, 5 with an action (9 rows).
LPCC (candidate): 12,151 rows, 12,123 licensees, 89 with an action (117
rows). The roster has no document links and no barcode numbers.

## 3. Per-licensee lookup and the open-data feed

**apps.colorado.gov is CAPTCHA-walled.** Every request to
`https://apps.colorado.gov/dora/licensing/Lookup/LicenseLookup.aspx` (and to
any other path on that host, including the roster page the board links to)
returns HTTP 405 with a 2 KB "Human Verification" page from Amazon WAF
(`challenge.js` and `captcha.js` from awswaf.com). Nothing on that host is
reachable by a script.

**apps2.colorado.gov serves the same application without the WAF.** The
lookup form loads there (HTTP 200, 85 KB): board list
(`lbMultipleCredentialTypePrefix`, Professional Counselors = 184), prefix
list (`ddCredPrefix`: LPC, LPCC, MSLPC, MSLPCC), license number, name,
city, state, zip, and a CAPTCHA box (`CaptchaSecurity1$txtCAPTCHA`, a
"FormShield" image CAPTCHA with an audio option). The page also states
"This Online License Verification site is not designed for web crawling
programs". The search was therefore not scripted. The results appear in a
modal loaded by JavaScript (`ShowLookupDetail(credentialID, contactID)`),
so even a solved CAPTCHA would need a second step.

**Direct detail page.** Colorado's open-data dataset (below) publishes, per
credential, `linkToVerifyLicense` =
`https://www.colorado.gov/dora/licensing/Lookup/PrintLicenseDetails.aspx?cred=<credential id>&contact=<contact id>`.
On www.colorado.gov that redirects into the WAF; the same path on
apps2.colorado.gov opens without a CAPTCHA (HTTP 200, 13 KB, "Print Lookup
Details"). It shows the licensee, the credential (license number in DORA's
printed form, e.g. `LPC.0000224`), a Board/Program Actions table (case
number, public action, resolution, effective and completed dates) and an
"Online Documents" table with Barcode ID Number and Document Type (for
example 209006, "HPPP-CO PUBLIC DISCIPLINARY ACTION"). There is no file
link: the page says to take the barcode to the "DPO Public Documents
System" and search there. So the per-licensee route is: roster -> open data
for the credential id -> detail page for barcodes -> DDMS for the file.
Four steps and about 600 requests, all of which DDMS makes unnecessary
(section 4). Verified on one licensee only; not built.

**Open data.** `https://data.colorado.gov/resource/7s5z-vewr.json` (Socrata,
"Professional and Occupational Licenses in Colorado", all boards, updated
2026-09-16) answers SoQL queries without a key. Columns: lastname,
firstname, middlename, suffix, entityname, city, state, mailzipcode,
licensetype, subcategory, licensenumber, licensefirstissuedate,
licenselastreneweddate, licenseexpirationdate, licensestatusdescription,
specialty, title, degrees, casenumber, programaction,
disciplineeffectivedate, disciplinecompletedate, linktoverifylicense,
linktoviewhealthcareprofile. Rows with a case number on 2026-09-18: LPC
955, LPCC 122, LPP 9, NLC 847 (the count is higher than the roster's 910
because the dataset repeats rows per credential). It is the roster by
another door, useful for the credential id, with no document links. No
separate discipline or documents dataset exists on the portal (catalog
search for "discipline license" returns nothing relevant).

## 4. DPO Public Documents System (DDMS): the documents

`https://www.dora.state.co.us/pls/real/DDMS_Search_GUI.DPO_Search_Form`
(Oracle PL/SQL gateway; HTTPS only, plain HTTP times out). The form takes
last, first and middle name, business name, State Board (45 boards,
"PROFESSIONAL COUNSELORS" among them), License Type (368 values, including
"LICENSED PROFESSIONAL COUNSELOR", "LICENSED PROFESSIONAL COUNSELOR
CANDIDATE", "PROVISIONAL LICENSED PROFESSIONAL COUNSELOR"), license number
(numeric part, prefix match: "224" also returns 2242 and 2246), barcode and
effective date. The form posts to
`!DDMS_Search_GUI.Process_DPO_Search_Form`; the leading `!` matters (it is
Oracle's flexible-parameter mode; without it the site re-displays the empty
form, which is what the first three attempts got).

Three searches, all HTTP 200:

| Search | Result |
|---|---|
| barcode 209006 | 1 row: HERRERA-GILLESPIE, LPC 224, 04/09/1997, HPPP-CO PUBLIC DISCIPLINARY ACTION, link `DDMS_documents_api.download?p_file=F270087831/209006_Page7_92314_22547.pdf` |
| board Professional Counselors, license number 224 | 3 rows (prefix match) |
| board Professional Counselors, nothing else | **898 rows on one page** ("Query returned 898 document records"), 306 KB of HTML |

The result table has ten cells per row: Barcode ID, Last Name, First
Name, Middle Name, Business Name, State Board, License Type, License
Number, Effective Date, Document Type, with the barcode cell linking the
file. Breakdown of the 898:

| Field | Values |
|---|---|
| License type | LICENSED PROFESSIONAL COUNSELOR 772; LPC CANDIDATE 92; UNLICENSED PRACTICE 16; PROVISIONAL LPC 6; blank 4; LICENSED ADDICTION COUNSELOR 4; REGISTERED PSYCHOTHERAPIST 2; LCSW 1; CAC I 1 |
| Document type | HPPP-CO PUBLIC DISCIPLINARY ACTION 572; BOARD/PROGRAM ACTION DOCUMENTS 264; HPPP-CO RESTRICTIONS OR SUSPENSIONS 50; HPPP-REFUSAL OF MALPRACTICE INSURANCE 6; APPLICATION / SUPPORTING DOCUMENTS 2; blank 2; one each of two "HPPP-OS" variants |
| Effective dates | 1992-08-30 to 2026-06-17; 11 rows blank. About 4 to 30 a year to 2015, then 59 (2016), 67, 77, 61, 54, 34, 49, 52, 51, 53 (2025), 22 (2026 to June) |
| Unique license numbers | 688 (37 rows have none); 895 unique barcodes; 697 distinct names |
| File names | all `.pdf`; older ones `<barcode>_Page<n>_<id>_<id>.pdf` (scanned batches), newer ones `2026-5-11_Kosley_FAO_Public.pdf`, `2024-05-16_Tallant_LOA_Public.pdf` (FAO = final agency order, LOA = letter of admonition) |

Cross-check against the roster: 540 of the 557 LPCs with a roster action
have at least one DDMS document; 54 DDMS license numbers are not in the
roster's action set (malpractice-insurance reports, licensees whose
action has since aged off the roster, or number typos in DDMS).

**Downloads.** `https://www.dora.state.co.us/pls/real/DDMS_documents_api.download?p_file=...`
answers a plain GET from a fresh session with no cookies and no referer:
`application/pdf` with a `Content-Disposition` filename. Three samples:

| Sample | Size | Pages | PyMuPDF text |
|---|---|---|---|
| 12516_Page6_79094_19620.pdf (LPC 1405, 2005-10-05) | 2.8 MB | 6 | 0 characters (image scan) |
| Stueve, Randall disciplinary action.pdf (LPC 18656, 2019-10-15) | 3.2 MB | 6 | 0 characters (image scan) |
| 2026-5-11_Kosley_FAO_Public.pdf (LPC 11765, 2026-05-11) | 242 KB | 11 | 13,043 characters, text-native: "BEFORE THE STATE BOARD OF LICENSED PROFESSIONAL COUNSELOR EXAMINERS ... Case No. 2025-7951 FINAL BOARD ORDER" |

A size probe of twelve random files (Content-Length only) averaged 2.3 MB,
from 14 KB to 11.9 MB (a 1999 scan), so the full counselor set is on the
order of 1.5 to 2 GB. No file approaches the 95 MB limit.

**Blocking.** None on DDMS or apps2: no 403, no CAPTCHA, no session. The
board's own links point at the WAF-protected host, so a person following
the board page in a browser sees a CAPTCHA that a script never has to
solve. Be polite anyway: the whole board comes back in one query, so
there is no reason to hit DDMS more than once per run.

## 5. Other official routes

- **Meeting minutes**: three 2026 PDFs on Google Drive linked from the
  board page. Not fetched; minutes name disciplinary matters by case
  number at most and are not the orders.
- **Office of Administrative Courts** (`https://oac.colorado.gov/`): the
  only decisions library is workers' compensation. Counselor cases heard
  by an ALJ end in a Final Agency Order that DDMS files under the board
  (the "FAO" files above), so the OAC site adds nothing.
- **Colorado Open Records Act**: needed only for the 19 roster action rows
  (12 licensees, mostly 1990s) with nothing in DDMS, and for any case file
  beyond the public order. Contact dora_dpo_licensing@state.co.us.

## 6. Downloader run (Phase 2)

`colorado_downloader\download_colorado_orders.py` (pass 1 rosters, pass 2
DDMS board query joined to the rosters on license number and effective
date, pass 3 downloads). `--list-only` first, then the full run, both on
2026-09-18.

Manifest (933 rows):

| Category | Documents | Licensees | Index-only rows | Note |
|---|---|---|---|---|
| counselor | 774 | 612 | 19 | LPC 764, provisional LPC 6, 4 typed blank in DDMS but on the LPC roster |
| candidate | 92 | 83 | 16 | LPCC; downloaded only with `--include-candidates` |
| review | 2 | 2 | 0 | "APPLICATION / SUPPORTING DOCUMENTS" |
| drop | 30 | 30 | 0 | unlicensed practice 16, malpractice-insurance reports 6, LAC 4, registered psychotherapist 2, LCSW 1, CAC I 1 |

Of the 774 counselor documents, 672 matched a roster action on license
number and date and carry its case number and action label (CLS
Stipulation 235, CLS Letter of Admonition 204, CLS Voluntary
Surrender/Relinquishment 54, CLS Revocation 25, ITRM Summary Suspension
15, ITRM Cessation of Practice 13, ...); 102 carry the roster name and
status but no case number (DDMS date matches no roster action, or the
roster shows no action). 15 counselor documents have no license number in
DDMS and are named with the barcode instead; 11 have no effective date and
are named "undated". 28 files carry a " (2)" suffix (same person, same date).

Full run: RUN_RESULTS_PLACEHOLDER

## 7. What the user must still do

1. Unpack `Colorado\` from the `board-orders-data` zip into
   `state_data\Colorado\` (PDFs at the top level, `downloader\manifest.csv`
   and `download_log.csv` over the local copies).
2. Foxit-OCR the image-only files (the `--text-check` list; roughly
   everything before 2019).
3. `py make_text_sidecars.py --states Colorado`, register "Colorado" in
   `PDF_STATES` in `board_order_extractor.py`, run the extractor.
4. Decide on the 2 review files (application material) and on the 19
   index-only roster actions (12 people) (CORA request or leave as index rows).
5. Optionally `--include-candidates` for the 92 LPCC documents.
