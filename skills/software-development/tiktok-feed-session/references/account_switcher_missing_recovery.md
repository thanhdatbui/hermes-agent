# Xử lý Account Switcher Missing Expected & Auto-Login Recovery

## Bối cảnh & Triệu chứng
- **Lỗi**: `manual-needed:account-switcher-missing-expected: expected account not found in account switcher`
- **Hiện trường**: TikTok đang mở modal bottom sheet "Chuyển đổi tài khoản" (`account switcher`), danh sách các tài khoản hiện có không chứa tài khoản mục tiêu từ workbook (ví dụ: `stevemgjqec`), cuối sheet có nút "+ Thêm tài khoản".

## Pitfalls & Quy tắc phục hồi trong `feed_swipe_smoke.py`

1. **Không để kẹt Modal Account Switcher**:
   - Khi `_find_account_switch_option(popup_xml, expected)` không tìm thấy tài khoản mục tiêu, sheet "Chuyển đổi tài khoản" vẫn đang mở trên màn hình thiết bị.
   - Nếu gọi trực tiếp `_maybe_recover_missing_account_via_login` hoặc kết thúc với `manual-needed` mà không đóng sheet, UI của máy bị che phủ, làm luồng login recovery hoặc các phiên tiếp theo bị kẹt/lỗi tương tác.
   - **Bắt buộc**: Phải gửi phím `BACK` (`ctx.adb.shell(["input", "keyevent", "4"])`) để dismiss switcher sheet về trạng thái Profile sạch trước khi gọi reconcile login hoặc trước khi trả về kết quả lỗi.

2. **Cơ chế Reconcile Auto-Login Recovery**:
   - `_maybe_recover_missing_account_via_login` gọi subprocess `reconcile_tiktok_accounts.py` với các tham số:
     `--workbook`, `--machines`, `--adb-path`, `--source-runner`, `--login-project`, `--login-workbook`, `--proxy-mapping`, `--allow-live-reconcile`, `--full-scope-takeover`.
   - Các biến mặc định (`DEFAULT_RECONCILE_*`) trỏ tới:
     - Python: `D:/Taadaa/python-envs/tiktok-reg-recovery/Scripts/python.exe`
     - Reconcile Script: `D:/Taadaa/tiktok-log-in/scripts/reconcile_tiktok_accounts.py`
     - Safe Workbook: `D:\OneDrive\TaadaaData\kibe\taikhoan_run_safe.xlsx`
     - ADB: `C:\Program Files (x86)\xiaowei\tools\adb.exe`
     - Login Project: `D:\Taadaa\Tiktok_Reg`
     - Login Workbook: `D:\OneDrive\TaadaaData\kibe\taikhoan_dat_v2_updated .xlsx`
     - Proxy Mapping: `D:\OneDrive\TaadaaData\kibe\PROXYgandienthoai.xlsx`
   - Cần đảm bảo `allow_auto_reconcile=True` được giữ nguyên khi preflight profile phát hiện thiếu account.

3. **Cảnh báo quét đĩa (Disk Scan Timeout)**:
   - Repo `tiktok-luot nuoi acc` chứa thư mục `.ai-runs`, `runs`, `artifacts` có dung lượng và số file rất lớn.
   - TUYỆT ĐỐI KHÔNG dùng `Path.glob('**/*')`, `os.walk`, `search_files` toàn repo vì sẽ bị timeout 900s.
   - Luôn dùng `python D:/Taadaa/tools/inspect_machine.py <N>` hoặc truy cập thẳng file cụ thể theo cấu trúc biết trước.
