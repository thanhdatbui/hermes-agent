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
- The $F_{out}$ vs $F_{src}$ Query Trap: Reading an output/render folder ID ($F_{out} = (M-1)*8 + S$) instead of the true canonical source folder ID ($F_{src} = (S-1)*80 + M$) when querying authoritative records. When an output folder ID happens to match an unrelated category in the source database, the sync script silently and systematically overwrites correct categories with wrong ones (e.g. overwriting student comedy with bakery).
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

## Evidence template

Report: authority before/after; mapping before/after; expected/generated files; rows checked; empty required-field counts; target rows before/after; post-cycle parity; backups; verdict (`DONE`, `PARTIAL`, or `BLOCKED`).

## Reference

See `references/cron-overwrite-and-workbook-drift.md` for a concrete dual-cluster workbook incident and verification checklist.
