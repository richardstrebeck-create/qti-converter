IOWA BEHAVIORAL HEALTH BOARD ORDER DOWNLOADER (LMHC ONLY)

Collects order documents for Licensed Mental Health Counselors from Iowa's
public discipline document index. VERIFIED LIVE 2026-09-18; the layout that
the first draft assumed does not exist, so read "WHERE THE ORDERS ARE".

WHERE THE ORDERS ARE
- https://dial.iowa.gov/i-need/board-actions is a single page with one
  collapsible section per board. The Behavioral Health section holds only
  the last two years of "Notice of Board Action" e-mail bulletins (30 of
  them, July 2024 to August 2026), each listing names and case numbers and
  linking to documents.iowa.gov. There are no per-action pages and no
  pagination, so that page is not crawled.
- https://documents.iowa.gov is the state document search. Filtered to
  Board = "Behavioral Health Professionals, Board of" and Category =
  "Public Discipline Documents" it returned 803 files on 2026-09-18
  (801 PDF, 2 Word), with last name, first name, city and state as
  metadata. 710 of them were bulk-uploaded on 2023-10-30 and are the
  archive of the old Board of Behavioral Science AND of the old social work
  and psychology boards; the rest were added 2024-01 to 2026-09. The index
  date is the upload date, not the order date. Each file downloads from
  https://documents.iowa.gov/home/download/<id>. This is what the script
  reads.

The index does not say the licence type and, since 1 July 2024, the Board
of Behavioral Health Professionals also covers social workers,
psychologists and behavior analysts, so the script works in three passes.

HOW TO RUN IT

1. Double-click Run_Iowa_Downloader.cmd.
2. Leave the window open while it works (about 800 downloads 1.5 s apart,
   so allow half an hour).

What happens:

PASS 1 - crawl
- the documents.iowa.gov index is read 200 records at a time;
- actions.csv records every document: id, document name, licensee name,
  city, state, upload date, file type, case number (when the document name
  carries one) and the download link.

PASS 2 - download
- every file is downloaded (three retries, real-PDF check, skip if
  present) into state_data\Iowa\_all_behavioral_health\ named
  "<id>__<document name>.pdf". Outcomes go to download_log.csv.

PASS 3 - classify by reading the PDF
- the first three pages of each PDF are read (the whole document if they
  are silent). The caption ("RE: Mental Health Counselor License of ...",
  "BEFORE THE BOARD OF SOCIAL WORK") and the licence sentence ("Respondent
  was issued mental health counselor license no. ...") are compared:
  LMHC orders are copied into the Iowa state folder as
  "Latta, Ronda 23-0052.pdf" (name from the index metadata);
  other professions stay in _all_behavioral_health only (recorded as
  "drop" in manifest.csv with the profession found);
  a caption that contradicts the body is sent to review with both readings;
- PDFs with no text layer, or with an unreadable text layer (some 2025-2026
  orders use Type3 fonts with no Unicode map, which extract as symbols),
  are copied to state_data\Iowa\review\ . Run Foxit OCR on that folder,
  then run
      py download_iowa_orders.py --reclassify

manifest.csv lists every file with its category, the profession found, the
character count read, and the target filename for kept ones, plus the
index id, city, state and upload date.

To crawl only (no downloads), which is the right first step:
    py download_iowa_orders.py --list-only
To limit the crawl while testing:
    py download_iowa_orders.py --list-only --max-pages 2

WHAT THE VERIFICATION FOUND (15 sample files)
- 11 of 15 had a usable text layer and classified as expected (LMHC kept,
  social work / psychology dropped, one contradictory file sent to review).
- 2 were scans with no text (one 2023 archive file, one 2025 order).
- 2 recent orders (2025-09 and 2026-08) had an unreadable Type3-font text
  layer; they need OCR like the scans.
- Expect roughly a quarter of the files to land in review\ before OCR.
- The counselor share is unknown until the run: the 803 files cover social
  work and psychology archives too, and 353 distinct people.

Cross-check: the monthly "Notice of Board Action" e-mails at
content.govdelivery.com (account IACIO) list the same recent actions.

AFTER DOWNLOADING
    Run make_text_sidecars.py --states Iowa from the Complaint Scraper
    folder, then register "Iowa" in board_order_extractor.py and run the
    extractor. The holding and review folders can be set to cloud-only once
    the kept orders are confirmed.

Official sources:
https://documents.iowa.gov  (Organization: Inspections, Appeals, and Licensing; Board: Behavioral Health Professionals)
https://dial.iowa.gov/i-need/board-actions
