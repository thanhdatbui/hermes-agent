# WinRT OCR Action Button Fallback & Zero-Token Watchdog Delivery (TikTok Follow)

## Bối cảnh & Vấn đề giải quyết
1. **Biến dị UI & nghẽn XML dump trên TikTok 46.x**:
   - Nút Follow liên tục đổi `resource_id` (`id/fds`, `id/ff8`, `id/fij`, `id/fi6`, `id/flo`, `id/fo4`...) hoặc bị làm phẳng thành plain TextView không clickable trong hierarchy.
   - Khi `atx-agent` bị lag hoặc đơ, `adapter.dump_ui()` tốn 15–30s hoặc văng `FollowAdapterError`, dẫn đến kết quả phân loại bị gán `"unknown"`, kích hoạt vòng lặp reload tốn kém hoặc báo `MANUAL_REVIEW` oan.
2. **Chi phí Quota & Token khi chạy Cronjob**:
   - Nếu cronjob để `no_agent=False`, mỗi lần chạy Hermes phải tốn token LLM chỉ để đọc kết quả stdout rồi in lại.
   - Ép LLM đọc ảnh (`browser_vision`) trên hàng trăm lượt follow gây cháy quota và chạm rate limit.

---

## Kiến trúc Giải pháp: Dual-Track OCR Fallback (Zero-Token)

### 1. Module Core OCR (`follow_runner/core/ocr.py`)
- Sử dụng PowerShell script `D:/Taadaa/tools/ocr_boxes.ps1` gọi Windows Native WinRT OCR (`Windows.Media.Ocr`).
- Chạy 100% offline trên CPU, tốc độ 0.2s - 0.5s/ảnh, tiêu tốn **0 token LLM**.
- Chuẩn hóa text tiếng Việt (`norm_text`) loại bỏ dấu tổ hợp (NFKD) để so khớp bền bỉ.
- Phân vùng nhận diện: Chỉ quét dải header `y < 1200` để loại bỏ các nút follow của video/gợi ý bên dưới.

### 2. OCR Fallback khi Tap Follow (`_tap_follow_button` trong `mode1_search_follow.py`)
- **Ưu tiên 1 (Semantic XML)**: Tìm nút qua `_action_targets(xml_text, markers)`.
- **Cứu hộ 2 (OCR Screen Center)**:
  ```python
  if len(matches) == 1:
      tap_center(adapter, matches[0])
      return True

  if hasattr(adapter, "ocr_screen"):
      try:
          from ..core.ocr import find_follow_button_center_ocr
          boxes = adapter.ocr_screen()
          center = find_follow_button_center_ocr(boxes, y_max=1200)
          if center is not None:
              adapter.tap(center[0], center[1])
              return True
      except Exception:
          pass
  return False
  ```

### 3. OCR Fallback khi Nghiệm thu trạng thái (`verify_after_tap` trong `verify_follow.py`)
- Sau khi tap, bọc `_classify_with_fallback()`:
  - Nếu `classifier(_dump())` văng exception (dump rỗng/lỗi XML) hoặc trả về `"unknown"`:
  - Tự động gọi `adapter.ocr_screen()` và `classify_button_from_ocr(boxes)`.
  - Nếu thấy từ khóa `"followed"` (*Nhắn tin, Message, Đã follow, Đang theo dõi, Bạn bè...*) -> Xác nhận `followed` ngay lập tức, triệt tiêu reload thừa.
  - Nếu thấy từ khóa `"not_followed"` (*Follow, Follow lại, Theo dõi...*) -> Xác nhận `not_followed`.

---

## Quy tắc Telegram Media Delivery trong Cron (`no_agent=True`)
Khi watchdog chạy chế độ `no_agent=True`, stdout được Telegram Gateway gửi nguyên văn:
- **CẤM** in text thuần như `Ảnh: D:\...` hoặc `| Ảnh: ...` (Gateway chỉ coi là text thường, không tải ảnh).
- **BẮT BUỘC** in định dạng chuẩn:
  ```python
  p_posix = str(proof_path).replace("\\", "/")
  print(f"✅ [FOLLOW] @{username} -> OK\nMEDIA:{p_posix}", flush=True)
  ```
- **Invariant đường dẫn**: Bắt buộc dùng dấu gạch xuôi `/`, tuyệt đối không dùng gạch ngược Windows `\` vì sẽ bị lỗi escape character parser của Gateway (`\t`, `\r`, `\n`).
