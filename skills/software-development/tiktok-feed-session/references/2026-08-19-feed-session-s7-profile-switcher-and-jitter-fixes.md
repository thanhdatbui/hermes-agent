# TikTok Feed Session: Samsung S7 Profile Switcher, SystemUI False Focus & Jitter Upgrades (19/08/2026)

## 1. Mất Focus Giả (`com.android.systemui`) trên Samsung Galaxy S7 (Android 8.0)
- **Hiện tượng**: TikTok đang mở trọn vẹn ở màn hình Profile/Feed, nhưng `get_focused_activity()` hoặc UI dump đọc trúng node SystemUI trên thanh trạng thái `[0,0][1080,72]` (thanh pin, wifi, giờ của Samsung).
- **Hậu quả**: Script kết luận sai `TikTok focus lost` và kích hoạt `preserve_blocker_screen` dừng oan toàn bộ phiên chạy của máy.
- **Quy tắc xử lý**: 
  - Hàm kiểm tra package phải lọc bỏ các node `com.android.systemui`.
  - Luôn ưu tiên nhận diện package chính (`com.ss.android.ugc.trill`, `com.zhiliaoapp.musically`, `com.ss.android.ugc.aweme`) nếu có node của TikTok trong cây phân cấp XML.

---

## 2. Tránh Bấm Nhầm Trang "Lượt Xem Hồ Sơ" (`id/ic7`)
- **Hiện tượng**: Trên giao diện TikTok mới, icon hình 2 người (Lượt xem hồ sơ `id/ic7`, `tv_number`, bounds `[720, 90][840, 210]`) nằm sát cạnh tên hiển thị profile `[366, 72][720, 228]`.
- **Hậu quả**: Khi hàm `_resolve_profile_switch_anchor()` tìm anchor đổi nick, nó nhận nhầm icon này ➔ máy bấm vào trang *"Số lượt xem hồ sơ"*.
- **Quy tắc xử lý**:
  - Loại trừ triệt để `id/ic7`, `tv_number`, content-desc *"Số lượt xem hồ sơ"* khi resolve anchor đổi nick.
  - Thêm cơ chế nhận diện subpage: Nếu máy lỡ đang ở trang *"Số lượt xem hồ sơ"*, tự động gửi phím Back để thoát về Profile root.

---

## 3. Account Switcher Cho Tài Khoản Chưa Đặt Tên (`+ Thêm tên`)
- **Hiện tượng**: Nick mới chưa đặt Display Name sẽ hiển thị nút `+ Thêm tên` (`id/se2`) ở vị trí tiêu đề trên cùng.
- **Hậu quả**: Script tưởng "Thêm tên" là Display Name để tap đổi acc ➔ bấm vào mở modal sửa tên hoặc bị chặn.
- **Quy tắc xử lý**:
  - Nếu text tiêu đề là `+ Thêm tên` / `Add name` / `Thêm tiểu sử` / `Add bio`:
  - Chuyển fallback anchor sang bấm trực tiếp vào **node `@username`** nằm bên dưới avatar để bung danh sách chuyển đổi tài khoản.

---

## 4. Chuẩn Hóa Mặc Định Anti-Bot Jitter & Watch Delay
- `DEFAULT_SWIPE_JITTER_PX = 15`: Toạ độ vuốt luôn tự động lệch ngẫu nhiên $\pm 15$px quanh trục chuẩn `(540, 1540) ➔ (540, 620)`.
- `DEFAULT_MIN_WATCH_SECONDS = 3.0s` & `DEFAULT_MAX_WATCH_SECONDS = 8.0s`: Mỗi video dừng ngẫu nhiên 3–8 giây trước khi vuốt tiếp.
- `DEFAULT_SWIPE_DURATION_MIN/MAX_MS = 550..750ms`: Tốc độ vuốt ngón tay biến thiên tự nhiên.

---

## 5. Báo Cáo Lỗi Realtime Từng Máy
- Khi chạy batch nhiều máy song song: Không chờ đến khi toàn bộ batch kết thúc mới tổng kết; **máy nào gặp lỗi/kẹt là phải bắn thông báo Telegram ngay lập tức** (kèm số máy `[MÁY XX]`, bước kẹt, ảnh màn hình và đề xuất fix) để user xử lý ngay trong phiên.
