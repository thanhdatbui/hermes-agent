# OmniRoute API Key Health & Warning State Diagnosis

## 1. Cơ chế cảnh báo API Key Warning trên Dashboard
- **Hiện tượng:** Dashboard OmniRoute (`http://127.0.0.1:20129` hoặc IP LAN) hiện banner vàng:
  `"{count} API key(s) in warning state due to elevated failure rate in connections: {connections}. Review to prevent rotation issues."`
- **Mã nguồn kích hoạt:** `src/app/(dashboard)/dashboard/HomePageClient.tsx`.
- **Nguyên lý:** Mỗi khi một connection phát sinh request lỗi hoặc test thất bại, OmniRoute cập nhật object `apiKeyHealth` trong `provider_specific_data`:
  - `failures == 1`: trạng thái `status = "warning"`
  - `failures >= 2`: trạng thái `status = "invalid"`
  Khi có ít nhất 1 key ở trạng thái `warning` hoặc `invalid`, banner cảnh báo sẽ hiển thị để nhắc nhở tránh lỗi xoay vòng (rotation issues).

## 2. Vị trí Database & Cách truy vấn nhanh O(1)
- **Đường dẫn DB thực tế:** `~/.omniroute/storage.sqlite` (trên Windows: `C:\Users\<User>\.omniroute\storage.sqlite`).
  *Lưu ý:* Tránh nhầm với thư mục cấu hình cũ/phụ `AppData\Roaming\omniroute\storage.sqlite`.
- **Lệnh Python kiểm tra nhanh các accounts cảnh báo:**
```python
import sqlite3, json

conn = sqlite3.connect(r'C:\Users\Kibe\.omniroute\storage.sqlite')
c = conn.cursor()
c.execute("SELECT id, provider, name, test_status, error_code, last_error, last_error_at, provider_specific_data FROM provider_connections;")
for r in c.fetchall():
    psd = json.loads(r[7]) if r[7] else {}
    health = psd.get('apiKeyHealth', {})
    unhealthy = [f"{k}:{v.get('status')}" for k, v in health.items() if v.get('status') in ('warning', 'invalid')]
    if unhealthy or r[3] not in (None, 'active'):
        print(f"[{r[1]}] {r[2]} | Status: {r[3]} | Health: {unhealthy} | Err: {r[4]} - {r[5]}")
```

## 3. Phân loại lỗi thường gặp theo Provider & Cách xử lý
1. **Codex (OAuth Token expired / 401 Unauthorized):**
   - **Triệu chứng:** `test_status: expired`, `error_code: 401.0`, `last_error: [401]: {"detail":"Unauthorized"}`.
   - **Xử lý:** Vào Dashboard OmniRoute mục Provider `codex`, re-authenticate lại tài khoản bị expired hoặc chạy flow OAuth cập nhật refresh token.
2. **ChatGPT-Web (Session Cookie hết hạn):**
   - **Triệu chứng:** `apiKeyHealth.primary.status: invalid`, lỗi 401 yêu cầu paste lại `__Secure-next-auth.session-token`.
   - **Xử lý:** Mở profile GPM tương ứng, copy session token mới từ cookies trình duyệt của `chatgpt.com` và paste cập nhật vào connection.
3. **Cảnh báo đơn lẻ / Warning nhẹ (1 failure):**
   - **Triệu chứng:** `failures: 1`, `status: warning` do một lần timeout mạng hoặc upstream gián đoạn tạm thời.
   - **Xử lý:** Bấm **Test Connection** trực tiếp trên giao diện Dashboard. Khi request test thành công, OmniRoute sẽ tự động reset trạng thái về bình thường.
