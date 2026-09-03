# Chống lỗi sinh ID trùng lặp & Quy tắc dọn dẹp hàng rác Workbook (2026-08-27)

## 1. Nguyên nhân gốc gây sinh ID trùng lặp (Duplicate ID Attribution Trap)
- **Cơ chế lỗi**: Khi chạy đăng ký (`social_reg_v1.py`) trên máy đã có tài khoản TikTok đăng nhập từ trước:
  1. Nếu flow đăng ký email mới gặp lỗi (trượt menu thêm tài khoản, văng về Home feed / Profile cũ), hàm `wait_login_success` bắt các từ khóa generic ("Trang chủ", "Hồ sơ", "Đề xuất") và kết luận sai là đăng ký thành công.
  2. Bước `ensure_profile_completed_and_track` truy cập vào Profile và đọc `@handle` hiện tại (thực chất là ID của nick cũ đang mở trên máy).
  3. Script ghi nhận ID cũ đó cho hàng của email mới trong `taikhoan_dat_v2_updated .xlsx` dẫn đến hiện tượng trùng ID hàng loạt trên cùng một máy.

## 2. Bản vá phòng chống 2 tầng trong `social_reg_v1.py`
1. **Tầng Profile (`ensure_profile_completed_and_track`)**:
   - Trước khi lưu, đối chiếu `@handle` vừa đọc với toàn bộ workbook `taikhoan_dat_v2_updated .xlsx`.
   - Nếu `@handle` trùng với một email khác đã tồn tại trong kho -> Lập tức fail-closed với lỗi `BLOCKED_DUPLICATE_HANDLE_DETECTED`, chụp ảnh màn hình và dừng, cấm ghi nhận đè.
2. **Tầng ghi Workbook (`upsert_tracking_account`)**:
   - Quét toàn bộ sheet master `Tài Khoản`.
   - Nếu `tiktok_id` đã xuất hiện ở hàng khác thuộc email khác -> từ chối ghi (`DUPLICATE_TIKTOK_ID_REJECTED`).

## 3. Quy tắc dọn dẹp hàng trùng trên Workbook (`taikhoan_dat_v2_updated .xlsx`)
- Khi phát hiện các hàng mang ID bị trùng do gán nhầm (không có password thật / không có 2FA):
  - **Xóa sạch toàn bộ thông tin tài khoản**: Xóa trắng các cột từ 3 đến 9 (`ID`, `PASS`, `2FA`, `GMAIL`, `PASS MAIL`, `NGÀY SINH`, `NGÀY TẠO`).
  - **Bảo toàn cấu trúc slot vật lý**: Giữ nguyên Cột 1 (`Máy`), Cột 2 (`Folder Video`), và Cột 10 (`device ID`) để giữ chuẩn định dạng 8 hàng / máy (640 hàng toàn farm).
  - Đồng bộ ngay sang `taikhoan_run_safe.xlsx` để cron nuôi acc không nhận diện nhầm nick rác.
