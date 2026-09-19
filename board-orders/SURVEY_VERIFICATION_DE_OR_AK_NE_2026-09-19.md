# Delaware, Oregon, Alaska, Nebraska: verification against the public-listing rule (2026-09-19)

Companion to `STATE_SURVEY_2026-09-18.md`, which put all four in Tier 2
("complete index in bulk, but orders require per-licensee lookup").
Checked live from a cloud session, at least 1.5 seconds between requests
to any state site, no CAPTCHA or bot wall bypassed, no login.

The rule applied (Richard, 2026-09-19): the project collects only order
documents that the board makes publicly available on its own website and
that a script can reach without a CAPTCHA, a login or a bot wall. An index
of names without the orders does not qualify.

## Summary

| State | Index (names, actions, dates) | Order documents | Scriptable? | Rating | Decision |
|---|---|---|---|---|---|
| Delaware | Open Data Portal CSV, all DPR boards, 1997 to 2025; 33 Professional Counselors of Mental Health with 69 action rows | On DELPROS (Salesforce): each license record lists its Board Orders with public file links | Index yes; per-licensee document list yes (JavaScript remoting, no CAPTCHA); the file download itself runs through a Salesforce viewer and was not reproduced by script in this pass | MODERATE | Qualifies. Small (about 30 to 40 documents). Build once the download step is solved, or fetch by hand |
| Oregon | None posted: the cumulative disciplinary_report.pdf is gone (404 live and in the archive); the Compliance page sends readers to the licensee lookup | On the Thentia register (oblpct.us.thentiacloud.net), per licensee: Notice of Proposed Action, Default Order, Stipulated Order, Bill of Costs as PDF attachments | Yes: the register's REST layer answers plain GETs (same design as Oklahoma); one order downloaded (8-page scan). The catch is enumeration: the search results omit the notices, so finding every disciplined LPC means one record call per LPC and associate (about 19,500 calls, 8 to 11 hours at 1.5 s), or a partial run on the Revoked, Surrendered and Suspended statuses (114 people) | MODERATE | SKIPPED by decision 2026-09-19 (Richard): the orders are reachable but only by opening every one of about 19,500 records, and the board posts no list. Not being pursued |
| Alaska | Quarterly "Disciplinary Action Report" PDFs, all boards, one paragraph per action, 2017 on; counselor section labeled "PCO - Board of Professional Counselors" | Per licensee on the Professional License Search, "for certain programs" | No: the whole commerce.alaska.gov host answers scripts with a DataDome bot challenge (HTTP 403, "Please enable JS"); the PDFs are readable only through the Wayback Machine | NOT FEASIBLE by script | Skip. Index only, and only by archive |
| Nebraska | Monthly and rolling ten-year PDFs, all professions; "Mental Health Practitioner" rows labeled (23 in the 2016 to 2026 file) | Per licensee in the License Information System (LIS) record, "Disciplinary/Non-Disciplinary Information" | No: the LIS search form carries a Google reCAPTCHA | NOT FEASIBLE by script | Skip. Index only |

## 1. Delaware

**Board page.** `https://dpr.delaware.gov/boards/profcounselors/` (Board of
Mental Health and Chemical Dependency Professionals) has no actions list.
Its "Disciplinary Action Information" page
(`https://dpr.delaware.gov/disciplinary-action-information/`) says it
plainly: the list of actions is on the Open Data Portal, and "Board Orders
are available from the license details page" on DELPROS: click the license
number, View More Info, scroll to Discipline, click the Board Order
documents.

**Index.** `https://data.delaware.gov/api/views/dz6p-akeq/rows.csv?accessType=DOWNLOAD`
(Disciplinary Actions for Professional and Occupational Licensees; 911 KB,
8,483 rows, columns Last Name, First Name, Combined Name, License_no,
Profession ID, License Type, disciplinary_action, disp_start, disp_end,
Count). Profession ID "Mental Health" has 79 rows: Professional Counselor
of Mental Health 69 (33 people, license numbers PC-0000043 style), Chemical
Dependency Professional 5, Marriage and Family Therapist 5. LPCMH action
rows by type: Letter of Reprimand 21, Probation 14, Suspension 12, Remedial
Education 11, Revocation 6, Fine 2, Stayed Suspension 1, Cease and Desist
1, Refer to Disciplinary Order 1. Start dates 1997 to 2025, most between
2009 and 2017. Several rows per person are one order (reprimand plus
probation plus education on the same date).

**DELPROS.** `https://delpros.delaware.gov/OH_VerifyLicense` is a
Salesforce Visualforce page with no CAPTCHA. Its search runs through
Visualforce JavaScript remoting (`POST /apexremote`, controller
`OH_VerifyLicenseCtlr`, methods `findLicensesForOwner`, `getSubmissionList`,
`fetchmetadata`; the per-method CSRF and authorization tokens are printed
in the page and are reusable for the session). Verified with one search
(last name Hicks, first name Joseph, searchType individual): three
licenses came back, one of them the LPCMH record PC-0000043 with
`Board_Action__c = Yes` and the Salesforce license id. `getSubmissionList`
on that id returned three documents:

| Name | Description | Link |
|---|---|---|
| Hicks, Joseph CA 2021 | Consent Agreement for Joseph B Hicks | dedpr.my.salesforce.com/sfc/p/C00000016khO/a/8y000000hRwT/... |
| 15-Hicks-Joseph-Discipline-2009.pdf | Disciplinary Order 2009 | dedpr.my.salesforce.com/sfc/p/C00000016khO/a/t0000000vSBU/... |
| 15-Hicks-Joseph-Disciipline-2010.pdf | Disciplinary Order 2010 | dedpr.my.salesforce.com/sfc/p/C00000016khO/a/t0000000vSQs/... |

That matches the open-data rows (2009, 2010, 2021 actions). So the
documents are public, listed per licensee, and reachable without a
CAPTCHA.

**The download step.** The links are Salesforce "content delivery" pages,
not files. A GET returns a page that posts itself back to `/sfc/p/`, and
the reply is a viewer that loads a Lightning component to show and
download the file. The classic download address
(`/sfc/dist/version/download/?oid=00DC00000016khO&ids=05Dt0000000vSBU&d=/a/...&asPdf=false&operationContext=DELIVERY`)
and two variants answered HTTP 200 with an empty JSON body, and the
Lightning delivery page (`/sfc/ld/...`) answered "We couldn't access the
content delivery". The viewer needs the content-version id that the
Lightning component fetches with its own call, which was not reproduced.
In a browser, "View" opens the PDF. So the last step needs either a
headless browser or one more look at the Lightning call, or a person
saving about 30 to 40 files by hand.

**Rating: MODERATE.** Qualifies under the rule (orders public on the
board's own licensing site, no CAPTCHA). The catch is the file transfer,
not access. Not built in this pass.

## 2. Oregon

**Board site.** `https://www.oregon.gov/oblpct/` no longer has a Board
Actions page. The survey's cumulative report
(`/oblpct/BoardAction/disciplinary_report.pdf`) is 404 live and the Wayback
Machine holds no copy. The Compliance page
(`/oblpct/Pages/Compliance.aspx`) says: "To search for Board actions
regarding licensed professional counselors (LPCs), licensed marriage and
family therapists (LMFTs), or registered associates, please use our
Licensee Lookup. Documents are available under the 'Disciplinary Actions'
heading within the person's record." A table of actions against
unlicensed persons sits on the same page, and "Contact us for a list of
Board disciplinary actions with summaries."

**The register.** `https://oblpct.us.thentiacloud.net/webs/oblpct/register/`
is a Thentia register, the same product Oklahoma uses, with a public REST
layer that answers plain GETs (no CAPTCHA, no session):

| Call | What it returns |
|---|---|
| `/rest/public/registrant/search/?keyword=&supervisor=&filter=all&skip=0&take=500&dsrList=` | Paged list of every registrant: 24,798 on 2026-09-19 (LPC 10,309; Professional Counselor Associate 9,007; LMFT 3,215; MFT Associate 1,938; limited permits 328). Fields: id, name, license number, category, status, city, expiry. The `publicNotices`, `registrationRecords` and `memberships` fields come back EMPTY in search results |
| `keyword=Revoked` (or Surrendered, Suspended) | The search matches status words: Revoked 57, Surrendered 53, Suspended 4 (114 people). Probation and reprimand are not statuses, so this misses them |
| `dsrList=true` | 285 supervisors approved for disciplinary supervision, not disciplined licensees |
| `/rest/public/registrant/get/?id=<id>` | One full record with `registrationRecords` (status history with dates) and `publicNotices`: notice type, effective date, case-number summary, and `attachments` with the file name and a 160-character attachment id |
| `/rest/public/annotation/download/index.php?id=<attachment id>&entity=<effi_entity>` | The PDF, plain GET, `application/pdf` |

Verified on two records: LPC C6554 (revoked 2024-06-13) has three notices,
Notice of Proposed Action 2023-10-31, Default Order 2024-06-13, Bill of
Costs 2024-07-09, each with one PDF; LPC C5496 (suspended 2026-02-10) has
three notices starting with a Notice of Proposed Action 2025-12-08. The
first PDF (Adkisson, NPDA, 1.5 MB) downloaded correctly: 8 pages, 0
characters of text, an image scan. File names follow
`Last.First_case_TYPE_date.pdf` (NPDA, DO, BoC, and presumably SO for
stipulated orders).

**Enumeration.** Because the search omits the notices, the only way to
find every disciplined LPC is to call `get` for each LPC and associate
(about 19,500 calls; 8 to 11 hours at one call every 1.5 seconds), or to
take the status shortcut (114 people) and miss probations and reprimands
on active licenses. `get` does not accept several ids at once (HTTP 500).

**Rating: MODERATE, Tier 1 by the rule** (orders public on the board's
licensee lookup, script-reachable without a CAPTCHA), but **SKIPPED by
decision 2026-09-19 (Richard)**: with no posted list, the only complete
route is a sweep of about 19,500 records (8 to 11 hours), and the
status-only shortcut misses probations and reprimands. Not being pursued.
If it is ever reopened: ask the Board for its "list of Board disciplinary
actions with summaries" first, then build in the Oklahoma shape with a
status-only quick mode and a resumable full sweep. Expect scans (OCR).

## 3. Alaska

**Index.** The Division of Corporations, Business and Professional
Licensing publishes a quarterly "Disciplinary Action Report" for every
board: `https://www.commerce.alaska.gov/web/Portals/5/pub/LicActions{YYYY}Qtr{N}.pdf`
(annual files for 2017 to 2019, quarterly from 2020 Q1 to 2026 Q1, 28
files in the Wayback Machine). Each action is a block: name, profession,
license number, board action (Consent Agreement, Order, Surrender), case
number, action date and a one-paragraph "Reason for Action" summary. The
2025 Q4 file (17 pages, text-native) has a "PCO - Board of Professional
Counselors" section with two consent agreements. Each page ends: "Copies
of disciplinary actions on professional licenses are available online for
certain programs at https://www.commerce.alaska.gov/cbp/main/Search/Professional.
Uploading this information to our web site may take up to 60 days."

**Bot wall.** Every request from this session to commerce.alaska.gov,
including the board page and the quarterly PDFs, answered HTTP 403 with a
DataDome challenge page ("Please enable JS and disable any ad blocker").
DataDome is a bot-detection service; it was not bypassed. The PDFs were
read from the Wayback Machine instead. The Professional License Search,
where the order copies sit per licensee, has no archive captures and is
behind the same wall.

**Rating: NOT FEASIBLE by script.** The index is good and public; the
orders are per-licensee behind a bot challenge. Skip. A person can open
the quarterly PDFs and the license search in a browser (a few counselor
actions a year).

## 4. Nebraska

**Index.** DHHS Licensure Unit, "Disciplinary Actions Against Health Care
Professionals and Child Care Providers"
(`https://dhhs.ne.gov/licensure/pages/disciplinary-actions-against-health-care-professionals-and-child-care-providers.aspx`):
a rolling ten-year PDF (`August16-26discip.pdf`, 270 pages) plus the last
three monthly files (`MM-YYdiscip.pdf`), and the same pair for voluntary
surrenders. Columns: profession, license type, name, license number, city,
type of action, violation section, start and end dates. "Mental Health
Practitioner" and "Independent Mental Health Practitioner" rows are
labeled (23 in the ten-year file; Nebraska has no LPC title, the LIMHP /
LMHP is the counterpart). Every page says: "To review the disciplinary
action document for any licensee on this report, you may go to our license
lookup web site ... The disciplinary action documents are located in the
'Disciplinary/Non-Disciplinary Information' section of the licensee's
record."

**Documents.** `https://www.nebraska.gov/LISSearch/search.cgi` loads
(HTTP 200) but its search form carries a Google reCAPTCHA
(`g-recaptcha-response`). Not submitted.

**Rating: NOT FEASIBLE by script.** Index only. Skip. A person can look up
the 23 names in LIS by hand.

## 5. What was not done

- No CAPTCHA, bot challenge or login was bypassed (Alaska DataDome,
  Nebraska reCAPTCHA).
- No downloader was built. Delaware qualifies and its file-download step
  is still open. Oregon qualifies on access but is skipped by decision
  because of the record sweep it would need.
- Nothing was added to branch `board-orders-data`.
