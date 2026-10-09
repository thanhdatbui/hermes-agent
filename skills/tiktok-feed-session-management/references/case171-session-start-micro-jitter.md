# Case 171 & Anti-Clustering Architecture Reference (14/09/2026)

## 1. Vấn Đề Kỹ Thuật (Anti-Clustering & Periodic Deterministic Anomaly)
- **Cảnh báo từ Risk Engine AI (GPT-5.6 Sol High Reasoning):**
  - Khi 160 thiết bị Android (Samsung Galaxy S7) cùng kích hoạt tại các mốc giờ chẵn cố định (`06:00:00`, `08:00:00`, `12:00:00`, `14:00:00`...), hệ thống phòng thủ của ByteDance (`libmetasec_ml.so`) nhận diện ngay "nhịp tim cơ học" (Deterministic Timetable).
  - Nguy cơ: Gom cụm 160 máy thành một Farming Cluster do có sự đồng bộ tuyệt đối về thời gian bắt đầu và kết thúc phiên.

## 2. Ranh Giới An Toàn Bất Biến (Invariant Boundaries)
- **TUYỆT ĐỐI KHÔNG SỬA LỊCH CRON HỆ THỐNG / HERMES JOBS:**
  - `tiktok_picker.py` khóa cứng khung giờ `02:00 - 05:59` là **Silent Window (Vùng chết cấm chạy)**. Nếu cron bị jitter âm chạy trước 06:00 (ví dụ 05:50) -> Picker nuốt toàn bộ Ca sáng, không máy nào được chạy.
  - `feed_session_watchdog.py` phân chia khung quét cứng theo `SESSION_WINDOWS` (Ca 1 bắt đầu 06:00, Ca 4 kết thúc 06:00). Nếu runner chạy trước 06:00 -> Watchdog gán kết quả vào Ca đêm hôm trước; khi đến 08:00 quét không thấy file run sẽ bắn nhầm Farm Alert ĐỎ (-5373649734).
  - Chuỗi Watchdog phía sau (`post-morning-gmail-2fa-watchdog` lúc 08:00, `post-noon-chain-watchdog` lúc 14:00) dựa vào các mốc chẵn để bắt đầu quét thiết bị rảnh.

## 3. Giải Pháp Chuẩn: Micro-Jitter Nội Bộ Trong PowerShell (`run-feed-session.ps1`)
- **Vị trí tích hợp:** `D:/Taadaa/tiktok-luot nuoi acc/scripts/run-feed-session.ps1`.
- **Cơ chế hoạt động:**
  1. Cron gọi `tiktok_runner.py` đúng giờ chẵn (ví dụ `06:00:02`).
  2. Tiến trình PowerShell `run-feed-session.ps1` được tạo -> Cờ `is_feed_runner_active()` lập tức chuyển thành `True`. Watchdog phát hiện phiên đang chạy hợp lệ nên kiên nhẫn chờ, không bị timeout.
  3. Trước khi thực hiện ADB chạm vào chiếc điện thoại đầu tiên, PowerShell tự động ngủ ngẫu nhiên từ 1 đến 3 phút (`60s – 180s`):
     ```powershell
     $isRecoveryMode = ($effectiveSwipes -gt 0) -or ($RecoveryTestSwipes -gt 0) -or $PSBoundParameters.ContainsKey("RecoveryTestSwipes")
     if ($Run -and -not $DisableSessionJitter -and -not $isRecoveryMode -and $SessionJitterMaxSeconds -gt 0) {
         $minJitter = [Math]::Min($SessionJitterMinSeconds, $SessionJitterMaxSeconds)
         $maxJitter = [Math]::Max($SessionJitterMinSeconds, $SessionJitterMaxSeconds)
         $sessionJitterSec = if ($minJitter -eq $maxJitter) { $minJitter } else { Get-Random -Minimum $minJitter -Maximum ($maxJitter + 1) }
         if ($sessionJitterSec -gt 0) {
             Write-Host "Applying natural session start jitter: sleeping $sessionJitterSec s before launching devices (use -DisableSessionJitter to skip)..."
             Start-Sleep -Seconds $sessionJitterSec
         }
     }
     ```
  4. Sau khi kết thúc micro-jitter, 40 máy tiếp tục khởi động so le từ 2s đến 8s (`MachineStartStaggerMs: 2000,8000`).
  5. Khi chạy test hoặc recovery (`-RecoveryTestSwipes` hoặc `-DisableSessionJitter`), jitter được tự động bypass để phục vụ debug tức thì.

## 4. Kiểm Thử & Nghiệm Thu
- Tham số được guard bằng `[ValidateRange(0, 600)]` và kiểm tra `SessionJitterMinSeconds <= SessionJitterMaxSeconds`.
- Syntax preview an toàn: `powershell -NoProfile -ExecutionPolicy Bypass -File run-feed-session.ps1 -Row 1 -Machines 19 -SkipAccountWorkbookSync` -> Exit 0.
- Được thẩm định độc lập bởi GPT-5.6 Sol High Reasoning (`VERDICT: APPROVED`).

## 5. Q&A Tối Ưu Lịch Trình & Tần Suất Thực Tế (Sol Audit 2026-10-07)
- **Hỏi: Có nên tăng Session Jitter từ 1–3 phút lên 3–5 phút không?**
  - **Đáp:** TUYỆT ĐỐI KHÔNG. Dải 1–3 phút (60s–180s) kết hợp stagger 2s–8s đã đủ hoàn toàn để phá vỡ chữ ký giờ tròn `:00`. Tăng lên 3–5 phút sẽ kéo dài phiên, đẩy thời gian kết thúc sát giờ của Phiên 2 (đặc biệt Ca 4 cách Ca 1 chỉ 90 phút: 00:00 và 01:30), dẫn đến Watchdog quét trúng grace period và báo động giả (False Alarm) đỏ cả dàn máy.
- **Hỏi: Có nên tăng số phiên lướt feed lên 3 phiên/ca hoặc đổi lịch không?**
  - **Đáp:** KHÔNG. Cấu trúc hiện tại (4 ca × 2 phiên/ngày, luân phiên ngày chẵn/lẻ) đạt chuẩn vàng:
    - 1 máy chạy 4 nick/ngày × 2 phiên = 8 phiên/máy/ngày.
    - Mỗi phiên 7–8 phút → Tổng thời gian sáng màn hình ~64 phút/ngày (< 1.1 giờ).
    - Máy S7 idle nghỉ sâu hơn 22.8 giờ/ngày, bảo vệ pin và CPU tối đa.
    - Mỗi nick chạy 2 phiên (~15 phút/ngày), nghỉ 32–36 tiếng giữa các ngày chạy, mô phỏng chuẩn xác người dùng thật. Không nhồi thêm phiên thứ 3 vào ca.
