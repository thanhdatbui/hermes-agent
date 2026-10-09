# Bẫy Nạp Nhầm Sheet Audit `wb.worksheets`, Target In Switcher Bypass & Nhầm Lẫn Screencap Launcher (2026-09-25)

## 1. Hiện Tượng & Sự Cố Thực Tế (Máy 72 - 25/09/2026)
- **Cảnh báo P0**: `manual-needed:account-switcher-missing-expected: expected account not found in account switcher` trên Máy 72 (tài khoản `@m.ngc4624`).
- Khi ca nuôi feed gọi auto-login:
  `python tiktok_login_v1.py 72 --email m.ngc4624 --ss --allow-parent-lock`
  tiến trình con thoát ngay ở giây 23 với lỗi:
  `STOPPED: Khong tim thay Gmail live tren may khop local-part 'duongthimyngoc190320011903' de xac nhan domain`.

## 2. Root Cause 1: Vòng lặp `wb.worksheets` nạp nhầm Sheet Audit / Nháp
- **Nguyên nhân**: Trong `tiktok_login_v1.py`, hàm `load_tracking_accounts_for_stt` lặp qua toàn bộ `wb.worksheets` của file Excel master `taikhoan_dat_v2_updated .xlsx`.
- Sổ cái master ngoài sheet chính chủ `Tài Khoản` còn có các sheet audit: `Máy Thiếu Acc`, `Audit Pending`, `Khong Co Trong GmailClean`.
- Tại dòng 126 sheet `Khong Co Trong GmailClean`, tài khoản `@m.ngc4624` bị ghi email khuyết domain `@gmail.com` (`duongthimyngoc190320011903`), khiến hàm `_infer_login_email` gắn cờ `email_missing_domain`.
- Khi `resolve_missing_domains_from_device` thấy cờ này, nó gọi `live_gmail_accounts` để đọc app Gmail trên điện thoại. Vì mail này không tồn tại trong app Gmail của máy 72, script quăng `RuntimeError` crash ngay lập tức.
- **Hậu quả**: Bỏ qua hoàn toàn dữ liệu chuẩn có đầy đủ ID + Password + 2FA TOTP trong sheet `Tài Khoản`.

### Khắc phục:
1. **Lọc cứng sheet canonical**: Chỉ nạp `Tài Khoản` (hoặc `Accounts`), loại trừ 100% các sheet phụ:
   ```python
   if "Tài Khoản" in wb.sheetnames:
       worksheets = [wb["Tài Khoản"]]
   elif "Accounts" in wb.sheetnames:
       worksheets = [wb["Accounts"]]
   else:
       worksheets = [
           ws for ws in wb.worksheets
           if ws.title not in ("Khong Co Trong GmailClean", "Máy Thiếu Acc", "Audit Pending")
       ] or [wb.active]
   ```
2. **Ưu tiên canonical record trong `pick_accounts`**: Nếu bộ lọc khớp nhiều account, ưu tiên account thuộc sheet `Tài Khoản`/`Accounts` và không mang cờ lỗi `email_missing_domain`.
3. **Fail-soft domain resolution**: Trong `resolve_missing_domains_from_device`, nếu account đã có sẵn `id` + `tiktok_pass` và không chạy cờ `--otp-only`, tự động fallback suy diễn `f"{local_part}@gmail.com"` thay vì raise crash.

## 3. Root Cause 2: Account Đã Nằm Ở Đáy Switcher Nhưng Cố Bấm "Thêm tài khoản"
- Trên layout mới của TikTok (v30+), danh sách account rows trong Switcher sử dụng resource-id `com.ss.android.ugc.trill:id/ng8` (text username) và `com.ss.android.ugc.trill:id/luu` (container content-desc username).
- Khi máy đã có đủ 8 tài khoản (trong đó tài khoản mục tiêu `@m.ngc4624` nằm ở dòng thứ 8 ở tọa độ đáy `[0,1788][1080,1920]`), nút "Thêm tài khoản" biến mất hoàn toàn.
- `ensure_login_entry_screen` mù quáng gọi `tap_add_account` $\to$ không tìm thấy nút $\to$ raise error dừng login.

### Khắc phục:
1. **Target in Switcher Auto-Switch**: Trước khi bấm `tap_add_account`, quét UI XML của Switcher. Nếu thấy account mục tiêu (theo `id` hoặc local-part email) đã xuất hiện trên Switcher:
   - Tap thẳng vào node/bounds của account đó để chuyển đổi.
   - Trả về `"already_logged_in"` và return `True` thành công ngay, bỏ qua form đăng nhập.
2. **Bổ sung `ng8` vào bộ đếm tài khoản**: Trong `tap_add_account` (`social_reg_v1.py`), thêm `ng8` vào danh sách resource-id đếm account để tránh tính toán sai số lượng account trên máy.

## 4. Cảnh Báo Quy Trình: Bẫy Screencap Sau Khi App Đã Văng Về Launcher
- **Lỗi ngớ ngẩn thường gặp**: Sau khi runner gặp lỗi và thoát, app TikTok đã bị `am force-stop` hoặc đóng về màn hình chính Android (`LauncherActivity`).
- Coordinator chạy `adb exec-out screencap` lấy màn hình hiện tại rồi gửi cho User và tuyên bố đây là "ảnh Switcher" $\to$ Bị User mắng vì gửi ảnh Launcher Home!
- **Quy tắc bắt buộc**:
  - Khi cần bằng chứng của Switcher / Login Form / Popup lúc xảy ra sự cố, **PHẢI lấy đúng file ảnh chụp lưu trong thư mục artifacts của đợt chạy** (ví dụ: `screenshots_social/fail_*.png` hoặc `artifacts/**/screen.png`).
  - Lệnh `adb exec-out screencap` thời gian thực chỉ phản ánh trạng thái NGAY LÚC NÀY của máy (thường là Launcher Home), TUYỆT ĐỐI CẤM dùng nó làm bằng chứng cho màn hình app trước đó.
