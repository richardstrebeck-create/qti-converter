# LPC Board Order Scraping — state feasibility survey

Which state counseling boards publish disciplinary orders in a form collectable with **minimal
access restrictions** (no CAPTCHA, no login, no records request)?

## Files

| File | What it is |
|------|-----------|
| **`FEASIBILITY.md`** | **Start here.** Ranked answer: 8 states ready now, 12 with extra work, 5 worth probing, 20 closed. Plus caveats, legal posture, and two analysis biases the survey surfaced. |
| `registry.json` | Machine-readable registry of all 51 jurisdictions: board name, credentials, discipline URLs, publication model, enumerability, retention limits, observed document URL patterns. |
| `probe.py` | Verification script. Run it locally to confirm the registry against live sites and detect CAPTCHAs. Stdlib only. |

## Headline

Access restrictions track *how* a board publishes, and the split is clean:

- **Document index** (static list of order PDFs) → no form, so no CAPTCHA, and **enumerable**
- **License lookup** (search by name) → where CAPTCHAs and gates live, and **not enumerable** —
  it can verify a case you already know about, but never generate a dataset

So low-restriction and research-usable are the *same* states. There is no ease-vs-coverage tradeoff
to agonise over.

## Ready to add now (Tier 1)

Louisiana · Missouri · North Carolina · Minnesota · Maryland · Virginia · Wisconsin · New Hampshire

Start with **Louisiana, Missouri, North Carolina** — single-profession boards, no license-type
filtering needed, deep or indefinite retention, structurally closest to the Alabama/Mississippi/Utah
sources already in the scraper.

## Important caveat

The sandbox this was compiled in **blocks outbound HTTPS to state government hosts** (403 at the
proxy CONNECT tunnel). Web search worked; page fetching did not. **Every URL and structural claim
here comes from search results, not from a fetched page.** They are high-quality leads, not verified
ground truth.

`probe.py` closes that gap from your machine:

```
python probe.py --include-hints
```

It ends with a **SCRAPE ORDER** list of CAPTCHA-free `EASY` endpoints. If the probe disagrees with
`FEASIBILITY.md`, believe the probe.

## Feeds into

The `lpc-research-analysis` pipeline (`lpc_board_complaint_scraper.pyw` → Excel export → recode →
crosswalk → deep dives → research brief). Per-state notes in `registry.json` flag where a source
yields full order text (usable for violation-category coding) versus sanction summaries only.
