# Fast Fail-Closed cho Lỗi Thiết Bị Offline / Mất Kết Nối (Multi-Machine Feed Session)

## 1. Bối cảnh & Vấn đề
- Trong batch multi-machine (`multi_machine_feed_session.py`), ThreadPoolExecutor có dung lượng worker bị giới hạn (thường `max_workers = 40` cho 74-80 máy).
- Khi một máy gặp lỗi phần cứng/kết nối vật lý:
  - `device is offline or ADB/USB disconnected`
  - `Device serial ... was not found in adb devices`
  - `required router proxy is unreachable` / `ping probe failed`
  - `is_connection_lost(err)` (ADB transport lost, device gone)
- Nếu flow tiếp tục retry hoặc chờ outer watchdog timeout (`DEFAULT_DEVICE_TIMEOUT_SECONDS = 2100s` / 35 phút), worker slot bị chiếm dụng suốt 35-60 phút khiến toàn bộ các máy đợt 2 (34+ máy còn lại) bị nghẽn hàng đợi nghiêm trọng.

## 2. Nguyên tắc Fast Fail-Closed & Giữ Nguyên Lock Blocked
1. **Ngắt Nhanh (<= 1-2 phút):**
   - Với các lỗi thiết bị offline, device not found, mất ADB transport hoặc proxy host unreachable, flow BẮT BUỘC fail-closed ngay lập tức.
   - Tuyệt đối không retry kéo dài hoặc chờ cạn budget 35 phút.
2. **BẮT BUỘC GIỮ NGUYÊN LOCK `blocked` (Thời hạn 1 giờ):**
   - Phải gọi `lease.set_status("blocked")` với đầy đủ message lỗi và stop reason.
   - Lock JSON file (`~/.codex/device-locks/machine_*.lock.json` hoặc runtime device locks) phải ghi nhận status `blocked`.
   - Cơ chế `reap-dead-owner-locks` trên farm được thiết lập giữ các lock `blocked` này trong vòng 1 giờ để bảo vệ thiết bị và giữ nguyên hiện trường cho người vận hành. CẤM release lock về free/released khi thiết bị đang offline/lỗi.
3. **Bắn Farm Alert & Lưu Evidence:**
   - In cảnh báo chuẩn: `[ALERT] [MÁY {machine}] Dừng: {final_status} | Lý do: {stop_reason}`.
   - Gọi `_send_farm_machine_alert_once` để báo tin cho operator.
   - Người vận hành có thể inspect hiện trường máy lỗi bằng:
     `python D:/Taadaa/tools/inspect_machine.py <N>`
   - Giải phóng worker thread ngay lập tức để đợt máy tiếp theo được nạp vào chạy.

## 3. Lưu ý Môi trường Python & Pytest Trên Máy Host (Windows)
- Python interpreter chuẩn của farm automation nằm tại:
  `D:/Taadaa/python-envs/automation/Scripts/python.exe` (chú ý: Windows venv dùng thư mục `Scripts/`, không phải `bin/` hay root).
- Khi chạy pytest qua bash terminal, biến môi trường `PYTHONPATH` có thể kế thừa từ venv của agent bên ngoài dẫn đến xung đột C-extensions (ví dụ `ImportError: cannot import name '_imaging' from 'PIL'`).
- Luôn cô lập `PYTHONPATH` khi kiểm thử:
  ```bash
  PYTHONPATH="D:/Taadaa/tiktok-luot nuoi acc/python_runner;D:/Taadaa/automation-core/src" \
  /d/Taadaa/python-envs/automation/Scripts/python.exe -m pytest python_runner/tests/test_multi_machine_feed_session.py -v
  ```
