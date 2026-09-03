# Hotmail/Outlook magic-link branch contract

## Trigger

Use the separate branch when the TikTok surface contains magic-link markers such as:

- `Kiểm tra hộp thư của bạn`
- `Gửi lại email` / `Gửi lại email sau ... giây`
- `liên kết được gửi đến ...`
- `Sign up with a link` / equivalent

This surface is for a not-yet-registered email and normally has no numeric OTP EditText.
A numeric code found in the mailbox is not permission to call the OTP entry handler.

## Required flow

1. Capture and persist a fresh TikTok XML/screenshot; classify the surface as magic-link.
2. For Hotmail/Outlook/Live, open or reuse the verified provider mailbox session.
3. Select the newest TikTok message using timestamp/order evidence. Do not trust an arbitrary first clickable row, stale conversation, or URL-bar text.
4. Prefer a short semantic link action tied to the opened TikTok message (`Verify email`, `Xác minh email`, `Confirm`, `Sign up`, etc.).
5. If semantic UI is absent, use only a bounded visual fallback derived from fresh message-body evidence and record before/after artifacts. Never tap generic `here`, a conversation aggregate, or an unverified link.
6. Recapture after the tap and verify Android resolver/Open-with or TikTok transition. Then return to the existing TikTok task through the guarded resolver/Recents path.
7. Recapture TikTok and verify a real signup transition (`registration_entry`, birthday/password surface, or another explicit post-auth state). A tap alone is not success.

## Fail-closed rules

- `prefer_magic_link=True` must not call numeric Outlook CDP readers as a success path.
- Never call `enter_otp_code()` while the preserved TikTok XML is a magic-link surface.
- If the newest TikTok message or link action cannot be proven, return a distinct blocker such as `OUTLOOK_MAGIC_LINK_ACTION_NOT_VERIFIED` / `NO_HANDLER_IMPLEMENTED` and preserve evidence.
- Keep the existing `registered_otp` path unchanged for accounts that explicitly show numeric OTP markers.
- Live retry requires the repository lifecycle: `DETECTED -> CLASSIFIED -> RECOVERY_RESERVED -> RECOVERING -> RECAPTURED -> RETRYING -> VERIFIED_SUCCESS | FINAL_BLOCKED`.

## Regression matrix

At minimum test:

- magic-link Hotmail skips numeric CDP/browser success and never calls `enter_otp_code`;
- verified newest TikTok message + verified link transition returns `MAGIC_LINK`;
- numeric-only or unverified-link mail fails closed;
- registered OTP still calls the numeric path;
- Gmail magic-link semantic/quoted-body behavior remains intact.

The live STT30 failure that motivated this contract was: Outlook CDP returned a fresh six-digit value, then the caller attempted numeric entry while TikTok still showed `Kiểm tra hộp thư`, producing `OTP_ENTRY_SCREEN_MISMATCH_MAGIC_LINK`.

## Live-run lessons (STT30, 2026-08-11, cùng ngày phát hiện)

1. **Đừng chạy lại từ đầu khi máy đang đứng sẵn ở màn magic-link** — failure UI preserved từ run trước. Full-flow restart sẽ nhận nhầm tab Điện thoại/Email, tap `Gửi lại email` nhiều lần (resend spam), timeout chờ email field rồi kết luận SAI "tất cả email đã có TK TikTok". Check màn thật (screencap + XML live) trước; đang ở magic-link → `--resume` tại chỗ: `SOCIAL_PREFERRED_EMAIL=<email> python -u social_reg_v1.py <serial> <stt> --ss --defer-tracking-write --resume`. Các mail vừa resend sẽ được nhánh magic-link đọc.
2. **Run exit-0 để lại lock `handoff`**: lần chạy sau bị skip `device lock active` (path machine_30.lock.json, pid cũ). Verify PID chết qua `wmic` rồi rm CẢ `machine_<stt>` + `serial_<serial>` lock trước khi retry.
3. **Nhánh mới `_read_outlook_magic_link_with_evidence`** (thêm 2026-08-11, social_reg_v1.py): inbox verified → `_outlook_newest_tiktok_row` (row TikTok clickable đầu tiên theo DOM order newest-first + time token, loại url_bar) → mở mail (bắt buộc Chrome + text TikTok) → `_outlook_magic_link_semantic_action` (short clickable Chrome node, labels `Xác minh email`/`Verify email`/`Confirm`/`Sign up`..., KHÔNG có 'here') hoặc visual fallback CHỈ tap node clickable có `https://` trong chính label → recapture transition (TikTok foreground / Open-with dialog handled) → `"MAGIC_LINK"`. Helper trả None → `_capture_tiktok_email_otp_final_blocked(...OUTLOOK_MAGIC_LINK_ACTION_NOT_VERIFIED)` raise NGAY (đứng trước env-gated refuse lẫn shared resend) → không resend, không enter, không health cleanup numeric. Regression: `tests/test_login_outlook_magiclink_branch.py`.
