# Chained Pipeline Watchdog & Blocked Locks TTL Handling

## 1. Ngữ cảnh bài toán
Khi triển khai các pipeline nối tầng tự động (như `post_noon_chain_watchdog.py`: sau ca nuôi trưa -> chạy Reg Gmail -> chạy TikTok 2FA):
- Watchdog kiểm tra 2 điều kiện an toàn:
  1. Không có runner nuôi acc đang hoạt động (`is_feed_runner_active() == False`).
  2. Không có device lock nào đang active (`has_active_device_locks() == False`).

## 2. Vấn đề thực tế với Blocked Locks sau ca nuôi
- Khi runner nuôi acc hoàn thành ca hoặc gặp lỗi trên một số máy, nó chuyển lock của các máy đó sang trạng thái `blocked` (với timestamp `handoff_at`) để giữ nguyên hiện trường phục vụ operator triage.
- Các lock này có TTL là 60 phút (`LOCK_TTL_SECONDS = 3600`).
- **Hiện tượng:** Runner chính (`run_tiktok.py` / `multi-machine-feed-session`) đã thoát hoàn toàn, phần lớn đàn máy (ví dụ 67/80 máy) đã hoàn toàn rảnh, nhưng do có một lượng nhỏ máy (ví dụ 13 máy) còn lock `blocked`, điều kiện `has_active_device_locks()` vẫn trả về `True` (vì tập active statuses gồm: `active`, `running`, `queued`, `blocked`).
- Nếu script waiter chờ vô điều kiện, nó có thể bị treo hoặc phải chờ hết trọn vẹn 60 phút TTL của các máy bị lỗi đó.

## 3. Quy tắc xử lý chuẩn cho Coordinator / Watchdog
1. **Phân biệt Dead Owner vs Active Runner:**
   - Kiểm tra PID trong file lock: nếu owner PID đã chết (`owner_process_alive(pid) == False`), lock `blocked` đang trong giai đoạn chờ TTL 60p của Reaper.
2. **Dọn sạch Zombie / Orphan Waiters:**
   - Trước khi kích hoạt lệnh watchdog hoặc spawn tiến trình theo dõi mới, BẮT BUỘC kiểm tra và dọn các orphan waiter chạy nền (`post_noon_waiter.py`, inline bash sleep loops) để tránh xung đột tài nguyên hoặc kích hoạt trùng lặp.
3. **Chờ tự nhiên hay Takeover/Skip:**
   - **Chờ Reaper tự nhiên:** Nếu số máy `blocked` ít và pipeline yêu cầu toàn bộ farm phải sạch 100% lock, đợi Reaper thu hồi khi hết TTL 60p.
   - **Bypass / Partial Batch (nếu script hỗ trợ):** Nếu pipeline cho phép chạy trên các máy đã rảnh (unlocked machines), có thể truyền danh sách máy rảnh vào launcher hoặc dùng cờ `--force` / exclusion list để không làm trễ khung giờ vàng của chuỗi nghiệp vụ.
4. **Nghiệm thu hiện trường Gate 6:**
   - Dù ở trạng thái chờ hay đã chạy, bất kỳ báo cáo hiện trường nào cũng phải kèm theo bằng chứng screencap O(1) qua ADB của máy đại diện (`MEDIA:<path_anh>`).
