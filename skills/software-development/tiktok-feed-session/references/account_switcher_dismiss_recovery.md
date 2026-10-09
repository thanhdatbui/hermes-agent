# Account Switcher Modal Dismiss & Auto-Recovery Pattern

## Bối cảnh & Vấn đề
Trong flow `verify_and_switch_profile` (`python_runner/flows/feed_swipe_smoke.py`):
Khi profile hiện tại không khớp với `expected_account`, flow mở Account Switcher bottom sheet để tìm và chuyển account.
Nếu `expected_account` không tìm thấy trong danh sách switcher (`_find_account_switch_option` trả về `None`), script ghi nhận `last_reason = "manual-needed:account-switcher-missing-expected: expected account not found in account switcher"`.

## Pitfall nghiêm trọng
Nếu thoát khỏi vòng lặp switcher hoặc kích hoạt `_maybe_recover_missing_account_via_login()` mà **không dismiss modal switcher**:
1. Modal Account Switcher vẫn treo lơ lửng đè lên toàn bộ màn hình Profile/TikTok.
2. Flow auto-recovery login (reconcile) hoặc bất kỳ thao tác UI nào tiếp theo sẽ bị che khuất và chặn tương tác (touch, click, typing), dẫn đến fail liên hoàn hoặc kẹt cứng UI.
3. Khi flow kết thúc và trả về `manual-needed`, màn hình để lại vẫn là modal switcher đang mở, cản trở các lượt can thiệp tiếp theo.

## Quy tắc xử lý chuẩn
1. Trước khi invoke `_maybe_recover_missing_account_via_login` hoặc kết thúc với `manual-needed:account-switcher-missing-expected`:
   - Bắt buộc gửi keyevent BACK (`ctx.adb.shell(["input", "keyevent", "4"])`) để đóng modal switcher.
   - Ghi log với `action="dismiss_switcher_on_missing_account"`.
   - Chờ UI ổn định (`time.sleep(1.0)`).
2. Đảm bảo UI trở về TikTok root / Profile root sạch sẽ trước khi chuyển quyền cho login subprocess hoặc thoát.
