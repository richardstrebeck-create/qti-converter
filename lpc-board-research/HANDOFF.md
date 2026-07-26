# Handoff prompt — run this in Claude Code on the desktop

Copy everything inside the fence below into Claude Code running on your Windows machine
(where network access and OneDrive are both available).

---

```
I'm expanding a multi-state research dataset of published LPC/counseling board
disciplinary orders. A prior session did the feasibility survey but ran in a sandbox
that blocked state-government hosts, so nothing was ever actually fetched. You have
real network access. I need you to verify the targets and then collect the data.

## Where things are

- Scraper + data:  C:\Users\richa\OneDrive - WCU\!Python Tools\LPC Board\Complaint Scraper\
- Existing scraper: lpc_board_complaint_scraper.pyw  (Windows GUI app)
- Download target:  C:\Users\richa\OneDrive - WCU\!Python Tools\LPC Board\Complaint Scraper\state_data\
- Prior research:   github.com/richardstrebeck-create/qti-converter,
                    branch claude/lpc-board-scraping-feasibility-b54u9b,
                    folder lpc-board-research/
                    (registry.json = all 51 jurisdictions; FEASIBILITY.md = ranked
                     analysis; probe.py = verification script, stdlib only)

Clone or pull that branch first — registry.json has per-state URLs, publication
models, retention limits, and observed document-URL patterns you'll want.

## Task

1. VERIFY FIRST. Run probe.py from the repo folder:
       python probe.py --include-hints
   It checks robots.txt, detects CAPTCHAs/bot walls and form friction, and classifies
   each endpoint EASY / MODERATE / HARD / CAPTCHA. It ends with a SCRAPE ORDER list.
   Every URL in registry.json is search-derived and UNVERIFIED — treat the probe
   output as ground truth and tell me where it disagrees with FEASIBILITY.md.

2. BUILD A COLLECTOR that downloads board orders per state into
   state_data\<State>\ , with a per-state manifest.csv recording:
   source_url, local_filename, fetched_utc, bytes, sha256.
   Use sha256 so re-runs are idempotent and skip files already downloaded.

3. EXCLUDE STATES I ALREADY HAVE. Auto-detect rather than hardcode:
   - skip any state whose state_data\<State>\ folder already contains files
   - also read the existing scraper export workbook (one sheet per state) and skip
     any state that already has a sheet — ask me for the workbook filename, or take
     it as a --existing-workbook argument
   - Alabama, Mississippi and Utah are already in the dataset; confirm against the
     workbook rather than assuming that list is complete
   Give me a --force flag to override, and print exactly which states were skipped
   and why. Never silently skip.

4. RUN IT for the verified states, then report per state: files downloaded, date
   range covered, and anything that looked wrong.

## Priority order

Tier 1 — static document indexes, enumerable, full order text, no form to defeat.
Start with the first three (single-profession boards, no license-type filtering):

  Louisiana      lpcboard.org/disciplinary-action
                 docs: /assets/Disciplinary_Actions/<case-no>.pdf
  Missouri       pr.mo.gov/counselors-discipline.asp
  North Carolina ncblcmhc.org/Complaints/DisciplinaryActions   (2005-present)
  Minnesota      mn.gov/boards/behavioral-health/public-information/complaints-discipline.jsp
                 docs: mn.gov/boards/assets/<Last>,%20<First>%20<M-D-YY>_tcm21-<id>.pdf
  Maryland       health.maryland.gov/bopc/pages/publicorders.aspx   (organised by credential)
  Virginia       dhp.virginia.gov/enforcement/cdecision/boardresults.asp?board=7
                 (board=7 is Counseling; plain query param, server-rendered .asp)
  Wisconsin      online.drl.wi.gov/orders/searchorders.aspx
                 docs: online.drl.wi.gov/decisions/<YYYY>/ORDER<n>-<n>.pdf  (1998-present)
  New Hampshire  oplc.nh.gov/board-mental-health-practice-actions  plus year-suffixed
                 siblings (-2021, -2023, -2024 ...) — enumerate by iterating years

Tier 2 — enumerable but needs multi-profession filtering or PDF-prose parsing:
  Pennsylvania (richest fields: basis + appeal status), Tennessee (monthly DAR PDFs,
  inconsistent filenames — crawl the index, don't guess), Illinois, Rhode Island
  (health.ri.gov/lists/disciplinaryactions/resultsbydate?prof=224 — confirm which
  prof code is LMHC), Nebraska (dhhs.ne.gov/licensure/Documents/<MM-YY>discip.pdf —
  pattern inferred from ONE example, verify before iterating), Iowa, Vermont,
  Hawaii, Michigan (orders need FOIA — summaries only), Washington (press-release
  prose), Alaska, Oregon.

Tier 3 — URL unlocated; one probe each, could jump to Tier 1:
  Texas   find the enforcement-actions page on bhec.texas.gov — HIGHEST VALUE
          (publishes name + alleged violation + action, permanently; large state)
  Florida mqa-internet.doh.state.fl.us/MQASearchServices/... — the ShowLast30DaysOthr
          and ShowLast30DaysErso routes are confirmed but are rolling 30-day views.
          Find the archive route.
  Idaho   dopl.idaho.gov/cou/cou-disciplinary-actions/   (INFERRED)
  S.Carolina llr.sc.gov/cou/finalorders.aspx             (INFERRED)
  N.Jersey njconsumeraffairs.gov/pc/Pages/actions.aspx   (INFERRED; also check /mft)

Do NOT attempt: Arizona, Arkansas, California, Colorado, Delaware, DC, Montana,
Nevada, Oklahoma, South Dakota (license-lookup only — not enumerable, CAPTCHA risk),
or Georgia, Indiana, Kansas, Maine, Massachusetts, New Mexico, North Dakota, Ohio,
West Virginia, Wyoming (nothing enumerable published).

## Output schema

Downloaded documents feed an existing analysis pipeline expecting these columns:
  #, Name, License, Date, Violation Category, Disposition, Previous Category,
  Reanalysis Notes, Sanction, Summary, Source, Comments
If you also write extraction code, emit exactly these. Keep raw downloaded files —
the pipeline recodes from source text and needs the originals.

## Hard rules

- Honor robots.txt. If a board disallows the discipline path, drop that state and
  tell me — there are others.
- Never defeat an access control. No CAPTCHA solving, no gate bypass, no scraping
  behind a login. A CAPTCHA means that state is out; the route there is a public-
  records request, not a workaround.
- Rate limit (~2s between requests to the same host) and set an honest User-Agent
  with my email: richard.strebeck@gmail.com. These are small board servers.
- Prefer periodic report files over crawling search interfaces where both exist.
- DO NOT commit the scraped dataset to the qti-converter repo — it is PUBLIC. The
  data is named individuals attached to disciplinary conduct. Collector code is fine
  to commit; the downloaded files and any export are not.

## Known traps

- South Carolina: llr.sc.gov/cou/SancUnlicPrac.aspx is UNLICENSED PRACTICE only,
  not licensee discipline. Don't mistake it for the disciplinary index.
- Wisconsin: DSPS states not all orders are formal disciplinary actions. Filter, or
  sanction counts inflate.
- New Hampshire: retains documents 7 YEARS only — truncates inside a 2016-2026
  window. Note it; don't compare NH volume naively.
- Minnesota: board is still uploading its historical collection; online set is
  incomplete for older years. Report actual year coverage found.
- Kentucky: board discussed capping online retention at 5 years. Check current state
  before including KY in trend analysis.
- Maryland: informal actions are confidential and never published, so MD skews toward
  more serious matters.

Start with step 1 and show me the probe output before downloading anything.
```

---

## Why this handoff exists

The session that produced `registry.json` and `FEASIBILITY.md` ran in a remote sandbox whose
egress policy blocks state-government hosts (403 at the proxy CONNECT tunnel) and which has no
access to the local OneDrive filesystem. Web search worked; page fetching and local file writing
did not. Desktop Claude Code has both, so the collection step belongs there.
