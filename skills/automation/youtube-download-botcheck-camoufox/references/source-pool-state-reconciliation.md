# Source-pool/state reconciliation checklist

## 1. Baseline

Record before changing anything:

- `git status --short --branch`
- active downloader command lines/processes
- `state.db` path, output root, source manifest, ledger directory
- MP4 count and newest file under the target folder

Do not infer success from a wrapper exit code or `RECOVERED_INTERRUPTED` count.

## 2. State queries

```sql
SELECT folder_num,niche,platform,source_channel,video_count,status,completed_at
FROM folders WHERE folder_num=?;

SELECT status,rejection_reason,COUNT(*)
FROM videos WHERE folder=? GROUP BY status,rejection_reason;

SELECT lower(source_channel),platform,niche,status,COUNT(*)
FROM videos WHERE folder IS NULL
GROUP BY lower(source_channel),platform,niche,status;
```

Compare DB rows with actual `*.mp4` files. Treat `.part.mp4` as incomplete.

## 3. Candidate validation

For each cached `discovered` candidate selected for resume:

- match source URL case-insensitively, platform, and niche;
- probe metadata before queueing;
- reject unavailable URLs and duration over 300 seconds;
- do not count unknown duration as valid until metadata is hydrated;
- preserve the candidate's source channel; never silently merge channels into one folder.

If a channel has fewer than the required valid candidates after probing, report `INSUFFICIENT_POOL` for that source and select a different qualified source rather than declaring the downloader globally broken.

## 4. Proxy boundary test

Workbook forms may be `host:port:user:password` or `http://host:port:user:password`. Normalize once at the input boundary and verify the exact value used by the worker (`_worker_proxy()`), not only the parser unit function. URL-encode reserved password characters such as `#`, `!`, `@`, and `:` when constructing a URL for yt-dlp.

A minimal regression assertion:

```python
assert format_proxy("http://test.example:5101:u:p#x!") == \
       "http://u:p%23x%21@test.example:5101"
```

## 5. Canary and resume completion

Use one folder, one fixed source, `--parallel 1`, and the production state/output/ledger paths. Verify during and after execution:

- a new non-empty MP4 appears;
- DB status changes to `downloaded`;
- no zero-byte file is accepted;
- `avatar.jpg` and the folder completion state are produced when the target is reached;
- if the canary is interrupted, run exactly one resume and verify no `downloading` rows remain for that folder;
- final `folders.status='complete'`, `video_count` equals target, and clean MP4 count is at least target.

Only after this evidence should the batch launcher be resumed or scaled.

## 6. Common misleading evidence

- `RECOVERED_INTERRUPTED folders=N videos=M`: state recovery, not new downloads.
- `exit code 0` with `INSUFFICIENT_POOL`: orderly skip, not successful download.
- `This channel does not have a shorts tab`: source listing failure/fallback signal; inspect candidate pool and duration, do not blindly accept `/videos` content.
- DB `source_channel` differing only by case: same source; use case-insensitive matching.
- MP4 count above DB `downloaded`: a stopped process may have written files before its DB commit; resume and reconcile instead of deleting/resetting immediately.
