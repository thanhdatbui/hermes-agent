# Xử lý thoát màn hình "Không gian sự kiện" / "Sự kiện LIVE" (Event Space Overlay)

## Hiện tượng & Nguyên nhân gốc
- **Màn hình kẹt:** TikTok hiển thị subpage / overlay "Không gian sự kiện" (chứa các thẻ sự kiện như "MEGALIVE...", "SIÊU SALE NGÀY ĐÔI", "Đăng ký", với top bar có mũi tên Back "←").
- **Nguyên nhân:**
  - Vuốt màn hình (feed swipe) thông thường không thể thoát khỏi overlay này.
  - Hệ thống thiếu quy tắc nhận diện trong `core/classifier.py` và `flows/benign_popup.py`, dẫn đến phân loại nhầm thành `manual-needed:sponsored-ad-feedback` hoặc popup không thể đóng tự động, làm dừng phiên feed.

## Giải pháp chuẩn hóa (Dual-Path)
1. **Quy tắc nhận diện (Detector):**
   ```python
   def detect_event_space_overlay(xml_content: str | None = None, ocr_text: str | None = None) -> bool:
       """Phát hiện overlay/subpage Không gian sự kiện hoặc Sự kiện LIVE."""
       markers = [
           "Không gian sự kiện",
           "Sự kiện LIVE",
           "Khong gian su kien",
           "Su kien LIVE",
       ]
       text_data = (xml_content or "") + " " + (ocr_text or "")
       return any(m in text_data for m in markers)
   ```

2. **Hành động thoát (Dismiss Handler):**
   ```python
   def dismiss_event_space_overlay(ctx: DeviceContext) -> PopupDismissResult:
       """Đóng overlay Không gian sự kiện bằng phím BACK để trở lại Feed."""
       before = {"screen": "event_space_overlay"}
       send_device_back_key(ctx)
       time.sleep(1.0)
       return PopupDismissResult(
           dismissed=True,
           reason="dismissed_event_space_overlay",
           before_attempt=before,
           popup_closed=True,
       )
   ```

3. **Tích hợp vào Benign Popup Registry:**
   - Trong `flows/benign_popup_registry.py`, đăng ký entry:
     ```python
     register_popup_handler(
         RegistryEntry(
             "event_space_overlay",
             80,
             _detect_event_space,
             _dismiss_event_space,
             True,
             "manual",
         )
     )
     ```
   - Điều này giúp toàn bộ các điểm kiểm tra popup trước/sau swipe trong `feed_swipe_smoke.py` tự động nhận diện và gửi phím BACK mà không bị dừng phiên.
