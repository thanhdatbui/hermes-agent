---
name: scheduled-data-normalization
description: "Use when cron overwrites normalized data."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [cron, sync, normalization, source-of-truth, parity]
---

# Scheduled Data Normalization

Use this class skill when a scheduled generator repeatedly restores stale or incorrect values in workbooks, reports, manifests, or caches.

## Core rule

Never repair only a generated output when a scheduler can overwrite it. Trace and repair the full path:

`authoritative state -> label/slug mapping -> pool/config selection -> generator -> generated outputs -> consumer`.

## Workflow

1. **Freeze scope.** Record the scheduler/job, cadence, source store, generator, exact output set, expected row count, target records, and acceptance criteria.
2. **Read the live source before editing.** Query the authoritative record and capture the generated row before and after one isolated sync or scheduler cycle.
3. **Check mapping completeness.** Every new slug/category needs a label and canonical pool in the mapping source consumed by the generator. Missing mappings can trigger stale fallback values.
4. **Repair authority and output together.** Back up the source and outputs, update the source plus mapping, regenerate all intended clusters, and preserve unrelated workbook structure and credentials.
5. **Separate operational files from lookalikes.** Define the exact operational population (for example, 8 files per cluster). Exclude statistics workbooks, backups, temporary files, and historical exports from parity totals.
6. **Verify independently.** Re-open live source and outputs from the coordinator. Assert exact target rows, source/output parity, expected file and row counts, zero empty required fields, and no overwrite after the next cycle.

## Drift scanning

Run operational parity and exploratory drift scans separately. Uploader/channel-name heuristics are candidate signals only, not proof. Require source/video evidence before bulk mutation. Never infer that a mixed scan's empty-cell count describes the operational population.

## Failure patterns

- Editing only the workbook while the source still contains the old category.
- Adding a source slug without adding it to the generator's label/pool mapping.
- **Scrape/Extraction Partial-Failure Overwrite Trap (Ghi bậy bạ khi cào thiếu / không tra được)**: When automated periodic trackers/crawlers (such as daily account stats crawlers) fail to extract specific fields (e.g. `followerCount` or `followingCount` returning 0, empty, or missing due to anti-bot WAF, mobile header variations, or rate-limits) while other fields (heart, video, status) remain intact, writing literal 0 into the persistent database clobbers valid historical metrics. Downstream consumers (dashboards, anomaly detectors) then observe a massive -100% delta drop (e.g., 245 -> 0 = -245) and raise false-positive emergency alerts (`⚠️ TỤT BẤT THƯỜNG`).
  - *Invariant Rule*: When an automated crawler cannot extract data or returns 0/missing for an active account with historical positive values, it MUST NOT write fake zeros to overwrite valid data. Instead, it must forward-fill / preserve the last known good historical values (`prev_follower`, `prev_following`) independently per field (never couple following protection to follower==0), set deltas to 0, emit structured warning telemetry (`zero-scrape telemetry: <field> preserved for <user>`), and provide unit tests verifying both independent field branches with `caplog`. In dashboards and anomaly detectors, a drop to 0 while hearts/likes remain healthy must be treated as scrape-glitch, not a real anomaly drop.
- The $F_{out}$ vs $F_{src}$ Query Trap: Reading an output/render folder ID ($F_{out} = (M-1)*8 + S$) instead of the true canonical source folder ID ($F_{src} = (S-1)*80 + M$) when querying authoritative records. When an output folder ID happens to match an unrelated category in the source database, the sync script silently and systematically overwrites correct categories with wrong ones (e.g. overwriting student comedy with bakery).
- **Dual-Cluster Single-Authority Shadowing Trap**: When managing dual clusters (e.g. Kibe and Admin) with independent media sources (`video goc` vs `video goc may 2`), a scheduled sync script configured with only one cluster's authority database will iterate over both cluster workbook directories and silently clobber the second cluster's workbooks with the first cluster's categories. Even if an operator repairs the second cluster's workbooks, the scheduled sync will re-contaminate them on the next cycle unless each cluster queries its own authoritative store or multi-cluster sync is properly partitioned.
- **False-negative audit drift**: When audit/verification scripts lack dictionary mappings for newly added or specialized niches (e.g. missing baby/family keywords), unmapped transcriptions return None and default to `mismatch=False`. The auditor falsely passes contaminated accounts, allowing schedulers to keep overwriting them with wrong categories.
- **Missing hard-lock registry check in sync scripts**: When sync scripts blindly copy from upstream state without checking a manual lock registry (`manual_avatar_protected_folders.json` / `is_folder_avatar_protected`), operator hand-fixed values in workbooks or databases get clobbered on the very next scheduled cycle.
- Relying on syntactic-only assertions (e.g. "cell is non-empty", "count is 3..5") which pass 100% green while semantic categories are completely clobbered.
- Using unchecked magic numbers for cluster machine offsets without boundary validation, causing out-of-range machines to silently map into corrupted source folders.
- Forgetting downstream consumer dictionaries (e.g. `KEYWORD_HASHTAGS` in selector code).
- Windows CRLF newline conversions exploding git diff numstat on mapping files.
- Asserting on cumulative `caplog.records` in pytest loops instead of `caplog.records[-1]`.
- Counting `*_stats*`, backup, or temporary workbooks as live account workbooks.
- Trusting a worker's success report without coordinator read-back.
- Editing while the scheduler is concurrently writing.
- Declaring DONE after save without post-cycle verification.
- **Header Renaming without Consumer Code Alignment (Đổi header Excel làm generator định kỳ ghi đè rác)**: Standardizing or clarifying column headers in authoritative workbooks (e.g., `Folder Video` -> `Folder Video (Slot 1-640)`) without expanding alias lists in generators and consumers. Exact string/tuple checks fail to find the column, causing generators to fall back to sequential row assignment, scramble slot order (e.g. M76 slot 8 -> slot 7), and periodically overwrite runtime safe workbooks on every cron cycle. Generators MUST use multi-alias substring matching and fail-closed instead of falling back to sequential assignment.
- **Hashtag Reversion & Multi-Cluster Authority Desync (Hashtag bị lộn hoài do cron đè CSDL gốc)**: Editing keywords/hashtags in workbooks without updating the upstream authority database causes periodic cron watchdogs (e.g. 15m sync) to silently overwrite workbooks back to stale scraped categories. Sync scripts omitting secondary clusters (e.g. Admin) or ignoring manual lock markers (`.manual_hashtag_locked`) perpetuate category drift across the farm.
- **Unchecked Row-Append Column Drift (Dời cột khi ghi đè / append dữ liệu mới)**: When scripts append newly registered or modified accounts into authoritative workbooks without strict schema enforcement, misaligned field counts shift columns to the right (e.g., writing timestamp into `device ID` and pushing real serials into nameless column 11). Downstream batch runners (2FA, Avatar, Login) fail preflight check against hardware mapping (`PROXYgandienthoai.xlsx`) and skip accounts massively. Normalization MUST re-align drifted columns against hardware ground truth before running batches.

## Evidence template

Report: authority before/after; mapping before/after; expected/generated files; rows checked; empty required-field counts; target rows before/after; post-cycle parity; backups; verdict (`DONE`, `PARTIAL`, or `BLOCKED`).

## Reference

- See `references/cron-overwrite-and-workbook-drift.md` for a concrete dual-cluster workbook incident and verification checklist.
- See `references/hashtag-reversion-and-cron-source-of-truth-trap.md` for the 3 root causes of periodic keyword/hashtag clobbering, multi-cluster desync, and the 4-step immutable lock protocol.
- See `references/scrape-partial-data-fail-closed-preservation.md` for handling partial scraper extractions, preventing false zero-metric overwrites, and protecting downstream anomaly detectors.
- See `references/header-renaming-and-scheduled-generator-desync.md` for the header renaming desync failure mode, multi-alias matching rules, and the 5-tier audit protocol.
