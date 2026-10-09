# Folder niche audit completeness checklist

Use this reference before syncing `state.db` into Tik workbooks.

## Required evidence table

For each target folder, record:

| Field | Required check |
|---|---|
| Expected range | Is the folder inside the declared scope (for example 1..640)? |
| `folders` row | Exists, current niche, source channel, status, video count |
| `videos` evidence | Matching rows, uploader/source channel, niche distribution, output paths |
| Historical evidence | Downloader DB / manifest / source metadata when current DB is sparse |
| Filesystem evidence | Actual source folder and media provenance, when requested |
| Decision | `CONFIRMED`, `REVIEW`, or `DO_NOT_SYNC` with reason |

## Coverage gate

1. Count expected folders and folders present in the current DB.
2. Count folders with at least one trustworthy source signal: source channel, uploader/video rows, or verified historical provenance.
3. Print the missing/evidence-poor folder list.
4. Do not describe the result as a complete scan if any in-scope folder was skipped; report `partial coverage` and the exact counts.

## Single-folder recovery recipe

1. Resolve the account row by Tik workbook, machine, account ID, and `video gốc`.
2. Inspect the current `state.db` folder row.
3. If the current row is sparse or contradictory, inspect the historical downloader DB and group videos by niche/uploader/source channel.
4. Prefer a clear majority plus source-channel identity. If the folder contains mixed content, retain the provenance explanation and mark ambiguous cases for review rather than guessing.
5. Update the DB only after the evidence is sufficient; preserve a backup.
6. Run the canonical sync once.
7. Reopen the exact Kibe/Admin workbook rows and verify both `Keyword Video` and `Hashtag Pool`, plus the `Hashtag theo Folder` row.

## Failure pattern to avoid

A previous folder-12 incident showed the danger of this sequence:

- the workbook once had the correct niche;
- a broad “all folders” audit only evaluated folders with usable current metadata;
- folder 12 had a stale `mevabe` row and no current source/uploader evidence, so it was silently skipped;
- the sync then copied `mevabe` back into the workbook.

The durable lesson is: **a sync pass proves propagation, not classification**. A stale DB row must be independently reclassified before it is allowed to overwrite derived workbook data.
