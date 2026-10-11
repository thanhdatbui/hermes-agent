# Cron overwrite and workbook drift

## Incident pattern

A manual correction changed `Tik4.xlsx` to a history-related keyword, but the next observation showed the old `Mẹ và bé` value again. The live source database still contained the old niche for folder 412, while the generator consumed that database and rewrote both Kibe and Admin workbooks every 15 minutes.

A second issue was mapping incompleteness: the generator's `niches_pool.txt` did not contain the new `lichsu` slug. Updating only the database could therefore still produce an incorrect label or fallback hashtag pool.

## Correct evidence sequence

1. Read the scheduler job and actual script path.
2. Query the live source row, not a backup or a prior report.
3. Inspect the generator's mapping loader and fallback behavior.
4. Re-open the live workbook and identify the exact target row by machine/account/folder, not by a broad keyword search.
5. Repair the source record and the mapping entry before regenerating outputs.
6. Re-open all intended outputs and verify exact values.
7. After one isolated or scheduled sync cycle, re-open the source and outputs again. A saved workbook before this check is only `PARTIAL`.

## Population-count trap

The operational parity set was 16 workbooks: 8 Kibe plus 8 Admin, with 80 account rows each (1,280 rows). A broad glob also picked up `tiktok_stats_farm.xlsx` and backup/history workbooks; that produced misleading totals such as 1,952 rows and false empty-field counts. Exclude `*_stats*`, `.bak`, temporary, and historical files from operational parity. Report exploratory scans separately.

## Heuristic-scan rule

Uploader/channel names can identify candidates but do not prove a niche. For bulk changes, require corroborating source metadata or video evidence. A candidate mismatch list is not a mutation plan.

## Coordinator verification fields

- source value before/after;
- mapping value before/after;
- exact live workbooks checked;
- rows per workbook and total rows;
- empty keyword/hashtag counts in the operational set;
- target row before/after;
- post-cycle source/output parity;
- backup paths;
- final verdict: `DONE`, `PARTIAL`, or `BLOCKED`.

Worker summaries are untrusted until these fields are independently re-read by the coordinator.
