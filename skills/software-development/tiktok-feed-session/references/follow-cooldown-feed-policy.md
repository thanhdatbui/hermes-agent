# Follow Cooldown Policy in TikTok Feed Session

## Bối cảnh
Khi tài khoản TikTok đang trong thời gian giãn cách follow (cooldown) sau các đợt chạy follow automation hoặc phát hiện cảnh báo tương tác nhanh:
- Mọi tương tác follow tự nhiên trên Feed video (`_maybe_follow_video` trong `feed_swipe_smoke.py`) BẮT BUỘC phải bị chặn triệt để.
- Mọi popup/card gợi ý kết bạn, follow lại trên Feed hoặc dạng dialog hệ thống (`dismiss_follow_friends_suggestion_popup` trong `benign_popup.py` và `follow_back_suggestion` trong blind popup rules) BẮT BUỘC KHÔNG ĐƯỢC bấm nút Follow. Thay vào đó phải dismiss (bấm "Không quan tâm" / đóng qua nút X ngữ nghĩa).

## Triển khai kỹ thuật chuẩn
1. **Kiểm tra trạng thái cooldown (`is_account_in_follow_cooldown`)**:
   - Kiểm tra file state cooldown tại `runs/state/follow_state_{machine}_row_{row}.json` hoặc `runs/state/follow_state_{machine}.json`.
   - Nếu `cooldown_until` > thời gian hiện tại (`time.time()`), tài khoản được coi là đang trong cooldown.

2. **Chặn Follow video tự nhiên (`feed_swipe_smoke.py`)**:
   - Trong `_maybe_follow_video(ctx, after_attempt, follow_rate_percent)`:
     Ngay sau kiểm tra `follow_rate_percent <= 0`, gọi `is_account_in_follow_cooldown(ctx)`. Nếu `True` -> trả về `False` ngay lập tức, không parse UI hay tap nút follow.

3. **Xử lý Popup gợi ý bạn bè / Follow lại (`benign_popup.py`)**:
   - Trong `dismiss_follow_friends_suggestion_popup(ctx, xml_root)`:
     Khi tài khoản đang trong cooldown, bỏ qua vòng lặp thử bấm nút Follow (`for _ in range(2):`), nhảy thẳng xuống logic tìm nút đóng X ngữ nghĩa (`_find_follow_friends_semantic_close_control`) để tắt popup mà không phát sinh thêm follow.

4. **Blind Popup Rule (`follow_back_suggestion`)**:
   - Trong `GEMPHONEFARM_BLIND_POPUP_RULES`: không tap vào nút "Follow lại" / "Theo dõi lại" mà ưu tiên tap vào nút dismiss / "Không quan tâm" nếu có, hoặc đóng card gợi ý.

5. **Bộ test hồi quy (`test_feed_swipe_smoke_popups.py`)**:
   - Luôn cập nhật và chạy `pytest D:/Taadaa/tiktok-luot nuoi acc/python_runner/tests/test_feed_swipe_smoke_popups.py` để đảm bảo 100% test case pass khi thay đổi logic popup.
