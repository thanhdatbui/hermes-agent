# Transient Focus Drop Recovery, Scoping Trap & Screencap Corrupt Guard (Case 125-128)

*Ghi nhận từ sự cố thực tế trên Taadaa Phone Farm (Máy 69, Máy 46, Máy 27 - 06/09/2026).*

---

## 1. Transient Focus Drop on Navigation Tap & Screen Transition (Case 125, 127)

### Hiện tượng:
- Khi runner gửi lệnh tap thanh điều hướng (Home/Profile) hoặc trong lúc TikTok transition render giữa các video/view, runner query package foreground qua `dumpsys window` và nhận về `None` hoặc rỗng `""`.
- Runner vội vàng đánh giá `is_launcher_or_systemui_or_unknown = True`, gửi phím Back `4` hoặc monkey restart app, dẫn đến dừng phiên với lỗi:
  `TikTok focus lost after navigation tap: unknown` hoặc `SAFETY_FAILED: focused package unavailable`.

### Nguyên nhân cốt lõi:
- Trên các thiết bị Samsung cũ (như Samsung S7), window focus state bị rớt tạm thời trong vài frame chuyển view dù TikTok vẫn đang hiển thị trên màn hình.
- Flow phụ thuộc 100% vào `get_focused_activity` (window focus) mà bỏ quên tầng kiểm tra activity stack (`mResumedActivity`) và tầng bằng chứng UI XML.

### Giải pháp Multi-Tier Fallback chuẩn:
1. **Tier 1 (Resumed Activity Fallback):**
   Kiểm tra `dumpsys activity activities` tìm `mResumedActivity` hoặc `topResumedActivity`. Nếu chứa `expected_package`, khôi phục `post_package = expected_package` và `recovered_focus = True`.
2. **Tier 2 (UI XML Evidence Fallback):**
   Nếu `dumpsys` vẫn không xác định được window, capture nhanh root XML (`capture_required_ui`). Nếu XML chứa package name hoặc các markers đặc trưng của TikTok ("Đề xuất", "Bạn bè", "Following", tab bar), tự động khôi phục `focus_pkg = expected` với log cảnh báo thay vì fail closed sai.
3. **Fail-Closed Boundary:**
   Chỉ fallback sang `expected` khi `focus_pkg is None` HOẶC nằm trong `SYSTEM_OVERLAY_PACKAGES`. Nếu focus thực sự là package của bên thứ ba khác (launcher ngoài, browser lạ), BẮT BUỘC giữ nguyên fail closed.

---

## 2. Scoping Trap in Fallback Exception Handlers (Case 126)

### Cạm bẫy:
- Khi viết logic fallback (ví dụ: xử lý tài khoản placeholder khi `verify_selected_account` ném `AccountSwitcherError`), lập trình viên vô tình đặt khối `if is_placeholder_candidate: ... else: ...` ra ngoài khối `except AccountSwitcherError:` (sai thụt lề).
- Khi hàm chạy vào luồng bình thường (happy path, không có exception), biến `recaptured_xml` chưa từng được khởi tạo, dẫn đến crash:
  `UnboundLocalError: cannot access local variable 'recaptured_xml' where it is not associated with a value`.

### Quy tắc phòng ngừa:
1. **Luôn khởi tạo biến mặc định** trước khối `try:` (ví dụ: `recaptured_xml = ""`).
2. **Đưa toàn bộ logic fallback vào bên trong khối `except:`**, không để sót lại code xử lý lỗi ở top-level của hàm.

---

## 3. Corrupt Screencap Buffer & PNG Magic Bytes Validation (Case 128)

### Cạm bẫy:
- Khi thiết bị farm lag hoặc nghẽn ADB transport, lệnh `screencap -p` có thể nhả về buffer byte rỗng hoặc stream dở dang không đủ header chuẩn.
- Các module AI recovery / verifier gọi trực tiếp `Image.open(io.BytesIO(img_bytes))` mà không kiểm tra, làm phát sinh `UnidentifiedImageError` hoặc `OSError: image file is truncated`, làm crash toàn bộ batch lướt feed.

### Giải pháp chuẩn:
1. **Kiểm tra 8 Magic Bytes của file PNG trước khi parse:**
   ```python
   PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
   if not img_bytes or len(img_bytes) < 8 or not img_bytes.startswith(PNG_MAGIC):
       # Fallback an toàn (trả về 0 hoặc bỏ qua)
       return 0
   ```
2. **Bọc ngoại lệ đầy đủ quanh `Image.open`:**
   ```python
   try:
       img = Image.open(io.BytesIO(img_bytes))
   except (UnidentifiedImageError, OSError, ValueError):
       return 0  # hoặc fallback safe
   ```
