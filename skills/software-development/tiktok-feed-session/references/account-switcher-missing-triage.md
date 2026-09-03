# Triage: `manual-needed:account-switcher-missing-expected`

## 1. Hiện tượng & Triệu chứng
- Telegram bot Farm Alerts phát cảnh báo:
  - `🚨 [MÁY X] DỪNG PHIÊN`
  - `• Script:` `multi-machine-feed-session`
  - `• Tài khoản:` `<username_row_R>`
  - `• Lý do:` `manual-needed:account-switcher-missing-expected: expected account not found in account switcher`
  - `• Trạng thái:` 🟡 `GIỮ HIỆN TRƯỜNG ĐỂ HERMES AGENT XỬ LÝ`

## 2. Nguyên nhân
- Khi ca nuôi acc theo row (ví dụ Row 4) chạy trên máy X, script vào `Hồ sơ` -> mở bảng `Chuyển đổi tài khoản` (Account Switcher bottom sheet).
- Script quét danh sách tài khoản hiện có trong RecyclerView của TikTok nhưng không tìm thấy username được chỉ định theo cấu hình slot `account_row` của máy trong `taikhoan_run_safe.xlsx`.
- Máy đó có thể mới chỉ đăng nhập 1-3 nick (ví dụ Row 1, 2, 3), chưa được đăng nhập nick Row 4.

## 3. Quy trình chẩn đoán (Triage Protocol)
1. **Kiểm tra cấu hình phân bổ tài khoản:**
   - Tra cứu `D:\OneDrive\TaadaaData\kibe\taikhoan_run_safe.xlsx` tại cột `May` = X.
   - Xác định username kỳ vọng tại slot `account_row` đang chạy.
2. **Kiểm tra hiện trường từ Artifact:**
   - Mở file `summary.txt` tại thư mục runtime:
     `D:\Taadaa\runtime\kibe\live\<YYYY-MM-DD>\row-<R>-<HHMMSS>\<run_id>\machines\machine_<X>\<run_id>\summary.txt`
   - Đọc file UI XML được chụp tại bước guard:
     `.../profile_preflight_switcher_1_guard/attempt_1/ui.xml`
   - Kiểm tra các node `android.widget.Button` có `content-desc` trong `androidx.recyclerview.widget.RecyclerView` để thấy danh sách các nick đang login thực tế trên máy.
3. **Xử lý:**
   - Đăng nhập nick bị thiếu vào máy qua luồng `tiktok-login-automation` hoặc công cụ login trước ca tiếp theo của row đó.
