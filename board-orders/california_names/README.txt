California Board of Behavioral Sciences (BBS): counselor names in the monthly enforcement notices
Built 2026-09-19 from Wayback Machine captures of https://www.bbs.ca.gov/consumers/enforcement_actions.html

SUMMARY
-------
Months covered: 2017-11 through 2026-08 (70 distinct notice months out of 106 calendar months; 36 months have no capture, listed below).
Distinct counselor people (LPCC, APCC, PCCI) in the visible notices: 71, plus 2 known only from commented-out HTML (see caveat 6), 73 in california_counselor_people.csv.
  By license type: LPCC 32, APCC (including the pre-2018 PCCI intern title) 39.
Person-months (one row per person per notice month): 91.
Distinct people by the kind of listing they appeared under (a person can appear under more than one, so the columns add to more than the total):
  Citation                       24
  Accusation                     27
  Decision                       31
  Petition to Revoke Probation   3

Per calendar year (from the notice month, not the capture date). "Listings" are person-months; a person with an Accusation in one month and a Decision in another counts twice.
  Year  Listings  Citation  Accusation  Decision  Petition  LPCC  APCC/PCCI  New people (first seen)
  2017         5         2           2         1         0     2          3  5
  2018        16         3           6         7         0     4         12  13
  2019         6         2           0         2         2     2          4  5
  2020         4         0           1         2         1     2          2  3
  2021         5         0           0         4         1     0          5  2
  2022        11         0           6         4         1     2          9  7
  2023         2         0           1         1         0     0          2  1
  2024        14         5           2         7         0     5          9  11
  2025        14         7           6         1         0    10          4  14
  2026        14         5           3         6         0     9          5  10
Coverage is uneven: 2017 is one month (November), 2026 runs through August, and every year has gaps (see the missing-month list). These are not annual totals for the Board.

FILES
-----
bbs_enforcement_all.csv        Every line of every distinct capture, all six BBS license types (1 row per name per license credential per capture).
                               Columns: capture_timestamp, month_shown, section, name, license_type, license_number, source_url, then
                               month_inferred (see caveat 3), section_group (Citation / Accusation / Decision / Petition to Revoke Probation /
                               Accusation and Petition to Revoke Probation), note, hidden_in_html (yes = the line sat inside an HTML comment and
                               was not displayed; see caveat 6), raw_line (the line as printed). capture_timestamp "live-20260919" is the live page.
california_counselor_names.csv Counselor types only (LPCC, APCC, PCCI), one row per person per notice month, sections joined with ";".
                               name is normalized to First Last; name_as_printed keeps the page text (some 2019-2020 months print Last, First).
california_counselor_people.csv One row per distinct person: person_key, most common name, name variants, license type(s) and number(s),
                               first and last month seen, every month seen, sections, and the months of each kind of listing, plus notes.
README.txt                     This file.

SOURCE
------
The BBS page "Enforcement Actions" shows, under "Latest Enforcement Actions", the text of the Board's monthly subscriber e-mail for ONE month
("Subscriber List Notifications - Enforcement Actions - <Month Year>" or, in 2018, "Enforcement Actions - <Month Year>"): names grouped under
Citations, Accusations, Decisions, Petition to Revoke Probation and variants (First Amended Accusation, Accusation and Statement of Issues, etc.),
each line "First Middle Last, TYPE number". No dates, no case numbers, no links. The site keeps no archive of earlier months.
The Wayback Machine (web.archive.org) holds 132 captures of the page from 2018-01-07 to 2026-09-10 with 78 distinct page versions; all 78 were
downloaded (one per distinct content digest, using the raw "id_" capture form) with a 1.5 second pause between requests, plus the live page on
2026-09-19. Capture list: https://web.archive.org/cdx/search/cdx?url=bbs.ca.gov/consumers/enforcement_actions.html&output=json&filter=statuscode:200&fl=timestamp,digest
Older addresses were checked: the pre-2018 site had /consumer/disciplinary_actions.shtml (115 captures, 2007-06 to 2017-12), /consumer/enf_documents.shtml,
/consumer/enfstats.shtml and /consumer/enfstats_archive.shtml. Those pages carried the verify-a-license text, a glossary and how to request copies;
none of them listed names (checked 2007, 2015, 2016 and 2017 captures). The monthly names list therefore starts with the November 2017 notice
captured on 2018-01-07, and the LPCC license itself dates from 2012, so the first five years of LPCC discipline are not recoverable from this source.
enforcement_actions.shtml never existed (no captures).

MONTHS WITH NO CAPTURE (36)
-------------------------
  2018: 07, 08, 09, 12
  2019: 02, 05, 06, 07, 08, 09, 12
  2020: 02, 04, 07, 11
  2021: 01, 04, 06, 10, 11
  2022: 02, 04, 09, 10
  2023: 01, 03, 05, 07, 09
  2024: 03, 07, 09
  2025: 09, 11
  2026: 03, 06
A month is missing when no capture was taken while that month's notice was on the page (the page is replaced each month). Nothing can be recovered
for those months from this source; the Board's e-mail subscribers and the DCA License Search (per licensee) are the only other records.

CAVEATS
-------
1. Names only. Each line is a name, license type and license number as the Board printed it. There are no dates, case numbers, violations,
   outcomes or documents. A "Decision" line says a decision became effective that month; it does not say what the decision was (revocation,
   surrender, probation, reprimand, dismissal). A "Citation" is an administrative fine, not discipline.
2. Filings and outcomes as of that month, not a history. The notices report what happened in that month. Accusations are charges, not findings.
   The same person appears again when the case ends (Decision) or if probation is later revoked (Petition to Revoke Probation). Nothing before
   November 2017 is included, and gaps (above) mean some people were never captured at all.
3. Month labels. Two captures (2018-06-18 and 2018-06-22) still carried the "April 2018" header over a list that shared few names with the April
   captures of 2018-05-17 and 2018-05-22; they are recorded as month_inferred 2018-05 with a note. All other captures use the month printed.
   The live page and the 2026-09-10 capture both show August 2026.
4. Deduplication. People are matched by license type and number. The PCCI registration (Professional Clinical Counselor Intern) was renamed APCC
   (Associate Professional Clinical Counselor) on 2018-01-01 with the same numbers, so PCCI n and APCC n are one person (Krystal Jaydenne Howard,
   2363). One name appears with two APCC numbers (Ie Run Jung, APCC 3404 in 2022-11 and APCC 15629 in 2024-01, a re-registration); it is merged
   by name and noted. Name spellings vary between months (e.g. Amanda A Ingalls / Amanda Ann Ingalls-Brunzell, LPCC 8332); the number governs.
   People who hold an LPCC or APCC together with another BBS credential (e.g. "AMFT 164442/APCC 23133") are included under the counselor credential.
5. Typing errors on the page were kept but normalized with a note: APPC for APCC (Steven Craig Lund, 2021-07), ACSW for ASW, LMT for LMFT (one
   LMFT line each). Some months print "Last, First"; the name column is reordered and name_as_printed keeps the original.
6. Commented-out HTML. The Board edits the page by commenting out the previous month's sections, and captures sometimes contain those leftovers
   inside HTML comments. They are kept in bbs_enforcement_all.csv with hidden_in_html = yes and no month. Two counselor names appear only there:
   Marina Michelle Nojima, APCC 6392, Decisions, in the comments of the 2023-07-20 capture (month shown June 2023), so from an earlier, uncaptured month (probably May 2023).
   Bruce Eugene Osborn, LPCC 7272, Decisions, in the comments of the 2023-07-20 capture (month shown June 2023), so from an earlier, uncaptured month (probably May 2023).
   They are included in the counselor files with month "before 2023-06".
7. Out of scope types. LMFT, LCSW, LEP, AMFT, ASW and IMF (the pre-2018 MFT intern title) are kept in bbs_enforcement_all.csv only.
   Total visible lines by type across all captures (a name repeats when two captures show the same month):
   LMFT 679, AMFT 376, LCSW 327, ASW 266, APCC 61, LEP 54, LPCC 38, IMF 12, PCCI 3
8. Verification. Every capture was parsed by the same script; 7 lines needed special handling (no comma, comma between type and number, second
   credential on the line). Spot-check any name against the capture in source_url before using it. Nothing was submitted to search.dca.ca.gov.

PER-MONTH LINE COUNTS BY LICENSE TYPE (visible lines, one capture per distinct page version; months shown twice had two differing captures)
----------------------------------------------------------------------------------------------------------------------------------------
  Month    Total  LPCC  APCC  PCCI  LMFT  LCSW  LEP  AMFT  ASW  IMF   Captures
  2017-11     78     2     0     3    35    15    6     0    6   11   20180107225157
  2017-12     33     0     0     0    18    10    2     0    2    1   20180114222011
  2018-01     24     0     1     0    12     4    0     6    1    0   20180209224645
  2018-02     52     0     2     0    22     2    0    15   11    0   20180313215423
  2018-03     46     1     1     0    16     9    0    13    6    0   20180414011718
  2018-04     88     0     4     0    28    16    0    22   18    0   20180517213345, 20180522081731
  2018-05     72     4     4     0    32    10    6    12    4    0   20180618073655, 20180622205837
  2018-06     98     0     4     0    30    24    2    30    8    0   20180720033322, 20180731224331
  2018-10     50     1     0     0    32     4    1     4    8    0   20181130000807
  2018-11     49     0     2     0    13     9    2    12   11    0   20181221222415
  2019-01     74     0     0     0    32    14    2    18    8    0   20190223041906, 20190323041610
  2019-03     74     0     2     0    36    14    0    16    6    0   20190425041817, 20190425051452
  2019-04     75     0     3     0    45     6    0    18    3    0   20190601000616, 20190716001541, 20190817111350
  2019-10     34     1     1     0    14     8    2     6    2    0   20191116010319
  2019-11     21     1     1     0     7     3    0     5    4    0   20191220231439
  2020-01     15     0     1     0     3     4    0     4    3    0   20200229013946
  2020-03     10     0     0     0     3     1    0     3    3    0   20200420011447
  2020-05     22     1     0     0     7     4    1     7    2    0   20200627032227
  2020-06     23     0     0     0     7     5    1     5    5    0   20200828235442
  2020-08     16     1     0     0     2     4    0     6    3    0   20200921031830
  2020-09      7     0     1     0     2     1    0     2    1    0   20201016161950
  2020-10     15     0     0     0     7     1    0     3    4    0   20201222232927
  2020-12      8     0     0     0     2     3    0     2    1    0   20210224203932
  2021-02     23     0     2     0     5     2    0     8    6    0   20210411132204
  2021-03     13     0     1     0     5     1    0     5    1    0   20210413233444
  2021-05     18     0     0     0     3     4    0     5    6    0   20210619062437
  2021-07     19     0     2     0     6     1    0     8    2    0   20210827005334
  2021-08      7     0     0     0     2     1    0     2    2    0   20210926033930
  2021-09     18     0     0     0     8     1    0     4    5    0   20211008234938
  2021-12     13     0     0     0     4     2    0     3    4    0   20220117223856
  2022-01     30     0     0     0    10     6    0     8    6    0   20220217224105, 20220308015602
  2022-03     10     1     1     0     5     0    0     1    2    0   20220427210641
  2022-05     14     0     0     0     9     4    0     1    0    0   20220701162546
  2022-06      4     0     1     0     0     3    0     0    0    0   20220716215156
  2022-07     17     1     1     0     4     3    0     4    4    0   20220825180444
  2022-08     19     0     3     0     8     3    0     4    1    0   20221004103626
  2022-11     13     0     3     0     0     5    0     3    2    0   20221223212253
  2022-12      3     0     0     0     3     0    0     0    0    0   20230204155251
  2023-02     11     0     1     0     4     3    0     1    2    0   20230330171434
  2023-04      9     0     0     0     5     0    0     1    3    0   20230518043526
  2023-06      6     0     0     0     4     0    0     0    2    0   20230720180846
  2023-08      7     0     0     0     1     2    0     2    2    0   20230919164140
  2023-10      9     0     0     0     0     1    0     5    3    0   20231127194829
  2023-11      4     0     0     0     1     1    0     2    0    0   20231207234950
  2023-12     20     0     1     0     5     1    0     6    7    0   20240124232520
  2024-01      8     0     1     0     6     0    0     1    0    0   20240225015950
  2024-02     13     0     0     0     2     3    0     3    5    0   20240319183909
  2024-04     27     0     2     0     6     8    0     6    5    0   20240516043831
  2024-05      6     0     0     0     2     0    1     1    2    0   20240614123409
  2024-06     26     0     2     0    14     2    1     3    4    0   20240716222459
  2024-08     24     1     1     0     4     4    0     7    7    0   20240920182922
  2024-10     16     1     0     0     4     2    0     7    2    0   20241119193924
  2024-11     13     0     0     0     4     5    0     3    1    0   20241206080146
  2024-12     29     3     3     0    10     2    5     4    2    0   20250104131851
  2025-01     13     0     0     0     7     2    0     1    3    0   20250218214606
  2025-02     10     0     0     0     3     5    0     1    1    0   20250309183019
  2025-03     30     0     1     0     8     5    0     9    7    0   20250413200322
  2025-04      9     0     1     0     2     1    2     3    0    0   20250519165841
  2025-05     37     3     0     0    13     6    1     8    6    0   20250614111931
  2025-06     10     1     0     0     6     1    0     0    2    0   20250717192922
  2025-07     30     3     1     0     8     5    3     6    4    0   20250831152239
  2025-08     13     1     0     0     2     2    4     4    0    0   20250909224642
  2025-10     18     0     0     0     4     7    2     2    3    0   20251114091426
  2025-12     31     2     1     0    10     5    0     5    8    0   20260118205233
  2026-01     16     0     0     0     7     4    4     1    0    0   20260215003517
  2026-02     40     2     2     0    16    11    2     2    5    0   20260415184957
  2026-04     35     3     1     0    16     6    2     4    3    0   20260519100736
  2026-05     21     1     0     0     9     4    1     5    1    0   20260626123648
  2026-07     36     3     2     0    11     6    1     4    9    0   20260908034332
  2026-08     34     0     0     0     8    16    0     4    6    0   20260910235703, live-20260919
  (Where a month has two captures, both are counted, so the line count for that month is doubled; the person-month files are deduplicated.)

BOARD MEETING ENFORCEMENT STATISTICS (step 5, 20 minute budget)
---------------------------------------------------------------
Result: the Board publishes NO per-license-type counts of accusations, decisions or citations. Every enforcement table found (quarterly
"Enforcement Update" memos, the annual "Consumer Complaint & Criminal Conviction Report" attached to the Executive Officer Report, the 2019 and
2024 Sunset Review Reports, and DCA's Annual Enforcement Statistics dataset) is aggregate across all BBS license and registration types
(LMFT, LCSW, LPCC, LEP, AMFT, ASW, APCC). The only LPCC-specific figures in the enforcement items are continuing-education audit pass/fail
counts and supervisor audit counts (Attachments B and C of the quarterly update), which are not citations, accusations or orders. So the
names above are the only public per-type view, and the BBS-wide figures below are context for how small a share of Board enforcement the
LPCC/APCC population is (LPCC, APCC and PCCI lines are 102 of the 1,816 visible notice lines in bbs_enforcement_all.csv, about 5.6 percent).

Documents read (all bbs.ca.gov unless noted):
  a. Enforcement Update, Feb 19-20 2026 meeting, item 16 (11 pp.): https://www.bbs.ca.gov/pdf/agen_notice/2026/20260219_20_item_16.pdf
     Q2 FY 2025/26 vs Q2 FY 2024/25. Attachment A chart "Discipline & Probation Data": Accusations Filed 19 vs 12; Statement of Issues Filed
     8 vs 2; Petitions to Revoke Probation Filed 4 vs 13; Citations Issued 33 vs 13; Final Disciplinary Orders 18 vs 23; New Probationers
     11 vs 12; Revocations 2 vs 2; Surrenders 3 vs 1; Cases Referred to AG 27 vs 35.
  b. Enforcement Update, Aug 13-14 2026 meeting, item 19 (8 pp.): https://www.bbs.ca.gov/pdf/agen_notice/2026/20260813-14_agenda_item19.pdf
     FY 2025/26: complaints received 3,050 (Q1 795, Q2 715, Q3 748, Q4 738); 19 complaints referred to the Attorney General; 18 citations
     from the consumer complaint unit; 119 citations and fines for failed CE audits; prior-year complaint totals 2,340 (FY 24/25),
     2,122 (FY 23/24), 1,888 (FY 22/23). No accusation or final-order totals in this item.
  c. Executive Officer Report, Aug 21-22 2025 meeting, item 15, Attachment D "Consumer Complaint & Criminal Conviction Report FY 24/25"
     (PDF p. 43): https://www.bbs.ca.gov/pdf/agen_notice/2025/20250821_22_item_15.pdf
  d. Executive Officer Report, Sept 19-20 2024 meeting, item 8, Attachment D "... Report FY 23/24" (PDF p. 71):
     https://www.bbs.ca.gov/pdf/agen_notice/2024/20240919-20_item_8.pdf
  e. Sunset Review Report 2024, Nov 14-15 2024 meeting, item 17, Table 9a Enforcement Statistics (report pp. 43-46):
     https://www.bbs.ca.gov/pdf/board_minutes/2024/20241114-15_item17.pdf
  f. Sunset Review Report December 2019, Tables 9A and 9B (report pp. 53-54): https://www.bbs.ca.gov/pdf/agen_notice/2019/20191122_sunset.pdf
  g. DCA Open Data, Annual Enforcement Statistics (one aggregate row per board per fiscal year): https://www.dca.ca.gov/data/enforcement.html
     (CSV: https://dca.box.com/shared/static/rbnw5lhg8rqzs3lqgt248jz5r2j2qru9.csv)

BBS-wide counts, all license types, by fiscal year (July to June). Row labels as printed in the source.
  From c and d (annual Consumer Complaint & Criminal Conviction Report):
    FY 2023/24: Consumer Complaints 2,126; Criminal Convictions 845; Referred to Attorney General 114; Accusations Filed 55;
                Statement of Issues Filed 23; Citations Issued 36; Final Disciplinary Orders 59.
    FY 2024/25: Consumer Complaints 2,324; Criminal Convictions 949; Referred to Attorney General 101; Accusations Filed 59;
                Statement of Issues Filed 24; Citations Issued 73; Final Disciplinary Orders 99.
  From e (Sunset Report 2024, Table 9a):
    FY               2019/20  2020/21  2021/22  2022/23  2023/24
    Complaints rec.    1,854    1,803    1,878    1,888    2,127
    Citations Issued     251       32       21       15       36
    Accusations Filed    101       64       51       71       54
    Revocation            23       25       11       21       10
    Surrender             21       18        9       14       11
    Probation only        40       48       23       39       47
    Public Reprimand       1        3        0        0        0
    Other                  3        0        1        0        1
    (No "final disciplinary orders" row; the outcome rows are the closest equivalent. Several probation rows are printed TBD.)
  From f (Sunset Report 2019, Tables 9A/9B):
    FY               2015-16  2016-17  2017-18  2018-19
    Complaints rec.    1,121    1,418    1,375    1,701
    Accusations Filed     96       99      152      100
    Proposed/Default Decisions 37   26       42       62
    Stipulations          58       88       84      126
    Revocation            27       21       39       50
    Voluntary Surrender   17       50       42       54
    Probation             57       66       92       85
    Citations Issued      93      167      286      172
    SOIs Filed            31       32       56       56
    Petitions to Revoke Probation 9  17      14       24
  From g (DCA dataset, rows "Board of Behavioral Sciences"; FY ending 6/30): Citations and fines issued 2016 94, 2017 167, 2018 286,
    2019 172, 2020 243, 2021 33, 2022 18, 2023 15; AG Accusations Filed 2016 96, 2017 99, 2018 152, 2019 100, 2020 101, 2021 64, 2022 49,
    2023 54. DCA's figures differ slightly from the Board's own Table 9a for FY 2020 onward (e.g. 243 vs 251 citations), and two DCA columns
    are unpopulated for early years; the Board's tables are the better source.

Not found: any LPCC or APCC breakdown in the above; no BBS annual report or statistics page exists on bbs.ca.gov; the Enforcement Committee
notice of Jan 8 2016 is a one-page notice with no data. Not read (time budget): the Nov 2025, Feb 2025 and May 2025/2026 quarterly updates,
the Aug 2026 Executive Officer Report (which should carry the FY 2025/26 annual table), and the Senate sunset background papers.

HOW TO EXTEND
-------------
Each month, read the live page (or the subscriber e-mail) and append the LPCC/APCC lines; the Wayback Machine will not necessarily capture
every month. To look up any named person: https://search.dca.ca.gov/ (Board of Behavioral Sciences, license type and number), which requires
passing a CAPTCHA by hand and shows the public record actions and documents. See CALIFORNIA_VERIFICATION_2026-09-19.md for the routes.
Scripts used (kept outside the repository this run): a CDX listing, one fetch per distinct digest with a 1.5 s pause, an HTML parser that
strips comments, walks the "Latest Enforcement Actions" panel by section heading and splits each line at the first license-type token, and a
builder that infers stale month headers and deduplicates by license number.
