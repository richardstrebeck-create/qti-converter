VERMONT ALLIED MENTAL HEALTH DECISION DOWNLOADER (LCMHC ONLY)

Collects conduct decisions for Licensed Clinical Mental Health Counselors
from the Vermont Office of Professional Regulation. Vermont posts every
decision for the Board of Allied Mental Health Practitioners as one PDF in a
single SharePoint folder, mixed with marriage and family therapists,
psychoanalysts and non-licensed psychotherapists, and the file names do not
say which profession is which. So this downloader works in two passes.

HOW TO RUN IT

1. Double-click Run_Vermont_Downloader.cmd.
2. Leave the window open while it works.

What happens:

PASS 1 - list and download
- the decisions folder is listed (SharePoint REST first, page scrape as a
  fallback) and EVERY PDF is downloaded, 1.5 s apart with three retries,
  into  state_data\Vermont\_all_allied_mental_health\
  (files already present are skipped; outcomes go to download_log.csv).

PASS 2 - classify by reading the PDF
- the first three pages of each PDF are read. Decisions naming a Licensed
  Clinical Mental Health Counselor / LCMHC are copied into the Vermont state
  folder as "Reed Luce, Mary docket mh020903.pdf";
- other professions stay in _all_allied_mental_health only (recorded as
  "drop" in manifest.csv with the profession found);
- PDFs with no text layer (older scans) are copied to
  state_data\Vermont\review\ . Run Foxit OCR on that folder, then run
      py download_vermont_orders.py --reclassify
  to sort them. OCR'd copies in review\ take precedence over the originals.

manifest.csv lists every PDF with its category, the profession found, the
character count read, and the target filename for kept ones.

To list the folder without downloading anything:
    py download_vermont_orders.py --list-only

FIRST RUN: THINGS TO CHECK
    Written without access to the live site. Two things are unverified:
    1. Folder listing. If the run says it could not list the folder, open
       https://outside.vermont.gov/dept/sos/office_professional_regulation/conduct_decisions/allied_mental_health/
       in a browser. If the folder has moved, update FOLDER at the top of the
       script; if only the listing page differs, any page fetched is saved
       under downloader\debug\ for comparison.
    2. Classification words. Open a few "drop" and "review" rows in
       manifest.csv and confirm they are not counselors. Adjust COUNSELOR or
       OTHER_RULES near the top of the script if Vermont uses other wording.

    A cross-check is available: OPR's monthly discipline reports
    (https://sos.vermont.gov/opr/complaints-conduct-discipline/monthly-discipline-reports/)
    list every LCMHC action by name and date. Spot-check a few against the
    manifest.

AFTER DOWNLOADING
    Run make_text_sidecars.py --states Vermont from the Complaint Scraper
    folder, then register "Vermont" in board_order_extractor.py and run the
    extractor. The _all_allied_mental_health and review folders can be set
    to cloud-only once the kept orders are confirmed.

Official sources:
https://sos.vermont.gov/opr/complaints-conduct-discipline/conduct-decision-search
https://outside.vermont.gov/dept/sos/office_professional_regulation/conduct_decisions/allied_mental_health/
