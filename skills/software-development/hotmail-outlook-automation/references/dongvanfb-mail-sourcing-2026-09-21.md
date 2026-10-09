# DongVanFB.net — Hotmail Source for Taadaa Farm (thêm 2026-09-21)

## API Endpoints (không cần auth cho catalogue)

```
# Danh mục sản phẩm (public)
GET https://api.dongvanfb.net/api/products_lists
  → JSON: data[].clone_type[] với type=2 là mail; trả quality (stock), price

# Signed endpoints (cần apikey)
GET https://api.dongvanfb.net/user/account_type?apikey=<KEY>
GET https://api.dongvanfb.net/user/balance?apikey=<KEY>
GET https://api.dongvanfb.net/user/buy?apikey=<KEY>&account_type=<ID>&quality=<N>&type=full
  → type=full: xuất email|pass|refresh_token|client_id (+ trường 5 mail khôi phục nếu loại 57/58)
  → type=null: chỉ email|pass
```

## Lấy API key từ Chrome CDP (tab đã đăng nhập dongvanfb.net)

```python
import websocket, json, urllib.request

resp = urllib.request.urlopen("http://localhost:9222/json")
tabs = json.loads(resp.read().decode())
target = next(t for t in tabs if "dongvanfb.net" in t.get("url", ""))
ws_url = target["webSocketDebuggerUrl"]

ws = websocket.create_connection(ws_url, suppress_origin=True)
ws.send(json.dumps({
    "id": 1, "method": "Runtime.evaluate",
    "params": {"expression":
        "JSON.stringify(Object.keys(localStorage).reduce((o,k)=>{o[k]=localStorage.getItem(k);return o;},{}))"
    }
}))
raw = json.loads(ws.recv())["result"]["result"]["value"]
ws.close()
data = json.loads(json.loads(raw))  # double parse
api_key = json.loads(data["user_data"])["api_key"]
print("API key:", api_key)
```

## Phân biệt loại sản phẩm — SCOPE OAUTH2 THỰC TẾ (verified 2026-09-21)

| Product ID | Tên | Scope Microsoft nhận về | Dùng farm? |
|---|---|---|---|
| **5** | `Hotmail TRUSTED [GRAPH API]` | `IMAP.AccessAsUser.All POP.AccessAsUser.All SMTP.Send` | ❌ KHÔNG — thiếu `Mail.Read`, `GET /me/messages` → 401 |
| **59** | `Hotmail TRUSTED [IMAP/POP3/GRAPH API]` | Tương tự ID 5 (tên gây nhầm lẫn) | ❌ KHÔNG |
| **57** | `HOTMAIL TRUSTED THÊM KHÔI PHỤC FVIAINBOXES.COM` | `openid profile User.Read Mail.ReadWrite Mail.Read IMAP POP SMTP` | ✅ ĐÚNG |
| **58** | `OUTLOOK TRUSTED THÊM KHÔI PHỤC FVIAINBOXES.COM` | Tương tự ID 57 | ✅ ĐÚNG |

**Tên sản phẩm có "GRAPH API" ≠ scope `Mail.Read`.** Verify scope thực tế:
```python
import urllib.request, urllib.parse, json

def check_scope(refresh_token, client_id="9e5f94bc-e8a4-4e73-b8be-63364c29d753"):
    params = {"client_id": client_id, "grant_type": "refresh_token", "refresh_token": refresh_token}
    data = urllib.parse.urlencode(params).encode()
    resp = urllib.request.urlopen("https://login.microsoftonline.com/consumers/oauth2/v2.0/token", data)
    return json.loads(resp.read())["scope"]
    # Cần thấy "Mail.Read" hoặc "Mail.ReadWrite" → dùng được cho Graph
```

## Format xuất loại 57/58

```
email|pass|refresh_token|client_id|recovery_mail@fviainboxes.com
```

Khi ghi vào `gmail_clean_v2.xlsx`:
- Cột 2 `tài khoản gmail` = email
- Cột 3 `pass mail` = pass
- Cột 5 `mail khôi phục` = trường thứ 5 (recovery_mail@fviainboxes.com)
- Cột 9 `token` = refresh_token
- Cột 10 `client_id` = client_id

## Workflow đầy đủ: Mua → Reg → Ngâm → Đổi pass (user Kibe)

1. Mua qua API `/user/buy?account_type=57&quality=N&type=full`
2. Parse chuỗi `|`, ghi vào `gmail_clean_v2.xlsx`
3. Verify token: `exchange_refresh_token(rt, cid)` → kiểm scope có `Mail.Read`
4. Reg TikTok (OTP đọc từ PC qua `read_tiktok_otp_from_graph_token`)
5. Ngâm 7 ngày nuôi acc
6. Đổi pass Hotmail **TRÊN MÁY FARM** (đúng IP proxy):
   - Chọn "Sign me out of all devices" → đá phiên shop
   - Security → Advanced Security Options → xóa `@fviainboxes.com` → thêm mail/SĐT cá nhân
   - Sau đổi pass: refresh_token cũ dies (OK, reg đã xong rồi)

## Lưu ý vận hành

- Sàn DongVanFB chuyên phục vụ tệp FB/clone → **không cam kết "Chưa qua TikTok"** (khác BoxTaiKhoan / CloneFBIG)
- Không có label "đã qua TikTok" hoặc "chưa qua dịch vụ" → test thử 1-5 mail trước khi order lớn
- client_id `9e5f94bc-e8a4-4e73-b8be-63364c29d753` là client_id shop chuẩn, dùng chung toàn kho
- Công cụ đọc OTP song song: `tools.dongvanfb.net/api/graph_messages` — nhưng chỉ hoạt động với token loại 57/58
  (loại 5 trả `"Graph token invalid."` dù token Microsoft live)
