DELAWARE COUNSELOR BOARD ORDER DOWNLOADER

Collects the public disciplinary documents for Professional Counselors of
Mental Health (Delaware's LPC-equivalent, license prefix "PC-") from the
Delaware Division of Professional Regulation (DPR), Board of Mental Health
and Chemical Dependency Professionals. Chemical Dependency Professionals
(LCDP) and Marriage and Family Therapists (LMFT), who share the same board,
are recorded in manifest.csv as dropped, with the reason, and never fetched.

Built to mirror the Oklahoma, Texas and Colorado downloaders: same flags,
same manifest and log layout, same filename convention.

WHERE THE DOCUMENTS COME FROM

Delaware keeps two public systems that between them give the full picture:

1. The Open Data Portal "Disciplinary Actions for Professional and
   Occupational Licensees"
       https://data.delaware.gov/api/views/dz6p-akeq/rows.csv?accessType=DOWNLOAD
   One row per action for every DPR licensee (License Type, License_no,
   disciplinary_action, disp_start, disp_end). The rows with License Type
   "Professional Counselor of Mental Health" are the counselors. This is
   the INDEX: who has an action, which kind, when. It has no document links.

2. DELPROS, the license-verification site
       https://delpros.delaware.gov/OH_VerifyLicense
   A Salesforce site whose search runs through Visualforce JavaScript
   remoting (no CAPTCHA). For each counselor license number the script
   asks DELPROS for that license, then for its "Board Order documents":
   each one has a name, a description ("Consent Agreement", "Disciplinary
   Order 2016", "Board Order") and a public Salesforce content-delivery
   link. This is the DOCUMENT list.

THE ONE MANUAL STEP

The delivery links are Salesforce "content delivery" pages, not files.
Opening one in a browser shows the PDF with a Download button, but the
bytes are fetched by a Lightning component after the page runs
JavaScript, so a plain download tool cannot pull the file straight from
the link. The script still does the entire tedious part for you: it finds
every counselor, every board-order document, and the exact link and file
name for each. Then, for the files it cannot pull directly, it writes a
page you click through:

    state_data\Delaware\manual_downloads.html

Open that file in your browser. It lists every document grouped by
licensee. Click each link, wait for the Salesforce viewer, press its
Download button, and save the file into state_data\Delaware\ under the
name shown next to the link (the same name manifest.csv gives it). On
2026-09-19 that was 38 files for 26 counselors, about 15 minutes once.

HOW TO RUN IT

1. Install once:  py -m pip install requests beautifulsoup4
   (and  py -m pip install pymupdf  if you want --text-check).
2. Double-click Run_Delaware_Downloader.cmd.
3. When it finishes, open state_data\Delaware\manual_downloads.html and
   save the listed files by hand (see above).

What happens:

- pass 1 downloads the open-data CSV into downloader\index\ and reads the
  counselor rows: name, license number, and every action with its type
  and dates;
- pass 2 asks DELPROS for each counselor's board-order documents (two
  remoting calls per licensee, 1.5 s apart);
- manifest.csv gets one row per document (name, license number, action
  types and dates from the index, document name and description, delivery
  URL, target file name, category) plus one "index only" row for every
  counselor whose action is in the open-data list but who has no record in
  DELPROS (old licenses that predate the system);
- pass 3 tries a direct download of each link (saved and checked for %PDF
  if Delaware ever serves the file directly), and records every link it
  could not pull as "MANUAL" in download_log.csv, then writes
  manual_downloads.html;
- files already present in state_data\Delaware\ are skipped, so the script
  can be re-run safely; a re-run only adds new actions.

Flags:
    py download_delaware_orders.py --list-only     build manifest.csv and manual_downloads.html only
    py download_delaware_orders.py --skip-index    reuse the CSV already in downloader\index\
    py download_delaware_orders.py --max-downloads N
    py download_delaware_orders.py --text-check    count downloaded PDFs with a text layer (needs PyMuPDF)

VERIFIED 2026-09-19 (live, from a cloud session)
    Board page: dpr.delaware.gov/boards/profcounselors/ has no actions
    list; its "Disciplinary Action Information" page says the list is on
    the Open Data Portal and the Board Orders are on DELPROS, per licensee.

    Open-data CSV on 2026-09-19: 33 Professional Counselors of Mental
    Health with a disciplinary action (69 action rows, 1997 to 2025;
    Letter of Reprimand, Probation, Suspension, Remedial Education,
    Revocation, Fine, Cease and Desist). Also under the same board: 5
    Chemical Dependency Professional and 5 Marriage and Family Therapist
    rows, dropped.

    DELPROS documents: 26 of the 33 counselors have board-order documents
    (38 documents total). The other 7 have no record in DELPROS (their
    licenses predate the system) and are kept as index-only rows; their
    action is in manifest.csv but the order is not posted. The robust key
    is the license number: a name search misses several licensees, a
    license-number search finds them.

    The document bytes could not be pulled by script from the Salesforce
    delivery links (browser-only, see THE ONE MANUAL STEP). None was
    downloaded automatically in the verification run; the 38 are listed in
    manifest.csv and manual_downloads.html for the by-hand save.

    Older orders are image scans (the "15-Lastname-...-Discipline-YEAR.pdf"
    files); run Foxit OCR before make_text_sidecars.py. Run --text-check
    after saving the files to get the exact scan list.

WHAT THIS ROUTE DOES NOT COVER
    - The 7 counselors with an action in the open-data list but no
      document in DELPROS (old cases). A Delaware FOIA request to DPR
      (customerservice.dpr@delaware.gov) is the only route to those orders.
    - Chemical Dependency Professionals and Marriage and Family Therapists
      under the same board (out of scope for this project).

Official sources:
https://dpr.delaware.gov/boards/profcounselors/                                  (board home page)
https://dpr.delaware.gov/disciplinary-action-information/                        (how DPR posts discipline)
https://data.delaware.gov/api/views/dz6p-akeq/rows.csv?accessType=DOWNLOAD       (open-data index)
https://delpros.delaware.gov/OH_VerifyLicense                                    (DELPROS, the documents)
