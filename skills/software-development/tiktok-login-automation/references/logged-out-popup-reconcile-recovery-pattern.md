# Logged-out Popup Dismiss & Auto-Reconcile Recovery Pattern

## Bối cảnh & Hiện tượng
1. **Popup "Trạng thái tài khoản" (Account Logged Out):**
   - Text: `"Trạng thái tài khoản"`, `"Tài khoản của bạn đã bị đăng xuất. Hãy thử đăng nhập lại."`
   - Nút: `"OK"` / `"Đã hiểu"` / `"Xác nhận"`.
   - Vấn đề cũ (Anti-pattern): Phân loại popup này thành `manual-needed:login` / fail-closed, khiến device bị lock cách ly và sleep 90 phút.

2. **Quy trình xử lý chuẩn (Dismiss + Auto-Reconcile):**
   - **Bước 1: Dismiss popup:** Tìm nút `OK` thuộc hierarchy của TikTok package (`com.ss.android.ugc.trill`, `com.zhiliaoapp.musically`), bấm `OK` và xác nhận dialog đã đóng hoàn toàn.
   - **Bước 2: Trigger Account Reconcile:** Không dừng phiên ở trạng thái thiếu tài khoản; lập tức kích hoạt runner reconcile (`reconcile_tiktok_accounts.py` / `tiktok-log-in`) cho đúng machine/serial target để:
     - So khớp danh sách tài khoản hiện có trong Account Switcher với `taikhoan_run_safe.xlsx`.
     - Phát hiện tài khoản bị thiếu/văng session.
     - Tự động đăng nhập lại tài khoản thiếu (qua OTP Hotmail trên app Outlook hoặc mật khẩu + 2FA).
   - **Bước 3: Tiếp tục phiên chạy:** Sau khi reconcile trả về `RECOVERED_SUCCESS` và đủ 3/3 slot tài khoản, đưa app về Home và tiếp tục feed/follow/upload.

## Pitfall: False Positive `_is_profile_subpage` trên Profile Root (TikTok 46.x)
- **Hiện tượng:** Màn hình Profile Root xuất hiện icon button "Số lượt xem hồ sơ" (`desc="Số lượt xem hồ sơ"` / `"Profile views"`), trùng với `_SUBPAGE_MARKERS`.
- **Hậu quả:** `leave_profile_subpage` tưởng nhầm đang ở trang con xem lịch sử profile views, gửi phím Back vô hiệu trên Profile Root và fail với lỗi `PROFILE_SUBPAGE_STUCK: Profile subpage remained open`.
- **Khắc phục chuẩn:**
  - Định nghĩa `_is_profile_root_screen` bắt buộc thỏa mãn cả (1) hành động đặc trưng của root (`"menu hồ sơ"`, `"profile menu"`, `"sửa hồ sơ"`, `"edit profile"`, `"thêm tiểu sử"`) VÀ (2) thanh điều hướng dưới cùng đang chọn tab Profile kèm tab Trang chủ (`_selected_bottom_tab == True` và có marker Home).
  - Ưu tiên kiểm tra modal editor/prompt (Unsaved bio prompt, Edit bio editor) trước, sau đó nếu là `_is_profile_root_screen` thì return `False`, cuối cùng mới check `_SUBPAGE_MARKERS` cho subpage thật.
