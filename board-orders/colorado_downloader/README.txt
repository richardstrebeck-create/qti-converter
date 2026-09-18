COLORADO PROFESSIONAL COUNSELOR BOARD ORDER DOWNLOADER

Collects the public disciplinary documents for Licensed Professional
Counselors (LPC, plus the handful of Provisional LPCs) from the Colorado
Division of Professions and Occupations (DORA DPO), State Board of Licensed
Professional Counselor Examiners. Documents filed under the same board for
LPC Candidates (LPCC, people still under supervision) are listed separately
and downloaded only on request. Documents for other license types that DORA
files under the counselor board (unlicensed practice cease-and-desist
orders, a few addiction counselors, registered psychotherapists, one social
worker) and the "refusal of malpractice insurance" reports are deliberately
left out; each dropped document and the reason is still recorded in
manifest.csv.

Built to mirror the Oklahoma, Texas, Kansas and Maryland downloaders. Same
flags, same manifest and log layout, same filename convention.

WHERE THE DOCUMENTS COME FROM

DORA keeps two public systems that between them give the full picture:

1. The "Licensee/Discipline List" roster generator
       https://apps2.colorado.gov/dora/licensing/Lookup/GenerateRoster.aspx
   Tick a license type, press Continue, download a CSV of every licensee
   of that type. Licensees with a public action get one extra row per
   action with Case Number, Program Action (for example "CLS Stipulation",
   "CLS Letter of Admonition", "CLS Revocation"), Discipline Effective
   Date and Discipline Complete Date. This is the INDEX. It has no links.

2. The "DPO Public Documents System" (DDMS)
       https://www.dora.state.co.us/pls/real/DDMS_Search_GUI.DPO_Search_Form
   Pick State Board = Professional Counselors, leave everything else blank,
   press Search: one page lists every public document filed under the
   board (898 on 2026-09-18) with barcode, name, license type, license
   number, effective date, document type and a direct PDF link. That is
   what the script downloads. The links are plain files: no login, no
   CAPTCHA, no session.

The per-licensee "Verify a License" lookup is NOT used. The address the
board page links to (apps.colorado.gov) answers every request with an
Amazon WAF "Human Verification" CAPTCHA, and the search form on the working
host (apps2.colorado.gov) has its own CAPTCHA box. The per-credential detail
page does open on apps2 without a CAPTCHA, but its "Online Documents" section
only lists barcode numbers and tells the reader to search DDMS for the file,
so it adds nothing the DDMS query does not already give.

HOW TO RUN IT

1. Install once:  py -m pip install requests beautifulsoup4
   (and  py -m pip install pymupdf  if you want --text-check).
2. Double-click Run_Colorado_Downloader.cmd.
3. Leave the window open while it works. The 774 counselor documents add
   up to about 1 GB (the older ones are big scans), so the first run
   takes 60 to 90 minutes depending on the connection. Later runs only
   fetch what is new.

What happens:

- pass 1 asks the roster generator for the LPC, LPP (provisional) and
  LPCC (candidate) lists (three requests, 1.5 s apart) and saves them under
  downloader\rosters\. It then reads each one: who holds the license, their
  status, and every public action with its case number and dates;
- pass 2 asks DDMS for every document under the counselor board (one
  request) and sorts each document by the license type printed on it:
  LPC and Provisional LPC = counselor, LPC Candidate = candidate,
  anything else = drop. Malpractice-insurance refusal reports are dropped
  whatever the license type, and "Application / Supporting Documents" go
  to review. Each document is then matched to the roster by license number
  and effective date so its manifest row also carries the case number, the
  action label and the end date from the roster;
- manifest.csv gets one row per document (name, license number, license
  type, license status, case number, action, effective and end dates,
  document type, barcode, DDMS file name, URL, target filename, category,
  note, flags) plus one "index only, no document" row for every roster
  action whose licensee has nothing in DDMS at all;
- pass 3 downloads every counselor document (1.5 s pause, three retries,
  checked to be a real PDF) into the Colorado state folder one level up,
  named
      "Kosley, Lisa Marie LPC.0011765 2026-05-11.pdf"
  (DORA's printed license format, then the document's effective date). A
  second document for the same person on the same date becomes
  "... 2026-05-11 (2).pdf". Documents with no effective date in DDMS are
  named "... undated.pdf"; documents with no license number use the DDMS
  barcode instead;
- files already present are skipped, so the script can be re-run safely;
- every outcome is written to download_log.csv.

To check the list without downloading any orders:
    py download_colorado_orders.py --list-only

To also download the LPC Candidate documents (92 on 2026-09-18):
    py download_colorado_orders.py --include-candidates

To reuse the rosters already saved under downloader\rosters\ instead of
asking DORA for them again:
    py download_colorado_orders.py --skip-roster

To count how many downloaded PDFs already have a text layer (needs PyMuPDF):
    py download_colorado_orders.py --text-check

VERIFIED 2026-09-18 (live, from a cloud session; first full run the same day)
    Routes checked and rejected: the board's page
    (dpo.colorado.gov/ProfessionalCounselor) has no disciplinary-actions
    list, no board-actions page and no newsletter; its only enforcement
    content is meeting minutes on Google Drive (2026 only, no order links).
    Guessed pages such as /ProfessionalCounselor/BoardActions are 404. The
    Office of Administrative Courts site publishes decisions for workers'
    compensation only. Colorado's open-data portal (data.colorado.gov,
    "Professional and Occupational Licenses in Colorado", 7s5z-vewr) has
    the same rows as the roster with the same case number and action
    columns plus a per-credential detail link, but no document links.

    What the first full run found: rosters of 20,098 LPCs (557 with a
    public action, 910 action rows), 633 provisional LPCs (5 with an
    action) and 12,123 LPC Candidates (89 with an action, 117 action rows).
    DDMS listed 898 documents under the counselor board: 774 counselor
    (LPC and provisional LPC, four of them typed blank in DDMS but on the LPC
    roster), 92 candidate, 2 review (application material), 30 drop.
    Effective dates 1992-08-30 to 2026-06-17; about 20 documents a year
    before 2015 and 50 to 77 a year since 2016. Document types: "HPPP-CO
    PUBLIC DISCIPLINARY ACTION" (the older scans, through about 2019),
    "BOARD/PROGRAM ACTION DOCUMENTS" (the newer files) and "HPPP-CO
    RESTRICTIONS OR SUSPENSIONS". 540 of the 557 roster LPCs with an
    action have at least one document; 19 roster actions (12 people) belong
    to licensees with nothing in DDMS (index-only rows). 672 of the 774
    counselor documents matched a roster action on license number and
    effective date and carry its case number and action label; the rest
    have the roster name and status but no case number (the DDMS date
    differs from every roster action date, or the roster lists no action).

    The roster license number is the bare number ("11765"); the script
    writes DORA's printed form ("LPC.0011765") into the file names and the
    manifest so LPC and LPCC numbers cannot collide. Names come from the
    roster (proper case) when the license number is on it, otherwise from
    DDMS (all caps, title-cased by the script).

    The older documents are IMAGE SCANS. --text-check on the 774 files of
    the first run: 196 have a text layer, 578 are image only (everything
    through 2018, most of 2019, half of 2020, and 31 files from 2021 on).
    Run Foxit OCR on the image-only files BEFORE make_text_sidecars.py.
    The first run downloaded all 774 with 0 failures (976 MB).

    First run on your machine:
    1. py download_colorado_orders.py --list-only and open manifest.csv.
       Expect about 930 rows, about 775 counselor rows with a URL. If the
       roster step fails, open the GenerateRoster page in a browser and
       check that "LPC - Licensed Professional Counselor" is still a
       checkbox; if the DDMS step returns 0 documents, run the search by
       hand at the DDMS address above and compare the result table.
    2. Double-click Run_Colorado_Downloader.cmd. Files already on disk are
       skipped, so re-running after an interruption is safe.
    3. DDMS is an old Oracle site and is slow at times; a "FAILED" row in
       download_log.csv with a timeout just needs a re-run.

AFTER DOWNLOADING
    Foxit OCR the image-only files (the --text-check list), then run
    make_text_sidecars.py --states Colorado from the Complaint Scraper
    folder, register "Colorado" in board_order_extractor.py and run the
    extractor. The manifest's case_number and action columns can be joined
    to the extractor output on license number and effective date.

WHAT THIS ROUTE DOES NOT COVER
    - Roster actions with no document in DDMS (19 LPC action rows for 12
      people, mostly 1990s cases). These need a Colorado Open Records Act
      request to DORA (dora_dpo_licensing@state.co.us).
    - Case numbers for documents whose DDMS date matches no roster action
      (102 counselor files); the case number is inside the PDF.

Official sources:
https://dpo.colorado.gov/ProfessionalCounselor                                   (board home page)
https://apps2.colorado.gov/dora/licensing/Lookup/GenerateRoster.aspx             (roster / discipline list)
https://www.dora.state.co.us/pls/real/DDMS_Search_GUI.DPO_Search_Form            (public documents)
