# Hermes Gateway Watchdog Exit=128 Failure Cascade & Fix

## Bối cảnh sự cố (2026-09-23)
- **Triệu chứng**: Hermes Gateway (Telegram bot) bị đơ, không nhận được tin nhắn inbound từ người dùng trong suốt ~1 tiếng (21:46 → 22:44).
- **Log `hermes-gateway-watchdog/watchdog.log`**:
  ```text
  21:46 -> 22:42 WATCHDOG_ERROR line=42 command=if ($terminationFailure) { throw $terminationFailure } message=taskkill failed for PID ..., exit=128
  ```
  Lặp lại liên tục mỗi 2 phút, watchdog không khởi động lại được Gateway.

## Cơ chế lỗi cốt lõi
1. Khi OmniRoute bị nghẽn (499 request storm / heavy load), tiến trình Hermes Gateway gửi request sang OmniRoute và bị treo (hung).
2. Script `D:\Taadaa\AI-Tools\tools\hermes-gateway-watchdog\hermes-gateway-watchdog.ps1` kiểm tra Gateway thấy không phản hồi hoặc timeout 45s lúc start, liền gọi `Stop-ChildProcessBounded` để dập tiến trình cũ bằng `taskkill.exe /PID <pid> /T /F`.
3. Nếu tiến trình đã tự exit trước hoặc PID không còn tồn tại, Windows `taskkill.exe` trả về `exit=128` ("process not found").
4. Tại dòng 29–31:
   ```powershell
   elseif ($killer.ExitCode -ne 0) {
       $terminationFailure = "taskkill failed for PID $($Process.Id), exit=$($killer.ExitCode)"
   }
   ```
   Và dòng 42:
   ```powershell
   if ($terminationFailure) { throw $terminationFailure }
   ```
   Script quăng exception unconditionally. Luồng thực thi nhảy vào khối `catch`, ghi log `WATCHDOG_ERROR` và `exit 1` mà KHÔNG chạy xuống khối khởi động Gateway mới.
5. Watchdog rơi vào crash-loop vô tận mỗi khi gặp tiến trình đã thoát.

## Giải pháp dứt điểm
Trong hàm `Stop-ChildProcessBounded`:
- Kiểm tra `$Process.HasExited`: nếu tiến trình đã thoát thì việc kill đã đạt mục đích.
- Nếu `$killer.ExitCode -eq 128` (hoặc process đã dead), coi như thành công và xóa `$terminationFailure = $null`.
- Chỉ throw khi tiến trình thực sự còn sống sau cả 2 bước taskkill và PowerShell Stop-Process fallback.
