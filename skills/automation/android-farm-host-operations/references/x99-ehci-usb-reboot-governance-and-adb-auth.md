# X99 EHCI USB Bus Reset, Reboot Governance & ADB Key Authentication

## 1. Bản chất phần cứng Chipset Intel X99 (C610 EHCI Controller)
- Bo mạch chủ Huananzhi X99 chạy 2 chip điều khiển USB 2.0 EHCI (`8D26` và `8D2D`).
- **Giới hạn phần mềm:** Driver Windows không hỗ trợ tính năng Live Disable/Enable mềm (`Disable-PnpDevice` trả về `HRESULT 0x8004100c - NotImplemented`, `pnputil /restart-device` yêu cầu reboot).
- **Hiện tượng kẹt socket:** Khi chạy quá tải I/O (stream màn hình nhiều máy qua XiaoWei hoặc >30 workers đồng thời), thanh ghi chip EHCI bị kẹt hoặc đường truyền Micro-USB dài (Box 4) bị drop gói. Điện thoại vẫn báo sạc nhưng socket ADB bị kẹt `offline` hoặc biến mất hẳn.
- **Biện pháp khôi phục duy nhất:** Phải kích hoạt chu kỳ reboot hệ điều hành (`shutdown /r /t 2`) để BIOS thực hiện System Bus Reset xóa sạch thanh ghi.

## 2. Phòng ngừa lỗi "unauthorized" hàng loạt sau khi Reboot
Khi máy tính khởi động lại, để tránh việc thiết bị Android rơi vào trạng thái `unauthorized` do lệch session hoặc thiếu key:
1. **Khóa biến môi trường Machine:**
   Set `ADB_VENDOR_KEYS = C:\Users\Admin\.android\adbkey` ở cấp Machine scope (`[Environment]::SetEnvironmentVariable('ADB_VENDOR_KEYS', ..., 'Machine')`). Điều này đảm bảo bất kỳ tiến trình nào gọi ADB đều đọc đúng cặp key RSA.
2. **Phân quyền Scheduled Task:**
   - Mọi task khởi chạy ADB (`Taadaa_ADB_User_Remote`, `Taadaa_Safe_USB_Guard_15m`) BẮT BUỘC cấu hình `UserId: Admin` (Interactive / Logon Session 1).
   - TUYỆT ĐỐI CẤM chạy ADB server dưới quyền `SYSTEM` (Session 0) vì sẽ chiếm cổng 5037 và chặn các app điều khiển của user (như XiaoWei).
3. **Cú pháp file kiểm tra cổng listening:**
   Trong file batch khởi động ADB, dùng đúng biến `%errorlevel%` thay vì `%0%`:
   ```bat
   netstat -ano | findstr ":5037" | findstr "LISTENING" >nul 2>&1
   if %errorlevel% equ 0 exit /b 0
   ```

## 3. Quy chuẩn Reboot Farm hàng ngày (TFT Game Guard: Chỉ chặn khi In-Match)
- **Khung giờ tối ưu:** 11:35 sáng (25 phút trước Ca 2 trưa 12:00). Tránh reboot lúc sáng sớm (05:30) vì còi POST BIOS và quạt CPU bung 100% RPM gây ồn khi người dùng đang ngủ.
- **TFT Game Guard (User Invariant — Chỉ chặn khi đang trong trận đấu thực sự):**
  * Script preflight (`farm_preflight_daily_reset.py`) **CHỈ CHẶN** tiến trình engine 3D:
    `League of Legends.exe` (Trận đấu TFT đang diễn ra).
    Nếu phát hiện `League of Legends.exe`: **ABORT REBOOT NGAY LẬP TỨC** để tránh làm user bị xử thua AFK.
  * **Cho phép reboot khi ở ngoài sảnh / hàng chờ:** Nếu user chỉ mở Riot Client, `LeagueClient.exe`, `LeagueClientUx.exe` (lobby / queue / xem BXH) $\rightarrow$ **VẪN TIẾN HÀNH REBOOT BÌNH THƯỜNG**.
  * **Tất cả tác vụ nền khác (farm, cào video, render ffmpeg, cron, sync):** Chấp nhận tự động reboot làm sạch trước ca trưa.

## 4. Tự Động Phục Hồi Cào & Render Sau Reboot Trên Admin Farm
- Khi Admin PC reboot xong, tính năng Windows `AutoAdminLogon = 1` tự nạp thẳng vào Desktop của user `Admin` (Session 1).
- Toàn bộ các tiến trình crawler (`run_admin_downloader`) và render engine (`ffmpeg.exe` xử lý kho `D:\video goc may 2`, script hàng đợi tại `D:/Taadaa/Tiktok-video/scripts`) được liên kết với Windows Startup $\rightarrow$ Tự động hồi sinh và tiếp tục cày cuốc mà không cần can thiệp thủ công.

## 5. Trần Concurrency USB 2.0 cho Feed Session
- Hạ `MaxWorkers` mặc định từ 40 xuống 25.
- Đặt ràng buộc cứng mức engine `[ValidateRange(1, 30)]` trong `run-feed-session.ps1` để ngăn chặn tham số vượt ngưỡng an toàn băng thông USB 2.0.
