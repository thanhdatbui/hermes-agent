# Quy Tắc Khóa Follow Nick 0 Video & Cơ Chế Phục Hồi Hạn Mức Theo Ngày (19/08/2026)

## 1. Dữ Liệu Thực Nghiệm & Bản Chất Thuật Toán TikTok (19/08/2026)
- **Thực nghiệm trên 64 máy sáng 19/08**:
  - **Nick đã có video (Row 1: 8-12 video)**: Đạt tỷ lệ follow thành công cao ở 3-4 phiên đầu (06:00 - 08:30), follow được trung bình 4-8 nick/phiên trước khi chạm ngưỡng rate-limit buổi sáng.
  - **Nick chưa đăng video nào (Row 3, 5: 0 video)**: Bị TikTok gắn cờ bot/clone và **nhả nút follow 100% ngay từ cú tap đầu tiên (`followed = 0`)**.
- **Quy luật Daily Rolling Limit của TikTok**:
  - TikTok tính hạn mức tích lũy trong ngày (24h calendar day) kết hợp Burst velocity.
  - Khi một tài khoản bị kích hoạt nhả follow (`FOLLOW_FAILED`) trong ngày, dù cho máy nghỉ 10-12 tiếng (từ sáng tới tối), khi bấm follow lại vẫn bị nhả ngay.
  - Hạn mức chỉ được phục hồi hoàn toàn khi bước sang ngày mới (00:00).

---

## 2. Quy Tắc Khóa Cứng Follow Nick 0 Video (`multi_machine_feed_session.py`)
- Trong hàm `_run_follow_hook`:
  - Trước khi khởi chạy subprocess `run_follow`, bắt buộc kiểm tra trường `video_count` (hoặc `Video Đã Đăng` từ workbook):
  - Nếu `video_count <= 0` hoặc giá trị là `None`/chuỗi rỗng:
    - **LẬP TỨC SKIP BỎ QUA HOÀN TOÀN TIẾN TRÌNH FOLLOW**.
    - Ghi nhận `status = "skipped"`, `reason = "zero-video-follow-disabled"`, `followed_count = 0`.
    - Máy tiếp tục hoàn tất phiên nuôi feed và dọn dẹp an toàn mà không gọi follow runner.
  - Chỉ khi nick đã đăng $\ge 1$ video (tối ưu là $\ge 8$ video) mới được phép tham gia mạng lưới follow chéo.

---

## 3. Cơ Chế Tự Động Phục Hồi Cooldown Qua Ngày Mới (`follow_state.py`)
- Khi một nick bị dính nhả follow trong ngày:
  - Ghi nhận `follow_failed = True` và `follow_failed_date = "YYYY-MM-DD"` vào file state riêng của nick đó (`follow_state_<máy>_row_<index>.json`).
  - Trong hàm `_roll_day()`: Khi hệ thống phát hiện ngày hiện tại (`today`) khác với `budget_date` hoặc `follow_failed_date`:
    - Tự động reset `follow_failed = False`.
    - Xóa `follow_failed_date` khỏi state.
    - Giúp tài khoản tự động phục hồi quyền follow tự nhiên khi bước sang ngày mới mà không cần can thiệp thủ công.
