# Profile Tab Bottom-Nav Filter & Fallback Pruning (Tiktok-video / adapter.py)

## 1. Vấn đề: Trúng nhầm Avatar Node trên Feed/Overlay
- Trong UI XML của TikTok (đặc biệt bản 46.x trên các thiết bị Samsung như S7 SM-G930x), trên màn hình Feed video hoặc comment overlay thường xuất hiện các node hình đại diện / avatar của kênh với `content-desc="Hồ sơ <Tên Kênh>"` (ví dụ: `Hồ sơ BEN EAGLE`).
- **Nguy cơ:** Nếu sử dụng partial match dạng `if "hồ sơ" in cd or "profile" in cd` mà không lọc toạ độ vùng bottom-nav, hàm `tap_profile` sẽ click nhầm vào avatar của video creator ở giữa/nửa dưới màn hình thay vì tab Hồ sơ ở góc dưới cùng bên phải.

## 2. Chuẩn hoá Bộ lọc Bottom-Navigation Tab
Để đảm bảo node được chọn là tab điều hướng thật sự:
1. **Lọc toạ độ không gian (Spatial Bounding Box):**
   - Xác định kích thước màn hình `_screen_w`, `_screen_h` từ bounds của root/window nodes (fallback mặc định `1080x1920`).
   - Yêu cầu toạ độ tâm element:
     ```python
     _min_x = _screen_w * 0.75
     _min_y = _screen_h * 0.80
     ```
   - Node hợp lệ phải thoả mãn: `cx >= _min_x and cy >= _min_y` và `visible-to-user != "false"` và `enabled != "false"`.
2. **Thứ tự ưu tiên selector:**
   - **Bước 1 (Resource ID):** `com.ss.android.ugc.trill:id/oly` (ID chính xác của tab Hồ sơ trên các bản TikTok mới), sau đó đến `profile_tab`.
   - **Bước 2 (Text):** Duyệt toàn bộ node, so khớp exact `"hồ sơ"` hoặc `"profile"`.
   - **Bước 3 (Content-desc):** So khớp EXACT `_cd in ("hồ sơ", "profile")` (tuyệt đối không dùng substring `in`).
   - Mọi node tìm thấy đều phải đi qua hàm kiểm tra `_is_valid_bottom_nav(_node)`.

## 3. Pitfall Cú pháp khi Xoá/Prune Khối Fallback Cũ
- Trong `scripts/tiktok_workflow/adapter.py`, toàn bộ `Strategy 1` nằm trong khối `try:` mở đầu bằng:
  ```python
  # Strategy 1: dùng UI dump để find profile tab element
  try:
      xml_text = self.dump_ui()
  ```
- Khối `try:` này được đóng ở cuối bằng:
  ```python
  except Exception as exc:
      logger.warning(f"[TAP_PROFILE] UI dump approach failed: {exc}")
  ```
- **Bẫy cú pháp (SyntaxError Trap):**
  - Khối fallback cũ `# Thử content-desc` có khối `try:... except ET.ParseError: pass` nằm bên trong `Strategy 1`.
  - Nếu xóa cả dòng `except Exception as exc:...` ở ngoài cùng, khối `try:` của `Strategy 1` sẽ bị mồ côi (không có `except` hoặc `finally`), dẫn đến lỗi biên dịch:
    `SyntaxError: expected 'except' or 'finally' block` khi chạy `python -m py_compile`.
  - **Quy tắc:** Khi thay thế khối fallback cũ bằng comment:
    `# (removed) partial content-desc fallback — đã thay bằng exact-match + bottom-nav filter phía trên`
    phải giữ nguyên `except Exception as exc:` của khối `Strategy 1` bao bọc bên ngoài.
