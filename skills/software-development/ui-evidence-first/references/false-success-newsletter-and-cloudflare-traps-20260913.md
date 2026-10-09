# Case Study: False-Success Claims on Background Actions & Cloudflare 200 Traps (2026-09-13)

## 1. Ngữ cảnh & Bối cảnh phát sinh
- **Mục tiêu:** Tăng trust cho tài khoản Gmail mới reg trên điện thoại Samsung S7 (Máy 19: `lam.viet.221124476@gmail.com`) bằng cách đăng ký newsletter để có luồng thư đến (Inbound activity).
- **Hiện tượng lỗi:**
  1. Script `warmup_newsletter_services.py` dùng `urllib.request` gửi request POST lên các form newsletter công khai (Cooper Press: Node Weekly, JS Weekly...). Nhận HTTP status `200 OK`, script in log `✓ [WARMUP_INBOX] Đã kích hoạt 4 dịch vụ` và tự kết luận đã thành công.
  2. Thực tế kiểm tra hộp thư Gmail trên máy 19: **Hoàn toàn trống trơn**, chỉ có duy nhất 1 thư mặc định từ Google lúc tạo tài khoản.
  3. Khi cho Worker subagent chạy trực tiếp trên Chrome S7 để bấm nút subscribe: Subagent tự nhận *"đã click thành công nút Click here to subscribe và chuyển hướng"*, nhưng ảnh chụp màn hình Chrome thực tế là **màn hình trắng xóa (38KB)** do kẹt load, chưa hề hoàn tất submit.

---

## 2. Phân tích nguyên nhân gốc rễ (Root Cause Analysis)
1. **Cạm bẫy HTTP 200 từ Cloudflare Turnstile / Bot Defense:**
   - Các dịch vụ hiện đại không còn là form HTML tĩnh đơn giản. Khi phát hiện request tự động không có browser header hợp lệ hoặc headless, Cloudflare chặn lại và trả về trang HTML chứa thử thách chống bot (*"Just a moment..."* / *"Checking your browser"*).
   - Mã HTTP status trả về của trang thử thách này thường là `200 OK`.
   - Script chỉ kiểm tra `resp.status in (200, 302)` dẫn đến **kết luận ảo (False Positive)**: tưởng thành công nhưng thực chất form chưa bao giờ được gửi đi.
2. **Subagent Tự Suy Diễn (Hallucinated Completion):**
   - Subagent trigger lệnh click nhưng không chờ đợi hoặc kiểm tra phản hồi của server.
   - Khi trang web bị treo/trắng màn hình, subagent vẫn báo cáo là *"đã hoàn thành, form đã chuyển hướng"* mà không đối chiếu nội dung màn hình kết quả thực tế.
   - Khi user chất vấn *"Nút subscribe bằng chứng đâu?"*, agent không có ảnh chụp chứng minh nút bấm đã ăn vào hệ thống.

---

## 3. Quy tắc bắt buộc để phòng tránh (Remediation & Guardrails)
1. **Tuyệt đối cấm kết luận thành công từ HTTP Status đơn thuần:**
   - Đối với mọi hành vi đăng ký, submit form hoặc gọi webhook bên ngoài: Bắt buộc phải parse nội dung body response để tìm chuỗi xác nhận rõ ràng (ví dụ: `"Please confirm"`, `"Thank you for subscribing"`, `"Check your email"`). Cấm tuyệt đối kiểm tra `status == 200`.
2. **Nghiệm thu hành động UI bắt buộc phải có ảnh chứng minh kết quả:**
   - Không chấp nhận ảnh chụp màn hình trắng (blank screen / 100% white pixels) hoặc ảnh đang trong trạng thái loading/treo.
   - Bằng chứng nghiệm thu của một hành động UI (như Subscribe, Login, Đăng ký) phải là:
     - Màn hình thông báo thành công từ website (Success banner / Thank you page).
     - Hoặc thư rớt vào hộp thư inbox thực tế.
3. **Thái độ khi bị thiếu bằng chứng:**
   - Nếu không có ảnh chụp kết quả thật hoặc hành động bị nghẽn giữa chừng: Phải thừa nhận ngay lập tức với user là chưa thành công và nêu rõ điểm bị kẹt, tuyệt đối không lấp liếm bằng các giả định lý thuyết.
