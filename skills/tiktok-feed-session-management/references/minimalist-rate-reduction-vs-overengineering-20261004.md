# Minimalist Rate Reduction vs Overengineering (User Mandate 2026-10-04)

## 1. Bối Cảnh & Hiện Tượng
- Khi phát hiện một hành vi hoặc tỷ lệ trong hệ thống vận hành quá dày (ví dụ: follow tự nhiên 20% ở nhịp Deep Inspect gây áp lực lên Action Limit của tài khoản TikTok):
  - Phản xạ sai lầm của AI (Bệnh Over-Engineering): Đề xuất tạo thêm state machine per-session, thêm biến đếm thao tác (`session_organic_follow_counter`), thêm cờ khóa động (`is_locked_after_1_follow`), hard-cap phân tầng...
  - **Hậu quả của việc chế cháo:** Làm phình mã nguồn, tăng blast radius, tăng nguy cơ race condition giữa các luồng chạy song song, tạo thêm stateful context cần cleanup, dễ làm gãy test suite.

## 2. Kỷ Luật Thực Thi Dứt Khoát (User Mandate)
- **"Giảm tỉ lệ là được rồi, đừng chế cháo thêm phức tạp"**.
- Nếu vấn đề cốt lõi chỉ là **tần suất (frequency) quá cao**, giải pháp thanh thoát và an toàn nhất là **hạ hằng số cấu hình O(1)** (từ `DEFAULT_DEEP_FOLLOW_RATE_PERCENT = 20` xuống `5`).
- **Lợi ích thực tế:**
  1. Zero state mutation, zero architecture change, zero regression risk.
  2. Giữ nguyên 1 dòng diff duy nhất, 101/101 unit tests pass sạch sẽ.
  3. Đạt đúng 100% mục tiêu nghiệp vụ: giảm từ ~27 lượt/ca xuống ~5–7 lượt/ca mà không đụng chạm đến flow chạy của hệ thống.
