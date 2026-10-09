# Profile Identity Drift & Account Switcher Versioning (Case 127 & 128)

Tài liệu chi tiết về xử lý lỗi đọc nhầm Video Feed làm Profile (`profile username still mismatched after switch`) và sự cố tap chuyển tài khoản trên các phiên bản TikTok khác nhau (46.2.3 vs 46.7.3).

---

## 1. Case 127: Lỗi Nhận Diện Nhầm Video Feed Làm Profile Khi Switch Nick

### Hiện tượng lỗi thực tế
- Alert `[MÁY N]` dừng phiên nuôi acc / lướt feed với triệu chứng: `profile username still mismatched after switch`.
- Sự cố xảy ra đồng loạt trên nhiều máy (Máy 79, Máy 78, Máy 42...) sau bước `profile_preflight_switch`.
- Ảnh chụp hiện trường cho thấy màn hình đang hiển thị video For You / Home Feed (ví dụ video của creator `@Linhnguyen1707`).

### Nguyên nhân cốt lõi (Anti-Pattern)
1. **Màn hình bị trôi về Feed sau Switch/Reload:**
   Sau khi tap chuyển đổi tài khoản hoặc khi TikTok khởi động lại phiên, app tự động chuyển hướng về Trang chủ (Home Feed - For You video feed).
2. **Logic phát hiện Drift bị lọt khi XML dump sạch:**
   Hàm `_profile_guard_drifted_from_profile` trước đây có điều kiện:
   ```python
   if "keyboard cleanup" in reason:
       return True
   return xml_error in FEED_CONFIRMED_XML_DEGRADED_ERRORS
   ```
   Khi XML dump hoàn toàn bình thường (`xml_error == ""`), hàm trả về `False`, khiến runner ngỡ rằng app vẫn đang ở màn hình Profile.
3. **Parse nhầm Creator Video thành Username nuôi:**
   Runner gọi tiếp `read_profile_identity()`, đọc cây XML của video feed như Profile, bốc nhầm `@creator` trên video For You đem so khớp với nick nuôi chỉ định $\rightarrow$ Báo mismatch sai lệch và trigger dừng an toàn dạng fail-closed.

### Giải pháp chuẩn (Case Fix)
1. **Khẳng định Drift ngay khi màn hình là Feed:**
   Trong `_profile_guard_drifted_from_profile`, bổ sung kiểm tra:
   ```python
   if detected in {"home", FEED_TYPE_FOR_YOU, FEED_TYPE_FOLLOWING, FEED_TYPE_FRIENDS}:
       return True
   ```
   Kể cả khi XML dump sạch (`xml_error == ""`), việc phát hiện màn hình là Home/Feed luôn khẳng định app đã bị trôi khỏi Profile.
2. **Tự động Re-tap Tab Profile:**
   Trong `_read_profile_identity_with_add_phone_guard`, khi `is_drifted` là `True`, lập tức gọi `_try_profile_retap_on_drift` tap lại tab Hồ sơ đáy (`[972, 1857]`) để kéo TikTok về đúng Profile trước khi đọc lại danh tính.

---

## 2. Case 128: Account Switcher Tap Failure & Phân Mảnh Phiên Bản TikTok

### Hiện tượng lỗi thực tế
- Khi chạy Canary / đổi nick trên Máy 79 hoặc Máy 78:
  - Bottom sheet *"Chuyển đổi tài khoản"* mở lên thành công.
  - Nick mục tiêu có sẵn trong danh sách switcher (`Button id/l9b`).
  - Lệnh tap của runner không kích hoạt đổi nick (dấu kiểm `id/fdu` vẫn đứng yên ở nick cũ).
  - Runner tap tiếp vào tab Profile đáy `[972, 1857]` nhưng vô tình trúng vào hàng *"Thêm tài khoản"* (`[0, 1680][1080, 1896]`) do sheet chưa đóng.

### Nguyên nhân cốt lõi (Anti-Pattern)
1. **Phân mảnh layout phiên bản TikTok:**
   - Các máy chuẩn farm (như Máy 26, Máy 17, Máy 40...) đang chạy **TikTok 46.7.3 / 46.6.3** sử dụng resource-id `com.ss.android.ugc.trill:id/lkp`.
   - Các máy cũ (như Máy 79, Máy 78) đang chạy **TikTok 46.2.3** sử dụng resource-id `com.ss.android.ugc.trill:id/l9b`.
2. **Lệch tọa độ tap do override bounds:**
   - Trong `_find_account_switch_option`: Nếu override bounds sang inner `TextView` (`mtx`, `clickable=false` tại `x ≈ 397`), trên một số phiên bản máy Samsung, tap vào non-clickable child không kích hoạt event click của `Button` cha.
   - Ngược lại, nếu lấy center của full-width button `[0, 816][1080, 1032]` (`x=540`), tọa độ rơi vào khoảng trống bên phải của hàng danh sách, có thể bị view nuốt sự kiện.
3. **Race Condition điều hướng khi Bottom Sheet chưa đóng:**
   - Sau cú tap switcher, runner gọi ngay `_navigate_profile_for_preflight` (tap `[972, 1857]`). Nếu switcher sheet chưa đóng hoàn toàn, cú click này sẽ chạm trúng vào hàng *"Thêm tài khoản"* ở đáy sheet, gây nhiễu luồng.

### Giải pháp chuẩn (Case Fix)
1. **Bảo toàn clickable button bounds:**
   Trong `_find_account_switch_option`:
   ```python
   is_node_clickable = node.attributes.get("clickable", "false").casefold() == "true"
   if not is_node_clickable and node.bounds is not None and (node.bounds[2] - node.bounds[0]) >= 600:
       # Chỉ override bounds khi button container không clickable
   ```
2. **Nâng thời gian chờ sau Switch & Guard Bottom Sheet:**
   - Tăng thời gian settle sau khi chọn nick lên `random.uniform(4.5, 6.0)`.
   - Trước khi re-navigate tab Profile, kiểm tra xem màn hình hiện tại đã ở Profile chưa để tránh tap lại gây văng/refresh.
3. **Chuẩn hóa APK Farm:**
   - Đối với các máy chạy version cũ `46.2.3` có tỷ lệ tap trượt cao, giải pháp bền vững nhất là đồng bộ APK lên bản chuẩn farm **46.7.3** từ `D:/OneDrive/apk-bank/com_ss_android_ugc_trill/base.apk`.
