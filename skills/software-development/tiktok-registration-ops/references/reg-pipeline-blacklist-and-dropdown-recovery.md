# Kỹ thuật Xử lý Lỗi [07], Lệch Excel 8 Acc & Blacklist Email Reg TikTok

## 1. Căn nguyên lỗi [07] (Email đã có tài khoản TikTok)
- **Tuyệt đối không đổ lỗi cho bên bán**: Bên bán mail không bao giờ bán mail đã reg TikTok.
- **Thực tế 100% do farm rớt dữ liệu**:
  - Máy farm đã reg thành công ở các đợt trước nhưng bị rớt dữ liệu (OneDrive lock `dwShareMode=0`, lỗi mạng hoặc `apply_results` reject duplicate UID giả).
  - Mail chưa được nạp vào sổ cái `taikhoan_dat_v2_updated .xlsx`.
  - Script `_detect_clean.py` đọc sổ cái thấy trống nên tưởng là "mail sạch chưa dùng" và bốc lại cấp cho máy -> Khi gõ mail vào TikTok, TikTok nhận diện đã có tài khoản -> Văng màn hình OTP/Login và báo lỗi `[07]`.

## 2. Quy trình phục hồi dữ liệu từ hiện trường
1. **Kiểm tra OCR dropdown switcher**:
   - Dùng WinRT OCR đọc ảnh `screenshots_social/<may>_03_dropdown_*.png` trên máy để trích xuất danh sách username thực tế đang đăng nhập trên app TikTok.
2. **Khôi phục từ Run Artifacts**:
   - Quét các file `tracking_result_*.json` trong `runtime/<cluster>/artifacts/runs/social-batch-all/` để lấy thông tin tài khoản (TikTok ID, email, pass, date, serial).
   - Nạp bù ngay vào:
     - `taikhoan_dat_v2_updated .xlsx`
     - `TikN.xlsx` (theo đúng slot)
     - Chạy `sync-safe-workbook.py` để cập nhật `taikhoan_run_safe.xlsx`.
3. **Cơ chế Blacklist Email Tập trung (`registered_emails_blacklist.json`)**:
   - Bắt buộc ghi nhận các email đã từng phát hiện có TikTok vào `data/registered_emails_blacklist.json`.
   - `_detect_clean.py`, `tiktok_target_eligibility.py` và `social_reg_v1.py` tự động check blacklist này để không bao giờ bốc lại.

## 3. Lỗi MACHINE_FULL_8_ACCOUNTS giả (Máy 7 acc báo đủ 8)
- Khi máy có 7 account, danh sách chiếm trọn bottom-sheet khiến nút "Thêm tài khoản" bị che khuất ở cạnh dưới.
- Bắt buộc cuộn `swipe(device_id, 540, 1500, 540, 800, 400)` 1-2 lần để nút lộ diện trước khi quyết định máy đã đủ 8 acc.
- Bộ đếm fallback `_acc_count` chỉ đếm text/content-desc username thực tế, loại trừ layout container rỗng để tránh false-alarm.

## 4. Tự động đồng bộ 1-chiều (Pipeline Auto-sync)
- `ensure_row_accounts.py` khi nạp kết quả reg bắt buộc chạy tuần tự:
  1. Ghi nhận sổ cái `taikhoan_dat_v2_updated .xlsx`.
  2. Đồng bộ 1-chiều sang `Tik1..Tik8.xlsx` qua `sync-tik-workbooks.py`.
  3. Đồng bộ sang `taikhoan_run_safe.xlsx` qua `sync-safe-workbook.py`.
