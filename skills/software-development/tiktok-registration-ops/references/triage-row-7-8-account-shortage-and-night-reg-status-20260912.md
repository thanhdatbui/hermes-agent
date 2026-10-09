# Triage: Thiếu Tài Khoản Row 7 / Row 8 & Trạng Thái Reg Tự Động Ban Đêm

## 1. Bản chất kiến trúc & Phân bổ Slot 7 và 8
- Toàn farm chuẩn hóa tối đa **8 acc/máy** (tương ứng Row 1 đến Row 8).
- **Slot 7 (Row 7)**: Nuôi vào Ca 4 các ngày lẻ (00:00).
- **Slot 8 (Row 8)**: Nuôi vào Ca 4 các ngày chẵn (00:00).
- **Quy hoạch phôi trắng (Incubator - Feed only, Cấm upload)**: Slot 7 & 8 nuôi tích trust 48–72h trước khi luân chuyển, không render/upload video tại Kibe.

## 2. Kiểm tra nhanh trạng thái thiếu tài khoản (O(1) Checklist)
Khi user hỏi "Ca chạy row 7/8 hôm nay không có tài khoản, có tự chạy reg chưa hay lỗi?":
1. **Kiểm tra phân bố tài khoản hiện tại**:
   - Đọc `D:\OneDrive\TaadaaData\kibe\taikhoan_run_safe.xlsx` (sheet `Accounts`).
   - Đếm số máy có `ID` hợp lệ ở index 6 (Row 7) và index 7 (Row 8).
   - So sánh với `D:\OneDrive\TaadaaData\kibe\taikhoan_dat_v2_updated .xlsx` để nắm số lượng nick thực tế.
2. **Kiểm tra đợt chạy ban đêm**:
   - Mở thư mục run mới nhất: `D:\Taadaa\runtime\kibe\artifacts\runs\social-batch-all\YYYYMMDD-HHMMSS\all_results.json`.
   - Đọc log `D:\Taadaa\Tiktok_Reg\social_reg_log.txt` (dùng tail, đọc byte cuối, **CẤM** load toàn bộ file > 10MB vào memory).
   - Đối soát số lượng máy SUCCESS vs FAILED.
3. **Kiểm tra target sẵn sàng trong kho**:
   - Chạy O(1): `python D:/Taadaa/Tiktok_Reg/_detect_clean.py` để xem còn bao nhiêu targets sạch trong `gmail_clean_v2.xlsx`.

## 3. Các bẫy thất bại thường gặp khi Reg ban đêm & Phân loại
1. **Proxy rớt mạng (`Khong co ket noi Internet` / `fail_*_network_error`):**
   - Biểu hiện: XML status bar hiện `Khong co internet`, script timeout khi load trang hoặc gửi request.
   - Bản chất: Hạ tầng mạng di động / proxy box 4G chập chờn ban đêm. Không phải bug logic code.
2. **TikTok Rate Limit (`'different method' error banner`):**
   - Biểu hiện: `detected: TikTok rate-limit / 'different method' error banner` ngay sau khi nhập email hoặc bấm Tiếp tục.
   - Bản chất: TikTok phát hiện IP proxy có tần suất reg dày đặc hoặc IP bị đánh cờ spam, ép đổi phương thức khác.
3. **Gmail / Hotmail OTP không về:**
   - Biểu hiện: `quachtieu... khong co trong account list` hoặc `reason=target_account_not_verified (Google Account vẫn LIVE, nhưng TikTok không phát OTP)`.
   - Xử lý: Kiểm tra health của mail; nếu mail sống nhưng TikTok không gửi mã thì cần ngâm cooldown máy/IP trước khi thử lại.

## 4. Hành vi tự bảo vệ an toàn của hệ thống (Safe-Skip)
- Khi đến ca nuôi (Row 7 hoặc Row 8), máy nào chưa có nick trong `taikhoan_run_safe.xlsx` sẽ tự động **skip an toàn** (`account row N is empty, skipping`).
- Tuyệt đối không dừng cả batch hay crash chuỗi nuôi của toàn farm.
