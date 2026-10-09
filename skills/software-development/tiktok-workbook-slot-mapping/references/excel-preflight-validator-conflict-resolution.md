# Quy Trình Tự Động Xử Lý Xung Đột & Trùng Lặp Excel Preflight Validator (2026-09-24)

## 1. Hiện tượng & Triệu chứng
- Cronjob `taikhoan-run-safe-sync` (Job `95f8cd3f4e52`) thất bại (exit code 1) với thông báo từ `excel_preflight_validator.py`:
  `[PREFLIGHT_VALIDATOR_FAIL] Hủy sync runtime do Excel vi phạm Invariant: [FAIL] tik3.xlsx: dòng 11, cột 3, máy 10 - Trùng lặp tài khoản 'laquyen2601': xuất hiện tại tik3.xlsx (slot 3, máy 10) và Tik2.xlsx (dòng 11, slot 2, máy 10)`
  `[FAIL] tik3.xlsx: dòng 63, cột 3, máy 62 - Trùng lặp tài khoản 'tongly2009': xuất hiện tại tik3.xlsx (slot 3, máy 62) và Tik2.xlsx (dòng 63, slot 2, máy 62)`
- Validator chặn đứng việc sync sang `taikhoan_run_safe.xlsx` và runtime `hermes_cron_source_config.json` để bảo vệ farm khỏi dữ liệu rác.

---

## 2. Anti-Pattern Cần Tránh Tuyệt Đối (User Steering & Thụ Động)
- **CẤM TUYỆT ĐỐI**: Thông báo cho user "chờ anh/sếp xử lý file Excel", "cần sửa lại 1 trong 2 file Excel này để job sync an toàn chạy tiếp".
- **Hậu quả**: Khiến user cực kỳ bức xúc ("Đkm", "Sửa cho tao"). Hệ thống thuê Coordinator AI tự vận hành phone farm, không phải để bắt user mở Excel bằng tay sửa từng ô.
- **Kỷ luật**: Khi preflight validator báo lỗi duplicate/conflict, Coordinator BẮT BUỘC tự chủ động phân tích nguồn gốc, truy vết DB/live status và tự động lập Patch Contract sửa Excel.

---

## 3. Quy Trình 4 Bước Tự Động Giải Quyết Xung Đột (O(1) Trace & Fix)

### Bước 1: Trích xuất tọa độ xung đột từ Validator
Chạy validator lấy toàn bộ danh sách vi phạm:
```bash
python D:/Taadaa/tools/excel_preflight_validator.py --excel-dir D:/OneDrive/TaadaaData/kibe
```
Xác định:
- Cặp file và slot trùng (ví dụ `Tik2.xlsx` slot 2 vs `tik3.xlsx` slot 3).
- Số máy `machine` (ví dụ M10, M62) và chuỗi tài khoản trùng lặp `account_id` (`laquyen2601`, `tongly2009`).

### Bước 2: Truy vết Nguồn Sự Thật (Source of Truth Audit)
Tra cứu theo thứ tự ưu tiên:
1. **Master DAT (`taikhoan_dat_v2_updated .xlsx`)**:
   Đọc hàng tương ứng với `Máy` và `Folder Video` (`Folder = (máy - 1)*8 + slot`).
   Kiểm tra email ở cột 5 (GMAIL), ngày tạo cột 8, mật khẩu cột 3, 2FA cột 4.
2. **SQLite Database `D:/Taadaa/data/tiktok_tracker.db`**:
   Truy vấn bảng `farm_account_info`, `account_mapping`, và `snapshots`:
   ```sql
   SELECT may, tik, username FROM farm_account_info WHERE may = ?;
   SELECT may, tik, username FROM account_mapping WHERE may = ?;
   ```
3. **Session Search & Backup Workbooks**:
   Nếu ô ID trong DAT bị gõ đè, dùng `session_search(query="<email>")` hoặc dò trong các bản backup gần nhất (`.bak-*`) để tìm nick chính chủ ban đầu của email đó.
4. **Kiểm tra Live TikTok Web (Real Proof)**:
   Xác minh nick thật trên TikTok xem nick có tồn tại không:
   ```bash
   curl -s "https://www.tiktok.com/@<handle>" | grep -o '"statusCode":[0-9]*'
   ```
   - Nếu `statusCode: 0`: Nick LIVE, có follower, có video -> Nick chính chủ của slot bị gõ đè.
   - Nếu `statusCode: 10221`: Nick NOT FOUND (chưa từng reg hoặc đã đổi tên) -> Cột ID bị copy paste trùng từ slot trước -> Cần reset về `None`.

### Bước 3: Phân loại Case Xung Đột
- **Case A - Nick chính chủ bị ghi đè nhầm**:
  - *Ví dụ M10*: Folder 74 (slot 2) là `laquyen2601` (mail `laquyen26012003@gmail.com`). Folder 75 (slot 3) mail là `thachnha1103199810@gmail.com`, nick TikTok thật là `tranvantrang9810` (LIVE 100%). Do thao tác trước đó gõ nhầm `laquyen2601` đè vào slot 3.
  - *Cách sửa*: Khôi phục ô ID của Folder 75 về `tranvantrang9810` trong cả `taikhoan_dat_v2_updated .xlsx` và `tik3.xlsx`.
- **Case B - Mail chưa reg nick nhưng bị copy trùng ID**:
  - *Ví dụ M62*: Folder 490 (slot 2) là `tongly2009` (mail `tongly20092001@gmail.com`). Folder 491 (slot 3) mail là `nhatngoan050262@gmail.com` (chưa reg TikTok, web báo 10221). Ô ID slot 3 bị copy trùng `tongly2009`.
  - *Cách sửa*: Reset ô ID của Folder 491 về `None` (hoặc rỗng) trong cả DAT và `tik3.xlsx`.

### Bước 4: Sao Lưu, Thực Thi Patch & Tái Kiểm Chứng
1. **BẮT BUỘC sao lưu** các file Excel trước khi sửa bằng đuôi `.bak-<timestamp>.xlsx`.
2. Dùng Python `openpyxl` mở workbook, cập nhật đúng ô mục tiêu và `wb.save()`.
3. Chạy lại validator để nghiệm thu:
   ```bash
   python D:/Taadaa/tools/excel_preflight_validator.py --excel-dir D:/OneDrive/TaadaaData/kibe --exit-on-error
   ```
   Kết quả phải đạt `[RESULT] PASS` (0 FAIL, 0 WARN).
4. Kích hoạt cron `taikhoan-run-safe-sync` để nạp dữ liệu sạch vào runtime.
