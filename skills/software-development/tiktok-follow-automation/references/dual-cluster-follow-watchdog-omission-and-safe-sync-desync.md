# Dual-Cluster Follow Watchdog Omission & Safe Sync Desync

## 1. Sự Cố Nuốt Chửng Cụm Admin Trong Báo Cáo Follow Watchdog
### Hiện Tượng
- Báo cáo cronjob `tiktok-follow-session-watchdog` (job_id: `6991768931e1`) chỉ hiển thị khối `🏢 【FARM KIBE - MÁY 1-80】`.
- Toàn bộ khối của `🏢 【FARM ADMIN - MÁY 201-280】` biến mất không dấu vết, không có bất kỳ dòng cảnh báo lỗi nào.

### Nguyên Nhân Gốc (Root Cause)
- Trong `feed_session_watchdog.py` (chạy bởi `follow_session_watchdog.py`), khi một cụm không có dữ liệu chạy trong phiên window, khối text của cụm đó được tạo như sau:
  ```text
  🏢 【FARM ADMIN - MÁY 201-280】
  • Trạng thái: Không có lượt chạy nào trong phiên (Chưa chạy / Bị skip)
  ```
- Tuy nhiên, trong hàm `format_follow_report_from_blocks()`:
  ```python
  sec = lambda kw: next((lines[i:next((j for j in range(i+1, len(lines)) if lines[j].startswith("• ")), len(lines))] for i, l in enumerate(lines) if l.startswith(f"• {kw}")), [])
  fl_s = sec("Follow chéo")
  if fl_s:
      fl_p.append("\n".join(hdr + fl_s))
  ```
  Hàm chỉ trích xuất phần bắt đầu bằng `• Follow chéo`. Do cụm không có lượt chạy nên không có dòng `• Follow chéo` (`fl_s == []`), và logic hoàn toàn thiếu nhánh `else` để bảo tồn dòng `• Trạng thái:`. Khối của cụm bị drop hoàn toàn khỏi báo cáo.
- Vấn đề tương tự xuất hiện trong `dispatch_split_reports()` khi chia báo cáo riêng cho các kênh Telegram Follow và Upload.

### Khắc Phục Chuẩn
Bổ sung nhánh `else` trích xuất `• Trạng thái:` trong cả `format_follow_report_from_blocks()` và `dispatch_split_reports()`:
```python
if fl_s:
    fl_p.append("\n".join(hdr + fl_s))
else:
    status_lines = [l for l in lines if l.startswith("• Trạng thái:")]
    if status_lines:
        fl_p.append("\n".join(hdr + status_lines))
```

---

## 2. Sự Cố Runner Skip Tick Do Mất File Safe Workbook
### Hiện Tượng
- Cụm Admin dừng chạy hoàn toàn sau Ca 1 (Row 2 lúc 08:00 sáng).
- Cả Ca 2 (Row 4) và Ca 3 (Row 6) đều không sinh bất kỳ thư mục chạy nào trong `D:/Taadaa/runtime/admin/live/YYYY-MM-DD/`.
- File state `runner_simple_state.json` của Admin dừng ở `last_window: YYYY-MM-DDT08`.

### Cơ Chế Lỗi (Silent Skip & Desync)
1. **Runner Silent Skip:**
   - Trong `tiktok_runner.py`:
     ```python
     valid_count = _count_valid_accounts_for_row(row, workbook_path=cluster_wb)
     if valid_count == 0:
         sys.stdout.write(f"tiktok_runner [{cluster_name}]: Row {row} co 0 account hop le trong {cluster_wb}, skipping current tick...\n")
         continue
     ```
   - Khi file `taikhoan_run_safe.xlsx` tại `D:\OneDrive\TaadaaData\admin` bị mất (chỉ còn các file temp atomic dạng `.taikhoan_run_safe.*.xlsx`), hàm đọc trả về 0 account. Runner lập tức `continue`, không spawn tiến trình, không ném exception, không update state.
2. **Cron Sync Thoát Sớm Do Khớp Signature:**
   - Trong `hermes_taikhoan_sync_cron.py`:
     ```python
     if (state.get("source_sig") == current[0]
             and state.get("tik_sigs") in (current[1], persisted_tik_sigs)
             and not state.get("last_error")):
         return 0  # khong doi -> silent
     ```
   - Cron sync chỉ kiểm tra xem source DAT và các file TikN có đổi kích thước/mtime hay không. Nếu source không đổi, cron thoát sớm (0) dù file safe output ở đích đã biến mất.

### Khắc Phục Chuẩn
1. **Kiểm tra liveness của file output trước khi silent exit:**
   - Bắt buộc kiểm tra `all(out.exists() for out in outputs)`. Nếu bất kỳ file safe output nào bị thiếu, bắt buộc chạy lại quá trình sync bất kể signature source có đổi hay không.
2. **Lệnh khôi phục hiện trường nhanh:**
   ```bash
   python "D:/Taadaa/tiktok-luot nuoi acc/scripts/sync-safe-workbook.py" \
       --source "D:/OneDrive/TaadaaData/admin/taikhoan_dat_v2_updated .xlsx" \
       --output "D:/OneDrive/TaadaaData/admin/taikhoan_run_safe.xlsx" \
       --tik-dir "D:/OneDrive/TaadaaData/admin"
   ```
3. **Thẩm định sau khôi phục:**
   ```bash
   python D:/Taadaa/tools/excel_preflight_validator.py --excel-dir "D:/OneDrive/TaadaaData/admin"
   ```
