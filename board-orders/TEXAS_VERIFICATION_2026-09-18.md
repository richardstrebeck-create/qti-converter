# Texas verification: BHEC / State Board of Examiners of Professional Counselors (2026-09-18)

Companion to `STATE_SURVEY_2026-09-18.md`, which rated Texas Tier 3 ("lookup
portal only") from search-engine snippets. This pass loaded the live pages
from a cloud session with open network access, paused at least 1.5 seconds
between requests, and tried a handful of lookup searches only. Where a route
yielded documents, at most three samples were checked with PyMuPDF before the
downloader was built; the downloader was then run in full (Phase 2).

## Summary

| Route | URL | What it really is | Orders? | Rating |
|---|---|---|---|---|
| 1. bhec.texas.gov enforcement list | https://bhec.texas.gov/tbhec/discipline-and-complaints/ and sub-pages | Process description only; no list of actions, no names, no order links anywhere on the site | No | Not a route |
| 2. HPC datamart lookup | https://vo.licensing.hpc.texas.gov/datamart/selSearchType.do | Tyler Technologies form app; every search POST must carry a Google reCAPTCHA Enterprise token; scripted and headless-browser searches are refused | Per licensee, browser only; could not verify | NOT FEASIBLE for bulk |
| 3. Council meeting materials | https://bhec.texas.gov/tbhec/important-dates/past-council-meeting-dates/ | 17 packets (Oct 2021 to Jun 2026); each carries the quarter's signed Agreed Orders, sorted by profession, with a bookmark or a file per licensee | YES, full orders | EASY to MODERATE (built and run) |
| 4. Texas Register, AG, open records, data.texas.gov | see section 4 | Nothing published; open records is the only route for pre-2021 and contested-case orders | No | Fallback only |

**Final rating: MODERATE.** Route 3 is an enumerable index and a direct
document source that needs no browser, login or captcha: 172 LPC agreed
orders for 166 people (June 2021 to May 2026) were downloaded with 0
failures. It is not EASY because the orders are image scans (161 of 171
files need OCR), the packet format changed three times (per-licensee files
since 2024, bookmarked combined PDFs in 2023, bookmarked packet sections in
2021 to 2022, one 2022 packet without bookmarks), it covers agreed orders
only (no default or SOAH orders), and nothing before June 2021 is online.
The survey's Tier 3 rating was wrong: Texas moves to Tier 1.

## 1. BHEC website (Texas State Board of Examiners of Professional Counselors)

Pages loaded (all HTTP 200, WordPress): the home page, the LPC board page
(`/texas-state-board-of-examiners-of-professional-counselors/`),
`/tbhec/discipline-and-complaints/`, `/tbhec/discipline-and-complaints/resolution-of-a-complaint/`,
`/tbhec/verify-a-license/`, `/tbhec/open-records/`, `/tbhec/council-and-board-meetings/`,
`/tbhec/news/`, the upcoming-dates pages for the Council and the LPC board,
and the past-meetings pages for both. The LPC board's "News and Updates"
link (`/texas-state-board-of-examiners-of-professional-counselors/news-and-updates/`)
is a 404.

What is there: the discipline pages describe the complaint process
(priority system, informal settlement conference, Disciplinary Review
Panel, agreed orders, SOAH) and nothing else. The news feed (Nov 2024 to
Sep 2026) is rule adoptions, CE Broker notices, surveys and webinars; no
enforcement press releases. No page on the site lists enforcement actions,
agreed orders or licensee names, and the raw HTML of these pages contains
no PDF links to orders. The rule that the board "publicizes enforcement
actions on its website" is satisfied, in practice, only by the lookup
portal (route 2) and by the meeting packets (route 3).

Two useful things on `/tbhec/verify-a-license/`:

- It states how discipline is shown in the lookup: "If a licensee has a
  publicly available disciplinary history the search results will contain a
  section entitled Reports Available for Download. This section will
  contain a link to any disciplinary action taken against the licensee."
- Downloadable licensee lists, refreshed every 24 hours:
  https://www.bhec.texas.gov/csv/LPC.csv (also PSY.csv, MFT.csv, SW.csv).
  Plain CSV, no login, 5.5 MB. On 2026-09-18: 43,924 rows (36,214 LPC,
  7,710 LPCA), with columns LIC_TYPE, RANK, LIC_NBR, ENTITY_NBR, names,
  LIC_STATUS, LIC_EXPR_DTE, RANK_EFCT_DTE, **DISCPL_ACTN** (Yes/No), address
  and phone where public. 301 rows are flagged Yes (296 LPC, 5 LPCA; by
  status: 257 Active, 25 Probated/Suspended, 9 Delinquent, 6 Suspended, 4
  Inactive). This is a free index of every currently licensed counselor with
  a public disciplinary history, but it covers current licensees only
  (revoked, surrendered and expired people are absent), gives no dates and
  no document, and the LPC.csv row carries no link to the order. The
  downloader uses it to cross-check names and fill in license numbers; 104
  of the 301 flagged people have an order in the packets, which is
  consistent with the packets starting in mid-2021 and most flagged
  histories being older.

## 2. Public License Search (HPC datamart)

URLs: https://vo.licensing.hpc.texas.gov/datamart/selSearchType.do (the
menu) and mainMenu.do (redirects to staff/login.do; the public entry is
selSearchType.do). Tyler Technologies "Version 2.11.10.999", shared by
eight Texas boards (BHEC is boardId 520).

How a search is submitted (read from the served forms):

- A session cookie `JSESSIONID` (path /datamart, 90-minute timeout) is set
  on the first page load. Opening a search form without first loading
  selSearchType.do returns "Timeout Error: Your session has expired".
- Menu links: `searchByName.do`, `selLicType.do?type=name` (search by
  name within one license type), `searchByLicNumber.do`,
  `selLicType.do?type=city`, `selLicType.do?type=county`.
- `searchByName.do` POST fields: `searchType=name`, `selector=false`,
  `indOrgInd=I`, `surname` (at least 2 characters), `firstName`,
  `organizationName`, `pageSize` (5/10/20/30), `g-recaptcha-response`,
  and the submit name (`search`). No wildcard syntax is documented; the
  two-character minimum suggests prefix matching, which could not be tested.
- `searchByLicNumber.do` POST fields: `searchType=licNumber`,
  `boardId=520`, `licTypeId`, `licNumber`, `pageSize`, `g-recaptcha-response`,
  `search`. Choosing a board reloads the form (a POST without a token) to
  fill the license-type list; for BHEC the types are 5261 "Professional
  Counselor", 5262 "Marriage and Family Therapist", 5201/5202 Psychology,
  5272/5273 Social Worker. The same list comes back from a plain POST to
  `selLicType.do` with `boardId=520`, so the license-type filter itself is
  reachable without a captcha.
- There is no filter for "has disciplinary action"; discipline appears
  only on the licensee's detail page.

The blocker: every search form loads
`https://www.google.com/recaptcha/enterprise.js?render=6Lf1h84pAAAAAASnEA-aJTypA2bRKOg9U34Ztwiu`
and the page's submit handler calls `grecaptcha.enterprise.execute(...,
{action: 'search'})` and posts the token in `g-recaptcha-response`. The
server checks it: a POST without a token returns the form again with
"Google reCAPTCHA verification failed, please try again later." (tested for
a name search and a license-number search). A headless Chromium on the cloud
host (Playwright) obtained real tokens (about 2,300 characters) from Google,
but the datamart rejected them the same way, from inside the browser and
when replayed with curl on the browser's session: reCAPTCHA Enterprise is
score-based, and a headless browser on a data-centre address scores too
low. Six searches were attempted in total; none returned a result list.
No JSON, REST or other data layer was found: the app's only scripts are
jQuery, jQuery UI, a session-timeout timer and `common.js`, and the results
and detail pages are server-rendered form posts.

Could not verify: the detail-page URL pattern, whether "Reports Available
for Download" links are direct PDF URLs that work without the captcha, how
many documents a licensee record carries, and how far back they go. A
person can do a search by hand in a normal browser (the site says "it is
not necessary to register or login"); a script cannot.

**Rating for route 2: NOT FEASIBLE for bulk collection.** It remains the
only online place for per-licensee history before mid-2021 and for
contested-case (SOAH) orders.

## 3. Council meeting materials (the route that works)

Index page: https://bhec.texas.gov/tbhec/important-dates/past-council-meeting-dates/
(the survey's link `/past-council-meeting-dates/` redirects there). Static
HTML: a date heading ("June 16, 2026") followed by one link "Agenda &
Public Meeting Materials" per meeting. On 2026-09-18: 18 meetings listed,
17 with a file (November 2020 links to "#"). Files:

| Meeting | File | Size | Agreed-orders format |
|---|---|---|---|
| 2021-10-26 | BHEC-2021October-Agenda_Public-Meeting-Materials.pdf | 115 MB | packet PDF, bookmark section "3.e LPC Agreed Orders" with a bookmark per licensee (26 LPC) |
| 2022-02-01 | 20220201-BHEC-Public-Meeting-Materials.pdf | 38 MB | same, "3.e FY2022 Q1 LPC Agreed Orders" (6 LPC) |
| 2022-05-18 | BHEC-20220518-meeting-materials.pdf | 18 MB | broken bookmarks (only the SW orders are bookmarked); the LPC, MFT and PSY orders are unbookmarked pages 28 to 36 |
| 2022-08-23 | BHEC_PublicMeetingMaterials_20220823.pdf | 50 MB | "3.e FY22 Q3 LPC Agreed Orders" (8 LPC) |
| 2022-10-25 | 2022-10-25-Public-Meeting-Materials.pdf | 44 MB | "3.e FY22 Q4 Agreed Orders for LPC Board" (10 LPC) |
| 2023-01-31, 05-23, 08-15, 10-24 | ...zip | 26 to 92 MB | zip with folder "3.e FY2023 Qn Agreed Orders and Dismissals": one combined PDF per profession ("LPC Q3 FY23 Agreed Orders.pdf") with a bookmark per licensee (10, 9, 14 and 5 LPC); the Q4 file has two bookmarks without page numbers |
| 2024-02-20 to 2026-06-16 (8 packets) | ...zip | 27 to 109 MB | zip with folder "4.e FY20nn Qn Agreed Orders and Dismissals" and sub-folders LPC, LMFT, PSY, SW, one PDF per licensee ("Joslin, Gene AO.pdf"); the June packets carry two quarters each |

Each packet also holds the quarter's dismissals (a docx or xlsx table of
complaint numbers by classification and reason, no names) and a quarterly
enforcement status report (counts only). The agenda item is always "Agreed
Orders and Dismissals for the fiscal-quarter", so the packets are a
complete index of AGREED orders from FY21 Q4 (June to August 2021)
onward, reported about six weeks after each quarter. Default orders and
SOAH final orders are not in them (the LPC board's own agenda item 9.a
"contested cases from SOAH" has no attachments).

The LPC board's own meeting packets (e.g. JANUARY-31-2025-Public-Meeting-Materials-Revised.pdf,
75 pages, half of them images) carry only an "Enforcement Report" of charts
(pending complaints by fiscal year, classifications) and no names or
orders. They are not an index.

Text layer: the orders are scans. Of the three Q4 FY25 samples (Allen,
Cavazos, Henderson: 3 pages each, 1 to 3 MB) all had 0 characters of text;
the combined FY23 Q1 LPC file (40 pages) had 0 characters; the 2022-10
packet's LPC section had one OCR'd page out of 33. After the full run,
`--text-check` on all 171 files: 10 text-native, 161 image-only. Each order
is 3 to 6 pages: caption ("IN THE MATTER OF <NAME>, COMPLAINT NO.
2025-00247, BEFORE THE TEXAS BEHAVIORAL HEALTH EXECUTIVE COUNCIL, THE
TEXAS STATE BOARD OF EXAMINERS OF PROFESSIONAL COUNSELORS"), Findings of
Fact (license number in finding 1), Conclusions of Law, Order, signatures.
"Agreed Order for Eligibility" (applicants and lapsed licensees) uses the
same layout.

Blocking: none. Plain WordPress uploads, HTTP 200 with a browser user
agent, no captcha.

## 4. Other official routes

- **Texas Register** (sos.texas.gov / texreg): a web search for BHEC agreed
  orders in the Register finds only rule notices and law-firm pages. BHEC
  files its open-meeting notices there (the site says so), not its orders.
  Not a route; could not verify beyond a search.
- **Attorney General**: the OAG represents BHEC at SOAH but does not publish
  BHEC orders. Not a route.
- **Open records**: https://bhec.texas.gov/tbhec/open-records/ gives the
  Public Information Act contact (Open.Records@bhec.texas.gov, fillable
  request form). It also notes that current complaint and investigation
  status and dismissed complaints are not released. This is the only route
  for orders before June 2021, for default and SOAH orders, and for the
  detail-page documents the datamart holds.
- **data.texas.gov**: the Socrata catalog search
  (`/api/catalog/v1?q=disciplinary counselor`, `q=behavioral health
  executive council`) returns nothing from BHEC; the only occupational
  discipline sets are other states' (Delaware). Not a route.

## 5. Phase 2: downloader built and run

`board-orders/texas_downloader/` (download_texas_orders.py, README.txt,
Run_Texas_Downloader.cmd, manifest.csv, download_log.csv). Standard library
plus requests and PyMuPDF (needed to split the bookmarked PDFs). Steps:
LPC.csv for name cross-checks; the meetings page for the packet list; one
download per packet; extract, split or copy the LPC orders; drop LMFT, PSY,
SW with the reason recorded. `--list-only`, `--keep-packets`, `--refresh`,
`--text-check`; skip-if-present; a `packet_index.json` cache so a re-run
fetches only packets whose orders are missing.

Run 2026-09-18 (`--list-only --keep-packets`, then the full run):

| Item | Count |
|---|---|
| Packets read | 17 (2021-10-26 to 2026-06-16), 0 failed |
| LPC order files written | 171 for 166 people (172 orders: one file holds two, see below), 0 failed |
| Quarters covered | FY21 Q4 to FY26 Q3 (19 quarters; FY22 Q2 only in the review file); 3 to 26 orders per quarter |
| Review | 1 file: the unbookmarked pages 28 to 36 of the May 2022 packet (FY22 Q2), starting with an LPC order (Cynthia Kay) followed by MFT and PSY orders; split by hand after OCR |
| Dropped | 119 manifest entries for other professions, never extracted: 97 per-licensee files (LMFT 21, PSY 16, SW 60), 10 combined 2023 files and 12 bookmarked 2021 to 2022 packet sections (holding 36 more orders between them) |
| Text layer | 10 text-native, 161 scans (Foxit OCR needed) |
| Names cross-checked | 105 of 171 matched a current licensee (license number filled in; 3 LPC Associates); 97 of those are flagged Discpl_Actn=Yes, 8 No (eligibility orders); 8 names match several licensees; 4 bookmarks carry a surname only |
| Size delivered | 436 MB (largest file 7.3 MB; none near the 95 MB limit) |

Name order: 77 bookmarks are written "First Last" without a comma; they are
turned round, one ("Howson Heather") by frequency of the words as first and
last names in LPC.csv, one ("FRANK DEL RIO") by keeping the particle with
the surname. The Q4 FY23 combined file had two bookmarks without page
numbers, so "Luongo, Eric" took pages 1 to 3 (inferred) and "Pruitt,
Jennifer + Ripstra, Leeann FY23Q4 2023-10-24.pdf" holds two orders.

Delivered on branch `board-orders-data`, folder `Texas/` (171 PDFs,
`review/` with 1 PDF, `downloader/manifest.csv` and `download_log.csv`),
one commit of 175 files; README_DATA.md has a Texas section and a counts
row. No PDFs on the working branch.

What the user must still do:

1. Unpack `Texas/` from the data-branch zip into `state_data\Texas\`.
2. Foxit OCR the Texas folder (161 scans) and the review file.
3. Split by hand the Pruitt + Ripstra file and the review file (keep the
   "PROFESSIONAL COUNSELORS" pages as "Kay, Cynthia FY22Q2 2022-05-18.pdf").
4. `make_text_sidecars.py --states Texas`, register Texas in
   `board_order_extractor.py`, run the extractor. LPC Associates are not
   marked in file names; the order text says "professional counselor
   associate" where it applies.
5. For orders before June 2021 and for contested-case orders, send a Public
   Information Act request to Open.Records@bhec.texas.gov (the LPC.csv
   Discpl_Actn flag gives 301 currently licensed names to ask about, 197 of
   whom have no order in the packets).
6. Re-run the downloader after each Council meeting (February, June and
   October); only the new packet is fetched.
