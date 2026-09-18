IOWA BEHAVIORAL HEALTH BOARD ORDER DOWNLOADER (LMHC ONLY)

Collects order documents for Licensed Mental Health Counselors from the Iowa
Department of Inspections, Appeals and Licensing (DIAL) "Board Actions"
list. Iowa lists actions by date with the licensee's name, city and case
number, one page per action, each linking the documents (statement of
charges, settlement agreement, final order, emergency order). The list does
not say the licence type, and since 1 July 2024 the Board of Behavioral
Health Professionals also covers social workers, psychologists and behavior
analysts (before that, the Board of Behavioral Science covered LMHC and
LMFT only). So this downloader works in three passes.

HOW TO RUN IT

1. Double-click Run_Iowa_Downloader.cmd.
2. Leave the window open while it works (the crawl opens every action
   page 1.5 s apart, so a long list takes a while).

What happens:

PASS 1 - crawl
- the board-actions list is read page by page (following "Next") and each
  action page is opened. Pages that mention the behavioral health /
  behavioral science board or a counselling licence are marked relevant.
- actions.csv records every action page found, whether it was relevant,
  and the PDF links on it.

PASS 2 - download
- every PDF linked from a relevant page is downloaded (three retries,
  real-PDF check, skip if present) into
      state_data\Iowa\_all_behavioral_health\
  named "<action-page>__<document>.pdf". Outcomes go to download_log.csv.

PASS 3 - classify by reading the PDF
- the first three pages of each PDF are read. Orders naming a Licensed
  Mental Health Counselor / LMHC are copied into the Iowa state folder as
  "Honke, Erin 26-0123.pdf";
- other professions stay in _all_behavioral_health only (recorded as
  "drop" in manifest.csv with the profession found);
- PDFs with no text layer (scans) are copied to state_data\Iowa\review\ .
  Run Foxit OCR on that folder, then run
      py download_iowa_orders.py --reclassify

manifest.csv lists every PDF with its category, the profession found, the
character count read, and the target filename for kept ones.

To crawl only (no downloads), which is the right first step:
    py download_iowa_orders.py --list-only
To limit the crawl while testing:
    py download_iowa_orders.py --list-only --max-pages 5

FIRST RUN: THINGS TO CHECK
    Written without access to the live site. Three things are unverified:
    1. List layout. If pass 1 finds no action links, the first list page is
       saved under downloader\debug\ - open it and compare with the site.
       The "Next" link detection may need the site's exact label.
    2. Board filter. Open actions.csv and check that counselling-board
       actions are marked relevant = yes and, for example, nursing actions
       are not. Adjust BOARD_WORDS near the top of the script if needed.
    3. Older orders. DIAL says pre-2024 orders are archived at
       documents.iowa.gov. If action pages link there, they are picked up;
       if the archive is a separate index, it needs its own pass.

    Cross-check: the monthly "Notice of Board Action" emails mirrored at
    content.govdelivery.com (account IACIO) list the same actions by name.

AFTER DOWNLOADING
    Run make_text_sidecars.py --states Iowa from the Complaint Scraper
    folder, then register "Iowa" in board_order_extractor.py and run the
    extractor. The holding and review folders can be set to cloud-only once
    the kept orders are confirmed.

Official source:
https://dial.iowa.gov/i-need/board-actions
