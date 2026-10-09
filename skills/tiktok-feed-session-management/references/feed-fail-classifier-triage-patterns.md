# Chẩn đoán nguyên nhân Feed Fail & False Positive Classifier Search Landing (13/09/2026)

## 1. Hiện tượng & Phân tích hiện trường Ca 2 - Phiên 2/2 (Row 3)
Phiên chạy ghi nhận:
- 50 máy Success
- 29 máy Fail
- 1 máy Trống slot (M66)

### Phân rã theo root cause thực tế:
1. **17 máy Config-Error / Offline**: M22, M34, M40, M53, M57, M62, M67, M70, M72, M73, M75, M76, M77, M78, M79, M80 (`serial not found in adb devices`). Tại thời điểm kiểm tra, `adb devices` chỉ có 74 máy online.
2. **2 máy Rớt USB / Disconnected**: M30, M61 (`device offline or ADB/USB disconnected`).
3. **2 máy vướng Lock phiên trước**: M13, M68 (`device lock active`). Lock được Reaper 5 phút thu dọn tự động sau khi kết thúc ca.
4. **1 máy Trống slot**: M66 (`account row 3 is empty (no username), skipping`).
5. **7 máy vướng UI / Popup / Guard**:
   - M4: Classifier nhận diện nhầm search landing page.
   - M11, M18, M19: Vướng popup khuyến mãi tính năng mới (`feature_promo_overlay`).
   - M12: Chạm nhầm mở camera quay video TikTok (`camera/video creation screen`).
   - M6, M33: Kẹt dialog confirm chuyển tab, swipe recovery không thoát.
   - M74: Kẹt account switcher không mở được.
   - M44: Feed swipe command timeout/mất kết nối shell.

## 2. False Positive: `detect_search_landing_page` trên Feed có EditText ẩn
- **Nguyên nhân cốt lõi**: Trong `core/benign_popup.py`, hàm `detect_search_landing_page` kiểm tra:
  ```python
  has_search_input = any(element.attrib.get("class", "").endswith("EditText") ...)
  search_tab_terms = {"top", "người dùng", "users", "video", "videos", ...}
  is_search_results = has_search_input and has_search_tabs
  ```
- Trên một số video Feed thông thường (đặc biệt là dạng bài viết hình ảnh / carousel), TikTok inject các node ẩn `android.widget.EditText` (bounds nhỏ, text rỗng). Đồng thời từ khóa `"Video"` nằm trong content-desc của nút media Feed ("Video").
- Hai điều kiện trên vô tình làm `is_search_results` thỏa mãn `True` dù màn hình đang hiển thị hoàn toàn bình thường ở tab `for-you`.
- Khi đó, classifier trả về `manual-needed:popup` với reason `"TikTok search landing / suggestions page detected"`, khiến session dừng giữa chừng để bảo vệ an toàn.

## 3. Quy tắc kiểm tra O(1) cho Coordinator
- Khi gặp Farm Alert `manual-needed:popup` hoặc `unexpected popup/dialog marker detected`:
  1. Kiểm tra ngay log máy cụ thể tại:
     `D:/Taadaa/runtime/kibe/live/<date>/<session>/machines/machine_<N>/<run_id>/log.jsonl`
  2. Parse XML cuối cùng trong thư mục artifact để xem classification reason:
     ```python
     from core.classifier import classify_tiktok_screen
     from flows.observe import parse_xml
     res = classify_tiktok_screen(parse_xml(xml_content))
     # res.screen, res.reasons
     ```
  3. Đính kèm screenshot minh chứng bằng cú pháp an toàn: `MEDIA:<path_to_png>` với dấu gạch chéo xuôi `/`.

## 4. Triage Nhanh Danh Sách Máy Fail Từ Báo Cáo Watchdog (16/09/2026)

### Quy trình trích xuất O(1) không quét đĩa diện rộng:
Khi watchdog báo cáo danh sách N máy fail, Coordinator KHÔNG dùng `os.walk` hay quét rộng. Trích xuất trực tiếp file summary của từng máy theo đường dẫn xác định:
`D:/Taadaa/runtime/kibe/live/<YYYY-MM-DD>/<shift-folder>/<run_id>/machines/machine_<N>/<run_id>/summary.txt`

Trích xuất 4 trường trọng yếu:
- `final_status`
- `stop_reason`
- `total_swipes_completed`
- `total_swipes_requested`

### Phân loại 4 nhóm chuẩn hỗ trợ ra quyết định:
1. **Nhóm 1 — Hoàn thành gần đủ/đủ quota (swipes >= requested - 2):**
   - Thường gặp: Dừng ở gate kiểm tra XML profile cuối (`navigation target profile not found in XML`), popup đánh giá/kết thúc phiên, frame chụp màn hình invalid.
   - **Đánh giá & Xử lý:** Tài khoản đã hoàn thành phần lớn (hoặc 100%) thời lượng nuôi feed và thời gian on-screen. **KHÔNG cần chạy bù hoặc can thiệp khẩn**, để tài khoản nghỉ ngơi bình thường.
2. **Nhóm 2 — Dừng giữa chừng do popup / feed (0 < swipes < requested - 2):**
   - Thường gặp: `unexpected popup/dialog marker detected`, `feed not confirmed`, `contact_follow_suggestion`.
   - **Đánh giá & Xử lý:** Xem xét selector dialog xem có phải popup lành tính cần whitelist thêm hay không; nếu tỷ lệ toàn farm <= 15% thì an toàn.
3. **Nhóm 3 — Lỗi chuyển tài khoản (swipes = 0):**
   - Thường gặp: `manual-needed:account-switcher-not-open: profile screen remained after switch-anchor tap`.
   - **Đánh giá & Xử lý:** TikTok kẹt UI bottom-sheet hoặc lag profile. Cần kill TikTok, mở lại hoặc kiểm tra layout nút đổi nick.
4. **Nhóm 4 — Ngoại vi / Cáp ADB:**
   - Thường gặp: `Device serial '...' was not found in adb devices`.
   - **Đánh giá & Xử lý:** Máy bị rớt kết nối vật lý, đứt cáp hoặc crash daemon adbd. Tuyệt đối không debug code runner, cần kiểm tra cổng USB/hub.

### Kiểm tra giải phóng Device Lock trước khi chuyển ca:
Sau khi phân loại xong máy fail, kiểm tra ngay `D:/Taadaa/tiktok-luot nuoi acc/locks/*.lock` để đảm bảo farm đã giải phóng toàn bộ lock (0 lock tồn đọng), cho phép các watchdog cuốn chiếu tiếp theo (`post-evening-account-reconcile`, `post-evening-avatar`, `post-evening-gpm-login`) vận hành thông suốt.
