# Preflight 3-Shift Reboot Schedule & Task Validation Protocol (2026-10-13)

## 1. Bối Cảnh & Kỷ Luật Người Dùng (User Directed)
- **Quy tắc phân định Ca vs Phiên (Chống reboot dày đặc):**
  - Farm vận hành theo 3 Ca chính hàng ngày (mỗi Ca gồm 2 phiên cách nhau 2 tiếng: Ca sáng 06:00/08:00, Ca trưa 12:00/14:00, Ca tối 18:00/20:00).
  - **CẤM TUYỆT ĐỐI** cài đặt lịch reboot trước từng phiên lẻ (chu kỳ 2 tiếng) vì tần suất quá dày, làm ngắt quãng trải nghiệm máy tính và văng game/app liên tục.
  - **Lịch cố định chuẩn:** Đúng 3 mốc trước 3 Ca chính:
    1. **05:45:00** — Trước Ca 1 Sáng (06:00, 15 phút đệm).
    2. **11:35:00** — Trước Ca 2 Trưa (12:00, 25 phút đệm).
    3. **17:45:00** — Trước Ca 3 Tối (18:00, 15 phút đệm).

## 2. Kiến Trúc Triển Khai Đơn Nguồn (Single Source of Truth)
- Để tránh lệch cấu hình (Configuration Drift) giữa Python wrapper và PowerShell script:
  * **File thực thi gốc (SSOT):** `D:\Taadaa\tools\services\Taadaa_Service\setup_daily_reboot_task.ps1`.
  * **Wrapper quản lý:** `D:\Taadaa\tools\services\Taadaa_Service\update_reboot_schedule.py` gọi trực tiếp script `.ps1` qua PowerShell thay vì duplicate inline code.
  * **Fail-Fast Validation:** Script PowerShell bắt buộc dùng `Test-Path` kiểm tra tồn tại của `$pythonExe` và `$scriptPath` trước khi gỡ task cũ (`Taadaa_Farm_Daily_Reboot_0530`, `Taadaa_Farm_Daily_Reboot_0745`) hay tạo task mới.
  * **Read-Back Verification:** Ngay sau khi `Register-ScheduledTask`, script bắt buộc truy vấn lại `Get-ScheduledTask` và assert đúng 3 trigger boundaries (`05:45:00`, `11:35:00`, `17:45:00`). Nếu thiếu trigger hoặc sai lệch thì văng ngoại lệ exit 1 ngay lập tức.

## 3. Kỷ Luật Telemetry & Chống Phình Log
- Wrapper `update_reboot_schedule.py` ghi structured JSON telemetry ra stdout và file `C:\Taadaa_Service\reboot_task_update.log`:
  * `timestamp`: UTC ISO 8601.
  * `correlation_id`: UUID4 cho mỗi lần chạy.
  * `duration_ms`: Thời gian thực thi tiến trình PowerShell (ms).
  * `stdout` và `stderr`: Bắt buộc cắt ngắn (`truncate`) tối đa 500 ký tự và gắn suffix `...[truncated]` để chống phình log khi PowerShell dump bảng dài.

## 4. TFT Game Guard Invariant
- `farm_preflight_daily_reset.py` kiểm tra danh sách tiến trình:
  - Nếu `League of Legends.exe` đang chạy (trong trận đấu 3D TFT thực tế) $\rightarrow$ **HỦY REBOOT NGAY (`ABORT`)** để bảo vệ ván cờ, không bị xử thua AFK.
  - Nếu chỉ mở Riot Client, `LeagueClient.exe` (ngoài sảnh / hàng chờ) hoặc không chơi game $\rightarrow$ **VẪN TIẾN HÀNH REBOOT BÌNH THƯỜNG**.
