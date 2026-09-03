# False Positive Substring Matching trên Nút Đóng & Sound Detail Overlay (2026-08-21)

## Bối cảnh & Hiện tượng
- Khi chạy feed session nuôi tài khoản trên farm (ví dụ máy 45, ngày 21/08/2026), flow lướt feed gặp màn hình feed bình thường.
- Tuy nhiên hệ thống quét nhầm màn hình thành `contact_follow_suggestion` (do thấy các chữ 'Đề xuất', 'Follow') và cố gắng tìm nút đóng (`dismiss_not_interested_button`).
- Thay vì đóng popup hoặc không làm gì, runner lại tap vào tọa độ `(999, 1712)` là nút đĩa nhạc/âm thanh ở góc dưới bên phải (`id/p89`), khiến TikTok mở thẳng vào trang chi tiết âm thanh (Sound Detail) của bài hát mang tên "Closer".

## Nguyên nhân gốc
1. **Substring Matching không biên từ (`in`) trong bộ lọc text**:
   - Hàm `_find_clickable_text(elements, terms)` trong `automation_core.tiktok.benign_popup` dùng `_element_contains` với logic: `any(term.lower() in value for term in terms)`.
   - Danh sách `terms` tìm nút đóng có từ khóa `"close"`.
   - Thuộc tính `content-desc` của nút đĩa nhạc là `"Âm thanh: Closer của hppr & Hollis Lane"`.
   - Do chuỗi `"Closer"` chứa chuỗi con `"close"`, bộ lọc nhận nhầm nút đĩa nhạc là "nút đóng" và bấm trúng tâm `(999, 1712)`.
2. **Thiếu cơ chế xử lý khi lọt vào màn hình Sound Detail**:
   - Khi đã lỡ nhảy vào trang chi tiết âm thanh (Sound Detail), `benign_popup_registry.py` trước đó chưa đăng ký handler mặc định để tự động thoát ra khỏi trang âm thanh để quay lại video feed.

## Giải pháp & Bài học chuẩn
1. **Tuyệt đối không dùng substring matching không biên từ cho các từ tiếng Anh ngắn**:
   - Đối với các từ khóa điều khiển như `"close"`, `"open"`, `"back"`, bắt buộc dùng:
     - Exact match (`_find_clickable_exact_label`), hoặc
     - Word boundary regex (`\bclose\b`), hoặc
     - Kiểm tra class / resource-id và loại trừ các node âm thanh (resource-id `p89`, `content-desc` có tiền tố `Âm thanh:` / `Sound:`).
2. **Đăng ký `sound_detail_overlay` trong Popup Registry**:
   - Đăng ký `sound_detail_overlay` với priority 78 trong `benign_popup_registry.py`:
     - Detector: Quét các marker đặc trưng `"Sử dụng âm thanh"`, `"Use this sound"`, `"Thêm vào Nhật"`, `"Thêm vào Mục ưa thích"`.
     - Dismisser: Nhấn nút BACK (`actions.back()` hoặc `keyevent 4`) để đóng overlay âm thanh và quay trở lại Feed.
