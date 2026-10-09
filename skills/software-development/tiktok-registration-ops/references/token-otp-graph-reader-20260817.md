# Token-OTP reader: đọc OTP hotmail qua Graph API (2026-08-17, cập nhật 2026-09-21)

Hotmail "loại 2" mua từ shop MMO (boxtaikhoan.com, dongvanfb.net) giao dạng:
`mail|pass|refresh_token|client_id` — refresh_token sống 12-36 tháng, đọc mail qua
Graph API từ PC **không cần app Outlook trên máy farm**.

---

## SOURCE MUA MAIL — DONGVANFB.NET (mới, thêm 2026-09-21)

API lấy danh mục sản phẩm (public, không cần auth):
```
GET https://api.dongvanfb.net/api/products_lists
```
Lấy list acc + balance (cần `api_key`):
```
GET https://api.dongvanfb.net/user/account_type?apikey=<API_KEY>
GET https://api.dongvanfb.net/user/balance?apikey=<API_KEY>
```
Mua:
```
GET https://api.dongvanfb.net/user/buy?apikey=<API_KEY>&account_type=<ID>&quality=<N>&type=full
```
- `type=full` → xuất `email|pass|refresh_token|client_id`
- `type=null` → chỉ `email|pass`

**Trích API key từ Chrome CDP (CDP :9222 đang chạy logged-in tab):**
```python
import websocket, json, urllib.request
resp = urllib.request.urlopen("http://localhost:9222/json")
tabs = json.loads(resp.read().decode())
target = next(t for t in tabs if "dongvanfb.net" in t.get("url",""))
ws = websocket.create_connection(target["webSocketDebuggerUrl"], suppress_origin=True)
ws.send(json.dumps({"id":1,"method":"Runtime.evaluate","params":{"expression":
    "JSON.stringify(Object.keys(localStorage).reduce((o,k)=>{o[k]=localStorage.getItem(k);return o;},{}))"}}))
data = json.loads(json.loads(ws.recv())["result"]["result"]["value"])
api_key = json.loads(data["user_data"])["api_key"]
ws.close()
```

---

## SO SÁNH 3 LOẠI HOTMAIL DONGVANFB (verified 2026-09-21)

| ID | Tên sản phẩm | Scope OAuth2 nhận về | Phù hợp Farm? |
|---|---|---|---|
| **5** | `Hotmail TRUSTED [GRAPH API]` | `IMAP.AccessAsUser.All POP.AccessAsUser.All SMTP.Send` (HẸP) | ❌ KHÔNG: Graph `/me/messages` yêu cầu `Mail.Read`, scope này không có → đọc OTP thất bại |
| **59** | `Hotmail TRUSTED [IMAP/POP3/GRAPH API]` | IMAP/POP3 scope tương tự ID 5 | ❌ KHÔNG: tên nhầm, KHÔNG phải Graph API thật, chỉ hỗ trợ IMAP/POP3 cổ |
| **57** | `HOTMAIL TRUSTED THÊM KHÔI PHỤC FVIAINBOXES.COM` | `openid profile User.Read Mail.ReadWrite Mail.Read IMAP POP SMTP` (ĐẦY ĐỦ) | ✅ ĐÚNG: đọc OTP qua `GET /me/messages` bình thường |
| **58** | `OUTLOOK TRUSTED THÊM KHÔI PHỤC FVIAINBOXES.COM` | Tương tự ID 57 | ✅ ĐÚNG |

**BÀI HỌC:** Tên sản phẩm có chữ "GRAPH API" ≠ scope `Mail.Read`. Phân biệt bằng scope thực tế sau khi exchange refresh_token:
```python
import urllib.request, urllib.parse, json
params = {"client_id": client_id, "grant_type": "refresh_token", "refresh_token": rt}
data = urllib.parse.urlencode(params).encode()
resp = urllib.request.urlopen("https://login.microsoftonline.com/consumers/oauth2/v2.0/token", data)
print(json.loads(resp.read())["scope"])  # nếu thiếu Mail.Read → không dùng được
```

---

## WORKFLOW KINH DOANH: REG TIKTOK → NGÂM 7 NGÀY → ĐỔI PASS (user Kibe, 2026-09-21)

1. **Mua mail loại ID 57** (dongvanfb) → định dạng `email|pass|refresh_token|client_id|mail_khoi_phuc`
   - Cắt lấy 4 trường đầu khi ghi vào gmail_clean_v2.xlsx (cột 2-3-9-10)
   - Ghi thêm cột 5 `mail khôi phục` = trường thứ 5 (đuôi `@fviainboxes.com`)
2. **Reg TikTok** → OTP đọc qua Graph API từ PC, KHÔNG mở Outlook app
3. **Ngâm 7 ngày nuôi acc**
4. **Đổi pass Hotmail** (trên máy farm để đúng IP proxy):
   - Chọn *"Sign me out of all devices"* khi đổi pass → đá phiên shop cũ
   - Vào *Security → Advanced Security Options* → xóa `@fviainboxes.com` → thêm mail/SĐT của mình
   - Sau đổi pass: refresh_token cũ dies (không cần thiết cho reg vì đã xong), token mới cần device-code flow nếu muốn tiếp tục đọc mail

---

## Cơ chế (verified live 2026-08-16/17, acc AncilBrolly73102@hotmail.com)

1. POST `https://login.microsoftonline.com/common/oauth2/v2.0/token`
   `grant_type=refresh_token` + `refresh_token` + `client_id` (client_id CỦA SHOP —
   `9e5f94bc-e8a4-4e73-b8be-63364c29d753` — hoạt động tốt nhất) + `scope=https://graph.microsoft.com/Mail.Read offline_access`
   → `access_token` (dạng opaque `EwAo...`, KHÔNG phải JWT — decode payload `token.split('.')[1]` sẽ IndexError, đừng làm),
   scope response = `Mail.Read` (không User.Read → `/me` 401, `/me/messages` 200 — bình thường, không cần User.Read).
2. `GET https://graph.microsoft.com/v1.0/me/messages?$top=10` (Bearer) → đọc subject/body,
   regex `\b\d{6}\b` lấy OTP.

- **An toàn với Microsoft**: đọc mail qua API là thao tác thụ động, không thuộc risk engine.
- **Đổi pass/logout thiết bị = token cũ chết** (Microsoft thu hồi). Đúc token mới bằng
  device-code flow (`microsoft.com/link`) — nên đúc TRÊN MÁY FARM (proxy/thiết bị riêng).

---

## Code trong repo

- `Tiktok_Reg/hotmail_provider.py::read_tiktok_otp_from_graph_token`
- `Tiktok_Reg/hotmail_provider.py::resolve_graph_credentials(email)` — ưu tiên: kwargs → env token file → per-mailbox `.token` → HOTMAIL_TOKEN_LIST → **gmail_clean_v2.xlsx** (col 9/10)
- `Tiktok_Reg/hotmail_provider.py::exchange_refresh_token(rt, client_id)` → `(access_token, new_refresh)`
- Test: `read_tiktok_otp_from_graph_token(device, email, *, timeout=...)` — THAM SỐ ĐẦU LÀ `device` (serial)

## Token storage — gmail_clean_v2 cột 9 + 10 (source of truth)

- Cột 9 `token` = refresh_token (riêng từng acc), cột 10 `client_id` (chung cả kho `9e5f94bc-...`)
- Cột 5 `mail khôi phục` = backup mail (đuôi fviainboxes.com nếu loại 57)

---

## Stale lock cooldown recovery (2026-09-21)

Khi `social_reg_v1.py 80` báo "Cooldown 1 ngày" nhưng process PID đã chết:
```python
import json
import sys; sys.path.insert(0, "D:/Taadaa/Tiktok_Reg")
from device_lock import _daily_reg_cooldown_path, _read_json, release_machine_reg_reservation

p = _daily_reg_cooldown_path(create=False)
data = _read_json(p)
rec = data["machines"]["80"]
# Verify PID không còn chạy (wmic process where ProcessId=XXXX get CommandLine)
release_machine_reg_reservation(80, token=rec["token"])
```
→ Sau khi release: `is_machine_reg_cooldown_active(80)` trả False, reg được bình thường.

---

## Pitfalls live batch (2026-08-17, máy 75-79)

1. **AdbKeyboard IME**: cài APK xong PHẢI `ime enable com.github.uiautomator/.AdbKeyboard`; verify
   `ime list -s` (chỉ enabled) KHÔNG `-a` — thiếu → `refusing unsafe password input`.
2. **Lock screen**: máy S7 để lâu tự khóa → `LOGIN_FORM_NOT_IDENTIFIED`. Unlock: `input keyevent 82` + swipe.
3. **`INBOX_NOT_REACHED` nhưng acc đã login**: verify drawer thật (tap account_button 96,156 → drawer_header_summary =
   email). Đúng → ghi workbook thủ công bằng ảnh xác nhận, không chạy lại.
4. **ACCOUNTS hardcode**: `social_reg_v1.py` chỉ nhận STT trong list `ACCOUNTS` trong file — dù detector
   báo target; thêm `{"stt": N, "device": "<serial>", "email": "", "pass": ""}` 4-space indent + `py_compile`.
5. **taikhoan_run_safe.xlsx bẩn**: ngày tháng rơi vào cột Device ID → detector `TARGET_INVENTORY_CONFLICT`.
6. **VenV live reg**: `D:/Taadaa/python-envs/automation/Scripts/python.exe` (KHÔNG automation venv — PIL hỏng),
   `TAADAA_HOST_CONFIG='D:/Taadaa/machine-config/kibe.yaml'`, redirect `> log 2>&1`.

## OTP qua token CHẠY LIVE end-to-end — máy 76, 2026-08-17 chiều

Lần đầu token-OTP chạy thật: `read_tiktok_otp_from_graph_token('9885b64d56305a3731', 'LilyanLederhos64090@hotmail.com', timeout=60)` → `'585970'`.
Chuỗi: nhập email TikTok → Đăng nhập → TikTok gửi OTP → token reader lấy code 60s → nhập 6 ô → xác nhận → DOB → Tạo mật khẩu.
