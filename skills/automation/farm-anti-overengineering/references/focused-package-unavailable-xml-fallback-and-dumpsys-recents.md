# Fallback Focused Package Unavailable & UI XML Recovery (tiktok-luot nuoi acc)

## Bối cảnh & Nguyên nhân gốc
Trên các máy farm Android (Samsung S7), trong quá trình chuyển màn hình, hiển thị popup/overlay hoặc khi hệ thống trả về `mCurrentFocus=null` / `mFocusedApp=null` trong `dumpsys window`, `parse_focused_activity` không tìm thấy match nào và trả về `{"package": None, "activity": None}`.
Hệ quả trước đây:
- `safety_check` nhận `focus_pkg = None`.
- Mặc dù ATX hoặc ADB UI Automator đã dump được XML giao diện TikTok (`xml_available=True`), `safety_check` vẫn ngắt phiên với lỗi:
  `SAFETY_FAILED: focused package unavailable`
  gây gián đoạn feed session và các batch tự động hóa dù app TikTok thực tế vẫn đang hiển thị ở foreground.

## Giải pháp 2 lớp (Two-Layer Fallback Pattern)

### Lớp 1: Fallback regex & Dumpsys Recents trong `flows/observe.py`
1. **Fallback Regex trong `parse_focused_activity(output)`**:
   - Khi `FOCUS_RE.findall(output)` không tìm thấy match (`matches` rỗng):
   - Quét regex trực tiếp các package TikTok đã biết (`com.ss.android.ugc.trill`, `com.zhiliaoapp.musically`, `com.ss.android.ugc.aweme`) trong `output` dumpsys:
     `re.search(re.escape(target_pkg) + r"/([A-Za-z0-9_.$/]+)", output)`
   - Nếu có activity, trả về cả package và activity. Nếu xuất hiện chuỗi package trong dumpsys, trả về `{"package": target_pkg, "activity": None}`.
2. **Fallback Query `dumpsys activity recents` trong `get_focused_activity(ctx)`**:
   - Nếu vòng lặp thử qua `dumpsys window` và `dumpsys activity activities` vẫn trả về `package: None`, truy vấn thêm `dumpsys activity recents` trước khi bỏ cuộc.

### Lớp 2: Phục hồi Focus từ UI XML trong `core/safety.py`
1. **Bổ sung tham số `raw_xml: str | None = None` vào `safety_check`**:
   - `observe.py` truyền `raw_xml=xml_text` / `current_xml_text` vào các điểm gọi `safety_check`.
2. **Nhận diện TikTok UI qua XML Content**:
   - Kiểm tra `is_tiktok_xml`:
     ```python
     is_tiktok_xml = bool(
         raw_xml
         and (
             expected in raw_xml
             or "com.zhiliaoapp.musically" in raw_xml
             or "com.ss.android.ugc.trill" in raw_xml
             or "Đề xuất" in raw_xml
             or "Bạn bè" in raw_xml
         )
     )
     ```
3. **Phục hồi an toàn kèm Warning Log**:
   - Khi `(focus_pkg in SYSTEM_OVERLAY_PACKAGES or focus_pkg is None) and xml_available and (is_known_tiktok_screen or is_tiktok_xml)`:
     ```python
     logger.warning(
         "Recovered focus_pkg to %s (focus_pkg=%s, detected=%s, is_known_tiktok_screen=%s, is_tiktok_xml=%s)",
         expected,
         focus_pkg,
         detected,
         is_known_tiktok_screen,
         is_tiktok_xml,
     )
     focus_pkg = expected
     ```
   - Thay vì văng lỗi `SAFETY_FAILED ("focused package unavailable")`, phiên tiếp tục chạy bình thường vì bằng chứng UI XML xác nhận app vẫn đang ở màn hình TikTok.

## Nguyên tắc áp dụng
- Không đoán mò: Chỉ phục hồi `focus_pkg = expected` khi `xml_available=True` VÀ (đã phân loại được screen TikTok hoặc có bằng chứng package/text rõ ràng trong `raw_xml`).
- Nếu không có XML (`xml_available=False`), vẫn giữ nguyên `SAFETY_FAILED ("focused package unavailable")` để đảm bảo an toàn.
