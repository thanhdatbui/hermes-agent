# Chẩn Đoán Watchdog 2FA Đêm Bỏ Qua (Skip) & Bẫy Lệch Cột Workbook Admin (18/10/2026)

## 1. Hiện Tượng & Câu Hỏi Thường Gặp
- **Triệu chứng:** Báo cáo định kỳ 6H của watchdog `night-tiktok-2fa-watchdog` (job `2029d4224662`) ghi nhận số lượng `Bỏ qua` (skip) rất lớn, ví dụ:
  * Farm Kibe: Hoàn tất 21 | Bỏ qua 16 | Lỗi 35
  * Farm Admin: Hoàn tất 0 | Bỏ qua 146 | Lỗi 7
- **Câu hỏi của Operator:** "Lí do bỏ qua cả đống?" / "Chuẩn hoá chưa?"

## 2. Bản Chất Kiến Trúc Khiến Số Lượng Bỏ Qua Lớn
1. **Thiết kế Deduplication O(1) Bắt Buộc (Mỗi máy tối đa 1 nick / batch):**
   - Mỗi máy vật lý chứa từ 6 đến 8 accounts (tương ứng các slot 1–8).
   - `freeze_targets()` trong `run_batch_live_2fa.py` bắt buộc deduplicate theo máy:
     `if target.machine in machines or serial_key in serials or target.source_row in rows: continue`
   - Do đó, trong 1 batch 80 máy, tối đa chỉ có 80 accounts được đóng băng (freeze) để chạy song song. Toàn bộ các nick còn lại trên các máy này (thường từ 200–500 nick) bắt buộc phải đợi các đợt cuốn chiếu tiếp theo chứ không thể chạy dồn, tránh đụng độ màn hình và lock thiết bị.
2. **Device Lock Contention & Cooldown:**
   - Khi runner bắt đầu phân bổ thiết bị, nếu máy đang vướng `reboot_cooldown` (sau các mốc reboot 05:20, 11:20, 17:20), hoặc đang được các watchdog khác giữ lock (`feed_session_watchdog`, `clear-tiktok-cache`), runner sẽ đánh dấu `status="skipped"`, `reason="DEVICE_LOCK_UNAVAILABLE"`.
3. **Preflight Kiểm Tra An Toàn VPN / Proxy ViChanger:**
   - Runner kiểm tra `serial_is_mapped_in_workbook(proxy_mapping, target.serial)` và `require_android_vpn(...)`.
   - Nếu thiết bị chưa kết nối VPN hoặc serial chưa có trong mapping `PROXYgandienthoai.xlsx`, runner chủ động skip (`VICHANGER_VPN_NOT_CONNECTED`) để bảo vệ tài khoản khỏi lộ IP gốc.

## 3. Cạm Bẫy Lệch Cột (Column Drift) Trên File Workbook Admin & Công Thức Chuẩn Hoá
- **Hồ sơ sự cố:** Kiểm tra trực tiếp file `D:\OneDrive\TaadaaData\admin\taikhoan_dat_v2_updated .xlsx` phát hiện **171 dòng bị dời cột** chia làm 2 pattern:
  * **Pattern 1 (167 dòng):** Dữ liệu tuple `(0, 1, 2, 5, 6, 9, 10)` — Chuỗi timestamp tạo nick (dạng `2026-09-25 08:06:55`) bị ghi nhầm vào cột `device ID` (cột thứ 10). Chuỗi serial thật của máy (ví dụ `988678393355475942` hoặc `ce0516...`) bị đẩy sang cột thứ 11 (`None` header). Cột `NGÀY TẠO` (cột 9) bị trống.
  * **Pattern 2 (4 dòng):** Dữ liệu tuple `(0, 1, 2, 5, 6, 8, 9, 10)` — Cột `NGÀY TẠO` (cột 9) đã có timestamp hợp lệ, nhưng serial bị ghi lặp cả ở cột 10 lẫn cột 11.
- **Hậu quả:**
  * Runner đọc `serial = _clean(values[serial_col - 1])`, nhận chuỗi `2026-09-25...`.
  * Khi preflight gọi ADB hoặc map proxy với serial dạng ngày tháng này, bước preflight thất bại và runner đánh dấu `skipped` ngay lập tức.
- **Canonical Normalization Tool (`D:/Taadaa/tools/normalize_admin_workbook_columns.py`):**
  * Luôn tạo safety backup trước khi ghi đè (`.bak_before_normalize_<timestamp>`).
  * Nạp `PROXYgandienthoai.xlsx` của Admin làm nguồn đối soát (ground truth mapping máy ↔ serial).
  * Kiểm tra và chuẩn hoá hai pattern:
    ```python
    # Pattern 1
    if val_dev.startswith("2026-") and val_extra:
        assert val_extra.casefold() == proxy_map[m_num]
        c_created.value = c_device_id.value
        c_device_id.value = c_extra.value
        c_extra.value = None
    # Pattern 2
    elif c_created.value and str(c_created.value).startswith("2026-") and val_extra and val_dev == val_extra:
        c_extra.value = None
    ```
  * Nghiệm thu post-normalization bằng lệnh dry-run của runner:
    `python python_runner/run_batch_live_2fa.py --workbook-path "D:/OneDrive/TaadaaData/admin/taikhoan_dat_v2_updated .xlsx" --limit 10`
    Xác nhận 0 dòng bị lệch cột, serial đọc lên đúng chuẩn máy Android (`ce0...`, `988...`).

## 4. Điền Bù Serial Khuyết (Backfill 55 Rows Missing Serials) & Dọn Dead Locks
1. **Backfill 55 Serials Khuyết:**
   - Khi tạo hàng mới trước đây trên cụm Admin, có 55 dòng tài khoản để trống hoàn toàn `device ID`.
   - Tool `D:/Taadaa/tools/backfill_admin_serials.py` đối soát qua `PROXYgandienthoai.xlsx` và điền bù đủ 55/55 serials, nâng tổng số máy sẵn sàng lên trọn vẹn 80/80 máy Admin (Máy 201–280).
2. **Dọn 60 Dead-Owner Device Locks:**
   - Trên remote node `Admin-PC`, 60 file lock trong `C:\Users\Admin\.codex\device-locks` bị bỏ quên từ các PID đã tắt.
   - Chạy lệnh dọn lock chuẩn farm qua SSH:
     `python D:/Taadaa/tools/admin_ssh.py "python \"D:/Taadaa/tiktok-luot nuoi acc/scripts/reap-dead-owner-locks.py\""`
     Thu gom toàn bộ vào `device-locks-reaped/<timestamp>`, nhả toàn bộ 60 locks mồ côi.
3. **Bẫy Regex Parse Output trong Watchdog (`parse_summary_counts`):**
   - `run_batch_live_2fa.py` in `_print_results(results)` (gồm skip) rồi in tiếp `_print_results(skipped)` ở cuối.
   - Regex `table_rows = re.findall(r"^\s*(\d+)\s*\|\s*(\d+)\s*\|\s*[^|]+\|\s*(\w+)", output, re.M)` quét cả 2 bảng làm số liệu skip bị nhân đôi trong báo cáo (73 skip thực tế -> 146 báo cáo). Khi kiểm tra số liệu 6H cần đối soát lại với `freeze-targets total`.
