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
   $xwConn = Get-NetTCPConnection -LocalPort 5038 -State Listen -ErrorAction SilentlyContinue
   if ($xwConn) {
       Write-Host "[PRE-FLIGHT] Port 5038 occupied (PID $($xwConn[0].OwningProcess)), running kill-server..."
       $xw = "C:\Program Files (x86)\xiaowei\tools\adb.exe"
       if (-not (Test-Path -LiteralPath $xw)) { $xw = (Get-Command adb -ErrorAction SilentlyContinue).Source }
       if ($xw) { try { & $xw -P 5038 kill-server *>$null } catch {} }
       Start-Sleep -Seconds 1
       if (Get-NetTCPConnection -LocalPort 5038 -State Listen -ErrorAction SilentlyContinue) {
           throw "PREFLIGHT_PORT_5038_BLOCKED: Port 5038 remains occupied after kill-server attempt."
       }
   }
   ```
   * **Nguyên tắc an toàn Farm:** CẤM dùng `Stop-Process -Force` quét PID tùy tiện vì có thể giết nhầm tiến trình ngoài ý muốn và trượt Closeout Gate. CHỈ dùng lệnh chính thống `adb -P 5038 kill-server` thông qua binary của XiaoWei hoặc fallback `(Get-Command adb).Source`.
   * **Fail-Closed:** Nếu sau khi kill-server mà cổng 5038 vẫn ở trạng thái LISTEN, script BẮT BUỘC throw lỗi `PREFLIGHT_PORT_5038_BLOCKED` để dừng toàn bộ ca, bảo vệ bus USB và không để 80 workers đâm đầu vào thất bại.
