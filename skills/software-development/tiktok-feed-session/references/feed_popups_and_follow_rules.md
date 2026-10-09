# Feed Popup & Follow Suggestion Rules

## 1. Follow Back & Friend Suggestions on Feed
- **Rule `follow_back_suggestion`** (`feed_swipe_smoke.py`):
  - Khi xuất hiện thẻ gợi ý "Bạn bè với", "Người bạn có thể biết" kèm nút "Follow lại" / "Theo dõi lại" và nút "Không quan tâm":
  - **Mục tiêu**: Bấm "Không quan tâm" để bỏ qua thẻ gợi ý, không bấm "Follow lại" để tránh bị spam follow ngoài ý muốn và vi phạm quota/rate limit.
  - Test fixture tương ứng: `test_follow_back_suggestion_taps_follow_back_button` trong `python_runner/tests/test_feed_swipe_smoke_popups.py`.

## 2. Follow Cooldown Guard
- Khi xét duyệt follow tự động trên video feed (`_maybe_follow_video` trong `feed_swipe_smoke.py`) hoặc popup gợi ý bạn bè (`dismiss_follow_friends_suggestion_popup` trong `benign_popup.py`):
  - Luôn kiểm tra cooldown follow của tài khoản (`is_account_in_follow_cooldown(ctx)`). Nếu đang trong thời gian cooldown, phải skip việc bấm follow hoặc đặt `follow_limit = 0`.

## 3. Test Runner Command
Để chạy test popup & dismiss rules trong môi trường Windows Git-Bash mà không bị xung đột môi trường Python:
```bash
cd "/d/Taadaa/tiktok-luot nuoi acc" && PYTHONPATH= /c/Users/Kibe/AppData/Local/Programs/Python/Python312/python.exe -m pytest python_runner/tests/test_feed_swipe_smoke_popups.py
```
