# Admin Farm Direct3D & Remote Hook Collision Resolution (2026-10-27)

## Bối cảnh sự cố
Khi điều khiển máy remote Windows (`admin-farm` / `192.168.110.119`) qua SSH hoặc background automation để khởi chạy game / ứng dụng DirectX / Vulkan (TFT, League of Legends, Unreal Engine, Unity games):
- Ứng dụng game bị crash ngay lập tức hoặc không thể kết nối lại vào trận (`Reconnect` button vô tác dụng hoặc client kẹt).
- Kiểm tra Windows Application Event Log xuất hiện lỗi:
  ```text
  Faulting application name: bad_module_info, version: 0.0.0.0
  Faulting module name: uvh64.dll_unloaded, version: 0.0.0.0
  Exception code: 0xc0000005 (Access Violation)
  ```
- Tiến trình báo lỗi của Windows (`WerFault.exe`) bị treo ngầm liên tục, cản trở các tiến trình game mới spawn hoặc phục hồi state.

## Nguyên nhân gốc rễ
- Các phần mềm điều khiển từ xa cũ như **UltraViewer** cài đặt display/input hook (`uvh64.dll`, `uv_x64.exe`) vào toàn bộ tiến trình có giao diện đồ họa.
- Khi game 3D khởi động hoặc chuyển đổi render context, module `uvh64.dll` bị unload đột ngột gây crash `c0000005` (Access Violation) trong subsystem đồ họa.
- Dịch vụ nền `UltraViewService` chạy ở chế độ `Auto` (Automatic Startup) sẽ liên tục spawn lại `UltraViewer_Service.exe` và nạp lại hook mỗi khi máy khởi động hoặc user đăng nhập.

## Quy chuẩn khắc phục triệt để (Không để tái diễn)
1. **Dọn sạch crash handler & tiến trình kẹt:**
   - Dùng script Python qua SSH chạy lệnh hủy tiến trình:
     ```python
     for proc in ['WerFault.exe', 'TFTClient-Win64-Shipping.exe', 'TFTClient.exe']:
         os.system(f'taskkill /F /IM {proc} /T >nul 2>&1')
     ```
2. **Vô hiệu hóa vĩnh viễn Service UltraViewer:**
   - Trong Windows Service, dịch vụ của UltraViewer có tên là `UltraViewService` (không phải `UltraViewer`):
     ```powershell
     Stop-Service -Name 'UltraViewService' -Force -ErrorAction SilentlyContinue
     Set-Service -Name 'UltraViewService' -StartupType Disabled
     ```
3. **Diệt sạch hook trong RAM & Startup:**
   - Diệt tiến trình service và desktop client:
     ```cmd
     taskkill /F /IM UltraViewer_Service.exe /T
     taskkill /F /IM UltraViewer_Desktop.exe /T
     taskkill /F /IM uv_x64.exe /T
     ```
   - Rà soát Registry `HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Run` và các thư mục Startup (`Start Menu\Programs\Startup`) để đảm bảo không còn shortcut tự khởi chạy.
4. **Khởi chạy ứng dụng đồ họa đúng session user (Session 1):**
   - Không chạy trực tiếp qua SSH non-interactive subshell nếu ứng dụng cần tương tác GUI; dùng `schtasks` tạo task với cờ `/it` (interactive) hoặc `/rl highest` để ứng dụng xuất hiện trực tiếp trên màn hình desktop console của người dùng.
