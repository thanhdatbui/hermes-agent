# Farm Alert Error Patterns — multi-machine-feed-session

Tài liệu tra cứu nhanh các mẫu lỗi thường gặp gửi về nhóm Telegram "Farm Alerts" từ scheduler `multi-machine-feed-session` (`tiktok-luot nuoi acc`).

---

### 1. `worker returned unexpected result type: NoneType` / `child exited`
- **Ngữ cảnh:** Xuất hiện khi `ThreadPoolExecutor` / tiến trình con xử lý máy ném `SystemExit` hoặc unhandled exception trước khi tạo ra `MachineFeedSessionResult`.
- **Vị trí code:** `python_runner/flows/multi_machine_feed_session.py` (`_run_child` & future resolution loop).
- **Nguyên nhân chính:**
  - Script con bị kill đột ngột hoặc crash do lỗi memory/driver.
  - Exception ngoại lệ không được bọc khiến worker trả về `None` hoặc exit ngang.
- **Xử lý:**
  - Máy được đưa về trạng thái `GIỮ HIỆN TRƯỜNG` (`handoff` lock).
  - Kiểm tra log chi tiết của máy trong `runs/` hoặc artifact directory tương ứng.

---

### 2. `run plan max_duration_seconds exceeded before <operation>`
- **Ngữ cảnh:** Kịch bản feed session bị dừng do chạm ngưỡng thời gian tối đa (`max_duration_seconds` / `_device_timeout_seconds`, mặc định 900s / 15 phút per-device watchdog).
- **Vị trí code:** `python_runner/core/deadline.py` (`ensure_run_plan_deadline`), `python_runner/flows/feed_swipe_smoke.py`, `python_runner/flows/multi_machine_feed_session.py`.
- **Nguyên nhân chính:**
  - Phiên lướt đủ 15 video (delay xem 2-8s/vid) cộng dồn với thời gian capture UI XML, kiểm tra popup/like ở từng bước.
  - Proxy tải video/feed chậm hoặc lag ATX capture khiến tổng thời gian thực thi vượt mốc 900s trước khi xong swipe cuối (ví dụ `before feed swipe 15 after watch delay`).
  - Watchdog ném `RunPlanDeadlineExceeded` để ngắt runner, tránh chiếm giữ worker vĩnh viễn.
- **Xử lý:**
  - Tăng `_device_timeout_seconds` (ví dụ 1200s / 20 phút) nếu mạng tải chậm hoặc cấu hình nhiều swipe/watch delay lớn.
  - Giảm bớt số swipes / watch delay nếu muốn phiên ngắn và đồng đều hơn.

---

### 3. `TikTok focus lost`
- **Ngữ cảnh:** Kịch bản dừng an toàn khi safety check phát hiện package hiển thị trên foreground không phải TikTok (`com.ss.android.ugc.trill`).
- **Vị trí code:** `python_runner/core/safety.py` (`safety_check`), `python_runner/flows/observe.py` (`get_focused_activity`).
- **Nguyên nhân chính:**
  - Màn hình bị văng ra Home / Samsung Launcher (`com.sec.android.app.launcher`).
  - Cài đặt hệ thống (`com.android.settings`), popup quyền hoặc thông báo hệ thống che mất giao diện TikTok.
  - Runner kích hoạt cơ chế an toàn giữ nguyên hiện trường (`GIỮ HIỆN TRƯỜNG`) để tránh click nhầm ra ngoài ứng dụng.
- **Xử lý:**
  - Kiểm tra screencap xem app bị crash văng ra ngoài hay do popup hệ thống che.
  - Mang TikTok quay lại foreground (`adb shell monkey -p com.ss.android.ugc.trill -c android.intent.category.LAUNCHER 1` hoặc resume flow).
  - Bổ sung xử lý dismiss cho các popup/activity hệ thống ngoại lệ trước khi safety check ngắt phiên.

---

### 4. `required Android VPN is not connected` / `ViChanger GET_IP failed after 3 retries`
- **Ngữ cảnh:** Xuất hiện ở bước Preflight trước khi mở TikTok trong `multi-machine-feed-session`.
- **Vị trí code:** `automation_core/preflight.py` (`check_android_vpn`, `require_android_vpn`), `python_runner/core/vpn_preflight.py` (`require_vichanger_connected`).
- **Nguyên nhân chính:**
  - Máy được map proxy trong workbook nhưng `tun0` down, VPN mất kết nối hoặc ViChanger broadcast `GET_IP` thất bại sau 3 lần retry (timeout / proxy die / app ViChanger mất login).
  - Cơ chế *fail-closed* chặn đứng kịch bản, dừng phiên ngay (`swipes_completed = 0`) để chống lộ real IP gây hỏng nick.
  - Chụp màn hình hiện trường và gửi cảnh báo `[MÁY XX] DỪNG PHIÊN` lên Telegram. Các máy khác trong batch vẫn tiếp tục chạy độc lập; phiên sau của máy đó vẫn được kích hoạt theo lịch.
- **Xử lý:**
  - Kiểm tra trạng thái proxy/VPN và app ViChanger trên máy (xem `references/vichanger-vpn-blocker-after-reboot-2026-08-11.md`).
  - Kiểm tra log GanProxy watcher xem proxy có được gán lại thành công hay không.
