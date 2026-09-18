# LPC Board Orders: Survey of Remaining States (written 2026-09-18)

Companion to `HANDOFF_2026-09-17.md`. Purpose: decide which of the 31
remaining jurisdictions (30 states + DC) are worth scraping next.

## How this was produced, and one caveat

Twenty states are complete in `board_orders_master.xlsx` (2,335 rows):
AL, AZ, FL, KY, LA, MD, MN, MS, MO, NJ, NC, OH, PA, RI, SC, TN, UT, VA,
WA, WI.

The remaining 31 were researched from a cloud session whose network
policy blocks state government websites. Every finding below therefore
comes from search-engine indexing of the real pages and file URLs, not
from opening the pages. Formats and ratings are provisional. Before
building a downloader, open the listed URL in a browser and confirm
(a) that the page exists, (b) that it links the full order documents,
not just a summary line, and (c) roughly how many entries it has.

The distinction that matters most for this project: many boards publish
an INDEX (who was disciplined, when, what sanction) without publishing
the ORDER itself. The dataset depends on the full order narrative, so a
state is only "easy" if the order PDFs are linked in bulk.

## Tier 1: full orders posted, one PDF per action (Maryland pattern)

| State | Board / page | What the index shows | Notes |
|---|---|---|---|
| Kansas | BSRB, https://www.ksbsrb.ks.gov/complaints/disciplinary-actions with sub-pages /a-c, /d-f, /g-j, /k-m, /n-q, /r-v, /w-z | A-Z list pages, each entry links one PDF per order at ksbsrb.ks.gov/docs/default-source/disciplinary-actions/<case>.pdf. Case numbers carry a profession code (22-PC-0163 = professional counselor). Cases from 1996 onward. | Best candidate. Static HTML, 7 pages, profession filter is in the case number. Older PDFs likely scanned. Board also covers SW, MFT, psychology, addiction. |
| New Hampshire | OPLC Board of Mental Health Practice, https://www.oplc.nh.gov/board-mental-health-practice-actions plus yearly pages ...-actions-2017 through -2026 | One row per action (name, license type, license #, action type, date), each linking a PDF. LCMHC rows labeled. | Small volume (3 to 8 actions/year all types). Documents kept online 7 years only. Easy build. |
| Vermont | OPR, monthly reports https://sos.vermont.gov/opr/complaints-conduct-discipline/monthly-discipline-reports/ ; decision PDFs at https://outside.vermont.gov/dept/sos/office_professional_regulation/conduct_decisions/allied_mental_health/ | Monthly PDF reports with predictable URLs (monthly_discipline_reports_YYYY-MM.pdf) listing name, license type, action, date. Full decisions as individual PDFs in a per-profession SharePoint folder (filenames like lastname_first_docket_NNNN.pdf). | Two-step: monthly reports give the LCMHC names, folder gives the orders. Older decisions look scanned (OCR needed). Folder listing page needs JavaScript, direct PDF links do not. |
| Iowa | Board of Behavioral Health Professionals (now under DIAL), https://dial.iowa.gov/i-need/board-actions ; older orders reportedly on documents.iowa.gov | Dated list of board actions with name, city, case number, each with its own page (e.g. /i-need/board-actions/2023-03-07/recent-board-action-february-28-2023). Orders (charges, settlement, final order) presumably linked from each page. | Board merged with social work and psychology on 2024-07-01, so license type must be read from the order. Could not confirm PDF links. Was on the handoff's candidate list. |
| Oklahoma | State Board of Behavioral Health Licensure, Thentia register https://obbhl.us.thentiacloud.net/webs/obbhl/register/ (tick "Disciplined"). The register's REST layer answers plain GET requests: `rest/public/profile/search/?keyword=&take=2000&disciplined=true` (186 records, 144 LPC), `rest/public/profile/get/?id=` (Public Notices), `rest/public/annotation/download/index.php?id=&entity=` (signed PDF link) | One Public Notice per action on each licensee's profile: notice type, effective date, one-sentence summary, attached order PDF. Notices back to 1989; PDFs mostly 2021 on with a few back to 2010. | Verified 2026-09-18 live and downloaded the same day: 144 disciplined LPCs, 161 notices, 39 order PDFs (0 failures), 7 text-native and 32 scans (OCR). The old ok.gov lists are gone; the AG board supervisory letters are JavaScript-listed HTML summaries, fallback only. Profession filter is the `registrationCategory` field. Moved up from Tier 2. See SURVEY_VERIFICATION_OK_NM_NV_ND_2026-09-18.md and state_data\Oklahoma\downloader\README.txt. |
| Texas | BHEC Council meeting packets, https://bhec.texas.gov/tbhec/important-dates/past-council-meeting-dates/ (one "Agenda & Public Meeting Materials" zip or PDF per meeting, October 2021 on) | Each packet's item "Agreed Orders and Dismissals for the fiscal-quarter" is the signed agreed orders themselves, sorted by profession: one PDF per licensee in an LPC folder since 2024, bookmarked combined PDFs in 2023, bookmarked packet sections in 2021 to 2022. Plus BHEC's daily current-licensee CSV (https://www.bhec.texas.gov/csv/LPC.csv) with a Discpl_Actn flag (301 of 43,924 on 2026-09-18) for cross-checks. | Verified 2026-09-18 and downloaded the same day: 17 packets, 172 LPC agreed orders for 166 people (FY21 Q4 to FY26 Q3, June 2021 to May 2026), 0 failures; 161 of 171 files are scans (OCR). Agreed orders only; nothing before June 2021; the HPC datamart lookup is reCAPTCHA-protected and refuses scripts (headless browser included), so no per-licensee route. Moved up from Tier 3. See TEXAS_VERIFICATION_2026-09-18.md and texas_downloader\README.txt. |
| Colorado | DORA DPO: roster generator https://apps2.colorado.gov/dora/licensing/Lookup/GenerateRoster.aspx (CSV per license type, one row per public action with case number, action, effective and end dates) plus the DPO Public Documents System https://www.dora.state.co.us/pls/real/DDMS_Search_GUI.DPO_Search_Form (one search with State Board = Professional Counselors lists every document with a direct PDF link) | Roster: 20,098 LPCs, 557 with a public action (910 action rows, 1992 to 2026). DDMS: 898 documents under the counselor board, 774 LPC/provisional LPC, 92 LPCC, 30 other; effective dates 1992-08-30 to 2026-06-17, about 50 to 77 a year since 2016. | Verified 2026-09-18 and downloaded the same day: 774 counselor documents, RUN_SUMMARY_PLACEHOLDER. The per-licensee lookup the survey expected is behind an Amazon WAF CAPTCHA (apps.colorado.gov) and a form CAPTCHA (apps2), but it is not needed: the roster is the index and DDMS is the document store, both plain HTTP. Older documents are scans (OCR). Moved up from Tier 2 MODERATE to EASY. See COLORADO_VERIFICATION_2026-09-18.md and colorado_downloader\README.txt. |
| Nevada | Board of Examiners for MFT and CPC, https://marriage.nv.gov/Services/Disciplinary_Actions/ | Dedicated disciplinary actions page exists; contents not visible in the index. Board covers MFT and CPC only. | Tiny volume (about one settled case per year per a 2019 report). Worth a 5-minute look, not a scraper. Verified 2026-09-18: page is at https://www.marriage.nv.gov/services/disciplinary-actions/ (the bare host and both survey paths 404). Text-only list of 37 licensees, 2012 to 2026, name, license number, complaint number, action label and date; no order PDFs and no links. CPC separable by complaint number (NV23CPC008) and CP/CI license prefix: 10 CPC people. NOT FEASIBLE for orders; index only. See SURVEY_VERIFICATION_OK_NM_NV_ND_2026-09-18.md. |
| New Mexico | RLD Counseling and Therapy Practice Board, https://www.rld.nm.gov/boards-and-commissions/individual-boards-and-commissions/counseling-and-therapy-practice/discipline-and-enforcement/ | Sibling RLD boards keep a list of final actions with linked PDFs on this same page type; could not confirm the counseling page is populated. Actions before July 2011 by records request. | WordPress, plain links if the list exists. Board covers LPCC, LMHC, LMFT, alcohol/drug counselors. Verified 2026-09-18: page loads (HTTP 200) but is empty: heading and site navigation only, zero PDF links, zero actions, no records-request sentence. The sibling Social Work page has a populated table with 39 text-native order PDFs, so the site format is fine; the counseling board has posted nothing. NOT FEASIBLE; records request only. |
| North Dakota | Board of Counselor Examiners, https://www.ndbce.org/ ("Disciplinary Actions" menu item) | Static site; roughly one action per several years. | Negligible yield. Verified 2026-09-18: the menu item is a single one-page PDF, https://www.ndbce.org/PDFs/Disciplinary%20Actions.pdf (text-native), with 8 rows from 2022 to 2026: name, license number, action date, action label, effective and end dates. No order documents. NOT FEASIBLE for orders; index only. |

## Tier 2: complete index in bulk, but orders require per-licensee lookup

| State | Index source | Where the orders live | Rating |
|---|---|---|---|
| Delaware | Open-data CSV https://data.delaware.gov/api/views/dz6p-akeq/rows.csv?accessType=DOWNLOAD (all DPR disciplinary actions, filterable by profession) | DELPROS (Salesforce, JavaScript-heavy), per name | MODERATE. Same two-step pattern as Colorado but the lookup is harder to automate. |
| Oregon | Cumulative PDF of all actions since 2008, https://www.oregon.gov/oblpct/BoardAction/disciplinary_report.pdf | Licensee Lookup https://www.oregon.gov/mhra/pages/verify.aspx, "Disciplinary Actions" heading per record | MODERATE. Board is LPC/LMFT only. |
| California | BBS recent-actions list https://www.bbs.ca.gov/consumers/enforcement_actions.html | DCA License Search https://search.dca.ca.gov/ per licensee | MODERATE. Large LPCC population; list depth unknown. |
| Alaska | Quarterly all-profession PDFs, predictable URLs https://www.commerce.alaska.gov/web/Portals/5/pub/LicActions{YYYY}Qtr{N}.pdf (2017 on), sectioned by board | Search Professional Licenses portal per licensee | EASY index, MODERATE for orders. Counselor entries 0 to 3 per quarter. |
| Nebraska | Monthly PDFs https://dhhs.ne.gov/licensure/Documents/MM-YYdiscip.pdf, rolling 10-year window, PROFESSION column | LISSearch lookup per licensee | EASY index, HARD for orders. |
| Hawaii | Monthly HTML press releases (cca.hawaii.gov "DCCA Disciplinary Actions Through <Month> <Year>"), MHC case numbers | OAH decisions page http://cca.hawaii.gov/oah/oah_decisions/ | EASY index. A few MHC actions per year. |
| Connecticut | Quarterly HTML Regulatory Action Reports https://portal.ct.gov/dph/regulatory-action-report/regulatory-action-report, LPC entries labeled, 2013 on | eLicense per licensee | EASY index. Summaries are fairly detailed (sanction, penalty, probation terms). |
| New York | Searchable HTML summaries since 1994, https://www.op.nysed.gov/enforcement/enforcement-actions, profession filter, query-string pagination | No order PDFs found | EASY index, no orders. Summaries are one paragraph. |
| Illinois | Monthly all-profession PDFs, https://idfpr.illinois.gov/news/disciplines/discreports.html (files like /forms/discpln/YYYY-MMenf.pdf) | License lookup or FOIA | Summaries only. |
| Michigan | Periodic all-profession Disciplinary Action Reports by fiscal year, https://www.michigan.gov/lara/bureau-list/bpl/health/dar-reports-health/health-license-disciplinary-action-reports | MiCLEAR lookup or FOIA | Summaries only. |
| Massachusetts | BHPL disciplinary collection https://www.mass.gov/collections/disciplinary-actions-taken-by-the-bureau-of-health-professions-licensure, apparently current calendar year | Individual mass.gov/doc downloads exist | MODERATE, unverified depth. |
| South Dakota | Single cumulative PDF https://dss.sd.gov/docs/licensing/counselors/Disciplinary_Actions.pdf with LPC/LPC-MH rows | Not posted online | Index only; orders need a records request. |

## Tier 3: hard or not feasible without a records request

| State | Why |
|---|---|
| Georgia | GOALS "Board Public Disciplinary Actions" is a Salesforce portal (https://goals.sos.ga.gov/GASOSOneStop/s/disciplinary-actions). The SOS "Disciplinary Actions Taken by the Board" PDFs are Nursing, not counseling. |
| Arkansas | No disciplinary list found on ADH, abec.statesolutions.us, or the state portal; per-name lookup only. Was on the handoff candidate list; drop it. |
| Maine | ALMS Online ASP.NET portal (session tokens, postbacks), case documents rendered as HTML. Feasible with browser automation only. |
| Indiana | PLA litigation search (ASP.NET) defaults to last 90 days; documents at viewer.aspx?id=N may be enumerable. |
| Idaho | DOPL disciplinary tool appears portal-driven; public records request as fallback. |
| Montana | License search only; no list. |
| West Virginia | Certemy registry only; no discipline list found. |
| DC | One "Signed Consent Order" PDF linked on the licensing page; otherwise per-licensee lookup. |

## Recommended order of work

1. Kansas. Closest match to the Maryland downloader (letter pages, PDF per order, profession code in the filename). Copy `state_data\Maryland\downloader\` as the starting point.
2. Vermont. Enumerate monthly report PDFs to build the LCMHC name list, then pull decision PDFs from the allied_mental_health folder. Expect OCR on older files.
3. New Hampshire. Small, clean, one afternoon.
4. Iowa. Confirm the per-action pages link order PDFs; if they do, it is Tier 1.
5. Oklahoma and New Mexico. Ten minutes each in a browser will settle whether they are Tier 1 or Tier 2. (Settled 2026-09-18: Oklahoma is Tier 1 via the Thentia register API; New Mexico publishes nothing. See SURVEY_VERIFICATION_OK_NM_NV_ND_2026-09-18.md.)
6. Colorado and Delaware as the first two-step states (roster export, then per-licensee document pull), if the project wants larger western coverage. (Colorado settled 2026-09-18: it is Tier 1, the documents come from DORA's DDMS in one query; downloader built and run. Delaware remains.)

Verification checklist per state (do this in a browser before writing code):
- Open the list URL; count entries and note the date range.
- Click two entries; confirm the link is the order PDF, not a summary.
- Open one PDF; check whether text is selectable (text-native) or a scan (OCR).
- Note whether LPC can be separated by a code, a label, or only by reading the order.
