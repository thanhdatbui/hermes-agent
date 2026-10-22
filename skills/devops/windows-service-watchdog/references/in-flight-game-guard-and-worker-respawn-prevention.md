# In-Flight Game Guard & Worker Respawn Prevention

## Bối cảnh & Hiện trường sự cố
Trên máy trạm đa nhiệm (vừa render video nền, vừa chơi game như Warcraft III, TFT, LMHT):
- Người dùng đã cấu hình watchdog định kỳ (ví dụ Task Scheduler chạy mỗi 15 phút) để tìm và kill tiến trình nặng (`ffmpeg.exe`) khi phát hiện game.
- Tuy nhiên trong thực tế, người dùng vào game vẫn bị giật lag nặng nề, CPU vẫn bị chiếm dụng 100%.

## Nguyên nhân gốc rễ (2 điểm gãy kiến trúc)
1. **Chu kỳ watchdog quá thưa (Coarse-Grained Polling):**
   - Chu kỳ 15 phút là khoảng cách quá lớn đối với trải nghiệm game thời gian thực. Nếu người dùng bật game ở phút thứ 2, hệ thống sẽ tiếp tục cày nát CPU thêm 13 phút trước khi watchdog kịp thức dậy.
2. **Bẫy vòng lặp hồi sinh ngay lập tức của Worker cha (Worker Respawn Trap):**
   - Worker render (`run_admin_render_worker.py`) chạy trong vòng lặp vô tận `while True: for task in tasks: ...`.
   - Lệnh render là lệnh chặn (blocking `subprocess.run(cmd)`).
   - Khi Watchdog bên ngoài phát hiện game và kill tiến trình con `ffmpeg.exe`, `subprocess.run()` trả về `returncode != 0`.
   - Worker cha bắt được mã lỗi, ghi log cảnh báo và **ngay lập tức bước sang vòng lặp kế tiếp để spawn một tiến trình `ffmpeg.exe` mới toanh ngay tại giây đó!**
   - Hậu quả: Watchdog vừa kill xong thì worker cha lại sinh ra ffmpeg mới; watchdog đã hết lượt chạy và ngủ 15 phút, bỏ mặc ffmpeg mới chiếm trọn CPU trong suốt trận game.

## Giải pháp kiến trúc chuẩn (In-Flight Game Guard)

### 1. Nhúng Game Guard trực tiếp vào vòng lặp Worker (Pre-spawn + In-flight)
Không giao toàn bộ trách nhiệm phát hiện game cho watchdog bên ngoài, mà Worker phải tự giám sát:
- **Pre-spawn Check:** Trước khi nhận hoặc khởi động bất kỳ task render mới nào, worker kiểm tra `is_gaming_active()`. Nếu game đang bật $\rightarrow$ Chuyển trạng thái `STANDBY`, ngủ và không spawn subprocess.
- **In-flight Polling ($\le 2$ giây):** Trong suốt thời gian render, chạy vòng lặp kiểm tra game mỗi 2 giây (`while proc.poll() is None:` hoặc thread giám sát).
  + Khi phát hiện game bật lên: can thiệp ngay lập tức trong $\le 2$ giây.

### 2. Đóng băng / Rã đông (`p.suspend()` / `p.resume()`) thay vì Kill thô bạo
- Thay vì `kill()`, sử dụng `psutil.Process(pid).suspend()` cho toàn bộ cây tiến trình (`ffmpeg` + worker):
  - CPU ngay lập tức tụt về **0%** trong $\le 2$ giây, nhường 100% tài nguyên cho game.
  - Video đang render dở không bị vứt bỏ, không bị hỏng file hay phí phạm thời gian đã mã hóa.
- Khi người dùng tắt game: tự động gọi `resume()` để tiếp tục render từ đúng khung hình đang dở.
- Nếu treo quá lâu (`MAX_SUSPEND_SEC = 7200s`): Escalate sang kill sạch để dọn dẹp tránh deadlock.

### 3. Tái định vị vai trò của Watchdog
Watchdog định kỳ (Task Scheduler / Cron) không nên can thiệp thô bạo vào vòng đời task render đang chạy, mà chuyển sang làm nhiệm vụ dọn dẹp và cứu hộ:
- **Dọn tiến trình mồ côi (`sweep_orphan_ffmpeg`):** Quét và kill các tiến trình `ffmpeg.exe` mà `ppid` không còn tồn tại trên OS.
- **Giám sát nhịp tim (`render_heartbeat.json`):** Worker cập nhật timestamp mỗi giây. Nếu worker bị crash hoặc timestamp stale $> 30$ giây $\rightarrow$ Watchdog mới khởi động lại worker.
