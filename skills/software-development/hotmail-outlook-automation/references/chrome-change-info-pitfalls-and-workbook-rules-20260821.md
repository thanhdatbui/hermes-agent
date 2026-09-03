# Hotmail Change-Info Chrome vs Outlook & Catalog Rules — 2026-08-21

## 1. Outlook App vs Web Chrome for Security / Change-Info
- **Outlook Mobile App** is strictly a mail client. It does not provide native forms for password change, 2FA setup, or "Sign out everywhere".
- **Microsoft Security Portal** (`account.live.com/password/Change`, `account.microsoft.com/security`) requires a web browser (Chrome on Android device) routed through the device's local proxy.
- **Workflow**: Change password & logout sessions via Chrome on device -> Re-authenticate / update credentials in Outlook app -> Update workbook.

## 2. boxtaikhoan Catalog & Token Lifecycle (Type 1 vs Type 2)
- **Type 1 (262đ - GraphAPI / Mail Khôi Phục)**:
  - Format: `email|pass|mail_kp`.
  - Usage: Direct login into Outlook app on device. Best for budget farm setups where OTP is read via app.
- **Type 2 (393đ - OAuth2 Token)**:
  - Format: `email|pass|refresh_token|client_id`.
  - Usage: High-speed parallel TikTok registration from PC via Microsoft Graph API without opening device UI.
  - **Token Invalidation**: Changing the Hotmail password on Day 7 **immediately revokes and kills the shop's refresh_token**.
  - **Post-Change**: No need to generate a new token; device Outlook app remains the inbox reader for any future recovery needs.

## 3. 7-Day Aging Gate & Workbook Marking
- **7-Day Rule (`MIN_LOGIN_AGE_DAYS = 7`)**:
  - Hotmail accounts must be aged on device >= 7 days before password change to avoid aggressive Microsoft fraud/checkpoint triggers.
  - Initial login date must be recorded in Col 7 (`ngày tạo` / index 6) or Col 8 (`mã phụ hồi` / index 7) as `YYYY-MM-DD`.
- **Workbook Mutation on Verified Success**:
  - Col 3 (`pass mail`): Write new randomized password.
  - Col 5 (`mail khôi phục`): Write `thanhdatbui1995@gmail.com`.
  - Col 9 (`token`): Clear / null out (since token is dead).
  - Snapshot backup created before mutation (`.backup_before_password_update_machine_XX_...`).

## 4. Pitfalls & UI Handling on Chrome / Mobile
- **IME Input Glitches**: Direct `input text` via standard Samsung keypad on Chrome web inputs can drop characters or append phantom characters (e.g. `.come` instead of `.com`). Switch to `AdbKeyboard` (base64 broadcast) or clipboard paste, and verify text node content before clicking "Next".
- **Recovery Challenges**: If Microsoft challenges with "Verify your email" (`th*****@gmail.com`), script must handle OTP retrieval from `thanhdatbui1995@gmail.com` mailbox before proceeding to password change.
