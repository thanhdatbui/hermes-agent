# Xử Lý ADB Screencap Byte Stream Hỏng / Rỗng và PIL Image.open

## 1. Triệu Chứng & Hiện Trường
Khi thiết bị Android (đặc biệt các máy farm cũ như Samsung J7/S7 hoặc máy chịu tải cao) bị lag hoặc nghẽn USB/ADB transport:
- Lệnh `adb exec-out screencap -p` trả về byte rỗng `b""` hoặc stream byte dở dang không đủ header chuẩn PNG.
- Khi truyền `io.BytesIO(img_bytes)` vào `PIL.Image.open()`, thư viện Pillow ném ra ngoại lệ:
  `PIL.UnidentifiedImageError: cannot identify image file <_io.BytesIO object at 0x...>` (hoặc `OSError`, `ValueError`).
- Nếu không có try-except bọc hoặc thiếu validation magic bytes, luồng nuôi acc / lướt feed sẽ bị dừng đột ngột (Farm Alert dừng phiên).

## 2. Anti-Pattern Cần Tránh
- Gọi trực tiếp `Image.open(io.BytesIO(img_bytes))` mà không kiểm tra độ dài tối thiểu và magic bytes.
- Chỉ bắt `Exception` chung chung hoặc không bắt `UnidentifiedImageError`, để lọt lỗi làm crash runner.
- Giả định ADB screencap luôn trả về ảnh PNG hợp lệ 100%.

## 3. Quy Chuẩn Xử Lý (Defensive Guard)

### A. Kiểm tra Magic Bytes PNG
Header chuẩn của file PNG luôn bắt đầu bằng 8 bytes: `b"\x89PNG\r\n\x1a\n"`.
```python
if not img_bytes or len(img_bytes) < 8 or not img_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
    return fallback_value  # 0 đối với dhash, None đối với luma_hash
```

### B. Bọc Khối Image.open bằng Tuple Ngoại Lệ Đầy Đủ
Luôn bọc `Image.open` và các thao tác `convert`/`resize` bằng:
```python
from PIL import Image, UnidentifiedImageError

try:
    img = Image.open(io.BytesIO(img_bytes)).convert("L")
    # ... xử lý tiếp ...
except (UnidentifiedImageError, OSError, ValueError):
    return fallback_value
```

### C. Cơ Chế Fallback Fail-Closed
- **Trong hàm băm ảnh (`_dhash` tại `screen_verifier.py`):** Trả về `0`. Khi 2 lần chụp liên tiếp đều lỗi, khoảng cách Hamming giữa 2 ảnh lỗi là `_hamming(0, 0) == 0` -> coi màn hình không đổi, không kích hoạt recovery bừa bãi.
- **Trong hàm so sánh ảnh (`_images_differ` tại `agent.py`):** Trả về `None`. Nếu không thể tính hash do ảnh hỏng, fallback an toàn sang so sánh raw bytes `img_a != img_b`.
