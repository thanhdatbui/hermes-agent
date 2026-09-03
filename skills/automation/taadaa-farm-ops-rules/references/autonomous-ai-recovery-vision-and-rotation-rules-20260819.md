# Autonomous AI Recovery Vision & Lock Rotation Lessons (2026-08-19)

## 1. Bản Chất Lỗi "clear_all button and empty-recents evidence not found"
- **Nguyên nhân**: Khi máy vừa mở khóa hoặc đã sạch app chạy ngầm, giao diện Recent Apps không hiển thị nút "Đóng tất cả / Xóa tất cả".
- **Khắc phục**: Cả 2 hàm trong `automation_core/startup.py` (`prepare_app_for_automation` và `prepare_android_for_automation`) bắt buộc phải kiểm tra: nếu `close.result == "failed"` và `"clear_all button" in str(close.error)` thì **cho phép bỏ qua (pass)**, gửi phím Home và tiếp tục mở app thay vì làm sập startup.

## 2. Cấu Hình NINEROUTER_API_KEY Cho Vision Client
- **Vấn đề**: Khi `.env` thiếu `NINEROUTER_API_KEY` hợp lệ, `ai_recovery/vision_client.py` rơi vào fallback mặc định (gửi phím Back) và báo "API key không tìm thấy".
- **Khắc phục**: API Key chuẩn được quản lý trong cơ sở dữ liệu SQLite của 9Router tại `C:\Users\Kibe\AppData\Roaming\9router\db\data.sqlite` (bảng `apiKeys`). Key có tiền tố `sk-...` phải được nạp vào `C:\Users\Kibe\AppData\Local\hermes\.env`.

## 3. Khóa Cứng Chế Độ Dọc (Portrait) Trên Samsung Cũ (Máy 41)
- **Vấn đề**: Cảm biến con quay hoặc cài đặt tự động xoay (`accelerometer_rotation = 1`) khiến thiết bị bị lật ngang khi gặp video/quảng cáo.
- **Khắc phục**: Áp dụng cơ chế khóa kép (Dual-layer lock) bằng ADB:
  ```bash
  settings put system accelerometer_rotation 0
  settings put system user_rotation 0
  content insert --uri content://settings/system --bind name:s:accelerometer_rotation --bind value:i:0
  content insert --uri content://settings/system --bind name:s:user_rotation --bind value:i:0
  ```

## 4. Phân Vai Model Trong Hệ Thống Farm
- **Thợ code / Refactor / Debug**: Dùng **Claude Sonnet (Claude Code CLI)** để viết code, patch file và chạy test suite.
- **Mắt đọc ảnh & Suy luận rule**: Dùng **`ag/claude-opus-4-6-thinking`** qua cổng 9Router 20128.
- **Thẩm định & Audit diff**: Dùng combo **`plan-review` (`gpt-5.6-terra` / `claude-opus-4-6-thinking`)** với `reasoning_effort: max`.
