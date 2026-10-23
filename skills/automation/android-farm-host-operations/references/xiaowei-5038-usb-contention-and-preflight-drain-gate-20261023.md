# Tranh Chấp Cổng ADB 5038 (Tiểu Vi), Bẫy Báo Mất Kết Nối Giả & Quy Chuẩn Preflight Drain Gate (23/10/2026)

## 1. Hiện Tượng & Bẫy Quy Chụp Sai Lệch (User Bắt Lỗi)
- **Báo mất kết nối diện rộng giả (False Positive USB Drop):**
  * Trong ca nuôi TikTok, watchdog báo cáo có tới 41 máy (M2, M4, M10, M11, M12...) bị "Mất kết nối ADB/USB".
  * Thực tế khi kiểm tra màn hình Tiểu Vi (`放卫安卓投屏 v9.11.147`), toàn bộ các máy đều đang sáng màn hình, stream video bình thường. Duy nhất chỉ có 5 máy (M10, M14, M30, M35, M36) thực sự hiển thị thông báo "Điện thoại đã ngắt kết nối".
- **Bản chất kỹ thuật tranh chấp USB Bus:**
  * Tiểu Vi chạy daemon riêng: `C:\Program Files (x86)\xiaowei\tools\adb.exe -P 5038`.
  * Trên Windows, WinUSB driver chỉ cho phép một endpoint độc quyền. Khi tiến trình ADB cổng 5038 mở stream 80 máy, nó chia rẽ interface và làm nghẽn trần băng thông USB 2.0 EHCI (35 MB/s).
  * Daemon ADB chuẩn của Farm chạy trên cổng `5037` bị đẩy ra ngoài, trả về `device not found` cho 20–40 máy ngẫu nhiên.
  * Bộ phân loại lỗi `classify_feed_failure` trong watchdog map bất kỳ lỗi `device not found` / `device offline` thành "Mất kết nối ADB/USB", dẫn đến bản báo cáo mù quáng quy chụp do phần cứng/cáp USB.

---

## 2. Điểm Mù Điều Phối (Root Cause)
1. **Bẫy Idle Threshold của Watchdog Tự Đóng:**
   * Script `xiaowei_idle_auto_close_watchdog.py` có ngưỡng `IDLE_THRESHOLD_SECONDS = 600` (10 phút).
   * Nếu người dùng vừa mở Tiểu Vi lên soi hoặc đang có thao tác chuột/phím, watchdog không bao giờ đóng Tiểu Vi.
2. **Thiếu Preflight Drain Gate trong Runner:**
   * Script khởi động ca nuôi (`tiktok_runner.py` / `run-feed-session.ps1`) đâm thẳng 80 luồng vào hệ thống mà không kiểm tra xem cổng 5038 có đang mở hay không.
   * Khi tài nguyên USB đang bị Tiểu Vi chiếm dụng, runner vẫn chạy mù và làm fail hàng loạt máy.

---

## 3. Quy Trình Cứu Hộ O(1) T0 Tại Hiện Trường
Khi phát hiện nghi vấn mất kết nối hàng loạt nhưng máy vẫn có điện / sáng màn hình:
1. **Kiểm tra cổng 5038:**
   ```python
   import socket
   s = socket.socket()
   is_open = (s.connect_ex(('127.0.0.1', 5038)) == 0)
   s.close()
   ```
2. **Hạ Tiểu Vi & Drain cổng 5038 ngay lập tức:**
   ```powershell
   # 1. Đóng GUI
   taskkill /F /IM xiaowei.exe 2>$null
   # 2. Hạ ADB server cổng 5038
   & "C:\Program Files (x86)\xiaowei\tools\adb.exe" -P 5038 kill-server
   # 3. Đợi 2s để Windows trả USB endpoint về cổng 5037
   Start-Sleep -Seconds 2
   ```
3. **Kiểm chứng phục hồi bằng `inspect_machine.py <N>`:**
   * Chạy kiểm tra các máy vừa bị báo lỗi (M2, M4, M11, M21...). Các máy sẽ lập tức trả về `SM-G930...`, pin, proxy và focus đầy đủ mà không cần đụng vào phần cứng.

---

## 4. Chuẩn Hóa Preflight Drain Gate Trong Runner
Mọi runner ca nuôi (`run-feed-session.ps1` hoặc wrapper Python) bắt buộc chèn block Preflight kiểm tra trước khi spawn bất kỳ worker nào:
```powershell
# Pre-flight: Giai phong cong 5038 / XiaoWei de tranh chia re USB va gay mat ket noi ADB
try {
    $xw = Get-Process -Name "xiaowei" -ErrorAction SilentlyContinue | Where-Object { $_.Path -like "*xiaowei*" }
    if ($xw) { Stop-Process -InputObject $xw -Force -ErrorAction SilentlyContinue }
    $xwPorts = @(Get-NetTCPConnection -LocalPort 5038 -State Listen -ErrorAction SilentlyContinue | ForEach-Object {
        $proc = Get-Process -Id $_.OwningProcess -ErrorAction SilentlyContinue
        if ($proc -and ($proc.Path -like "*xiaowei*" -or $proc.Name -eq "adb")) { $proc.Id }
    } | Where-Object { $_ })
    if ($xwPorts) {
        $xwAdb = "C:\Program Files (x86)\xiaowei\tools\adb.exe"
        if (Test-Path -LiteralPath $xwAdb) { & $xwAdb -P 5038 kill-server 2>&1 | Out-Null }
        foreach ($pidToKill in $xwPorts) { Stop-Process -Id $pidToKill -Force -ErrorAction SilentlyContinue }
        Start-Sleep -Seconds 2
    }
    $p5038 = Get-NetTCPConnection -LocalPort 5038 -State Listen -ErrorAction SilentlyContinue
    if ($p5038) { Write-Warning "[PRE-FLIGHT] Port 5038 still in LISTEN state" }
} catch {
    Write-Warning "[PRE-FLIGHT] XiaoWei/port 5038 cleanup warning: $($_.Exception.Message)"
}
```

---

## 5. Bẫy Thẩm Định Closeout Gate & Chuẩn Hóa An Toàn Farm
Khi đưa bản vá Preflight Drain Gate vào review chấm điểm Closeout Gate:
1. **Xác minh định danh tiến trình (Process Identity):**
   - Tuyệt đối CẤM dừng mù quáng mọi PID nghe trên cổng 5038.
   - Bắt buộc kiểm tra `($proc.Path -like "*xiaowei*" -or $proc.Name -eq "adb")` để tránh dừng nhầm các dịch vụ hệ thống khác.
2. **Kiểm tra hậu điều kiện (Post-condition Verification):**
   - Phải có bước đọc lại `Get-NetTCPConnection -LocalPort 5038 -State Listen` sau khi kill server để xác nhận cổng đã thực sự đóng.
3. **Bẫy Telemetry va chạm Launcher Contract:**
   - Trong `run-feed-session.ps1`, test launcher (`test_run_feed_session_config.py`) parse dòng `[TELEMETRY_METRIC]` đầu tiên để lấy payload `feed_session_launch`.
   - CẤM tự ý phát dòng `[TELEMETRY_METRIC]` trong preflight cleanup khi không có sự cố, vì sẽ làm gãy các test contract phụ thuộc phía sau.
   - Chỉ dùng `Write-Warning` hoặc `Write-Host "[PRE-FLIGHT] ..."` cho nhánh thông tin tiền trạm.
4. **Ngân sách O(1) <= 30 dòng:**
   - Logic cleanup trong PowerShell phải súc tích, gói gọn trong 18-20 dòng để cùng với file test không vượt quá trần 30 dòng git diff numstat.
