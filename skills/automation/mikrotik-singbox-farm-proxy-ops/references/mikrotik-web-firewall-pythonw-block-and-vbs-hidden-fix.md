# MikroTik Web (:2310) Windows Firewall Block via pythonw.exe & Hidden VBS Fix

## 1. Triệu chứng Sự cố (2026-11-03)
- Giao diện TikTok Farm Dashboard (`kibe:1905`) có tab "Quản Lý Proxy" nhúng iframe tới `http://kibe:2310/` (MikroTik Web).
- Khi mở trên điện thoại (qua Tailscale hoặc Wi-Fi LAN), tab MikroTik bị trắng tinh, kẹt ở dòng chữ *"Đang kết nối MikroTik Web..."*.
- Kiểm tra trên máy host Kibe: `http://127.0.0.1:2310` vẫn phản hồi HTTP 200 (17.8 KB), server không bị crash.

## 2. Nguyên nhân gốc rễ (Root Cause)
1. **Windows Firewall Rule `Action=Block` trên `pythonw.exe`:**
   - Script khởi động trong Windows Startup (`run_hidden.vbs`) gọi:
     `WshShell.Run "cmd /c pythonw.exe """ & serverPath & """", 0, False`
   - Lệnh `pythonw.exe` không truyền đường dẫn tuyệt đối nên Windows ưu tiên lấy `C:\Users\Kibe\AppData\Local\Programs\Python\Python312\pythonw.exe` từ biến môi trường `PATH`.
   - Trước đây trong Windows Firewall, tiến trình `Python312\pythonw.exe` bị lưu một rule chặn cứng:
     `Action=Block|Dir=In|App=...\Python312\pythonw.exe`
   - Do đó, mọi request từ mạng ngoài (LAN `192.168.110.x` hoặc Tailscale `100.x.x.x`) gửi tới cổng 2310 đều bị Windows Firewall drop gói TCP SYN trong im lặng. Localhost truy cập được nhưng điện thoại bị drop packet hoàn toàn.
2. **`python.exe` thì có `Action=Allow`:**
   - Trong khi đó, `Python312\python.exe` lại có sẵn rule `Action=Allow|Dir=In` trên firewall.

## 3. Cách khắc phục chuẩn
1. **Chuyển `run_hidden.vbs` sang `python.exe`:**
   ```vbscript
   Set WshShell = CreateObject("WScript.Shell")
   WshShell.Run "cmd /c python.exe """ & serverPath & """", 0, False
   ```
   *Lưu ý:* Tham số `0` trong `WshShell.Run` là hằng số `SW_HIDE`, đảm bảo tiến trình `python.exe` chạy ngầm 100% không bật cửa sổ console CMD nào trên màn hình, đồng thời được hưởng rule `Action=Allow` của Windows Firewall.
2. **Bỏ mã lệnh mở trình duyệt tự động trong `server.py`:**
   Xóa khối lệnh `webbrowser.open(f"http://localhost:{port}")` trong hàm `main()` để khi khởi động máy không tự động bung tab Chrome thừa thãi.
3. **Phân định kiến trúc:**
   Người dùng chỉ cần bookmark và truy cập Dashboard tập trung `kibe:1905` (tab Quản Lý Proxy). Cổng `kibe:2310` giữ vai trò backend service chạy ngầm, không cần mở trực tiếp.
