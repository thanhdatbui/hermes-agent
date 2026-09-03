#!/usr/bin/env python3
"""
Windows Native OCR (WinRT) — extract text from images on Windows 10/11.
Zero dependencies — uses built-in Windows OCR engine.

Usage:
    python winrt_ocr.py C:\path\to\image.jpg
    python winrt_ocr.py C:\path\to\image.jpg --lang vi-VN
    python winrt_ocr.py C:\path\to\image.jpg --upscale 3
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False


PS_TEMPLATE = r"""
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

$engine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromLanguage([Windows.Globalization.Language]::new('$LANG'))
if ($null -eq $engine) {
    Write-Error "Language '$LANG' not installed. Run: [Windows.Media.Ocr.OcrEngine]::AvailableRecognizerLanguages"
    exit 1
}
$result = AwaitTask ($engine.RecognizeAsync($bitmap)) ([Windows.Media.Ocr.OcrResult])

foreach ($line in $result.Lines) { Write-Host $line.Text }
"""


def upscale_image(input_path: str, scale: int) -> str:
    """Upscale image using Pillow, return temp path."""
    if not HAS_PIL:
        raise RuntimeError("Pillow not installed. `pip install pillow` to use --upscale")
    img = Image.open(input_path)
    new_size = (img.width * scale, img.height * scale)
    img = img.resize(new_size, Image.Resampling.LANCZOS)
    temp_path = input_path.replace('.', f'_upscale{scale}x.')
    img.save(temp_path)
    return temp_path


def run_ocr(image_path: str, lang: str = "en-US") -> str:
    """Run WinRT OCR on the given image file."""
    abs_path = os.path.abspath(image_path)
    if not os.path.exists(abs_path):
        raise FileNotFoundError(f"Image not found: {abs_path}")

    # Windows paths in PowerShell string need escaped backslashes
    ps_path = abs_path.replace('\\', '\\\\')
    ps_script = PS_TEMPLATE.replace('$IMG_PATH', ps_path).replace('$LANG', lang)

    ps_file = Path("ocr_winrt_temp.ps1")
    ps_file.write_text(ps_script, encoding="utf-8")

    try:
        res = subprocess.run(
            ["powershell", "-ExecutionPolicy", "Bypass", "-File", str(ps_file)],
            capture_output=True,
            timeout=60,
        )
        text = res.stdout.decode("utf-8", errors="replace")
        if res.returncode != 0:
            err = res.stderr.decode("utf-8", errors="replace")
            raise RuntimeError(f"OCR failed (exit {res.returncode}): {err}")
        return text.strip()
    finally:
        try:
            ps_file.unlink()
        except Exception:
            pass


def main():
    parser = argparse.ArgumentParser(description="Windows WinRT OCR for images")
    parser.add_argument("image", help="Path to image file (JPG/PNG/BMP)")
    parser.add_argument("--lang", default="en-US", help="OCR language tag (e.g., en-US, vi-VN, ja-JP)")
    parser.add_argument("--upscale", type=int, default=1, help="Upscale factor (3 recommended for small text)")
    args = parser.parse_args()

    img_path = args.image
    if args.upscale > 1:
        if not HAS_PIL:
            print("ERROR: Pillow required for --upscale. `pip install pillow`", file=sys.stderr)
            sys.exit(1)
        img_path = upscale_image(args.image, args.upscale)

    try:
        text = run_ocr(img_path, args.lang)
        print(text)
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()