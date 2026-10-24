# XiaoWei WinUSB Collision & PowerShell Pre-flight Triage (2026-10-23)

## 1. Triệu Chứng Hiện Trường & Cơ Chế Xung Đột
- **Hiện tượng:** Watchdog nuôi nick báo alert mất kết nối hàng loạt (>40 máy cùng lúc) với lỗi `Mất kết nối ADB/USB` hoặc `device not found`.
- **Nguyên nhân gốc rễ:** Ứng dụng Tiểu Vi (`放卫安卓投屏` / `xiaowei.exe`) chạy daemon ADB ngầm tại cổng TCP `5038`. Daemon này chiếm giữ độc quyền các endpoint WinUSB của Windows đối với farm điện thoại, khiến ADB server chính tại cổng `5037` không thể bind vào thiết bị.
- **Quy tắc điều phối:** Tuyệt đối không phán đoán lỗi cáp/hub phần cứng diện rộng khi số lượng máy rớt đột ngột tăng vọt. Bắt buộc kiểm tra probe socket cổng `5038` trước tiên:
  ```python
  import socket
  s = socket.socket(); s.settimeout(1)
  is_busy = (s.connect_ex(('127.0.0.1', 5038)) == 0); s.close()
  ```

## 2. Quy Trình Giải Phóng Khẩn Cấp (Emergency Recovery)
1. Dừng ứng dụng Tiểu Vi và ngắt server 5038:
   ```cmd
   taskkill /f /im xiaowei.exe
   "C:\Program Files (x86)\xiaowei\tools\adb.exe" -P 5038 kill-server
   ```
2. Chờ 1-2 giây để kernel Windows giải phóng hoàn toàn pipe WinUSB.
3. Chạy `python D:/Taadaa/tools/inspect_machine.py <N>` để xác nhận thiết bị tự động online trở lại trên ADB cổng 5037 mà không cần rút cắm cáp vật lý.

## 3. Cạm Bẫy Cú Pháp PowerShell Khi Viết Pre-flight Gate
1. **Cạm bẫy Array Wrapping với `$null`:**
   - Trong PowerShell, `@($null)` trả về mảng có độ dài là `1` chứa một phần tử rỗng (`.Count -eq 1`).
   - Nếu viết `@(Get-NetTCPConnection ... | Where-Object { $_ })`, khi không có kết nối trả về `$null`, `@($null)` sẽ bị tính là có 1 listener nếu không lọc rỗng cẩn thận.
   - **Khắc phục:** Luôn bọc điều kiện lọc rõ ràng:
     ```powershell
     $listeners = @(Get-NetTCPConnection -LocalPort 5038 -State Listen -ErrorAction Stop | Where-Object { $_ })
     ```
2. **Cạm bẫy toán tử logic trong lệnh:**
   - Cú pháp `if (Test-Path -LiteralPath $Adb -and $procs.Count -gt 0)` bị lỗi `ParameterBindingException: A parameter cannot be found that matches parameter name 'and'`.
   - **Khắc phục:** Bắt buộc đóng ngoặc đơn cụm lệnh cmdlet: `if ((Test-Path -LiteralPath $Adb) -and ($procs.Count -gt 0))`.
3. **Cơ chế ngoại lệ của `Get-NetTCPConnection`:**
   - Khi một cổng không có bất kỳ tiến trình nào lắng nghe, Windows PowerShell mặc định ném ngoại lệ CIM: `No matching MSFT_NetTCPConnection objects found`.
   - Không được dùng `-ErrorAction SilentlyContinue` vì sẽ nuốt chẩn đoán khi gặp lỗi quyền truy cập hoặc lỗi WMI hệ thống.
   - **Chuẩn hóa:** Dùng `-ErrorAction Stop` và bọc trong khối `try/catch`:
     ```powershell
     try {
         $listeners = @(Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction Stop | Where-Object { $_ })
     } catch {
         if ($_.Exception.Message -notlike "*No matching*") {
             throw "PORT_QUERY_ERROR: $($_.Exception.Message)"
         }
         $listeners = @()
     }
     ```
