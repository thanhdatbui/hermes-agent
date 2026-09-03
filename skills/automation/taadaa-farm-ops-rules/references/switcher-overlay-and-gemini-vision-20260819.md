# Tổng Kết Vận Hành: Xử Lý Kẹt Account Switcher, Nhả Follow Cleanup & Chuyển Đổi Vision Engine (19/08)

## 1. Xử Lý Kẹt Bàn Phím / Overlay Khi Mở Account Switcher
- **Hiện tượng (Máy 21)**: Khi tap vào header profile để mở danh sách chọn tài khoản (Account Switcher), thiết bị chạm nhầm vào ô nhập bình luận hoặc overlay đang mở, làm bật bàn phím ảo che khuất menu chọn nick ➔ Script không dump được danh sách tài khoản và báo lỗi `manual-needed:account-switcher-not-open`.
- **Cơ chế Auto-Recovery đã handle trong `feed_swipe_smoke.py`**:
  1. Gửi phím `KEYCODE_BACK` (keyevent 4) để hạ bàn phím ảo và đóng overlay.
  2. Nghỉ 1.0s ➔ Thực hiện tap lại vào `switch_anchor` (tên hiển thị / Display Name).
  3. Capture lại XML xác nhận đã mở menu chọn nick thành công để tiếp tục phiên.

## 2. Dọn Dẹp Ứng Dụng Về Home Khi Dính Nhả Follow
- **Quy chuẩn trong `tiktok-follow` (`follow_engine.py`)**:
  - Khi phát hiện TikTok nhả follow sau khi vuốt pull-to-refresh (`FOLLOW_FAILED`):
    1. Ghi nhận `follow_failed = True` và `follow_failed_date = YYYY-MM-DD` cô lập riêng cho nick (Row) đó trong ngày.
    2. **Tự động đóng app TikTok (`close_all_apps`) ➔ Xóa danh sách ứng dụng gần đây (Clear Recents) ➔ Đưa máy về màn hình chính (Home)** để giải phóng tài nguyên và tránh treo app trên màn hình.

## 3. Chuyển Đổi Model Vision Engine Sang Gemini 3.7 Flash
- **Lý do**: Claude Sonnet/Opus có độ trễ lớn và dễ rơi vào các phán đoán đoán mò nếu thiếu context. `ag/gemini-3.7-flash-high` phản hồi siêu nhanh (~1.2s), nhận diện chữ Tiếng Việt và các nút bấm chính sách/quảng cáo trên màn hình điện thoại nhạy bén và chính xác hơn hẳn.
- **Cấu hình trong `ai_recovery/vision_client.py`**:
  - `NINEROUTER_URL = "http://127.0.0.1:20128/v1/chat/completions"`
  - `VISION_MODEL = "ag/gemini-3.7-flash-high"`
- **Nguồn Master API Key 9Router**: Lưu trong `C:\Users\Kibe\AppData\Roaming\9router\db\data.sqlite` (bảng `apiKeys`). Bắt buộc đồng bộ vào `NINEROUTER_API_KEY` trong `C:\Users\Kibe\AppData\Local\hermes\.env`.
