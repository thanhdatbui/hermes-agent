# Quy tắc lưu Password và Quản lý Device Lock khi Reg TikTok (21/08/2026)

## 1. Quy tắc lưu Password TikTok vào Workbook tracking
- **Trường hợp có qua màn nhập Password:** Nhập pass thành công trên UI và ghi đúng pass đó vào cột PASS (cột 4) của file tracking (`taikhoan_dat_v2_updated .xlsx`).
- **Trường hợp KHÔNG qua màn nhập Password (Flow OTP / Email-only):** Cột PASS (cột 4) **BẮT BUỘC ĐỂ TRỐNG (`None`/blank)**. 
  - **CẤM** tự ý ghi pass ngẫu nhiên vào file tracking khi không qua màn nhập pass (để sau này người vận hành vào TikTok cài đặt pass).

## 2. Quy tắc nhả Lock và giữ Lock thiết bị
- **CHỈ NHẢ LOCK khi máy REG THÀNH CÔNG:** Máy đạt `VERIFIED_SUCCESS`, đã sync tracking an toàn và hoàn tất dọn về Home thì mới được giải phóng (release) device lock.
- **MÁY FAILED / DỪNG HIỆN TRƯỜNG BẮT BUỘC GIỮ LOCK:** Các máy lỗi phải tiếp tục giữ lock ở trạng thái `blocked` (hoặc retain lock `blocked`), **TUYỆT ĐỐI KHÔNG ĐƯỢC NHẢ LOCK** để tránh các script/cron khác can thiệp phá vỡ hiện trường trước khi được user xử lý.
