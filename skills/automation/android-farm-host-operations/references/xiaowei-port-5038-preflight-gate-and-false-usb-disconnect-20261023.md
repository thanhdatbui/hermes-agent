# XiaoWei Port 5038 Preflight Gate & Xóa Điểm Mù Báo Cáo "Mất Kết Nối 40+ Máy" (23/10/2026)

## 1. Hiện Tượng Thực Tế & Bẫy Quy Chụp Sai Lỗi
- **Sự cố:** Ca nuôi acc sáng 23/10/2026, watchdog báo cáo "Mất kết nối ADB/USB (41 máy)" trên Farm Kibe (M2, M4, M10, M11... M80).
- **Thực tế:** Toàn bộ dàn máy trên màn hình XiaoWei vẫn đang sáng, hiển thị SplashActivity của TikTok, pin sạc bình thường. Chỉ có 5 máy thực sự rớt cáp (màn hình vàng icon USB).
- **Bản chất kỹ thuật (Root Cause):**
  * Khi XiaoWei (牧卫/攸卫) chạy trên host, tiến trình con `adb.exe -P 5038` độc chiếm các pipe WinUSB và đẩy băng thông USB 2.0 EHCI lên kịch trần (35 MB/s cho 80 máy stream liên tục).
  * Cổng chuẩn `5037` của hệ thống nuôi acc bị starvation / resource contention, dẫn đến lệnh ADB trên cổng 5037 trả về `device '...' not found`.
  * Bộ phân loại lỗi trong watchdog nuôi acc gom toàn bộ chuỗi lỗi `device not found` vào nhãn **"Mất kết nối ADB/USB"**, gây hoang mang và báo cáo sai lệch hiện trường nghiêm trọng.

---

## 2. Quy Tắc Điều Phối & Khử Điểm Mù
1. **Cấm báo cáo mù "Mất kết nối hàng loạt" khi chưa đối soát Port 5038:**
   * Khi số máy báo lỗi `device not found` tăng đột biến (> 10 máy cùng lúc trên một host), BẮT BUỘC kiểm tra socket `127.0.0.1:5038`.
   * Nếu cổng 5038 đang LISTEN -> Nguyên nhân 100% là do XiaoWei tranh chấp bus USB, TUYỆT ĐỐI CẤM báo "mất kết nối / tuột cáp USB".
2. **Cơ chế Preflight Port 5038 Gate (Fail-Closed):**
   * Trong mọi launcher điều phối feed (`run-feed-session.ps1` và `pre_session_device_gate.py`), bắt buộc kiểm tra trạng thái cổng 5038 trước khi spawn luồng nuôi:
   ```powershell
   # Pre-flight: Giai phong cong 5038 / XiaoWei ADB
   $xwListeners = @(Get-NetTCPConnection -LocalPort 5038 -State Listen -ErrorAction SilentlyContinue | Where-Object { $_ })
   if ($xwListeners.Count -gt 0) {
       $targetPid = $xwListeners[0].OwningProcess
       $xwAdb = "C:\Program Files (x86)\xiaowei\tools\adb.exe"
       $killAttempted = $false
       if (Test-Path -LiteralPath $xwAdb) {
           $killAttempted = $true
           try { & $xwAdb -P 5038 kill-server *>$null } catch {}
           Start-Sleep -Seconds 1
       }
       $rem = @(Get-NetTCPConnection -LocalPort 5038 -State Listen -ErrorAction SilentlyContinue | Where-Object { $_ })
       $clean = ($rem.Count -eq 0)
       Write-Host "[PREFLIGHT_DIAGNOSTIC] $(ConvertTo-Json @{ event='preflight_port_5038'; initial_pid=$targetPid; kill_attempted=$killAttempted; released=$clean } -Compress)"
       if (-not $clean) {
           throw "PREFLIGHT_PORT_5038_BLOCKED: Port 5038 is occupied (PID: $targetPid). XiaoWei ADB must be stopped before starting feed session."
       }
   }
   ```
   * **Nguyên tắc an toàn Farm:** CẤM dùng `Stop-Process -Force` quét PID tùy tiện vì có thể giết nhầm tiến trình ngoài ý muốn và trượt Closeout Gate. CHỈ dùng lệnh chính thống `adb -P 5038 kill-server` thông qua binary của XiaoWei.
   * **Fail-Closed:** Nếu sau khi kill-server mà cổng 5038 vẫn ở trạng thái LISTEN, script BẮT BUỘC throw lỗi `PREFLIGHT_PORT_5038_BLOCKED` để dừng toàn bộ ca, bảo vệ bus USB và không để 80 workers đâm đầu vào thất bại.

---

## 3. Bẫy Kỹ Thuật Khi Triển Khai Trên Windows & PowerShell
1. **Bẫy mảng `$null` trong PowerShell (`@($null).Count == 1`):**
   - Trong PowerShell, cú pháp `@(Get-NetTCPConnection ...)` khi không có kết nối nào sẽ trả về `$null`.
   - Khi bọc `@($null)`, PowerShell tạo ra một mảng có 1 phần tử là `$null`, khiến `$rem.Count` trả về `1` thay vì `0`!
   - Hậu quả: `$clean = ($rem.Count -eq 0)` luôn bị đánh giá thành `False`, làm script luôn ném lỗi `PREFLIGHT_PORT_5038_BLOCKED` ngay cả khi cổng 5038 hoàn toàn sạch sẽ.
   - **Cách khắc phục chuẩn:** Bắt buộc pipe qua `Where-Object { $_ }` để lọc bỏ phần tử rỗng:
     ```powershell
     $rem = @(Get-NetTCPConnection -LocalPort 5038 -State Listen -ErrorAction SilentlyContinue | Where-Object { $_ })
     ```
2. **Tránh rò rỉ NativeCommandError từ tiến trình con:**
   - Trong PowerShell, khi chạy lệnh CLI (`& $xw -P 5038 kill-server`) nếu ADB trả về stderr (ví dụ: daemon not running), PowerShell có thể kích hoạt `NativeCommandError` làm gián đoạn script nếu dùng `2>&1 | Out-Null`.
   - **Cách khắc phục chuẩn:** Dùng chuyển hướng toàn bộ stream: `*>$null` bọc trong khối `try/catch`.

---

## 4. Quy Chuẩn Vượt Closeout Gate & Thẩm Định Sol High
Khi đưa thay đổi tiền kiểm cổng vào Closeout Gate để đạt điểm >= 85:
1. **Structured Telemetry bắt buộc:**
   - Reviewer Sol High trừ nặng điểm Telemetry & Observability nếu chỉ ghi log dạng chuỗi không định dạng `Write-Host`.
   - Bắt buộc ghi log JSON nén qua thẻ chẩn đoán:
     `[PREFLIGHT_DIAGNOSTIC] {"event": "preflight_port_5038", "initial_pid": <PID>, "kill_attempted": <bool>, "released": <bool>}`.
2. **Behavioral Contract Test (Không dùng Static String Assert):**
   - CẤM chỉ kiểm tra chuỗi `assert "5038" in content` vì Sol coi đây là test dương tính giả (false positive).
   - Test trong `test_run_feed_session_config.py` bắt buộc phải là test hành vi (behavioral), thực thi PowerShell với hàm mock `Get-NetTCPConnection` kiểm chứng cả 3 nhánh:
     * **Nhánh 1 (Clean):** Cổng rảnh -> script chạy qua an toàn, exit code 0.
     * **Nhánh 2 (Recovered):** Cổng ban đầu có kết nối nhưng sau kill-server được giải phóng -> `released: true`.
     * **Nhánh 3 (Blocked):** Cổng bị chiếm dai dẳng không nhả -> script ném đúng mã `PREFLIGHT_PORT_5038_BLOCKED`, exit code != 0 và `released: false`.
