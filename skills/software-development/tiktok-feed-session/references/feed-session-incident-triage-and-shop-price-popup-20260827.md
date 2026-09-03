# Feed Session Incident Triage & Shop Price Popup Patterns (2026-08-27)

## 1. Context & Incidents Triage Signatures

Khi vận hành `multi-machine-feed-session` trên phone farm, các lỗi dừng phiên thường gặp qua Telegram Farm Alerts gồm:

### A. Popup Thương mại TikTok Shop: "Chi tiết giá" (Price Details)
- **Triệu chứng / Log**: `unknown TikTok state; swipe recovery (2 swipes) still stuck`
- **Hiện trạng màn hình**: Modal/Bottom sheet "Chi tiết giá" (Giá gốc, Giảm giá sản phẩm, Voucher TikTok Shop, Giá tạm tính) che video feed.
- **Root Cause**: Dạng overlay thương mại mới chưa nằm trong rule nhận diện `benign_popup`, khiến cơ chế auto-dismiss bỏ qua và làm kẹt feed swipe.
- **Xử lý**:
  - Tức thời: Tap nút `X` (close icon) góc trên bên phải của modal để đóng overlay.
  - Runtime / Code: Cần bổ sung rule nhận diện popup "Chi tiết giá" (text markers: `Chi tiết giá`, `Voucher TikTok Shop`, `Giá tạm tính`, nút đóng `X`) vào `automation_core.tiktok.benign_popup`.

### B. Session Expired / Checkpoint: Dialog "Trạng thái tài khoản"
- **Triệu chứng / Log**: `navigation target profile not found in XML`
- **Hiện trạng màn hình**: Hộp thoại modal "Trạng thái tài khoản: Tài khoản của bạn đã bị đăng xuất. Hãy thử đăng nhập lại." kèm nút `OK`.
- **Root Cause**: Token/session đăng nhập của tài khoản hết hạn hoặc bị TikTok force logout, che mất bottom navigation bar.
- **Xử lý**:
  - Nhấn `OK` để giải phóng dialog.
  - Phân loại tài khoản bị logout để đưa vào hàng đợi đăng nhập lại (login/re-auth flow).

### C. Lệch Profile Active / Switcher Mismatch
- **Triệu chứng / Log**: `profile verification mismatch: profile account mismatch` hoặc `manual-needed:account-switcher-missing-expected`
- **Hiện trạng màn hình**:
  - Trang Profile đang đứng ở nick khác (không khớp nick trong ca chạy).
  - Hoặc Account Switcher mở lên chỉ có nick đang active, không tìm thấy nick target.
- **Xử lý**:
  - Kiểm tra đối chiếu sheet phân công tài khoản (`TikN.xlsx`, `taikhoan_run_safe.xlsx`).
  - Nếu nick target chưa được đăng nhập trên máy: chạy flow login bổ sung.
  - Nếu nick target đã có: trigger mở switcher và chọn đúng profile.
