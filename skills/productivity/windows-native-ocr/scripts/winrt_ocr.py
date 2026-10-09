#!/usr/bin/env python3
r"""
Windows Native OCR (WinRT) — extract text, coordinates, and generate visual evidence annotations.
Zero dependencies — uses built-in Windows OCR engine.

Usage:
    python winrt_ocr.py C:\path\to\image.jpg
    python winrt_ocr.py C:\path\to\image.jpg --lang vi-VN
    python winrt_ocr.py C:\path\to\image.jpg --boxes
    python winrt_ocr.py C:\path\to\image.jpg --upscale 3
    python winrt_ocr.py C:\path\to\image.jpg --highlight "WhatsApp" --zoom-crop "WhatsApp"
"""

import argparse
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

try:
    from PIL import Image, ImageDraw
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
    Write-Warning "Language '$LANG' not installed, falling back to 'en-US'..."
    $engine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromLanguage([Windows.Globalization.Language]::new('en-US'))
}
if ($null -eq $engine) {
    $engine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromUserProfileLanguages()
}
if ($null -eq $engine) {
    Write-Error "No OCR engine available for '$LANG', 'en-US', or user profile."
    exit 1
}
$result = AwaitTask ($engine.RecognizeAsync($bitmap)) ([Windows.Media.Ocr.OcrResult])

$outputBoxes = [bool]('$WITH_BOXES' -eq 'True')

foreach ($line in $result.Lines) {
    if ($outputBoxes) {
        $x1 = 999999; $y1 = 999999; $x2 = 0; $y2 = 0;
        foreach ($w in $line.Words) {
            $r = $w.BoundingRect
            if ($r.X -lt $x1) { $x1 = $r.X }
            if ($r.Y -lt $y1) { $y1 = $r.Y }
            if ($r.X + $r.Width -gt $x2) { $x2 = $r.X + $r.Width }
            if ($r.Y + $r.Height -gt $y2) { $y2 = $r.Y + $r.Height }
        }
        $cx = [int](($x1 + $x2) / 2)
        $cy = [int](($y1 + $y2) / 2)
        Write-Host "$($line.Text) | Bounds: [$x1, $y1, $x2, $y2] | Center: ($cx, $cy)"
    } else {
        Write-Host $line.Text
    }
}
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


def run_ocr(image_path: str, lang: str = "en-US", with_boxes: bool = False) -> str:
    """Run WinRT OCR on the given image file."""
    abs_path = os.path.abspath(image_path)
    if not os.path.exists(abs_path):
        raise FileNotFoundError(f"Image not found: {abs_path}")

    # Windows paths in PowerShell single-quoted string: keep single backslashes, escape single quotes
    ps_path = abs_path.replace("'", "''")
    ps_script = (
        PS_TEMPLATE.replace('$IMG_PATH', ps_path)
        .replace('$LANG', lang)
        .replace('$WITH_BOXES', str(with_boxes))
    )

    with tempfile.NamedTemporaryFile("w", suffix=".ps1", encoding="utf-8", delete=False) as tf:
        tf.write(ps_script)
        ps_file_path = tf.name

    try:
        res = subprocess.run(
            ["powershell", "-ExecutionPolicy", "Bypass", "-File", ps_file_path],
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
            os.remove(ps_file_path)
        except Exception:
            pass


def parse_ocr_boxes(ocr_output: str):
    """Parse output from OCR when run with --boxes into structured records."""
    records = []
    for line in ocr_output.splitlines():
        if "| Bounds:" in line:
            m = re.search(r"^(.*?)\s*\|\s*Bounds:\s*\[(\d+),\s*(\d+),\s*(\d+),\s*(\d+)\]\s*\|\s*Center:\s*\((\d+),\s*(\d+)\)", line)
            if m:
                text = m.group(1).strip()
                b = [int(m.group(2)), int(m.group(3)), int(m.group(4)), int(m.group(5))]
                c = (int(m.group(6)), int(m.group(7)))
                records.append({"text": text, "bounds": b, "center": c})
    return records


def annotate_and_zoom(image_path: str, keyword: str, highlight: bool = True, zoom_crop: bool = True, output_prefix: str = None):
    """Highlight matching text with a red rectangle and generate 2x zoomed crop for Telegram visual evidence."""
    if not HAS_PIL:
        raise RuntimeError("Pillow required for visual evidence annotation. `pip install pillow`")

    ocr_out = run_ocr(image_path, with_boxes=True)
    records = parse_ocr_boxes(ocr_out)

    kw_lower = keyword.lower()
    matched = [r for r in records if kw_lower in r["text"].lower()]
    if not matched:
        print(f"WARN: Keyword '{keyword}' not found in OCR results", file=sys.stderr)
        return None, None

    # Merge bounding boxes of all matches
    x1 = min(r["bounds"][0] for r in matched)
    y1 = min(r["bounds"][1] for r in matched)
    x2 = max(r["bounds"][2] for r in matched)
    y2 = max(r["bounds"][3] for r in matched)

    base = output_prefix or os.path.splitext(image_path)[0]
    annotated_path = f"{base}_annotated.png"
    zoomed_path = f"{base}_zoomed.png"

    orig_im = Image.open(image_path).convert("RGB")

    if highlight:
        im = orig_im.copy()
        draw = ImageDraw.Draw(im)
        draw.rectangle([max(0, x1 - 6), max(0, y1 - 6), min(im.width, x2 + 6), min(im.height, y2 + 6)], outline="red", width=4)
        im.save(annotated_path)
        print(f"ANNOTATED_IMAGE: {annotated_path}")

    if zoom_crop:
        crop_x1 = max(0, x1 - 80)
        crop_y1 = max(0, y1 - 80)
        crop_x2 = min(orig_im.width, x2 + 80)
        crop_y2 = min(orig_im.height, y2 + 120)
        cropped = orig_im.crop((crop_x1, crop_y1, crop_x2, crop_y2))
        zoomed = cropped.resize((cropped.width * 2, cropped.height * 2), Image.Resampling.LANCZOS)
        zoomed.save(zoomed_path)
        print(f"ZOOMED_IMAGE: {zoomed_path}")

    return annotated_path, zoomed_path


def main():
    parser = argparse.ArgumentParser(description="Windows WinRT OCR for images")
    parser.add_argument("image", help="Path to image file (JPG/PNG/BMP)")
    parser.add_argument("--lang", default="en-US", help="OCR language tag (e.g., en-US, vi-VN, ja-JP)")
    parser.add_argument("--boxes", action="store_true", help="Output bounding boxes and center (x, y) coordinates")
    parser.add_argument("--upscale", type=int, default=1, help="Upscale factor (3 recommended for small text)")
    parser.add_argument("--highlight", type=str, default=None, help="Keyword to highlight with red box")
    parser.add_argument("--zoom-crop", type=str, default=None, help="Keyword to crop and 2x zoom for visual evidence")
    parser.add_argument("--out-prefix", type=str, default=None, help="Output path prefix for annotated/zoomed images")
    args = parser.parse_args()

    img_path = args.image
    if args.upscale > 1:
        if not HAS_PIL:
            print("ERROR: Pillow required for --upscale. `pip install pillow`", file=sys.stderr)
            sys.exit(1)
        img_path = upscale_image(args.image, args.upscale)

    if args.highlight or args.zoom_crop:
        kw = args.highlight or args.zoom_crop
        try:
            annotate_and_zoom(
                img_path,
                kw,
                highlight=bool(args.highlight),
                zoom_crop=bool(args.zoom_crop),
                output_prefix=args.out_prefix
            )
        except Exception as e:
            print(f"ERROR annotating: {e}", file=sys.stderr)
            sys.exit(1)
        return

    try:
        text = run_ocr(img_path, args.lang, with_boxes=args.boxes)
        print(text)
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
