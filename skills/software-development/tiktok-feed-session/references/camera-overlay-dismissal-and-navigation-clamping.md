# Camera Creation Overlay Dismissal & Navigation Clamping (Case 100, 102)

## 1. Hiện tượng & Nguyên nhân gốc rễ
- **Hiện tượng:** Khi đang lướt feed hoặc chuyển tab điều hướng (`tap_profile`, `tap_home`), máy bất ngờ rơi vào màn hình quay video / chụp ảnh Camera của TikTok (có nút ✕ ở góc trên bên trái, thanh công cụ "Thêm âm thanh", "Lật", "Hẹn giờ", các chế độ quay "15s", "60s", "10 phút", "Văn bản", "Mẫu").
- **Nguyên nhân kích hoạt:**
  1. **Horizontal Swipe Drift:** Cử chỉ vuốt ngang từ trái sang phải (Swipe Right) trên tab FYP kích hoạt gesture mở Camera.
  2. **Mis-tap nút `+` ở thanh đáy:** Thanh điều hướng đáy có nút Tạo/Camera ở chính giữa (`x = 400..680, y >= 1700`). Khi tính toán fallback hoặc bounds lệch, tap rơi vào vùng này sẽ mở Camera.
  3. **Lỗi Classifier & Dismiss:** Classifier cũ chỉ quét mode quay ở nửa dưới màn hình (`y >= 1000`), bỏ sót camera có nút ✕ ở trên cùng hoặc công cụ camera bên phải. Dismiccer cũ chỉ gửi `KEYCODE_BACK` mà không ưu tiên tap nút ✕.

## 2. Quy tắc xử lý chuẩn
1. **Phân loại màn hình Camera (`classifier.py`):**
   - Quét đầy đủ các mode quay: "10 phút", "60s", "15s", "văn bản", "templates", "photo", "live", "story", "tạo", "quay".
   - Quét các công cụ: "lật", "hẹn giờ", "tốc độ", "bộ lọc", "thêm âm thanh", "hiệu ứng", "làm đẹp".
   - Nhận diện nút đóng ✕ ở `y < 500`.
2. **Dismisser trong Registry (`benign_popup_registry.py` & `benign_popup.py`):**
   - Ưu tiên bóc tách XML tìm nút ✕ đóng ở góc trên bên trái (`y < 400`) để tap trực tiếp.
   - Nếu không có nút ✕ mới fallback gửi `send_device_back_key`.
   - Ghi nhận `source = "xml_after_popup_dismiss"` khi capture lại XML sau khi dismiss.
3. **Whitelist trong `calibrate_screens.py`:**
   - Đưa `camera_creation_overlay` vào danh sách overlay được phép tự động dismiss trước khi thực hiện navigation tap.
4. **Safety Clamping cho Navigation Bar:**
   - Cấm tuyệt đối tap vào vùng giữa `[400..680]` trên thanh đáy `y >= 1700`.
   - Home target: clamp `x: 50..180, y: 1800..1880`.
   - Profile target: clamp `x: 900..1030, y: 1800..1880`.
5. **Account Switcher Matching & UIElement Invariant:**
   - CẤM truyền `center` vào `UIElement(...)` (vì `center` là computed property tính từ `bounds`).
   - Luôn lọc bỏ các nhãn hành động ("Thêm tài khoản", "Add account", "Log in", "Đăng nhập") khỏi matcher tài khoản để tránh nhảy vào flow đăng nhập.
   - Clamp `best_bounds` right edge bằng `min(node.bounds[0] + 700, max_r)` với `max_r = node.bounds[2]`.
