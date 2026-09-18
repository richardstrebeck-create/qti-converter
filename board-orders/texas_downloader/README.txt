TEXAS PROFESSIONAL COUNSELOR AGREED-ORDER DOWNLOADER

Collects the signed Agreed Orders for Licensed Professional Counselors (and
LPC Associates, which the source does not separate) from the Texas Behavioral
Health Executive Council (BHEC), the umbrella agency over the Texas State
Board of Examiners of Professional Counselors. Marriage and family therapy
(LMFT), psychology (PSY) and social work (SW) orders sit in the same
packets; they are deliberately left out, and each one is still recorded in
manifest.csv with the reason.

Built to mirror the Oklahoma, Kansas and Maryland downloaders. Same flags,
same manifest and log layout, same filename convention.

WHERE THE ORDERS COME FROM

BHEC has no disciplinary list on its website, and its licensee lookup
(the HPC "datamart") is protected by Google reCAPTCHA and refuses any search
sent by a script. What BHEC does publish is the "Public Meeting Materials"
packet for every Council meeting, three or four times a year, on
    https://bhec.texas.gov/tbhec/important-dates/past-council-meeting-dates/
Since the October 2021 meeting each packet has carried the item "Agreed
Orders and Dismissals for the fiscal-quarter", and that item IS the signed
orders, sorted by profession. The script downloads each packet once, pulls
the LPC orders out of it and throws the packet away.

HOW TO RUN IT

1. Install once:  py -m pip install requests pymupdf
2. Double-click Run_Texas_Downloader.cmd.
3. Leave the window open while it works. The 17 packets add up to about
   950 MB, so the first run takes 10 to 30 minutes depending on the
   connection; later runs only fetch packets that are new.

What happens:

- pass 0 downloads BHEC's daily list of every CURRENT LPC and LPC Associate
  (https://www.bhec.texas.gov/csv/LPC.csv, about 44,000 rows, with a
  "Discpl_Actn" yes/no column). It is used only to check names and to fill
  in license numbers; people whose license has since lapsed or been revoked
  are not on it, so about a third of the orders get no license number;
- pass 1 reads the past-meetings page and lists every "Agenda & Public
  Meeting Materials" link with its meeting date (17 packets on 2026-09-18,
  October 2021 to June 2026);
- pass 2 downloads each packet (1.5 s apart, three retries) into
  downloader\packets\ and reads it:
    . packets from February 2024 on are zip files with one PDF per licensee
      in folders named LPC, LMFT, PSY, SW: the LPC files are copied out;
    . the four 2023 packets are zip files with one combined PDF per
      profession ("LPC Q3 FY23 Agreed Orders.pdf") that has a bookmark per
      licensee: the file is split at the bookmarks;
    . the five 2021 to 2022 packets are single big PDFs with a bookmark
      section "3.e ... LPC Agreed Orders" and a bookmark per licensee:
      split the same way. The May 2022 packet has no LPC bookmarks, so
      its unbookmarked pages go to review\ for a manual split (see below);
- every LPC order is written to the Texas state folder one level up, named
      "Joslin, Gene FY25Q4 2025-10-14.pdf"
  (the fiscal quarter the order was reported in, then the date of the
  Council meeting whose packet carried it; the order's own signature date
  is inside the scan). A second order for the same person in the same
  quarter becomes "... (2).pdf";
- files already present are skipped, and packet_index.json remembers what
  each packet contained, so a re-run downloads only packets whose orders
  are not yet on disk. Every outcome is written to download_log.csv.

To build the manifest without writing any orders (the packets still have
to be downloaded to read them; add --keep-packets so the real run does not
download them a second time):
    py download_texas_orders.py --list-only --keep-packets

To count how many downloaded PDFs already have a text layer:
    py download_texas_orders.py --text-check

To ignore packet_index.json and re-read every packet: --refresh

VERIFIED 2026-09-18 (live, from a cloud session; first full run the same day)
    Routes checked and rejected: bhec.texas.gov has no enforcement or
    disciplinary-actions page (the "Discipline and Complaints" pages
    describe the process only; the news feed is rules and webinars). The
    HPC datamart (vo.licensing.hpc.texas.gov/datamart) answers every search
    with "Google reCAPTCHA verification failed" unless the form is submitted
    from a real browser with a good reCAPTCHA score; a headless browser
    from a cloud address was refused too, so the per-licensee "Reports
    Available for Download" links could not be reached or verified. The
    LPC Board's own meeting packets carry an enforcement report with charts
    only, no names. data.texas.gov has no BHEC discipline data set.

    What the first full run found: 17 Council packets (2021-10-26 to
    2026-06-16), 171 LPC order files for 166 people (FY21 Q4 to FY26 Q3,
    i.e. orders reported from June 2021 to May 2026; 3 to 26 per quarter),
    0 failures. One of the 171 files holds two orders (Pruitt and Ripstra,
    FY23 Q4: the packet's bookmark for the second order had no page
    number), so 172 orders in all. 119 orders for LMFT, PSY and SW were
    dropped. One review file: the nine unbookmarked pages of the May 2022
    packet (FY22 Q2), which hold at least one LPC order (Cynthia Kay)
    followed by MFT and PSY orders.

    The orders are IMAGE SCANS. --text-check on the 171 files: 10 have a
    text layer, 161 are image only. Run Foxit OCR on the Texas folder
    BEFORE make_text_sidecars.py.

    Name handling: 105 of the 171 orders matched a current licensee in
    LPC.csv (license number and rank filled in; 3 are LPC Associates).
    Bookmarks written "Howson Heather" or "Frank Del Rio" are put in
    "Lastname, Firstname" order using the licensee list (see the flags
    column). Four 2023 bookmarks carry a surname only ("Martin AO",
    "Pickett AO", "Ross AO", "2023-00143 Ecke"); the full name is on the
    first page of the scan. Eight names match several current licensees,
    so their license number is left blank.

    First run on your machine:
    1. py download_texas_orders.py --list-only --keep-packets and open
       manifest.csv. Expect about 170 counselor rows and 17 packets. If a
       packet fails to download, open its packet_url in a browser; the
       links on the past-meetings page are plain files.
    2. Double-click Run_Texas_Downloader.cmd. Files already on disk are
       skipped, so re-running after an interruption is safe.
    3. If the meetings page changes layout (0 packets found), open the URL
       above in a browser and compare with MEETINGS_URL / PACKET_LINK in
       the script.

AFTER DOWNLOADING
    1. Foxit OCR the Texas folder (161 of 171 are scans).
    2. Split by hand:
       - "Pruitt, Jennifer + Ripstra, Leeann FY23Q4 2023-10-24.pdf"
         (two orders; each starts with "IN THE MATTER OF");
       - review\REVIEW 2022-05-18 BHEC-20220518-meeting-materials.pdf
         (keep the pages whose caption says "PROFESSIONAL COUNSELORS",
         name the file "Kay, Cynthia FY22Q2 2022-05-18.pdf" and drop the
         MFT and PSY pages).
    3. Run make_text_sidecars.py --states Texas from the Complaint Scraper
       folder, register "Texas" in board_order_extractor.py and run the
       extractor. LPC Associates are not marked in the file names; the
       order text says "professional counselor associate" where it applies.

WHAT THIS ROUTE DOES NOT COVER
    - Orders before June 2021 (the Council's first packet with orders is
      October 2021; earlier orders were entered by the old TSBEPC under
      DSHS and are not online). A Public Information Act request to
      Open.Records@bhec.texas.gov is the only route.
    - Default orders and SOAH final orders (contested cases). Only AGREED
      orders are in the packets. Contested-case outcomes appear in the
      datamart record of the licensee and would need a records request.
    - Anything after the latest packet; a new packet appears about six
      weeks after each fiscal quarter (Sep-Nov, Dec-Feb, Mar-May, Jun-Aug).

Official sources:
https://bhec.texas.gov/tbhec/important-dates/past-council-meeting-dates/   (packets)
https://www.bhec.texas.gov/csv/LPC.csv                                     (current licensees)
https://vo.licensing.hpc.texas.gov/datamart/selSearchType.do               (per-licensee lookup, browser only)
