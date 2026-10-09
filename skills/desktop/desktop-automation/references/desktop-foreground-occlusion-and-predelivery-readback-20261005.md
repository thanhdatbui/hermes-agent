# Bẫy Che Khuất Cửa Sổ Desktop (Foreground Occlusion Trap) & Kỷ Luật Soi Ảnh Trước Khi Gửi (Pre-Delivery Readback Gate)

**Ngày ghi nhận:** 05/10/2026  
**Ngữ cảnh:** Điều phối thao tác trên Windows Desktop (Claude Desktop, Electron apps, Browser) khi có game hoặc ứng dụng khác đang mở đè lên màn hình.

---

## 1. Hiện tượng & Triệu chứng
- Agent điều phối cấu hình model trên Claude Desktop (đổi sang Sonnet 5.5 và bật Advisor Opus 5.5).
- Sau khi thao tác thành công, agent dùng lệnh chụp màn hình toàn cảnh (`ImageGrab.grab()`) để gửi ảnh nghiệm thu `MEDIA:<path>` cho User kèm lời khẳng định chắc nịch: *"Bằng chứng trên màn hình: Thanh model phía dưới đang hiện Sonnet 5.5, Advisor set to Opus 5.5..."*.
- Tuy nhiên, User mở ảnh ra thì thấy toàn bộ màn hình là game (Riot Client / Đấu Trường Chân Lý - TFT) với Sett, Leona, Shen... Cửa sổ Claude Desktop thực tế đang nằm chìm ở phía sau.
- **Phản ứng của User:** Cực kỳ tức giận vì agent không thèm kiểm tra nội dung ảnh trước khi gửi, tạo cảm giác bịa đặt / báo cáo dối trá:
  > *"Ảnh xác nhận mày gửi như v mà mày dám bảo là có đó hả, mày đéo coi ảnh trc khi gửi à"*

---

## 2. Nguyên nhân gốc rễ (Root Cause)
1. **Lầm tưởng giữa Window Background vs Fullscreen Capture:**
   - Các công cụ như `computer_use` (cua-driver) có thể click/type vào ứng dụng ở chế độ background hoặc foreground ngắn hạn.
   - Nhưng khi dùng thư viện chụp toàn màn hình như `PIL.ImageGrab.grab()` hoặc lệnh chụp desktop thô, hệ thống chụp lại bề mặt hiển thị trên cùng (Composite Desktop Surface).
   - Nếu User đang mở game toàn màn hình hoặc có cửa sổ khác đè lên, ảnh chụp toàn cảnh sẽ bắt trọn cửa sổ đè, hoàn toàn không thấy cửa sổ ứng dụng mục tiêu.
2. **Vi phạm Kỷ luật Verification Readback (Gửi ảnh mù không kiểm tra):**
   - Agent tự tin sau khi thấy lệnh gõ phím hoàn thành là mặc định ảnh chụp sẽ đúng.
   - Không chạy OCR hay đọc lại pixel/nội dung ảnh trước khi append `MEDIA:<path>` vào tin nhắn gửi cho User.

---

## 3. Quy trình khắc phục & Kỷ luật bắt buộc

### Quy tắc 1: Ưu tiên chụp trực tiếp Window DC (PrintWindow)
Khi cần chụp ảnh nghiệm thu một cửa sổ cụ thể trên Windows mà không muốn làm phiền hoặc bị ảnh hưởng bởi các cửa sổ khác:
- Dùng `win32gui` và `ctypes.windll.user32.PrintWindow(hwnd, saveDC, 2)` (`PW_RENDERFULLCONTENT = 2`).
- Phương pháp này trích xuất trực tiếp buffer đồ họa của cửa sổ mục tiêu, không phụ thuộc vào việc cửa sổ đó có bị che khuất hay không.

```python
import ctypes, win32gui, win32ui
from PIL import Image

hwnd = win32gui.FindWindow(None, "Claude")
rect = win32gui.GetWindowRect(hwnd)
w, h = rect[2] - rect[0], rect[3] - rect[1]

hwndDC = win32gui.GetWindowDC(hwnd)
mfcDC = win32ui.CreateDCFromHandle(hwndDC)
saveDC = mfcDC.CreateCompatibleDC()
saveBitMap = win32ui.CreateBitmap()
saveBitMap.CreateCompatibleBitmap(mfcDC, w, h)
saveDC.SelectObject(saveBitMap)

# PW_RENDERFULLCONTENT = 2
res = ctypes.windll.user32.PrintWindow(hwnd, saveDC.GetSafeHdc(), 2)
bmpinfo = saveBitMap.GetInfo()
bmpstr = saveBitMap.GetBitmapBits(True)
im = Image.frombuffer('RGB', (bmpinfo['bmWidth'], bmpinfo['bmHeight']), bmpstr, 'raw', 'BGRX', 0, 1)

win32gui.DeleteObject(saveBitMap.GetHandle())
saveDC.DeleteDC(); mfcDC.DeleteDC()
win32gui.ReleaseDC(hwnd, hwndDC)
im.save(output_path)
```

### Quy tắc 2: Nếu chụp Fullscreen, BẮT BUỘC Bring-To-Front có kiểm soát
Nếu cần ảnh chụp toàn cảnh màn hình:
1. Lưu lại HWND của cửa sổ đang active hiện tại (`fg = win32gui.GetForegroundWindow()`).
2. Kích hoạt cửa sổ mục tiêu lên trên cùng: `win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)` và `win32gui.SetForegroundWindow(hwnd)`.
3. Chờ `time.sleep(0.5)` để Windows kịp vẽ lại giao diện.
4. Chụp màn hình bằng `ImageGrab.grab()`.
5. Khôi phục lại focus ban đầu nếu cần: `win32gui.SetForegroundWindow(fg)`.

### Quy tắc 3: BẮT BUỘC Soi Ảnh Trước Khi Gửi (Pre-Delivery Readback Gate)
- **CẤM TUYỆT ĐỐI** gửi thẻ `MEDIA:<path>` nếu chưa tự kiểm tra nội dung ảnh vừa tạo.
- Chạy nhanh script OCR cục bộ (`winrt_ocr.py <path>`) để đọc text trên ảnh.
- Kiểm tra xem các từ khóa nhận diện của ứng dụng đích (ví dụ: `Sonnet 5.5`, `Advisor set to Opus`, tiêu đề cửa sổ) có thực sự xuất hiện trong kết quả OCR không.
- Nếu OCR phát hiện ảnh chụp sai cửa sổ (ví dụ thấy game, trang web khác hoặc màn hình đen):
  - **HỦY NGAY LẬP TỨC** không gửi ảnh đó cho User.
  - Tiến hành chụp lại theo Quy tắc 1 hoặc 2.
