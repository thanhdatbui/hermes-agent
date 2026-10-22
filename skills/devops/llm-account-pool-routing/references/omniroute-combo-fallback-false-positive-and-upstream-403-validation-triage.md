# OmniRoute Combo Fallback False-Positive & Upstream 403 Validation Triage

## 1. Nguyên Lý Vận Hành Của Combo Router & Fallback
Trong OmniRoute, một Combo Model (ví dụ `ag-gemini-pool-3`) quản lý nhiều provider connections cùng phục vụ chung một định danh model (như `gemini-3.8-flash-tiered`).
Khi client gửi request:
1. Router chọn connection đầu tiên dựa theo chiến lược (priority / round-robin / least-busy).
2. Nếu connection đó trả về lỗi HTTP 4xx hoặc 5xx từ upstream (ví dụ: HTTP 403 `PERMISSION_DENIED / VALIDATION_REQUIRED` từ Google Cloud Code):
   ```
   {"level":40,"service":"omniroute","module":"sse","tag":"COMBO","status":403,"errorBody":"[403]: Antigravity upstream error (403)","msg":"Model antigravity/gemini-3.8-flash-tiered failed, trying next"}
   ```
3. Router KHÔNG trả lỗi về client ngay mà tự động kích hoạt **Fallback Cascade**, chuyển tiếp request sang connection tiếp theo trong pool.
4. Nếu connection tiếp theo thành công, client nhận về **HTTP 200 OK**.

---

## 2. Cạm Bẫy Chẩn Đoán Của Coordinator (False-Positive Health Conclusion)
- **Sai lầm phổ biến**: Coordinator sau khi sửa một tài khoản hoặc nạp mới tài khoản vào combo, tiến hành gửi test request vào model combo và thấy kết quả trả về `HTTP 200 OK`. Coordinator vội vàng kết luận "Tài khoản đã hoạt động bình thường, token live 100%".
- **Hậu quả**: Thực tế tài khoản đó đã bị upstream từ chối (403 / 429) và request được gánh bởi tài khoản khác trong pool. Tài khoản lỗi tiếp tục nằm chết ngầm trong hệ thống, gây lãng phí tài nguyên và làm nghẽn router khi lặp lại vòng lặp thử lỗi.

---

## 3. Quy Trình Thẩm Định Chuẩn (Evidence-First Verification)
Để xác nhận chắc chắn một tài khoản cụ thể đã hoạt động thành công sau khi sửa hoặc nạp mới:
1. **Truy vấn `call_logs` trong `storage.sqlite`**:
   BẮT BUỘC kiểm tra dòng log mới nhất ngay sau khi gửi test request:
   ```sql
   SELECT timestamp, status, model, account, connection_id, error_summary, duration
   FROM call_logs
   ORDER BY timestamp DESC
   LIMIT 3;
   ```
2. **Đối soát Ownership của bản ghi**:
   - Trường `connection_id` và `account` trong bản ghi 200 OK BẮT BUỘC phải trùng khớp với tài khoản mục tiêu vừa sửa.
   - Nếu bản ghi mang email/connection_id của tài khoản khác, tài khoản mục tiêu đã bị fail và rớt vào fallback.
3. **Tra cứu Upstream Log Khi Bị Lỗi 403**:
   - Tra cứu file log hệ thống `AppData/Roaming/omniroute/logs/omniroute-stdout.log` để tìm payload lỗi thật từ Google:
     - Lỗi `VALIDATION_REQUIRED`: Tài khoản bị Google bắt mở trình duyệt xác thực phiên (`validation_url`). Việc mở browser click "Thử lại" chỉ có tác dụng nếu sau đó request API trực tiếp trả về `status == 200` và `error_summary IS NULL` trên đúng `connection_id` đó.
