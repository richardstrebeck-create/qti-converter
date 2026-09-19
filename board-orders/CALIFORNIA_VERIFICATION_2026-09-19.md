# California verification: Board of Behavioral Sciences / LPCC (2026-09-19)

> **Decision 2026-09-19 (Richard): California is SKIPPED.** The project
> collects only orders that a board lists publicly on its website. California
> posts no order documents on a public page; they sit behind a CAPTCHA-gated
> per-licensee search. The API sign-up and the Public Records Act request
> below are recorded for reference and are not being pursued.

Companion to `STATE_SURVEY_2026-09-18.md`, which rated California Tier 2
MODERATE from search-engine snippets ("BBS recent-actions list plus DCA
License Search per licensee"). This pass loaded the live pages from a cloud
session with open network access, paused at least 1.5 seconds between
requests to any state site, and stopped at every CAPTCHA and login. No
order PDF could be sampled: every document link on the state's side sits
behind a Cloudflare Turnstile challenge that this project does not bypass.
No downloader was built (Phase 2 skipped).

## Summary

| Route | URL | What is really there | Result |
|---|---|---|---|
| 1. BBS enforcement page | https://www.bbs.ca.gov/consumers/enforcement_actions.html | One month of names ("Subscriber List Notifications - Enforcement Actions - August 2026"): name, license type, license number, grouped by Citations / Accusations / Decisions / Petitions. No links, no dates, no archive of earlier months. LPCC entries are labeled but rare (0 to 2 a month) | Index only, current month only |
| 2. DCA License Search | https://search.dca.ca.gov/ (and /advanced) | The per-licensee route. The search form is gated by Cloudflare Turnstile (submit button disabled until the challenge passes); detail pages carry an opaque 32-character hash in the URL; document links are /download plus a 200-character token; robots.txt disallows /details/ and /download*. Advanced Search has "Has Discipline = Yes" and "Has Documents = Yes" filters, so a PERSON can list every disciplined LPCC in a browser | Not scriptable; the by-hand route |
| 3. DCA iServices Search API | https://iservices.dca.ca.gov/ (spec at /swagger/spec/search.json, guide at /docs/iservice_user_guide.pdf) | An official, documented REST API for the same data: search by license type with hasDiscipline / hasDocuments flags per licensee, full detail per license number including "public record actions". Needs a self-service account, an application, and approval by DCA's API team (APP_ID and APP_KEY headers). Whether the order PDFs themselves are served through it is not stated in the spec | The scripted route, once the user holds a key |
| 4. Other official routes | BBS board meeting materials, BBS newsletter, DCA Open Data Portal, data.ca.gov, Office of Administrative Hearings, DCA public licensee file, BreEZe | Aggregate enforcement statistics only; no orders anywhere; OAH publishes no general-jurisdiction decisions | Nothing to download |

**Rating: HARD, SKIPPED by decision.** California publishes the full order documents (accusations,
decisions, stipulated settlements) for every disciplined LPCC, but only
behind the DCA License Search, whose search form is a CAPTCHA (Turnstile)
and whose detail and download addresses cannot be derived. The BBS page is
a one-month rolling list of names with no links. The one legitimate scripted
route is DCA's iServices API, which needs a registered, DCA-approved key
that only the user can obtain. Until then the job is by hand, or by Public
Records Act request. Down from Tier 2 MODERATE.

## 1. BBS enforcement pages

`https://www.bbs.ca.gov/consumers/enforcement_actions.html` (HTTP 200,
static HTML, 43 KB). Sections: About, Verify a License (points to
search.dca.ca.gov), Glossary (Accusation, Citation, Effective Decision
Date, Probation, Public Reprimand, Revocation, Stay, Stayed, Suspension,
Voluntary Surrender, Writ of Mandate), Latest Enforcement Actions,
Forms/Pubs. The only PDF links on the page are complaint and reporting
forms, the Disciplinary Guidelines and the statutes book.

"Latest Enforcement Actions" is the text of the Board's monthly subscriber
e-mail for ONE month. On 2026-09-19 it read "Subscriber List Notifications
- Enforcement Actions - August 2026" with 19 names under Citations (6),
Accusations (9), First Amended Accusation (1) and Petition To Revoke
Probation (1): 4 LMFT, 8 LCSW, 2 AMFT, 3 ASW, no LPCC. Each line is
"First Middle Last, TYPE number". No dates, no document links, no case
numbers.

There is no archive of earlier months on the site (no yearly pages, no
"past actions" link; guessed addresses were not tried beyond the site's
own navigation). The Wayback Machine holds captures of the page, and the
same one-month layout goes back at least to November 2017. Captures read
for this pass:

| Capture | Month shown | Names | LPCC / APCC / PCCI entries |
|---|---|---|---|
| 2018-01-07 | November 2017 | 78 | LPCC 2, PCCI 3 (registered intern, old title) |
| 2018-05-22 | April 2018 | 44 | APCC 2 |
| 2020-06-27 | May 2020 | 22 | LPCC 1 (a Decision) |
| 2022-07-01 | May 2022 | 14 | 0 |
| 2024-05-23 | April 2024 | 27 | APCC 2 |
| 2025-05-27 | April 2025 | 9 | APCC 1 |
| 2026-02-21 | January 2026 | 16 | 0 |
| 2026-06-26 | May 2026 | 21 | LPCC 1 (a Citation) |
| 2026-09-19 (live) | August 2026 | 19 | 0 |

**Update 2026-09-19 (later session):** all 78 distinct Wayback captures
(2018-01-07 to 2026-09-10) plus the live page were read and parsed;
the names, per-month counts and caveats are in `california_names/`
(README.txt, bbs_enforcement_all.csv, california_counselor_names.csv,
california_counselor_people.csv): 70 notice months from November 2017 to
August 2026, 73 distinct LPCC/APCC/PCCI people, 36 months with no capture.
The pre-2018 site pages (`/consumer/disciplinary_actions.shtml`, captures
back to 2007) listed no names.

So the BBS list covers all six BBS license types (LMFT, LCSW, LEP, LPCC and
the associate registrations AMFT, ASW, APCC), labels LPCCs clearly, and
yields roughly 5 to 15 LPCC or APCC entries a year. Rebuilding a multi-year
LPCC index from Wayback captures is possible (one capture per month, about
100 requests to archive.org) but gives names only.

The BBS probation page (`/licensees/probation.html`) is a description of
the probation program and its forms; it has no probationer list. The BBS
newsletter (Spring 2026, 20 pages) has no enforcement actions section. The
subscribe page (`/webapplications/apps/subscribe/`) is the Board's own
mailing-list form, not GovDelivery, so there is no public bulletin archive.

## 2. DCA License Search (search.dca.ca.gov)

**The search form.** `https://search.dca.ca.gov/` (HTTP 200) posts to
`/results` with boardCode (Behavioral Sciences = 3), licenseType (Licensed
Professional Clinical Counselor = 221; also 883 and 622 for the temporary
military-spouse LPCC and APCC types), licenseNumber, busName, firstName,
lastName, registryNumber, a csrfToken, cfAction=search and cfMode=managed.
The form carries a Cloudflare Turnstile widget (`cf-turnstile`, site key
0x4AAAAAAB258ZxC1TBrjjzg, action "search"); the SEARCH button is rendered
`disabled` and is enabled only by the widget's success callback, and the
widget's expiry callback disables it again. `/advanced` is the same form
with advBoardCode, advLicenseType, advCity, advCounty, advStatus (46 values
including Accusation Filed, Revoked, Probation), advSecStatus,
**advHasDiscipline (Yes/No)** and **advHasDocuments (Yes/No)**, and the
same Turnstile widget. Because the challenge is a CAPTCHA, no search was
submitted by script. Whether the server would accept a POST without a
token was deliberately not tested.

**Detail pages.** Results link to
`/details/<boardCode>/<licenseTypeCode>/<licenseNumber>/<32 hex characters>`.
The last segment is not the md5 of any obvious combination of the first
three (tested), and a request without it, or with a wrong value, is
redirected to the home page (verified with one barber record whose full
address is public in the Wayback Machine: the correct address returns the
licensee page with no Turnstile; the address without the hash returns the
search home). The Wayback Machine has no capture of any BBS detail page
(`/details/3/...`), so no LPCC detail address is known.

**Documents.** The FAQ says an icon on a result marks records with "public
record or disciplinary actions" and another marks records with "public
documents available". Documents are served from
`https://search.dca.ca.gov/download<about 200 hex characters>` (one such
address is indexed by a search engine). The token is opaque, so documents
cannot be enumerated or guessed.

**robots.txt** on search.dca.ca.gov: `Disallow: /details/` and
`Disallow: /download*`. DCA has explicitly put both the licensee pages and
the documents off limits to crawlers. Combined with the CAPTCHA, this route
is closed to scripts on purpose.

**Enumeration.** There is no public list of disciplined licensees outside
the Advanced Search filters above. DCA's monthly "Public Information" file
(`https://www.dca.ca.gov/consumers/public_info/`, a Box folder with one
file per board: name, license type, number, address, issue and expiry
dates, status) is a full LPCC roster with no discipline flag, so it would
only turn this into a 10,000-page crawl of a site that forbids crawling.
Not pursued.

**BreEZe.** `https://www.breeze.ca.gov/datamart/loginCADCA.do` is the
licensee login and complaint portal ("Please verify you're human" on the
login); its public verification link just goes back to search.dca.ca.gov.

## 3. DCA iServices Search API (the scripted route, key required)

`https://iservices.dca.ca.gov/` is DCA's developer portal (3scale). The
"DCA Search API" specification (`/swagger/spec/search.json`, OpenAPI
3.0.1, production server `https://iservices.dca.ca.gov/api/search/v1`)
covers the BreEZe boards, the Board of Behavioral Sciences among them.
Every call needs `APP_ID` and `APP_KEY` headers. Endpoints:

| Endpoint | What it returns |
|---|---|
| GET breezeDetailService/getAllBoards, getAllLicenseTypes, getRanks; statusListService/getLicenseStatuses; licenseModifierService/getLicenseModifiers | Code tables: boards, license types (client codes), status and secondary-status codes |
| POST licenseSearchService/getPublicLicenseSearch | Limited details; body `searchMethod` = SNDX (name), LIC_NBR (license numbers) or CLNT (client code = license type), with optional statusId, city, county. Each result carries `hasDiscipline`, `hasPublicrecordActions`, `hasDocuments`, primary and secondary status codes |
| POST licenseSearchService/getPublicAgileSearch | Same request, full details |
| GET licenseSearchService/getLicenseNumberSearch?licType=&licNumber= | "Full licensee details - everything that is available on the licensee details web screen": names, addresses, license details with modifiers, `getPublicRecordActions` (display order, action group, action details), plus Medical-Board-only document and psych-site blocks |
| POST commonSearchService/publicLicDelta | Licenses changed since a timestamp, per license type, with the same has-flags |

So the API can (a) list every LPCC with `hasDiscipline` or
`hasPublicrecordActions` true in one CLNT search, and (b) return the public
record actions per licensee. The spec does not show a field that carries
the document file or its address for BreEZe boards (only `getMbcDocument`,
for the Medical Board), so the order PDFs may still have to be fetched from
the web detail page; that is the first thing to test once a key exists.

Getting a key (from the user guide, October 2025): Sign up on the portal
(organization, type of business, address, e-mail), confirm by e-mail,
subscribe to the DCA Search API service, create an application with a
justification of how the data will be used, and wait for approval by DCA's
API team; keys do not work until then. Responses carry `ratelimit-*`
headers. No fee is mentioned. This is a login and an approval, so it was not
attempted from this session.

## 4. Other official routes

- **BBS board meeting materials** (`/about/board_meetings.html`): agendas
  and item PDFs. The quarterly "Enforcement Update" (February 2026, item
  16, 11 pages) gives counts only (complaints received, cases referred to
  the Attorney General, accusations filed, final disciplinary orders,
  probationers), not names or orders. Disciplinary matters are taken in
  closed session; petition items (reinstatement, early termination) are
  listed by name but their material is not posted.
- **DCA Open Data Portal** (`https://www.dca.ca.gov/data/`): aggregate
  Enforcement Performance Measures and Annual Enforcement Statistics as
  CSV/XLSX on Box, per board; no case-level data.
- **data.ca.gov**: no BBS or DCA discipline dataset (catalog searches for
  "behavioral sciences" and "consumer affairs license" return health and
  environment datasets only).
- **Office of Administrative Hearings** (dgs.ca.gov/OAH): publishes a
  decisions search for Department of Developmental Services cases only; the
  proposed decisions in BBS cases are adopted by the Board and released as
  the Board's Decision through the DCA search, not by OAH.
- **Public Records Act**: the fallback for everything (section 6).

## 5. Sample orders

None fetched. Every document address depends on the Turnstile-gated search,
so the text-layer check could not be run. For what it is worth, BBS
Decisions are Attorney General filings and ALJ proposed decisions of the
last decade and are very likely text-native; older stipulations may be
scans. Check with `--text-check` once anything is downloaded.

## 6. What a person can do by hand, and what to ask for

**By hand (browser, no code):**

1. Open `https://search.dca.ca.gov/advanced`, pass the Turnstile check,
   set Board = Behavioral Sciences, License Type = Licensed Professional
   Clinical Counselor, Has Discipline = Yes (a second pass with Has
   Documents = Yes), leave the rest blank, SEARCH. Note the hit count; this
   is the LPCC discipline population.
2. For each result, open MORE DETAILS, read the "Public Record Actions"
   block (action, date, case number) and save every document under
   "Public Documents" (Accusation, Stipulated Settlement, Decision, etc.)
   as `Lastname, Firstname LPCC<number> <effective date>.pdf` into
   `state_data\California\`.
3. Repeat for Associate Professional Clinical Counselor if registrants are
   wanted. LMFT, LCSW and LEP are out of scope.
4. Each month, read the BBS enforcement page (or the subscriber e-mail) for
   new LPCC and APCC names and look them up the same way.

**The API route (needs the user):** sign up at
`https://iservices.dca.ca.gov/`, request an application for the DCA Search
API with a research justification (regulatory study of counselor
discipline across states), and send the approved APP_ID and APP_KEY to the
next coding session. With a key, a downloader in the house style is
straightforward: one CLNT search for license type 221 to get every LPCC
with `hasDiscipline` true, one getLicenseNumberSearch per hit for the
public record actions, then the document files, from the API if it serves
them, otherwise from the detail page addresses the API returns (to be
confirmed). Rate limits apply; keep the 1.5 s pause.

**Public Records Act request** (to the Board of Behavioral Sciences, 1625
North Market Blvd., Suite S-200, Sacramento, CA 95834; the Board's PRA
contact is on bbs.ca.gov under Contact Us). Ask for, in electronic form:

1. A list of all Licensed Professional Clinical Counselors and Associate
   Professional Clinical Counselors against whom the Board has taken a
   public disciplinary action or issued a citation since the LPCC license
   was created (Business and Professions Code section 4999.10 and
   following; first licenses issued 2012), giving name, license or
   registration number, case number, action type, and effective date.
2. Copies of the public disciplinary documents for each such matter:
   Accusation (and amended accusations), Statement of Issues, Stipulated
   Settlement and Disciplinary Order, Decision and Order (including the
   ALJ proposed decision where adopted), Default Decision, Petition to
   Revoke Probation, Citation and Order, and any order of surrender,
   probation modification or termination.
3. The Board's current disclosure policy for how long citations and
   disciplinary actions remain posted on the DCA License Search, so the
   dataset can record what has aged off.

Cite the California Public Records Act (Government Code section 7920.000
and following) and Business and Professions Code section 4990.20 (public
records of Board actions). Expect the Board to point to the DCA License
Search first; the request should say that the search cannot be used in
bulk and that a list plus copies is being requested under the Act.

## 7. What was NOT done and why

- No search was submitted to search.dca.ca.gov (CAPTCHA).
- No account was created on iservices.dca.ca.gov (login and approval that
  belong to the user).
- No PDFs downloaded, so nothing was added to branch `board-orders-data`.
- `california_downloader\` was not built; a skeleton would have nothing
  to fetch until a key exists.
