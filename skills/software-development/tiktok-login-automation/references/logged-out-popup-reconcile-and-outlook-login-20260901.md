# Cross-Repo Reconcile & Hotmail Outlook OTP Login Flow (2026-09-01)

## 1. Bối cảnh & Hiện tượng
- Màn hình TikTok xuất hiện popup `Trạng thái tài khoản` (*"Tài khoản của bạn đã bị đăng xuất. Hãy thử đăng nhập lại."*).
- **Yêu cầu vận hành:** Bấm nút `OK` đóng popup giải phóng UI, sau đó BẮT BUỘC chạy ngay script `reconcile_tiktok_accounts.py` / `tiktok_login_v1.py` để kiểm tra danh sách tài khoản, phát hiện tài khoản văng/thiếu và đăng nhập lại ngay; tuyệt đối không dừng lại sau khi chỉ đóng popup.

## 2. Các điểm nghẽn & Giải pháp xử lý

### A. Lỗi `PROFILE_SUBPAGE_STUCK` do nút "Số lượt xem hồ sơ"
- **Nguyên nhân:** Trên giao diện profile TikTok mới, xuất hiện icon/button `Số lượt xem hồ sơ` (`profile views`). Hàm `_is_profile_subpage` trong `automation_core.tiktok.account_switcher` thấy marker này nên tưởng lầm máy đang ở subpage profile, cố gắng bấm Back/Cancel và ném lỗi `PROFILE_SUBPAGE_STUCK`.
- **Khắc phục chuẩn:** Thêm `_is_profile_root_screen` yêu cầu kết hợp giữa các root action (`menu hồ sơ`, `profile menu`, `sửa hồ sơ`, `thêm tiểu sử`) VÀ bottom nav bar (profile tab selected + home tab). Ưu tiên các modal/editor thật (unsaved bio, edit bio) trước, sau đó loại trừ profile root trước khi kiểm tra `_SUBPAGE_MARKERS`.

### B. Đăng nhập Hotmail vào app Outlook khi gặp màn hình OAuth
- **Hiện tượng:** Khi nhập email Hotmail vào app Outlook trên máy S7, sau khi bấm `TIẾP TỤC` -> chọn loại tài khoản `Microsoft Outlook`, màn hình mở WebView `AuthorizationActivity` yêu cầu *"Xác minh email của bạn"*.
- **Cách vượt qua:**
  1. Dưới nút *"Gửi mã"* có nút **`Sử dụng mật khẩu của bạn`** (tọa độ bounds `[288,1443][792,1494]` / center `(540, 1468)`).
  2. Tap nút này để chuyển sang form nhập mật khẩu (`passwordEntry` `[99,639][909,753]`).
  3. Gửi mật khẩu từ workbook qua `AdbKeyboard` -> bấm `Tiếp theo` `(540, 915)`.
  4. Lần lượt tap `OK` (màn hình Thông báo về tài khoản Microsoft), `CÓ LẼ ĐỂ SAU` (màn hình thêm tài khoản khác), `TIẾP THEO` -> `CHẤP NHẬN` -> `TIẾP TỤC VỚI OUTLOOK` để vào Hộp thư đến (Inbox).

### C. Đăng nhập TikTok qua Fast-path & OTP Outlook
- **Fast-path 1-tap:** Khi mở Account Switcher -> `Thêm tài khoản`, nếu TikTok hiện màn hình gợi ý *"Tiếp tục với tên @username"* trùng khớp với nick cần login -> tap trực tiếp vào center `(540, 1250)`.
- **Nhận OTP:**
  1. TikTok chuyển sang màn hình *"Nhập mã ... gửi đến ...@hotmail.com"*.
  2. Mở app Outlook (`com.microsoft.office.outlook`), thực hiện vuốt xuống (pull-to-refresh) để tải mail mới nhất.
  3. Đọc mã 6 số từ thông báo/snippet của sender TikTok (ví dụ: `276673`).
  4. Đưa TikTok về foreground và gõ lần lượt từng số vào màn hình OTP.
  5. TikTok tự động đăng nhập và chuyển vào Profile.

### D. Nghiệm thu hoàn tất
- Mở Account Switcher trên TikTok, xác thực đủ 3/3 tài khoản theo danh sách workbook (`taikhoan_run_safe.xlsx`).
- Chạy `reconcile_tiktok_accounts.py` kiểm tra đạt trạng thái `RECOVERED_SUCCESS` và `remaining_device_missing: []`.
- Đưa máy về màn hình Home, dọn dẹp sạch toàn bộ lock file.
