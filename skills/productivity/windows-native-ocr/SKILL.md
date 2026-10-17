---
name: windows-native-ocr
description: "Extract text from screenshots/JPEG/PNG on Windows using built-in WinRT OCR — zero install, no dependencies."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [windows]
metadata:
  hermes:
    tags: [OCR, Windows, WinRT, Screenshots, Images]
    related_skills: [ocr-and-documents, pdf, docx]
---

# Windows Native OCR (WinRT)

**Windows 10/11 ships WinRT OCR — no pip install needed.** Works on any Windows machine. Best for screenshots, JPEG, PNG, BMP images (NOT PDFs — see `ocr-and-documents` skill for PDF extraction).

## When to Use

- Input is a screenshot, photo, or image file (JPG/PNG/BMP)
- Need quick text extraction on Windows without installing Tesseract/PaddleOCR/marker-pdf
- The image contains UI text, notifications, dialogs, or web UI elements

## Quick Start

```python
import subprocess

ps_script = r"""
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
Add-Type -AssemblyName System.Runtime.WindowsRuntime

$types = @(
    "Windows.Globalization.Language, Windows.Globalization, ContentType=WindowsRuntime",
    "Windows.Graphics.Imaging.BitmapDecoder, Windows.Graphics.Imaging, ContentType=WindowsRuntime",
    "Windows.Graphics.Imaging.SoftwareBitmap, Windows.Graphics.Imaging, ContentType=WindowsRuntime",
    "Windows.Media.Ocr.OcrEngine, Windows.Media.Ocr, ContentType=WindowsRuntime",
    "Windows.Media.Ocr.OcrResult, Windows.Media.Ocr, ContentType=WindowsRuntime",
    "Windows.Storage.StorageFile, Windows.Storage, ContentType=WindowsRuntime",
    "Windows.Storage.Streams.IRandomAccessStream, Windows.Storage.Streams, ContentType=WindowsRuntime",
    "Windows.Storage.FileAccessMode, Windows.Storage, ContentType=WindowsRuntime"
)
foreach ($t in $types) { try { [void][Type]::GetType($t, $true) } catch {} }

$asTaskGeneric = ([System.WindowsRuntimeSystemExtensions].GetMethods() |
    Where-Object { $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and
                   $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1' })[0]

function AwaitTask($WinRtTask, $ResultType) {
    $asTask = $asTaskGeneric.MakeGenericMethod($ResultType)
    $netTask = $asTask.Invoke($null, @($WinRtTask))
    $netTask.Wait(-1) | Out-Null
    return $netTask.Result
}

$imgPath = '$IMG_PATH'
$file = AwaitTask ([Windows.Storage.StorageFile]::GetFileFromPathAsync($imgPath)) ([Windows.Storage.StorageFile])
$stream = AwaitTask ($file.OpenAsync([Windows.Storage.FileAccessMode]::Read)) ([Windows.Storage.Streams.IRandomAccessStream])
$decoder = AwaitTask ([Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($stream)) ([Windows.Graphics.Imaging.BitmapDecoder])
$bitmap = AwaitTask ($decoder.GetSoftwareBitmapAsync()) ([Windows.Graphics.Imaging.SoftwareBitmap])

$engine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromLanguage([Windows.Globalization.Language]::new('en-US'))
$result = AwaitTask ($engine.RecognizeAsync($bitmap)) ([Windows.Media.Ocr.OcrResult])

foreach ($line in $result.Lines) { Write-Host $line.Text }
"""

ps_script = ps_script.replace('$IMG_PATH', r'C:\absolute\path\to\image.jpg'.replace("'", "''"))

with open("ocr_winrt.ps1", "w", encoding="utf-8") as f:
    f.write(ps_script)

res = subprocess.run(["powershell", "-ExecutionPolicy", "Bypass", "-File", "ocr_winrt.ps1"], capture_output=True)
text = res.stdout.decode('utf-8', errors='replace')
print(text)
```

## Pitfalls (Critical)

| Pitfall | Fix |
|---------|-----|
| Python `import winrt` (`ModuleNotFoundError: No module named 'winrt'`) | WinRT is a native Windows/.NET API, **not** a pre-installed Python module. Do **not** try to `import winrt` in Python directly. Always invoke PowerShell via `subprocess.run(["powershell", "-ExecutionPolicy", "Bypass", "-File", ...])` or call `scripts/winrt_ocr.py`. |
| Forward slash in Windows path (`/`) | WinRT `GetFileFromPathAsync` crashes with `AggregateException: One or more errors occurred` if given forward slashes (e.g. `D:/path/file.jpg`). Always normalize path with Windows native backslashes: `os.path.abspath(path).replace('/', '\\')` before passing to PowerShell. |
| Relative path | Use **absolute** path (`C:\...`) — `GetFileFromPathAsync` fails silently on relative |
| Double backslash in single-quoted PS string | In `$imgPath = '$IMG_PATH'`, do **not** double `\` to `\\`. In PowerShell single quotes `'...'`, `\` is literal; doubling creates `C:\\path` which crashes `GetFileFromPathAsync` with `AggregateException`. Only escape `'` as `''`. |
| `$outputBoxes` string boolean evaluation | In PowerShell, `[bool]($WITH_BOXES -eq 'True')` fails if `$WITH_BOXES` is injected without quotes or evaluates to non-boolean (unquoted `True` in PowerShell evaluates to empty/false). Always wrap as `[bool]('$WITH_BOXES' -eq 'True')`. |
| Bash `-Command` multiline escape break | Passing complex multiline PowerShell scripts via `powershell -Command "..."` inside Git-Bash/MSYS often breaks on backticks or quotes (`unexpected EOF while looking for matching ``'`). Always write to a `.ps1` file and invoke with `powershell -ExecutionPolicy Bypass -File <script.ps1>`. |
| `text=True` in subprocess | Use `capture_output=True` + `.decode('utf-8', errors='replace')` — Vietnamese/UTF-8 causes `UnicodeDecodeError` on Windows with `text=True` |
| Inline `-Command` string | Write to `.ps1` file + `-File` — backtick/escape hell otherwise |
| Language pack missing | `TryCreateFromUserProfileLanguages()` returns `null`; always fall back to `TryCreateFromLanguage(Language::new('en-US'))` |
| Low-res/small text | Upscale 3x first with Pillow: `crop.resize((w*3, h*3), Image.Resampling.LANCZOS)` |
| Vietnamese diacritics on en-US engine | When `vi-VN` is missing, `en-US` OCR transliterates Vietnamese vowels to Nordic/German accents (e.g. `Xác nhận` -> `Xåc nhån`, `cài đặt` -> `cäi dät`). Use Unicode NFKD decomposition + combining diacritics stripping (`unicodedata.normalize('NFKD', text)`) and replace `đ`/`Đ` with `d` to match both raw and accent-stripped keywords reliably. |
| Low-contrast input box & diacritic distortion (Android EditText) | Khi OCR ô nhập liệu (EditText) có con trỏ nhấp nháy hoặc chữ màu xám nhạt (như ô sửa tên TikTok), WinRT OCR thường đọc sai/méo các nguyên âm tiếng Việt phức tạp (e.g. `Sơn Nấm` -> `Sdn I\lam`, `Tươi Đậu` -> `Tl-fdi DåU`, `Bùi Duy Phương` -> `Bbi Duy Phi-fdng`). Giải pháp: Không dùng ngưỡng `ratio >= 0.70` đơn độc trên ô input; kết hợp bộ đếm ký tự `(\d{1,2})/30` làm neo vật lý + so khớp từng từ đơn (`found_word`) hoặc hạ threshold toàn chuỗi `ratio >= 0.45` để tránh false-negative abort. Chốt chặn nghiêm ngặt giữ ở màn hình kết quả (Profile readback). |
| Python 3.12+ `SyntaxWarning` | Use raw strings (`r"""..."""`) for docstrings and templates containing `\p`, `\U`, or backslashes |
| Python f-string Windows path escape (`\U...`) | Trong Python f-string với Windows paths dạng `f'C:\Users\...'`, `\U` bị trình biên dịch diễn giải là escape sequence unicode 32-bit (`\UXXXXXXXX`) gây lỗi `SyntaxError: (unicode error) 'unicodeescape' codec can't decode bytes`. Luôn dùng forward slashes `f'C:/Users/...'` hoặc raw path / `os.path.join()`. |
| CWD script pollution/collision | Write the temporary `.ps1` using `tempfile.NamedTemporaryFile(suffix='.ps1', delete=False)` and remove in `finally` |
| Bash unquoted Windows path (`\`) | In Git-Bash / MSYS shell, unquoted paths like `D:\Taadaa\m38.png` treat `\T` and `\m` as escape sequences, stripping `\` and resulting in `D:Taadaam38.png`. Always use forward slashes or wrap in double quotes (`"D:/Taadaa/m38_verified_net.png"`). |
| ADB dump `null root node` fallback | Khi `uiautomator dump` bị fail (`ERROR: null root node returned by UiTestAutomationBridge`), dùng WinRT OCR trực tiếp lên ảnh chụp screencap (`screencap -p` -> `pull`) để đọc UI text và xác minh trạng thái màn hình thay vì dựa vào XML. |
| Telegram image cache & Browser vision screenshot inspection | Khi agent nhận ảnh qua Telegram (`...\image_cache\img_*.jpg`) hoặc từ `browser_vision` (`...\cache\screenshots\browser_screenshot_*.png`), dùng WinRT OCR để đọc text/UI mà không phụ thuộc vision API. Bắt buộc truyền `timeout=30` khi gọi qua `terminal` (`GUARD_FOREGROUND_TIMEOUT_MISSING`). **Lưu ý Guard blacklist, multiline shell & T1 write budget:** (1) Tuyệt đối KHÔNG truyền trực tiếp đường dẫn thư mục nhạy cảm hệ thống vào lệnh `terminal` hay URL `browser_navigate` (sẽ bị Guard chặn `GUARD SOURCE BLACKLISTED`). (2) CẤM tạo nhiều file script con riêng lẻ (`write_file`) ở `D:/Taadaa/tools/` vì làm cạn kiệt ngân sách T1 của Coordinator (tối đa 5 files, <= 200 dòng cộng dồn cả session). Bắt buộc tái sử dụng cùng 1 file tạm hoặc dùng `scripts/winrt_ocr.py`. (3) Tránh chạy `python -c "..."` dạng multiline phức tạp qua Git-Bash terminal vì `lifecycle_guard` có thể báo lỗi `embedded null character in path` khi kiểm tra đối số; nên viết ra 1 file script duy nhất rồi chạy hoặc giữ lệnh trên 1 dòng đơn. (4) Khi đối soát widget hoặc khu vực cụ thể trên trang web dài, crop vùng tọa độ trước khi OCR để tránh WinRT bitmap decoder bị tràn hoặc bỏ sót chữ. |
| Ultra-tall full-page screenshots (>65,000px height / DecompressionBombWarning) | Full-page browser captures trên bảng lớn (1.000+ rows) có thể tạo ảnh >70.000px height (>90 Megapixels). WinRT bitmap decoder thất bại im lặng (trả về chuỗi rỗng) do giới hạn kích thước bitmap của Windows, đồng thời Pillow văng `DecompressionBombWarning`. Luôn crop phần viewport hoặc vùng hàng mục tiêu trước khi OCR: `from PIL import Image; Image.MAX_IMAGE_PIXELS = None; im = Image.open(path); crop = im.crop((0, y1, im.width, y2)); crop.save(cropped_path)`. |
| Multi-button State Ambiguity & Optimistic Cache (Follow vs Message) | Khi OCR đọc trạng thái nút quan hệ (TikTok/mạng xã hội), nhiều nút action cùng tồn tại (e.g. `[Follow]` đỏ + `[Nhắn tin]` xám khi chưa follow hoặc follow lại). Nếu OCR đọc được `Nhắn tin` nhưng đọc trượt `Follow` do tương phản màu/icon, TUYỆT ĐỐI KHÔNG phán `followed` (nguy cơ false-positive nghiêm trọng). Áp dụng quy tắc Follow Dominance (còn từ khóa follow là chưa follow). Khi màn hình CHỈ có duy nhất nút `[Nhắn tin]`, mặc định `allow_message_alone=False` phải trả về `unknown` để fail-closed chuyển sang xác thực sâu. BẮT BUỘC vuốt reload (`pull_to_refresh`) trước khi OCR để phá vỡ Optimistic UI Cache của app. |
| Top-Bar Nav Tabs Exclusion ($y_1 < 200$) | Các tab điều hướng đỉnh Feed (e.g. `"Bạn bè"`, `"LIVE"`, `"Dành cho bạn"`) có tọa độ $y_1 < 200$. Khi phân loại trạng thái Profile, bắt buộc đặt ngưỡng `y_min = 200` để loại bỏ hoàn toàn các tab đỉnh, tránh nhận nhầm chữ "Bạn bè" trên top bar thành trạng thái quan hệ bạn bè của Profile. |
| Word-Boundary Regex on Sensitive Screen Guards | Khi quét từ khóa nhạy cảm dập popup, bắt buộc dùng regex `\b` word boundary (`re.search(r"\b" + re.escape(sk) + r"\b", n_txt)`), tránh false-positive khi gặp các từ ngữ thông thường chứa chuỗi con (e.g. "Prepayment" hay "Footprint"). |
| Top-Bar Nav & Tab Collision (Feed Tabs vs Profile Action) | Trên màn hình Feed/trang chủ ứng dụng, thanh tab điều hướng trên cùng ($y_1 < 200$, ví dụ tab `Bạn bè`, `Đang follow`, `LIVE`, `Dành cho bạn`) chứa các từ khóa quan hệ. Nếu chạy OCR toàn màn hình với $y_{min} = 0$, parser sẽ bắt trúng chữ `Bạn bè` trên thanh tab và phán nhầm màn hình Feed là `followed`! BẮT BUỘC thiết lập ngưỡng quét mặc định $y_{min} = 200$ (hoặc loại trừ vùng header/status bar $y_1 < 200$) khi phân loại nút profile. |
| Button Action Word-Length Guard vs Long Description | Khi dùng từ khóa ngắn như `"follow"` để tìm nút bấm, nếu người dùng viết Bio dài chứa từ này (e.g. *"Follow kênh mình nhé mọi người"*), regex tìm từ sẽ match nhầm Bio thành nút bấm. Luôn đặt rào cản độ dài từ: `len(n_txt.split()) <= 3` cho nút bấm hành động; nếu vượt quá 3 từ lập tức loại trừ. |
| Popup Dismissal Safety Guard on Sensitive Screens | Khi tự động dập popup bằng OCR (tìm *"Để sau"*, *"Hủy"*, *"Đóng"*), bắt buộc quét toàn màn hình trước xem có từ khóa nhạy cảm / bảo mật (`mật khẩu`, `captcha`, `otp`, `đăng nhập`, `thanh toán`, `credential`) hay không. Nếu có, FAIL-CLOSED (trả về `None`) ngay lập tức, tuyệt đối không tự ý bấm đóng làm hỏng luồng thử thách danh tính. |
| SequenceMatcher Ratio Trap on Stale Username with Digits | Khi đối soát tên mục tiêu (e.g. target `'Phan Nhung'`), nếu tên hiển thị cũ vẫn là username kèm số đuôi (e.g. `'phannhung1710'`), `SequenceMatcher.ratio()` đạt 0.78 >= 0.75, dẫn tới phán đoán sai là tên đã đổi rồi (`ALREADY`) và bỏ qua không gõ tên mới. BẮT BUỘC kiểm tra `re.search(r'\d{2,}$', nl)`: nếu còn dính số đuôi thì loại trừ false-positive ngay để kích hoạt flow sửa tên thật sự. |
| PowerShell Non-zero Returncode & Stderr Audit | Hàm wrapper gọi PowerShell OCR (`ocr_boxes.ps1`) không được nuốt exception âm thầm. Bắt buộc kiểm tra `r.returncode != 0` và log cảnh báo kèm `r.stderr` để phân biệt chính xác giữa lỗi script PowerShell/WinRT crash với màn hình thực tế không có chữ. |
| Adapter Telemetry & Silent Exception Swallowing Trap | Khi tích hợp OCR vào Adapter/Engine (`ocr_screen`, `_classify_with_fallback`), CẤM TUYỆT ĐỐI nuốt ngoại lệ `except Exception: return []` hoặc `pass` im lặng. Hành vi này làm biến tướng mọi lỗi hạ tầng (screencap rỗng, WinRT crash, timeout, permission) thành trạng thái `unknown` mà không để lại dấu vết vận hành. BẮT BUỘC ghi log có cấu trúc: thời gian `elapsed`, mã thiết bị `serial`, nguyên nhân thất bại (`invalid_screencap`, `timeout`, `ocr_error`), và log cảnh báo khi dọn dẹp file tạm thất bại (`ocr_temp_cleanup_failed`). Đồng thời kiểm tra chặt chẽ PNG magic header (`\x89PNG\r\n\x1a\n`) trước khi nạp vào bộ giải mã. |

## Language Support

List installed languages (requires loading WinRT runtime first in PowerShell 5.1):
```powershell
powershell -Command "Add-Type -AssemblyName System.Runtime.WindowsRuntime; [void][Type]::GetType('Windows.Media.Ocr.OcrEngine, Windows.Media.Ocr, ContentType=WindowsRuntime', \$true); [Windows.Media.Ocr.OcrEngine]::AvailableRecognizerLanguages | ForEach-Object { \$_.LanguageTag }"
```
Common: `en-US`, `vi-VN`, `ja-JP`, `zh-CN`, `zh-Hans`, `ko-KR`. Note: If `vi-VN` is not installed, fall back to `en-US` (Latin text and numbers are recognized reliably under `en-US`).

### CJK / Multilingual Fallback (Scanned Catalogs & Docs)
Nếu WinRT thiếu language pack CJK (`zh-CN`, `ja-JP`, `ko-KR`) hoặc tài liệu dạng PDF scan hình ảnh:
- Dùng `pymupdf` render trang PDF thành ảnh (`page.get_pixmap(dpi=150).save('page_N.png')`).
- Gửi ảnh qua Multimodal Vision LLM (Gemini 3.8 / Flash qua proxy Omni `:20129`) để vừa OCR tiếng Trung/Anh vừa dịch thuật ngữ kỹ thuật sang tiếng Việt chuẩn xác mà không cần tải model offline nặng (marker-pdf / PaddleOCR).
- Xem chi tiết pattern chia batch và bàn giao audit cho Claude CLI tại: `references/multimodal-scanned-document-translation.md`.

## Helper Script

See `scripts/winrt_ocr.py` — ready-to-use Python wrapper.

```bash
python scripts/winrt_ocr.py C:\path\to\image.jpg          # Default: en-US
python scripts/winrt_ocr.py C:\path\to\image.jpg --lang vi-VN
python scripts/winrt_ocr.py C:\path\to\image.jpg --boxes         # Includes [x1, y1, x2, y2] and Center (cx, cy) for click targeting
python scripts/winrt_ocr.py C:\path\to\image.jpg --upscale 3

# Visual Evidence Protocol (Red Highlight & 2x Zoom Crop for Telegram reports):
python scripts/winrt_ocr.py C:\path\to\image.jpg --highlight "WhatsApp" --zoom-crop "WhatsApp"
# Outputs: C:\path\to\image_annotated.png and C:\path\to\image_zoomed.png
```

### Visual Evidence Annotation Workflow
Khi cần trình bày bằng chứng trực quan cho User qua Telegram (Gate 6 / Visual Evidence Protocol):
1. **Highlight & Zoom**: Chạy `python scripts/winrt_ocr.py <image_path> --highlight "<keyword>" --zoom-crop "<keyword>"`.
   - Script tự động OCR bốc tọa độ hộp chữ (`Bounds`), vẽ viền đỏ nổi bật quanh từ khóa lỗi/cảnh báo, và cắt cúp phóng to 2x (LANCZOS) để xem rõ trên Telegram di động.
2. **Gửi đính kèm MEDIA:**: Đưa đường dẫn ảnh `MEDIA:<annotated_path>` và `MEDIA:<zoomed_path>` vào phản hồi để hiển thị trực tiếp.

## Comparison

| Method | Install | Speed | PDF? | Image? | Tables/Equations |
|--------|---------|-------|------|--------|------------------|
| WinRT OCR (this skill) | **Zero** | Fast | ❌ | ✅ | ❌ |
| pymupdf | ~25MB | Instant | ✅ (text) | ❌ | ❌ |
| marker-pdf | ~5GB | Slow | ✅ (OCR) | ✅ | ✅ |
| Tesseract | ~50MB | Medium | ❌ | ✅ | ❌ |

**Rule**: WinRT for screenshots/JPEG on Windows. pymupdf for text PDFs. marker-pdf for scanned PDFs/equations. Tesseract for cross-platform images.

## Zero-Token Offline State-Machine Farm Automation (WinRT OCR + no_agent Cron)

Triết lý tối ưu chi phí & tốc độ vận hành quy mô lớn (160+ devices, 80 Kibe + 80 Admin):
- **Phân vai hai tầng**: LLM Coordinator chỉ đóng vai trò "Compiler" (triage sự cố, thiết kế State-Machine, kiểm thử Canary). Sau khi đóng gói thành script canonical, LLM rút lui hoàn toàn.
- **Thực thi 100% Offline trên CPU**: Vòng lặp tự động hóa chạy ngầm dùng WinRT OCR (`Windows.Media.Ocr` via `ocr_boxes.ps1`) bóc tách text + bounding box (`[x1, y1, x2, y2]`) trong 0.2s - 0.5s, tốn **đúng 0 token LLM, 0 đồng API**, không phụ thuộc mạng và triệt tiêu lỗi treo `uiautomator dump` XML.
- **Tái cấu trúc workflow**: Mọi quy trình lớn (Reg, Follow, Login, Rename, Nurture) được phân rã thành chuỗi micro-actions: Screencap -> WinRT OCR box -> Tap tâm box / Keyevent cứng -> WinRT OCR readback verification.
- **Báo cáo Native Media**: Cronjob cấu hình `no_agent=True` và script in `\nMEDIA:{p_posix}` (dùng `/`) để Telegram Gateway tự động upload ảnh photo mà không cần LLM đọc ảnh.
- Chi tiết kiến trúc & danh mục repo áp dụng: xem `references/zero-token-farm-watchdog-and-repo-applicability.md`, `references/zero-token-offline-state-machine-farm-automation.md`, và `references/hybrid-ocr-vs-xml-architecture-and-stat-traps.md` (kiến trúc Hybrid OCR vs XML, luật Follow Dominance chống bẫy nút Nhắn tin & bẫy nhãn thống kê stat counter).
