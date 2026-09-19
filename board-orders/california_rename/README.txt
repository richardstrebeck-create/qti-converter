CALIFORNIA LPCC ORDER RENAMER

Identifies and renames the California Board of Behavioral Sciences (BBS)
order PDFs for a fixed list of 29 Licensed Professional Clinical Counselors
(LPCC). You saved these orders by hand from the DCA License Search into
state_data\California\ and ran OCR on them; this tool reads the OCR text,
works out which of the 29 people each PDF belongs to, and renames the
matches to the project's file-name style:

    Lastname, Firstname LPCC <number> <effective date>.pdf
    for example  Osborn, Bruce Eugene LPCC 7272 2023-05-10.pdf

HOW IT DECIDES

- License number first: it looks for the LPCC license number printed next
  to an "LPCC" marker (for example "LPCC 7272", "LPCC No. 7272",
  "Licensed Professional Clinical Counselor License No. 7272"). This is the
  reliable key and avoids matching a stray number elsewhere in the order.
- Name as backup: if OCR dropped the license number, it matches the
  licensee's name (including the known spelling variants) and marks the row
  "name only" so you can glance at it.
- A PDF that matches none of the 29, or more than one, is LEFT ALONE and
  listed so you can look at it by hand.

The effective date in the file name is best-effort: it takes the order's
"effective" date when it can find one, otherwise the "Dated:" date,
otherwise the latest date in the document, otherwise "undated". Check the
dates in the plan; OCR sometimes garbles them.

HOW TO RUN

1. Install once:  py -m pip install pymupdf
2. Put rename_california_files.py and Run_Rename_California.cmd INTO the
   state_data\California\ folder, beside the PDFs.
3. Double-click Run_Rename_California.cmd. This is a DRY RUN: it prints the
   plan (each PDF and the name it would get), writes rename_plan.csv, and
   changes nothing.
4. Read the plan. When it looks right, open a Command Prompt in that folder
   and run:  py rename_california_files.py --apply

The dry run also prints which of the 29 targets have no PDF in the folder,
so you can see who is still missing.

NOTES

- The 29 targets are built into the script (license number, name, name
  variants). To change the list, edit the TARGETS block near the top.
- Nothing is deleted. Files already named correctly, or left alone, are not
  touched. Re-running is safe.
- One judgement call: for Nga Caroline Tran Ryan (LPCC 997) the last name
  was taken as "Ryan"; if her orders read differently, rename by hand or
  edit her TARGETS line.

Built 2026-09-19. Companion to california_names\ (the BBS name index) and
CALIFORNIA_VERIFICATION_2026-09-19.md (why California orders are saved by
hand).

-------------------------------------------------------------------------
UPDATE 2026-09-19: LPCC-only scope, three more LPCCs, and the retrieval list
-------------------------------------------------------------------------
Scope is licensed LPCC only (no APCC/AMFT associates or interns).

Three licensed LPCCs turned up in the saved orders but were not on the
original 29-name list; they are now in TARGETS so the tool names them:
  - Guillermo Jesus Alvarez, LPCC 1067 (the BBS name index showed him under
    Accusation only, but his case resolved and the order is in the folder)
  - Kevin Scott Thorpe, LPCC 240 (not in the BBS index at all)
  - Elizabeth Marie Still, LPCC number not yet known (matched by name; read
    her LPCC number off her order PDF and put it in her TARGETS line so the
    file name carries the number)

The associate and marriage-and-family files in the folder (APCC, AMFT, PCC
Intern, applicants) are OUT of scope. Run with --move-nonlpcc to move every
file the tool leaves alone into a _not_LPCC subfolder, so state_data\California\
holds only LPCC orders:
    py rename_california_files.py --apply --move-nonlpcc

dca_lookup_worklist.csv is the retrieval list. Of the 29 licensed LPCCs,
only Osborn and Ingalls were saved so far; the other 27 still need their
orders. For each "no" row, open https://search.dca.ca.gov/ , pick Board of
Behavioral Sciences and license type Licensed Professional Clinical
Counselor, enter the license number, pass the CAPTCHA by hand, open the
record, and save every document under Public Documents into
state_data\California\ . Then re-run this tool to name them.

Three rows are marked CHECK (Atwood 4997, Miller 15, Reagan 7527): the index
shows them under Accusation only. Look each up in DCA; download the order
ONLY if the search shows a Decision or Citation. If the accusation is still
the only entry, leave them out (charges are not discipline).
