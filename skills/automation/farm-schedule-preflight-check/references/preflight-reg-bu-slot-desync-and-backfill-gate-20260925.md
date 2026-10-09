# Preflight Reg Bù Slot Desync & Backfill Gate (2026-09-25)

## 1. Hiện tượng & Bối cảnh Sự cố (Incident Case Study)
- **Cảnh báo từ Farm Alert:**
  ```text
  📋 [PREFLIGHT REG BÙ ROW 5]
  • Tổng máy thiếu: 1 (Đã chạy: 1, Cooldown: 0)
  ❌ Thất bại (1):
    - Máy 28: Máy đã đủ 8 acc (Lệch Excel - Cần kiểm tra backfill)
  • Thời gian: 18:04:51 25/09/2026
  • Hiện trường: D:/Taadaa/Tiktok_Reg/screenshots_social/
  ```
- **Hiện trường thực tế khi kiểm tra O(1):**
  - Thiết bị: Máy 28 (`ce031603a3dc2d2804`), focus Launcher, không có lock file active.
  - Workbook `taikhoan_dat_v2_updated .xlsx`: Sheet `Tài Khoản`, dòng 223 (Folder Video 221 - tương ứng Slot 5 của Máy 28) hoàn toàn rỗng ở các cột ID, PASS, GMAIL.
  - Safe Workbook `taikhoan_run_safe_combined.xlsx`: Dòng 223 chỉ có 7 tài khoản cho Máy 28 (bỏ qua slot 5).
  - SQLite Source of Truth (`D:/Taadaa/data/tiktok_tracker.db`):
    - `farm_account_info`: Máy 28 có đầy đủ 8 tài khoản (`tik = 1..8`), trong đó `tik = 5` là nick `@anggiathinh2905` (`updated_at: 2026-09-22 10:40:46`, `host_id: kibe`).
    - `snapshots`: Nick `@anggiathinh2905` có nhiều snapshot trạng thái `LIVE`, gần nhất là ngày `2026-09-25 07:02:58` (đang chạy lướt feed ổn định).
    - `account_mapping`: Chỉ có 7 nick, thiếu bản ghi của `@anggiathinh2905`.

## 2. Bản chất Cơ chế Lỗi (Root Cause)
1. **Lệch Dữ Liệu Hai Chiều (Workbook ↔ SQLite/Device):**
   - Khi preflight quét danh sách máy thiếu theo ca (`ensure_row_accounts.py <row>`), script đọc workbook Excel để tìm các dòng có ô ID/Email rỗng. Do dòng Folder 221 của M28 bị trống, script kết luận Máy 28 đang thiếu nick Row 5 và đưa vào diện cần reg bù.
   - Nhưng khi tiến trình can thiệp thiết bị hoặc đọc Account Switcher thì phát hiện thiết bị đã chứa đủ 8 nick (`MACHINE_FULL_8_ACCOUNTS`).
2. **Nguy cơ Vi Phạm Tài Sản Doanh Nghiệp (FARM-ASSET-001):**
   - Nếu Agent tự suy diễn "máy thừa nick" hoặc "có nick lạ trên máy" rồi tự ý logout `@anggiathinh2905` để dọn slot reg bù Row 5 $\rightarrow$ Đây là hành vi phá hủy tài sản nghiêm trọng, làm mất session của một tài khoản đang hoạt động bình thường.
   - Ngược lại, nếu cố reg bù đè lên máy đầy acc $\rightarrow$ Sẽ làm tràn bộ nhớ, crash app hoặc văng nick cũ.

## 3. Quy trình Triage O(1) & Xử Lý Chuẩn (Protocol)
Khi nhận cảnh báo `[PREFLIGHT REG BÙ ROW N] Máy đã đủ 8 acc (Lệch Excel - Cần kiểm tra backfill)`:

1. **Bước 1: Không chạm thiết bị, không chạy reg bù, không logout (Freeze):**
   - Không được phép dispatch worker reg hoặc logout.
   - Tra cứu nhanh trạng thái máy qua `python D:/Taadaa/tools/inspect_machine.py <N>`.

2. **Bước 2: Truy vấn SQLite Source of Truth (`D:/Taadaa/data/tiktok_tracker.db`):**
   - Chạy query O(1) kiểm tra slot N của máy:
     ```sql
     SELECT username, may, tik, updated_at, host_id 
     FROM farm_account_info 
     WHERE may = ? AND tik = ?;
     ```
   - Kiểm tra bảng `snapshots` để xác nhận trạng thái tài khoản:
     ```sql
     SELECT timestamp, username, status, avatar_url 
     FROM snapshots 
     WHERE username = ? 
     ORDER BY id DESC LIMIT 5;
     ```
   - Nếu nick tồn tại và có snapshot `LIVE` $\rightarrow$ Khẳng định 100% tài khoản chính chủ của Farm, thuộc quyền sở hữu của máy đó.

3. **Bước 3: Rà soát vị trí thiếu trên các Workbook (Master Tracking & Tik1..Tik8):**
   - Mở `D:/OneDrive/TaadaaData/kibe/taikhoan_dat_v2_updated .xlsx` tại dòng ứng với Folder Video `(may - 1) * 8 + slot`. Xác nhận tình trạng rỗng.
   - Mở file `Tik<slot>.xlsx` tương ứng (ví dụ Slot 5 -> `Tik5.xlsx` tại dòng `Máy + 1`) để kiểm tra cột Username (`ID`).
   - Mở `D:/OneDrive/TaadaaData/taikhoan_run_safe_combined.xlsx` kiểm tra danh sách nick hiện tại của máy.
   - Kiểm tra `account_mapping` trong SQLite để xác định xem có bị thiếu record mapping hay không.

4. **Bước 4: Gate Backfill An Toàn (CẤM BỊA PASSWORD):**
   - Để khôi phục hàng trong Excel, BẮT BUỘC phải truy vết đủ: `ID`, `PASS`, `GMAIL`, `PASS MAIL` (hoặc cờ `--otp-only` nếu reg passwordless).
   - Truy vết trong các file backup: `taikhoan_dat_v2_updated .xlsx.bak*`, `gmail_clean_v2.xlsx`, hoặc artifact log reg cũ.
   - **NẾU THIẾU NGUỒN EMAIL/PASS:**
     - DỪNG LẠI NGAY ở trạng thái: `FINAL_BLOCKED — Thiếu nguồn email/PASS để backfill an toàn`.
     - Báo cáo chi tiết cho User kèm username, số máy, slot để User cung cấp thông tin hoặc chỉ đạo.
     - TUYỆT ĐỐI CẤM tự ý bịa chuỗi password giả hoặc điền dữ liệu rác vào workbook chính.
   - **NẾU ĐẦY ĐỦ THÔNG TIN:**
     - Soạn Patch Contract đóng, dispatch worker ghi atomic vào `taikhoan_dat_v2_updated .xlsx` và `taikhoan_run_safe_combined.xlsx`.
     - Cập nhật record vào bảng `account_mapping` trong SQLite:
       ```sql
       INSERT OR REPLACE INTO account_mapping (username, may, tik) VALUES (?, ?, ?);
       ```
     - Chạy lại kiểm tra preflight để xác nhận Máy N không còn nằm trong danh sách thiếu.
