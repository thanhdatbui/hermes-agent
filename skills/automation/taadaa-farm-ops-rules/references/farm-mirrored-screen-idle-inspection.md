# Farm Mirrored Screen Idle Inspection vs Running Artifact Triage

Khi User gửi ảnh chụp màn hình công cụ chiếu đàn (ví dụ: 数卫安卓投屏 / Xiaowei / Total Control) với nghi vấn: *"là đang chạy dở à, xong hết chưa mà thấy nhiều máy còn chạy / còn sáng màn hình / hiển thị app khác nhau"*:

## 1. Bản chất kiến trúc thiết bị (Root Cause)
1. **Không Force-Kill app về Home**:
   - Khi runner hoàn tất một phiên (Feed, Upload, Follow), runner **không kill app TikTok / Gallery về Home screen** trừ khi có crash/recovery.
   - Việc giữ nguyên app ở foreground để duy trì session tự nhiên, tránh TikTok bị khởi động lại liên tục gây nghi ngờ bot.
2. **Màn hình dừng ở điểm cuối của quy trình**:
   - Máy kết thúc lướt feed: dừng ở video feed cuối cùng.
   - Máy upload video: dừng ở gallery/thư viện ảnh hoặc trang profile cá nhân.
   - Máy bị lỗi switcher / verify: dừng ở popup hoặc giao diện onboarding.
   - Một số máy đã về Home: do watcher recovery hoặc kết thúc tác vụ đặc thù.

## 2. Quy trình kiểm tra 3 bước O(1) (Xác định Idle vs Running)

### Bước 1: Kiểm tra tiến trình host & runner state O(1)
- Đọc file state nhẹ:
  `cat D:/Taadaa/runtime/kibe/cron-state/runner_simple_state.json`
- Kiểm tra tiến trình chạy trên host:
  `ps aux | grep -i "feed\|runner\|multi_machine" | grep -v "hermes"`
- Nếu tiến trình đã kết thúc và `runner_simple_state.json` đã update timestamp phiên gần nhất $\rightarrow$ runner đã thoát.

### Bước 2: Canary probe I/O cảm ứng trên thiết bị thật qua ADB (getevent)
Đường dẫn ADB chuẩn trên host Kibe:
`"C:\Program Files (x86)\xiaowei\tools\adb.exe"`

Dùng lệnh `getevent` có timeout ngắn (2-3s) trên một vài máy mẫu đang hiển thị app trên màn chiếu:
```bash
# Kiểm tra máy có đang nhận touch/swipe tự động không:
python -c "
import subprocess
ADB = r'C:\Program Files (x86)\xiaowei\tools\adb.exe'
p = subprocess.Popen([ADB, '-s', '<SERIAL>', 'shell', 'getevent -c 5'], stdout=subprocess.PIPE)
try:
    stdout, _ = p.communicate(timeout=3)
    print('Touch event detected:', stdout)
except subprocess.TimeoutExpired:
    p.kill()
    print('No input event (IDLE).')
"
```
- Nếu **No input event**: Máy hoàn toàn IDLE (chỉ là màn hình giữ nguyên state cũ), không hề có runner nào đang thao tác.

### Bước 3: Đối soát watchdog report & trả lời dứt khoát
- Đối soát với báo cáo Ca/Phiên gần nhất từ watchdog (`1d62cb3562e0`).
- Trả lời thẳng cho User: Đã chạy xong hoàn tất, giải thích rõ lý do UI trên màn chiếu dừng ở state cuối của tác vụ, không làm User hoang mang tưởng treo hay chạy dở.
