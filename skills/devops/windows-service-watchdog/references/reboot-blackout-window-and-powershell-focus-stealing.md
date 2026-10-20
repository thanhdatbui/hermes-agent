# Reboot Blackout Window & PowerShell Focus-Stealing Prevention

## 1. Va Chạm Giữa Batch Runner và Mốc Reboot Định Kỳ (Reboot Blackout Window)

### Ngữ Cảnh & Cơ Chế Va Chạm
Hệ thống Farm Taadaa có 3 mốc reboot định kỳ cố định: `05:20`, `11:20`, `17:20` (`farm_preflight_daily_reset.py`).
Trước khi gửi lệnh reboot (Admin qua SSH, Kibe local), script preflight kiểm tra:
1. `is_tft_match_in_progress()`: Nếu phát hiện đang trong trận game (TFT/War3), hệ thống `[ABORT]` hủy reboot để không làm AFK / xử thua.
2. `has_active_device_locks()`: Nếu phát hiện bất kỳ `active device lock` nào trên các thiết bị farm, hệ thống `[SKIP]` bỏ qua lượt reboot để bảo vệ phiên thao tác trên điện thoại.

### Cạm Bẫy Trùng Lịch (Schedule Contention)
- **Sự cố thực tế:** Cronjob mang tên ban đêm (`night-tiktok-2fa-watchdog`) lại được cấu hình schedule `*/15 * * * *` (chạy mỗi 15 phút, suốt 24 giờ). Đồng thời hàm kiểm tra cửa sổ an toàn `is_safe_rolling_window()` chỉ né ca tối từ `17:45`, hoàn toàn không có vùng đệm bảo vệ mốc reboot `17:20`.
- Hậu quả: Lúc `17:15:00` (chỉ 5 phút trước reboot), watchdog kích hoạt `run_batch_live_2fa.py` với 15 workers, chiếm giữ 64 file device lock (`machine_*.lock.json`). Đúng 5 phút sau (`17:20:02`), Windows Task Scheduler chạy `farm_preflight_daily_reset.py`, thấy 64 locks active nên tự động `[SKIP]`. Mốc reboot quan trọng trước ca tối bị hủy bỏ, để lại thiết bị và bus USB không được reset.

### Kỷ Luật Khắc Phục Bắt Buộc
1. **Reboot Blackout Buffer:** Mọi watchdog hoặc batch runner có hành vi chiếm giữ device lock (2FA, Reg Gmail, Upload Avatar, Video Workflow) BẮT BUỘC phải tích hợp ngưỡng cấm chạy trước các mốc reboot ít nhất 35 phút và sau reboot 15 phút:
   - Khung cấm Ca Sáng: `04:45 – 05:35`
   - Khung cấm Ca Trưa: `10:45 – 11:35`
   - Khung cấm Ca Chiều: `16:45 – 17:35`
2. **Cron Schedule Alignment:** Các watchdog mang tính chất ca đêm (`night-*`) tuyệt đối không được dùng schedule `*/15 * * * *` rồi dựa vào logic code để lọc, mà phải giới hạn cứng ngay từ tầng scheduler (`*/15 0,1,2,3 * * *`).

---

## 2. Ngăn Chặn Hoàn Toàn Focus Stealing Của PowerShell và CUA Overlay Khi Chơi Game

### Bẫy PowerShell `Start-Process -WindowStyle Hidden`
Trong PowerShell, việc khởi tạo process con bằng:
```powershell
# CẠM BẪY: Vẫn cấp phát console window và conhost.exe trong desktop session, gây cướp focus / giật alt-tab game trong 50-100ms
Start-Process -FilePath "cmd.exe" -ArgumentList $cmd -PassThru -WindowStyle Hidden
```
`-WindowStyle Hidden` chỉ gửi cờ `SW_HIDE` sau khi console window đã được hệ điều hành Windows tạo lập. Khi người dùng đang trong game toàn màn hình (DirectX/Exclusive Fullscreen), sự kiện tạo cửa sổ console này lập tức làm mất focus chuột và giật hình.

### Giải Pháp Triệt Để Qua .NET ProcessStartInfo
Bắt buộc dùng `System.Diagnostics.ProcessStartInfo` với thuộc tính `CreateNoWindow = $true`:
```powershell
$psi = New-Object System.Diagnostics.ProcessStartInfo
$psi.FileName = "cmd.exe"
$psi.Arguments = $cmd
$psi.CreateNoWindow = $true
$psi.UseShellExecute = $false
$p = [System.Diagnostics.Process]::Start($psi)
```
Cờ `CreateNoWindow = $true` tương đương với cờ Win32 `CREATE_NO_WINDOW (0x08000000)`, ngăn Windows kernel tạo bất kỳ console buffer hay cửa sổ conhost nào trên Desktop Session 1.

### Xử Lý Cửa Sổ Overlay `Cua.AgentCursorOverlay.default`
Khi sử dụng công cụ `computer_use`, tiến trình `cua-driver` tạo ra một cửa sổ overlay toàn màn hình `Cua.AgentCursorOverlay.default` (1920x1080) để vẽ con trỏ ảo. Khi phiên desktop hoàn tất hoặc khi người dùng đang chơi game:
- Quét và ẩn các cửa sổ overlay còn sót lại bằng Win32 `ShowWindow(hwnd, SW_HIDE)`:
```python
import ctypes
from ctypes import wintypes

user32 = ctypes.windll.user32
SW_HIDE = 0

def hide_cua_overlays():
    def cb(hwnd, lparam):
        length = user32.GetWindowTextLengthW(hwnd)
        if length > 0:
            title = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, title, length + 1)
            if "Cua.AgentCursorOverlay" in title.value:
                user32.ShowWindow(hwnd, SW_HIDE)
        return True
    user32.EnumWindows(ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, ctypes.c_long)(cb), 0)
```
