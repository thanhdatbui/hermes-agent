# Fleet Bulkhead Isolation & Watchdog Multi-Cluster Visibility

## 1. Context & Incident
Vào ngày 2026-10-29, Farm Kibe (M01-M80) biến mất hoàn toàn khỏi báo cáo Telegram của Ca 1 và Ca 2. Toàn bộ farm không chạy một máy nào, trong khi báo cáo chỉ hiển thị cụm Farm Admin (M201-M280).

Hai lỗi nghiêm trọng liên hoàn được phát hiện:
1. **Bẫy sập chùm (Blanket Crash) do thiếu Bulkhead trong Host Guard:**
   File Excel nguồn `taikhoan_dat_v2_updated .xlsx` vô tình bị dán nhầm 1 dòng chứa Máy 261 (thuộc Farm Admin). Khi cron sync sang `taikhoan_run_safe.xlsx`, `tiktok_runner.py` truyền danh sách `--machines 1,2,...,80,261` sang `run_tiktok.py`.
   Trong `run_tiktok.py`:
   ```python
   # Anti-pattern: 1 máy lạ làm sập cả 80 máy
   for _part in str(args.machines).split(","):
       if _m.isdigit():
           taadaa_host.assert_machine_in_range(int(_m), _host)  # Crash toàn bộ process!
   ```
   Do dải Kibe là `[1, 80]`, gặp máy 261 thì `taadaa_host` văng `HostConfigError`, khiến toàn bộ batch 80 máy chết ngay trước khi khởi động bất kỳ tiến trình nào.

2. **Nuốt chửng cụm trong Watchdog Session Loop (Watchdog Blindspot):**
   Trong `feed_session_watchdog.py`:
   ```python
   # Anti-pattern: Folder date chưa tồn tại -> bỏ qua luôn cụm khỏi báo cáo
   c_live = cluster.get("live_root")
   date_live = os.path.join(c_live, target_date)
   if not os.path.exists(date_live):
       continue  # <-- LỖI: Cụm Kibe bị nuốt mất không để lại dấu vết
   ```
   Vì Kibe crash từ preflight nên folder `live/YYYY-MM-DD` chưa được tạo. Watchdog gặp `continue` đã âm thầm bỏ qua Kibe, khiến Operator lầm tưởng Kibe đã bị xóa hoặc không được giám sát.

---

## 2. Invariants & Implementation Patterns

### Invariant 1: Fleet Host Guard Bulkhead (Anti-Blanket Crash)
Khi nhận danh sách `--machines`, host guard phải lọc độc lập từng máy. Máy ngoài phạm vi host chỉ được in `HOST_WARNING` và bị loại bỏ; các máy hợp lệ còn lại tiếp tục được chạy:
```python
valid_machines = []
for _part in str(args.machines).split(","):
    _m = _part.strip()
    if _m.isdigit():
        m_int = int(_m)
        try:
            taadaa_host.assert_machine_in_range(m_int, _host)
            valid_machines.append(str(m_int))
        except taadaa_host.HostConfigError as _herr:
            print(f"[HOST_WARNING] Bỏ qua machine {m_int} không thuộc host: {_herr}", file=sys.stderr)
if not valid_machines:
    print("CONFIG_ERROR: Không còn machine nào thuộc host hợp lệ sau khi lọc", file=sys.stderr)
    return ExitStatus.CONFIG_ERROR.code
args.machines = ",".join(valid_machines)
```

### Invariant 2: Multi-Cluster Session Fallback (Zero Silent Drops)
Trong mọi vòng lặp duyệt cluster của Watchdog, nếu thư mục ngày của cluster chưa tồn tại, bắt buộc gán `runs = []` để cluster rơi xuống nhánh hiển thị trạng thái `Chưa chạy / Bị skip`, cấm `continue`:
```python
c_live = cluster.get("live_root")
if not c_live or not os.path.exists(c_live):
    continue
date_live = os.path.join(c_live, target_date)
runs = sorted(os.listdir(date_live)) if os.path.exists(date_live) else []
# Tiếp tục xử lý: runs rỗng -> hiển thị block "Chưa chạy / Bị skip"
```

---

## 3. Verification Protocol
1. **Unit Test Bulkhead:** Kiểm tra cả 2 trường hợp:
   - Danh sách hỗn hợp `1,2,261`: máy 261 bị loại, máy 1,2 chạy thành công (exit 0).
   - Danh sách thuần máy lạ `261,200`: trả về CONFIG_ERROR (exit 3) một cách sạch sẽ.
2. **Unit Test Watchdog:** Thư mục `live/YYYY-MM-DD` không tồn tại không được gây exception, `runs` trả về `[]` an toàn.
