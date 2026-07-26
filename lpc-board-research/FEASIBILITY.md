# Which states can I add to the scraper? — feasibility assessment

**Question:** which state counseling boards publish board orders / sanctions in a form that can be
collected with minimal access restrictions (no CAPTCHA, no login, no records request)?

**Short answer:** 8 states are ready to add now, 12 more are worth adding with extra parsing work,
5 are high-value unknowns worth one probe each, and 20 are effectively closed to scraping.

---

## 1. The finding that decides everything

Access restrictions are not distributed randomly across states. They track *how* a board publishes.

There are two fundamentally different things a board can put on the web:

- **A document index** — a page listing disciplinary actions, usually linking a PDF order per case.
  Static. No form, no session, no cookie. **CAPTCHAs essentially never appear here**, because there
  is nothing to submit.
- **A license-lookup portal** — a search box where you type a name and get that licensee's record.
  This is where CAPTCHAs, click-through disclaimer gates, ASP.NET postback tokens, and session
  requirements live, because it *is* a form.

That split matters more than it first appears, because it coincides with a second problem:

> A lookup portal cannot be **enumerated**. You can only ask it about a name you already have.
> There is no way to say "list every disciplinary action" — so it cannot generate a dataset,
> only verify one.

So the two things you care about — *low access restriction* and *usable for research* — turn out to
be the same states. **You are not trading ease against coverage.** The states that are easy to
scrape are the states that can actually produce a dataset, and the states with CAPTCHAs and gates
were never going to produce one anyway. That simplifies the decision considerably: there is no
tempting-but-hard middle tier to agonise over.

A concrete illustration: Montana's disciplinary access point is literally
`ebizws.mt.gov/PUBLICPORTAL/disclaimer.jsp` — a click-through gate in front of a name search.
Louisiana's is `lpcboard.org/disciplinary-action` — a plain list of PDFs. Same nominal
"public record", opposite practical accessibility.

---

## 2. TIER 1 — add these first (8 states)

Static, enumerable, full order text, no form to defeat. All are single-hop: fetch index → follow
document links. These are structurally the same shape as the Alabama/Mississippi/Utah sources
already in the scraper, so the existing extraction approach should largely carry over.

| # | State | Entry point | Why it's easy | Depth |
|---|-------|-------------|---------------|-------|
| 1 | **Louisiana** | `lpcboard.org/disciplinary-action` | Plain index of all disciplined licenses → linked Final Consent Agreements. Case-number filenames encode fiscal year. **Single profession** — no filtering. | Indefinite |
| 2 | **Missouri** | `pr.mo.gov/counselors-discipline.asp` | Counselor-specific page on a stable flat `.asp` path. No composite-board filtering. | Indefinite |
| 3 | **North Carolina** | `ncblcmhc.org/Complaints/DisciplinaryActions` | Single-profession board (LCMHC only). One page, actions 2005→present. | ~20 yrs |
| 4 | **Minnesota** | `mn.gov/boards/behavioral-health/public-information/complaints-discipline.jsp` | Per-case PDFs whose **filenames embed licensee name + order date** — date normalisation nearly free. | See caveat ⚠ |
| 5 | **Maryland** | `health.maryland.gov/bopc/pages/publicorders.aspx` | Orders organised **by credential type**, so counselor cases isolate cleanly without post-filtering. | Good |
| 6 | **Virginia** | `dhp.virginia.gov/enforcement/cdecision/boardresults.asp?board=7` | The most scraper-friendly endpoint found: server-rendered `.asp`, board filter as a **plain query parameter** (`board=7` = Counseling). No JS, no session. | Good |
| 7 | **Wisconsin** | `online.drl.wi.gov/orders/searchorders.aspx` | **Deepest archive found** — all orders Nov 1998→present, many back to 1977. PDFs on a year-partitioned path. Explicitly open under WI Open Records law. | ~27 yrs |
| 8 | **New Hampshire** | `oplc.nh.gov/board-mental-health-practice-actions` (+ `-2021`, `-2023`, `-2024`…) | **Year-partitioned sibling URLs** — enumerate by iterating the year suffix. Filenames encode name, action type, ISO date. | 7 yrs ⚠ |

### Tier 1 caveats you should not skip

- ⚠ **Minnesota** states it is *still uploading* its historical collection. The online set is
  incomplete for older years. Check actual year coverage before treating MN volume as comparable.
- ⚠ **New Hampshire retains disciplinary documents for only 7 years.** That truncates *inside* your
  current 2016–2026 window, so NH will show a structurally shorter series than other states. Do not
  compare NH case volume naively — it is a retention artifact, not an enforcement difference.
- **Wisconsin**: DSPS states plainly that *not all orders constitute formal disciplinary action*.
  The raw result set must be filtered or it will inflate your sanction counts.
- **Maryland**: informal actions (letters of education, advisory letters) are confidential and never
  published, so MD's visible set skews toward more serious matters.
- **Virginia** also publishes a *Sanctioning Reference Points Manual* — directly useful for
  normalising VA sanction severity against other states in the crosswalk.

---

## 3. TIER 2 — add second (12 states)

Enumerable and unrestricted, but each carries real extra work: multi-profession filtering, PDF prose
parsing, or thinner conduct narrative. Worth adding, just not first.

| State | Entry point | Extra work required |
|-------|-------------|---------------------|
| **Pennsylvania** | `pa.gov/agencies/dos/alerts-and-notices/professional-licensing-disciplinary-actions` | Filter to the counseling board. **Richest field set found**: name, license no., address, sanction, *description of the basis*, effective date, *and appeal status*. |
| **Tennessee** | `tn.gov/health/health-professionals/health-professionals-boards-disciplinary-actions.html` | Monthly DAR PDFs, deep archive. Filenames are **inconsistent across years** (`19.09-DAR.pdf` vs `FEB-2024-DAR.pdf`) so crawl the index, don't guess URLs. Large multi-profession docs need per-board section parsing. |
| **Illinois** | `idfpr.illinois.gov/news/disciplines/discreports.html` | Monthly consolidated reports, all IDFPR professions. Filter to LPC/LCPC. Conduct description is brief. |
| **Rhode Island** | `health.ri.gov/lists/disciplinaryactions/resultsbydate?prof=224` | **Profession-code query param** — enumerable directly. Publishes *full text of the decision*. Limits: post-2014-12-09 only; default view is rolling 60 days. |
| **Nebraska** | `dhhs.ne.gov/licensure/Documents/<MM-YY>discip.pdf` | Filename pattern inferred from one example — verify before iterating months. Good granularity: licensee, all license types, date, named grounds. |
| **Iowa** | `dial.iowa.gov/i-need/board-actions` | Orders archived via `documents.iowa.gov`. Board was renamed (Behavioral Science → Behavioral Health Professionals) so history may sit under both names. |
| **Vermont** | `outside.vermont.gov/.../conduct_decisions/allied_mental_health/` | A **per-profession decisions directory** — ideal shape if browsable. Small state, low volume, excellent full text. |
| **Hawaii** | `cca.hawaii.gov/oah/oah_decisions/` + DCCA monthly releases | Enumerable summaries plus retrievable full decisions. Low volume. |
| **Michigan** | `michigan.gov/lara/.../health-license-disciplinary-action-reports` | Monthly DARs give name, licence no., action, date, *general nature* of complaint, plus appeal updates. **But order documents require a FOIA request** — good for sanction severity, weak for violation coding. |
| **Washington** | `doh.wa.gov/newsroom/state-disciplines-health-care-providers-<MM-DD-YYYY>` | Date-templated URLs, enumerable by iterating dates. Format is **press-release prose**, not tabular — regex/heuristic parsing. |
| **Alaska** | `commerce.alaska.gov/web/cbpl/DisciplinaryActionReports.aspx` | Quarterly, division-wide. 2017+ only; up to 60-day posting lag. |
| **Oregon** | `oregon.gov/oblpct/pages/compliance.aspx` | Single-profession board, periodic reports. Oregon State Library digital collections archives past editions — useful independent backfill source. |

---

## 4. TIER 3 — five probes worth running before you write anything off

Each of these could jump straight to Tier 1 if the URL resolves. Two are documented-but-unlocated;
three are pattern inferences from confirmed sibling pages on the same site.

| State | What to check | Why it matters |
|-------|---------------|----------------|
| **Texas** | Find the enforcement-actions page on `bhec.texas.gov` | **Highest-value unknown.** BHEC is documented as publishing counselor enforcement actions *including names, the alleged violation, and the action* — the alleged-violation field is exactly what your violation recoder needs — and denials/surrenders/revocations are posted **permanently**. Large state, high volume. |
| **Florida** | `mqa-internet.doh.state.fl.us/MQASearchServices/Document` and date-parameterised variants | Enforcement routes are **confirmed** (`ShowLast30DaysOthr`, `ShowLast30DaysErso`) but are rolling-30-day views. Find the archive route and Florida becomes a top-3 addition. |
| **Idaho** | `dopl.idaho.gov/cou/cou-disciplinary-actions/` *(inferred)* | DOPL publishes per-board discipline pages on this exact pattern for other boards (`/sre/sre-disciplinary-actions/` is confirmed). Single highest-value guess in the registry. |
| **South Carolina** | `llr.sc.gov/cou/finalorders.aspx` *(inferred)* | Pattern confirmed at `llr.sc.gov/boil/finalorders.aspx` for another LLR board. ⚠ Do **not** mistake the confirmed `SancUnlicPrac.aspx` for this — that page covers *unlicensed practice* only, not licensee discipline. |
| **New Jersey** | `njconsumeraffairs.gov/pc/Pages/actions.aspx` *(inferred)* | Confirmed for other NJ boards (`/acc/Pages/actions.aspx`). Check `/mft` too — the counselor committee is a sub-committee of the MFT board, so actions may publish there. |
| **Connecticut** | Locate the quarterly *Regulatory Action Report* archive under DPH/PLIS | Report is documented as compiling disciplinary actions across all DPH-licensed individuals quarterly, but the archive URL was not isolated. CT State Library also archives DPH agency decisions — a possible independent source for full order text. Would land in Tier 2 if found. |

Run these with
`python probe.py --include-hints --states Texas Florida Idaho "South Carolina" "New Jersey" Connecticut`.

---

## 5. TIER 4 — do not attempt by scraping (20 jurisdictions)

**Lookup-only (not enumerable; CAPTCHA/gate risk concentrated here):**
Arizona, Arkansas, California, Colorado, Delaware, District of Columbia, Montana, Nevada, Oklahoma,
South Dakota

**Nothing enumerable published (records request is the route):**
Georgia, Indiana, Kansas, Maine, Massachusetts, New Mexico, North Dakota, Ohio, West Virginia, Wyoming

Two of these deserve a footnote rather than a flat no:

- **Colorado** is the one genuine near-miss. Its roster generator
  (`apps2.colorado.gov/dora/licensing/lookup/generateroster.aspx`) can export the full licensee
  list, which makes it enumerable *in two hops*: export roster, then walk each licensee's record.
  Full order text is available and posted within days. That is thousands of requests against a state
  server for one state's data — technically possible, but it is a different kind of undertaking from
  Tier 1, and it needs deliberate rate limiting. My recommendation: leave it until the 20 easy
  states are done, then decide whether CO is worth it.
- **Ohio** is enumerable in principle — disciplinary actions appear in quarterly board newsletters
  (name + credential + reason). But the reasons are 2–3 words (`"Impairment"`, `"Audit Failure"`),
  filenames are inconsistent, and it is PDF-prose parsing. Highest effort-to-yield ratio of any
  enumerable state, and too thin for meaningful violation-category coding. Skip unless you
  specifically need Ohio.

---

## 6. Why I could not verify these URLs myself

This session runs in a sandbox whose egress policy blocks state-government hosts. Every attempt
returned `403` at the proxy's CONNECT tunnel, logged proxy-side as
`gateway answered 403 to CONNECT (policy denial)` for `ncblcmhc.org`, `lpcboard.org`,
`dpo.colorado.gov`, `oregon.gov`, and `pa.gov`. Web *search* works (it is an Anthropic-side
service); direct page fetching does not.

**So: every URL and structural claim in `registry.json` and in the tables above is derived from
search results, not from a fetched page.** The publication models, retention windows, and field
descriptions come from board and agency text quoted in those results, which is good evidence but not
the same as having parsed the page. Treat all of it as high-quality leads requiring confirmation.

That confirmation step is `probe.py`, which is the deliverable that closes this gap. Since your
scraper already runs locally on Windows, this is not a real obstacle — it just means the verification
happens on your machine instead of mine.

---

## 7. Running the probe

From `C:\Users\richa\OneDrive - WCU\!Python Tools\` (or wherever you put this folder):

```
python probe.py                        # all jurisdictions
python probe.py --include-hints        # also test the 3 inferred URLs
python probe.py --states Louisiana Missouri "North Carolina" Minnesota Maryland Virginia Wisconsin "New Hampshire"
```

Stdlib only — nothing to install. It is read-only: checks `robots.txt` before every fetch, sleeps
between requests to the same host, identifies itself with a real contact address, and never submits
a form. It collects **no case data** — it only characterises each page so you can decide where to
write extractors.

Outputs `probe_results.csv` and `probe_results.json`, with per-URL columns for:

- `captcha` — which bot-wall was detected (reCAPTCHA, hCaptcha, Turnstile, Cloudflare, Incapsula,
  Akamai, PerimeterX, DataDome, or generic "verify you are human" text). **Non-empty = exclude.**
- `friction` — not CAPTCHAs but real obstacles: ASP.NET postback tokens, click-through disclaimer
  gates, session requirements.
- `verdict` — `EASY` / `MODERATE` / `HARD` / `CAPTCHA-BOT-WALL` / `WEAK`
- `pdf_links`, `tables`, `name_like`, `date_like`, `sanction_words` — the raw signals behind the verdict
- `year_links` — detected year-partitioned sibling pages (the New Hampshire pattern)
- `robots_allowed` — honored, not just recorded

The run ends with a **SCRAPE ORDER** list: states with at least one `EASY`, CAPTCHA-free endpoint.
That list, not my Tier 1 table, is your ground truth — if the probe disagrees with this document,
believe the probe.

---

## 8. Data-collection posture

These are records that state boards publish deliberately, for public protection, on unauthenticated
pages. Collecting them for academic research sits on solid ground, and Wisconsin even frames its
order archive explicitly under the state Open Records law. A few practical commitments keep it that
way:

- **Honor `robots.txt`.** `probe.py` does; your extractors should too. If a board disallows the
  discipline path, that state comes out of the set — there are 19 others.
- **Never defeat an access control.** No CAPTCHA solving, no gate bypass, no scraping behind a login.
  A CAPTCHA is a board saying no; the correct response is a public-records request, not a workaround.
  This is also why Tier 4 is a genuine stopping point rather than a harder problem to solve.
- **Rate limit and identify yourself.** Small board sites run on modest infrastructure. A couple of
  seconds between requests and an honest User-Agent with a contact address costs you nothing and
  means a webmaster emails you rather than silently blocking your IP.
- **Prefer the archive to the crawl.** Where a state publishes periodic report files (PA, TN, IL, MI,
  NE, AK), fetching those is far lighter on their servers than walking a search interface.

One research-design note, separate from access: these records name real people alongside sensitive
conduct. Public-records research is typically IRB-exempt, but whether identifiers belong in your
*published outputs* is a distinct decision from whether they can be collected. Your pipeline
currently retains a `Name` column — worth deciding deliberately how that surfaces in the research
brief and deep dives rather than by default.

---

## 9. Two cross-state biases this survey surfaced

Both affect the analysis, not the scraping, but they are easier to handle if you know now.

**Retention limits left-censor the record — unevenly.** Documented earliest coverage varies far more
than expected: Wisconsin 1998 (some 1977), NC 2005, RI Dec 2014, AK 2017, MT 1996, SC 1994,
**NH 7 years rolling**. Kentucky's board has actively discussed capping online retention at 5 years,
explicitly contrasting itself with Louisiana and Missouri, which report indefinitely. Your 10-year
window (2016–2026) dodges most of this — but not New Hampshire, and not Kentucky if that cap was
adopted. Confirm KY's current retention before including it in trend analysis.

**Diversion programs suppress substance cases, state by state.** New York's Professional Assistance
Program lets impaired licensees surrender confidentially *as an alternative to discipline*, so those
cases never enter the public record at all. Other states run similar monitoring programs. This means
cross-state differences in substance-related violation rates partly measure **program design, not
practitioner behavior** — worth an explicit footnote in the crosswalk wherever impairment categories
are compared.

---

## 10. Recommendation

1. Run `probe.py --include-hints`. It costs one coffee and replaces every unverified claim here
   with measured fact.
2. Add the Tier 1 states that come back `EASY`, starting with **Louisiana, Missouri, North Carolina**
   — single-profession boards, no filtering, indefinite or deep retention, closest in shape to what
   your scraper already handles.
3. Chase **Texas** and **Florida** next. They are the two largest-volume additions available, and
   both are blocked only on locating a URL rather than on any access restriction.
4. Add Tier 2 as parsing time allows, taking **Pennsylvania** first — its per-entry *basis* and
   *appeal status* fields are the richest structured data found in this survey.
5. Leave Tier 4 alone. Twenty jurisdictions is already a large multi-state dataset, and the closed
   states are closed for reasons that a better scraper does not fix.

Expected result: **~20 states** collectable without defeating any access restriction, of which
**8 are ready now** and 8–10 carry full order text suitable for violation-category coding.
