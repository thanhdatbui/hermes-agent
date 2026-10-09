# Sol Auditor Reviewer Scoring Pitfalls & Passing Playbook

## 1. Môi trường kiểm định thực tế
- Reviewer Sol Auditor chấm điểm độc lập qua cổng OmniRoute `:20129` model `review`.
- Ngưỡng đạt chuẩn: **Overall Score >= 85/100 (APPROVED)**. Bất kỳ điểm nào dưới 85 hoặc `REJECTED` đều kích hoạt Circuit Breaker, cấm push và cấm đóng phiên.

## 2. Các cạm bẫy khiến Sol Auditor chấm dưới 85 điểm
1. **Thiếu Verified Test Execution Evidence (Bằng chứng chạy test thật):**
   - *Triệu chứng:* Thêm file test code vào git nhưng trong patch/input không đính kèm output thực tế khi chạy pytest/unittest.
   - *Đánh giá của Reviewer:* "Chỉ thấy bổ sung test code, chưa có bằng chứng chạy test thực tế" -> Trừ từ 7 đến 10 điểm mục `Test Evidence`.
   - *Cách vượt qua:* Chạy test thực tế, ghi nhận command, duration, passed/failed và đính kèm khối `VERIFIED TEST EXECUTION EVIDENCE` vào diff patch trước khi đưa qua `closeout_gate.py`.
2. **Fail-open khi parse dữ liệu cấu hình / ngày tháng:**
   - *Triệu chứng:* Khi parse ngày tạo/cập nhật hoặc metadata từ Excel/DB, nếu gặp lỗi `except Exception:` lại dùng `pass` và cho account tiếp tục chạy.
   - *Đánh giá của Reviewer:* "Fail-open là rủi ro an toàn farm nếu dữ liệu lỗi định dạng" -> Trừ điểm `Farm Safety` và `Logic Correctness`.
   - *Cách vượt qua:* Áp dụng cơ chế **Fail-Closed**: Bất kỳ lỗi parse, format sai hoặc thiếu metadata bắt buộc phải `continue` bỏ qua account để đảm bảo an toàn tối đa.
3. **Hardcode mật khẩu hoặc cấu hình nhạy cảm:**
   - *Triệu chứng:* Dùng mật khẩu fallback cố định (ví dụ `Taadaa@2026#`) khi thiếu mật khẩu.
   - *Đánh giá của Reviewer:* "Rủi ro bảo mật nghiêm trọng do mật khẩu mặc định hard-code" -> Trừ nặng điểm kiến trúc và an toàn.
   - *Cách vượt qua:* Luôn dùng chung mật khẩu của chính tài khoản từ nguồn Master Data, fail-fast `MISSING_PASSWORD` nếu thiếu dữ liệu.
4. **Thiếu Telemetry & Observability:**
   - *Triệu chứng:* Script tự động chạy ngầm chỉ in text stdout/stderr đơn giản, không có structured counters.
   - *Cách vượt qua:* Bổ sung telemetry dictionary tổng hợp các metric: `scanned_targets`, `skipped_locked`, `skipped_feed`, `attempted`, `success`, `failed`, và hỗ trợ flag CLI `--dry-run`.
