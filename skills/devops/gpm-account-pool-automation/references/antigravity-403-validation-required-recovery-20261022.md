# Antigravity `VALIDATION_REQUIRED` 403 — Fresh URL Extraction & GPM Re-OAuth Recovery

**Date:** 2026-10-22  
**Trigger:** `chuanh250416@gmail.com` dính 403 PERMISSION_DENIED với reason `VALIDATION_REQUIRED` từ `daily-cloudcode-pa.googleapis.com`. OmniRoute tự fallback sang ACC khác; acc chuanh bị skip hoàn toàn nhưng `call_logs` vẫn ghi `status=403` với `error_summary = '[403]: Antigravity upstream error (403)'`.

---

## 1. Triệu Chứng & Phân Biệt

| Dấu hiệu | Ý nghĩa |
|---|---|
| `call_logs.status = 403` + `error_summary contains 'Antigravity upstream error'` | ACC dính VALIDATION_REQUIRED |
| `omniroute-stdout.log` chứa `"reason": "VALIDATION_REQUIRED"` | Google yêu cầu xác minh session qua link |
| `call_logs.status = 200` nhưng không đúng `connection_id` | OmniRoute đã fallback sang acc khác |
| Provider test trả `probe_inconclusive` (HTTP 400) | Không phán quyết được — phải test thực tế qua `forcedConnectionId` |

**CẤM kết luận acc sống dựa vào:**
- Quota % trên dashboard UI (luôn 100% nếu chưa tiêu)
- Provider test trả `valid: true` với `probe_inconclusive`
- Một call 200 OK không kèm `forcedConnectionId` đúng acc

---

## 2. Lấy `validation_url` Trong 1 Bước

```bash
grep -n "validation_url" "C:/Users/Kibe/AppData/Roaming/omniroute/logs/omniroute-stdout.log" | tail -n 5
```

URL có dạng:
```
https://accounts.google.com/signin/continue?sarp=1&scc=1&continue=https://developers.google.com/gemini-code-assist/auth/auth_success_gemini&plt=<TOKEN>&flowName=GlifWebSignIn&authuser
```

Lưu ý:
- `plt=` token có TTL ngắn (hàng phút) — URL mới nhất trong log mới có giá trị.
- Mã QR từ URL này chỉ có tác dụng nếu quét bằng điện thoại đang đăng nhập ĐÚNG acc cần fix (`chuanh250416@gmail.com`). Điện thoại có acc Google khác sẽ xác thực nhầm acc.

---

## 3. Cách Đúng: Re-OAuth Qua GPM Profile

**Không cần QR.** Dùng script `D:/Taadaa/tools/reauth_chuanh_gpm.py` chạy toàn bộ OAuth flow qua CDP trên profile GPM tương ứng:

```python
# reauth_chuanh_gpm.py — core flow
# 1. Lấy authUrl từ OmniRoute: GET /api/oauth/antigravity/authorize?redirect_uri=...
# 2. Mở GPM profile qua Local API: GET http://127.0.0.1:19995/api/v3/profiles/start/{id}
# 3. connect_over_cdp với addr từ response
# 4. Điều hướng tới authUrl, tự động chọn account, click consent
# 5. Bắt URL /callback?code=... → exchange code với OmniRoute POST /api/oauth/antigravity/exchange
# 6. Exchange HTTP 200 = token mới đã ghi vào DB
# 7. Đóng profile qua GET /api/v3/profiles/close/{id}
```

**Verify sau re-OAuth:**
```python
req = urllib.request.Request(
    'http://127.0.0.1:20129/v1/chat/completions',
    data=json.dumps({
        'model': 'antigravity/gemini-3.8-flash-tiered',
        'messages': [{'role': 'user', 'content': 'ping'}],
        'forcedConnectionId': '<connection_id>'  # phải đúng acc cần kiểm tra
    }).encode(),
    headers={'Content-Type': 'application/json', 'Authorization': 'Bearer env-key'}
)
```
→ Phải trả HTTP 200 với `choices[0].message.content` không None.

**Xác nhận trong call_logs:**
```sql
SELECT timestamp, status, account, connection_id, error_summary
FROM call_logs
WHERE connection_id = '<connection_id>'
ORDER BY timestamp DESC LIMIT 1;
-- status phải = 200, error_summary IS NULL
```

---

## 4. Schema `proxy_assignments` (Thực tế)

Bảng có columns: `id, proxy_id, scope, scope_id, position, created_at, updated_at`

**CẤM INSERT với `id` là UUID string** — cột `id` là INTEGER (auto-increment). Dùng:
```sql
INSERT INTO proxy_assignments (proxy_id, scope, scope_id, position, created_at, updated_at)
VALUES (?, "connection", ?, 0, datetime("now"), datetime("now"))
```

**Bảng `proxy_registry`** không có cột `url` — có: `id, name, type, host, port, username, password, region, ...`

---

## 5. Nạp ACC Mới Vào `ag-gemini-pool-3` (Combo Model Entry)

Khi thêm connection mới vào combo bằng Python, entry trong `models` array phải theo đúng schema của các entry cũ (không có `name`-field cho non-branded entry). Để chuẩn hóa về cùng dạng null (khớp với các entry cũ), reset `name = None` ngay sau khi insert.

**Verify token test trực tiếp forcedConnectionId:**
```python
# Gửi với forcedConnectionId để bắt OmniRoute route đúng acc
# Nếu trả 200 và tên acc trong call_logs = email mới → OK
```
