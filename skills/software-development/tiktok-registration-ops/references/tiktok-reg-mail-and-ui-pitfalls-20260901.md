# TikTok Registration & Mailbox Triage Learnings (2026-09-01)

## 1. Truyền `--email` trong `_run_all_targets.py` xuống `social_reg_v1.py`
- Khi detector chọn 1 target (ví dụ Hotmail mới mua), `_run_all_targets.py` phải truyền tường minh `--email <email>` vào tiến trình con `social_reg_v1.py`.
- Nếu thiếu cờ `--email`, `social_reg_v1.py` sẽ duyệt ngược danh sách trong `gmail_clean_v2.xlsx` từ dưới lên và bốc nhầm các tài khoản Gmail cũ (không còn đăng nhập trên thiết bị thật), dẫn đến lỗi `tulanh... khong co trong Gmail account list`.

## 2. Popup Auto-Sync của ứng dụng Gmail
- Dialog hệ thống *"Bật tính năng tự động đồng bộ hóa?"* của Gmail có thể mang resource ID `com.google.android.gm:id/alertTitle` hoặc `alertTitle`.
- Bộ lọc `_dismiss_gmail_popups` phải kiểm tra cả `alertTitle`/`alert_title` và text `bat tinh nang tu dong dong bo hoa` để tap nút `Bật` (`android:id/button1`), tránh kẹt `no_inbox_marker`.

## 3. TikTok Account Switcher layout mới
- Một số phiên bản TikTok hiển thị header với resource ID `pkh` / `pke` thay vì `p48` / `pcs`.
- Hàm `_try_open_account_dropdown_once` cần bổ sung `pkh`, `pke` vào danh sách sticky bar & account row selectors để mở được bottom sheet chọn/thêm tài khoản.

## 4. AdbKeyboard Socket Hang / Typing Failure
- Khi `type_into_node` qua `AdbKeyboard` không inject được chữ vào `EditText` (ô nhập email vẫn trống / placeholder), nguyên nhân là daemon `atx-agent` hoặc UIAutomator stub bị mất socket kết nối.
- Fix chuẩn:
  1. `pkill -9 -f atx-agent` & `am force-stop com.github.uiautomator`
  2. Khởi động lại daemon `/data/local/tmp/atx-agent server -d`
  3. Kích hoạt stub bằng `monkey -p com.github.uiautomator 1`
