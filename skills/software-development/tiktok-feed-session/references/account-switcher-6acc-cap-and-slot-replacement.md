# Account Switcher 6-Account Cap & Slot Replacement Triage

## Hiện tượng
- Runner dừng với lỗi: `manual-needed:account-switcher-missing-expected: expected account not found in account switcher`
- Chi tiết: Phiên nuôi (feed/upload/follow) ca N kỳ vọng tài khoản $A$ (ví dụ `janayerton71` ở Tik5 / Ca 3), nhưng trong Account Switcher của máy không tìm thấy tài khoản $A$.

## Root Cause
1. **TikTok 6-Account Cap**: Ứng dụng TikTok trên Android giới hạn tối đa 6 tài khoản đăng nhập đồng thời trên một thiết bị.
2. **Lệch Mapping Giữa Các Workbook**:
   - `taikhoan_dat_v2_updated .xlsx` chứa nhiều hơn 6 dòng (ví dụ 7-8 dòng cho 1 máy).
   - Máy đang đăng nhập một tài khoản thuộc dòng khác (ví dụ dòng 7 `buithudung2011`) chiếm slot thay vì tài khoản ca hiện tại (`janayerton71`).
   - Khi đó danh sách trong switcher đủ 6 tài khoản nhưng thiếu tài khoản theo lịch `taikhoan_run_safe.xlsx`.

## Quy trình Triage & Xử lý Chuẩn
1. **Kiểm tra hiện trường & đối soát 3 nguồn**:
   - Lấy XML/screenshot Account Switcher trên máy thật (`máy X`). Liệt kê chính xác 6 tài khoản đang đăng nhập.
   - Đọc 6 dòng tương ứng của `Máy X` trong `taikhoan_run_safe.xlsx`.
   - Đọc toàn bộ các dòng của `Máy X` trong `taikhoan_dat_v2_updated .xlsx` (sheet `Tài Khoản`).
2. **Xác định tài khoản thừa / tài khoản thiếu**:
   - Tài khoản thiếu: Tài khoản có trong `taikhoan_run_safe.xlsx` mà không có trên máy.
   - Tài khoản ngoài ca / thừa: Tài khoản đang đăng nhập trên máy nhưng không thuộc 6 slot của `taikhoan_run_safe.xlsx` (hoặc slot đã bị thay thế).
3. **Báo cáo Stop Gate**:
   - Báo cáo rõ danh sách 6 nick trên máy vs danh sách 6 slot trong safe workbook.
   - Đính kèm ảnh hiện trường qua `MEDIA:<path>` (dòng riêng).
   - Đề xuất 2 hướng: (a) Logout nick thừa để đăng nhập bù nick thiếu; hoặc (b) Cập nhật lại mapping Excel nếu có thay đổi ca/slot.
