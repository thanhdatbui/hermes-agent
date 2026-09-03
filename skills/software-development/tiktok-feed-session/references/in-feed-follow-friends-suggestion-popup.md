# Xử lý Thẻ / Popup Gợi ý Bạn bè In-Feed ("Follow lại" / "Follow bạn")

## 1. Hiện tượng & Triệu chứng
- Màn hình Feed xuất hiện thẻ đề xuất bạn bè / người liên hệ ("Follow bạn", "Bạn bè với", "Follow lại", "Không quan tâm", "Vuốt lên để bỏ qua").
- Hệ thống bị phân loại thành `manual-needed:popup` và báo `unexpected popup/dialog marker detected`, kích hoạt alert đỏ Telegram "GIỮ HIỆN TRƯỜNG" làm gián đoạn máy nuôi nick.

## 2. Các cạm bẫy kỹ thuật (Pitfalls)
1. **Bắt nhầm nút Đóng của thẻ bị tràn lề trái:**
   - Trong giao diện ViewPager/RecyclerView của TikTok, card liền trước có thể bị tràn sang mép trái màn hình với icon `c3t` (Đóng) ở tọa độ $x \in [0, 46]$.
   - Nếu bộ quét DOM lấy icon `c3t` đầu tiên mà không lọc bounds ($x < 50$ và width $< 50$), ADB sẽ tap hụt vào tọa độ $x=23$ mép màn hình, không đóng được card hiện tại ở $x=864$.
2. **Thiếu import hàm capture:**
   - Khi gọi `dismiss_follow_friends_suggestion_popup`, nếu thiếu `from core.ui_capture import capture_required_ui`, Python văng `NameError` và bị bẫy `except Exception` nuốt lỗi trả về `initial_capture_failed`.
3. **Bộ lọc tiêu đề quá chặt:**
   - Nếu `_find_follow_friends_semantic_close_control` chỉ tìm đúng chuỗi cứng `"Follow bạn bè của bạn"`, nó sẽ bỏ lọt các thẻ in-feed có nhãn quan hệ `"Follow bạn"`, `"Bạn bè với"`.

## 3. Quy tắc xử lý chuẩn (Case 50)
1. **Nhận diện đầy đủ markers:** Bao gồm `"Follow bạn bè của bạn"`, `"Follow your friends"`, `"Gợi ý follow"`, `"Follow lại"`, `"Follow back"`, `"Theo dõi lại"`, `"Follow bạn"`, `"Bạn bè với"`.
2. **Lọc tọa độ bounds khi tương tác:**
   - Nút "Follow lại": Yêu cầu $x \ge 50$ và $y > \text{min\_y}$ để bấm trúng nút trên card active.
   - Nút đóng "X" / "Không quan tâm": Yêu cầu $x \ge 50$ và width $\ge 30$, height $\ge 30$.
3. **Quy trình bấm:**
   - Bấm tối đa 1-2 lượt "Follow lại".
   - Recapture hierarchy tươi và bấm nút `X` (hoặc `Không quan tâm`) để đóng card sạch sẽ và trở về Feed tiếp tục phiên lướt.
