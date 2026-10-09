# Multilingual Popups & Navigation Confirmation Fallback Patterns

## 1. Multilingual Modal & Subpage Gating (Case 180: Edit Name / Add Name)
### Bối cảnh & Nguyên nhân gốc
- Farm thiết bị Samsung (S7 G930F/W8, S8, Note...) thường chạy các bản ROM quốc tế khác nhau (Việt Nam, Đức `de-AT`, Mỹ `en-US`...).
- Mặc dù hệ thống có lệnh set `persist.sys.locale vi-VN`, TikTok app vẫn có thể kích hoạt chuỗi giao diện tiếng Anh hoặc tiếng Đức tùy thuộc vào cache hoặc bundle app.
- Khi tài khoản mới chưa đặt Tên hiển thị (Display Name):
  - TikTok hiển thị nút trên đầu trang Hồ sơ: tiếng Việt là `+ Thêm tên`, tiếng Anh là `+ Add name`, tiếng Đức là `+ Namen hinzufügen`.
  - Nếu click vào, app mở trang đổi tên phụ (`edit_name_subpage_overlay`):
    - Tiếng Việt: `"Thêm tên bạn mong muốn"`, `"Bạn chỉ có thể đổi tên một lần mỗi 7 ngày"`.
    - Tiếng Anh: `"Add your preferred name"`, `"Your name can only be changed once every 7 days"`.
    - Tiếng Đức: `"Füge deinen bevorzugten Namen hinzu"`.

### Quy tắc triển khai (Anti-Pattern vs Best Practice)
- **CẤM**: Chỉ kiểm tra chuỗi tiếng Việt trong các hàm detect popup/overlay (`_detect_edit_name`, `detect_edit_name_subpage`).
- **CHUẨN HÓA**: Mọi bộ nhận diện popup/subpage BẮT BUỘC phải đối soát tuple từ khóa đa ngôn ngữ:
  ```python
  has_input_hint = any(k in combined for k in (
      "thêm tên bạn mong muốn", "them ten ban mong muon",
      "add your preferred name", "füge deinen bevorzugten namen hinzu",
  ))
  has_7days_rule = any(k in combined for k in (
      "chỉ có thể đổi tên", "chi co the doi ten", "đổi tên một lần",
      "changed once every 7 days", "einmal alle 7 tage",
  ))
  ```
- **Chặn anchor chuyển nick**: Bộ lọc anchor tên nick tại Profile (`is_excluded_name`) phải bổ sung đầy đủ các biến thể đa ngôn ngữ:
  `{"thêm tên", "add name", "namen hinzufügen", "füge einen namen hinzu"}`.

---

## 2. Empty Feed Tab Navigation Confirmation Fallback
### Bối cảnh & Nguyên nhân gốc
- Tài khoản mới (hoặc tài khoản chưa follow ai) khi chuyển sang tab **Bạn bè (Friends)** hoặc **Đang follow (Following)** sẽ gặp trang rỗng kèm gợi ý kết nối danh bạ / Facebook (`contact_follow_suggestion`).
- Trước đây cơ chế fallback `empty_feed_fallback_for_you` chỉ nằm bên trong vòng lặp vuốt (`swipe loop`).
- Hậu quả: Khi runner bấm chuyển tab và chụp ảnh đối soát tại bước `switch_friends_13_navigation_confirm`, bộ phân loại nhận diện popup gợi ý danh bạ và gán `manual-needed:popup`. Khi runner đóng popup, app quay về For-You feed -> runner đối soát thấy mismatch (`expected: Friends`, `detected: for-you`) và dừng toàn bộ phiên nuôi với lỗi `manual-needed`.

### Giải pháp chuẩn hóa trong `feed_swipe_smoke.py`
- Tại bước `_navigation_confirm`: Nếu đang chuyển sang tab `FEED_TYPE_FRIENDS` hoặc `FEED_TYPE_FOLLOWING` mà gặp `manual-needed:popup` hoặc xác nhận rỗng qua `_has_friends_feed_content(confirm)`, kích hoạt ngay luồng **fallback êm đẹp về For-You**:
  ```python
  if manual_guard.record(_safety_from_row(ctx, confirm)):
      if next_feed_type in {FEED_TYPE_FOLLOWING, FEED_TYPE_FRIENDS} and (
          confirm.get("detected") in {"manual-needed:popup", "manual-needed:blanket-dismiss"}
          or not _has_friends_feed_content(confirm)
      ):
          # Kích hoạt fallback_feed_tab về For-You, gán degraded status thay vì ném lỗi
          return _fallback_to_for_you(ctx, ...)
  ```

---

## 3. Cưỡng chế Locale & Tắt màn hình trong Watchdog Provisioning
- Trong `farm_app_provision_watchdog.py`, không chỉ chạy `POST_CONFIG_COMMANDS` khi cài đặt app thiếu.
- **Quy tắc**: Kể cả khi thiết bị đã có đủ toàn bộ package và split APK, watchdog khi quét thấy máy rảnh (idle, không có lock) vẫn BẮT BUỘC gọi `apply_post_config`:
  - `persist.sys.locale = vi-VN`
  - `settings put system system_locales vi-VN`
  - `input keyevent 223` (tắt màn hình dưỡng pin)
- Điều này đảm bảo 100% thiết bị không bị trôi về ngôn ngữ gốc của ROM hoặc bị sáng màn hình treo máy.

---

## 4. Closeout Gate Focused Test Timeout
- Khi repo có nhiều bộ test suite liên quan (`test_benign_popup_registry.py` có 166 test, `test_feed_swipe_smoke.py` có 101 test), chạy nối tiếp trên môi trường Windows có thể mất từ 180s - 220s.
- `closeout_gate.py` phải cấu hình `timeout_seconds = min(300, remaining_for_test)` thay vì `min(120, ...)` để tránh ngắt test hợp lệ khi chạy các bộ regression lớn.
