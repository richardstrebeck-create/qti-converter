NEW HAMPSHIRE MENTAL HEALTH PRACTICE BOARD ORDER DOWNLOADER

Collects order PDFs for Licensed Clinical Mental Health Counselors (LCMHC)
ONLY from the New Hampshire Office of Professional Licensure and
Certification's "Board of Mental Health Practice - Board Actions" pages.
Clinical social workers (LICSW/LCSW), marriage and family therapists,
pastoral psychotherapists and unlicensed respondents share the same pages
and are deliberately left out; each dropped entry and the reason is still
recorded in manifest.csv.

Built to mirror the Maryland and Kansas downloaders: same flags, manifest
and log layout, and filename convention.

HOW TO RUN IT

1. Double-click Run_New_Hampshire_Downloader.cmd.
2. Leave the window open while it works.

What happens:

- the root Board Actions page and one page per year (2017 to the current
  year, plus any year the root page links) are read;
- every PDF link is classified by the license type in its row (LCMHC kept);
- manifest.csv lists every entry (counselor, drop, review) with the target
  filename for kept ones;
- each kept PDF is downloaded sequentially (1.5 s pause, three retries,
  checked to be a real PDF) into the New Hampshire state folder one level
  up, named "DeValk, Sara LCMHC2564 2023-08-18.pdf";
- files already present are skipped, so the script can be re-run safely;
- every outcome is written to download_log.csv.

VOLUME AND RETENTION
    Small: a handful of actions per year across all license types, LCMHC a
    minority. OPLC removes documents after about seven years, so re-run
    yearly to keep the folder current; older orders need a records request.

"REVIEW" ENTRIES
    Rows whose license type could not be read are marked "review" and are
    NOT downloaded unless you run
        py download_new_hampshire_orders.py --include-review

To check the list without downloading any orders:
    py download_new_hampshire_orders.py --list-only

FIRST RUN: THINGS TO CHECK
    Written without access to the live site. Run --list-only first and open
    manifest.csv: confirm counselor rows are LCMHC and names parsed cleanly.
    If nothing is found, the fetched pages are saved under downloader\debug\.

AFTER DOWNLOADING
    Run make_text_sidecars.py --states "New Hampshire" from the Complaint
    Scraper folder, then register "New Hampshire" in board_order_extractor.py
    and run the extractor.

Official source:
https://www.oplc.nh.gov/board-mental-health-practice-actions
