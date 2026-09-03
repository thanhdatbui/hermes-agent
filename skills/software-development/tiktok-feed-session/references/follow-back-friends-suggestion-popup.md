# Xử lý Popup / Tab Bạn bè "Follow lại" trong TikTok Feed Session

## Bối cảnh & Hiện tượng
Khi chạy nuôi acc TikTok (`feed-session-smoke` / `multi-machine-feed-session`), TikTok có thể điều hướng hoặc hiển thị overlay / tab **Bạn bè** gợi ý danh sách tài khoản "Follow bạn" kèm các nút đỏ **"Follow lại"** (hoặc "Follow back") và mục "Mời Bạn bè".

Nếu script không xử lý và tiếp tục cố gắng vuốt video trên màn hình này, bot sẽ bị kẹt không nhận diện được feed video chính dẫn tới lỗi timeout `run plan max_duration_seconds exceeded` (ví dụ ở lượt vuốt thứ 8).

## Quy tắc xử lý chuẩn
1. **Giới hạn số lượt bấm Follow lại mỗi turn**:
   - Chỉ bấm ngẫu nhiên tối đa **1 đến 2 nút "Follow lại"** (`random.randint(1, 2)`).
   - Tuyệt đối không bấm ồ ạt hàng loạt để tránh trigger spam restriction / bot flag của TikTok.
2. **Khôi phục về Feed video**:
   - Ngay sau khi bấm 1-2 nút (hoặc nếu không tìm thấy nút nào), BẮT BUỘC bấm chuyển về tab **"Đề xuất" (For You Feed)** ở header hoặc bottom navigation bar (hoặc nút **X / Back** nếu là modal popup).
   - Đảm bảo màn hình trở về For You Feed để tiếp tục các lượt vuốt video bình thường.

## Mã nguồn liên quan
- `python_runner/flows/benign_popup.py`: `detect_follow_friends_suggestion_popup`, `dismiss_follow_friends_suggestion_popup`
- `python_runner/flows/benign_popup_registry.py`: `_detect_follow_friends`, `_dismiss_follow_friends` (priority 82).
