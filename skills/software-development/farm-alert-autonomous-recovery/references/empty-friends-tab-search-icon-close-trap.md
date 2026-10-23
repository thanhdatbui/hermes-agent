# Empty Friends Tab vs Search Icon False Close Control Trap (Case 122 Regression Prevention)

## 1. Triệu Chứng Hiện Trường (Symptom)
- Máy nuôi lướt Feed bình thường tới khi chuyển sang tab **Bạn bè** (*Friends*) thì dừng phiên với lỗi:
  `stop_reason: unknown TikTok state; swipe recovery (2 swipes) still stuck`
  (ví dụ: Máy 5, Ca 2 Row 3).
- Ảnh hiện trường và UI XML cho thấy màn hình đang mở tab "Bạn bè", nhưng tài khoản không có bạn bè đăng video nên TikTok hiển thị danh sách người dùng gợi ý kết bạn (*"Follow bạn"*, nút *"Follow lại"*, nút *"Xóa"*), thanh điều hướng Home/Friends vẫn hiển thị đầy đủ, không có dialog modal nào che khuất.

## 2. Cơ Chế Gốc Rễ & Bẫy Kính Lúp (Search Icon Trap)
1. **Lỗi Logic trong `_find_follow_friends_semantic_close_control`:**
   - Bộ tìm nút đóng ngữ nghĩa quét tìm `title_node` có text `"Follow bạn"` (vốn nằm ở dòng đầu tiên của danh sách gợi ý bạn bè, tọa độ $Y \approx 241$).
   - Sau đó, hàm quét các `ImageView` có thể click gần tiêu đề (bán kính $\le 600$px).
   - Icon Tìm kiếm (Kính lúp, `id=":id/k_g"`, `content-desc="Tìm kiếm"` ở góc trên bên phải $[912,75][1080,243]$) thỏa mãn điều kiện này nên bị hàm nhận diện nhầm là nút Đóng của popup!
2. **Thủng Guard Case 122 (`_is_main_feed_or_profile_screen`):**
   - Case 122 đã quy định: Nếu màn hình ở Profile hoặc Main Feed mà không có modal dialog thực sự (`android.app.Dialog`) hoặc semantic close control, thì bắt buộc trả về `False`.
   - Do hàm trên trả về Search Icon làm "close control", guard của Case 122 bị qua mặt $\rightarrow$ `detect_follow_friends_suggestion_popup` trả về `True`.
   - `classifier.py` phân loại nhầm màn hình Feed thành `manual-needed:popup` (`known follow_friends_suggestion_popup popup detected`).
   - Runner gọi dismisser tap trúng Kính lúp mở giao diện tìm kiếm, vuốt 2 lần không thoát được nên fail-closed.

## 3. Cạm Bẫy Giải Pháp Bề Mặt (Regression Hazard)
- **CẤM DÙNG BLUNT HAMMER:** Không được dùng điều kiện bao quát như `selected_feed_screen is None` trong `classifier.py` để ép bỏ qua popup khi có tab feed active.
- **Rủi ro:** Khi trên feed xuất hiện một modal dialog thực sự (ví dụ popup cập nhật chính sách, popup xin quyền danh bạ/bạn bè che toàn màn hình), điều kiện này sẽ vô hiệu hóa detector khiến runner không đóng popup mà cố vuốt feed $\rightarrow$ gây kẹt phiên hàng loạt.

## 4. Giải Pháp Chuẩn Bền Vững (Zero-Regression)
1. **Siết Chặt Semantic Close Control (`_find_follow_friends_semantic_close_control`):**
   - Loại trừ dứt khoát các nút có `desc` hoặc `text` là `"tìm kiếm"` hoặc `"search"`.
   - Nhánh fallback khoảng cách ($\le 600$px) CHỈ được kích hoạt khi phần tử có nhãn đóng tường minh (`text`/`desc` trong `{"đóng", "close", "✕", "x"}` hoặc resource-id chứa `c3t`, `e63`, `e8c`). Tuyệt đối không cho phép `ImageView` vô danh lọt qua nếu không phải `is_sheet_header_close` ở góc trên của bottom sheet ($X \ge 800, \Delta Y \le 150$).
2. **Kích Hoạt Fallback Tab Cho Feed Bạn Bè Rỗng (`_FRIENDS_FEED_CONTENT_TERMS`):**
   - Bổ sung các cụm từ `"Follow bạn"`, `"Follow lại"`, `"Follow bạn bè của bạn"` vào `_FRIENDS_FEED_CONTENT_TERMS` trong `feed_swipe_smoke.py`.
   - Khi bot chuyển sang tab Bạn bè rỗng, `_has_friends_feed_content(after)` sẽ nhận diện chính xác và tự động gọi `fallback_to_for_you` để chuyển về tab Đề xuất lướt tiếp bình thường.
