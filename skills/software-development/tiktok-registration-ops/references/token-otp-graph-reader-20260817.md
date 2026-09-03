# Token-OTP reader: đọc OTP hotmail qua Graph API (2026-08-17)

Hotmail "loại 2" mua từ shop MMO (boxtaikhoan.com) giao dạng:
`mail|pass|refresh_token|client_id` — refresh_token sống 12-36 tháng, đọc mail qua
Graph API từ PC **không cần app Outlook trên máy farm**.

## Cơ chế (verified live 2026-08-16/17, acc AncilBrolly73102@hotmail.com)

1. POST `https://login.microsoftonline.com/common/oauth2/v2.0/token`
   `grant_type=refresh_token` + `refresh_token` + `client_id` (client_id CỦA SHOP —
   `9e5f94bc-e8a4-4e73-b8be-63364c29d753` — hoạt động tốt nhất) + `scope=https://graph.microsoft.com/Mail.Read offline_access`
   → `access_token` (dạng opaque `EwAo...`, KHÔNG phải JWT — decode payload `token.split('.')[1]` sẽ IndexError, đừng làm),
   scope response = `Mail.Read` (không User.Read → `/me` 401, `/me/messages` 200 — bình thường, không cần User.Read).
2. `GET https://graph.microsoft.com/v1.0/me/messages?$top=10` (Bearer) → đọc subject/body,
   regex `\b\d{6}\b` lấy OTP. Tự gửi mail (sendMail) bị 403 — scope chỉ có Mail.Read, đúng thiết kế.

- **An toàn với Microsoft**: đọc mail qua API là thao tác thụ động, không thuộc risk engine —
  toàn bộ checker hotmail MMO chạy kiểu này. Thứ gây ban là LOGIN tương tác từ IP bẩn (CAPTCHA → khóa tạm 24-72h).
- **Đổi pass/logout thiết bị = token cũ chết** (Microsoft thu hồi). Đúc token mới được bằng
  device-code flow (`microsoft.com/link`) — nên đúc NGAY TRÊN MÁY FARM (proxy/thiết bị riêng) để tránh CAPTCHA.
  Flow đổi pass hàng loạt từ 1 PC cùng IP = flag "bất thường" → đổi pass trên TỪNG MÁY (IP riêng).

## Code trong repo

- `Tiktok_Reg/hotmail_provider.py::read_tiktok_otp_from_graph_token` (commit `8752c7b`) —
  nhận token/client_id từ tham số, file token list (`HOTMAIL_TOKEN_FILE`, format mail|pass|refresh_token|client_id),
  hoặc env. `social_reg_v1.py` ưu tiên token reader, fallback `read_tiktok_otp_from_outlook_app` (app Outlook).
- Script test: `Hotmail/scripts/test_graph_token.py` — `--refresh-token --client-id`, trả access_token + đọc inbox.
- Test mẫu: `tests/test_hotmail_provider.py` (13 pass) — mock HTTP, dummy token (KHÔNG commit token thật).

## Token storage — gmail_clean_v2 cột 9 + 10 (source of truth, 2026-08-17)

- Cột 9 `token` = refresh_token (riêng từng acc), cột 10 `client_id` (chung cả kho `9e5f94bc-...`).
- `Hotmail/scripts/hotmail_list_runner.py` — login hàng loạt từ TXT `mail|pass|refresh_token|client_id`:
  `--list 17-08.txt --machine-map "75:mailA,76:mailB,..."` → TUẦN TỰ (OTP shared), SUCCESS → ghi row
  (máy/email/pass/ngày/token/client_id) + xóa acc khỏi TXT; lỗi → giữ + report.
- `resolve_graph_credentials(email)` đọc: kwargs → env token file → per-mailbox `<HOTMAIL_TOKEN_DIR>/<mailbox>.token`
  → `HOTMAIL_TOKEN_LIST` → **gmail_clean_v2.xlsx** (col 9/10; env `HOTMAIL_WORKBOOK` override).
## Reg song song: token đọc RIÊNG từng mailbox → hết bottleneck OTP shared. Verify:
  `resolve_graph_credentials(email)` token len>0 → `exchange_refresh_token` OK → `_graph_newest_otp` đọc được.

## OTP qua token CHẠY LIVE end-to-end — máy 76, 2026-08-17 chiều

Lần đầu token-OTP chạy thật tới hết reg: `read_tiktok_otp_from_graph_token('9885b64d56305a3731',
'LilyanLederhos64090@hotmail.com', timeout=60)` → `'585970'` — đọc từ PC qua Graph, KHÔNG mở Outlook app.
Chuỗi: nhập email TikTok → Đăng nhập → TikTok gửi OTP → token reader lấy code 60s → nhập 6 ô → xác nhận
→ DOB → Tạo mật khẩu. **Cơ chế hoạt động end-to-end (không chỉ unit test mock).**
Lưu ý signature: `read_tiktok_otp_from_graph_token(device, email, *, token=..., client_id=..., timeout=...)` —
THAM SỐ ĐẦU LÀ `device` (serial), KHÔNG phải email (gọi nhầm `(email)` → TypeError missing email).

## Pitfalls live batch (2026-08-17, máy 75-79)

1. **AdbKeyboard IME**: cài APK xong PHẢI `ime enable com.github.uiautomator/.AdbKeyboard`; verify
   `ime list -s` (chỉ enabled) KHÔNG `-a` — thiếu → `refusing unsafe password input`. Máy 31 có sẵn; 75-79 cài+enable.
2. **Lock screen**: máy S7 để lâu tự khóa → `LOGIN_FORM_NOT_IDENTIFIED`. Unlock: `input keyevent 82` + swipe.
3. **`INBOX_NOT_REACHED` nhưng acc đã login**: verify drawer thật (tap account_button 96,156 → drawer_header_summary =
   email). Đúng → ghi workbook thủ công bằng ảnh xác nhận, không chạy lại.
4. **ACCOUNTS hardcode**: `social_reg_v1.py` chỉ nhận STT trong list `ACCOUNTS` trong file (đến STT 74) — dù detector
   báo target; thêm `{"stt": N, "device": "<serial>", "email": "", "pass": ""}` 4-space indent + `py_compile`.
5. **taikhoan_run_safe.xlsx bẩn**: ngày tháng rơi vào cột Device ID (máy 38 `21/07/2026`) → detector
   `TARGET_INVENTORY_CONFLICT`. Fix: backup + thay serial đúng + xóa row rác (device+ID rỗng).
6. **VenV live reg**: `D:/CodexRuntime/tiktok-video/venv-core024/Scripts/python.exe` (KHÔNG automation venv — PIL hỏng),
   `PYTHONPATH="D:/Taadaa/Hotmail;."`, `TAADAA_HOST_CONFIG='D:/Taadaa/machine-config/kibe.yaml'`, redirect `> log 2>&1`
   không pipe tail (giữ exit code).

## Workflow kinh doanh (user, 2026-08-16/17)

Mua hotmail (có pass + token) → **login lên máy farm** (vẫn cần: acc "thuộc về máy" + đổi pass an toàn trên máy
ngày 7) → **reg TikTok đọc OTP qua token từ PC** (nhanh, song song nhiều máy — không còn OTP-shared qua
Gmail recovery) → 7 ngày đổi pass trên máy (token cũ chết, không sao, reg đã xong) → bán TikTok kèm hotmail.

Lưu ý acc shop loại "TRUSTED GraphAPI" (rẻ hơn) KHÔNG kèm token — chỉ có pass; vẫn dùng app Outlook cho OTP,
hoặc đúc token riêng bằng pass (device-code). Loại "OAuth2" (đắt hơn ~50%) kèm token sẵn.