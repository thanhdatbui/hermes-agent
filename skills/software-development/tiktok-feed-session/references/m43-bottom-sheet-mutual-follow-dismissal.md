# Case Study: M43 Bottom Sheet "Đã follow chung" che Navigation Bar (2026-09-19)

### 1. Hiện tượng & Taxonomy Alert
- Cảnh báo Farm Alert: `⚠️ [P0 CẢNH BÁO MẤT PHIÊN / VĂNG ACCOUNT]: Máy M43: profile verification navigation-failed: navigation target profile not found in XML` thuộc nhóm `login/GMS/verification`.
- Thực tế tài khoản không hề bị văng hay checkpoint.

### 2. Nguyên nhân gốc rễ (Root Cause)
1. **Lớp phủ Bottom Sheet**: Sau khi kết thúc chuỗi swipe feed, TikTok bung popup Bottom Sheet (`content-desc="Trang tính dưới cùng"` hoặc `resource-id="com.ss.android.ugc.trill:id/g1i"`) có tiêu đề `"Đã follow chung (1)"`.
2. **Che khuất Navigation Bar**: Bottom sheet chiếm nửa dưới màn hình (`bounds="[0,1266][1080,1920]"`), đè hoàn toàn lên thanh điều hướng chứa tab "Hồ sơ" (Profile).
3. **Double-fault skip phím Back**:
   - Popup chứa nút `"Đã follow"`. Hàm `classify_tiktok_screen` có `following_terms` chứa `"Đã follow"`, khiến màn hình bị nhận diện nhầm là feed tab `following`.
   - Trong `flows/calibrate_screens.py`, khi chuyển tab sang Profile, hệ thống thấy `is_home_or_feed = True` nên kích hoạt cơ chế `navigation_back_recovery_skipped_at_home_feed` (bỏ qua phím Back để tránh văng ra launcher).
   - Kết quả: Phím Back không được nhấn -> Bottom sheet không được đóng -> XML không thấy tab "Hồ sơ" -> Báo lỗi P0 navigation-failed.

### 3. Giải pháp khắc phục 3 lớp (Đã áp dụng & kiểm thử)
1. **`flows/calibrate_screens.py`**:
   - Thêm `has_overlay` guard khi đánh giá `is_home_or_feed`.
   - Nếu cây XML chứa `Trang tính dưới cùng`, `g1i`, hoặc `android.app.Dialog`, ép `is_home_or_feed = False` để cho phép `KEYCODE_BACK` thực thi giải phóng lớp phủ.
2. **`flows/benign_popup_registry.py`**:
   - Bổ sung marker `"Đã follow chung"`, `"Follow chung"` vào detector `_detect_follow_friends`.
3. **`flows/benign_popup.py`**:
   - Mở rộng tiêu đề bắt đầu bằng `"đã follow chung"`, `"follow chung"`.
   - Bắt nút đóng `X` ở header của Bottom Sheet: `ImageView` có `b[0] >= 800` và cách tiêu đề sheet theo trục dọc `<= 150px` (`abs(b[1] - t_bounds[1]) <= 150`).
