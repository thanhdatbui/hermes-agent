# CapCut Desktop (Qt6) Automation & Photo Timeline Mapping

## Context & Architecture
CapCut Desktop for Windows is built with **Qt 6** (`Qt622QWindowIcon`) and custom DirectUI canvas rendering.
- **UIA / AX Blindness:** Standard Windows UI Automation (UIA) and cua-driver AX mode only see top-level window frames. The internal canvas (timeline, media bin, player, template masonry grid) does not expose standard OS accessibility nodes.
- **Screen & Frame Capture:** Traditional `PIL.ImageGrab.grab()` often fails in remote/unfocused sessions with `OSError: screen grab failed`. However, Win32 `PrintWindow(hwnd, saveDC.GetSafeHdc(), 2)` (`PW_RENDERFULLCONTENT`) captures the full application canvas cleanly in the background.

## UI Navigation & Interaction Patterns
1. **Background Window Capture via Python:**
   ```python
   import win32gui, win32ui, ctypes
   from PIL import Image

   def capture_window(hwnd, out_path):
       rect = win32gui.GetWindowRect(hwnd)
       w, h = rect[2] - rect[0], rect[3] - rect[1]
       hwndDC = win32gui.GetWindowDC(hwnd)
       mfcDC = win32ui.CreateDCFromHandle(hwndDC)
       saveDC = mfcDC.CreateCompatibleDC()
       saveBitMap = win32ui.CreateBitmap()
       saveBitMap.CreateCompatibleBitmap(mfcDC, w, h)
       saveDC.SelectObject(saveBitMap)
       ctypes.windll.user32.PrintWindow(hwnd, saveDC.GetSafeHdc(), 2)
       bmpinfo = saveBitMap.GetInfo()
       bmpstr = saveBitMap.GetBitmapBits(True)
       im = Image.frombuffer('RGB', (bmpinfo['bmWidth'], bmpinfo['bmHeight']), bmpstr, 'raw', 'BGRX', 0, 1)
       win32gui.DeleteObject(saveBitMap.GetHandle())
       saveDC.DeleteDC(); mfcDC.DeleteDC(); win32gui.ReleaseDC(hwnd, hwndDC)
       im.save(out_path)
   ```

2. **OCR-Assisted Coordinate Targeting:**
   - Pair background captures with `windows-native-ocr` (WinRT OCR) to dynamically discover text bounds:
     - Search input field: typically near top bar (`x ~ 300, y ~ 77`).
     - Template tabs: `Mẫu` (`x ~ 560, y ~ 69`).
     - Card modal close: top-right `'✕'` at (`x ~ 1220, y ~ 135`).
     - Template action buttons: "Sử dụng mẫu" (`x ~ 850, y ~ 860`).

3. **Background Mouse & Keyboard Events:**
   - Clicks are posted via `win32gui.PostMessage(hwnd, WM_LBUTTONDOWN / WM_LBUTTONUP, ...)`.
   - Modals and popups can be dismissed with `PostMessage(hwnd, WM_KEYDOWN, VK_ESCAPE)`.
   - To type into search inputs reliably without Telex/diacritic mangling, use Windows clipboard paste (`OpenClipboard` -> `SetClipboardText` -> `Ctrl+V`).

## Photo Timeline & Milestone Video Assembly
CapCut video templates (e.g. `12 Month Baby 1 year`, `My first year`) enforce a **fixed number of clip slots** (e.g. 10, 12, or 13 clips) with pre-designed transitions and text animations.

When ingesting a raw photo directory (e.g. iCloud Photos with flat UUIDs or disorganized filenames):
1. **EXIF Timestamp Extraction:**
   - Do not rely on file modification time (`os.path.getmtime`), as cloud sync updates mtime upon download.
   - Read EXIF tag `36867` (`DateTimeOriginal`) or tag `306` (`DateTime`) via `PIL.Image._getexif()`.
2. **Chronological Milestone Selection:**
   - Sort images by actual capture date from birth to milestone date (e.g. 1st birthday / thôi nôi).
   - Downsample/distribute evenly into $N$ representative slots (e.g. 12 milestones for 12 months).
3. **Template Feeding & Replacement Mechanics (PC Desktop vs. Mobile App UX):**
   - **Crucial Platform UX Difference:**
     - **Mobile App (iOS/Android):** Tapping "Sử dụng mẫu" opens a modal grid of empty numbered slots (e.g., 40 slots) where users simply tap 40 photos sequentially from the album to batch populate all clips at once.
     - **Desktop PC (CapCut Windows):** There is NO batch slot-picker modal. Tapping the template track on the timeline displays a single unified group clip labeled `Mẫu [duration] - N clip cần thay thế`. Double-clicking or clicking the track does not open a replacement popup.
   - **How Replacement Actually Works on Desktop PC:**
     - **Method 1 (Drag & Drop Replace):** In the Media panel (`Tệp phương tiện`), click and drag an image directly down over the specific clip segment on the timeline template track. Release mouse to open the contextual popup (`Thay thế / Chèn`) and choose **Thay thế (Replace)**.
     - **Method 2 (Batch Replace Preparation):** Due to the high friction of replacing 30–50 clips individually via drag-and-drop on PC, advise users to prefer smaller fixed-milestone templates (e.g. 10–12 clips) or to use the mobile CapCut app for large batches (40+ clips) where native bulk selection exists.
