# AI Recovery & Screen Navigation: XML-First & Anti-Coordinate Guidelines (2026-08-21)

## 1. NGUYÊN NHÂN TỌA ĐỘ MÙ GÂY KẸT CAMERA / LIVE STUDIO
Trên độ phân giải chuẩn 1080x1920 của máy Samsung Galaxy S7 (Farm):
- **Thanh Bottom Navigation:**
  - Tab 1: `Trang chủ` (Home) [0, 1794][216, 1920] (Tâm 108, 1857)
  - Tab 2: `Cửa hàng` (Shop) [216, 1794][432, 1920] (Tâm 324, 1857)
  - **Tab 3: `Tạo video (+)` [432, 1794][648, 1920] (Tâm 540, 1857)**
  - Tab 4: `Hộp thư` (Inbox) [648, 1794][864, 1920] (Tâm 756, 1857)
  - Tab 5: `Hồ sơ` (Profile) [864, 1794][1080, 1920] (Tâm 972, 1857)

### 2 BẪY TỌA ĐỘ PHỔ BIẾN:
1. **Lệnh swipe shade / notification dismiss:**
   - Lệnh cũ: `input swipe 540 1800 540 300 250` -> Điểm bắt đầu `(540, 1800)` đè đúng đỉnh nút `+` tạo video. Khi trễ cảm ứng, máy nhận thành click nút `+` -> Nhảy vào Camera.
   - Sửa: `input swipe 540 1540 540 300 250` (Y=1540 an toàn, cách đáy 380px).
2. **Fallback Navigation Coordinate:**
   - `tap_navigation_target` khi miss XML fallback sang `(972, 1857)` hoặc tỷ lệ `(0.9, 0.967)`. Khi tab bar bị che bởi overlay/banner hoặc máy ở trang khác, cú click trúng nút LIVE Studio -> Hiện popup *"Để phát LIVE, bạn cần: Có ít nhất 50 follower"*.
   - Sửa: Xóa bỏ hoàn toàn fallback tọa độ. BẮT BUỘC chỉ click khi tìm thấy Node XML (`text="Hồ sơ"` / `desc="Profile"`). Không thấy -> trả `not-found` an toàn.

## 2. RUNTIME XML-FIRST ENFORCEMENT TRONG AI RECOVERY
Trong `python_runner/ai_recovery/agent.py`:
- `_execute_adb(serial, adb_path, action_type, action_args, ui_xml_raw)`:
  - Khi `action_type == 'tap'`: Bắt buộc kiểm tra `(tx, ty)` có nằm trong `bounds` của Node UI nào trong `ui_xml_raw` không (`b[0] <= tx <= b[2]` và `b[1] <= ty <= b[3]`).
  - Nếu không có node hợp lệ trong XML (tap mù) -> TỪ CHỐI tap, fallback gửi phím `BACK` (`keyevent 4`).

## 3. CLASSIFIER INVARIANTS CHỐNG FALSE POSITIVE TRÊN FEED
Trong `python_runner/core/classifier.py`:
- Caption video trên Feed thường chứa từ: `"Ảnh"` hoặc nhãn `"Có chứa nội dung do AI tạo"`.
- BẮT BUỘC KHÔNG dùng substring matching trên từ đơn `"ảnh"`, `"tạo"`, `"đăng"`.
- Quy tắc nhận diện Camera chuẩn:
  - Chỉ quét element ở nửa dưới màn hình (`Y >= 1000`).
  - Bọc `try/except` quanh `parse_bounds`.
  - Phải có ít nhất 2 chế độ quay KHÁC NHAU (`distinct modes >= 2`) gồm: `{"15s", "60s", "10 phút", "văn bản", "10m", "templates", "photo", "camera"}`.

## 4. QUY TẮC XỬ LÝ POPUP "FOLLOW BẠN BÈ CỦA BẠN"
Trong `benign_popup.py`:
- Khi gặp popup `dismiss_follow_friends_suggestion_popup`: Quét và click toàn bộ các nút `"Follow lại"` / `"Follow back"` xuất hiện trên màn hình để tăng follow chéo, sau đó mới bấm nút `"X"` hoặc `BACK` để thoát về Feed.
