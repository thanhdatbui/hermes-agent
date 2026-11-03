# Quy Chuẩn Đồng Bộ Hai Chiều SQLite SSOT Farm Master & Failover Cụm Admin (2026-11-03)

## 1. Bối cảnh & Điểm Kẹt Lịch Sử (Root Cause)
- **Sự cố:** Khi runner 2FA ban đêm (`run_batch_live_2fa.py`) chạy trên cụm Admin (Máy 201–280), máy Admin chưa có file `farm_master.db` $\rightarrow$ fallback về Excel `taikhoan_dat_v2_updated .xlsx` $\rightarrow$ gây ra 69 lỗi `POST_SUCCESS_VERIFICATION_FAILED` và 43 lỗi `WorkbookError`.
- **Căn nguyên kẹt sync SSH:** Cố gắng bắn file nhị phân SQLite 1.6MB qua PowerShell SSH Base64 với chunk 2.500 ký tự (mất 869 lần gọi $\times 3\text{s} \approx 43.5$ phút) khiến subprocess timeout 300s/600s bị ngắt giữa chừng, dẫn đến file SQLite trên Admin bị `malformed` (Length 33KB).

## 2. Kiến Trúc Đồng Bộ Cục Bộ Độc Lập (Autonomous Dual-Node SSOT)
- **Đặc tính phân vùng dải máy (Zero Overlap Invariant):**
  * Kibe quản lý máy 1–80.
  * Admin quản lý máy 201–280.
  * Cả hai không chồng lấn `machine_id` $\rightarrow$ không bao giờ xung đột giao dịch khi cập nhật.
- **Biên dịch SQLite tại chỗ bằng `migrate_excel_to_sqlite.py --apply`:**
  * File Excel nguồn nằm trên OneDrive (`D:\OneDrive\TaadaaData\`) được OneDrive daemon (`PID 11296`) sync ngầm 24/7.
  * Script `migrate_excel_to_sqlite.py` trên Admin tự đọc file Excel local đã sync và biên dịch thành `D:\Taadaa\data\farm_master.db` nguyên vẹn trong 3.6 giây (1.270 nick, 1.487 mailboxes, 246 máy).
- **Task Scheduler Cục Bộ trên Admin (Failover khi Kibe hỏng):**
  * Tên Task: `Taadaa_Sync_Admin_SQLite`
  * Tần suất: Chạy mỗi 2 giờ một lần (`schtasks /create /tn 'Taadaa_Sync_Admin_SQLite' /tr '...migrate_excel_to_sqlite.py --apply' /sc HOURLY /mo 2 /f`).
  * Đảm bảo kể cả khi Kibe sập nguồn/cháy máy, máy Admin vẫn tự tạo và duy trì SQLite SSOT local để vận hành 80 máy độc lập $O(1)$.

## 3. Chống Lỗi Truy Vấn & Fail-Safe Fallback
- **Tên cột chuẩn trong `farm_master.db`:**
  * Bảng `machines`: `machine_id`, `device_serial` (CẤM nhầm sang `machine`, `serial`).
  * Bảng `tiktok_accounts`: `machine_id`, `video_slot`, `username`, `twofa_secret`, `password`.
- **Bọc Fail-safe cho Runner:**
  * Trong `run_batch_live_2fa.py`: Luôn bọc `try/except Exception` quanh `freeze_targets_from_sqlite()`. Nếu file SQLite chưa toàn vẹn, runner tự động fallback êm ái sang freeze targets từ workbook Admin mà không bị crash.
