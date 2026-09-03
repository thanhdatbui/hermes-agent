# Hermes Session Direct Recovery & Pytest Alert Suppress (2026-08-19)

## 1. Chuyển Đổi Kiến Trúc: Gom Toàn Bộ Auto-Recovery về Hermes Agent Session
- **Vấn đề cũ**: `automation-core/alerts.py` tự động spawn subprocess chạy ngầm `ai_recovery/agent.py`. Tiến trình này không có đầy đủ công cụ kiểm thử, dễ bị lỗi parse model dẫn đến fallback cứng gửi phím Back mù quáng làm hỏng hiện trường lỗi.
- **Kiến trúc mới**:
  - Tắt hoàn toàn subprocess `agent.py` trong `alerts.py`.
  - Script khi gặp sự cố chỉ làm nhiệm vụ: **Giữ nguyên hiện trường + Gửi ảnh đóng dấu Banner đỏ về Telegram Farm Alerts** với trạng thái `🟡 GIỮ HIỆN TRƯỜNG ĐỂ HERMES AGENT XỬ LÝ`.
  - **Hermes Agent (Session trực tiếp)** đảm nhận toàn bộ luồng cứu hộ:
    1. Soi ảnh bằng `vision_analyze` và đọc XML qua ATX/logs.
    2. Sửa code trực tiếp trong file repo.
    3. Chạy `pytest` test suite kiểm chứng chất lượng.
    4. Gửi lệnh ADB chính xác lên thiết bị để giải phóng màn hình.
    5. Đưa ra báo cáo phân tích và kết quả minh bạch, chấm dứt hoàn toàn mẫu câu rập khuôn.

## 2. Chặn Live Telegram Alerts Khi Chạy Pytest Unit Tests
- Khi chạy `pytest` cho các test suite (như `test_multi_machine_feed_session.py`), các test case giả lập lỗi máy (ví dụ Máy 11 `user11`, mock MagicMock, no VPN...) có thể gọi `send_farm_machine_alert` và bắn tin nhắn giả lập lên nhóm Telegram thật.
- **Giải pháp chuẩn hóa trong `alerts.py`**:
  ```python
  # Bỏ qua gửi Telegram alert khi đang chạy trong môi trường Unit Test
  if "PYTEST_CURRENT_TEST" in os.environ:
      return False
  ```
- Đảm bảo 100% tin nhắn trên kênh Telegram Farm Alerts là sự cố thực tế từ các thiết bị Android vật lý.

## 3. Cách Ly Cooldown Nhả Follow Riêng Từng Nick (`account_row_index`)
- Khi một nick bị TikTok nhả nút Follow sau khi vuốt kiểm tra (`FOLLOW_FAILED` / `bị nhả follow sau vuốt`):
  - Cờ Cooldown trong ngày `follow_failed_date = "YYYY-MM-DD"` được lưu độc lập theo từng tài khoản:
    `follow_state_{machine}_row_{account_row_index}.json`.
  - Chỉ riêng nick đó bị dừng follow trong ngày (các phiên sau chỉ nuôi feed).
  - Các nick khác trên cùng máy đó (khác Row / khác Ca) vẫn chạy lướt Feed và Follow chéo bình thường.
  - Sang ngày mới (00:00), cờ `follow_failed_date` tự động hết hạn và reset về trạng thái bình thường.

## 4. Xử Lý Các Popup Đặc Biệt Mới Trên Feed TikTok:
- **Quảng cáo Enfagrow A+ / CTA Overlay**: Bấm nút "Đóng" (`id/hwn`, $x=540, y=1106$).
- **Trang hồ sơ thương hiệu (Closeup product grid)**: Gửi `keyevent BACK` để thoát về Feed.
- **Trang tìm kiếm / Bàn phím ảo**: Gửi `keyevent BACK` đóng bàn phím và đóng màn hình tìm kiếm về Feed.
- **Thẻ đề xuất kết bạn / Người mà bạn có thể biết trên Feed**: Bấm nút **"Follow lại"** màu đỏ.
- **Followers List Idle Scrolls**: Giới hạn `idle_scrolls <= 5` + thêm random jitter (1.2s - 2.5s) giữa các lần cuộn để chống anti-bot detection.
