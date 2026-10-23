# Preflight Port 5038 Drain & Chẩn Đoán Lỗi Báo Mù "Mất Kết Nối ADB/USB" (23/10/2026)

## 1. Hiện Tượng Thực Tế & Bẫy Báo Mù Của Watchdog
- **Hiện trường sự cố:** Sau Ca 1 Phiên 2 (Sáng) ngày 23/10/2026, watchdog báo cáo 41/80 máy trên Farm Kibe bị "Mất kết nối ADB/USB" (M2, M4, M11, M12, M13, M16, M18, M21, M22, M23...).
- **Đối soát màn hình thực tế (XiaoWei):** User mở Tiểu Vi (`放卫安卓投屏 v9.11.147`) thấy 80 máy vẫn sáng màn hình và truyền frame bình thường; chỉ có đúng 5 máy (M10, M14, M30, M35, M36) thực sự ngắt kết nối vật lý.
- **Bản chất kỹ thuật (USB Endpoint Starvation):**
  * Tiểu Vi chạy tiến trình con `adb.exe -P 5038` độc chiếm các pipe WinUSB và ăn trần băng thông USB 2.0 EHCI (35 MB/s).
  * ADB server chuẩn của farm (`port 5037`) bị từ chối truy cập vào các endpoint USB của thiết bị $\rightarrow$ trả về `device not found` hoặc `device offline`.
  * Bộ phân loại lỗi trong watchdog (`classify_feed_failure`) chỉ dựa vào chuỗi `device not found` để gán nhãn "Mất kết nối ADB/USB" $\rightarrow$ dẫn đến kết luận sai bản chất, báo động giả toàn farm.

---

## 2. Điểm Mù Kiến Trúc: Tại Sao Script Không Tự Kill?
1. **Giới hạn của Idle Watchdog:**
   * `xiaowei_idle_auto_close_watchdog.py` được thiết kế chỉ đóng khi máy nhàn rỗi (idle) >= 10 phút (600s).
   * Khi người dùng vừa mở Tiểu Vi lên xem hoặc cửa sổ còn active, idle watchdog tuyệt đối không can thiệp.
2. **Thiếu Pre-flight Gate ở tầng Runner:**
   * Trình điều phối chạy feed (`run-feed-session.ps1` và `tiktok_runner.py`) đến giờ ca chạy là spawn đồng loạt các worker đâm thẳng vào cổng 5037 mà hoàn toàn không có bước tiền kiểm (Preflight) để giải phóng tranh chấp USB bus.

---

## 3. Chuẩn Hóa Pre-flight Port 5038 Drain
Bắt buộc tích hợp vào đầu mọi script runner (`run-feed-session.ps1`) và bộ tiền kiểm thiết bị (`pre_session_device_gate.py`):

### A. Triển khai trong PowerShell (`run-feed-session.ps1`):
```powershell
# Pre-flight: Giai phong cong 5038 / XiaoWei de tranh chia re USB va gay mat ket noi ADB
if (Get-Process -Name "xiaowei" -ErrorAction SilentlyContinue) {
    Write-Host "[PRE-FLIGHT] Phat hien XiaoWei dang chay, tien hanh dong de giai phong USB bus..."
    Stop-Process -Name "xiaowei" -Force -ErrorAction SilentlyContinue
}
$xwPorts = @(Get-NetTCPConnection -LocalPort 5038 -State Listen -ErrorAction SilentlyContinue | ForEach-Object { [int]$_.OwningProcess })
if ($xwPorts) {
    Write-Host "[PRE-FLIGHT] Phat hien cong ADB 5038 dang mo (PID: $($xwPorts -join ',')), tien hanh giai phong..."
    $xwAdb = "C:\Program Files (x86)\xiaowei\tools\adb.exe"
    if (Test-Path -LiteralPath $xwAdb) {
        & $xwAdb -P 5038 kill-server 2>&1 | Out-Null
    }
    foreach ($p in $xwPorts) {
        $proc = Get-Process -Id $p -ErrorAction SilentlyContinue
        # Xác minh danh tính: chỉ dừng nếu là adb hoặc tiến trình trong thư mục xiaowei
        if ($proc -and ($proc.ProcessName -eq "adb" -or ($proc.Path -and $proc.Path -like "*xiaowei*"))) {
            Stop-Process -Id $p -Force -ErrorAction SilentlyContinue
        }
    }
    Start-Sleep -Seconds 2
    # Hậu kiểm: xác nhận cổng 5038 đã thực sự được giải phóng
    $stillOpen = Get-NetTCPConnection -LocalPort 5038 -State Listen -ErrorAction SilentlyContinue
    if (-not $stillOpen) {
        Write-Host "[PRE-FLIGHT] Giai phong cong ADB 5038 thanh cong."
    } else {
        Write-Warning "[PRE-FLIGHT] Cong ADB 5038 van con listener sau cleanup!"
    }
}
```

### B. Triển khai trong Python (`pre_session_device_gate.py`):
```python
def ensure_adb_port_5038_clean() -> None:
    """Đảm bảo XiaoWei và cổng 5038 đã được dọn sạch để không tranh chấp WinUSB."""
    try:
        import socket
        s = socket.socket()
        s.settimeout(0.5)
        if s.connect_ex(("127.0.0.1", 5038)) == 0:
            s.close()
            subprocess.run(["taskkill", "/F", "/IM", "xiaowei.exe"], capture_output=True, timeout=5)
            xw_adb = r"C:\Program Files (x86)\xiaowei\tools\adb.exe"
            if os.path.isfile(xw_adb):
                subprocess.run([xw_adb, "-P", "5038", "kill-server"], capture_output=True, timeout=5)
            _time.sleep(2.0)
        else:
            s.close()
    except Exception:
        pass
```

---

## 4. Tiêu Chuẩn Thẩm Định Closeout Gate
Khi đưa bản vá dọn tiến trình/port qua Closeout Gate:
1. **Kiểm tra định danh tiến trình:** CẤM dừng mù PID nghe cổng 5038 nếu không chứng minh được đó là `adb` hoặc thuộc `xiaowei` (chống tác dụng phụ ngoài ý muốn).
2. **Kiểm tra hậu điều kiện (Post-condition check):** Bắt buộc có bước kiểm tra socket / TCP Connection sau khi kill để xác nhận cổng đã thực sự đóng (`stillOpen == False`).
3. **Telemetry & Logging:** Ghi nhận rõ ràng trạng thái thành công/cảnh báo ra stdout/telemetry thay vì nuốt lỗi bằng `Out-Null` âm thầm.
4. **Focused Test:** Chạy test focused `test_run_feed_session_config.py` và `test_tiktok_runner_healing.py` đảm bảo không phá vỡ hợp đồng CLI và pre-session gate.
