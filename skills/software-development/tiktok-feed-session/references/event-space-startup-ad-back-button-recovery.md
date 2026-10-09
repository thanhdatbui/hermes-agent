# Event Space / Campaign Hub Startup Ad Recovery (Case 130)

## 1. Hiện tượng & Nhận diện lỗi
- **Farm Alert:** `startup ad/splash marker detected`.
- **Màn hình hiện trường:** "Không gian sự kiện" (Event Space / Campaign Hub) — trang quảng cáo chiến dịch toàn màn hình (Megalive ngày đôi, Đăng ký sự kiện...) xuất hiện ngay sau khi mở app TikTok.
- **Đặc điểm UI:**
  - Tiêu đề "Không gian sự kiện" hoặc "Event Space".
  - Góc trên bên trái có nút điều hướng quay lại (`←`, content-desc "Quay lại" / "Navigate up" / "Back").
  - Không có các nút skip quảng cáo truyền thống (như "Bỏ qua quảng cáo", "Skip ad", "Vuốt lên để bỏ qua", icon "✕" đóng).

## 2. Nguyên nhân cốt lõi (Anti-Pattern)
- Trong `python_runner/flows/feed_swipe_smoke.py`:
  - Bộ phân loại màn hình gắn cờ trạng thái `STARTUP_AD_SCREEN` (`manual-needed:startup-ad`).
  - Hàm `_startup_ad_skip_selector()` lần lượt kiểm tra:
    1. `_find_startup_ad_close_button()` (tìm nút Đóng / icon close).
    2. `_find_startup_ad_skip_button()` (tìm text "Bỏ qua quảng cáo", "Skip ad").
    3. `_startup_ad_has_swipe_marker()` (kiểm tra swipe-up marker).
  - Do màn hình "Không gian sự kiện" chỉ có nút quay lại ở header (`←`), cả 3 hàm trên đều trả về `None`.
  - Luồng rơi vào nhánh fallback blind tap tại `DEFAULT_SKIP_TAP_CENTER` (tọa độ dưới đáy 950, 1700), chạm trúng card sản phẩm hoặc vùng chết và không đóng được màn hình, dẫn đến dừng phiên và bắn Farm Alert.

## 3. Giải pháp chuẩn (Canonical Fix)
Tại `python_runner/flows/feed_swipe_smoke.py`:
1. **Hàm nhận diện nút back sự kiện:**
   ```python
   def _find_startup_ad_event_space_back_button(attempt: dict[str, Any]) -> UIElement | None:
       xml_path = attempt.get("xml_path")
       if not xml_path:
           return None
       try:
           xml_content = Path(str(xml_path)).read_text(encoding="utf-8")
           root = parse_xml(xml_content)
       except Exception:
           return None

       xml_lower = xml_content.lower()
       page_text = str(attempt.get("page_text") or "").lower()
       if "không gian sự kiện" not in xml_lower and "event space" not in xml_lower and "không gian sự kiện" not in page_text and "event space" not in page_text:
           return None

       elements = list(iter_elements(root))
       back_terms = ("quay lại", "navigate up", "back", "←")
       candidates = []
       for element in elements:
           if not element.center or not element.bounds:
               continue
           left, top, right, bottom = element.bounds
           width = right - left
           height = bottom - top
           if top >= int(SCREEN_HEIGHT_PX * 0.20):
               continue
           if width <= 0 or height <= 0:
               continue
           if width > int(SCREEN_WIDTH_PX * 0.40) or height > int(SCREEN_HEIGHT_PX * 0.20):
               continue
           if _element_has_any_term(element, back_terms):
               candidates.append((0, top, left, element))
           elif left < int(SCREEN_WIDTH_PX * 0.25):
               candidates.append((1, top, left, element))

       if not candidates:
           return None
       candidates.sort(key=lambda item: (item[0], item[1], item[2]))
       return candidates[0][3]
   ```
2. **Tích hợp vào `_startup_ad_skip_selector`:**
   - Ưu tiên gọi `_find_startup_ad_event_space_back_button(attempt)` trước `_find_startup_ad_close_button`.
   - Nếu tìm thấy, trả về selector action `'tap_back_button'` cùng tọa độ tâm (`event_back_button.center`).
3. **Cập nhật `_perform_startup_ad_skip`:**
   - Thêm `'tap_back_button'` vào tập action cho phép tap:
     ```python
     if action in {"tap_skip_ad", "tap_close_ad", "tap_default_skip", "tap_back_button"}:
         center = selector.get("center")
         ...
     ```

## 4. Quy trình kiểm chứng & Chốt phiên
- **Compile check:** `python -m py_compile "D:/Taadaa/tiktok-luot nuoi acc/python_runner/flows/feed_swipe_smoke.py"`.
- **Focused Unit Test:** Kiểm tra unit test mock XML chứa "Không gian sự kiện" và nút back `←` xác nhận `_startup_ad_skip_selector` trả về `tap_back_button`.
- **Gate 0 Live Canary:** Chạy runner chính thức trên máy gặp alert (`run-feed-session.ps1 -Machines <N> -Row 1 -RecoveryTestSwipes 2 -SkipAccountWorkbookSync -Run`) để xác nhận máy tự thoát màn hình sự kiện và hoàn thành 2/2 swipes về For You.
- **Gate 0.5 Docs:** Ghi nhận Case 130 vào `docs/farm-automation-cases.md`.
