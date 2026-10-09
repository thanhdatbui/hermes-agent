# Gate 3 Circuit Breaker & Exact Contract Re-Dispatch Protocol (19/09/2026)

## 1. Hiện tượng thực tế (Sự cố liên kết ChatGPT sau Reg Gmail)
- **Lượt 1 (Dispatch Khái Quát):** Coordinator giao task yêu cầu worker rà soát và patch 2 file (`check_gmail_live_fast.py` và `hook_chatgpt_register.py`).
- **Thất bại cấu trúc (Structural Failure):** Worker tiêu tốn toàn bộ ngân sách 15 API calls chỉ để:
  1. Chạy baseline pytest (`15 passed`).
  2. Đọc file, xác nhận lại nguyên nhân và lập kế hoạch chi tiết.
  3. Kết quả: `api_calls = 15`, `0 files modified` (hết budget trước khi kịp áp dụng patch).

## 2. Kích hoạt Gate 3 Circuit Breaker
- **Quy tắc bất biến:** Khi worker trả về `0 files modified` và cạn iterations, đó là **Thất bại cấu trúc (Analysis Paralysis)**.
- **CẤM TUYỆT ĐỐI:** Không retry prompt cũ, không tăng budget mù quáng để worker tiếp tục đọc/nghĩ.
- **Hành động bắt buộc của Coordinator trước khi Re-dispatch (Lượt 2):**
  1. **Đóng gói Exact Patch Contract:** Coordinator tự chuẩn bị sẵn chuỗi thay thế chính xác tuyệt đối (`old_string` -> `new_string`) cho từng file.
  2. **Khóa chặt phạm vi (Scope Lock):** Worker ở Lượt 2 bị tước quyền phân tích/khảo sát; chỉ được phép thực hiện 2 thao tác:
     - Gọi `patch(mode='replace')` hoặc `write_file` với code Coordinator đã đóng gói sẵn.
     - Chạy focused test xác nhận (`pytest <test_file>`).
  3. **Ngân sách Lượt 2:** Giới hạn <= 5-8 API calls (không cho phép tiêu hao quá 10 calls).

## 3. Bài học về Browser Automation & Mobile Timing
- **Bẫy Blind-tap + Keyevent 4 (Back):** Khi WebView chưa kịp render element (do proxy lag), tuyệt đối cấm nhánh fallback tap tọa độ và gửi `keyevent 4` để "ẩn bàn phím". Trên Android, gửi `keyevent 4` khi chưa có bàn phím sẽ thoát ứng dụng ra Home Launcher.
- **Bẫy Playwright Lock Collision:** Khi chạy song song nhiều worker trên Host, cấm dùng chung thư mục `user-data-dir` tĩnh cho Playwright Chromium persistent context. Bắt buộc dùng thư mục tạm duy nhất theo PID + timestamp kèm cleanup trong `finally:`.
- **Bẫy Initial Sync Delay của Gmail:** Tài khoản Google vừa tạo mất 30-50s để hoàn tất đồng bộ hòm thư ban đầu; polling OTP cần kiên nhẫn >= 25 vòng lặp kết hợp pull-to-refresh.
