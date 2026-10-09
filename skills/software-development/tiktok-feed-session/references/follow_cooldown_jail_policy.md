# Kỷ luật chặn Follow khi nick trong cooldown phạt (đi tù) (2026-09-13)

Khi tài khoản bị TikTok phạt nhả follow / rate limit follow (trạng thái đi tù):
1. **Cấm tuyệt đối follow tự nhiên trên Feed (`_maybe_follow_video` trong `feed_swipe_smoke.py`):**
   - Phải kiểm tra trạng thái cooldown phạt của account trước khi thực hiện bất kỳ hành động follow ngẫu nhiên nào.
   - Nếu đang trong cooldown: skip follow ngay lập tức, ghi log rõ ràng `action="follow_video", result="skipped", error="account is in follow cooldown (imprisoned)"`, không capture XML và không tap.
2. **Cấm bấm Follow / Follow lại trên popup gợi ý bạn bè (`dismiss_follow_friends_suggestion_popup` trong `benign_popup.py`):**
   - Không được thực hiện vòng lặp bấm follow bạn bè khi nick đang trong cooldown.
   - Chỉ được phép tìm và tap nút Semantic Close (X / Đóng) để đóng popup an toàn.
3. **Cấm rule blind popup `follow_back_suggestion` tự ý bấm Follow lại:**
   - Thẻ gợi ý người bạn có thể biết trên feed không được tự động tap "Follow lại" / "Follow back" / "Theo dõi lại" mà phải dismiss an toàn bằng cách bấm "Không quan tâm" / đóng hoặc bỏ qua.
