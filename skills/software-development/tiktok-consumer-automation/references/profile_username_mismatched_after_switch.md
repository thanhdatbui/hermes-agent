# Root Cause & Pattern: Profile Username Still Mismatched After Switch

## Triệu chứng & Bối cảnh
Khi chạy feed session trên máy (ví dụ Máy 58: tài khoản mong muốn `lamnhu3003`, hiện tại `khoa4597`), runner báo lỗi:
`last_reason = "profile username still mismatched after switch"`
Màn hình kẹt lại ở tab Hồ sơ với tài khoản hiện tại không đổi.

## Nguyên nhân gốc rễ (Root Cause)
1. **Thiếu trigger Auto-Reconcile Fallback:**
   - Trong `verify_and_switch_profile` (`python_runner/flows/feed_swipe_smoke.py`), điều kiện kích hoạt auto-login reconcile là:
     ```python
     if allow_auto_reconcile and _is_account_switcher_missing_expected_reason(last_reason):
     ```
   - Điều kiện này chỉ kiểm tra chuỗi `manual-needed:account-switcher-missing-expected`.
   - Khi tài khoản mục tiêu không chuyển đổi được sau các lần thử (do chưa đăng nhập, session hết hạn, hoặc switcher không phản hồi), `last_reason` trở thành `"profile username still mismatched after switch"`, dẫn tới việc runner bỏ qua auto-reconcile và trả về `ExitStatus.MANUAL_NEEDED`.

2. **Tọa độ click trên Account Switcher Item:**
   - Khi phần tử dòng tài khoản có bounds full-width (chiều rộng >= 600px), việc tính center mặc định có thể rơi vào khoảng trống bên phải (dead margin) nơi không nhận sự kiện tap.
   - Cần đảm bảo định vị đúng inner TextView / avatar hoặc clamp bounds về vùng nội dung có thể click.

3. **Cảnh báo timeout khi tra cứu mã nguồn:**
   - Tuyệt đối không dùng `grep -rn` hoặc `glob(recursive=True)` quét qua `.ai-runs`, `python_runner`, hay thư mục mẹ trên Windows/MSYS vì sẽ gây timeout 900s.
   - Chỉ mở trực tiếp file flow đã biết (`feed_swipe_smoke.py`, `account_switcher.py`) và đọc theo offset/phạm vi hàm cụ thể.
