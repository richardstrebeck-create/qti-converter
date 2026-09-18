# Verification of the four new downloaders (2026-09-18)

Companion to `HANDOFF_2026-09-18.md`. The four scripts written that morning
had never touched their sites. This note records what the sites really look
like, what was changed, and what each state now yields. Everything below was
done from a cloud session with open network access, in list-only mode plus a
handful of sample PDFs per state. No PDFs are committed.

Two of the four sites (Kansas, New Hampshire) sit behind Akamai and refused
every request from this session with HTTP 403 "Access Denied" (including the
home pages and PDF links, with browser headers, and through a second fetch
route). Those two parsers were verified against Wayback Machine copies of
the pages instead, and their manifests come from those copies. Both scripts
gained a `--from-saved DIR` option so the user can save the pages from a
browser and run the parser on them if the block also affects a home machine.

Summary

| State | Site reached | Layout as assumed | Entries found | Counselor orders | PDF text layer |
|---|---|---|---|---|---|
| Kansas | No (403). Archived copy of 2026-08-14 used | No: table, no .pdf links | 583 documents, 511 licensees | 78 documents, 60 people, 1998 to 2026 | Could not verify |
| New Hampshire | No (403). Archived copies of 2025-05/06 used | Partly: no table, three layouts | 39 documents | 18 documents, 16 people, 2017 to 2024 | Could not verify |
| Vermont | Yes | Partly: REST closed, three file-name shapes | 138 PDFs | Unknown until OCR (all samples are scans) | Scanned, no text (8 of 8) |
| Iowa | Yes | No: different source entirely | 803 files (801 PDF) | Unknown until download (353 people, all professions) | Mostly text; about a quarter need OCR |

## Kansas (BSRB Disciplinary Actions)

**Site access.** `www.ksbsrb.ks.gov` returned Akamai "Access Denied" for
the root page, all seven letter pages, and a PDF, with plain and full
browser headers. The Wayback Machine holds a copy of all eight pages from
2026-08-14 (five weeks old), which is what the parser was verified against.
The manifest.csv in `kansas_downloader\` comes from that copy, so it can be
a few entries short of today's site.

**What the pages really look like.** Not a list of PDF links. Each letter
page is one HTML table with four columns:

    Name - LICENSE NUMBER | date(s) | city | Document type <case-number link>

Example row: `Abbey, Leslie - LSCSW 1264 | 12/16/2015 | Prairie Village, KS |
Consent Agreement and Order 13-CS-0110`. A licensee with several orders has
several dates and several links in the same row. The links go to
`/home/showpublisheddocument/<id>/<ticks>`, not to a `.pdf` file name, so
the old parser (which kept only `.pdf` hrefs) would have found nothing.

**Profession codes.** Every code seen in a case number was cross-tabulated
against the license label in the name column (584 links). Decoded:

| Code | Label | Meaning | Category |
|---|---|---|---|
| PC | LPC | Licensed Professional Counselor | counselor |
| LC | LCPC | Licensed Clinical Professional Counselor | counselor |
| MS, CS, BS, AS, SW | LMSW, LSCSW, LBSW, LASW | social work | drop |
| MF, CT | LMFT, LCMFT | marriage and family therapy | drop |
| AC, CA, MA, RD | LAC, LCAC, LMAC, RAODAC | addiction counseling | drop |
| LP, MP, CP | LP, LMLP, LCP | psychology | drop |
| BA | LBA | behavior analysis | drop |
| NL | (Unlicensed, or a licensee) | "no license" cases | by label, else review |
| APP | applicant | applicant | by label, else review |
| none (95-0588 style) | label only | 1980s to 1990s cases | by label, else review |

The first draft had PC only and would have dropped every LCPC (25 links).

**Changes to the script.**
- Row-based table parser: name cell (bold name, then license labels), date
  cell (one date per document), city, documents cell split on line breaks
  so each link keeps its own document type and date.
- Classification order: license label(s) in the name column, then the
  case-number code, then words in the row. A dual licensee holding LPC or
  LCPC (for example "LCAC 606, LPC 3068") is kept as a counselor and noted.
- Document links recognised by the `showpublisheddocument` path as well as
  `.pdf`. Links without a case number are named by the site's document id.
- `--from-saved DIR` to parse saved pages; Wayback link prefixes stripped.
- manifest.csv keeps all previous columns and adds `license`, `action_date`,
  `city` at the end.

**Counts (2026-08-14 copy).** 583 documents on 511 rows. Counselor 78
(46 PC, 25 LC, 3 legacy numbers with an LPC label, 4 dual or odd codes),
drop 503 (social work 304, psychology 71, addiction 69, MFT 58, behavior
analysis 1), review 2 (cease-and-desist orders against unlicensed persons,
codes NL). The 78 counselor documents belong to 60 people and are dated
1998-02-09 to 2026-05-11 (1990s 1, 2000s 9, 2010s 24, 2020s 44). Ten links
carry no case number and one no date; all are named and flagged.

**PDF text layer.** Could not verify: PDF downloads were blocked too.

**Still to decide.** Whether the two NL "unlicensed practice" orders belong
in the dataset (they are in `review`). Whether the home machine is blocked
as well; if so, save the pages from the browser and use `--from-saved`, and
download the 78 counselor PDFs by hand from the manifest's `official_url`.

## New Hampshire (OPLC Board of Mental Health Practice actions)

**Site access.** `www.oplc.nh.gov` returned the same Akamai "Access Denied".
Wayback copies of the root page and the 2017 to 2025 year pages (captured
2025-05-31 and 2025-06-30) were used. There was no archived 2026 page, and
the live 2026 page could not be fetched, so 2025-07 onward is not in the
manifest.

**What the pages really look like.** No table. Three layouts:
- 2017 to 2023: a bulleted list, one item per action, name and license
  type in bold ("Steven Durost, MA, LCMHC, License #605"), then
  "4/21/2017 - On April 21, 2017, the Board ... approved a <link>".
- 2024: one paragraph per action, bold name segment then a link labelled
  "Voluntary Surrender, 10/18/2024".
- 2025: the entire entry is the link label ("Samuel Rosario, LCSW,
  License # 324, Order of Dismissal, 04/18/2025").
The license labels in use are LCMHC, LICSW, LCSW, "Unlicensed", "Unlicensed
Practice", "Candidate for Licensure". No MFT or pastoral rows appeared.

**Changes to the script.** Classify the bold name segment first (the old
code classified the whole row, so a LICSW row whose link text mentioned
LCMHC would have been kept); fall back to the link label when there is no
name segment; accept two-digit years and dashed dates and the "On October
20, 2017" form; accept license numbers with a letter prefix ("EL06511");
handle "Jr" suffixes; add candidate and alcohol/drug counselor rules;
`--from-saved`; new last column `license_type` (the raw name segment).

**Counts (2025-06 copies).** 39 documents: counselor 18 (16 people,
2017-04-21 to 2024-09-20), drop 21 (social work 16, unlicensed 3,
candidate 2), review 0.

**PDF text layer.** Could not verify (downloads blocked). The documents are
recent and Word-generated, so a text layer is likely.

**Still to decide.** Nothing structural. Re-run once the block is
understood to pick up late-2025 and 2026 actions; OPLC removes documents
after seven years, so the 2017 and 2018 files may disappear soon.

## Vermont (OPR allied mental health conduct decisions)

**Site access.** Reached. The SharePoint REST endpoint the script tried
first answers 404 or 401 (anonymous access denied) at every web root. The
folder's "All Documents" view page works, and embeds the file list as JSON
(`WPQ1ListData`) 30 files per page with a `NextHref` to the next page. The
script now pages through that (5 pages on 2026-09-18).

**File names.** Not `lastname_firstname_docket_NNNN`. Three shapes:

    2025-105_Ashley_MacDonald_Signed_Order.pdf     docket(s), First Last, type
    2025-38_gould_adam_signed_order.pdf            docket(s), Last First, type
    albergate-scott-docket-2018-20.pdf             Last First, "docket", docket

The first two cannot be told apart from the file name, so the manifest marks
them "name order assumed First Last" and pass 2 now reads the "In re:" line
of the PDF and corrects the order when the two names match in either order.
Some files carry several dockets ("2023-161 & 2024-188", "2022-201-to-203");
the new `dockets_all` column keeps them all and `docket` keeps the first.

**Counts.** 138 PDFs. 99 were bulk-uploaded 2025-03-13, the rest added up
to 2026-09-18. Docket years: 2007 (1), 2012 (1), 2016 (2), 2018 (6), 2019 (9),
2020 (6), 2021 (1), 2022 (3), 2023 (12), 2024 (12), 2025 (19), 2026 (11), and
55 older-style dockets (aomh010300, mh020903, mft011207, 2012505 and the
like). Several people have two files for the same docket (a signed order
and a later modification), which the "(2)" suffix handles.

**PDF text layer.** All eight samples are image scans with zero extractable
text: 2007-era and 2018 files, a 2019 default order, 2023 orders of 85 KB
and 160 KB, and 2025 and 2026 signed orders. Expect every file to land in
`review\` on the first pass. No OCR engine was available in this session, so
the classification wording (LCMHC versus LMFT, psychoanalyst, non-licensed
psychotherapist) could not be tested on real text.

**Changes to the script.** All Documents paging as the listing method;
new file-name parser; PDF "In re:" name check; unreadable-text detection
(see Iowa); columns `modified` and `dockets_all` added at the end.

**Counselor orders available.** Unknown until OCR. A cross-check that needs
no OCR exists: the monthly discipline reports at
`sos.vermont.gov/opr/complaints-conduct-discipline/monthly-discipline-reports/`
are 92 text-native PDFs (2019-01 to 2026-08), one line per action
("Last, First, City, ST / LCMHC / date: action"). They can settle both the
profession and the name order for 2019 and later dockets, which is 90 of
the 138 files.

**Still to decide.** Whether to OCR all 138 files (Foxit, then
`--reclassify`) or to build the LCMHC name list from the monthly reports
first and OCR only the matches plus the pre-2019 files. The monthly-report
pass is not built; it would be a small addition to this script.

## Iowa (Board of Behavioral Health Professionals)

**Site access.** Reached. The assumed layout does not exist.
`dial.iowa.gov/i-need/board-actions` is a single page with a collapsible
section per board; the Behavioral Health section is 30 "Notice of Board
Action" e-mail bulletins (July 2024 to August 2026), each a GovDelivery link
listing names and case numbers, with each licensee linked to
`documents.iowa.gov/#document=<id>`. There are no per-action pages and no
"Next" link, so the old crawler would have found nothing.

**The real index.** `documents.iowa.gov` is a document search with a JSON
API (`POST /home/search`). Filtered to Board = "Behavioral Health
Professionals, Board of" and Category = "Public Discipline Documents" it
returned 803 files on 2026-09-18 (801 PDF, 2 Word), each with last name,
first name, city and state as metadata and a download link at
`/home/download/<id>`. 710 files were uploaded on 2023-10-30 and are the
archive of the former Board of Behavioral Science and, it turns out, of the
former social work and psychology boards too (sample captions: "BEFORE THE
BOARD OF SOCIAL WORK EXAMINERS", "BEFORE THE IOWA BOARD OF PSYCHOLOGY").
The rest were added 2024-01 to 2026-09. The index date is the upload date,
not the order date; the order date is inside the PDF. Document names are
inconsistent ("JohnPaul Nganga 1", "23-0145 Stewart-Sandusky, Michelle
SA.pdf"); 56 of 803 carry a case number in the name. The recordsTotal the
API reports moved from 790 to 803 during one crawl, so the script stops on
a short page rather than on that number.

**Changes to the script.** Rewritten around the documents.iowa.gov index:
pass 1 reads it 200 records per request into actions.csv (all previous
columns kept, plus doc id, name fields, city, state, upload date, file
type, size, archived flag, case number); pass 2 downloads by id; pass 3
takes the name from the index metadata rather than from "In the matter
of". Classification now compares the caption ("RE: Social Work License of
...", "BEFORE THE BOARD OF PSYCHOLOGY") with the licence sentence in the
body ("Respondent was issued mental health counselor license no. ...") and
sends a contradiction to review instead of guessing; when the first three
pages are silent it reads up to 15 pages. `--max-pages` now counts index
pages of 200. Word files are saved with their own extension and reviewed.

**Samples (15 files across 2023 to 2026 uploads).**

| Result | Files |
|---|---|
| Readable text, classified as expected | 11 (LMHC kept 4, social work 5, psychology 2) |
| Header contradicts body, sent to review | 1 (2025 order: caption "Social Work License", body "mental health counselor license") |
| Scan, no text layer | 2 (one 2023 archive file, one 2025 order of 5.9 MB) |
| Text layer present but unreadable | 2 (2025-09 and 2026-08 orders: Type3 fonts with no Unicode map, text extracts as symbols) |

The unreadable-text case is new: the old check (fewer than 200 characters)
would have passed those files through and classified them as "profession
not found". Both Iowa and Vermont now treat a text layer with under 50
percent letters as needing OCR. One 2023 file classified as counselor from
the body phrase "provides mental health counseling" on page 4 with no
caption; the note says "profession from body text only" so it can be
checked.

**Counselor orders available.** Unknown until the full download and
classification run: the 803 files cover 353 people across at least four
professions. The manifest.csv for Iowa is produced by pass 3, so only
actions.csv is committed from this list-only run.

**Still to decide.** Whether to keep the pre-2024 social work and psychology
archive files in `_all_behavioral_health` (they are downloaded and dropped)
or to skip them; the index cannot filter them out because the board field
is the current board. Expect roughly a quarter of the files to need OCR.

## Housekeeping

- `board-orders\.gitignore` added: PDFs, Word and Excel files, `debug\`,
  `__pycache__\`, download logs and the holding and review folders.
- Sample PDFs downloaded during verification were deleted.
- All four scripts remain standard library plus requests, beautifulsoup4
  and PyMuPDF, with the same file names, flags and filename conventions;
  new manifest columns were only appended.
- Not done: full downloads, OCR, `make_text_sidecars`, extractor
  registration. The Status column of the handoff table is updated.
