# Follow Friends / Follow Back Card Popup Dismiss Pitfalls

## Bối cảnh
Trên TikTok feed xuất hiện card modal/popup đề xuất bạn bè ("Follow bạn", "Follow bạn bè của bạn", "Follow lại", "Không quan tâm", "Vuốt lên để bỏ qua") kèm 3 thumbnail video.
Hệ thống có rule/handler xử lý nhưng vẫn có thể fail-closed thành `unexpected popup/dialog marker detected` (giữ hiện trường) do 2 bẫy sau:

## 1. Bẫy Semantic Title trong Registry Handler
- `_find_follow_friends_semantic_close_control`: Nếu chỉ tìm theo chuỗi cứng `"follow bạn bè của bạn"` hoặc `"follow your friends"`, khi TikTok hiển thị biến thể nhãn `"Follow bạn"` hoặc `"Vuốt lên để bỏ qua"` thì hàm trả về `None`.
- **Giải pháp**: Nhận diện tiêu đề mở rộng gồm `{"follow bạn bè của bạn", "follow your friends", "follow bạn", "follow back", "gợi ý follow"}` hoặc tìm nút `X` / `ImageView Đóng` (`id/c3t`) nằm trong vùng bounds của card popup active trên màn hình.

## 2. Bẫy Nút Đóng Bị Tràn/Cắt Ngoài Mép Màn Hình (Off-screen / Clipped Node)
- Khi carousel đề xuất render nhiều card, card trước/sau có thể nằm lệch mép màn hình (ví dụ `bounds=[0, 462][46, 570]`, x=0..46 bị cắt hơn một nửa).
- `detect_contact_follow_suggestion` nếu lấy node đầu tiên theo thứ tự cây XML sẽ chọn nhầm nút `id/c3t` ở mép màn hình thay vì nút `id/c3t` trung tâm của card hiện tại (`bounds=[804, 410][924, 530]`). Tap vào nút mép không có tác dụng đóng card.
- **Giải pháp**: Bắt buộc lọc bỏ các element có diện tích bị cắt sát mép (ví dụ `bounds.x1 == 0` và width < 60px, hoặc nằm ngoài vùng trung tâm hiển thị `x >= 100`) để luôn chọn đúng nút đóng của card đang focus.
