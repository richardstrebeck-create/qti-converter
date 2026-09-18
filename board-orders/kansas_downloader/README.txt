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

VERIFIED 2026-09-18 (against the 2026-08-14 archived copy of the site)
    The live site sits behind Akamai and refused every automated request from
    the verification session (HTTP 403 "Access Denied"), so the parser was
    verified against the Wayback Machine copy of all eight pages instead.
    What the pages really look like, and what the script now does:
    - one table per letter page, four columns: "Name - LICENSE NUMBER",
      date(s), city, "Document type <case number link>". A licensee with
      several orders has several dates and links in one row;
    - links go to /home/showpublisheddocument/<id>/<ticks>, not to a .pdf
      file name; they still return the PDF;
    - the license label next to the name decides the profession (LPC and
      LCPC are counselors, including dual licensees such as "LCAC 606,
      LPC 3068"); the case-number code is the fallback (PC and LC are the
      counselor codes; 19 codes are decoded in CODE_MAP);
    - manifest.csv gained three columns at the end: license, action_date, city.
    August 2026 copy: 583 documents, 78 counselor, 503 drop, 2 review
    (two cease-and-desist orders against unlicensed persons).

    First run on your machine:
    1. py download_kansas_orders.py --list-only and open manifest.csv. Expect
       about 80 counselor rows. If the counts differ a lot, the site changed.
    2. If the run stops with "Could not read ... 403", the site is blocking
       the script but not your browser. Open each page in the browser
       (root page and A-C ... W-Z), save each as "Webpage, HTML only" into
       downloader\debug\ as root.html, a-c.html, d-f.html, g-j.html, k-m.html,
       n-q.html, r-v.html, w-z.html, then run
           py download_kansas_orders.py --list-only --from-saved debug
       The PDF downloads may still be blocked; if so, they need the browser too.
    3. PDF text layer: could not be checked (downloads blocked). Older
       orders (1990s-2000s) are likely scans; run make_text_sidecars and OCR
       whatever comes back empty.

AFTER DOWNLOADING
    Run make_text_sidecars.py --states Kansas from the Complaint Scraper
    folder (Foxit OCR first if the older scans have no text layer), then
    register "Kansas" in board_order_extractor.py and run the extractor.

Official source:
https://www.ksbsrb.ks.gov/complaints/disciplinary-actions
