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
       manifest says "name order assumed First Last" for them, and pass 2
       reads the "In re:" line of the PDF to correct the order.
    3. EVERY sampled PDF is a scan with no text layer (8 samples: 2007-era,
       2018, 2019, 2023, 2025 and 2026 orders, 85 KB to 3 MB). Expect pass 2
       to send all 138 files to review\ on the first run. The workflow is
       therefore: run the .cmd (downloads all 138), Foxit-OCR review\, then
       py download_vermont_orders.py --reclassify. The classification words
       could not be checked against real text for this reason; open a few
       "drop" and "review" rows after OCR and adjust COUNSELOR / OTHER_RULES
       if Vermont's wording differs.
    4. Cross-check that does not need OCR: OPR's monthly discipline reports
       (https://sos.vermont.gov/opr/complaints-conduct-discipline/monthly-discipline-reports/,
       92 text-native PDFs, 2019-01 to 2026-08, one line per action:
       "Last, First, City, ST / LCMHC / date: action") name every LCMHC
       action since 2019. They can settle both the profession and the name
       order for 2019+ dockets; older dockets need the OCR pass.
    manifest.csv gained two columns at the end: modified (SharePoint date)
    and dockets_all (every docket number in the file name).

AFTER DOWNLOADING
    Run make_text_sidecars.py --states Vermont from the Complaint Scraper
    folder, then register "Vermont" in board_order_extractor.py and run the
    extractor. The _all_allied_mental_health and review folders can be set
    to cloud-only once the kept orders are confirmed.

Official sources:
https://sos.vermont.gov/opr/complaints-conduct-discipline/conduct-decision-search
https://outside.vermont.gov/dept/sos/office_professional_regulation/conduct_decisions/allied_mental_health/
