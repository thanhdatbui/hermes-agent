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
- Counting `*_stats*`, backup, or temporary workbooks as live account workbooks.
- Trusting a worker's success report without coordinator read-back.
- Editing while the scheduler is concurrently writing.
- Declaring DONE after save without post-cycle verification.

## Evidence template

Report: authority before/after; mapping before/after; expected/generated files; rows checked; empty required-field counts; target rows before/after; post-cycle parity; backups; verdict (`DONE`, `PARTIAL`, or `BLOCKED`).

## Reference

See `references/cron-overwrite-and-workbook-drift.md` for a concrete dual-cluster workbook incident and verification checklist.
