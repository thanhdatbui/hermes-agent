# Fix Video Count Workbook Parsing & Proxy Migration Follow Disable (20/08/2026)

## 1. Nguyên Nhân Acc Row 2 Bị Skip Follow Dù Đã Đăng Video
- **Hiện tượng**: Sáng ngày chẵn (20/08), dàn nick Row 2 (Acc 2) dù đã có từ 1 đến 6 video đăng trong `taikhoan_run_safe.xlsx` nhưng khi chạy feed lại bị bỏ qua hoàn toàn bước follow (`skipped: zero-video-follow-disabled` trên 100% 88 máy).
- **Nguyên nhân gốc rễ**:
  - Module `core/feed_session_workbook.py` khi đọc file Excel chỉ parse các cột `may`, `device id`, `tik`, `id` mà thiếu định nghĩa cho cột `Video Đã Đăng` (`video a ang` / `video da dang`).
  - Do đó thuộc tính `video_count` trong đối tượng `MachineAccount` bị rỗng / mặc định = 0.
  - Khi luồng nuôi kết thúc và gọi `_run_follow_hook()`, bộ lọc an toàn farm (`video_count <= 0`) tự động kích hoạt chế độ Skip Follow để bảo vệ nick.
- **Cách khắc phục chuẩn**:
  - Bổ sung `VIDEO_COUNT_COLUMNS = ("video da dang", "video a ang", "video", "videos", "video count", "so video", "da dang")` vào `feed_session_workbook.py`.
  - Parse số lượng video thực tế vào `MachineAccount.video_count` (giữ nguyên `as_dict()` tương thích ngược không thêm key thừa).

## 2. Quy Tắc Tắt Toàn Diện Follow Cho Mọi Row Trong Giai Đoạn Đổi Proxy
- **Quy tắc vận hành**:
  - Theo lệnh của người vận hành (20/08), toàn bộ farm trong giai đoạn chuyển đổi proxy và rửa IP phải **TẮT HOÀN TOÀN TÍNH NĂNG FOLLOW** cho tất cả các nick (kể cả Row 1 và Row 2 có video).
  - Đặt cờ kiểm soát cứng `ALLOW_CROSS_REPO_FOLLOW = False` ở ngay đầu hàm `_run_follow_hook()` trong `multi_machine_feed_session.py`.
  - Mọi nick khi kết thúc feed session đều ghi log an toàn:
    `"reason": "farm-follow-temporarily-disabled-for-proxy-migration"`
  - Khi nào proxy ổn định sau vài ngày và có lệnh mở lại từ user $\rightarrow$ chỉ cần chuyển cờ `ALLOW_CROSS_REPO_FOLLOW = True` là hệ thống tự động nhận diện đúng số video để đi follow chuẩn xác.
