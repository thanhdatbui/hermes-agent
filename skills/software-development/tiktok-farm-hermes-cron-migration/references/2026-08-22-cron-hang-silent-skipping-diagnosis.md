# Chẩn đoán Cron Nuôi Acc Im Lặng Không Gửi Alert (Job Hang & Already Running Skipping)

## Triệu chứng
- Sáng không thấy máy nào chạy nuôi acc.
- Không nhận được bất kỳ tin nhắn/alert báo lỗi nào trên Telegram.
- `manifests/<day>` hôm nay chưa tồn tại.

## Nguyên nhân gốc (Root Cause)
1. **Dangling Process / Timeout từ đêm hôm trước**:
   - Runner (`tiktok_runner.py`) hoặc Watcher (`tiktok_watcher.py`) bị kẹt tiến trình (ví dụ: timeout 3600s hoặc socket/lock wait không hồi kết).
   - Tiến trình Python của watcher/runner vẫn còn sống ngầm trong OS (ví dụ `python_runner/scripts/hermes_cron_watcher.py`).
2. **Hermes Scheduler Skip Toàn Bộ Các Lần Chạy Sau**:
   - Trong `agent.log`, Hermes kiểm tra trạng thái job và thấy tiến trình trước chưa hoàn tất, ghi log:
     `INFO cron.scheduler: Job 'phase9-runner-tiktok-feed' already running — skipping`
     `INFO cron.scheduler: Job 'phase9-watcher-tiktok-feed' already running — skipping`
   - Picker 06:00 sáng hoặc Runner các chu kỳ 15 phút kế tiếp không thể chạy.
   - Do không có máy nào được kích hoạt, không có runner sinh log/lỗi -> Watcher không có sự kiện để alert -> Telegram im lặng 100%.

## Quy trình kiểm tra nhanh (Diagnostic Recipe)
1. **Kiểm tra tiến trình treo ngầm**:
   ```python
   import psutil
   for p in psutil.process_iter(['pid', 'name', 'cmdline', 'create_time']):
       cmd = ' '.join(p.info['cmdline'] or [])
       if any(k in cmd for k in ['hermes_cron_watcher', 'hermes_cron_runner', 'tiktok_runner', 'tiktok_watcher']):
           print(p.info['pid'], p.info['create_time'], cmd)
   ```
2. **Kiểm tra log Hermes Cron Scheduler**:
   - Tìm log skipping: `grep "already running — skipping" ~/AppData/Local/hermes/logs/agent.log`
   - Xem output job runner: `~/AppData/Local/hermes/cron/output/cdd43b124363/*.md`
3. **Kiểm tra Manifest ngày hiện tại**:
   - Thư mục `D:/Taadaa/runtime/kibe/cron-state/manifests/<YYYY-MM-DD>` có tồn tại không.

## Cách xử lý (Recovery)
1. **Kill các process Python treo ngầm**:
   - Kill PID của các tiến trình watcher/runner cũ còn sót lại.
2. **Xử lý lease nếu có**:
   - Kiểm tra `D:/Taadaa/runtime/kibe/cron-state/runner-live-lease/<day>.json`, nếu lease cũ hết hạn nhưng chưa giải phóng thì xóa/dọn.
3. **Kích hoạt chạy lại Picker**:
   - Chạy lại `tiktok_picker.py` để sinh manifest cho ngày mới.
4. **Trigger Runner/Watcher**:
   - Hermes cron scheduler sẽ tự động nhả cờ và chạy lại ở tick tiếp theo.
