# Quy Tắc Chặn Follow Tự Nhiên & Popup Follow Trong Thời Gian Cooldown (Case 161)

## 1. Bối cảnh & Nguyên lý (Anti-Fraud TikTok)
- Khi tài khoản bị TikTok phạt nhả follow (Action Block/Silent Drop) được ghi nhận vào `follow_state_*.json`:
  - Mọi request tap Follow (trên video Feed, nút Follow lại trên thẻ đề xuất bạn bè, hoặc nút Follow trên popup bạn bè) đều bị TikTok server âm thầm hủy (Silent Drop).
  - Nghiêm trọng hơn: Mỗi lần gửi request follow trong thời gian đang thụ án phạt, thuật toán anti-spam của TikTok sẽ hiểu là bot tiếp tục cố chấp spam -> tự động reset hoặc gia hạn thêm thời gian cooldown (án chồng án).

## 2. Các chốt chặn đã tích hợp vào code flow (`tiktok-luot nuoi acc`)

1. **Helper kiểm tra cooldown (`feed_swipe_smoke.py`)**:
   - `is_account_in_follow_cooldown(ctx)`: Kiểm tra các file `follow_state_{machine}_row_{row}.json` hoặc `follow_state_{machine}.json`.
   - Đối soát `cooldown_until_at` (ISO timestamp UTC), `cooldown_until_date` và `follow_failed_date`. Trả về `True` nếu nick đang bị khóa.

2. **Chặn follow tự nhiên trên video feed (`_maybe_follow_video`)**:
   - Chèn guard kiểm tra `is_account_in_follow_cooldown(ctx)` ngay đầu hàm.
   - Nếu đang cooldown: Ghi log `result="skipped", error="account is in follow cooldown (imprisoned)"` và return `False` ngay, không capture XML hay click follow video.

3. **Chặn follow lại trên thẻ gợi ý bạn bè Feed (`GEMPHONEFARM_BLIND_POPUP_RULES`)**:
   - Rule `follow_back_suggestion`: Chuyển hành vi từ tap "Follow lại" sang tap nút "Không quan tâm" (`@text="Không quan tâm"` hoặc `@resource-id="com.ss.android.ugc.trill:id/cv6"`).
   - Tự động đóng thẻ gợi ý mà không gửi bất kỳ follow request nào lên server TikTok.

4. **Chặn follow bạn bè trên popup (`dismiss_follow_friends_suggestion_popup` trong `benign_popup.py`)**:
   - Kiểm tra `is_account_in_follow_cooldown(ctx)`.
   - Nếu tài khoản đang trong cooldown: Đặt `follow_limit = 0`, bỏ qua hoàn toàn vòng lặp tap 1–2 nút Follow bạn bè, chuyển thẳng sang đóng popup bằng nút `X` / Semantic Close control.
