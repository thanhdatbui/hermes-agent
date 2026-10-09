# Quy Trình Chẩn Đoán & Dọn Dẹp Tài Khoản Chết Khỏi Pool OmniRoute (:20129)

## 1. Triệu Chứng Thường Gặp
- Watchdog healer (`cron_chatgpt_web_pool_watchdog.py`) báo cáo danh sách tài khoản "Cần chú ý" lặp đi lặp lại:
  - `Timeout bắt OAuth code`
  - `Không thấy profile GPM`
  - `Refresh token rejected (unrecoverable_refresh_error)`
- Quét `/api/providers` thấy nhiều connection ở trạng thái `isActive: false` hoặc `testStatus: "expired"` / `"error"`.

---

## 2. Nguyên Nhân Bản Chất
1. **Tài khoản đã purge trong farm nhưng sót connection**:
   - Tài khoản đã bị xóa/chết trong `gmail_clean_v2.xlsx` (nằm trong backup purge die) nhưng chưa được xóa trong OmniRoute.
   - Profile GPM đã bị xóa dẫn tới watchdog không thể mở profile để refresh OAuth.
2. **Token Google OAuth bị Revoked/Expired Upstream**:
   - Refresh token của Antigravity bị Google vô hiệu hóa upstream (`invalid_grant` / HTTP 401 `Token invalid or revoked`).
   - Tài khoản này không thể tự refresh bằng exchange token thông thường.
3. **Tài khoản vẫn sống nhưng bị toggle `isActive: false`**:
   - Token vẫn hợp lệ, chỉ cần test connection qua API và PATCH `isActive: true`.

---

## 3. Quy Trình 3 Bước Xử Lý Triệt Để

### Bước 1: Test Trực Tiếp Connection Bằng OmniRoute Management API
Chạy test từng connection qua endpoint nội bộ OmniRoute:
```bash
curl -s -X POST http://127.0.0.1:20129/api/providers/<connection_id>/test
```
- Nếu trả về `{"valid": true}`: Tài khoản vẫn sống upstream! Re-enable bằng:
  ```bash
  curl -s -X PATCH http://127.0.0.1:20129/api/providers/<connection_id> \
    -H "Content-Type: application/json" -d '{"isActive": true}'
  ```
- Nếu trả về `{"valid": false, "error": "Token invalid or revoked"}` hoặc `unrecoverable_refresh_error`: Tiếp tục Bước 2.

### Bước 2: Kiểm Tra Đối Chiếu Profile GPM & Excel Purge
- Kiểm tra xem tài khoản có tồn tại trong GPM không (`GET http://127.0.0.1:19995/api/v3/profiles`).
- Kiểm tra xem tài khoản có nằm trong danh sách purge die không (`gmail_clean_v2.bak-purge*`).
- Nếu tài khoản đã purge die hoặc không còn profile GPM để re-auth $\rightarrow$ BẮT BUỘC xóa bỏ connection rác.

### Bước 3: Xóa Bỏ Connection Chết (Safe Cleanup)
Sử dụng endpoint chuẩn của OmniRoute để xóa connection (tự động dọn model mapping và audit log):
```bash
curl -s -X DELETE http://127.0.0.1:20129/api/providers/<connection_id>
```
*Lưu ý: KHÔNG can thiệp trực tiếp vào file SQLite `storage.sqlite` nếu có thể dùng REST API, để đảm bảo cache trong bộ nhớ của OmniRoute được đồng bộ ngay lập tức.*

---

## 4. Nghiệm Thu Sau Can Thiệp
1. **Kiểm tra tỷ lệ Active:**
   ```bash
   python -c "
   import urllib.request, json
   req = urllib.request.Request('http://127.0.0.1:20129/api/providers')
   with urllib.request.urlopen(req) as r:
       conns = json.loads(r.read()).get('connections', [])
   bad = [c for c in conns if not (c.get('isActive') and c.get('testStatus') == 'active')]
   print(f'Total: {len(conns)}, Bad: {len(bad)}')
   "
   ```
   Yêu cầu `Bad: 0`.
2. **Test E2E các combo trọng yếu:**
   - `ag-gemini-pool-3`
   - `ag-claude`
   - `ag-opus-pool`
   - `chatgpt-web-pool`
   - `omni-worker`
3. **Chạy lại Watchdog:**
   Chạy `cron_chatgpt_web_pool_watchdog.py` để đảm bảo output hoàn toàn sạch, không còn báo cáo tài khoản cần chú ý.
