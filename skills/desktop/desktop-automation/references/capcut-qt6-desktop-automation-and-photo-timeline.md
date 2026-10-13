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
   - **How Replacement Actually Works on Desktop PC & Critical Pitfalls:**
     - **The Drag & Drop Timeline-Stretching Trap (Music Beat Desync):**
       - In the Media panel (`Tệp phương tiện`), dragging an image down onto a template track segment often defaults to the static image duration (3–5 seconds) rather than conforming to the template slice (0.5–1.2 seconds) unless explicitly trimmed.
       - *Severe Consequence:* In 30–50 clip templates (e.g., milestone/birthday videos), replacing clips naively balloons the timeline from 30s to 4+ minutes (e.g., `04:32:17`), completely ruining the sync with background music and effects.
     - **The Compound Clip Trap (`Dòng thời gian 02` & Yellow Tooltip):**
       - Double-clicking or drilling into template tracks automatically jumps the user into a nested compound clip timeline (**`Dòng thời gian 02`**) and displays a yellow callout bubble: *"Clip của bạn được lưu ở đây. Bạn có thể chuyển về lại dòng thời gian trước đó bất cứ lúc nào."*
       - *User Experience Impact:* Users unfamiliar with NLE compound clips perceive this as an app crash/severe glitch ("Gì lỗi app kinh khủng v").
       - *Recovery:* Dismiss the yellow popup ("Đã hiểu"), click back to tab **`Dòng thời gian 01`** to restore the main project timeline.
     - **Best Practice & User Advice (Mobile vs. PC):**
       - **NEVER recommend replacing large templates (20–40+ clips) on CapCut PC.** CapCut PC lacks the mobile "Template Wizard" (Batch Slot Picker). Replacing 40 clips one-by-one with manual crop confirmation on PC is agonizingly tedious and error-prone.
       - **Always redirect large batch templates (thôi nôi, anniversary, baby milestone) to CapCut Mobile (iOS/Android):** Users tap "Sử dụng mẫu", select all 40 photos sequentially from their album, and export in under 60 seconds with perfect beat synchronization.
       - If forced to use PC: Right-click the segment -> **Thay thế clip (Replace clip)** -> select image -> **Confirm Crop Region (Xác nhận vùng cắt)** to prevent duration expansion, or restrict to short templates with $\le 10-12$ slots.
