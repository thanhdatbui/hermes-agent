# Watchdog Midnight Rollover & Cascading Batch Delay Invariants

## 1. Sự cố Watchdog chốt non báo cáo khi phiên vắt qua nửa đêm (Incident 2026-09-06)

### Triệu chứng & Nguyên nhân gốc
- **Triệu chứng:** Phiên Ca 3 Phiên 3 (Row 5, 74 máy) chạy lúc 22:32, đến 00:00:33 Watchdog Telegram bắn thông báo: `"• Tổng máy xử lý: 2 máy"` trong khi 72 máy còn lại vẫn đang chạy bình thường.
- **Root Cause 1 (Midnight Rollover):** Đồng hồ chuyển sang ngày mới (00:00), biến `target_date` thành ngày hôm qua (`is_today = False`). Hàm `can_report_session` khi thấy `is_today == False` đã trả về `True` vô điều kiện mà không kiểm tra runner có đang chạy vắt đêm hay không.
- **Root Cause 2 (CLI Flag Mismatch):** Hàm `is_feed_runner_active()` chỉ kiểm tra chuỗi `multi_machine_feed_session` (gạch dưới), trong khi câu lệnh thực tế từ Hermes cron chạy với `--mode multi-machine-feed-session` (gạch nối) và script `run_tiktok.py`, dẫn đến watchdog ngỡ rằng runner đã dừng.
- **Hậu quả:** Đúng lúc 00:00:33 mới chỉ có 2 máy (M55, M13) ghi xong summary. Watchdog chốt non 2 máy và đánh dấu phiên đã report vào `feed_session_reported.json`, nuốt mất kết quả của các máy còn lại.

### Quy tắc bất biến cho Watchdog báo cáo phiên
1. **Runner Active Hard Block:** Nếu `runner_busy == True`, TUYỆT ĐỐI KHÔNG được chốt báo cáo phiên, bất kể là phiên hôm nay hay phiên hôm qua vắt qua đêm (`return False`).
2. **Nhận diện tiến trình toàn diện:** Kiểm tra cả chuỗi gạch nối `--mode multi-machine-feed-session`, `run_tiktok.py`, `hermes_cron_runner.py`, `tiktok_runner.py`, `run-feed-session.ps1`. Luôn loại trừ PID của chính tiến trình watchdog (`p.pid == os.getpid()`).
3. **Điều kiện báo cáo phiên hôm trước (`not is_today`):** Chỉ cho phép chốt báo cáo khi `not runner_busy` VÀ (`completed_expected_count >= expected_count` HOẶC thời gian hiện tại đã vượt ngưỡng an toàn, ví dụ `now_hm >= "02:00"` sáng).
4. **Recovery khi chốt non:** Xóa session key (ví dụ `2026-09-05_ca3_phien3`) trong `D:\Taadaa\runtime\kibe\cron-state\feed_session_reported.json` để watchdog tự động quét lại toàn bộ khi tiến trình kết thúc thật sự.

---

## 2. Nguyên nhân trễ phiên dây chuyền (Cascading Batch Delay)

### Phân tích hiện tượng
- Phiên 2 chạy từ 20:31 kéo dài đến 22:31:43 (gần 2 tiếng) do:
  1. **Nghẽn hàng đợi Threadpool (`max_workers = 40`):** 74 máy chia làm 2 đợt. Một số máy bị mất mạng/rớt ADB/ATX không phản hồi (M12, M46, M68, M70, M76) ngâm worker thread chờ timeout 30s-60s qua nhiều bước, giữ slot threadpool tới 15-20 phút. Đợt 2 bị dồn ứ thời gian chờ slot.
  2. **Dead-owner Lock tồn đọng từ ca trước:** M19 và M40 bị khóa bởi tiến trình cũ từ 12:41 trưa (Ca 2), đến 20:31 tối (Ca 3) vẫn chưa hết TTL lock hoặc chưa được giải phóng.
  3. **Lỗi unhandled exception nội bộ:** Thiếu import `ADBError` trong `automation-core/src/automation_core/device.py` (chỉ import `AdbClient`) khiến `raise ADBError(...)` crash unhandled trên 5 máy (M4, M9, M24, M44, M64).
- Do Phiên 2 kết thúc trễ lúc 22:31, Phiên 3 bị đẩy lùi sang 22:32. Vì Phiên 3 mang tải nặng nhất (Lướt feed + Follow chéo + Đẩy video ADB + Post video + Verify Profile trên 74 máy tiêu tốn ~45-50 phút), việc bắt đầu sau 22:30 chắc chắn làm phiên chạy vắt qua nửa đêm.

### Giải pháp kỹ thuật chuẩn
1. **Giảm TTL Lock:** Rút ngắn TTL lock thiết bị để cron `reap-dead-owner-locks` thu hồi sớm các lock mồ côi/crash từ ca trước.
2. **Hard Deadline per-machine:** Áp đặt timeout cứng cho mỗi worker máy (ví dụ max 12-15 phút/máy). Máy nào rớt mạng hoặc lỗi ADB lặp lại phải fail-closed ngay để nhả slot threadpool cho máy khác.
3. **Fail-closed Safe Imports:** Đảm bảo mọi module tương tác thiết bị (`automation-core/device.py`, `python_runner/flows/*`) import đầy đủ `ADBError` để bắt ngoại lệ có kiểm soát, tránh crash worker ngoài ý muốn.
