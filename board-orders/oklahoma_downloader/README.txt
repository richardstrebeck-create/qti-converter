OKLAHOMA PROFESSIONAL COUNSELOR BOARD ORDER DOWNLOADER

Collects order PDFs for Licensed Professional Counselors ONLY from the
Oklahoma State Board of Behavioral Health Licensure's public register
(obbhl.us.thentiacloud.net). Marital and family therapists (LMFT) and
behavioral practitioners (LBP), regulated by the same board, are
deliberately left out; each dropped licensee and the reason is still
recorded in manifest.csv. LPC Candidates (people still under supervision,
not yet licensed) are listed separately and downloaded only on request.

Built to mirror the Kansas and Maryland downloaders. Same flags, same
manifest and log layout, same filename convention.

HOW TO RUN IT

1. Double-click Run_Oklahoma_Downloader.cmd.
2. Leave the window open while it works (about ten minutes).

What happens:

- pass 1 asks the register for every licensee it tags as "disciplined"
  (one request; 186 people of all professions on 2026-09-18). Each is
  sorted by the profession printed on the record: LPC = counselor,
  LPC Candidate = candidate, LMFT and LBP = drop;
- pass 2 opens the profile of every counselor and candidate (one request
  each, 1.5 s apart) and reads its "Public Notices". manifest.csv gets one
  row per notice: name, license number, profession, license status, notice
  type, effective date, the one-line summary, how many documents are
  attached, their names, the download links and the target filenames;
- notices with no attached document (most of those before 2021)
  stay in the manifest flagged "index only, no document". They are the
  older history and would need a records request;
- pass 3 downloads every attached document on a counselor notice
  (1.5 s pause, three retries, checked to be a real PDF) into the Oklahoma
  state folder one level up, named
      "Aggreh, Christiana LPC04898 2023-04-07.pdf"
  (license number, then the notice's effective date). A second document
  on the same notice becomes "... 2023-04-07 (2).pdf";
- files already present are skipped, so the script can be re-run safely;
- every outcome is written to download_log.csv.

To check the list without downloading any orders:
    py download_oklahoma_orders.py --list-only

To also download the LPC Candidate orders (11 people on 2026-09-18):
    py download_oklahoma_orders.py --include-candidates

To count how many downloaded PDFs already have a text layer (needs
PyMuPDF: py -m pip install pymupdf):
    py download_oklahoma_orders.py --text-check

VERIFIED 2026-09-18 (live, from a cloud session; first full run the same day)
    The old ok.gov "Disciplinary Licensee" lists are gone. The board's site
    (oklahoma.gov/behavioralhealth.html) now only links to the Thentia
    register, which is a JavaScript app. Its data layer, however, answers
    plain web requests without a login, and that is what the script uses:
    - search:   rest/public/profile/search/?keyword=&skip=0&take=2000&disciplined=true
                (144 LPC, 11 LPC Candidate, 23 LMFT, 8 LBP = 186 records);
    - profile:  rest/public/profile/get/?id=<id>  gives the Public Notices
                (notice type, effective date, summary, attachments);
    - download: rest/public/annotation/download/index.php?id=<id>&entity=<token>
                where both values are copied from the attachment record.
                The token is a per-file signature the register hands out
                with the profile, so the link needs no password.
    The register answers "403 Forbidden" to a bare script; the script
    therefore identifies itself as a normal browser, which is accepted.

    What the first full run found (2026-09-18): 144 disciplined LPCs with
    161 notices between them, dated 1989 to 2026-08-07. Only 39 notices
    carry a document; the other 122 are index-only lines (a date and a
    one-sentence summary). The 39 orders run from 2010-04-08 to 2026-08-07,
    eight of them before 2020 and the rest from 2021 on. All 39 downloaded
    without a failure. The 11 LPC Candidates have notices but no documents.
    Document names follow "Lastname, Firstname_<case number>_Consent Order.pdf",
    "..._Final Order.pdf", "..._Voluntary Surrender.pdf"; the case number
    (for example 2025-LPC-738) is kept in the manifest's case_number column.
    Four licensees have no license number on the register ("N/A"); their
    files are named with the case number instead, or with the name and
    date alone when there is no case number either.

    The orders are mostly IMAGE SCANS. --text-check on the 39 files: 7 have
    a text layer, 32 are image only. Run Foxit OCR on the Oklahoma folder
    BEFORE make_text_sidecars.py, otherwise 32 sidecars come back empty.

    First run on your machine:
    1. py download_oklahoma_orders.py --list-only and open manifest.csv.
       Expect about 160 counselor rows (one per notice) and about 40 with
       an attachment. If the counts differ a lot, the register changed.
    2. Double-click Run_Oklahoma_Downloader.cmd. Files already on disk are
       skipped, so re-running after an interruption is safe.
    3. If the run stops with "403" on every request, the register has
       started blocking scripts. Open https://obbhl.us.thentiacloud.net/webs/obbhl/register/
       in a browser, tick "Disciplined", and check that the site still
       works by hand; then adjust HEADERS in the script.

AFTER DOWNLOADING
    Foxit OCR the Oklahoma folder (the orders are scans), then run
    make_text_sidecars.py --states Oklahoma from the Complaint Scraper
    folder, register "Oklahoma" in board_order_extractor.py and run the
    extractor.

Official source:
https://obbhl.us.thentiacloud.net/webs/obbhl/register/   (tick "Disciplined")
https://oklahoma.gov/behavioralhealth.html               (board home page)
