# Search Landing / Suggestions Overlay Handler & Recovery

## Bối Cảnh Sự Cố (28/08/2026)
Trên các máy nuôi nick TikTok (ví dụ máy 10), trong lúc lướt feed hoặc chuyển trang, TikTok vô tình bị chạm vào thanh tìm kiếm hoặc điều hướng sang trang **Tìm kiếm / Gợi ý tìm kiếm (Search Landing Page)** (`com.ss.android.ugc.trill`).
Giao diện này gồm:
- Ô nhập tìm kiếm gợi ý (*"Cute Dog Videos..."*), nút **"Tìm kiếm"**, nút Back `←` góc trên bên trái (`[0, 50][150, 200]`).
- Banner tích điểm thưởng tìm kiếm: *"Tìm kiếm 12 lần để nhận 360 điểm — hãy tiếp tục để mở khóa tới 840 điểm hôm nay!"*.
- Các khối: *"Tìm kiếm gần đây"*, *"Bạn có thể thích"*, *"Live thịnh hành"*, nút *"Hỏi AI"*, *"Tìm kiếm bằng giọng nói"*.

## Cơ Chế Gây Lỗi (Anti-Pattern)
Do `classifier.py` và `benign_popup_registry.py` chưa định danh màn hình này:
1. `classifier.py` không nhận diện được giao diện feed chuẩn $\rightarrow$ phân loại là `unknown`.
2. `safety.py` phát hiện trạng thái không rõ ràng $\rightarrow$ báo lỗi `unknown TikTok state`.
3. Runner feed kích hoạt cơ chế fail-closed an toàn, chuyển trạng thái thiết bị sang `status: blocked` với lock TTL 2h, làm dừng phiên nuôi acc.

## Quy Chuẩn Khắc Phục (Standard Fix)
1. **Negative Exclusions (Bắt buộc):**
   Kiểm tra loại trừ nếu màn hình có các trường của:
   - Hồ sơ (`Đã follow`, `Follower`, `Sửa hồ sơ`...)
   - Camera/Editor
   - Màn hình nhạy cảm/Auth: `Thêm số điện thoại`, `+84`, `Xác minh`, `Mật khẩu`, `Liên kết email`.
2. **Positive Search Markers:**
   Nhận diện các cụm từ đặc thù:
   - `"bạn có thể thích"`, `"tìm kiếm gần đây"`, `"nội dung tìm kiếm thịnh hành"`, `"live thịnh hành"`, `"gợi ý tìm kiếm"`, `"hỏi ai"`, `"tìm kiếm bằng giọng nói"`.
   - Banner tích điểm thưởng kết hợp từ khóa `tìm kiếm` + `điểm` + (`nhận` | `mở khóa`).
3. **Đăng ký vào `BENIGN_POPUP_REGISTRY`:**
   - Tên handler: `search_landing_overlay` (priority 84).
   - Dismisser: Tìm nút Back `←` ở góc trên bên trái `[0, 50][150, 200]` hoặc gửi phím `BACK` (`input keyevent 4`), chờ 1.0s để UI trượt trở lại FYP/Home feed.
4. **Phân loại màn hình chuẩn:**
   - `classifier.py` nhận diện qua `detect_search_landing_page(root)` và gán nhãn `GENERIC_POPUP_SCREEN` (`manual-needed:popup`) thay vì `unknown TikTok state`.
