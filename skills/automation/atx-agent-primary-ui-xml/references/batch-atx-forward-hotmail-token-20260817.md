# ATX forward per-device port + Hotmail list-runner + token Graph OTP (2026-08-17)

## 1. Bug: batch nhiều máy dùng chung 1 local port ATX → fail đồng loạt

**Triệu chứng** (batch login 5 acc 75-79 bằng `hotmail_list_runner.py`): toàn bộ `BLOCKED OUTLOOK_APP_PASSWORD_FIELD_NOT_FOUND` / `OUTLOOK_APP_LOGIN_FORM_NOT_IDENTIFIED` — nhưng máy 31 chạy đơn lẻ OK.

**Root cause** — `_ensure_forward` (automation-core `persistent_ui.py`) reuse **entry `tcp:7912` đầu tiên trong `forward --list` bất kể serial**. Chạy batch tuần tự:
- Máy A forward local 7912 → máy A.
- Máy B/C/D gọi `capture_atx_session_ui` → thấy entry 7912 tồn tại → reuse → **JSON-RPC vẫn query 127.0.0.1:7912 = máy A** → dump NHẦM màn hình máy A (màn chọn tài khoản) cho máy B/C/D → flow tưởng máy B đang ở màn cũ → password field không tìm thấy → fail đồng loạt.

**Fix (`9044b91`)**:
1. `forward --list` match **theo `adb.serial`** — entry thuộc ĐÚNG máy → reuse luôn (đọc local port thật của dòng đó).
2. Entry của máy khác → `forward --remove tcp:7912` (stale) rồi tạo mới.
3. Tạo mới bằng **`forward tcp:0 tcp:7912`** (port động) — mỗi máy 1 local port riêng. LƯU Ý: `adb forward tcp:0` **KHÔNG in stdout** — phải re-list `forward --list` và parse local port từ entry đúng serial.
4. `forward --list` trên farm có NHIỀU entry `tcp:7912` của nhiều máy (proxy watcher + các tool khác dùng port random) — đừng tưởng "1 serial 1 entry".

**Verify live:** M75 `forward_local_port=55564` VERIFIED_HEALTHY (xml 12.7KB = màn thật máy 75), M76 `port=55656` VERIFIED_HEALTHY — 2 máy 2 port, dump đúng từng máy.

**Quy tắc vận hành farm:** KHÔNG dồn chung 1 local port ATX cho nhiều máy — 1 local port chỉ trỏ 1 máy; luôn port động per-device khi chạy multi-machine.

## 2. hotmail_list_runner.py — login hàng loạt từ file TXT (Hotmail repo)

`scripts/hotmail_list_runner.py`:
- Input TXT `mail|pass|refresh_token|client_id` (1 acc/dòng), parse pipe-delimited.
- `--machine-map "75:mailA,76:mailB,..."` gán máy per-acc; `--machine-override` cho tất cả; `--serial` override.
- Per acc: resolve serial từ `taikhoan_run_safe.xlsx` sheet `Accounts` (`may | device id | id`) → NO-ROTATION guard → `login_outlook_app` → SUCCESS thì:
  - `append_to_gmail_clean_v2`: ghi vào `gmail_clean_v2.xlsx` sheet `Gmail Accounts` — cột 1 `số máy`, 2 `tài khoản gmail` (email), 3 `pass mail`, 8 `ngày tạo` (= ngày login), **9 `token`** (refresh_token), **10 `client_id`**.
  - Xoá dòng acc khỏi file TXT nguồn (đã tiêu thụ) — trừ `--keep-tokens`.
- BLOCKED/ERROR → giữ dòng trong TXT + report. `--dry-run` chỉ parse + plan.
- Tuần tự 1 acc/lần (OTP mailbox shared — cấm song song).

**Serial máy 75-80** (từ taikhoan_run_safe, máy ít acc TikTok nhất để gán acc mới):
75=`ce011711d4cd802905`, 76=`9885b64d56305a3731`, 77=`ce05160595e7953b04`, 78=`ce0916090a9d320a01`, 79=`ce0516059d279f3e03`, 80=`ce061606cd45950405`. (All S7, Android 8, đã cài Outlook 4.2325.1.)

## 3. gmail_clean_v2 = source of truth token cho reg TikTok (user rule 2026-08-17)

- **Cột 9 `token` + cột 10 `client_id` thêm vào `gmail_clean_v2.xlsx` sheet `Gmail Accounts`** — login thành công → ghi token + client_id vào đây.
- **Reg TikTok đọc token TỪ workbook này, không phải file list riêng.** `hotmail_provider.py::resolve_graph_credentials` (Tiktok_Reg) có nhánh cuối: đọc `HOTMAIL_WORKBOOK` (default `D:\OneDrive\TaadaaData\kibe\gmail_clean_v2.xlsx`) sheet `Gmail Accounts`, match `tài khoản gmail` (col 2) → return token (col 9) + client_id (col 10).
- Priority resolve: kwargs → `HOTMAIL_TOKEN_FILE`/`HOTMAIL_CLIENT_ID_FILE` env → `HOTMAIL_TOKEN_DIR/<mailbox>.token` → `HOTMAIL_TOKEN_LIST` file → **workbook gmail_clean_v2** → None (fallback outlook-app).
- `client_id` của shop loại 2: **chung cả kho** (`9e5f94bc-e8a4-4e73-b8be-63364c29d753`) — không phải riêng từng acc.
- User confirm: "lấy sử dụng xong phải lưu vào gmail clean v2 — account đã log thành công thì lưu vào đó, lỗi thì báo; thành công xong phải xoá khỏi nguồn cấp".

**Verify e2e:** `resolve_graph_credentials('Ancil...')` → token 457 chars + client_id từ workbook → `exchange_refresh_token` → access_token OK → `_graph_newest_otp` đọc inbox (None vì rỗng). Chain chạy.

## 4. Token Graph API đọc OTP — thông số kỹ thuật (đã test live)

- Token loại 2 shop (`mail|pass|refresh_token|client_id`): POST `https://login.microsoftonline.com/common/oauth2/v2.0/token` với `grant_type=refresh_token`, `refresh_token`, `client_id`, `scope=https://graph.microsoft.com/Mail.Read offline_access` → access_token (opaque `EwAo...`, KHÔNG JWT — đừng decode payload), `scope: Mail.Read`, hạn 1h.
- GET `https://graph.microsoft.com/v1.0/me/messages?$top=10&$select=subject,body,receivedDateTime,from&$orderby=receivedDateTime desc` (header `Authorization: Bearer <access_token>`) → 200.
- `/me` KHÔNG có (401) — token chỉ có Mail.Read, không User.Read — bình thường, không cần.
- `sendMail` 403 (thiếu Mail.Send) — không cần cho OTP reader.
- Acc shop loại 2 login Outlook app **KHÔNG dính account protection** (máy 31: "Chọn loại tài khoản" → nhập mật khẩu → "Bạn muốn thêm tài khoản khác?" → inbox) — khác acc farm cũ.
- Đổi pass → token cũ chết; đúc token mới = device-code flow (đọc trong hotmail-outlook-automation skill §thêm).