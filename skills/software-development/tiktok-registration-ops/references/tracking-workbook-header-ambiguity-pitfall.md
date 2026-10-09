# Pitfall: Tracking Workbook Header Aliases Ambiguity in Tests

## Context
In `scripts/tiktok_target_eligibility.py`, `load_registered_mailboxes` validates workbook headers via `_header_indexes(worksheet, TRACKING_HEADER_ALIASES, ...)`.

`TRACKING_HEADER_ALIASES` contains:
- `stt`: `{"stt", "may", "machine", "machine stt", "so may", "so thu tu"}`
- `tiktok_id`: `{"id", "tik tok id", "tik tok username", "tiktok", "tiktok id", "tiktok username", "username"}`
- `email`: `{"email", "e mail", "gmail", "gmail address", "mail"}`

## The Pitfall
When creating mock workbooks / fixtures in tests (e.g. via `openpyxl`), providing realistic-looking column headers like:
```python
ws.append(["Máy", "STT", "ID", "Pass", "Mail", "GMAIL"])
```
causes `_header_indexes` to fail immediately with:
```
scripts.tiktok_target_eligibility.TargetEligibilityError: TRACKING_WORKBOOK_HEADERS_AMBIGUOUS: stt
```
because:
1. Column 0 `"Máy"` normalizes to `"may"`, matching `stt`.
2. Column 1 `"STT"` normalizes to `"stt"`, also matching `stt`.
3. Column 4 `"Mail"` normalizes to `"mail"`, matching `email`.
4. Column 5 `"GMAIL"` normalizes to `"gmail"`, also matching `email`.

`_header_indexes` fails closed whenever any required alias key matches more than one column header.

## Rule for Test Fixtures & Tracking Workbooks
1. Exactly ONE column must match each key in `TRACKING_HEADER_ALIASES` (`stt`, `tiktok_id`, `email`).
2. Any auxiliary columns in mock headers must use neutral names that never collide with any alias:
   - Bad: `["Máy", "STT", "ID", "Pass", "Mail", "GMAIL"]`
   - Good: `["Máy", "Index", "ID", "Pass", "Note", "GMAIL"]`
3. If matching positional indexing (`TRACKING_POSITIONAL_COLUMNS = {"stt": 0, "tiktok_id": 2, "email": 5}`), ensure:
   - Index 0 matches `stt` (e.g. `"Máy"`)
   - Index 2 matches `tiktok_id` (e.g. `"ID"`)
   - Index 5 matches `email` (e.g. `"GMAIL"`)
   - Indices 1, 3, 4 use neutral names (e.g. `"Col_STT"`, `"Pass"`, `"Extra"`).
