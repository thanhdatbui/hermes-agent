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

ps_script = ps_script.replace('$IMG_PATH', r'C:\absolute\path\to\image.jpg'.replace('\\', '\\\\'))

with open("ocr_winrt.ps1", "w", encoding="utf-8") as f:
    f.write(ps_script)

res = subprocess.run(["powershell", "-ExecutionPolicy", "Bypass", "-File", "ocr_winrt.ps1"], capture_output=True)
text = res.stdout.decode('utf-8', errors='replace')
print(text)
```

## Pitfalls (Critical)

| Pitfall | Fix |
|---------|-----|
| Relative path | Use **absolute** path (`C:\...`) — `GetFileFromPathAsync` fails silently on relative |
| `text=True` in subprocess | Use `capture_output=True` + `.decode('utf-8', errors='replace')` — Vietnamese/UTF-8 causes `UnicodeDecodeError` on Windows with `text=True` |
| Inline `-Command` string | Write to `.ps1` file + `-File` — backtick/escape hell otherwise |
| Language pack missing | `TryCreateFromUserProfileLanguages()` returns `null`; always fall back to `TryCreateFromLanguage(Language::new('en-US'))` |
| Low-res/small text | Upscale 3x first with Pillow: `crop.resize((w*3, h*3), Image.Resampling.LANCZOS)` |

## Language Support

List installed languages:
```powershell
[Windows.Media.Ocr.OcrEngine]::AvailableRecognizerLanguages | ForEach-Object { $_.LanguageTag }
```
Common: `en-US`, `vi-VN`, `ja-JP`, `zh-CN`, `zh-Hans`, `ko-KR`.

## Helper Script

See `scripts/winrt_ocr.py` — ready-to-use Python wrapper.

```bash
python scripts/winrt_ocr.py C:\path\to\image.jpg          # Default: en-US
python scripts/winrt_ocr.py C:\path\to\image.jpg --lang vi-VN
python scripts/winrt_ocr.py C:\path\to\image.jpg --upscale 3
```

## Comparison

| Method | Install | Speed | PDF? | Image? | Tables/Equations |
|--------|---------|-------|------|--------|------------------|
| WinRT OCR (this skill) | **Zero** | Fast | ❌ | ✅ | ❌ |
| pymupdf | ~25MB | Instant | ✅ (text) | ❌ | ❌ |
| marker-pdf | ~5GB | Slow | ✅ (OCR) | ✅ | ✅ |
| Tesseract | ~50MB | Medium | ❌ | ✅ | ❌ |

**Rule**: WinRT for screenshots/JPEG on Windows. pymupdf for text PDFs. marker-pdf for scanned PDFs/equations. Tesseract for cross-platform images.