# Case Study: Switcher Tray Pre-Opened Trap & Edit Profile Pencil Fallback (2026-10-20)

## 1. Hiện Tượng & Sự Cố (Problem Statement)
Trong quá trình vận hành rolling rename watchdog trên dàn Samsung Galaxy S7:
- Hàng loạt máy báo lỗi `exit_2` (`m2`, `m18`, `m20`, `m28`) với lý do: `canonical switcher khong chuyen duoc sang @username`.
- Máy 2 kẹt 35 vòng lặp liên tiếp: mở nhầm màn hình sửa Bio thay vì Sửa hồ sơ, dẫn đến timeout abort.

## 2. Nguyên Nhân Kỹ Thuật (Root Cause)
1. **Bẫy Switcher Pre-Opened (`PROFILE_TARGET_NOT_FOUND`):**
   - Khi TikTok ở trạng thái sheet `SWITCHER` mở sẵn, runner gọi hàm `canonical_switch_account`.
   - Hàm `open_account_switcher` của `automation-core` mặc định tìm nút semantic "Hồ sơ" / "Profile" ở thanh bottom nav để mở switcher từ đầu.
   - Do màn hình đã là khay Switcher che mất bottom nav, `open_account_switcher` ném lỗi `PROFILE_TARGET_NOT_FOUND`.
   - Runner cũ bắt ngoại lệ này lập tức `raise Abort(...)`, làm tiến trình thoát ngay với exit code 2 thay vì đóng khay.

2. **Bẫy Tọa Độ Fallback Nút Sửa Hồ Sơ Lệch Vào Nút Bio:**
   - Khi OCR không tìm thấy text "Sửa hồ sơ" chữ to, code cũ tap fallback vào `(360, 730)`.
   - Trên Galaxy S7, `(360, 730)` trùng với vị trí nút `+ Thêm tiểu sử` / dòng Bio, làm bot liên tục nhảy vào màn hình sửa Bio, lúng túng bấm Back ra rồi lại tap vào tiếp.

## 3. Khắc Phục Chuẩn Hóa (Standardized Pattern)
1. **Kiểm Tra Switcher Trước Khi Mở:**
   ```python
   from automation_core.tiktok.account_switcher import is_switcher_open, open_account_switcher

   if not is_switcher_open(adapter):
       open_account_switcher(adapter, profile_attempts=3, switcher_attempts=3, load_attempts=3)
   ```
2. **Xử Lý Thất Bại Không Crash (Non-Fatal Back):**
   - Nếu `canonical_switch_account` thất bại, không `raise Abort` văng runner mà thực hiện `keyevent 4` để đóng khay Switcher và tiếp tục vòng lặp State-Machine.
3. **Tọa Độ Bút Chì Chuẩn Cho Profile S7:**
   - Nút bút chì cạnh phải tên trên Galaxy S7 nằm tại `(870, 558)`. Cấm tap vào dải `y >= 680` khi đang tìm cách sửa tên.
