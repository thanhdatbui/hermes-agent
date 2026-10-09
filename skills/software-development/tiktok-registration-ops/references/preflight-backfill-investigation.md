# Preflight Reg Bù & MACHINE_FULL_8_ACCOUNTS Backfill Investigation Guide

## Triệu chứng & Nguyên nhân gốc
Khi preflight reg bù (`ensure_row_accounts.py <row>`) kích hoạt tự động trước ca nuôi:
- Nếu máy có dòng `ID = None` trong Excel (`taikhoan_dat_v2_updated .xlsx` / `taikhoan_run_safe.xlsx`), script sẽ coi là thiếu nick và chạy reg bù.
- Khi app TikTok mở dropdown switch account (`03_dropdown`), nếu thiết bị đã đăng nhập đủ 8 nick thật, nút "Thêm tài khoản" bị ẩn và ném lỗi:
  `RuntimeError: [04_add_account] MACHINE_FULL_8_ACCOUNTS: Thiết bị đã đạt giới hạn 8 tài khoản TikTok`
- **Nguyên nhân chính:** Nick đã được tạo thành công trong các đợt reg trước (có `tracking_result_stt*.json`) nhưng bị merge nhầm dòng vào máy khác trên Excel hoặc chưa được ghi nhận vào dòng Slot tương ứng.

## Quy trình điều tra O(1) chuẩn:
1. **Kiểm tra ảnh chụp dropdown thực tế:**
   - Tìm file chụp dropdown tại `D:/Taadaa/Tiktok_Reg/screenshots_social/<STT>_03_dropdown_*.png`.
   - Dùng WinRT OCR qua `powershell.exe -NoProfile -ExecutionPolicy Bypass -File "D:/Taadaa/do_ocr.ps1" "<path_to_png>"` để đọc danh sách 7-8 username trên màn hình.
2. **Tìm tracking artifact gốc:**
   - Quét thư mục runtime: `D:/Taadaa/runtime/kibe/artifacts/runs/social-batch-all/*/batch_*/stt_<STT>/tracking_result_*.json`.
   - Lấy thông tin tài khoản: `tiktok_id`, `email`, `password`, `mail_password`, `created_date`, `serial`.
3. **Đối soát bảng tính:**
   - Kiểm tra xem username tìm được đang nằm ở dòng nào trong `taikhoan_dat_v2_updated .xlsx`.
   - Phát hiện các trường hợp lệch dòng chéo (ví dụ nick của M61 bị ghi ở M28, nick của M76 bị ghi ở M36, nick của M3 bị ghi ở M5).
4. **Báo cáo & Xuất ảnh bằng chứng:**
   - Xuất đầy đủ ảnh `MEDIA:<path_to_dropdown.png>` cho từng máy bị lỗi.
   - Trình bày rõ: Nick thực tế trên máy, tracking record đối soát, và phương án backfill an toàn.
