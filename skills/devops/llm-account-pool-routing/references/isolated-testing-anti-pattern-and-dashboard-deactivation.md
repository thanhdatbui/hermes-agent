# Anti-Pattern: Mass Account Deactivation During Isolated Testing (`isActive: false`)

## 1. The Incident: False Outage & Mass Dashboard Deactivation
Khi một agent hoặc script muốn kiểm tra độc lập (probe / verify) một tài khoản LLM cụ thể trong pool mà không muốn request bị router xoay sang tài khoản khác:
- **Hành vi sai lầm nghiêm trọng (Anti-Pattern)**:
  Script (ví dụ `scan_pro_accounts.py` với hàm `isolated_chat_test()`) duyệt qua toàn bộ database hoặc gọi `PUT /api/providers/{id}` đặt `isActive: false` cho tất cả N - 1 tài khoản khác, chỉ để lại duy nhất 1 tài khoản đang test, sau đó test xong mới bật lại `isActive: true`.
- **Hậu quả thực tế trên hiện trường**:
  1. **Hiển thị giao diện**: Dashboard `/dashboard/quota` (Provider Quota) lập tức hiển thị toàn bộ dàn tài khoản bị gạt công tắc xám (`toggle_off`), trạng thái báo lỗi đỏ rực ("Token expired", "Deactivated"), gây hoang mang và khiến người vận hành nghi ngờ tài khoản bị ban/thu hồi hoặc bị phá hoại.
  2. **Tê liệt production routing**: Trong suốt thời gian script chạy (thường kéo dài 3–10 phút), mọi request thực tế từ các worker khác, farm scripts hoặc closeout reviewer gửi đến pool đều bị dội lỗi HTTP 503:
     ```text
     [503] Service temporarily unavailable: all targets were skipped by pre-dispatch filters
     ```
  3. **Nguy cơ kẹt vĩnh viễn (Outage Risk)**: Nếu script kiểm tra gặp exception, timeout mạng, hoặc bị ngắt (`SIGINT` / crash) giữa chừng trước khi kịp chạy vòng lặp khôi phục `isActive: true`, toàn bộ dàn tài khoản production sẽ bị bỏ quên ở trạng thái `isActive: false`, gây sập toàn bộ pool.

---

## 2. Kỷ Luật Bất Biến: CẤM Đổi `isActive` Để Cô Lập Test Target
- **Invariant**: TUYỆT ĐỐI CẤM mọi script, watchdog hay agent tự ý can thiệp `isActive = false` hàng loạt trên production `provider_connections` để phục vụ mục đích kiểm thử hoặc đo đạc quota đơn lẻ.
- Cột `isActive` chỉ dành riêng cho việc:
  - Người vận hành chủ động vô hiệu hóa tài khoản bị hỏng hoặc ngừng sử dụng.
  - Watchdog tự động loại trừ vĩnh viễn tài khoản bị ban (`AccountDeactivated` / `invalid_grant` không thể phục hồi).

---

## 3. Các Phương Pháp Chuẩn Để Test Cô Lập 1 Tài Khoản (Zero Side-Effects)

### Cách 1: Truyền Header Pin Connection ID Trực Tiếp (Khuyên Dùng Nhất)
OmniRoute hỗ trợ header routing định tuyến thẳng vào connection ID cụ thể mà không cần chạm vào cấu hình pool hay tắt bất kỳ account nào:
```python
import urllib.request
import json

headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {API_KEY}",
    "x-omniroute-connection-id": target_connection_id  # Pin chính xác connection cần test
}
payload = {
    "model": "antigravity/gemini-3.8-flash-tiered",
    "messages": [{"role": "user", "content": "ping"}]
}
req = urllib.request.Request("http://127.0.0.1:20129/v1/chat/completions", data=json.dumps(payload).encode(), headers=headers)
with urllib.request.urlopen(req, timeout=30) as resp:
    res = json.loads(resp.read().decode())
```

### Cách 2: Test Trực Tiếp Qua Native CLI Profile (Out-of-Band)
Nếu kiểm tra tài khoản Antigravity / Gemini Pro, chạy trực tiếp qua công cụ sandbox cô lập:
```bash
python D:/Taadaa/tools/ag_cli.py ask --profile <profile_name> --model gemini-3.8-flash-medium "say test-ok"
```
Cách này bypass hoàn toàn OmniRoute router, không làm ô nhiễm call logs, không kích hoạt semaphore cooldown, và không ảnh hưởng đến các request đang chạy song song.

### Cách 3: Tra Cứu Cache Quota Sẵn Có Thay Vì Bắn Request Mò
Khi chỉ cần kiểm tra quota còn hay hết, đọc trực tiếp từ cache endpoint mà không cần thực thi inference:
```bash
GET http://127.0.0.1:20129/api/usage/provider-limits
```
Dữ liệu cache trả về chi tiết `quotas[model].remainingPercentage`, `used`, `total`, và `resetAt` của từng connection ID mà không gây ra bất kỳ tác dụng phụ nào trên hệ thống.
