# Outlook magic-link fail-closed branch — session detail (2026-08-11, STT30)

## Context
STT30 2026-08-11: numeric code đọc từ tab nền và nhập trên màn magic-link →
`OTP_ENTRY_SCREEN_MISMATCH_MAGIC_LINK`. Worker trước đã tách nhánh Outlook
magic-link khỏi OTP số (`_read_outlook_magic_link_with_evidence`, uncommitted
trong working tree). Task tiếp theo mô tả bug "helper trả None → mặc định có
thể rơi xuống `_request_and_read_fresh_tiktok_email_otp`" — nhưng khi đọc
working tree, raise block đã có sẵn; bug mô tả khớp trạng thái TRƯỚC patch.
Việc còn thiếu là test coverage case env=`1`.

## Source map (social_reg_v1.py)
- `_read_outlook_magic_link_with_evidence` ~L9786: trả `None | "MAGIC_LINK"`.
- `_capture_tiktok_email_otp_final_blocked` ~L10177: save xml + screenshot rồi
  **raise RuntimeError vô điều kiện** `[otp][FINAL_BLOCKED][<signature>]`.
- `handle_tiktok_email_otp` ~L10678-10715:
  ```python
  if not code and not email.lower().endswith("@gmail.com"):
      if prefer_magic_link:
          code = _read_outlook_magic_link_with_evidence(device_id, email, password, stt=stt)
          if code != "MAGIC_LINK":
              _capture_tiktok_email_otp_final_blocked(device_id, stt, "OUTLOOK_MAGIC_LINK_ACTION_NOT_VERIFIED")
      else:
          code = _try_get_otp_outlook_cdp(device_id)
  if not code and not email.lower().endswith("@gmail.com") and not prefer_magic_link:
      code = _try_get_otp_browser(device_id, email, password)
  if not code and prefer_magic_link and os.environ.get("SOCIAL_NO_OTP_RESEND", "").strip() == "1":
      log("... refuse resend")          # chỉ Gmail magic-link path còn chạm tới
  elif not code:
      code = _request_and_read_fresh_tiktok_email_otp(...)   # shared numeric resend
  ```
- Gmail magic-link đi qua `_read_gmail_otp_with_target_recovery(prefer_magic_link=...)`
  ~L8157 — được phép rơi xuống shared resend (giữ nguyên).
- Caller không nuốt RuntimeError (tiktok_login_v1.py:670, social_reg_v1.py
  11525/11603/12000/12081 gọi trực tiếp) → raise lan đúng tới runner.

## Test gap đã đóng
- Test cũ `test_hotmail_magic_link_unverified_raises_distinct_and_never_enters_code`
  chỉ `monkeypatch.delenv("SOCIAL_NO_OTP_RESEND")` → chứng minh env unset.
- Bổ sung `test_hotmail_magic_link_unverified_blocks_regardless_of_resend_env`
  `@pytest.mark.parametrize("resend_env", [None, "1", "0"])`:
  setenv/delenv tương ứng + helper→None + counter mocks
  (`_request_and_read_fresh_tiktok_email_otp`, `enter_otp_code`,
  `_try_get_otp_outlook_cdp`, `_try_get_otp_browser`, `find_text_tap`)
  → `pytest.raises(RuntimeError, match="OUTLOOK_MAGIC_LINK_ACTION_NOT_VERIFIED")`
  + mọi counter rỗng.
- `_mock_otp_env` chung trong test file: delenv 3 vars, mock shell
  (`mResumedActivity: <APP_PACKAGE>/.OtpActivity`), get_ui_xml, save_ui_xml,
  screenshot, save_timeout_artifacts, time.sleep.

## Kết quả
- `tests/test_login_outlook_magiclink_branch.py` + `tests/test_login_magiclink_classify.py`
  → 25 passed (13 + 12).
- `tests/test_login_otp_health_fallback.py` → 16 passed + 1 pre-existing fail
  `test_outlook_browser_login_is_not_skipped_by_inbox_url_bar` (StopIteration do
  mock `get_ui_xml` iterator hết trang; không liên quan, không sửa).
- `py_compile social_reg_v1.py tests/...` OK; `git diff --check` OK (chỉ LF→CRLF warning).

## Verify recipe (ad-hoc, không live ADB/mail)
1. Suite: `python -m pytest tests/test_login_outlook_magiclink_branch.py tests/test_login_magiclink_classify.py -q`
2. Compile + diff: `python -m py_compile social_reg_v1.py tests/test_login_outlook_magiclink_branch.py && git diff --check`
3. Temp verify script (`%TEMP%/hermes-verify-*.py`, dọn sau khi chạy):
   - `inspect.getsource(social.handle_tiktoken_email_otp)` → assert
     `magic_idx < resend_idx < handler_idx` (ordering).
   - `pytest.main([node, "-q", "-p", "no:cacheprovider"])` chạy đúng node parametrize.
   - Behavioral: `mock.patch.dict(os.environ, {}, clear=True)` + setenv từng case;
     mock helper→None + counters → gọi `handle_tiktok_email_otp("serial-30",
     "target@hotmail.com", "mail-password", stt=30)` → expect RuntimeError chứa
     `OUTLOOK_MAGIC_LINK_ACTION_NOT_VERIFIED` và mọi counter = 0.
   - Kết quả thật: log `[otp-recovery] FINAL_BLOCKED signature=OUTLOOK_MAGIC_LINK_ACTION_NOT_VERIFIED stt=30` cho cả 3 env.

## Tool note
- `search_files`/rg với path `D:\...` (kể cả `D:/...`) fail "IO error ... /d/Taadaa/..."
  trên host này → dùng `grep -rn ...` qua terminal (git-bash) cho repo
  `D:\Taadaa\Tiktok_Reg`; `git diff`/`sed`/`read_file` đều OK với path đó.
- Repo có nhiều file dirty pre-existing (AGENTS.md, scripts, tests...) —
  chỉ `git add` đúng file mình sửa; test file mới untracked (`??`), không commit
  khi task yêu cầu "không commit/push".
