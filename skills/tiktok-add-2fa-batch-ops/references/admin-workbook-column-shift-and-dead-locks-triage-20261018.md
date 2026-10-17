# Admin Workbook Column Shift, Blank Serials, and Dead Locks Triage (18/10/2026)

## 1. Triệu chứng Báo cáo "Bỏ qua cả đống" (Skip Count Bất Thường)
Trong báo cáo định kỳ 6H của watchdog `night-tiktok-2fa-watchdog`:
```text
Farm Admin (Máy 201-280): Hoàn tất 0 máy | Bỏ qua 146 | Lỗi 7
```
Thực tế có 3 nguyên nhân cốt lõi đan xen:
1. **Lệch cột dữ liệu ngày tạo & Serial:** Cột `device ID` bị chèn nhầm chuỗi ngày tạo (`2026-09-25...`), serial thật bị đẩy sang cột 11 (None header).
2. **Khuyết Serial trên các hàng mới tạo:** 55 dòng tài khoản chỉ có thông tin ID, Gmail nhưng cột `device ID` bị bỏ trống.
3. **Dead-owner lock tồn đọng trên node Admin:** Các tiến trình cũ đã chết nhưng file lock `.codex/device-locks` không được nhả.
4. **Bẫy nhân đôi số lượng skip trong Watchdog regex:** Runner in bảng tổng kết `_print_results(results)` (đã gồm skip) rồi in tiếp `_print_results(skipped)` ở cuối $\rightarrow$ Regex đếm mỗi dòng skip 2 lần (73 dòng skip $\rightarrow$ 146).

---

## 2. Chuẩn hoá Lệch Cột Admin `taikhoan_dat_v2_updated .xlsx`
### A. Dấu hiệu nhận biết
- Cột 9 (`NGÀY TẠO`): Bị `None`.
- Cột 10 (`device ID`): Bị chèn chuỗi ngày tháng `2026-09-25 08:06:55`.
- Cột 11 (Không header): Chứa Serial phần cứng thực tế (vd `988678393355475942` hoặc `ce041604a976172104`).
- Thống kê: Thường xảy ra sau các đợt append dữ liệu batch lớn không căn cột.

### B. Quy trình chuẩn hoá an toàn O(1)
1. **Backup file nguồn:**
   ```python
   backup_path = f"{SOURCE_PATH}.bak_before_normalize_{timestamp}"
   shutil.copy2(SOURCE_PATH, backup_path)
   ```
2. **Đối soát chéo với cấu hình phần cứng `PROXYgandienthoai.xlsx`:**
   - Đọc mapping máy $\rightarrow$ serial từ `PROXYgandienthoai.xlsx`.
   - Đối với từng dòng lệch: Kiểm tra `col11 == proxy_serial`. Chỉ khi khớp 100% mới thực hiện di chuyển:
     ```python
     if val_dev.startswith("2026-") and val_extra:
         c_created.value = c_device_id.value
         c_device_id.value = c_extra.value
         c_extra.value = None
     ```
3. **Nghiệm thu:**
   - Đảm bảo `col11 is None` trên 100% các dòng.
   - Không còn dòng nào có `device ID` bắt đầu bằng `2026-`.

---

## 3. Điền bù Serial khuyết (Backfill Missing Serials)
### A. Nguyên nhân
- Khi đăng ký nick hàng loạt trên máy farm (6-8 slot/máy), một số script chỉ ghi Serial vào slot đầu tiên, các slot sau để rỗng (`device ID` is None).
- `freeze_targets` sẽ lập tức loại bỏ dòng này (`if not serial: continue`), làm giảm độ phủ của batch 2FA.

### B. Giải pháp
- Đọc `PROXYgandienthoai.xlsx` của cụm tương ứng (hoặc tìm serial của các slot khác trên cùng máy).
- Điền bù vào cột 10 cho các dòng thiếu serial:
  ```python
  if not val_dev and m_num in proxy_map:
      c_device_id.value = proxy_map[m_num]
  ```

---

## 4. Dọn dẹp Dead-Owner Device Locks trên Remote Node (Admin-PC)
### A. Dấu hiệu
- Runner báo `DEVICE_LOCK_UNAVAILABLE` dù trên máy Admin không có tiến trình nào đang thao tác.
- Kiểm tra thư mục `C:\Users\Admin\.codex\device-locks\` thấy các file lock có timestamp từ nhiều giờ hoặc nhiều ngày trước, PID ghi trong lock không còn tồn tại trong `tasklist` / `Get-Process`.

### B. Lệnh dọn dẹp chuẩn Farm
- Chạy script dọn lock mồ côi đã chuẩn bị sẵn qua `admin_ssh.py`:
  ```bash
  python D:/Taadaa/tools/admin_ssh.py "python \"D:/Taadaa/tiktok-luot nuoi acc/scripts/reap-dead-owner-locks.py\""
  ```
- Script tự động kiểm tra `owner_process_alive()` và di chuyển các lock mồ côi vào thư mục `device-locks-reaped/<timestamp>` an toàn, nhả hoàn toàn tài nguyên cho batch mới.

---

## 5. Bẫy Regex Parse Output trong Watchdog (`parse_summary_counts`)
- Trong `run_batch_live_2fa.py`:
  ```python
  _print_results(results)  # In toàn bộ results (bao gồm success, failed, skipped)
  skipped = [item for item in results if item.status == "skipped"]
  if skipped:
      _print_results(skipped, title="Skip do device lock hoặc preflight")  # In lại danh sách skipped!
  ```
- Trong `cron_night_tiktok_2fa_watchdog.py`:
  ```python
  table_rows = re.findall(r"^\s*(\d+)\s*\|\s*(\d+)\s*\|\s*[^|]+\|\s*(\w+)", output, re.M)
  ```
- **Hệ quả:** Regex match cả 2 bảng, dẫn đến `skip_safe` bị nhân đôi chính xác (73 skip thực tế $\rightarrow$ 146 trong báo cáo).
- **Lưu ý điều phối:** Khi kiểm tra số liệu báo cáo 6H, nếu thấy số skip chẵn bất thường, cần đối soát lại số target thực tế đóng băng (`freeze-targets total`) để tránh phán đoán sai lệch.
