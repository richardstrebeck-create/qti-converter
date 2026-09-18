# Survey verification: Oklahoma, New Mexico, Nevada, North Dakota (2026-09-18)

Companion to `STATE_SURVEY_2026-09-18.md`, which rated these four from
search-engine snippets only. This pass loaded the live pages from a cloud
session with open network access, pulled at most three sample PDFs per
state (deleted afterwards), and paused at least 1.5 seconds between
requests. No downloader was built. The Wayback Machine returned HTTP 429
(rate limited) for every request during this session, so no archived
copies could be checked; nothing below depends on one.

## Summary

| State | Working URL | What is there | Entries / range | Counselor separation | Order PDFs | Text layer | Rating |
|---|---|---|---|---|---|---|---|
| Oklahoma | Thentia register JSON, https://obbhl.us.thentiacloud.net/rest/public/profile/search/?keyword=&skip=0&take=2000&disciplined=true&profession=Licensed%20Professional%20Counselor%20(LPC)&lang=en-US | Per-licensee "Public Notices" with Consent Order / Final Order PDF attachments, all reachable through the register's own REST calls without a browser or login | 186 disciplined licensees, 144 LPC; notices from 1999 to 2026-08; attachments only on notices from about 2021 on | Yes, `profession` filter and `registrationCategory` field | Yes, signed download link per attachment | Scans, 0 characters of text in 3 of 3 samples (OCR needed) | EASY (two-step JSON crawl, then OCR) |
| New Mexico | https://www.rld.nm.gov/boards-and-commissions/individual-boards-and-commissions/counseling-and-therapy-practice/discipline-and-enforcement/ | Page exists but is empty: heading and site navigation only | 0 | n/a | None | n/a | NOT FEASIBLE (nothing published; records request only) |
| Nevada | https://www.marriage.nv.gov/services/disciplinary-actions/ | Text-only list: name, license number, complaint number, action type, date | 37 licensees, 2012 to 2026; 10 CPC, 27 MFT | Yes, complaint numbers carry MFT or CPC and CPC license numbers start with CP or CI | None (no links on the page) | n/a | NOT FEASIBLE for orders; the index is trivially copyable |
| North Dakota | https://www.ndbce.org/PDFs/Disciplinary%20Actions.pdf | One-page PDF table: license number, board action date, action, effective and end dates, names | 8 rows, 2022 to 2026 | Board is counselors only | None | Text-native (746 characters) | NOT FEASIBLE for orders; index of 8 rows |

Net effect on the survey: Oklahoma moves up to Tier 1 (the survey had it
in Tier 2 as "unverified"). New Mexico, Nevada and North Dakota drop out of
Tier 1 to index-only or nothing.

## 1. Oklahoma, State Board of Behavioral Health Licensure

**Where the orders live today.** The legacy page
`https://www.ok.gov/behavioralhealth/License_Verification.html` no longer
exists; it redirects (HTTP 200 after redirect) to
`https://oklahoma.gov/behavioralhealth.html`, a new oklahoma.gov site with
no disciplinary list at all. Its only relevant links are "Licensee Search"
and "Applicant Portal", both pointing to the Thentia register at
`https://obbhl.us.thentiacloud.net/webs/obbhl/register/`. The complaint
page, board-meetings page (agendas and minutes back to 2023 as PDFs) and
forms page carry no order documents. The "Disciplinary Licensee" lists the
survey described are gone.

**The Thentia register is an AngularJS app, but its data layer is open.**
The HTML shell (2.6 KB) renders nothing without JavaScript. The app's own
REST calls, however, answer plain HTTP GET requests with JSON and need no
session, token or browser:

- Search: `https://obbhl.us.thentiacloud.net/rest/public/profile/search/?keyword=<text>&skip=<n>&take=<n>&lang=en-US`.
  `take=2000` works; `skip` pages through the results (tested at 0, 2000,
  8000, 10000, 14000). The `resultCount` field is capped at 10000, so page
  until a short page comes back. Extra parameters taken from the app's
  search route also work: `disciplined=true` and `profession=<category>`.
  - `keyword=&disciplined=true` returned 186 records, every one with
    `hasPublicNotices: true` (LPC 144, LMFT and LBP and LPC Candidate for
    the rest).
  - Adding `profession=Licensed Professional Counselor (LPC)` returned the
    144 LPC records only. Statuses among them: Active 47, Revoked 44,
    Permanently Expired 27, Inactive 10, Retired 9, Expired 3, blank 3,
    Deceased 1.
  - `suspended=true` returned 0 records (the flag exists but nothing is
    tagged).
- Profile: `https://obbhl.us.thentiacloud.net/rest/public/profile/get/?id=<id>&lang=en-US`
  returns the licensee with `registrationHistory` and `publicNotices`. Each
  notice has `noticeType` (always "Disciplinary Finding" in the sample),
  `effectiveDate`, an HTML `summary` (one sentence, e.g. "Board accepted
  Consent Order to voluntarily surrender license 4-7-2023") and an
  `attachments` array.
- Attachment download (pattern read from the app's `profile.php`
  template): `https://obbhl.us.thentiacloud.net/rest/public/annotation/download/index.php?id=<attachment id>&entity=<effi_entity>`,
  where both values come from the attachment object. The `effi_entity`
  value is a per-file signed token supplied by the API, so the link works
  without any login. Three sample downloads all returned
  `application/pdf` (233 KB, 145 KB, 219 KB).

**Depth and completeness.** A sample of 12 disciplined LPC profiles
(every 12th record) had one notice each, effective dates from 1999-12-27 to
2025-06-30. Six of the twelve had an attached order; the six without were
the older notices (1999 to 2013). So the register is an index back to at
least 1999 but carries order documents only for roughly the last five
years (attachments seen from 2021-06 to 2026-08). Older orders would need a
records request. File names follow the pattern
`Lastname, Firstname_Consent Order.pdf`, `..._Final Order.pdf`,
`..._Voluntary Surrender.pdf`, sometimes prefixed with the case number
(`2025-LPC-654_...`). Expect roughly 70 to 90 LPC order PDFs.

**Sample PDFs.** Three Consent Orders (6, 6 and 7 pages). PyMuPDF
`get_text()` returned 0 characters for all three: image-only scans. OCR is
required, as for Vermont.

**AG board supervisory letters (fallback).** The index page
`https://oklahoma.gov/oag/opinions/board-supervisory-letters.html` renders
its "Recent Letters" list with client-side JavaScript; the served HTML and
the page's `.model.json` contain the intro text only, and the guessed year
pages (`.../2025.html`, `.../2026.html`) redirect to the state home page or
404. The individual letters do exist as server-rendered HTML pages with a
PDF copy, for example
`https://oklahoma.gov/oag/opinions/board-supervisory-letters/2026/12a.html`
(LPC, Medicaid fraud, proposed revocation and $2,000 penalty) and
`.../2026/45a.html`. Numbering is not contiguous (`2026/1a.html` is 404),
and the letters cover every profession's board, so enumerating them means
brute-forcing `YYYY/<n>a.html` and filtering by title. Each letter is a
one-paragraph summary of the proposed action, not the order. Useful only
to cross-check names and dates.

**Blocking.** None. No 403, no CAPTCHA, no session requirement on any of
the REST calls. Be polite: the register serves the whole licensee
population (about 14,600 records) and the disciplined filter avoids
crawling it.

**Rating: EASY.** One filtered JSON search lists every disciplined LPC,
one profile call per licensee gives the notice and a working PDF link, and
the only real cost is OCR on scanned orders.

## 2. New Mexico, RLD Counseling and Therapy Practice Board

**Working URL.** The survey's URL loads (HTTP 200, WordPress):
`https://www.rld.nm.gov/boards-and-commissions/individual-boards-and-commissions/counseling-and-therapy-practice/discipline-and-enforcement/`.

**What the page really contains.** Nothing. After the site header, the
breadcrumb and the "Explore Section" navigation (which is the same on every
RLD board page and is what produced the search-engine snippet), the
content area holds only the heading "Discipline and Enforcement". There is
no table, no list, no paragraph, no PDF link, and no "prior to July 2011"
records-request sentence. The raw HTML contains zero occurrences of
`.pdf`, "settlement", "order", "licensee", "LPCC" or "LMHC".

The sibling Social Work Examiners page at the same path pattern shows what
a populated RLD page looks like: an intro sentence ("When any final
disciplinary and enforcement actions are completed, the Board will update
this page ... prior to July 2011 can be obtained by filing a public
information request"), then a four-column table (Case #, Name, License #,
Board Action and Date) with 39 linked PDFs under `/wp-content/uploads/`.
One sample social-work order (12 pages, "Final Decision and Order") is
text-native (14,646 characters). So the site can publish orders in a
scrape-friendly way; the counseling board simply has not.

The board's overview and Board Information pages carry best-practice
sheets and two newsletter PDFs, no orders. The department-wide Enforcement
Actions hub (`/about-us/public-information-hub/enforcement-actions/`) just
links back to each board's page.

**Counselor separation.** Moot; nothing to separate. If the board ever
populates the page, the license-number and case-number conventions would be
the place to look (the social-work table uses `SW-<year>-<n>-COM` case
numbers).

**Blocking.** None (plain WordPress, HTTP 200). Wayback could not be
checked (429), so it is not known whether the page was populated in the
past.

**Rating: NOT FEASIBLE.** The page exists but carries no actions at all;
New Mexico counselor orders would come only through an IPRA public-records
request to RLD.

## 3. Nevada, Board of Examiners for MFT and CPC

**Working URL.** The bare host `marriage.nv.gov` returns a raw IIS 404
for every path, including the home page, and both survey URLs
(`/Services/Disciplinary_Actions/` and
`/Board/Disciplinary/DisciplinaryActions/`) are 404 on both hosts. The
site lives on `www.marriage.nv.gov` and the page is
`https://www.marriage.nv.gov/services/disciplinary-actions/` (HTTP 200,
linked from `https://www.marriage.nv.gov/services/`).

**What the page really contains.** A text-only list, one short block per
licensee, alphabetical, no table and no links anywhere in the content
(the only hrefs on the page are site navigation). Each block reads:

    Bartlett, Emma (License #2907-R)
    Complaint #NV24MFT007 Consent Decree 9/20/2024; Satisfied 3/21/2026

Some blocks add "Other Names: ..." or more than one complaint line. Action
types seen: Consent Decree (most), Order / Board Order, Stipulated
Agreement. There is no order document, no summary of the conduct, and no
sanction beyond the action label. License verification is on a separate
Certemy public registry (`https://nvboe.certemy.com/public-registry/...`),
which was not probed.

**Count and range.** 37 licensees. Dates run from 12/14/2012 to
8/18/2026. Complaint numbers: 35 MFT, 12 CPC (some licensees have several).

**CPC vs MFT.** Separable two ways: the complaint number embeds the
profession (`NV23CPC008` vs `NV23MFT004`), and license-number prefixes
follow the board's scheme (CP = CPC, CI = CPC intern, MI = MFT intern,
plain digits = MFT). By complaint number, 10 licensees are CPC-only and 27
are MFT (one CPC-licensed person, Michael Smith, has both). Actions per
CPC licensee: 11 complaint lines, 2018 to 2026.

**Sample PDFs.** None exist to sample.

**Blocking.** None once the `www` host is used. Static HTML, no
JavaScript needed.

**Rating: NOT FEASIBLE for orders.** The board publishes a name-and-date
index only, no order documents, and the CPC portion is ten people; copy
the page by hand if the index is wanted.

## 4. North Dakota, Board of Counselor Examiners

**Working URL.** `https://www.ndbce.org/` (HTTP 200, static site). The
"Disciplinary Actions" menu item links directly to a PDF:
`https://www.ndbce.org/PDFs/Disciplinary%20Actions.pdf` (note the space in
the file name). There is no HTML disciplinary page; the News page has no
discipline content either.

**What the PDF contains.** One page, produced 2026-04-29, titled "North
Dakota Professional Counselors Disciplinary Actions", with the note
"Disciplines updated as they occur". Columns: Name, License #, Date of
Board Action, Action Taken, Effective Date of Action Taken, End date of
action. Eight rows, board-action dates 6/10/2022 to 3/18/2026. Actions:
Suspension 1, Probation 2, Revoke License 2, "Discipline" 3. The text layer
is present (746 characters via PyMuPDF), though the names are laid out
apart from their rows and would need column-position parsing to pair up.

**Counselor separation.** Not needed; the board licenses counselors only
(LPC, LAPC, LPCC).

**Order documents.** None. No link, no case narrative, no sanction detail
beyond the one-word action.

**Blocking.** None.

**Rating: NOT FEASIBLE for orders.** An eight-row index PDF with no
orders; the yield would not justify even a records request.

## Method notes

- Fetches used a desktop browser User-Agent, 1.6-second pauses, and
  `requests`; nothing needed a headless browser.
- Oklahoma: 5 search pages of 2,000 records were pulled while probing
  pagination before the `disciplined` filter was found; a downloader
  should use the filter and never page the full register.
- Sample PDFs downloaded: Oklahoma 3, New Mexico 1 (a social-work order,
  used only to characterise the site's PDFs), North Dakota 1 (the index
  itself), Nevada 0. All deleted after inspection; none committed.
- Wayback Machine: every `archive.org/wayback/available` call returned
  HTTP 429 across three retries with 20-second waits, so "could not
  verify" applies to any question about how these pages looked in the
  past (in particular whether New Mexico's page was ever populated).
