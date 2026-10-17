# TikTok 'Tổng lượt thích' Milestone Popup & LIVE Camera Escape (2026-10-17)

## 1. Bẫy Popup Thành Tích "Tổng Lượt Thích" Che Switcher
- **Hiện tượng:** Khi runner điều hướng vào tab Profile để mở Account Switcher đổi tài khoản (ví dụ M45 cần chuyển sang nick Tik 4 `@giathu048`), TikTok bật popup chúc mừng:
  - **Tiêu đề:** *"Tổng lượt thích"*
  - **Nội dung:** *"<username> đã nhận tổng cộng 359 lượt thích cho tất cả video"*
  - **Nút bấm:** `[OK]` (text hoặc content_desc, nằm ở tâm giữa màn hình `[506, 1389, 575, 1425]`).
- **Hậu quả:** Popup này chặn toàn bộ tương tác lên thanh Profile header, khiến `open_switcher` không thể click vào tên nick để mở danh sách chuyển đổi, dẫn đến timeout hoặc kích hoạt soft-reboot phòng vệ sai lầm.
- **Giải pháp xử lý triệt để:**
  - Trong `prepare_switcher_anchor` (hoặc `_dismiss_simple_close_popup`):
    * Kiểm tra chuỗi `"tổng lượt thích"` hoặc `"tổng số lượt thích"` trong UI XML (casefold).
    * Quét và tap các nhãn đóng: `("OK", "ok", "Đóng", "Close", "Xong")` kiểm tra cả `text` lẫn `content_desc`.
    * Fallback coordinate tap: Tap trực tiếp vào tọa độ `(540, 1400)` nếu XML không trích xuất được nút bấm.
    * Sau khi tap, sleep 1.0s và dump lại UI XML mới trước khi tiếp tục dò anchor switcher.

## 2. Bẫy Màn Hình Camera LIVE Sau Khi Submit Video
- **Hiện tượng:** Sau khi hoàn tất điền caption và bấm nút Đăng (`POST`), TikTok đôi khi không trở về ngay Feed/Profile mà nhảy sang giao diện Camera phát LIVE (`CAMERA / TẠO / LIVE`).
- **Bẫy Android Back Key:** Trên giao diện này, app TikTok chặn lệnh `adb shell input keyevent 4` (BACK key), khiến lệnh back không có tác dụng. Runner thử 2 lần back thất bại và văng lỗi fail-closed `[LIVE_SURFACE] Màn LIVE vẫn còn sau 2 back semantic`.
- **Giải pháp xử lý triệt để:**
  - Trong hàm `_dismiss_live_surface` (hoặc `_recover_post_verify_live_surface`):
    * BẮT BUỘC tap trực tiếp vào nút `[X]` đóng camera ở góc trên bên trái màn hình: tọa độ x ~ 60, y ~ 140.
    * Kết hợp gửi lệnh `BACK` ngay sau đó.
    * Thao tác này đưa ứng dụng thoát khỏi camera surface 100% để runner quay về Profile kiểm tra lưới video (`VERIFY_POST`).

## 3. Chuẩn Hóa Header Workbook Có Ngoặc Đơn
- **Hiện tượng:** File `Tik*.xlsx` thường có header dạng chi tiết:
  - `Folder Video (Render Dich)`
  - `Video Goc (Nguon Cao)`
- **Xử lý:** Module đọc workbook (`account_source.py`) bắt buộc chuẩn hóa header bằng cách loại bỏ phần trong ngoặc đơn hoặc map regex linh hoạt `r"^folder\s*video"` và `r"^video\s*goc"`, tránh lỗi dừng pipeline `Missing required fields: Folder Video`.
