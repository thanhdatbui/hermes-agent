# TikTok Profile Account Switcher & Sticky Top Bar Navigation

## 1. Vấn đề trên UI TikTok 46.x
Trên các phiên bản TikTok mới (như TikTok 46.x trên Samsung S7), khi vào tab Hồ sơ / Profile:
- Tên tài khoản / handle và nút dropdown chevron (`rv5`, `rz5`, `sh3`) có thể nằm ở giữa màn hình (y ~ 500-600px).
- Khi tap vào các node này, danh sách chuyển đổi tài khoản (bottom sheet `Chuyển đổi tài khoản` / `Thêm tài khoản`) thường **không bung ra** (no-op hoặc bị vướng layout header).

## 2. Quy trình điều hướng chuẩn (Swipe to reveal Sticky Header)
1. **Vuốt màn hình lên 400px** (`swipe 540 1000 540 600 400`):
   - Thao tác này đẩy nội dung profile lên và làm thanh chuyển tài khoản thu nhỏ (Sticky Top Bar) ghim chặt ở mép trên màn hình (`y <= 350px`).
   - Resource-ID của thanh này thường là `pcs`, `p01`, `p1j`, `qx0`, hoặc `qzr`.
2. **Tap trực tiếp vào thanh Sticky Top Bar** (tọa độ tâm, ví dụ `540, 150`):
   - Ngay lập tức mở bottom sheet `Chuyển đổi tài khoản` chứa danh sách tài khoản hiện có và nút `Thêm tài khoản` (`ldd` / bounds `[540, 1788]`).
3. **Nếu cần reset vị trí:** Vuốt kéo xuống (pull-down `swipe 540 400 540 1400 400`) để trả profile về đỉnh trước khi thực hiện các thao tác khác.

## 3. Quy tắc Khóa Thiết Bị (Device Lock Lifecycle)
- **Khi chạy batch Reg / Login:** Bắt buộc bật `DEVICE_LOCK_ENABLED=1`.
- **Duy trì Lock:** Khóa máy được giữ trong suốt quá trình chạy.
- **Mở Lock:** CHỈ mở lock khi:
  1. Tác vụ đạt **SUCCESS** (đã cập nhật tracking workbook và đóng app về màn hình chính Home).
  2. Hoặc khi **User trực tiếp ra lệnh mở khóa**.
- Khi gặp lỗi hoặc chờ OTP/Captcha: Giữ nguyên hiện trường và **tiếp tục giữ lock** để tránh các tiến trình khác tranh chấp máy.

## 4. Phòng ngừa Lỗi `TARGET_INVENTORY_CONFLICT`
- Trong file `taikhoan_run_safe.xlsx`, Cột 2 phải luôn là `Device ID / Serial` (16-18 ký tự).
- Tuyệt đối không ghi đè ngày tạo (`dd/mm/yyyy`) vào Cột 2 khi lưu tracking, vì script `_detect_clean.py` sẽ kiểm tra tính nhất quán và báo lỗi conflict nếu cùng 1 STT máy có 2 serial khác nhau.
