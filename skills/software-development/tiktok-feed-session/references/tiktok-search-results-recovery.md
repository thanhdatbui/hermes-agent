# TikTok Search Results Screen Recovery Guide

## Bối cảnh & Hiện tượng
Máy bị kẹt ở màn hình Tìm kiếm kết quả TikTok (Search Results) sau khi bị điều hướng hoặc nhập từ khóa tìm kiếm (ví dụ 'lu.huyn926'). Màn hình chứa:
- Thanh tìm kiếm `search_edit_text` / `et_search` chứa từ khóa
- Các tab kết quả: `Top` / `Hàng đầu`, `Người dùng` / `Users`, `Video` / `Videos`, `Âm thanh` / `Sounds`
- Nút mũi tên Quay lại (←) ở góc trên bên trái
- Các thẻ kết quả user (chứa nhãn "follower", "đã follow", v.v.)

## Nguyên nhân gốc (Root Cause)
1. **Khác biệt giữa Search Landing và Search Results:**
   - Search Landing chỉ chứa gợi ý từ khóa ("bạn có thể thích", "tìm kiếm gần đây"), không có tab phân loại kết quả.
   - Search Results không chứa các từ khóa gợi ý này, nhưng có `search_edit_text` và các tab kết quả (`Top`, `Người dùng`, `Video`).
2. **Pitfall Negative Exclusion:**
   - Bộ nhận diện Search Landing (`detect_search_landing_page`) ban đầu có negative exclusion chặn các từ `follower`, `followers`, `đã follow` để tránh nhầm với trang cá nhân (Profile).
   - Khi ở Search Results, danh sách user card hiển thị số follower, dẫn đến bộ nhận diện từ chối nhầm là Profile page và bỏ qua.
3. **Recovery Loop bỏ sót:**
   - `_swipe_recovery_on_stuck` (Section 1B) ban đầu chỉ kiểm tra `DetailActivity` hoặc resource-id `:id/bq7`, không nhận diện Search Results để bấm Back.

## Kiến trúc xử lý chuẩn (Dual-Layer)
1. **Lớp 1 - Proactive Benign Popup (`python_runner/core/benign_popup.py`):**
   - Trong `detect_search_landing_page`:
     - Kiểm tra `has_search_input` (`search_edit_text`, `et_search`, `tv_search_input`) kết hợp `has_search_tabs` (`top`, `người dùng`, `users`, `video`, `videos`, ...).
     - Nếu là `is_search_results`, KHÔNG áp dụng exclusion trên `follower` / `following` (chỉ loại trừ các marker profile settings / login thực sự như `sửa hồ sơ`, `edit profile`, `xác minh`, `mật khẩu`).
     - Gắn marker `search_results_page` và trả về `BenignPopupMatch`.
2. **Lớp 2 - Reactive Stuck Recovery (`python_runner/flows/feed_swipe_smoke.py`):**
   - Trong `_swipe_recovery_on_stuck` (Mục 1B):
     - Quét node XML để phát hiện `is_search_results` (`has_search_input` + search tabs / `search_edit_text`).
     - Tìm nút Back top-left (bounds `[0..180, 0..320]`, hoặc ID/desc/text tương ứng).
     - Nếu có back node: tap tọa độ nút Back.
     - Nếu không có: gửi `input keyevent BACK` (keyevent 4).
     - Dự phòng: Nếu có tab Home (`:id/home`, "Trang chủ"), tap Home tab để ép quay về Feed chính.
     - Đặt `stale_xml_dismissed = True` và `handler_dismissed = True` để tránh double-back.
