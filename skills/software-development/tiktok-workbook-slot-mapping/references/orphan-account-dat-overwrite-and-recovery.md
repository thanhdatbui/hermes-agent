# Sự cố Nick Mồ Côi Do Bị Ghi Đè Slot Trong Master DAT (Case `ahmetsguthe17` Máy 1, 2026-09-17)

## 1. Hiện tượng & Triệu chứng
- Máy 1 (và các máy farm khác) khi chạy ca nuôi (Feed Session) báo lỗi dừng phiên:
  `manual-needed:account-switcher-missing-expected: expected account not found in account switcher`
- Mở danh sách Account Switcher trên thiết bị thật thì thấy có 7 nick, trong đó xuất hiện 1 nick lạ `ahmetsguthe17` có avatar đầy đủ.
- Tra cứu trong `taikhoan_run_safe.xlsx` và `taikhoan_dat_v2_updated .xlsx` hiện tại: hoàn toàn KHÔNG có tên `ahmetsguthe17`.
- Dễ dẫn tới kết luận nhầm: "đây là nick ký sinh" (1 nick log nhầm trên 2 máy).

## 2. Bản chất kỹ thuật (Root Cause Analysis)
1. **Nick chính chủ hợp pháp**:
   - Tra cứu các file backup lịch sử (`taikhoan_dat_v2_updated .xlsx.bak-clean-tatieu-20260901_162655.xlsx`, `gmail_clean_v2.backup...20260825.xlsx`):
   - Nick `ahmetsguthe17` được tạo từ email `ahmetsguthe@hotmail.com` (pass mail `Emma2004wOjd`, pass TikTok `3Za$Mz#GZ7Sl`) vào ngày 22/08/2026.
   - Nick được reg trực tiếp trên Máy 1 (`9885b64957334f5a46`), lưu tại Slot 6, có cột Avatar (Cột K) ghi nhận đúng Serial của Máy 1 -> đã từng chạy upload avatar thành công.
2. **Bị ghi đè khi chạy reg bù theo batch (14/09/2026)**:
   - Vào 00:00 ngày 14/09, hệ thống kích hoạt reg bù cho Row 8 (`ensure_row_accounts.py`).
   - Do Máy 1 trước đó có đợt dồn/shift slot và cấu trúc slot trống chưa được dọn dẹp triệt để, tool nạp kết quả đã ghi đè các tài khoản mới vào các Slot 6, 7, 8:
     + Slot 6: Ghi đè thành `nhimnhim1565` (thay thế và xóa mất `ahmetsguthe17`).
     + Slot 7: Ghi đè thành `beheo5746`.
     + Slot 8: Ghi đè thành `stutectzyes`.
3. **Sự lệch pha giữa CSDL Excel và Thiết bị thật**:
   - Master DAT bị mất thông tin của `ahmetsguthe17`.
   - Tuy nhiên, app TikTok trên Máy 1 không có lệnh đăng xuất tài khoản cũ này, nên `ahmetsguthe17` vẫn tiếp tục tồn tại trên app TikTok, chiếm 1 trong 8 slot tối đa của thiết bị.
   - Khi ca nuôi chạy cần tìm nick mới hoặc auto-login reconcile nạp nick còn thiếu, máy chạm trần 8 nick hoặc kẹt giao diện Switcher, dẫn đến fail-closed.

## 3. Quy tắc điều tra & khắc phục chuẩn (Playbook)
1. **Kiểm tra file Backup trước khi kết luận**:
   - Khi phát hiện nick có trên máy nhưng không có trong master DAT hiện tại, **BẮT BUỘC quét qua các bản backup Excel (`*.bak*.xlsx`) trong `D:\OneDrive\TaadaaData\kibe\`** để tìm lịch sử tạo nick và thông tin đăng nhập gốc (ID, Pass, Mail).
2. **Phân biệt rạch ròi Nick Ký Sinh vs Nick Mồ Côi**:
   - *Nick Ký Sinh*: Thuộc quyền quản lý của Máy A nhưng xuất hiện trên Máy B -> BẮT BUỘC logout khỏi Máy B.
   - *Nick Mồ Côi*: Vốn thuộc Máy A, từng có thông tin đầy đủ và up avatar trên Máy A nhưng bị ghi đè mất khỏi Excel -> Cần phục hồi thông tin nếu còn slot nuôi, hoặc logout dọn dẹp nhả slot nếu máy đã đủ 8 nick mới.
3. **Quy tắc nạp Reg Bù (Bảo toàn Slot cũ)**:
   - Khi chạy script nạp kết quả reg bù (`ensure_row_accounts.py` / `apply_deferred_tracking_results.py`), **TUYỆT ĐỐI CẤM ghi đè lên slot đã có username hợp lệ**.
   - Phải tính đúng dòng vật lý: `target_row = 1 + (m - 1) * 8 + slot`. Nếu slot chỉ định đã có ID khác, phải cảnh báo xung đột (Conflict) thay vì âm thầm ghi đè làm mất nick.
