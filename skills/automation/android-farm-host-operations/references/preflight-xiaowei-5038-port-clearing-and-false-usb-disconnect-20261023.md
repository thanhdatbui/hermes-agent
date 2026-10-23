# Cơ Chế Pre-flight Dọn Cổng 5038 / XiaoWei & Chống Báo Sai "Mất Kết Nối ADB/USB" Hàng Loạt (23/10/2026)

## 1. Hiện Tượng Thực Tế & Điểm Mù Giám Sát (Bẫy XiaoWei Port 5038)
- Khi người dùng mở Tiểu Vi (XiaoWei / 牧卫) lên xem màn hình hoặc bị kẹt chạy ngầm:
  * Tiến trình `adb.exe -P 5038` độc chiếm các pipe WinUSB và nghẽn băng thông USB 2.0 EHCI của 80 máy.
  * Cổng chuẩn `5037` của hệ thống nuôi acc bị chia rẽ, mất kết nối thiết bị và trả về `device '...' not found`.
  * Watchdog `feed_session_watchdog.py` gom toàn bộ lỗi `device not found` thành nhãn **"Mất kết nối ADB/USB (41 máy)"**.
  * **Hậu quả:** Báo động giả nghiêm trọng trong khi toàn bộ dàn máy trên thực tế vẫn cắm cáp, sáng màn hình và truyền frame bình thường trên giao diện Tiểu Vi.

## 2. Nguyên Tắc Điều Phối Bắt Buộc (Anti-False-Alarm)
1. **Cấm Báo Lỗi Mù Khi Chưa Kiểm Tra Port 5038:**
   - Khi phát hiện đồng loạt > 10 máy bị `not found` hoặc `device offline` trên cụm Kibe hoặc Admin:
   - **BƯỚC 1:** Lập tức kiểm tra cổng 5038: socket probe `127.0.0.1:5038` (hoặc `192.168.110.119:5038` trên Admin).
   - Nếu cổng 5038 đang LISTEN -> 100% là do XiaoWei chiếm giữ, TUYỆT ĐỐI CẤM báo "mất kết nối vật lý/rút cáp".
2. **Cưỡng Chế Giải Phóng Cổng 5038 Tức Thì:**
   - Terminate `xiaowei.exe` (kiểm tra `Path -like "*xiaowei*"`).
   - Gọi `adb.exe -P 5038 kill-server`.
   - Nếu còn tiến trình listener mồ côi: kill process sở hữu nếu thuộc `xiaowei` hoặc `adb.exe`.
   - Sleep 1–2 giây để Windows hoàn tất rebind WinUSB pipe về cổng chuẩn 5037.
   - Thử lại `inspect_machine.py <N>` để xác nhận thiết bị hồi sinh.

## 3. Kiến Trúc Pre-flight Gate Trong Code Vận Hành
1. **Trong `scripts/run-feed-session.ps1`:**
   - Tích hợp hàm `Clear-XiaoWeiPort5038`:
     ```powershell
     function Clear-XiaoWeiPort5038 {
         $res = [ordered]@{ Port = 5038; InitiallyOccupied = $false; ProcessesStopped = @(); CleanupSucceeded = $true; CleanupFailureReason = $null }
         if (-not (Get-NetTCPConnection -LocalPort 5038 -State Listen -ErrorAction SilentlyContinue)) { return [pscustomobject]$res }
         $res.InitiallyOccupied = $true; Get-Process -Name 'xiaowei' -ErrorAction SilentlyContinue | Where-Object { $_.Path -like '*xiaowei*' } | ForEach-Object { Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue; $res.ProcessesStopped += $_.Id }
         $xw = "C:\Program Files (x86)\xiaowei\tools\adb.exe"; if (Test-Path -LiteralPath $xw) { & $xw -P 5038 kill-server 2>&1 | Out-Null }
         @(Get-NetTCPConnection -LocalPort 5038 -State Listen -ErrorAction SilentlyContinue | ForEach-Object {
             $p = Get-Process -Id $_.OwningProcess -ErrorAction SilentlyContinue
             if ($p -and ($p.Path -like '*xiaowei*' -or $p.Path -like '*adb*')) {
                 Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue; $res.ProcessesStopped += $p.Id
             }
         })
         Start-Sleep -Seconds 1; if (Get-NetTCPConnection -LocalPort 5038 -State Listen -ErrorAction SilentlyContinue) {
             $res.CleanupSucceeded = $false; $res.CleanupFailureReason = 'Port 5038 still has active listeners'
         }
         return [pscustomobject]$res
     }
     $cleanupResult = Clear-XiaoWeiPort5038; if (-not $cleanupResult.CleanupSucceeded) { throw "PREFLIGHT_PORT_5038_BLOCKED: $($cleanupResult.CleanupFailureReason)" }
     ```
   - **Fail-closed:** Nếu cổng 5038 không thể giải phóng, ném ngoại lệ dừng phiên feed ngay lập tức, ngăn chặn việc spawn 80 worker lao vào bus USB đang nghẽn.
2. **Trong `pre_session_device_gate.py`:**
   - Hàm `filter_healthy_machines()` gọi `ensure_adb_port_5038_clean()` trước khi thăm dò `get-state` của bất kỳ máy nào.

## 4. Quy Chuẩn Vượt Closeout Gate Cho Code PowerShell Pre-flight
- **Tách Hàm Rõ Ràng:** Logic cleanup phải đóng gói thành hàm trả về structured object (`[pscustomobject]$res`) có các trường `InitiallyOccupied`, `ProcessesStopped`, `CleanupSucceeded`, `CleanupFailureReason`.
- **Behavioral Test Trong Pytest:** Bắt buộc có test thực thi hàm PowerShell qua `subprocess.run(["powershell", "-NoProfile", "-Command", ...])` và parse kết quả JSON để assert `CleanupSucceeded == True` thay vì chỉ assert chuỗi text đơn thuần.
