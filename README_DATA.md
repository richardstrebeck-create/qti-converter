# LPC board order PDFs (data branch)

Branch `board-orders-data` holds the disciplinary-order PDFs fetched on
2026-09-18 by the four downloaders on branch
`claude/board-orders-scraping-progress-sm425l` (folder `board-orders\`).
It is an orphan branch with no code history. Download it as a zip:

    https://github.com/richardstrebeck-create/qti-converter/archive/refs/heads/board-orders-data.zip

## How to unpack into OneDrive

Each top-level state folder here maps 1:1 onto

    OneDrive - WCU\!Python Tools\LPC Board\Complaint Scraper\state_data\<State>\

Copy the contents of `Vermont\` into `state_data\Vermont\`, and so on. Inside
each state folder:

| Item | Goes to | Meaning |
|---|---|---|
| `*.pdf` at the top level | `state_data\<State>\` | orders classified as counselor (LPC / LCPC / LCMHC / LMHC), named exactly as the downloader names them |
| `review\` | `state_data\<State>\review\` | files the classifier could not settle; OCR these (Foxit), leave the OCR'd copies in `review\`, then run the downloader with `--reclassify` |
| `downloader\*.csv` | `state_data\<State>\downloader\` | the run outputs (manifest, logs, name lists). Copy them over the versions already in the downloader folder so `--reclassify` and skip-if-present work |
| `MISSING.csv` (Kansas, New Hampshire) | `state_data\<State>\` | counselor documents not recovered, with their official URL |
| `recovery_log.csv` (Kansas, New Hampshire) | `state_data\<State>\` | one row per counselor document: where each file came from |

The holding folders (`_all_allied_mental_health\`, `_all_behavioral_health\`)
are NOT included. They hold the dropped other-profession files and duplicates
of everything here; the downloaders recreate them on a re-run (files already
present are skipped, so re-running only fetches what is new).

## Counts

| State | Counselor PDFs | People | In `review\` | Dropped (not delivered) | Missing | Size |
|---|---|---|---|---|---|---|
| Vermont | 45 | 34 | 52 | 41 | 0 | 76 MB |
| Iowa | 106 | 68 | 228 | 469 | 0 | 131 MB |
| Kansas | 76 | 60 | 0 (see OCR note) | 503 (never fetched) | 2 | 45 MB |
| New Hampshire | 18 | 16 | 0 (see OCR note) | 21 (never fetched) | 0 | 15 MB |
| Oklahoma | 39 | | 0 | | | 9 MB |

Total pushed: about 277 MB. No file exceeded the 95 MB single-file limit,
so nothing was skipped for size.

Oklahoma was added to this branch by a separate session (39 LPC orders from
the OBBHL Thentia register, 2010-04 to 2026-08, plus its manifest and
download log); it is not covered by the notes below.

## Vermont (138 PDFs in the OPR allied mental health folder)

Run: `build_vermont_name_list.py` (92 monthly reports parsed, 37 LCMHC
actions, 36 files matched as counselor, 35 as drop, 67 unmatched), then
`download_vermont_orders.py` (all 138 downloaded, 0 failures).

Classification (manifest.csv `category`):

- counselor 45: 36 from the monthly-report name list, 9 from the PDF text
  (unmatched files that turned out to have a text layer).
- drop 41: 35 from the name list, 6 from the PDF text (non-licensed
  psychotherapist, LMFT, applicant).
- review 52: 51 scans with no text layer, plus one readable file
  (`gelineau-yvonne-docket-m20164.pdf`) that is a Board of Nursing order
  misfiled in the allied mental health folder; the script left it in
  review without copying it, so it was copied into `review\` by hand so
  that every review row has a file. Expect it to drop after OCR/reclassify.

Delivered run outputs: `manifest.csv`, `name_match.csv`,
`lcmhc_actions.csv`, `download_log.csv`. Not delivered:
`monthly_actions_all.csv` (unchanged from the working branch) and the
`monthly_reports\` cache (the script re-downloads only missing months).

Still needs OCR: everything in `Vermont\review\` (52 files, mostly pre-2019
dockets and ten 2019+ names that appear in no monthly report).

## Iowa (803 files in the documents.iowa.gov discipline index)

Run: `download_iowa_orders.py` full run (index 803 files, all 803
downloaded, 0 failures, classified by reading each PDF).

- counselor 106 (68 people): 47 from the caption, 59 from the body text
  only (note "profession from body text only"; three of those found the
  licence sentence after page 3). Spot-checked three body-text files: all
  three name an Iowa mental health counselor licence.
- drop 469: social work 398, psychology 59, marriage and family therapy 8,
  applicant 4. Not delivered.
- review 228: 159 scans with no text layer, 13 with an unreadable Type3
  text layer, 45 readable but the profession was not found in the pages
  read, 9 header/body contradictions (6 "social work" caption with a
  counselor body, 2 with an MFT body, 1 MFT caption with a counselor
  body), 2 Word documents (`.docx`, not PDFs). The script copies only the
  scans and unreadable files into `review\` (172); the other 56 were
  copied in by hand so the folder matches the manifest.

Still needs OCR: the 172 scans/unreadable files. The 45 "profession not
found" files and the 9 contradictions need a human read, not OCR.
Delivered run outputs: `actions.csv`, `manifest.csv`, `download_log.csv`.

## Kansas (78 counselor documents in manifest.csv)

The live site (`www.ksbsrb.ks.gov`) still answers HTTP 403 to this cloud
environment, with browser headers. The 78 counselor PDFs were therefore
fetched from the Wayback Machine (`web.archive.org/web/<timestamp>id_/<url>`,
raw bytes, each verified to start with `%PDF`). 76 recovered, 2 missing
(listed in `Kansas\MISSING.csv` with the official URL):

- `Fedosyuk, Sindhuja 26-PC-0031 (2).pdf` (document 5882, no date on the
  site), no capture in the archive;
- `Smithmier, Elise 24-LC-0081.pdf` (document 5822), no capture, with or
  without the trailing ticks segment.

A "Save Page Now" request for both returned an error from archive.org.
Download those two by hand from the official URL on a home machine (the
block affects scripts, not browsers, as far as we know).

The 503 dropped (other-profession) and 2 review (unlicensed, code NL)
documents were never fetched, as the downloader is designed.

OCR note: 47 of the 76 files have little or no extractable text in their
first two pages and will need OCR before `make_text_sidecars.py` reads
them. No `review\` folder exists because Kansas classifies from the index,
not from the PDF.

## New Hampshire (18 counselor documents in manifest.csv)

Same block (`www.oplc.nh.gov` answers 403) and the same Wayback route. All
18 recovered (captures from 2024-07 to 2025-07); `MISSING.csv` is empty
apart from its header. The manifest is from the 2025-06 archived pages, so
actions after mid-2025 are not included.

OCR note: 13 of the 18 files have little or no extractable text in their
first two pages, so these are scans despite being recent.

## What was done to the branch and what was not

- Filenames are exactly what the scripts produce (Windows-safe).
- Committed in batches of at most 200 files, one state per push.
- No git LFS. No PDFs were added to the working branch.
- Each PDF was checked to start with `%PDF-` before commit.
