KANSAS PROFESSIONAL COUNSELOR BOARD ORDER DOWNLOADER

Collects order PDFs for Licensed Professional Counselors and Licensed
Clinical Professional Counselors ONLY from the Kansas Behavioral Sciences
Regulatory Board's public "Disciplinary Actions" index. Social workers,
marriage and family therapists, addiction counselors, psychologists and
behavior analysts (all regulated by the same board) are deliberately left
out; each dropped entry and the reason is still recorded in manifest.csv.

Built to mirror the Maryland downloader. Same flags, same manifest and log
layout, same filename convention.

HOW TO RUN IT

1. Double-click Run_Kansas_Downloader.cmd.
2. Leave the window open while it works.

What happens:

- the root Disciplinary Actions page and its seven last-name pages
  (A-C, D-F, G-J, K-M, N-Q, R-V, W-Z) are read; any extra sub-page linked
  from the root page is picked up automatically;
- every PDF link is classified. Kansas case numbers carry a profession code
  (22-PC-0163: "PC" = professional counselor). When the code is missing or
  unrecognised, the entry text is checked for profession words. Entries that
  cannot be settled either way are marked "review";
- manifest.csv lists every entry (counselor, drop, review) with the target
  filename for kept ones;
- each kept PDF is downloaded sequentially (1.5 s pause, three retries,
  checked to be a real PDF) into the Kansas state folder one level up,
  named "Anderson, Mary J. 22-PC-0163.pdf". A second document for the same
  case (for example a Consent Agreement plus a later Revocation order)
  becomes "... 22-PC-0163 (2).pdf";
- files already present are skipped, so the script can be re-run safely;
- every outcome is written to download_log.csv.

"REVIEW" ENTRIES
    Entries with no profession code and no profession words (typically the
    1990s cases numbered like 96-0608) are listed in manifest.csv with
    category "review" and are NOT downloaded unless you run
        py download_kansas_orders.py --include-review

To check the list without downloading any orders:
    py download_kansas_orders.py --list-only

FIRST RUN: THINGS TO CHECK
    This script was written without being able to open the live site, so on
    the first run:
    1. Run --list-only and open manifest.csv.
    2. Confirm the "counselor" rows are really LPC/LCPC and that last_name /
       first_name look right (the name column is parsed from the page text;
       cities or credentials may leak into it if the layout differs).
    3. If the run reports "No PDF links were found", the fetched pages are
       saved under downloader\debug\ - open one and compare with the site.
    4. If the board uses a profession code other than PC for counselors,
       add it to CODE_MAP near the top of the script.

AFTER DOWNLOADING
    Run make_text_sidecars.py --states Kansas from the Complaint Scraper
    folder (Foxit OCR first if the older scans have no text layer), then
    register "Kansas" in board_order_extractor.py and run the extractor.

Official source:
https://www.ksbsrb.ks.gov/complaints/disciplinary-actions
