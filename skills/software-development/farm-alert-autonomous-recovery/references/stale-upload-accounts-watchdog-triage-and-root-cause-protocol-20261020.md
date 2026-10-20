# Stale Upload Accounts Watchdog Triage & Root Cause Protocol (2026-10-20)

## 1. Bối cảnh & Bản chất Báo cáo
Watchdog `daily-stale-upload-accounts-watchdog` (chạy 07:15 sáng hàng ngày) gọi:
```bash
python D:/Taadaa/tools/audit_stale_upload_accounts.py --days 7 --critical-days 14 --json
```
- **Exit Code 1 là Intentional**: `audit_stale_upload_accounts.py` trả về `exit_code: 1` khi có bất kỳ drift issue hoặc `critical_stale_count > 0`. Đây là thiết kế alert của CLI, không phải crash/exception của script. Cron wrapper `cron_stale_upload_watchdog.py` hứng stdout và parse JSON an toàn.
- **Không đụng vào lifecycle của Cron**: Khi nhận bản tin báo cáo, CẤM gọi `cronjob(action='remove')` hoặc `pause`. Đây là bản tin báo cáo định kỳ cần giải trình và phân loại kỹ thuật.

---

## 2. Quy trình 5 Tầng Phân Loại Hiện Trường (Triage Hierarchy)

### Tầng 1: Data Integrity Gate (Master DAT vs Tik1..Tik8)
- Kiểm tra tính toàn vẹn workbook: Master DAT (`taikhoan_dat_v2_updated .xlsx`) và các file `Tik1.xlsx` .. `Tik8.xlsx`.
- Xác nhận không có hiện tượng mất ID (`MISSING_ID`), lỗi header (`Folder Video (Render Dich)`), hoặc silent drop.

### Tầng 2: Phân Tách Cụm (Admin vs Kibe)
- Truy vấn SQLite Single Source of Truth `D:/Taadaa/data/tiktok_tracker.db`:
```bash
python -c "import sqlite3; conn = sqlite3.connect('D:/Taadaa/data/tiktok_tracker.db'); c = conn.cursor(); c.execute('SELECT host_id, count(*) FROM farm_account_info GROUP BY host_id'); print(c.fetchall())"
```
*(Lưu ý cú pháp: luôn viết lệnh `python -c` trên 1 dòng đơn để tránh lỗi parsing đường dẫn trong guard).*
- **Cụm Admin (M201 - M280)**: Thường chiếm phần lớn danh sách stale (60-80%) do cụm Admin giữ nhịp upload để dồn tài nguyên render/download video nguồn. Đây là trạng thái có chủ đích theo kế hoạch vận hành.

### Tầng 3: Bóc Tách Phần Cứng Cụm Kibe (Hardware & Transport Check)
- Dùng `python D:/Taadaa/tools/inspect_machine.py <N>` kiểm tra O(1) các máy có nhiều nick bị kẹt lâu nhất:
  - Máy offline (`device not found`): Cáp USB lỏng, mất nguồn hub, sập nguồn máy (ví dụ M10, M30).
  - Máy socket timeout (>30s): Treo ADB transport hoặc crash daemon ADB (ví dụ M74).
  - Khắc phục: Yêu cầu xử lý vật lý cắm lại cáp hoặc reset ADB transport.

### Tầng 4: Phân Loại Vòng Đời Theo Slot (Slot Lifecycle)
- **Slot 7 & Slot 8**: Đa số là nick mới hoàn thành reg hoặc acc dự phòng, đang trong giai đoạn dưỡng warmup (0 follow / tương tác nhẹ), chưa đến chu kỳ được gán lịch upload đều đặn.

### Tầng 5: Kiểm Tra Tồn Kho Media (Media Source Stock)
- Với các nick Slot 1–2 trên máy đang online bình thường:
  - Tra cứu Folder Video: `Folder = (Machine - 1) * 8 + Slot`.
  - Kiểm tra tồn kho tại `D:/TIKTOK-videonuoinick/<Folder>`:
    - Nếu folder còn nhiều video `.mp4` (ví dụ 45 video): Không phải lỗi thiếu clip, mà do nhịp điều phối nuôi 4 ngày (N1 lẻ, N2 chẵn, N3 dưỡng, N4 dưỡng) chưa xoay tới ca upload của slot đó.
    - Nếu folder rỗng hoặc hết clip: Báo động cần bổ sung video render mới.
