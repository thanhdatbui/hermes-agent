# Watchdog Temporal Coupling vs Zero-Regression Invariant Architecture (Incident 2026-11-03)

## 1. Bản Chất Sự Cố Kẹt Gối Đầu Phiên & Hang ADB (Incident 2026-11-03)
- **Kẹt gối đầu phiên (Overlapping Session Lock):**
  - Phiên 1 (06:00 – 08:00) xong lúc 07:24 trên Admin. Đúng 08:00:54, Phiên 2 bắt đầu làm cờ `global_runner_busy = True`.
  - Trong `feed_session_watchdog.py`, hàm `is_cluster_session_busy` fallback về `global_runner_busy` khi phiên chưa chạm mốc kết thúc (`07:24 < 08:00` theo commit `fca40a4`), khiến báo cáo Phiên 1 bị giam giữ suốt 1.5 giờ đến tận 09:35 khi Phiên 2 xong hoàn toàn.
- **Treo luồng watchdog do gọi ADB live trong Incident Emitter:**
  - Khi một ca chạy có nhiều máy lỗi (ví dụ: 56 máy lỗi Follow trên Farm Admin), vòng lặp duyệt lỗi trong watchdog gọi `incident_emitter.emit_if_needed()`.
  - Hàm này tự động gọi `collect_telemetry()` kích hoạt lệnh `adb exec-out screencap` và `atx-agent dump` live qua mạng cho từng máy bị lỗi nếu thiếu artifact.
  - Hậu quả: 56 máy × 8s = ~450s làm watchdog cronjob bị timeout/hang kịch trần (600s), tiến trình bị ngắt trước khi kịp in kết quả ra `stdout`, trong khi file state có thể đã đánh dấu khiến báo cáo bị mất hút vĩnh viễn trên Telegram.

## 2. Ba Tầng Trạng Thái Độc Lập (Advisor Sol Architecture)
Hệ thống reporting tuyệt đối không được đánh đồng 3 tầng trạng thái:
1. **Runner Execution State:** Hệ điều hành có tiến trình runner nào đang sống không? (State 1)
2. **Session Completion State:** Phiên cụ thể đó đã thực sự hoàn tất và đóng `run_manifest.json` với `end_time` hợp lệ chưa? (State 2)
3. **Report Publication State:** Báo cáo của phiên đó đã đủ điều kiện xuất bản lên Telegram chưa? (State 3)

**Bất biến:** Runner bận vì Phiên 2 KHÔNG ĐỒNG NGHĨA với Phiên 1 chưa được phép chốt báo cáo. Khi Phiên 1 đã đạt State 2 (COMPLETED) và thư mục đã xuất hiện run của Phiên 2 (`has_later_run == True`), `is_cluster_session_busy` bắt buộc phải trả về `False` để giải phóng Phiên 1 ngay lập tức lúc 08:05.

## 3. Kỷ Luật Watchdog Read-Only (Cấm Gọi ADB Live)
- Watchdog cronjob chạy định kỳ 5 phút với ngân sách thời gian cực ngắn (<30s).
- **CẤM TUYỆT ĐỐI** watchdog gọi bất kỳ lệnh ADB trực tiếp nào tới điện thoại thật (cấm `screencap`, `input`, `dumpUI`, `adb shell`).
- Khi tích hợp `incident_emitter`:
  * Bắt buộc truyền cờ `is_post_shift=True` hoặc truyền đầy đủ `machine_dir` để hàm chỉ bóc tách artifact tĩnh đã ghi sẵn trên đĩa SSD.
  * Nếu không có artifact, ghi nhận lỗi thuần log text, tuyệt đối không fallback sang kết nối ADB live làm nghẽn luồng reporting.

## 4. Chốt Chặn Anti-Regression & GuardGate Invariant
- **Bảo toàn Invariant lịch sử:**
  * Giữ nguyên contract của commit `fca40a4` (28/09): `_is_session_manifest_completed` giữ nguyên kiểm tra mốc kết thúc phiên để không phá vỡ test suite.
  * Giữ nguyên múi giờ HCMC của commit `6fe351f` (13/10).
  * Giữ nguyên mốc an toàn 15 phút `latest_run_minutes_ago >= 15` của commit `490776f` (19/10).
- **Đăng ký Invariant vào `rules.json`:**
  * Bổ sung quy tắc cơ học vào `rules.json` của repo `tiktok-luot nuoi acc`:
    Bắt buộc hàm `is_cluster_session_busy` phải luôn chứa nhánh giải phóng `decision = False` khi `has_later_run == True` và phiên cũ đã có `run_manifest.json`.
  * Công cụ `D:/Taadaa/tools/guardgate/runner.py` sẽ tự động quét diff và chặn mọi commit vô tình xóa bỏ nhánh giải phóng này.
