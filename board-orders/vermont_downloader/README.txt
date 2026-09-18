VERMONT ALLIED MENTAL HEALTH DECISION DOWNLOADER (LCMHC ONLY)

Collects conduct decisions for Licensed Clinical Mental Health Counselors
from the Vermont Office of Professional Regulation. Vermont posts every
decision for the Board of Allied Mental Health Practitioners as one PDF in a
single SharePoint folder, mixed with marriage and family therapists,
psychoanalysts and non-licensed psychotherapists, and the file names do not
say which profession is which. Every one of those PDFs is an image scan
with no text layer, so the profession cannot be read from the file without
OCR. OPR's monthly discipline reports (text PDFs, one line per action, all
professions, 2019 onward) name the licence type, so the workflow reads
those first and OCRs only what they cannot settle.

ORDER OF OPERATIONS

1. Run the downloader
       double-click Run_Vermont_Downloader.cmd
   PASS 0 builds the LCMHC name list from the monthly reports (this is
   build_vermont_name_list.py, run automatically; it must sit next to the
   downloader). It downloads the monthly discipline reports into
   monthly_reports\ (92 as of 2026-09-18; only new months are fetched on
   later runs), reads every action into monthly_actions_all.csv, keeps the
   allied mental health rows in lcmhc_actions.csv, and matches them by name
   against the folder listing. The result is name_match.csv: one row per
   folder PDF with a proposed category
       counselor   the name matches an LCMHC action in a monthly report
       drop        the name matches only another allied profession
                   (non-licensed psychotherapist, LMFT, psychoanalyst)
       unmatched   no usable report row (pre-2019 dockets, or a name that
                   does not appear in any report)
   PASS 1 lists the decisions folder and downloads EVERY PDF, 1.5 s apart
   with three retries, into state_data\Vermont\_all_allied_mental_health\
   (files already present are skipped; outcomes go to download_log.csv).
   PASS 2 classifies each PDF. With name_match.csv present:
     - "counselor" matches are copied into the Vermont state folder as
       "Lastname, Firstname docket 2025-105.pdf" with the manifest note
       "profession from monthly report";
     - "drop" matches are recorded in manifest.csv with the profession the
       report gave and are NOT copied;
     - "unmatched" files fall through to the text check: the first three
       pages are read; a readable text layer naming an LCMHC is kept, other
       professions are dropped, and PDFs with no text layer (all of them,
       on the first run) are copied to state_data\Vermont\review\ for OCR.
   To see the verdicts before downloading anything:
       py download_vermont_orders.py --list-only
   writes manifest.csv with counselor / drop already filled in where the
   monthly reports settle it ("not downloaded" otherwise).
   To skip the monthly reports and classify by PDF text only:
       py download_vermont_orders.py --no-name-list

2. (Optional) rebuild the name list on its own
       double-click Run_Vermont_Name_List.cmd
       (or:  py build_vermont_name_list.py)
   Same pass 0, run by hand, for example to eyeball the fuzzy matches in
   name_match.csv without touching the downloads. Needs manifest.csv.

3. OCR only what landed in review\
   Run Foxit OCR on state_data\Vermont\review\ (about 67 files on
   2026-09-18, mostly pre-2019 dockets). Leave the OCR'd copies in review\;
   they take precedence over the originals.

4. Re-classify
       py download_vermont_orders.py --reclassify
   Refreshes the name list (new monthly reports, if any) and re-runs pass 2
   only; the OCR'd files are sorted by their text. Repeat 3 and 4 if some
   remain in review.

WHAT TO CHECK AFTER THE RUN

- manifest.csv: the category column. "counselor" rows have a filename;
  "drop" rows say which profession the report gave; "review" rows still
  need OCR. The three columns at the end (name_match_method,
  name_match_license_type, name_match_action_dates) show what the name
  list contributed.
- name_match.csv, rows with match_method "fuzzy" (9 on 2026-09-18): the
  file name and the report spell the name differently (typos such as
  "Savlatore", hyphenated names such as "Best-Bragg", "Ron" for "Ronald").
  All nine looked right, but eyeball them.
- name_match.csv, match_note "several licence types": the person appears in
  the reports under more than one allied licence (for example a
  non-licensed psychotherapist who later became an LCMHC). The file is
  kept as counselor; open it after OCR if the docket year matters.
- The 10 or so 2019+ dockets that are "unmatched" with the note "no report
  row with this name": the person does not appear in any monthly report.
  The reports do not list every filing (stipulations and dismissals in
  particular), so these need OCR like the older files.
- The one "name matches only non-allied-board rows" file (a social worker
  with the same name): also goes to OCR.
- After OCR, open two or three "drop" and "review" rows and confirm the
  wording the classifier keys on (COUNSELOR / OTHER_RULES at the top of
  download_vermont_orders.py) matches what Vermont's orders actually say.
- If a file was copied to review\ by an earlier run and is later settled
  by the name list, the script says so at the end of pass 2 ("need no
  OCR"); it does not delete anything from review\.

FILES IN THIS FOLDER
    download_vermont_orders.py   the downloader (runs pass 0 itself)
    build_vermont_name_list.py   pass 0 (monthly reports -> name_match.csv),
                                 imported by the downloader; runnable alone
    Run_Vermont_Downloader.cmd   double-click for step 1
    Run_Vermont_Name_List.cmd    double-click for the optional step 2
    manifest.csv                 one row per folder PDF: names, docket,
                                 category, note, target filename, and the
                                 name-list columns
    name_match.csv               pass 0 output, read by pass 2
    lcmhc_actions.csv            allied mental health actions from the reports
    monthly_actions_all.csv      every action in every monthly report
    monthly_reports\             cached monthly report PDFs (not in git)

Other options:
    py download_vermont_orders.py --list-only        name list + folder listing, download nothing
    py download_vermont_orders.py --offline-name-list  reuse the cached reports, fetch no new months
    py build_vermont_name_list.py --offline          re-parse the cached reports, no web
    py build_vermont_name_list.py --debug            write debug\parsed_YYYY-MM.txt per report

VERIFIED LIVE 2026-09-18
    1. Folder listing works. The SharePoint REST API refuses anonymous callers
       (401/404), so the script reads the folder's "All Documents" view page,
       which carries the file list as embedded JSON, 30 files per page, and
       follows the "next page" link. On 2026-09-18 the folder held 138 PDFs
       (99 of them bulk-uploaded on 2025-03-13; the rest added 2025-03 to
       2026-09). Dockets run from about 2000 (docket aomh010300) to 2026-134.
    2. File names do NOT follow one pattern. Three shapes were found:
           2025-105_Ashley_MacDonald_Signed_Order.pdf   docket, First Last, type
           2025-38_gould_adam_signed_order.pdf          docket, Last First, type
           albergate-scott-docket-2018-20.pdf           Last First, docket (older)
       The first two cannot be told apart from the name alone, so the
       manifest says "name order assumed First Last" for them; the monthly
       report (which prints names unambiguously) or the "In re:" line of an
       OCR'd PDF corrects the order.
    3. EVERY sampled PDF is a scan with no text layer (8 samples: 2007-era,
       2018, 2019, 2023, 2025 and 2026 orders, 85 KB to 3 MB). Without the
       name list, pass 2 sends all 138 files to review\.
    4. Monthly discipline reports: the page links all 92 PDFs (2019-01 to
       2026-08) directly; all 92 parse. They list 960 actions across all
       professions, 78 of them allied mental health (37 LCMHC rows for 27
       people, 40 non-licensed psychotherapist, 1 LMFT, no psychoanalyst).
       Matching against the 138 folder PDFs: 36 counselor (26 people),
       35 drop, 67 unmatched (56 pre-2019 dockets, 10 names in no report,
       1 social-worker-only name). The downloader itself has not been run
       against the decision PDFs yet; the name-list path was tested on a
       stand-in folder of blank PDFs with the real file names.
    manifest.csv columns added at the end: modified, dockets_all (2026-09-18,
    listing) and name_match_method, name_match_license_type,
    name_match_action_dates (2026-09-18, name list).

AFTER DOWNLOADING
    Run make_text_sidecars.py --states Vermont from the Complaint Scraper
    folder, then register "Vermont" in board_order_extractor.py and run the
    extractor. The _all_allied_mental_health and review folders can be set
    to cloud-only once the kept orders are confirmed.

Official sources:
https://sos.vermont.gov/opr/complaints-conduct-discipline/conduct-decision-search
https://outside.vermont.gov/dept/sos/office_professional_regulation/conduct_decisions/allied_mental_health/
https://sos.vermont.gov/opr/complaints-conduct-discipline/monthly-discipline-reports/
