# PIL Screencap Validation, Retry, and Safe Decoding in Android Device Automation

## 1. Context and Problem

Trong môi trường farm Android tự động (đặc biệt các dòng Samsung Galaxy SM-G930F/W8 chạy 40-80 workers song song):
- Lệnh chụp màn hình ADB (`exec-out screencap -p` hoặc socket screencap) thường xuyên gặp tình trạng nghẽn bus USB, ADB transport hiccup, hoặc tiến trình bị ngắt giữa chừng.
- Dữ liệu trả về có thể là:
  - Rỗng (`b""` hoặc 0 bytes)
  - Cụt byte dở dang (truncated PNG data)
  - Chuỗi text báo lỗi của ADB daemon (ví dụ `adb server killed...` hoặc `error: closed`) thay vì binary PNG.
- Khi truyền trực tiếp vào `Image.open(io.BytesIO(png_bytes))`:
  - Pillow ném ra ngoại lệ: `PIL.UnidentifiedImageError: cannot identify image file <_io.BytesIO object at 0x...>` (hoặc `OSError` / `ValueError` tùy phiên bản Pillow).
  - Do nhiều luồng (`screen_verifier.py`, `ai_recovery/agent.py`, `calibrate_screens.py`, `image_navigation.py`) không bọc try-except hoặc chỉ kiểm tra `if not img_bytes:`, ngoại lệ này làm crash toàn bộ worker session của máy đó.

---

## 2. Chuẩn hóa Validation & Try-Except khi load ảnh bằng PIL

Mọi vị trí nhận raw bytes từ screencap / ADB để load bằng PIL BẮT BUỘC tuân thủ 3 lớp bảo vệ:

### Lớp 1: Kiểm tra Magic Bytes & Kích thước tối thiểu
File PNG luôn bắt đầu bằng 8 bytes magic header: `\x89PNG\r\n\x1a\n` (`b"\x89PNG\r\n\x1a\n"`).
Kích thước tối thiểu của một ảnh PNG hợp lệ (IHDR + IEND) ít nhất là 67 bytes.

```python
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"

def is_valid_png_bytes(data: bytes | None) -> bool:
    if not data or not isinstance(data, (bytes, bytearray)):
        return False
    if len(data) < 67:
        return False
    return data.startswith(PNG_MAGIC)
```

### Lớp 2: Safe Image Open & Eager Load
`Image.open()` của PIL mặc định là lazy (chỉ đọc header, chưa giải mã toàn bộ pixel). Để tránh việc `Image.open()` thành công nhưng crash ở bước sau (`.convert("RGB")` hay `.resize()` do truncated PNG), cần gọi `.load()` hoặc bọc toàn bộ khối xử lý trong try-except:

```python
from io import BytesIO
from PIL import Image, UnidentifiedImageError

def safe_load_image(png_bytes: bytes | None) -> Image.Image | None:
    if not is_valid_png_bytes(png_bytes):
        return None
    try:
        image = Image.open(BytesIO(png_bytes))
        image.load()  # Buộc giải mã pixel để bắt lỗi truncated byte ngay lập tức
        return image
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        # Ghi log debug/warning, không để crash worker
        return None
```

### Lớp 3: Bọc Retry khi chụp qua ADB Screencap
Khi nhận ảnh hỏng, thử chụp lại 1–2 lần với độ trễ nhỏ (0.3s - 0.5s) trước khi chuyển sang fallback / degraded mode:

```python
def capture_screen_with_retry(device, max_retries: int = 2, delay: float = 0.5) -> Image.Image | None:
    for attempt in range(max_retries + 1):
        raw = device.screencap()
        img = safe_load_image(raw)
        if img is not None:
            return img
        if attempt < max_retries:
            time.sleep(delay)
    return None
```

---

## 3. Các vị trí thực tế và pattern chuẩn hóa (Đã hoàn thiện 2026-09-06)

1. **`python_runner/ai_recovery/screen_verifier.py` (`_dhash`):**
   - Kiểm tra magic bytes PNG: `if not img_bytes or len(img_bytes) < 8 or not img_bytes.startswith(b"\x89PNG\r\n\x1a\n"): return 0`.
   - Bọc `Image.open(io.BytesIO(img_bytes)).convert("L")` bằng `try ... except (UnidentifiedImageError, OSError, ValueError): return 0`.
   - **BẪY QUAN TRỌNG:** `_dhash` BẮT BUỘC trả về `0` (integer default) khi lỗi, KHÔNG ĐƯỢC trả về `None`. Nếu trả về `None`, hàm `_hamming(h1, h2)` (`bin(h1 ^ h2).count("1")`) sẽ văng lỗi `TypeError: unsupported operand type(s) for ^: 'NoneType'`.
2. **`python_runner/ai_recovery/agent.py` (`_images_differ`):**
   - Import `from PIL import Image, UnidentifiedImageError`.
   - Hàm con `luma_hash(b: bytes) -> bytes | None`:
     - Kiểm tra: `if not b or len(b) < 8 or not b.startswith(b"\x89PNG\r\n\x1a\n"): return None`.
     - Bọc `Image.open(io.BytesIO(b)).convert("L").resize((32, 32))` bằng `try ... except (UnidentifiedImageError, OSError, ValueError): return None`.
   - Fallback an toàn: `if h_a is not None and h_b is not None: return h_a != h_b; return img_a != img_b`.
3. **`python_runner/flows/calibrate_screens.py` (line ~414):**
   - Đang dùng `with Image.open(io.BytesIO(content)) as image:` - cần bọc try-except để không gián đoạn calibrate.
4. **`automation-core/tiktok/image_navigation.py`:**
   - Các hàm template matching nhận screencap cần validate `is_valid_png_bytes()` trước khi gọi `Image.open()`.

---

## 4. Kỷ luật điều tra log trong `.ai-runs` (Tránh Timeout 900s)

- `.ai-runs` chứa hơn 500 thư mục phiên chạy lịch sử với gigabytes ảnh và log jsonl.
- **CẤM TUYỆT ĐỐI:**
  - `grep -rn "error"` quét toàn bộ `.ai-runs` hoặc `runtime`.
  - `find . -name "*.txt" -exec grep ...` không giới hạn độ sâu / mtime.
  - `os.walk()` không lọc bỏ `.git`, `.ai-runs`, `node_modules`.
- **ĐÚNG QUY TRÌNH:**
  - Dùng `python D:/Taadaa/tools/inspect_machine.py <N>` nếu có mã máy.
  - Hoặc chỉ inspect top 1–3 thư mục mới nhất theo timestamp (`ls -td .ai-runs/* | head -n 3`).
