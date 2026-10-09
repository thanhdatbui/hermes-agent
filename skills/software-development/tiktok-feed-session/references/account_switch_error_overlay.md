# Lỗi "profile username still mismatched after switch" do mạng / popup "Đã xảy ra lỗi / Thử lại sau"

## Triệu chứng
Khi flow `verify_and_switch_profile` phát hiện profile đang ở tài khoản khác và mở bottom sheet switcher để tap chuyển sang tài khoản mục tiêu:
1. Script đã tap trúng dòng tài khoản mong muốn (`tap_expected_account`).
2. TikTok tải profile mới nhưng mạng chập chờn hoặc tải chậm, xuất hiện thông báo lỗi giữa màn hình:
   - Text: `"Đã xảy ra lỗi / Thử lại sau"` hoặc `"Đã xảy ra lỗi"`
   - Nút Thử lại: Text `"Thử lại"` hoặc resource ID `com.ss.android.ugc.trill:id/dcj`
3. Lúc này trang profile chưa cập nhật sang nick mới (vẫn giữ username của tài khoản cũ).
4. `verify_and_switch_profile` re-read identity thấy username vẫn là nick cũ -> kết luận `profile username still mismatched after switch` và dừng lại ở `ExitStatus.MANUAL_NEEDED`.

## Cách khắc phục & Xử lý chuẩn
1. **Nhận diện nút Thử lại:**
   - Trong `verify_and_switch_profile` sau khi tap switch account và điều hướng về profile:
   - Kiểm tra UI element có `id/dcj` hoặc text chứa `"Thử lại"` / `"Đã xảy ra lỗi"`.
2. **Auto-tap Thử lại & tăng settle delay:**
   - Nếu phát hiện nút `id/dcj` hoặc text `"Thử lại"`, tự động tap vào nút đó để trigger TikTok load lại profile.
   - Thêm khoảng chờ (delay 2.0s - 4.0s) để dữ liệu profile nick mới được render đầy đủ.
3. **Re-check identity:**
   - Đọc lại identity profile sau khi đã tap "Thử lại".
   - Tránh kết luận ngay là mismatch khi màn hình đang ở trạng thái lỗi mạng tải profile.
