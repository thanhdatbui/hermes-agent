# Case Study: Switcher Pre-Opened State, Non-Fatal Back, & Edit Profile Bounds (2026-10-20)

## 1. Hiện Tượng & Sự Cố (Problem Statement)
Trong quá trình chạy tự động hóa chuyển tài khoản và đổi tên hàng loạt (`tiktok_rename_rolling_watchdog.py` / `do_rename_canonical_runner.py`):
1. **Lỗi `exit_2` hàng loạt (`canonical switcher khong chuyen duoc sang @username`):**
   - Xảy ra đồng thời trên nhiều máy (`m2`, `m18`, `m20`, `m28`, `m32`).
   - Khi runner bắt gặp màn hình đang ở trạng thái `SWITCHER` (sheet danh sách tài khoản đã mở sẵn), runner gọi `canonical_switch_account`.
   - Hàm `open_account_switcher` của `automation-core` mặc định tìm semantic button "Hồ sơ" / "Profile" ở thanh bottom navigation để đi từ Profile root.
   - Khi khay Switcher đang che kín bottom nav, `open_account_switcher` ném lỗi `PROFILE_TARGET_NOT_FOUND`.
   - Runner cũ lập tức `raise Abort(...)`, khiến tiến trình thoát ngay với exit code 2 thay vì đóng khay.

2. **Lỗi Vòng Lặp Kẹt Màn Hình Sửa Bio (Loop 35 Bước trên Galaxy S7):**
   - Khi OCR không tìm thấy chữ "Sửa hồ sơ" to, code cũ tap fallback vào tọa độ `(360, 730)`.
   - Trên Galaxy S7, `(360, 730)` rơi trúng vào nút `+ Thêm tiểu sử` hoặc dòng Bio (`y=680..725`), làm mở màn hình sửa Bio. Runner nhận thấy không có yêu cầu sửa Bio nên bấm Back, rồi vòng lại tap tiếp `(360, 730)` $\to$ Kẹt 35 bước rồi timeout abort.

## 2. Nguyên Tắc & Khắc Phục Chuẩn Hóa (Standardized Invariants)
1. **Kiểm Tra Trạng Thái Switcher Trước Khi Mở (`is_switcher_open`):**
   ```python
   from automation_core.tiktok.account_switcher import is_switcher_open, open_account_switcher

   adapter = FollowAdapter(ADB, serial)
   if not is_switcher_open(adapter):
       open_account_switcher(adapter, profile_attempts=3, switcher_attempts=3, load_attempts=3)
   post_xml = select_exact_account(adapter, target_user)
   verify_selected_account(adapter, target_user, xml_text=post_xml)
   ```
2. **Xử Lý Thất Bại Không Crash (Non-Fatal Back Fallback):**
   - Nếu `canonical_switch_account` trả về False trong trạng thái `SWITCHER`, cấm `raise Abort` văng lỗi ngay lập tức.
   - Bắt buộc thực hiện `keyevent 4` để đóng khay Switcher trở về Profile/Feed và cho phép State-Machine thử lại ở các bước kế tiếp.
3. **Tọa Độ Bút Chì Profile Galaxy S7 Chuẩn:**
   - Cạnh phải tên trên Galaxy S7 nằm tại `(870, 558)`. CẤM tap vào vùng `y >= 680` khi đang tìm nút sửa tên/hồ sơ vì đó là vùng của Bio.
