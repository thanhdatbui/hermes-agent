# Account Switcher Missing Expected Account vs Display Name & Excel Shift-Overwrite Trap

## Bối cảnh sự cố (2026-09-17)
- Farm Alert kích hoạt hàng loạt máy (M1, M14, M50, M51, M59, M60, M66, M71, M74) với chữ ký `manual-needed:account-switcher-missing-expected: expected account not found in account switcher`.
- Cơ chế tự động `_maybe_recover_missing_account_via_login` (Case 74) nhảy vào nhưng bị timeout 900s hoặc fail mã lỗi 4.

## Root Cause Analysis
1. **Lệch pha Display Name vs Username (Handle) trong Switcher:**
   - App TikTok trong danh sách Switcher hiển thị **Display Name** tiếng Việt (ví dụ `"Anh Hoang"` trên M14, `"Anh Pham"` trên M71) thay vì `@username` (`hong.bo.anh83`, `ngc.anh.phm33`).
   - Hàm `matches_switcher_identity` trong `automation-core/tiktok/account_switcher.py` chỉ so sánh chuỗi normalize giữa text node và target account, dẫn đến `False`.
   - Hệ thống tưởng lầm nick bị vắng mặt trên máy và kích hoạt auto-login reconcile.
2. **Kẹt trần 8 tài khoản do tool reg bù ghi đè / shift slot Excel thô bạo:**
   - Khi chạy reg bù (ví dụ `ensure_row_accounts.py`), tool tính toán dòng Excel theo slot và ghi đè nick mới vào file master Excel mà **không kiểm tra hoặc logout nick cũ trên điện thoại thật**.
   - App TikTok trên thiết bị vẫn giữ session của nick cũ (ví dụ `ahmetsguthe17` trên M1, `ruitataxg6j`, `gaetiwcu04c` trên M66).
   - Thiết bị chạm trần 8 nick, Switcher ẩn nút "Thêm tài khoản" (`Add account`), khiến script login tự động đâm đầu vào ngõ cụt và fail-closed.
3. **Nguy cơ mất nick vĩnh viễn nếu tự ý logout / clear data:**
   - Các tài khoản Row 1, Row 2 nuôi lâu ngày nếu email gốc (Gmail) bị checkpoint / die hoặc mất pass, nếu bị script tự tiện logout hay clear data app thì **vĩnh viễn không thể đăng nhập lại**.

## Invariant Rules & Giải pháp
1. **Tuyệt đối cấm logout / clear data mù quáng:**
   - Khi gặp alert `account-switcher-missing-expected`, bước đầu tiên là dump XML và đối soát danh sách thực tế trên app. Tuyệt đối không tự ý logout nick cũ hay clear cache/data TikTok.
2. **Cấm ghi đè / dồn slot Excel khi chưa xử lý trên máy thật:**
   - Bất kỳ thay đổi, thay thế nick nào trong file master Excel (`taikhoan_dat_v2_updated .xlsx`) bắt buộc phải được thực hiện trên app điện thoại trước (xác nhận nhả slot trên app rồi mới update Excel).
3. **Hỗ trợ ánh xạ Display Name trong Matcher:**
   - Trong `account_switcher.py`, matcher cần tham chiếu metadata từ master workbook để so khớp cả `display_name` tương ứng với target username trước khi kết luận nick không tồn tại trong Switcher.
