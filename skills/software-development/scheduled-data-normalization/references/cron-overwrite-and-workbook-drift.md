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

## Runtime consumer and line-ending traps

1. **Runtime consumer mapping (`KEYWORD_HASHTAGS`)**:
   Adding a category to the source database and the mapping text file is necessary but not always sufficient. If the downstream consumer/selector module defines an internal keyword dictionary, the slug must also be added there; otherwise, runtime hashtag generation falls back to viral-only or unmatched behavior.

2. **Windows CRLF line-ending mutation**:
   Editing mapping text files on Windows can silently convert newlines from LF to CRLF (`\r\n`). In git repositories, this causes whole-file churn in `git diff --numstat` (e.g., 80+ lines replaced), violating O(1) change constraints. Always preserve or normalize byte-level LF endings when modifying mapping files.

3. **Log telemetry assertions across test loops**:
   When testing generator/selector telemetry across multiple input variations in pytest, `caplog.records` accumulates across iterations. Asserting on `next(...)` will inspect stale logs from earlier loop steps. Always take the latest record `caplog.records[-1]` or call `caplog.clear()` between iterations.

4. **Output folder index vs canonical source folder trap ($F_{out}$ vs $F_{src}$)**:
   In multi-slot farm workbooks maintaining both output render folders ($F_{out} = (\text{Máy} - 1) \times 8 + \text{Slot}$) and source folders ($F_{src} = (\text{Slot} - 1) \times 80 + m_{idx}$):
   If an existing column named `video gốc` mistakenly holds $F_{out}$, a generator that queries the authoritative database using `video gốc` will look up the wrong folder's category (e.g., folder 141 bakery instead of folder 338 student skit) and systematically clobber all target accounts.
   Rule: Never trust an existing `video gốc` column in a consumer workbook without reconciling it against the canonical slot/machine coordinate formula or the reference mapping sheet. When syncing, calculate $F_{src} = (\text{Slot} - 1) \times 80 + m_{idx}$ or read the 1:1 mapping from the reference sheet, and update both the source ID column and the resolved labels/pools simultaneously to eliminate drift at its source.

5. **The "Blind Syntax-Only Test Suite" Trap (Semantic vs Syntactic Parity)**:
   A dangerous false sense of security occurs when test suites only verify syntactic presence:
   `assert acc["keyword"] != ""` and `assert 3 <= len(tags) <= 5`.
   When a normalization script mistakenly clobbers an account (e.g. overwriting student comedy with bakery), the field is non-empty and generates valid tag counts, so tests pass 100% green while data is completely corrupted.
   Rule: Normalization tests must verify **Semantic Parity**:
   Assert that every account's `Keyword Video` and `Hashtag Pool` matches the authoritative reference (`Hashtag theo Folder` or source database record for $F_{src}$) 1:1 across all operational workbooks.

6. **Cluster Machine Offset & Boundary Guard**:
   Dual-cluster architecture has distinct machine ranges:
   - Cluster A (e.g. Kibe): $M \in [1..80] \implies m_{idx} = M$.
   - Cluster B (e.g. Admin): $M \in [201..280] \implies m_{idx} = M - 200$.
   Never write unchecked ternary expressions like `m if m <= 80 else m - 200`. Explicitly define constants (`KIBE_MAX_MACHINE = 80`, `ADMIN_MIN_MACHINE = 201`, `ADMIN_MAX_MACHINE = 280`, `ADMIN_MACHINE_OFFSET = 200`) and reject or flag any machine value outside `[1..80]` and `[201..280]` to prevent boundary overflow and silent mapping corruption.

7. **Case-Insensitive Workbook Filename Resolution**:
   On Windows/OneDrive file sync or legacy naming (e.g. `Tik3.xlsx` vs `tik3.xlsx`), hardcoded case matching in file synchronization loops can cause specific workbooks to be skipped silently.
   Rule: Always implement case-insensitive fallback (`f.name.lower() == target_name.lower()`) when locating workbooks in target directories.

8. **Structured Telemetry & No-Silent-Swallow Pattern**:
   Do not catch broad `Exception` silently with `pass` in workbook loading or parsing routines. Log specific warnings (`OSError`, `KeyError`, `ValueError`).
   Expose structured JSON telemetry summary (`SYNC_KEYWORDS_SUMMARY`) with `workbooks_checked`, `total_updated`, `skipped_rows`, `error_count`, and `status` to enable automated downstream audit and alerting.

9. **Multi-Layered Test Evidence for Closeout Review**:
   Closeout gate reviewers require evidence at multiple tiers:
   - Tier 1: Unit tests for pure calculation logic (`resolve_source_folder`, boundaries, invalid types).
   - Tier 2: Integration tests using `tmp_path` generating mock multi-sheet workbooks (`TaiKhoan` + `Hashtag theo Folder`), asserting data mutation and structural integrity.
   - Tier 3: Operational parity test across live workbooks ensuring 100% of accounts match authoritative source.

10. **The Dual-Cluster Single-Authority Shadowing Trap**:
   When managing dual clusters (e.g. Cluster A: Kibe, Cluster B: Admin) that maintain independent raw media directories (`video goc` vs `video goc may 2`) and independent crawl sources/databases:
   - A single-authority sync script configured with `FARM_DIRS = [Cluster_A, Cluster_B]` that queries only Cluster A's database will forcibly overwrite Cluster B's workbooks with Cluster A's categories and hashtags.
   - Even if an operator manually fixes Cluster B's workbooks, the scheduled cron sync will clobber them on the very next scheduled cycle.
   - Rule: Before running or scheduling bulk multi-cluster syncs, verify whether clusters share the same source-of-truth database or maintain separate cluster authorities. When media sources are independent, sync scripts MUST partition cluster authorities (querying each cluster's own store) or be strictly scoped to the targeted cluster only.
