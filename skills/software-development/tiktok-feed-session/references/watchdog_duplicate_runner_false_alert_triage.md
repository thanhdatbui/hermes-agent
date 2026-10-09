# CẨM NANG TRIAGE MASS FAIL ALERT DO DUPLICATE RUNNER & DEVICE LOCK COLLISION

## 1. Hiện tượng nhận dạng (False Alert Signatures)
Khi watchdog gửi Farm Alert báo lỗi hàng loạt (mass-fail >10 máy hoặc 100% farm, ví dụ `Fail (78): M1..M80`):
- Thống kê lướt feed: `0 video, 0 tim, 0 follow`.
- Thời lượng chạy của run artifact cực ngắn (thường chỉ 5-15 giây).
- Trong `summary.txt` tại root của run có dòng: `skipped-device-locked: <số máy lớn>`.

## 2. Bản chất kỹ thuật (Root Cause)
- **Race Condition / Duplicate Trigger:** Cron hoặc scheduler kích hoạt 2 tiến trình runner trong cùng một Ca/Phiên cách nhau 1-2 phút.
- **Runner 1 (Chính):** Đã acquire toàn bộ lock thiết bị (`~/.codex/device-locks/machine_*.lock.json`) và đang chạy thật trên các máy.
- **Runner 2 (Lặp):** Khởi động sau, gặp lock đang bị chiếm giữ bởi PID của Runner 1 -> Ghi nhận `skipped-device-locked` toàn bộ máy và kết thúc ngay lập tức.
- **Watchdog ngộ nhận:** Watchdog quét artifact thấy folder của Runner 2 đã có `summary.txt` (kết thúc sớm) nên phân tích và phát alert báo động giả, đồng thời đánh dấu session là `reported`. Trong khi đó, Runner 1 vẫn đang chạy thành công ngầm.

## 3. Quy trình Triage O(1) của Coordinator (CẤM quét đĩa diện rộng)
1. **Kiểm tra tiến trình runner còn sống:**
   ```bash
   tasklist | grep python
   ```
   Xem có tiến trình Python nào đang chiếm giữ CPU/RAM tương ứng với `run_tiktok.py --mode multi-machine-feed-session`.

2. **Kiểm tra log.jsonl của run folder bị báo fail:**
   Đọc 10 dòng đầu của `log.jsonl`:
   Nếu thấy lỗi dạng:
   `device lock active: path=...machine_X.lock.json pid=<PID_RUNNER_1> ... command=run_tiktok.py`
   -> **XÁC NHẬN NGAY: Đây là False Alert do Device Lock Collision.**

3. **Kiểm tra run folder đồng hành trong ngày:**
   ```bash
   ls -lt "D:/Taadaa/runtime/kibe/live/<YYYY-MM-DD>" | head -n 10
   ```
   Tìm run folder có cùng row index được tạo cùng khung giờ (ví dụ `row-6-200406` bên cạnh `row-6-200025`).

4. **Đếm tiến độ thực tế của Run thật:**
   Đọc nhanh `log.jsonl` của folder thật để kiểm tra số máy `success`:
   ```bash
   python -c '
   import json
   with open(r"<PATH_LOG_JSONL>", "r", encoding="utf-8") as f:
       lines = [json.loads(l) for l in f if l.strip()]
   succ = [l for l in lines if l.get("result") == "success" and l.get("action") == "feed-session-smoke"]
   print(f"Success machines: {len(succ)}")
   '
   ```

## 4. Hành động phục hồi (Recovery Actions)
1. **Xác thực bằng chứng (GATE 6):** Lấy screenshot O(1) từ máy đang chạy thành công trong artifacts đính kèm vào báo cáo `MEDIA:<path_screen.png>`.
2. **Kiểm tra máy kẹt teardown:** Nếu runner chính chạy quá lâu (ví dụ >35 phút), kiểm tra child process của runner xem có lệnh `adb shell` vào máy nào bị treo kết nối hay không.
3. **Reset State Watchdog:** Sau khi run thật hoàn tất:
   - Mở `D:\Taadaa\runtime\kibe\cron-state\feed_session_reported.json`.
   - Xóa session key bị báo cáo ảo (ví dụ `YYYY-MM-DD_ca3_phien2`) để watchdog quét lại và phát báo cáo số liệu thật chuẩn xác.
