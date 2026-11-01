# Cơ Chế Đóng Game Idle (Warcraft 3 / TFT) Giải Phóng Lịch Reboot Farm

## 1. Vấn Đề Thực Tế
- Lịch reboot định kỳ toàn farm chạy lúc `05:20`, `11:20`, `17:20` qua Task Scheduler (`farm_preflight_daily_reset.py`).
- Preflight kiểm tra nghiêm ngặt: Nếu phát hiện tiến trình game (`war3.exe`, `w3l.exe`, `league of legends.exe`, `tftclient...`) đang chạy trên Admin PC thì lập tức `ABORT` từ chối reboot để chống làm người chơi bị AFK / xử thua.
- **Hiện tượng treo lịch:** Người chơi rời máy để game mở qua đêm hoặc quên tắt game suốt nhiều giờ (`idle > 8h`), khiến mọi cữ reboot (như 11:20) đều bị chặn hoàn toàn, máy không được giải phóng tài nguyên.

## 2. Giải Pháp Watchdog Đóng Game Idle (`game_idle_auto_close_watchdog.py`)
1. **Kiểm tra thời gian không thao tác (Last Input Info):**
   - Dùng Win32 API `GetLastInputInfo` để tính thời gian idle chuột/phím của người dùng trên máy:
     $$\text{idle\_seconds} = \frac{\text{GetTickCount}() - \text{dwTime}}{1000.0}$$
2. **Ngưỡng hành động:**
   - Ngưỡng idle: $\ge 3600\text{s}$ (1 giờ).
   - Nếu game đang mở NHƯNG người dùng không đụng chuột/phím suốt $\ge 1$ giờ: Watchdog xác định người dùng đã rời máy ➔ Tiến hành đóng an toàn tiến trình game (`proc.terminate()`, fallback `taskkill /F`).
   - Nếu $\text{idle} < 3600\text{s}$: Im lặng tuyệt đối (exit 0) để người chơi tiếp tục trận đấu.
3. **Triển khai:**
   - Đặt script tại `C:\Taadaa_Service\game_idle_auto_close_watchdog.py` trên Admin PC và chạy qua SSH trước các khung reboot định kỳ.
