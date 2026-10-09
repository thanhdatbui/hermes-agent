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
| Relative path | Use **absolute** path (`C:\...`) — `GetFileFromPathAsync` fails silently on relative |
| Double backslash in single-quoted PS string | In `$imgPath = '$IMG_PATH'`, do **not** double `\` to `\\`. In PowerShell single quotes `'...'`, `\` is literal; doubling creates `C:\\path` which crashes `GetFileFromPathAsync` with `AggregateException`. Only escape `'` as `''`. |
| `$outputBoxes` string boolean evaluation | In PowerShell, `[bool]($WITH_BOXES -eq 'True')` fails if `$WITH_BOXES` is injected without quotes or evaluates to non-boolean (unquoted `True` in PowerShell evaluates to empty/false). Always wrap as `[bool]('$WITH_BOXES' -eq 'True')`. |
| Bash `-Command` multiline escape break | Passing complex multiline PowerShell scripts via `powershell -Command "..."` inside Git-Bash/MSYS often breaks on backticks or quotes (`unexpected EOF while looking for matching ``'`). Always write to a `.ps1` file and invoke with `powershell -ExecutionPolicy Bypass -File <script.ps1>`. |
| `text=True` in subprocess | Use `capture_output=True` + `.decode('utf-8', errors='replace')` — Vietnamese/UTF-8 causes `UnicodeDecodeError` on Windows with `text=True` |
| Inline `-Command` string | Write to `.ps1` file + `-File` — backtick/escape hell otherwise |
| Language pack missing | `TryCreateFromUserProfileLanguages()` returns `null`; always fall back to `TryCreateFromLanguage(Language::new('en-US'))` |
| Low-res/small text | Upscale 3x first with Pillow: `crop.resize((w*3, h*3), Image.Resampling.LANCZOS)` |
| Vietnamese diacritics on en-US engine | When `vi-VN` is missing, `en-US` OCR transliterates Vietnamese vowels to Nordic/German accents (e.g. `Xác nhận` -> `Xåc nhån`, `cài đặt` -> `cäi dät`). Use Unicode NFKD decomposition + combining diacritics stripping (`unicodedata.normalize('NFKD', text)`) and replace `đ`/`Đ` with `d` to match both raw and accent-stripped keywords reliably. |
| Python 3.12+ `SyntaxWarning` | Use raw strings (`r"""..."""`) for docstrings and templates containing `\p`, `\U`, or backslashes |
| Python f-string Windows path escape (`\U...`) | Trong Python f-string với Windows paths dạng `f'C:\Users\...'`, `\U` bị trình biên dịch diễn giải là escape sequence unicode 32-bit (`\UXXXXXXXX`) gây lỗi `SyntaxError: (unicode error) 'unicodeescape' codec can't decode bytes`. Luôn dùng forward slashes `f'C:/Users/...'` hoặc raw path / `os.path.join()`. |
| CWD script pollution/collision | Write the temporary `.ps1` using `tempfile.NamedTemporaryFile(suffix='.ps1', delete=False)` and remove in `finally` |
| Bash unquoted Windows path (`\`) | In Git-Bash / MSYS shell, unquoted paths like `D:\Taadaa\m38.png` treat `\T` and `\m` as escape sequences, stripping `\` and resulting in `D:Taadaam38.png`. Always use forward slashes or wrap in double quotes (`"D:/Taadaa/m38_verified_net.png"`). |
| ADB dump `null root node` fallback | Khi `uiautomator dump` bị fail (`ERROR: null root node returned by UiTestAutomationBridge`), dùng WinRT OCR trực tiếp lên ảnh chụp screencap (`screencap -p` -> `pull`) để đọc UI text và xác minh trạng thái màn hình thay vì dựa vào XML. |
| Telegram image cache inspection (Non-multimodal models) | Khi agent nhận ảnh qua Telegram dạng `[Image attached at: ...\image_cache\img_*.jpg]`, dùng ngay `scripts/winrt_ocr.py "<path>"` để đọc text/UI trong ảnh mà không phụ thuộc vision API. Khi gọi qua `terminal`, bắt buộc truyền `timeout=30` để tuân thủ guard foreground timeout (`GUARD_FOREGROUND_TIMEOUT_MISSING`). |
| Ultra-tall full-page screenshots (>65,000px height / DecompressionBombWarning) | Full-page browser captures trên bảng lớn (1.000+ rows) có thể tạo ảnh >70.000px height (>90 Megapixels). WinRT bitmap decoder thất bại im lặng (trả về chuỗi rỗng) do giới hạn kích thước bitmap của Windows, đồng thời Pillow văng `DecompressionBombWarning`. Luôn crop phần viewport hoặc vùng hàng mục tiêu trước khi OCR: `from PIL import Image; Image.MAX_IMAGE_PIXELS = None; im = Image.open(path); crop = im.crop((0, y1, im.width, y2)); crop.save(cropped_path)`. |

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