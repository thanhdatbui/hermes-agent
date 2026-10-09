# TikTok Account Switcher Diagnostics & Off-Screen Multi-Account Handling

## Context
Trên các dòng máy Samsung Galaxy S7 (1080x1920) tại Farm khi nạp đủ 8 tài khoản (Tik1 - Tik8), danh sách tài khoản trong bottom sheet `ACCOUNT_SWITCHER` bị tràn màn hình (off-screen). Viewport đầu tiên chỉ hiển thị tối đa 4 tài khoản. Nếu tài khoản đích nằm ở các slot dưới (như Tik4, Tik6, Tik8), quy trình tự động hóa sẽ gặp các lỗi nghiêm trọng nếu không xử lý đúng 2 khía cạnh: UI scrolling và Header Anchor matching.

---

## 1. Vấn đề 1: Tràn danh sách 8 tài khoản (Off-screen Account)
- **Triệu chứng**: `[ACCOUNT_SWITCHER_FAILED] select account failed: ACCOUNT_MISSING: expected account was not found`.
- **Nguyên nhân**: `find_exact_account()` chỉ tìm kiếm trên dump XML đầu tiên của viewport.
- **Giải pháp chuẩn**:
  - Khi bắt ngoại lệ `AccountSwitcherError("ACCOUNT_MISSING")`, tự động kích hoạt retry swipe lên (scroll down danh sách):
    - Tọa độ swipe tối ưu trên màn 1080x1920: `start_x = width // 2`, `start_y = int(height * 0.80)` (1536px), `end_x = width // 2`, `end_y = int(height * 0.50)` (960px).
    - Thời gian vuốt (`duration_ms`): `450ms` (tránh vuốt quá nhanh làm trôi quá đà hoặc mất sự kiện).
    - Settle delay: chờ tối thiểu `1.0s` sau khi vuốt trước khi dump lại UI hierarchy.
    - Lặp tối đa 3 lần swipe. Nếu tìm thấy thì break và tiến hành chọn tài khoản.

---

## 2. Vấn đề 2: Nhận nhầm Header Anchor & Sai lệch `coordinate_fallback`
- **Triệu chứng**:
  - Log báo `[ACCOUNT_SWITCHER] Switcher opened via core ✓` nhưng thực tế màn hình không bung bottom sheet switcher.
  - Ngay sau đó `select account failed: ACCOUNT_MISSING` và lặp lại liên tục dù có swipe.
  - Kiểm tra screencap thấy màn hình bị mở popup story ("Tám chuyện nào"), bàn phím ảo bung lên, hoặc chỉ đứng im ở Profile root.
- **Nguyên nhân cốt lõi**:
  1. **Nhận diện sai node anchor**: TikTok các bản mới bổ sung các icon điều khiển trên header profile:
     - `Số lượt xem hồ sơ` / `Profile views`
     - `Tám chuyện nào` / `Tám chuyện`
     Hàm `find_switcher_anchor` trong `automation-core` duyệt generic header candidates và nhầm các icon này là anchor mở switcher.
  2. **Tọa độ fallback trong adapter sai vị trí**:
     - `coordinate_fallback("switcher")` trong adapter bị cấu hình nhầm thành `(540, 552)` (vị trí giữa màn hình - trúng text display name hoặc nút Tám chuyện).
     - Vị trí thực tế của dropdown Switcher nằm ở **đỉnh thanh header bar**: tọa độ chuẩn là `(539, 140)`.
- **Cách khắc phục**:
  1. **Blacklist header control nodes**: Cập nhật `_PROFILE_HEADER_CONTROL_MARKERS` trong `automation_core/tiktok/account_switcher.py`:
     ```python
     _PROFILE_HEADER_CONTROL_MARKERS = frozenset({
         "home", "for you", "following", "friends", "profile", "hồ sơ", "search", "menu", "more",
         "back", "close", "đóng", "thông báo", "notifications", "bell", "activity log", "nhật ký",
         "số lượt xem hồ sơ", "profile views", "lượt xem hồ sơ", "tám chuyện nào", "tám chuyện",
     })
     ```
  2. **Sửa tọa độ fallback trong adapter**:
     ```python
     def coordinate_fallback(self, action: Optional[str] = None) -> Optional[tuple[int, int]]:
         if action == "switcher":
             return (539, 140)
         return None
     ```
