# Chrome UIA Provider Hang: Zero-Focus Background Automation Recipe

## Bối cảnh & Căn nguyên
Khi người dùng mở nhiều tab trên Google Chrome hoặc các ứng dụng Electron (`Chrome_WidgetWin_1`), cây Accessibility UI Automation (UIA) của Windows thường bị nghẽn hoặc treo cứng.
Lúc này, công cụ `computer_use` (chạy qua `cua-driver`) sẽ thất bại với lỗi:
```text
capture failed: cua-driver get_window_state failed: Error: get_window_state timed out after 4s (UIA provider unresponsive on hwnd 0x..., class 'Chrome_WidgetWin_1').
```
Do `capture()` chờ duyệt cây UIA, cả chế độ `mode='som'` lẫn `mode='vision'` đều bị timeout 4s, khiến agent không thể lấy screenshot hoặc tương tác bằng element index.

---

## Giải Pháp Thay Thế: GDI PrintWindow + WinRT OCR + PostMessage

Giải pháp này hoàn toàn chạy ngầm (zero-focus steal), không chiếm chuột hay nâng cửa sổ lên trước mặt người dùng:

### 1. Điều Hướng URL Không Cần CDP
Sử dụng thư viện chuẩn của Python:
```python
import webbrowser
webbrowser.open("https://github.com/login")
```
Lệnh này gửi thông điệp DDE/ShellExecute tới cửa sổ Chrome mặc định đang chạy của người dùng để mở tab mới hoặc tải trang mà không cần restart trình duyệt.

### 2. Chụp Ảnh Màn Hình Cửa Sổ Bằng GDI (`PrintWindow`)
Bỏ qua hoàn toàn cây UIA, trích xuất bitmap trực tiếp từ Device Context của cửa sổ (`hwnd`):
```python
import win32gui, win32ui, ctypes
from PIL import Image

def capture_hwnd_to_png(hwnd, out_path):
    rect = win32gui.GetWindowRect(hwnd)
    w = rect[2] - rect[0]
    h = rect[3] - rect[1]
    
    hwndDC = win32gui.GetWindowDC(hwnd)
    mfcDC = win32ui.CreateDCFromHandle(hwndDC)
    saveDC = mfcDC.CreateCompatibleDC()
    saveBitMap = win32ui.CreateBitmap()
    saveBitMap.CreateCompatibleBitmap(mfcDC, w, h)
    saveDC.SelectObject(saveBitMap)
    
    # PW_RENDERFULLCONTENT = 3
    ctypes.windll.user32.PrintWindow(hwnd, saveDC.GetSafeHdc(), 3)
    
    bmpinfo = saveBitMap.GetInfo()
    bmpstr = saveBitMap.GetBitmapBits(True)
    im = Image.frombuffer('RGB', (bmpinfo['bmWidth'], bmpinfo['bmHeight']), bmpstr, 'raw', 'BGRX', 0, 1)
    
    win32gui.DeleteObject(saveBitMap.GetHandle())
    saveDC.DeleteDC()
    mfcDC.DeleteDC()
    win32gui.ReleaseDC(hwnd, hwndDC)
    
    im.save(out_path)
    return True
```

### 3. Trích Xuất Tọa Độ Phím Bấm / Ô Nhập Bằng WinRT OCR
Chạy WinRT OCR với cờ bóc tách tọa độ hộp chữ (`$line.Words[...].BoundingRect`):
```powershell
$res = AwaitTask ($engine.RecognizeAsync($bitmap)) ([Windows.Media.Ocr.OcrResult])
foreach ($line in $res.Lines) {
    foreach ($w in $line.Words) {
        Write-Host "$($w.Text) | X=$($w.BoundingRect.X), Y=$($w.BoundingRect.Y), W=$($w.BoundingRect.Width), H=$($w.BoundingRect.Height)"
    }
}
```
Từ kết quả OCR, tính tọa độ tâm của nút bấm (ví dụ `Sign in` tại `X=385, Y=465`).

### 4. Click Chuột Ngầm Bằng `PostMessage` (Không Cướp Chuột OS)
Gửi cặp thông điệp `WM_LBUTTONDOWN` và `WM_LBUTTONUP` tới `hwnd` đích:
```python
import win32gui, win32con, win32api, time

def click_window_background(hwnd, x, y):
    lParam = win32api.MAKELONG(x, y)
    win32gui.PostMessage(hwnd, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, lParam)
    time.sleep(0.05)
    win32gui.PostMessage(hwnd, win32con.WM_LBUTTONUP, 0, lParam)
```

### 5. Hậu Kiểm Bắt Buộc (Post-Action Verification)
Sau khi click, chờ 1.5 - 2s cho trang web xử lý, lập tức gọi lại hàm `capture_hwnd_to_png` và chạy OCR để xác nhận:
- URL hoặc tiêu đề cửa sổ đã thay đổi.
- Xuất hiện màn hình tiếp theo (ví dụ: Device Verification, 2FA code, hoặc Dashboard).
- Tuyệt đối không phỏng đoán click đã thành công nếu chưa có ảnh chụp đối soát.
