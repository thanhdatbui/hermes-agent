---
name: cross-host-windows-maintenance
description: "Use when running Windows Defender scan or Task Scheduler."
---
# Cross-Host Windows Maintenance & Security Automation

## 1. Overview
Skill này quy định quy trình vận hành và tự động hóa bảo trì hệ thống, quét virus định kỳ (Microsoft Defender Antivirus) và lập lịch Windows Task Scheduler trên cụm nhiều máy tính Windows (Local Kibe + Remote Admin qua SSH).

## 2. Windows Defender CLI Architecture
- **Vị trí công cụ chính chủ:** `C:\Program Files\Windows Defender\MpCmdRun.exe`
- **Chiến lược quét tối ưu cho máy Farm (Quick Scan vs Full Scan):**
  - **Quick Scan (`-Scan -ScanType 1`) - Bắt buộc dùng cho quét định kỳ:** Quét thẳng vào bộ nhớ RAM, tiến trình đang chạy, registry startup, Task Scheduler, AppData/Temp. Chỉ mất 30s - 8 phút. Không làm nghẽn I/O đĩa hay đơ giật các batch automation/render/database của farm. Tóm sống >99% stealer malware (Lumma, Vidar, RedLine...).
  - **Full Scan (`-Scan -ScanType 2`) - Tuyệt đối không chạy định kỳ:** Quét từng file trên toàn bộ ổ đĩa (mất 2-6 tiếng), gây Disk 100% và ngốn CPU, làm đứt gãy kết nối ADB/proxy và timeout database. CHỈ chạy Full Scan thủ công khi máy có dấu hiệu nhiễm độc rõ ràng hoặc user lỡ chạy file lạ.
- **Cập nhật mẫu nhận diện (Signature Update):**
  - Local: `MpCmdRun.exe -SignatureUpdate`
  - Remote qua SSH: `ssh -o ConnectTimeout=10 admin-farm "\"C:\Program Files\Windows Defender\MpCmdRun.exe\" -SignatureUpdate"`
  - *Exit code:* `0` = Hoàn tất cập nhật hoặc đã ở phiên bản mới nhất.
- **Quét Nhanh (Quick Scan - ScanType 1):**
  - Local: `MpCmdRun.exe -Scan -ScanType 1`
  - Remote: `ssh -o ConnectTimeout=10 admin-farm "\"C:\Program Files\Windows Defender\MpCmdRun.exe\" -Scan -ScanType 1"`
  - *Exit code quy chuẩn:*
    - `0`: Scan hoàn tất, sạch 100% không phát hiện mã độc (No threats detected).
    - `2`: Phát hiện mối đe dọa (Threat detected). Cần trích xuất tên mã độc và cảnh báo khẩn.

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
