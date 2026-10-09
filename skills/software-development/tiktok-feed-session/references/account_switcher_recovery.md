# Xử lý lỗi `account-switcher-missing-expected` trong TikTok Feed Session

## Triệu chứng
- Lỗi: `manual-needed:account-switcher-missing-expected: expected account not found in account switcher`
- Màn hình TikTok: Menu switcher "Chuyển đổi tài khoản" đang mở, hiển thị các tài khoản đã đăng nhập và nút `+ Thêm tài khoản`.
- Tài khoản mong đợi (theo hàng chỉ định trong `taikhoan_run_safe.xlsx`) hoàn toàn không có trong danh sách switcher của máy.

## Nguyên nhân gốc rễ
1. **Nick chưa có trên máy:** Tài khoản được chỉ định chạy (theo workbook) chưa từng được đăng nhập hoặc đã bị logout khỏi thiết bị.
2. **Kẹt tại Profile Switcher Flow:**
   - Tại `D:/Taadaa/tiktok-luot nuoi acc/python_runner/flows/feed_swipe_smoke.py` (`verify_and_switch_profile`):
     - Hàm `_find_account_switch_option(popup_xml, expected)` không tìm thấy tài khoản.
     - Code đặt `last_reason = "manual-needed:account-switcher-missing-expected: expected account not found in account switcher"`.
   - Cơ chế fallback `_maybe_recover_missing_account_via_login()` gọi script `reconcile_tiktok_accounts.py` (`D:/Taadaa/tiktok-log-in/scripts/reconcile_tiktok_accounts.py`).
   - Nếu reconcile không kích hoạt hoặc trả về `False` (do modal switcher che màn hình, cờ auto-reconcile bị tắt, hoặc device-lock), runner dừng lại ở trạng thái `ExitStatus.MANUAL_NEEDED`.

## Quy trình xử lý chuẩn
1. **Kiểm tra workbook gán tài khoản:**
   - Đọc trực tiếp `D:\OneDrive\TaadaaData\kibe\taikhoan_run_safe.xlsx` để xác nhận nick thuộc Row nào của máy N.
2. **Khắc phục trong flow `feed_swipe_smoke.py`:**
   - Đảm bảo dismiss modal switcher trước khi kích hoạt login flow bổ sung tài khoản.
   - Kiểm tra và tối ưu logic nhận diện nút `+ Thêm tài khoản` để tự động chuyển tiếp sang nhánh đăng nhập khi tài khoản chưa có trong switcher.
3. **Pitfall nghiêm cấm khi điều tra:**
   - **CẤM quét đĩa đệ quy trên `.ai-runs`:** Thư mục `.ai-runs` chứa hàng nghìn thư mục con và tệp tin, quét đệ quy (`glob('**/*')`, `os.walk`) sẽ bị timeout (900s) và làm kiệt turn budget.
   - Chỉ đọc file cụ thể hoặc kiểm tra trực tiếp code trong `python_runner/flows/feed_swipe_smoke.py`.
