# Live batch recovery reference

Use this as a compact incident checklist; do not treat it as proof that a current run is healthy.

## Evidence pattern

- A downloader process can be alive while producing no files.
- Check the exact command line and parent/child tree; repeated wrapper launches can create two writers against the same state DB.
- Compare: `state.db` status counts, folder status counts, latest report mtime/size, latest clean MP4 mtime, and the fatal traceback.
- `sqlite3.OperationalError: database is locked` identifies a state-transaction concurrency failure, but fixing the lock does not prove the source pool or resume path works.

## Resume invariants

- Reset both folders and videos stranded in `reserved`/`downloading`.
- Restore source/channel claims for the same machine and folder; do not globally free a claim that another machine owns.
- A same-machine/same-folder claim may resume; a same source claimed by another folder or machine must remain blocked.
- Reuse already-discovered candidates from the state DB when crawling the source again returns no candidates. `INSERT OR IGNORE` alone does not enqueue an existing `discovered` row.
- Validate folder niche/platform/source niche/platform before download. A stale row can point a folder at an unrelated source and make the batch report `INSUFFICIENT_POOL` without downloading.

## Canary acceptance

A canary is green only when all are true:

1. One real MP4 appears under the intended folder.
2. File size is non-trivial and a media probe reads duration/container.
3. The matching DB row is `downloaded` and has the same folder/output path.
4. The report records the same source/channel and folder.
5. The clean output count or newest mtime increases after launch.

If only the process-start banner or `RECOVERED_INTERRUPTED` appears, the canary has not passed.

## Reporting

Use four short labels: `Action`, `Verified`, `Blocker`, `Next`. Avoid unrelated farm/process commentary for an independent downloader.
