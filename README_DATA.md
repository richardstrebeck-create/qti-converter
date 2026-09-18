# LPC board order PDFs (data branch)

Branch `board-orders-data` holds the disciplinary-order PDFs fetched on
2026-09-18 by the four downloaders on branch
`claude/board-orders-scraping-progress-sm425l` (folder `board-orders\`).
It is an orphan branch with no code history. Download it as a zip:

    https://github.com/richardstrebeck-create/qti-converter/archive/refs/heads/board-orders-data.zip

## How to unpack into OneDrive

Each top-level state folder here maps 1:1 onto

    OneDrive - WCU\!Python Tools\LPC Board\Complaint Scraper\state_data\<State>\

Copy the contents of `Vermont\` into `state_data\Vermont\`, and so on. Inside
each state folder:

| Item | Goes to | Meaning |
|---|---|---|
| `*.pdf` at the top level | `state_data\<State>\` | orders classified as counselor (LPC / LCPC / LCMHC / LMHC), named exactly as the downloader names them |
| `review\` | `state_data\<State>\review\` | files the classifier could not settle; OCR these (Foxit), leave the OCR'd copies in `review\`, then run the downloader with `--reclassify` |
| `downloader\*.csv` | `state_data\<State>\downloader\` | the run outputs (manifest, logs, name lists). Copy them over the versions already in the downloader folder so `--reclassify` and skip-if-present work |
| `MISSING.csv` (Kansas, New Hampshire) | `state_data\<State>\` | counselor documents not recovered, with their official URL |
| `recovery_log.csv` (Kansas, New Hampshire) | `state_data\<State>\` | one row per counselor document: where each file came from |

The holding folders (`_all_allied_mental_health\`, `_all_behavioral_health\`)
are NOT included. They hold the dropped other-profession files and duplicates
of everything here; the downloaders recreate them on a re-run (files already
present are skipped, so re-running only fetches what is new).

## Counts

| State | Counselor PDFs | People | In `review\` | Dropped (not delivered) | Missing | Size |
|---|---|---|---|---|---|---|
| Vermont | 45 | 34 | 52 | 41 | 0 | 76 MB |
| Iowa | 106 | 68 | 228 | 469 | 0 | 131 MB |
| Kansas | 76 | 60 | 0 (see OCR note) | 503 (never fetched) | 2 | 45 MB |
| New Hampshire | 18 | 16 | 0 (see OCR note) | 21 (never fetched) | 0 | 15 MB |
| Oklahoma | 39 | 38 | 0 (no review step; see OCR note) | 31 (LMFT and LBP, never fetched) | 0 | 9 MB |
| Texas | 171 (172 orders; one file holds two) | 166 | 1 (nine unbookmarked packet pages, FY22 Q2) | 119 (LMFT, PSY, SW; never extracted) | 0 | 436 MB |
| Colorado | 774 | 612 | 0 (2 application-material files flagged review in manifest.csv, not fetched) | 124 (92 LPCC candidates, 30 other license types or malpractice reports, 2 review; never fetched) | 0 | 976 MB |

Total pushed: about 277 MB, plus 436 MB for Texas and 976 MB for Colorado (added later the same day). No file exceeded the 95 MB single-file limit,
so nothing was skipped for size.

Oklahoma was added to this branch by a separate session (39 LPC orders from
the OBBHL Thentia register, 2010-04 to 2026-08, plus its manifest and
download log); see the Oklahoma section at the end.

## Vermont (138 PDFs in the OPR allied mental health folder)

Run: `build_vermont_name_list.py` (92 monthly reports parsed, 37 LCMHC
actions, 36 files matched as counselor, 35 as drop, 67 unmatched), then
`download_vermont_orders.py` (all 138 downloaded, 0 failures).

Classification (manifest.csv `category`):

- counselor 45: 36 from the monthly-report name list, 9 from the PDF text
  (unmatched files that turned out to have a text layer).
- drop 41: 35 from the name list, 6 from the PDF text (non-licensed
  psychotherapist, LMFT, applicant).
- review 52: 51 scans with no text layer, plus one readable file
  (`gelineau-yvonne-docket-m20164.pdf`) that is a Board of Nursing order
  misfiled in the allied mental health folder; the script left it in
  review without copying it, so it was copied into `review\` by hand so
  that every review row has a file. Expect it to drop after OCR/reclassify.

Delivered run outputs: `manifest.csv`, `name_match.csv`,
`lcmhc_actions.csv`, `download_log.csv`. Not delivered:
`monthly_actions_all.csv` (unchanged from the working branch) and the
`monthly_reports\` cache (the script re-downloads only missing months).

Still needs OCR: everything in `Vermont\review\` (52 files, mostly pre-2019
dockets and ten 2019+ names that appear in no monthly report).

## Iowa (803 files in the documents.iowa.gov discipline index)

Run: `download_iowa_orders.py` full run (index 803 files, all 803
downloaded, 0 failures, classified by reading each PDF).

- counselor 106 (68 people): 47 from the caption, 59 from the body text
  only (note "profession from body text only"; three of those found the
  licence sentence after page 3). Spot-checked three body-text files: all
  three name an Iowa mental health counselor licence.
- drop 469: social work 398, psychology 59, marriage and family therapy 8,
  applicant 4. Not delivered.
- review 228: 159 scans with no text layer, 13 with an unreadable Type3
  text layer, 45 readable but the profession was not found in the pages
  read, 9 header/body contradictions (6 "social work" caption with a
  counselor body, 2 with an MFT body, 1 MFT caption with a counselor
  body), 2 Word documents (`.docx`, not PDFs). The script copies only the
  scans and unreadable files into `review\` (172); the other 56 were
  copied in by hand so the folder matches the manifest.

Still needs OCR: the 172 scans/unreadable files. The 45 "profession not
found" files and the 9 contradictions need a human read, not OCR.
Delivered run outputs: `actions.csv`, `manifest.csv`, `download_log.csv`.

## Kansas (78 counselor documents in manifest.csv)

The live site (`www.ksbsrb.ks.gov`) still answers HTTP 403 to this cloud
environment, with browser headers. The 78 counselor PDFs were therefore
fetched from the Wayback Machine (`web.archive.org/web/<timestamp>id_/<url>`,
raw bytes, each verified to start with `%PDF`). 76 recovered, 2 missing
(listed in `Kansas\MISSING.csv` with the official URL):

- `Fedosyuk, Sindhuja 26-PC-0031 (2).pdf` (document 5882, no date on the
  site), no capture in the archive;
- `Smithmier, Elise 24-LC-0081.pdf` (document 5822), no capture, with or
  without the trailing ticks segment.

A "Save Page Now" request for both returned an error from archive.org.
Download those two by hand from the official URL on a home machine (the
block affects scripts, not browsers, as far as we know).

The 503 dropped (other-profession) and 2 review (unlicensed, code NL)
documents were never fetched, as the downloader is designed.

OCR note: 47 of the 76 files have little or no extractable text in their
first two pages and will need OCR before `make_text_sidecars.py` reads
them. No `review\` folder exists because Kansas classifies from the index,
not from the PDF.

## New Hampshire (18 counselor documents in manifest.csv)

Same block (`www.oplc.nh.gov` answers 403) and the same Wayback route. All
18 recovered (captures from 2024-07 to 2025-07); `MISSING.csv` is empty
apart from its header. The manifest is from the 2025-06 archived pages, so
actions after mid-2025 are not included.

OCR note: 13 of the 18 files have little or no extractable text in their
first two pages, so these are scans despite being recent.

## What was done to the branch and what was not

- Filenames are exactly what the scripts produce (Windows-safe).
- Committed in batches of at most 200 files, one state per push.
- No git LFS. No PDFs were added to the working branch.
- Each PDF was checked to start with `%PDF-` before commit.

## Oklahoma (39 counselor documents in manifest.csv)

Source: Oklahoma State Board of Behavioral Health Licensure public register
(Thentia), https://obbhl.us.thentiacloud.net/webs/obbhl/register/ (tick
"Disciplined"). Downloaded 2026-09-18 with
`board-orders/oklahoma_downloader/download_oklahoma_orders.py` from the
working branch.

- `Oklahoma/` holds 39 order PDFs (9.3 MB), one per Public Notice that had
  an attachment, for Licensed Professional Counselors only. Files are named
  "Lastname, Firstname <license number> <effective date>.pdf"; four people
  with no license number on the register are named with the case number or
  the name and date alone.
- `Oklahoma/downloader/manifest.csv` lists every disciplined licensee the
  register returned (186: 144 LPC, 11 LPC Candidate, 23 LMFT, 8 LBP) with
  one row per Public Notice for the LPCs and candidates (161 LPC notices,
  1989 to 2026-08-07; 122 of them are index-only lines with no document).
  `download_log.csv` records the 39 downloads (0 failures).
- Date range of the PDFs: 2010-04-08 to 2026-08-07 (8 before 2020, the
  rest 2021 on). LPC Candidates have notices but no documents; LMFT and LBP
  were not fetched.
- Text layer: 7 of 39 are text-native, 32 are image scans. Run Foxit OCR
  on the folder before make_text_sidecars.py.

## Texas (171 counselor documents in manifest.csv)

Source: the Texas Behavioral Health Executive Council's quarterly "Public
Meeting Materials" packets, linked from
https://bhec.texas.gov/tbhec/important-dates/past-council-meeting-dates/ .
Each packet's item "Agreed Orders and Dismissals for the fiscal-quarter" is
the signed agreed orders themselves, sorted by profession. Downloaded
2026-09-18 with `board-orders/texas_downloader/download_texas_orders.py`
from the working branch (17 packets, October 2021 to June 2026; the packets
themselves, about 950 MB, are not kept).

- `Texas/` holds 171 order PDFs (436 MB; the largest is 7.3 MB) for
  Licensed Professional Counselors and LPC Associates, named
  "Lastname, Firstname <fiscal quarter> <Council meeting date>.pdf", for
  example "Joslin, Gene FY25Q4 2025-10-14.pdf". The quarter is the one the
  order was reported in (Texas FY runs September to August); the order's own
  signature date is inside the scan. Orders run from FY21 Q4 (June to
  August 2021) to FY26 Q3 (March to May 2026), 3 to 26 per quarter.
  "Pruitt, Jennifer + Ripstra, Leeann FY23Q4 2023-10-24.pdf" holds two
  orders because the packet's bookmark for the second had no page number;
  split it by hand after OCR.
- `Texas/review/` holds one file: the nine unbookmarked pages of the May
  2022 packet (FY22 Q2), which start with an LPC order (Cynthia Kay) and
  continue with MFT and PSY orders. Keep the "PROFESSIONAL COUNSELORS"
  pages as "Kay, Cynthia FY22Q2 2022-05-18.pdf" and drop the rest.
- `Texas/downloader/manifest.csv` has one row per order found in the
  packets (171 counselor, 119 other professions not extracted, 1 review)
  with the packet URL, the zip entry or page range it came from, and, for
  the 105 orders whose name matched BHEC's current-licensee list, the
  license number and rank (3 are LPC Associates). `download_log.csv`
  records the 172 files written (0 failures).
- Text layer: 10 of 171 are text-native, 161 are image scans. Run Foxit
  OCR on the folder before make_text_sidecars.py.
- Not covered: orders before June 2021, default and SOAH orders (only
  agreed orders are in the packets), and anything after the June 2026
  packet. The BHEC licensee lookup (datamart) is reCAPTCHA-protected and
  could not be used.

## Colorado (774 counselor documents in manifest.csv)

Source: two DORA Division of Professions and Occupations systems. The
"Licensee/Discipline List" roster generator
(https://apps2.colorado.gov/dora/licensing/Lookup/GenerateRoster.aspx) is
the index: one CSV per license type with a row per public action (case
number, action label, effective and end dates). The "DPO Public Documents
System" (https://www.dora.state.co.us/pls/real/DDMS_Search_GUI.DPO_Search_Form)
is the document store: one search with State Board = Professional
Counselors lists every document filed under the board with a direct PDF
link. Downloaded 2026-09-18 with
`board-orders/colorado_downloader/download_colorado_orders.py` from the
working branch (898 documents listed, 774 counselor documents fetched).

- `Colorado/` holds 774 order PDFs (976 MB; the largest is 19.1 MB)
  for Licensed Professional Counselors and Provisional LPCs, named
  "Lastname, Firstname <license> <effective date>.pdf" in DORA's printed
  license form, for example "Kosley, Lisa Marie LPC.0011765 2026-05-11.pdf".
  A second document for the same person on the same date carries " (2)".
  15 files have no license number in DDMS and use the DDMS barcode instead;
  11 have no effective date and end in "undated". Effective dates run from
  1992-08-30 to 2026-06-17 (about 4 to 30 a year to 2015, 50 to 77 a year
  since 2016).
- `Colorado/downloader/manifest.csv` has one row per DDMS document (774
  counselor, 92 LPCC candidate not fetched, 30 other license types or
  malpractice-insurance reports not fetched, 2 application-material files
  flagged review and not fetched) plus 19 "index only, no document" rows
  for roster actions (12 people, mostly 1990s) with nothing in DDMS. 672
  of the 774 counselor rows carry the roster's case number and action
  label (matched on license number and effective date); the other 102
  have the roster name and status only. `download_log.csv` records the
  774 files written (0 failures).
- Text layer: 196 of 774 are text-native, 578 are image scans (everything
  through 2018, most of 2019, half of 2020, 31 later ones). Run Foxit OCR on the image-only
  files (the `--text-check` list) before make_text_sidecars.py.
- Not covered: the 19 roster actions with no DDMS document (Colorado Open
  Records Act request to DORA), the 92 LPC Candidate documents (re-run with
  `--include-candidates`), and anything filed after 2026-09-18 (re-run;
  only new files are fetched).
