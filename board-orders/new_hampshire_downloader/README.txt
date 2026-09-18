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

VERIFIED 2026-09-18 (against the 2025-06 archived copy of the site)
    The live site sits behind Akamai and refused every automated request from
    the verification session (HTTP 403 "Access Denied"), so the parser was
    verified against the Wayback Machine copy of the root page and the 2017
    to 2025 year pages instead. What the pages really look like:
    - no table. 2017-2023: a bulleted list, one item per action, the name and
      license type in bold ("Steven Durost, MA, LCMHC, License #605"), then
      "4/21/2017 - On April 21, 2017, the Board ... approved a <link>";
    - 2024: one paragraph per action, bold name segment then a link whose
      label is "Voluntary Surrender, 10/18/2024";
    - 2025: the whole entry is the link label
      ("Samuel Rosario, LCSW, License # 324, Order of Dismissal, 04/18/2025").
    The license type in the name segment decides the category (LCMHC kept;
    LICSW / LCSW, MFT, pastoral, unlicensed and candidates dropped).
    manifest.csv gained one column at the end: license_type (the raw name
    segment, so the decision can be checked by eye).
    June 2025 copy: 39 documents 2017-2025, 18 LCMHC (13 people), 21 dropped.
    No "review" rows.

    First run on your machine:
    1. py download_new_hampshire_orders.py --list-only and open manifest.csv.
    2. If the run stops with "Could not read the root page ... 403", the site
       is blocking the script but not your browser. Save the root page and
       each year page as "Webpage, HTML only" into downloader\debug\ as
       root.html, 2017.html, 2018.html ... then run
           py download_new_hampshire_orders.py --list-only --from-saved debug
       If the PDFs are blocked as well, download the 18 LCMHC files by hand
       using the official_url and filename columns of the manifest.
    3. PDF text layer: could not be checked (downloads blocked). These are
       recent Word-generated documents, so a text layer is likely.

AFTER DOWNLOADING
    Run make_text_sidecars.py --states "New Hampshire" from the Complaint
    Scraper folder, then register "New Hampshire" in board_order_extractor.py
    and run the extractor.

Official source:
https://www.oplc.nh.gov/board-mental-health-practice-actions
