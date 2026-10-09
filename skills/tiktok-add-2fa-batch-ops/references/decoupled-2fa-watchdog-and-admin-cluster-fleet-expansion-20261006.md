# Decoupled 2FA Watchdogs, Multi-Cluster (Kibe + Admin) Fleet Expansion & Reporting Architecture (06/10/2026)

## 1. Bối cảnh & Yêu cầu Operator
- Operator bức xúc khi phát hiện: *"kẹt phase reg gmail thì kệ con mẹ nó chứ mắc gì k chạy phase add 2fa đéo hiểu"*, *"tao cần thiết kế phase add 2fa nhiều hơn để phủ all nick kiểm tra lại các cron hiện tại r thiết kế cho tao"*, *"add 2fa cả farm admin chứ"*, *"vẫn lưu dữ liệu đúng theo file dữ liệu mỗi dàn farm chứ"*.
- Toàn farm có 639 nick Kibe (185 nick thiếu 2FA) và 614 nick Admin (100% chưa có 2FA).
- Cần mở rộng hệ thống 2FA phủ cả cụm Admin (Máy 201–280), đảm bảo an toàn dữ liệu tách biệt theo file Excel từng dàn và báo cáo Telegram minh bạch.

---

## 2. Bẫy Khóa Cứng Lane & Coupling Sai Trong Chuỗi Sau Ca Trưa
- **Hiện tượng cũ:** Trong `post_noon_chain_watchdog.py`, argparse khai báo `--lane` có `default="gmail"`. Khi caller truyền `--lane all`, code cũ in cảnh báo *"backward-compatible chỉ chạy lane Gmail"* và bỏ qua Phase 2 Add 2FA.
- **Hậu quả:** Khi Phase 1 (Reg Gmail) fail hoặc bị treo, Phase 2 (Add 2FA TikTok) không bao giờ được kích hoạt.
- **Khắc phục chuẩn (Decoupled Flow):**
  1. Đổi `default="all"` cho `--lane`.
  2. Bóc tách độc lập hoàn toàn giữa 2 Phase:
     ```python
     if args.lane in ("gmail", "all"):
         g_code, g_out = run_gmail_batch(dry_run=args.dry_run)
     if args.lane in ("tiktok", "all"):
         t2fa_code, t2fa_out = run_tiktok_2fa_batch(dry_run=args.dry_run)
     ```
  3. Bất kể Reg Gmail kết thúc với exit code nào, Phase Add 2FA TikTok bắt buộc vẫn chạy nếu có mục tiêu hợp lệ.

---

## 3. Mở Rộng Dải Máy Admin (201–280) Trong Core Runner (`run_batch_live_2fa.py`)
- **Bẫy Hardcode Giới Hạn Machine 80:**
  - Trong `_machine(value)`: code cũ quy định `return str(number) if 1 <= number <= 80 else ""`.
  - Khi nạp workbook Admin (`Máy: 201..280`), hàm lọc toàn bộ thành rỗng và trả về `{"status": "validated", "reason": "NO_ELIGIBLE_TARGETS"}`.
- **Khắc phục & Boundary Tests:**
  - Nâng giới hạn hợp lệ: `return str(number) if 1 <= number <= 999 else ""`.
  - Bổ sung unit test biên trong `test_run_batch_live_2fa.py`:
    - Chấp nhận: `1, 80, 81, 201, 280, 999`.
    - Từ chối: `0, 1000, "nonnumeric", None`.
  - Đồng bộ file runner sang máy Admin (`admin-farm`) qua SSH/SCP.

---

## 4. Tách Biệt Tuyệt Đối File Dữ Liệu Từng Cụm Farm (Single-Writer Guard)
- **Quy tắc Workbook Mapping:**
  - Cụm Kibe (Máy 1–80): `D:\OneDrive\TaadaaData\kibe\taikhoan_dat_v2_updated .xlsx`
  - Cụm Admin (Máy 201–280): `D:\OneDrive\TaadaaData\admin\taikhoan_dat_v2_updated .xlsx`
- **Thực thi phân lập:**
  - Kibe: Chạy cục bộ bằng Python runtime `D:\Taadaa\python-envs\automation\Scripts\python.exe` với `TAADAA_HOST_CONFIG="D:\Taadaa\machine-config\kibe.yaml"`.
  - Admin: Điều phối từ Kibe qua `ssh admin-farm` gọi Powershell thực thi tại remote cwd `D:/Taadaa/tiktok-add-bao-mat-f2a` trỏ đích danh file workbook Admin.
  - Tuyệt đối không trỏ chung file, bảo vệ toàn vẹn single-writer lock và auto-backup `.backup.xlsx` của từng cụm.

---

## 5. Chu Kỳ 2 Khung Giờ Vàng Phủ 2FA & Báo Cáo Phân Tách
1. **Khung Sau Ca Trưa (14:30 – 18:30):** Cron `post-noon-chain-watchdog` chạy mỗi 5 phút (`*/5 14..18 * * *`).
2. **Khung Đêm Muộn (01:00 – 02:50):** Cron mới `night-tiktok-2fa-watchdog` chạy mỗi 10 phút (`*/10 1,2 * * *`).
3. **Báo Cáo Phân Tách Chi Tiết:**
   - Watchdog phân tách stdout thành 2 khối `=== CLUSTER KIBE ===` và `=== CLUSTER ADMIN ===`.
   - Báo cáo gửi Telegram bóc tách rõ ràng:
     ```text
     [BÁO CÁO 2FA TIKTOK]
     • Farm Kibe (Máy 1-80): Hoàn tất X máy | Bỏ qua Y | Lỗi Z
     • Farm Admin (Máy 201-280): Hoàn tất A máy | Bỏ qua B | Lỗi C
     ```
4. **Giám Sát Tỷ Lệ Phủ Hàng Ngày:**
   - Bổ sung thống kê 2FA Kibe & Admin vào `tiktok_account_tracker.py` chạy lúc 07:00 sáng trong cron `daily-tiktok-farm-tracker`.
