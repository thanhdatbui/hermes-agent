# SQLite VACUUM & Hermes Gateway Lock Safety

## Root Cause
When SQLite executes a standard `VACUUM` (or `VACUUM INTO <path>`) on a large database (e.g. `state.db` > 10GB):
1. SQLite acquires an **EXCLUSIVE write lock** for the entire duration of the copy and page re-allocation process.
2. If `VACUUM` is run on the same drive (e.g. `C:`), it allocates temporary journal and shadow pages requiring up to **2x the database size in free disk space**. If available space is lower than required, SQLite fails with `SQLITE_FULL` (`database or disk is full`).
3. While the exclusive write lock is held (often lasting several minutes for 10GB+ DBs), any running **Hermes Gateway process** attempting to write incoming Telegram/Discord session turns will time out (5s lock timeout), throwing `"the turn was stopped because session storage could not be written"` and dropping user messages.

## Operational Rules
- **NEVER run `VACUUM` or `VACUUM INTO` on `state.db` while Hermes Gateway is active/serving traffic.**
- **Pruning vs Vacuuming:** Running `hermes sessions prune --older-than <N>d` safely removes records and returns pages to SQLite's internal `freelist`. SQLite will automatically reuse these freelist pages for future message storage without needing physical file truncation via `VACUUM`.
- If an offline compact is strictly needed:
  1. Stop all Gateway and background worker processes (`Stop-Process -Name hermes, python`).
  2. Perform `VACUUM INTO` to a secondary high-capacity drive (e.g. `D:\`).
  3. Swap the compacted database file.
  4. Restart Hermes Gateway services.
