# WinRT OCR Fast-Path & Fallback Rescue for TikTok Follow Automation

## 1. Context & Motivation
Trên TikTok Android (đặc biệt các phiên bản 46.x/47.x), giao diện liên tục biến động:
- `resource_id` của nút Follow (`id/fds`, `id/ff8`, `id/fij`...) liên tục bị obfuscate và thay đổi qua các bản cập nhật.
- `uiautomator dump` XML trên Samsung S7 thường có độ trễ lớn (5s – 15s), dễ văng lỗi timeout hoặc trả về hierarchy rỗng `""` khi giao diện đang render hiệu ứng.
- Khi XML trả về rỗng hoặc không parse được nút bấm, hệ thống cũ thường retry mù quáng, gây nghẽn hàng đợi hoặc abort oan.

Để giải quyết triệt để, hệ thống tích hợp **WinRT OCR Offline native** (tốc độ 0.2s – 0.5s/ảnh) làm tầng bảo vệ kép (dual-layer):
1. **Lớp 1 (Primary Semantic XML)**: Vẫn ưu tiên tìm nút và phân loại theo node bounds chuẩn của XML hierarchy.
2. **Lớp 2 (Fast OCR Fallback)**: Khi XML rỗng, lỗi parse, hoặc trả về `"unknown"`, tự động chụp ảnh màn hình và đọc trực tiếp bằng WinRT OCR Windows để cứu nguy.

---

## 2. Core Architecture (`follow_runner/core/ocr.py`)

Module OCR độc lập offline 100%, không phụ thuộc vào ADB XML dump:

```python
"""WinRT OCR utilities for TikTok follow action classification and targeting."""
from __future__ import annotations

import logging
import re
import subprocess
import unicodedata
from pathlib import Path
from typing import List, Tuple, Optional

logger = logging.getLogger(__name__)
OCR_PS1 = Path(r"D:\Taadaa\tools\ocr_boxes.ps1")

FOLLOWED_KEYWORDS = {
    "nhan tin", "message", "da follow", "dang theo doi",
    "following", "gui tin nhan", "ban be", "friends"
}
NOT_FOLLOWED_KEYWORDS = {
    "follow lai", "follow", "theo doi"
}

def norm_text(s: str) -> str:
    if not s:
        return ""
    s = s.replace("đ", "d").replace("Đ", "D")
    s = "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", s.lower()).strip()

def classify_button_from_ocr(boxes: List[Tuple[str, Tuple[int, int, int, int]]], y_max: int = 1200) -> str:
    """Phân loại trạng thái Profile header (y < y_max) thành followed / not_followed."""
    has_followed = False
    has_not_followed = False
    for text, (x1, y1, x2, y2) in boxes:
        if y1 >= y_max:
            continue
        n_txt = norm_text(text)
        if any(kw in n_txt for kw in FOLLOWED_KEYWORDS):
            has_followed = True
        if any(kw in n_txt for kw in NOT_FOLLOWED_KEYWORDS):
            has_not_followed = True
    if has_followed and not has_not_followed:
        return "followed"
    if has_not_followed and not has_followed:
        return "not_followed"
    return "unknown"

def find_follow_button_center_ocr(boxes: List[Tuple[str, Tuple[int, int, int, int]]], y_max: int = 1200) -> Optional[Tuple[int, int]]:
    """Tính tọa độ tâm (cx, cy) của nút Follow trên màn hình để tap trực tiếp."""
    for text, (x1, y1, x2, y2) in boxes:
        if y1 >= y_max:
            continue
        n_txt = norm_text(text)
        if any(kw in n_txt for kw in NOT_FOLLOWED_KEYWORDS):
            return (x1 + x2) // 2, (y1 + y2) // 2
    return None
```

---

## 3. Adapter Integration (`FollowAdapter.ocr_screen`)

Trong `follow_runner/core/adapter.py`, method `ocr_screen()` chụp ảnh qua `screencap -p` và chuyển qua WinRT OCR trong bộ nhớ tạm (dọn dẹp ngay sau khi đọc):

```python
def ocr_screen(self, timeout: float = 30.0) -> list[tuple[str, tuple[int, int, int, int]]]:
    from .ocr import ocr_screen_boxes
    import tempfile
    try:
        png = self.screencap()
        if not png or len(png) < 100:
            return []
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tf:
            tf.write(png)
            tpath = tf.name
        try:
            return ocr_screen_boxes(tpath, timeout=timeout)
        finally:
            Path(tpath).unlink(missing_ok=True)
    except Exception:
        return []
```

---

## 4. Fallback Points in Flows

### 4.1 Bấm Nút Follow (`mode1_search_follow.py` / `_tap_follow_button`)
Khi XML hierarchy không tìm được đúng 1 nút bấm (do TikTok đổi selector hoặc DOM bị chia cắt):
```python
if len(matches) == 1:
    tap_center(adapter, matches[0])
    time.sleep(random.uniform(2.5, 5.0))
    return True

# OCR Fallback
if hasattr(adapter, "ocr_screen"):
    try:
        from ..core.ocr import find_follow_button_center_ocr
        boxes = adapter.ocr_screen()
        center = find_follow_button_center_ocr(boxes, y_max=1200)
        if center is not None:
            adapter.tap(center[0], center[1])
            time.sleep(random.uniform(2.5, 5.0))
            return True
    except Exception:
        pass
return False
```

### 4.2 Nghiệm Thu Sau Tap (`verify_follow.py` / `verify_after_tap`)
Khi nghiệm thu sau khi tap, nếu `_dump()` rỗng hoặc classifier XML trả về `"unknown"`:
```python
def _classify_with_fallback() -> str:
    try:
        res = classifier(_dump())
    except Exception:
        res = "unknown"
    if (res == "unknown" or not current_dump) and hasattr(engine.adapter, "ocr_screen"):
        try:
            from ..core.ocr import classify_button_from_ocr
            boxes = engine.adapter.ocr_screen()
            ocr_res = classify_button_from_ocr(boxes)
            if ocr_res in ("followed", "not_followed"):
                return ocr_res
        except Exception:
            pass
    return res
```

---

## 5. Cạm Bẫy Kiểm Thử Pytest & Collection Trap

1. **Bẫy ParseError khi dump rỗng**:
   Khi `_dump()` trả về chuỗi rỗng `""`, việc gọi trực tiếp `classifier(dump)` sẽ ném `xml.etree.ElementTree.ParseError: no element found` thay vì trả về `"unknown"`.
   👉 BẮT BUỘC bọc `classifier(_dump())` trong khối `try...except Exception` để khi dump lỗi hoặc rỗng, luồng rơi mượt mà vào nhánh OCR fallback.
2. **Pytest Collection Trap trong `runs/probes/`**:
   Thư mục `runs/probes/` chứa các script thăm dò cũ import các hàm đã bị tái cấu trúc (e.g. `_open_follower_tab`).
   Lệnh chạy broad `pytest` toàn repo sẽ bị crash ở khâu collection (15 errors).
   👉 BẮT BUỘC chạy targeted test:
   `python -m pytest follow_runner/tests/test_ocr.py follow_runner/tests/test_verify_follow.py -q`
