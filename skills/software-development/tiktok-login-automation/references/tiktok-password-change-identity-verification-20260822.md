# TikTok Password Change & Identity Verification (2026-08-22)

## 1. Authoritative Workbook Invariant (User Correction)
- **Do NOT ask the user for information already present in the workbook**:
  - Check `D:\OneDrive\TaadaaData\kibe\taikhoan_dat_v2_updated .xlsx` sheet `Tài Khoản`.
  - Column 3 (`ID` / TikTok username) is mapped to Column 6 (`GMAIL`) and Column 7 (`PASS MAIL`).
  - When TikTok presents a masked email (e.g. `q***8@gmail.com`), match it against Column 6 (`quachtieu21061998@gmail.com`).
  - Treat the workbook as authoritative and proceed without querying the user.

## 2. Duplicate Account Row Disambiguation
- When multiple rows share the same TikTok ID (e.g. `quachtieu2106` on rows 547 and 548):
  - Differentiate by full tuple: `(Machine, ID, Pass, GMAIL, PASS MAIL, 2FA)`.
  - Identify invalid rows (e.g. wrong email `tongngoan...` without 2FA vs correct email `quachtieu...` with 2FA).
  - Always backup the workbook (`.bak-<timestamp>`) before clearing stale row contents (Columns 3-9).
  - Verify that the cleared row has `None` and the valid row remains intact.

## 3. TikTok Password Change Runner (`login_runner/password_change.py`)
- **Default Filter Trap (`target_in_default_scope`)**:
  - The default filter only matches accounts with passwords ending in `@Ks` or `@hotmail.com` emails.
  - If targeting a custom row or specific password format, inspect `freeze_targets` or pass explicit row filters.
- **SparkActivity Identity Verification Flow**:
  1. Profile -> Settings and Privacy (`Cài đặt và quyền riêng tư`) -> Account (`Tài khoản`) -> Password (`Mật khẩu`).
  2. TikTok opens `com.bytedance.hybrid.spark.page.SparkActivity` (WebView).
  3. "Xác minh danh tính" / "Xác minh đó là bạn": Displays masked email option `q***8@gmail.com`.
  4. Requires selecting the email option to enable the "Tiếp" (Continue) button.
  5. Advances to "Nhập mã gồm 6 chữ số".
- **OTP Destination & Fetching**:
  - TikTok sends verification codes directly to the **primary email** (`GMAIL` column), NOT the recovery email (`thanhdatbui1995@gmail.com`).
  - Google IMAP basic auth fails with `[ALERT] Invalid credentials (Failure)` on consumer Gmail accounts without App Password.
  - Codes must be fetched via configured Gmail App, OAuth2 App Password, or operator prompt.
