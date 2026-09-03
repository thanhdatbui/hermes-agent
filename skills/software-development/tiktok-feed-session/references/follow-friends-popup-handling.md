# Quy tắc xử lý Popup / Tab Gợi ý Bạn bè & Follow lại (TikTok Feed Session)

## Bối cảnh & Hiện tượng
Khi nuôi acc / lướt feed TikTok (`feed-session-smoke` / `multi-machine-feed-session`), app có thể tự bung popup hoặc chuyển sang tab "Bạn bè" hiển thị danh sách người dùng kèm nút "Follow lại" (Follow bạn / Gợi ý kết bạn) và mục "Mời Bạn bè". Nếu không xử lý đúng, script sẽ không vuốt được video feed và bị kẹt timeout `max_duration_seconds exceeded`.

## Quy tắc thực thi chuẩn (Automated Handler)
1. **Phát hiện (`detect_follow_friends_suggestion_popup` / registry entry `follow_friends_suggestion_popup`):**
   - Quét từ khóa: `Follow bạn bè của bạn`, `Follow your friends`, `Gợi ý follow`, `Follow lại`, `Mời Bạn bè`, `Mời bạn bè`.
2. **Giới hạn số lượng bấm mỗi turn:** 
   - Mỗi turn / phiên gặp popup này, chỉ bấm ngẫu nhiên tối đa **1 đến 2 nút "Follow lại"** (`random.randint(1, 2)`) (không bấm hết toàn bộ danh sách).
3. **Thoát về Feed video:** 
   - Sau khi bấm xong 1-2 nút (hoặc nếu không có nút để bấm):
     - Ưu tiên bấm chuyển sang tab **"Đề xuất" (For You Feed)** (ưu tiên header Y < 350 hoặc bottom bar Y > 1700).
     - Tìm nút đóng (icon X / Close) để tắt modal nếu có overlay.
     - Fallback: Bấm phím **Back** để trở lại luồng lướt video bình thường, tránh kẹt lặp gây timeout.
