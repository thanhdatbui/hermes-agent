# GPM Window Background Capture & Manual Takeover Protocol

## 1. Vấn đề cốt lõi & Hiện tượng

### Hiện tượng 1: `computer_use` và PowerShell `CopyFromScreen` bị màn hình đen / rỗng (Blank Screenshot Choke)
- Khi Windows chạy ở chế độ nền (background), màn hình bị khóa (lock screen) hoặc không có active desktop session, các lệnh chụp màn hình toàn màn hình thông thường như `CopyFromScreen` (System.Drawing) hoặc `computer_use(action='capture', app='screen')` có thể xuất ra file ảnh chỉ vài KB (8-9 KB) hoàn toàn rỗng/đen xì.
- Thao tác `computer_use(action='focus_app', raise_window=true)` cũng có thể bị Windows từ chối do chính sách chống cướp focus (`code: 'foreground_unavailable'`, `effect: 'refused'`).

### Hiện tượng 2: Cần chụp ảnh bằng chứng cửa sổ GPM-Login (WPF) / Chrome để gửi `MEDIA:` chuẩn Gate 6 mà không làm phiền màn hình người dùng
- Người dùng đang làm việc song song, nếu cướp cửa sổ lên foreground sẽ gây khó chịu và gián đoạn công việc của người dùng.
- Cần cơ chế chụp trực tiếp buffer của cửa sổ đích (Window-level DC) ở chế độ nền mà vẫn cho độ phân giải sắc nét $O(1)$ và WinRT OCR đọc được đầy đủ dữ liệu bảng (DataGrid).

---

## 2. Giải pháp kỹ thuật: Win32 `PrintWindow` API Background Capture

Sử dụng hàm Win32 API `user32.PrintWindow` với cờ `PW_RENDERFULLCONTENT = 2` thông qua Python `ctypes` và `PIL` (Pillow). Cơ chế này trực tiếp yêu cầu cửa sổ đích vẽ lại giao diện vào một memory Device Context (DC) độc lập, hoạt động hoàn hảo ngay cả khi cửa sổ bị che khuất hoặc nằm ở nền.

### Code mẫu chuẩn (`capture_window_by_title.py`):
```python
import ctypes
from ctypes import wintypes
import os
import win32ui
from PIL import Image

def capture_window_background(window_title: str, output_path: str) -> bool:
    user32 = ctypes.windll.user32
    gdi32 = ctypes.windll.gdi32

    hwnd = user32.FindWindowW(None, window_title)
    if not hwnd:
        print(f"Window not found: {window_title}")
        return False

    rect = wintypes.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(rect))
    w = rect.right - rect.left
    h = rect.bottom - rect.top

    if w <= 0 or h <= 0:
        print(f"Invalid window size: {w}x{h}")
        return False

    hdc_screen = user32.GetWindowDC(hwnd)
    hdc_mem = gdi32.CreateCompatibleDC(hdc_screen)
    hbm = gdi32.CreateCompatibleBitmap(hdc_screen, w, h)
    gdi32.SelectObject(hdc_mem, hbm)

    # PW_RENDERFULLCONTENT = 2 (Ép render toàn bộ nội dung cửa sổ)
    res = user32.PrintWindow(hwnd, hdc_mem, 2)

    bmp = win32ui.CreateBitmapFromHandle(hbm)
    bmpinfo = bmp.GetInfo()
    bmpstr = bmp.GetBitmapBits(True)
    img = Image.frombuffer('RGB', (bmpinfo['bmWidth'], bmpinfo['bmHeight']), bmpstr, 'raw', 'BGRX', 0, 1)

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    img.save(output_path)

    gdi32.DeleteObject(hbm)
    gdi32.DeleteDC(hdc_mem)
    user32.ReleaseDC(hwnd, hdc_screen)
    return bool(res)
```

---

## 3. Kỷ luật Bàn giao Manual Takeover ("Vọc tay")

Khi người dùng yêu cầu: *"Mở profile đó ra t vọc tay"* hoặc *"Mở lại gpm đi"*:

1. **Tuyệt đối không thao tác thừa**:
   - Chỉ thực hiện: Mở app GPM / Khởi chạy profile qua Local API cổng 19995.
   - Điều hướng tới URL yêu cầu (ví dụ `chatgpt.com`).
   - Xử lý các dialog cản trở cơ bản nếu cần (ví dụ: nút Accept Cookies để hiện giao diện chính).
2. **Cấm bấm các nút xác nhận nghiệp vụ thay cho người dùng**:
   - Nếu trình duyệt hiện banner *"GPM-Browser didn't shut down correctly. Khôi phục trang?"*, **CẤM TUYỆT ĐỐI** tự ý click nút Khôi phục (Restore). Hãy để người dùng tự quyết định có khôi phục các tab cũ hay không.
3. **Thực thi Gate 6 & Bàn giao**:
   - Chụp ảnh xác nhận cửa sổ đang mở sẵn sàng bằng `PrintWindow` hoặc screenshot CDP.
   - Soi mắt qua WinRT OCR / Vision xác nhận đúng cửa sổ, đúng trạng thái Sẵn sàng.
   - Phản hồi ngắn gọn kèm `MEDIA:<path>`, nêu rõ trạng thái hiện tại và nhường toàn quyền thao tác cho người dùng.
