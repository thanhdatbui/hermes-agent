---
name: cross-host-windows-maintenance
description: "Use when running Windows Defender scan or Task Scheduler."
---

# Cross-Host Windows Maintenance & Security Automation

## 1. Overview
Skill này quy định quy trình vận hành và tự động hóa bảo trì hệ thống, quét virus định kỳ (Microsoft Defender Antivirus) và lập lịch Windows Task Scheduler trên cụm nhiều máy tính Windows (Local Kibe + Remote Admin qua SSH).

## 2. Windows Defender CLI Architecture
- **Vị trí công cụ chính chủ:** `C:\Program Files\Windows Defender\MpCmdRun.exe`
- **Cập nhật mẫu nhận diện (Signature Update):**
  - Local: `MpCmdRun.exe -SignatureUpdate`
  - Remote qua SSH: `ssh -o ConnectTimeout=10 admin-farm "\"C:\Program Files\Windows Defender\MpCmdRun.exe\" -SignatureUpdate"`
  - *Exit code:* `0` = Hoàn tất cập nhật hoặc đã ở phiên bản mới nhất.
- **Quét Nhanh (Quick Scan - ScanType 1):**
  - Local: `MpCmdRun.exe -Scan -ScanType 1`
  - Remote: `ssh -o ConnectTimeout=10 admin-farm "\"C:\Program Files\Windows Defender\MpCmdRun.exe\" -Scan -ScanType 1"`
  - Quét bộ nhớ RAM, Registry, tiến trình hoạt động và các mục Startup/Windows cốt lõi (chỉ mất 30s - 8 phút), không làm nghẽn đĩa như Full Scan.
  - *Exit code quy chuẩn:*
    - `0`: Scan hoàn tất, sạch 100% không phát hiện mã độc (No threats detected).
    - `2`: Phát hiện mối đe dọa (Threat detected). Cần trích xuất tên mã độc và cảnh báo khẩn.

## 3. Critical Pitfalls & Solutions
1. **Lỗi Tranh Chấp Scan Engine (Single Engine Mutex):**
   - Microsoft Defender trên mỗi máy Windows chỉ cho phép DUY NHẤT một phiên scan engine hoạt động tại một thời điểm.
   - Nếu có tiến trình `MpCmdRun.exe` cũ bị mồ côi (do timeout lệnh trước đó hoặc ngắt kết nối SSH dở dang), tiến trình quét mới sẽ bị nghẽn treo.
   - **Xử lý:** Kiểm tra `tasklist | findstr MpCmdRun` và giải phóng PID cũ bằng `taskkill /F /PID <pid>` trước khi chạy đợt quét mới.
2. **Trần Timeout 60s Trên Terminal Coordinator:**
   - Quét Defender trên máy Admin có thể kéo dài 5-10 phút nếu tải CPU cao.
   - Lệnh terminal foreground có trần an toàn 60s.
   - **Xử lý:** Chạy qua `terminal(command=..., background=True, notify_on_complete=True)` và theo dõi bằng `process(action='wait', timeout=30)` cho đến khi tiến trình thoát hoàn toàn với exit code 0.
3. **Lên Lịch Hệ Thống Bền Vững (Windows Task Scheduler vs Cron):**
   - Khi cần lịch quét cố định sống độc lập qua các đợt restart gateway/reboot máy, dùng native Windows Task Scheduler:
     ```cmd
     schtasks /Create /TN "WeeklyWindowsDefenderScan" /TR "python D:\Taadaa\tools\cron_windows_defender_scan.py" /SC WEEKLY /D SUN /ST 03:30 /F
     ```
   - Khung giờ tối ưu: **03:30 sáng Chủ Nhật hàng tuần** (khung giờ farm nghỉ ca đêm, rảnh máy).

## 4. Kỷ Luật Phản Hồi Khi User Ra Lệnh (Anti-Promise / Anti-Stalling)
- Khi User yêu cầu "Làm đi", "Chạy phát luôn đi": CẤM TUYỆT ĐỐI chỉ trả lời tin nhắn hứa hẹn ("Đang dispatch...", "Sẽ gửi lại sau...") rồi dừng turn mà không thực thi.
- Phải dùng tool thực thi ra kết quả thật hoặc kích hoạt tiến trình nền cụ thể, theo dõi và đưa ra bằng chứng nghiệm thu thực tế trước khi kết thúc turn.
