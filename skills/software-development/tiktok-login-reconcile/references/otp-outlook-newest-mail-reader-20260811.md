# OTP Outlook newest-mail reader — session detail 2026-08-11 (STT30)

## Live bug transcript (STT30, serial ce0217126cd4bc640c)
- Email ĐÃ verify qua deep-link → TikTok mở CommonFlowActivity "Nhập mã 6 chữ số".
- Log: `[otp-cdp] Fresh Outlook code found in background tab` → nhập (540,738) → reject
  → tap "Gửi lại mã" → đọc lại vẫn code cũ → reject 2 lần liên tiếp
  → `OTP_REJECTED_AFTER_FRESH_RETRY`.
- Evidence: nhiều tab Chrome (161/163/165/168) mở CÙNG mail cũ
  (URL `.../mail/deeplink/warm?tfa=...&id=AQQk...`, mail 20:45, code 987307/335276)
  trong khi TikTok resend 21:15 gửi mail MỚI chưa được mở.

## Root cause class
`_try_get_otp_outlook_cdp` (CDP scan background tabs theo DOM-order) và
`_try_get_otp_browser` (fast-path CDP + `find_text_tap("TikTok")` + preview-read)
quét DOM tùy tiện, KHÔNG có guard "mail TikTok mới nhất". Với nhiều tab mở cùng
mail cũ → đọc code cũ → nhập → reject. Resend handler
`_request_and_read_fresh_tiktok_email_otp` dùng CÙNG reader → sau "Gửi lại mã"
vẫn đọc code cũ.

## Fix (patch tối thiểu, consumer-only)
New helper `_try_get_otp_outlook_newest(device_id, email, password, *, stt=None, timeout=240)`:
1. `_open_outlook_inbox_verified(device_id, email, password, timeout=timeout)` → None ⇒ fail closed
2. `_outlook_newest_tiktok_row(inbox_xml)` → None ⇒ fail closed (save_xml_blob `outlook_otp_no_row_<stt>`)
3. `save_xml_blob(inbox_xml, f"outlook_otp_row_{stt}")` + `screenshot` (try/except) + `tap(*row["coord"], wait=D_MEDIUM)`
4. Loop 4x: `extract_otp_from_xml(get_ui_xml(device_id))` → trả code; else `swipe(540,1300,540,400,"500")` + sleep 1.2
5. Guard: `email.lower().endswith(("@hotmail.com","@outlook.com","@live.com"))` else None

Call-site replacements:
- `handle_tiktok_email_otp` nhánh `else` (non-magic, non-Gmail): `code = _try_get_otp_outlook_newest(device_id, email, password, stt=stt)`; XÓA block fallback `if not code and not gmail and not prefer_magic_link: code = _try_get_otp_browser(...)`.
- `_request_and_read_fresh_tiktok_email_otp`: 2 call sites (`if not code and not gmail:` và sau `_swipe_outlook_inbox_refresh` + sleep 3) → `_try_get_otp_outlook_newest(..., stt=stt)`; bỏ nhánh `if not code2: code2 = _try_get_otp_browser(...)`.

Keep defined (backward-compat + direct tests): `_try_get_otp_outlook_cdp`, `_try_get_otp_browser`.

## Test updates (TDD)
`tests/test_login_outlook_magiclink_branch.py`:
- `test_hotmail_registered_otp_still_calls_numeric_path_and_enters_code`: mock `_try_get_otp_outlook_newest` → "123456"; assert `newest_calls == [True]`, `cdp_calls == []`, `browser_calls == []`, entered, `reader_calls == []`.
- New `test_outlook_numeric_reader_taps_newest_tiktok_row_and_reads_its_code`: mock `_open_outlook_inbox_verified` → 2-row inbox (TikTok 1:07 SA + TikTok 1:05 SA, bounds [100,320][900,470] và [100,520][900,670]); mock `get_ui_xml` → opened mail "Mã xác minh: 654321"; real `_outlook_newest_tiktok_row`; assert code == "654321", taps == [(500, 395)] (center của row mới nhất).
- New `test_outlook_numeric_reader_fails_closed_when_no_newest_row`: inbox chỉ có "Facebook" → None, taps == [], `get_ui_xml` mock throw nếu bị gọi.
- New `test_hotmail_registered_otp_newest_fail_closed_never_uses_old_codes`: handler-level — newest → None, cdp/browser mock trả code cũ "987307"/"335276", resend mock → None, `_require_hotmail_function` mock → "ALIVE", `_outlook_inbox_visible` → True; assert `pytest.raises(RuntimeError, match="OTP_RESEND_NO_FRESH_CODE")`, cdp/browser/entered == [].

`tests/test_login_otp_health_fallback.py`:
- `test_hotmail_otp_failure_checks_inbox_and_marks_dead` / `test_hotmail_otp_failure_live_inbox_keeps_mail`: đổi mock `_try_get_otp_outlook_cdp` → `_try_get_otp_outlook_newest` → None.
- `test_hotmail_gmail_timeout_falls_back_to_outlook_browser` → rename `..._outlook_newest_reader`: mock newest → "123456", assert `browser_calls == []`.

## Verify commands (đã chạy, kết quả THẬT)
```bash
cd /d/Taadaa/Tiktok_Reg
env -u PYTHONPATH /d/Taadaa/python-envs/automation/Scripts/python -m py_compile social_reg_v1.py
env -u PYTHONPATH /d/Taadaa/python-envs/automation/Scripts/python -m pytest \
  tests/test_login_outlook_magiclink_branch.py tests/test_login_magiclink_classify.py -q
# → 46 passed in ~1.1s (43 baseline + 3 mới)
env -u PYTHONPATH /d/Taadaa/python-envs/automation/Scripts/python -m pytest \
  tests/test_login_otp_health_fallback.py -q -k "not test_outlook_browser_login_is_not_skipped_by_inbox_url_bar"
# → 16 passed, 1 deselected (deselected = pre-existing failure, đụng real adb trong _try_get_otp_browser, KHÔNG sửa)
git diff --check
```
Ad-hoc verify script: bootstrap bằng `tempfile.mkstemp(prefix="hermes-verify-", dir=tempfile.gettempdir())`,
chạy bằng env python, xóa trong `finally`; kết quả = ad-hoc verification (không phải suite canonical).
Quan trọng: file working-tree có sẵn thay đổi worker khác — sau patch check `git diff --numstat <file>`
và `grep -n` call sites để chắc chỉ đổi đúng dòng của mình (CRLF file có thể làm diff phình).

## Post-patch sanity grep
```bash
grep -n "_try_get_otp_outlook_cdp\|_try_get_otp_browser(" social_reg_v1.py
# chỉ còn: định nghĩa (9265, 9335) + self-reference trong _try_get_otp_browser (9359, 9554) + comment
grep -n "_try_get_otp_outlook_newest(" social_reg_v1.py | grep -v "def _"
# 3 call sites: handle numeric branch + 2 trong resend handler
```
