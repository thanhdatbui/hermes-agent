# Phân Biệt Watchdog Fail vs Skipped-Device-Locked & Cơ Chế Ca Nuôi Acc

## 1. Hiện Tượng Watchdog Báo "Fail Số Lượng Lớn" (Ví dụ: Fail 20–30 máy)

Khi nhận báo cáo Telegram từ `tiktok-feed-session-watchdog` với số lượng Fail bất thường (ví dụ: `Fail (27): M1, M3, M7...`):

- **Bản chất:** Đa số các trường hợp Fail hàng loạt theo cụm máy là do **`skipped-device-locked`** (bị kẹt lock từ tiến trình chạy trước đó hoặc 2 batch gối đầu nhau).
- **Cơ chế:** Khi một tiến trình `multi-machine-feed-session` đang chạy, nó giữ các file lock `C:\Users\Kibe\.codex\device-locks\machine_<N>.lock.json`. Nếu watchdog hoặc batch phụ kích hoạt trong thời gian này, nó sẽ bỏ qua các máy đang bị lock để tránh chạy đè (`skipped-device-locked`) và watchdog tổng hợp trạng thái này vào danh sách "Fail".
- **Hành vi tự phục hồi:** Sau khi tiến trình trước nhả lock, tick cron kế tiếp (mỗi 15 phút) sẽ tự động gắp lại các máy này và chạy bình thường (`success`).

## 2. Quy Trình Kiểm Tra Nhanh (CẤM QUÉT ĐĨA)

1. **Kiểm tra lock files hiện tại:**
   ```python
   import json, glob, psutil
   for lf in glob.glob("C:/Users/Kibe/.codex/device-locks/machine_*.lock.json"):
       with open(lf) as f: d = json.load(f)
       pid = d.get("pid")
       print(f"Machine {d.get('machine')}: PID {pid} (alive={psutil.pid_exists(pid)})")
   ```
2. **Kiểm tra event_counts trong summary gần nhất:**
   Đọc file `D:/Taadaa/runtime/kibe/live/<YYYY-MM-DD>/<row-session-dir>/<timestamp>/summary.txt` để xem `event_counts`:
   - Nếu `skipped-device-locked` chiếm đa số $\rightarrow$ Do kẹt lock tạm thời (tiến trình trước bị kill/crash nhưng automation-core fail-closed không tự xóa lock; cần chờ cron `reap-dead-owner-locks` dọn sau 1h TTL).
   - Nếu `blocked-vichanger-vpn` / `blocked-proxy-vpn` $\rightarrow$ Mất kết nối WiFi / proxy router / thiết bị offline.
   - Nếu `failed` / `manual-needed` $\rightarrow$ Phân loại O(1) qua `log.jsonl` vào 6 nhóm lỗi chuẩn:
     1. **Kẹt Device Lock:** `skipped-device-locked` từ PID cũ.
     2. **Rớt ATX:** `ATX_SESSION_UNAVAILABLE` (daemon port 7912 trên máy rớt).
     3. **ADB Timeout:** `adb command timed out` (nghẽn USB bus khi swipe/settings).
     4. **Mất Focus TikTok:** `focused package unavailable` / `focus lost`.
     5. **UI / Popup:** `unknown TikTok state` / popup mới chưa có cờ dismiss.
     6. **Lỗi cú pháp Script:** ví dụ `name 'ADBError' is not defined` (do `feed_swipe_smoke.py` bắt `except ADBError` nhưng thiếu import từ `core.adb`).

## 3. Cảnh Báo Điều Tra O(1) Chống Treo Timeout (CẤM GREP TOÀN BỘ REPO)
- **CẤM TUYỆT ĐỐI:** Chạy `grep -rn ... python_runner/` hoặc `search_files` quét đệ quy vì repo rất lớn, I/O nặng gây timeout 900s đứng session!
- **Đúng chuẩn:** Chỉ tra cứu đúng 1 file flow cụ thể (ví dụ `grep -n "ADBError" python_runner/flows/feed_swipe_smoke.py`).

## 4. Quy Luật Số Lượng Máy Theo Ca (Row 1 vs Row 3 vs Row 5)

Số máy chạy giữa các ca trong ngày không cố định 80 máy mà giảm dần theo thiết kế:
- **Ca 1 (Row 1 - Sáng):** Đầy đủ 80 máy (1–80).
- **Ca 2 (Row 3 - Chiều):** Thường ~74 máy (loại bỏ các máy không có slot Row 3).
- **Ca 3 (Row 5 - Tối):** Thường ~66 máy (chỉ các máy có nick hợp lệ ở Row 5 trong `taikhoan_run_safe.xlsx`).

$\rightarrow$ Manifest scheduler được sinh tự động vào đầu ngày (06:00) dựa trên phân bổ nick trong workbook; việc ca tối chỉ có 66 máy là hoàn toàn bình thường.
