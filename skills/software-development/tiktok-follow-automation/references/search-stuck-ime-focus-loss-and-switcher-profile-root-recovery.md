# Case UI-56: Kẹt Màn Hình Search, IME Focus Loss Và Hệ Quả VERIFY_IDENTITY Fail

## 1. Triệu chứng & Hiện trường
- Runner dừng phiên hoặc báo lỗi khi tìm kiếm UID (ví dụ Máy 51 kẹt tìm kiếm `@tranngan8642`).
- Màn hình thiết bị dừng ở giao diện Tìm kiếm của TikTok, ô tìm kiếm đã điền UID, bàn phím mềm Samsung/Gboard đang mở, kèm theo dropdown gợi ý (autocomplete/history) bên dưới.
- Không gửi được lệnh submit tìm kiếm, runner thoát ra với màn hình Search vẫn giữ nguyên.
- Ở các phiên chạy tiếp theo (hoặc retry), `open_tiktok()` phát hiện app TikTok đang foreground nên không relaunch; runner tiếp tục chuyển sang bước `switch_account_and_verify()` -> `open_account_switcher()` -> `open_profile_root()`.
- Do màn hình Search và bàn phím ảo che khuất hoàn toàn thanh điều hướng dưới (bottom navigation bar), `open_profile_root()` không tìm thấy nút "Hồ sơ" (`PROFILE_TARGET_NOT_FOUND`), dẫn đến lỗi:
  `res.status = STATE_CONFIG_ERROR`
  `res.reason = "VERIFY_IDENTITY fail — nick không khớp @... (hoặc switcher fail)"`

## 2. Root Cause Cơ Chế Sâu
1. **Resource-ID Drift của Nút Tìm Kiếm (`_unique_search_submit`):**
   - Hàm `_unique_search_submit` đặt điều kiện lọc cứng:
     `(node.get("resource_id") or "").rstrip("/").endswith("id/tv_search_textview")`
   - Khi TikTok cập nhật layout (hoặc một số bản build biến thể), nút "Tìm kiếm" màu đỏ trên thanh header có thể đổi resource-id hoặc không có ID chuẩn này, khiến hàm trả về `None`.
2. **Cạm Bẫy Focus Loss Khi Mở Bàn Phím Ảo (IME Occlusion Fallback):**
   - Khi `submit is None`, code có nhánh fallback gửi phím `adapter.keyevent(66)` (`KEYCODE_ENTER`).
   - Tuy nhiên, nhánh fallback đặt điều kiện bảo vệ `valid_input`:
     `n.get("focused") is True or str(n.get("focused", "")).lower() == "true"`
   - Khi bàn phím mềm hệ thống (Samsung Keypad / Gboard) hoặc dropdown gợi ý autocomplete hiển thị, accessibility tree của Android thường chuyển active focus sang cửa sổ IME hoặc gán `focused="false"` cho `EditText`.
   - Hệ quả: `valid_input` trả về `False` -> runner bỏ qua `keyevent(66)` -> log `search input not proven focused with uid for @<uid>, skipping ENTER`.
   - Kết quả là lệnh tìm kiếm không được submit, và hàm `_nav_search` trả về `False` mà không thực hiện dọn dẹp (không đóng bàn phím, không bấm Back về Feed).
3. **Hiệu Ứng Domino Lên Switcher & Profile Root:**
   - Khi `open_tiktok()` kiểm tra `_feed_already_open()` hoặc package hiện tại, nếu TikTok vẫn ở foreground nhưng kẹt ở Search, app không được relaunch.
   - Bước tiếp theo `switch_account_and_verify` gọi core switcher tìm tab "Hồ sơ" ở đáy màn hình. Do Search layout chiếm toàn màn hình và bàn phím che kín nửa dưới, tab "Hồ sơ" hoàn toàn biến mất khỏi XML dump.

## 3. Giải Pháp & Quy Tắc Khắc Phục Chuẩn

### A. Nới Lỏng Nhận Diện Nút Submit
Không ràng buộc duy nhất ID `id/tv_search_textview`. Nhận diện nút submit dựa trên:
- Class: `android.widget.Button` hoặc `android.widget.TextView`.
- Thuộc TikTok package hợp lệ (`is_tiktok_package`).
- Text hoặc content-desc chuẩn hóa nằm trong `{"tìm kiếm", "search"}`.
- Tọa độ vùng header tìm kiếm (`bounds[1] < 400`).

### B. Fallback ENTER Chống IME Focus Loss
Trong `_nav_search`:
- Nếu không tìm thấy nút submit qua XML, kiểm tra sự hiện diện của `EditText` thuộc TikTok chứa đúng UID mục tiêu (`_normalize_search_value(n.get("text")) == _normalize_search_value(uid)`).
- Nếu text khớp, **cho phép gửi `adapter.keyevent(66)` ngay cả khi `focused is False`**, miễn là node thuộc TikTok package và nằm ở vùng search bar trên cùng (`y < 400`). Bàn phím đang mở đã ngầm định ô input đang active.
- Sau khi gửi `keyevent(66)`, chờ 1.5–2s để kết quả tìm kiếm load.

### C. Thoát Khỏi Màn Hình Search Khi Thất Bại & Pre-Switcher Feed Guard
- Trong `_nav_search`: nếu không thể tìm thấy kết quả hoặc bị fail, trước khi `return False`, luôn thực hiện đóng bàn phím (`adapter.press_back()`) và gọi `_back_to_feed(engine)` để không để lại màn hình Search kẹt cho lượt tiếp theo.
- Trong `follow_engine.py`: trước khi gọi `switch_account_and_verify()`, nếu màn hình hiện tại đang ở Search hoặc không thấy bottom nav, gọi `self.ensure_feed_for_follow()` để phục hồi về Feed trước khi mở Profile tab.
