# Batch Feed Watchdog Triage & O(1) Inspection Pattern (2026-10-14)

## 1. Bối cảnh
Khi nhận báo cáo tổng kết phiên từ `tiktok-feed-session-watchdog` (ví dụ: Ca 2 - Phiên 1/2 với 34 máy lỗi Kibe, 49 máy lỗi Admin), Coordinator cần trích xuất hiện trường nhanh chóng, chính xác mà không kích hoạt guard bảo vệ.

## 2. Các cạm bẫy Guard & Cách khắc phục chuẩn
- **Guard Foreground Timeout:** Lệnh terminal foreground thiếu tham số `timeout` sẽ bị chặn bởi `[GUARD_FOREGROUND_TIMEOUT_MISSING]`. Luôn truyền `timeout: 30` (hoặc <= 60s).
- **Guard ADB Default-Deny:** Gọi trực tiếp `adb.exe devices` bị chặn bởi Coordinator Guard. Thay vào đó, dùng lệnh chuẩn allowlist:
  ```bash
  python D:/Taadaa/tools/inspect_machine.py
  ```
  Lệnh này tự động liệt kê thiết bị cả 2 cụm: Kibe Local và Admin Remote (`192.168.110.119:5037`).
- **Guard Anti-Disk-Scan (Cấm `os.walk` / `glob(recursive=True)`):** Tuyệt đối không dùng glob đệ quy `**/row-*` để tìm log.

## 3. Quy trình trích xuất hiện trường Batch O(1)
1. **Xác định Folder phiên chạy gần nhất:**
   - Folder live theo ngày: `D:/Taadaa/runtime/kibe/live/<YYYY-MM-DD>/`
   - Liệt kê các thư mục phiên: `os.listdir('D:/Taadaa/runtime/kibe/live/<YYYY-MM-DD>')` -> ví dụ `['row-4-120009', 'row-4-140005']`.
2. **Đọc Summary tổng thể của Batch:**
   - File: `D:/Taadaa/runtime/kibe/live/<date>/<row-session>/<run_id>/summary.txt`
   - Cho biết ngay `total_swipes_completed`, `event_counts` (blocked-proxy-vpn, manual-needed, failed, success).
3. **Tổng hợp phân bố `stop_reason` toàn bộ máy trong 1-2 giây:**
   - Duyệt qua `machines/<machine_N>/<run_id>/summary.txt`:
   ```python
   import os
   from collections import Counter
   reasons = Counter()
   machines_dir = 'D:/Taadaa/runtime/kibe/live/2026-10-14/row-4-120009/20261014-120122/machines'
   for m in os.listdir(machines_dir):
       sub = os.path.join(machines_dir, m)
       for run in os.listdir(sub):
           sm = os.path.join(sub, run, 'summary.txt')
           if os.path.exists(sm):
               with open(sm, encoding='utf-8') as f:
                   for line in f:
                       if line.startswith('stop_reason:'):
                           reasons[line.split(':', 1)[1].strip()] += 1
                           break
   for r, c in reasons.most_common():
       print(f'{c}x: {r}')
   ```
4. **Phân biệt lỗi Transient ADB vs Lỗi Script thực tế:**
   - **Transient ADB Disconnect:** Khi khởi động đồng loạt 80 máy trên Admin Remote, daemon ADB có thể quá tải làm 20-30 máy báo "device not found" hoặc "adb command timed out". Kiểm tra lại bằng `inspect_machine.py` sau khi phiên kết thúc: nếu máy ONLINE trở lại thì đây là nghẽn bus/daemon tạm thời, không phải phần cứng offline thật.
   - **Lỗi Script thực tế (cần fix):** Ví dụ `prepare-tiktok failed to focus TikTok after launch` hoặc `profile username still mismatched after switch`.
