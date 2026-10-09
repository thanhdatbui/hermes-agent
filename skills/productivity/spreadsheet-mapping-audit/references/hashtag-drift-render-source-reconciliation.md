# Hashtag Drift Incident: Render Folder vs Source Folder Reconciliation

## Observed pattern
A TikTok profile visibly publishes pet content, while its workbook row contains an automotive keyword and `#oto` tags. This can happen even when the downloader database has already classified the **render folder** as pet content, because a row can carry two different folder identifiers:

- `Folder Video`: the rendered/uploaded media folder, used by the posting runner.
- `video gốc`: the source-folder identifier used by older allocation and sync logic.

Never assume those two numbers describe the same content.

## Bounded O(1) investigation
For one reported channel, bind the account by username and slot before editing:

1. Read the authoritative farm mapping (`farm_account_info` / `account_mapping`) to obtain `(username, machine, tik slot)`.
2. Open only the mapped `Tik<slot>.xlsx` and locate the exact `ID` row. Record `Folder Video`, `video gốc`, `Keyword Video`, and `Hashtag Pool`.
3. Query only the two relevant `state.db` records:
   - `folders WHERE folder_num = <Folder Video>` for the render-folder niche and source channel.
   - `videos WHERE folder = <Folder Video>` for uploader/source corroboration.
4. Check the exact render folder on disk, not a broad directory scan.
5. Compare the visible/profile evidence with the render-folder evidence. If the render folder is pet content but the workbook follows the source-folder label, classify this as mapping drift rather than a hashtag-selector failure.

## Safe correction contract
For a single-account repair, update only:

- the matching `TaiKhoan` row's `Keyword Video` and `Hashtag Pool`;
- the matching `Hashtag theo Folder` row keyed by `Folder Video`;
- `state.db.folders.niche` only if the DB value itself is wrong.

Do not rewrite the `videos` table merely because stale/failed historical rows exist. Do not change `Folder Video`, `video gốc`, account identity, posted count, render status, or source channel unless separately proven and explicitly requested.

Use the exact canonical pet pool when the target is general pet content:

`#thucung #chamsocthucung #thucungdangyeu #meocung #chocung #petvietnam #yeudongvat #thucungvietnam #thucungmoingay #tiktokvietnam #xuhuong #fyp #videohay`

## Backup and readback gate
Before any workbook or database write:

- create an explicit backup beside each target;
- preserve all sheets, formatting, formulas, and unrelated cells;
- use a same-directory temporary workbook and atomic replace where supported;
- update with a narrow cell/row predicate, not a positional guess;
- reopen the workbook and query the DB again;
- report exact changed cells/fields and backup paths.

A repair is not complete until readback shows the requested keyword/pool on both relevant workbook surfaces and the DB state is consistent. A green hashtag-selector unit test alone does not prove metadata alignment.

## Regression prevention & Cron Reversion Trap
Any sync job that derives hashtags from folder metadata (e.g. `sync_all_tik_keywords.py` running on a 15-minute cron) must explicitly declare whether it keys on `Folder Video` or `video gốc`:
- If the sync job keys on `video gốc` (e.g. `f_src = int(vg_val)`), patching ONLY `TikN.xlsx` and `state.db.folders.folder_num = <Folder Video>` will cause the 15-minute cron to immediately overwrite the row back to the old niche on its next run! Both `video gốc` AND `Folder Video` in `state.db` must be updated to the correct niche slug.
- **Legacy 279-folder blindspot**: Automated uploader-based niche mappers only detect mismatches for folders with known `uploader` / `source_channel` strings (e.g. YouTube downloads). 279 / 640 folders from early direct TikTok downloads lack `videos` table entries and retain synthetic modulo-mapped niches from `niches_pool.txt` (e.g. folder 137 = index 56 `oto`). When auditing whole-farm hashtag drift, identify folders lacking uploader metadata and audit them via audio/video inspection rather than assuming clean state from DB uploader queries alone.

