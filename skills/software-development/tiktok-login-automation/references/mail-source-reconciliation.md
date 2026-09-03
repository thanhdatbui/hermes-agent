# Mail-source reconciliation for unregistered TikTok candidates

## Canonical sources

- Mail inventory: `D:\OneDrive\TaadaaData\kibe\gmail_clean_v2.xlsx`, sheet `Gmail Accounts`
  - assignment: `số máy`
  - mailbox: `tài khoản gmail`
- TikTok tracking: `D:\OneDrive\TaadaaData\kibe\taikhoan_dat_v2_updated .xlsx`, sheet `Tài Khoản`
  - mailbox column: `GMAIL`
  - `ID` and `NGÀY TẠO` are tracking fields, not a sufficient standalone registration test
- Machine mapping: `D:\OneDrive\TaadaaData\kibe\taikhoan_run_safe.xlsx`, sheet `Accounts`
  - `May` + `Device ID`

## Bounded algorithm

1. Load both workbooks read-only with `openpyxl`.
2. Normalize mailbox values with `strip().casefold()`.
3. Build `dat_v2_emails = {row[GMAIL]}`.
4. Iterate `gmail_clean_v2` and select rows whose normalized mailbox is not in `dat_v2_emails`.
5. Apply `endswith('@hotmail.com')` only to the difference set when Hotmail is requested.
6. Keep the source machine number, then resolve it to a live serial from `taikhoan_run_safe.xlsx` or the source workbook's `device ID` rows.
7. Before installing or opening an app, check the serial is online and capture its current activity. Prefer a launcher/richly verified idle device when user asks for a test target.

## What went wrong previously

An early pass used `GMAIL is Hotmail AND NGÀY TẠO is blank` and concluded that four machines had unregistered Hotmail. Those rows already had TikTok IDs; the blank date was stale/incomplete metadata. The correct result came from the set difference: five Hotmail mailboxes on machines 38 (two), 54, 57, and 66.

## Redaction

Do not print full email addresses, `PASS MAIL`, `PASS`, `2FA`, recovery mail, or row dumps. Use a short mask such as `aug***@hotmail.com`, machine number, and aggregate counts. Never use the mail password as the TikTok password; the columns are distinct.
