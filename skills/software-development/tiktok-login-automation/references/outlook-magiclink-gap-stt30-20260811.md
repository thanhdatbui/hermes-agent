# Outlook/non-Gmail magic-link gap — STT30 (audit read-only 2026-08-11)

Audit read-only trên `D:\Taadaa\Tiktok_Reg` — KHÔNG sửa file, không live ADB/mail.
Verdict: **APPROVED kèm điều kiện (MINOR bắt buộc)**. Implement CHƯA tồn tại — đây là
gap đã xác nhận tại code + đề xuất đã audit, áp dụng khi sửa.

## Context

- Live STT30: màn TikTok **"Kiểm tra hộp thư của bạn"** (magic-link signup verify,
  email CHƯA có TK), Outlook CDP/browser tìm thấy mã 6 số TRƯỚC → code gọi
  `enter_otp_code` vào TikTok dù màn KHÔNG có field OTP → `OTP_ENTRY_SCREEN_MISMATCH_MAGIC_LINK`.
- Label `OTP_ENTRY_SCREEN_MISMATCH_MAGIC_LINK` **KHÔNG tồn tại trong code** (grep toàn
  repo = 0) — là label chuẩn hóa cần định nghĩa mới trong guard.

## Execution path hiện tại (non-Gmail)

1. Bước 7c (`social_reg_v1.py` L11166-11210) → `handle_tiktok_email_otp` L10282.
2. `prefer_magic_link` computed L10305-10316 (`MAGIC_LINK_SCREEN_HINTS` L1710 chỉ 3
   markers — thiếu "kiem tra email"/"check your email" so với `MAGIC_VERIFY_HINTS`
   L1716 có 6) — **CHỈ truyền vào Gmail reader** `_read_gmail_otp_with_target_recovery` L10336.
3. Non-Gmail: `_try_get_otp_outlook_cdp` L9247 — CDP scan DOM Outlook, mọi
   div/span/a chứa "tiktok" + số 6 chữ số, trả **candidate ĐẦU TIÊN** theo DOM order
   (commit `6149f26` 2026-08-11 bỏ `reversed()`: DOM liệt kê mail mới nhất trước,
   cũ sau — probe máy 57 1:07 AM trước 1:05 AM). **KHÔNG timestamp check**.
4. `_try_get_otp_browser` L9317 — preview scan `extract_otp_from_xml` L9563/L9571:
   số 6 chữ số ĐẦU TIÊN bất kỳ, KHÔNG recency check. Chỉ khi không có số mới thử
   tap link L9550-9555/L9577-9583 → `"MAGIC_LINK"`.
5. code = SỐ → `_enter_tiktok_email_otp_with_one_fresh_retry` L10103 → `enter_otp_code` L10197.

## Root cause chain

- `prefer_magic_link` KHÔNG propagate sang nhánh Outlook: `handle_tiktok_email_otp`
  L10374-10379 và `_request_and_read_fresh_tiktok_email_otp` L10072-10075 (không có
  param prefer_magic_link).
- Outlook reader không freshness/timestamp guard. Gmail thì ĐÃ có (đối chứng):
  `_gmail_timestamp_is_recent_after` L5995, `_gmail_latest_message_header` L6294,
  `_gmail_semantic_node` L6239, `_gmail_visual_magic_link_target` L6655 +
  `_verify_visual_magic_link_transition` L6744 — 57 tests, docs/ui-compatibility.md 2026-08-08.
- `enter_otp_code` guard L10215-10226: list
  `["kiem tra email","check your email","xac minh","nhap ma","verification"]` —
  thiếu `"kiem tra hop thu"`/`"gui lai email"`/`"sign up with a link"`. Màn magic
  signup thường kèm text **"Xác minh email"** → lọt qua substring `"xac minh"`;
  `_post_auth_ui_state` L4419 cũng trả `otp_required` cho `"xac minh email"` →
  `otp_nodes` rỗng (không EditText <200px) → **blind tap (540,900) L10247 +
  find_text_tap("Xác nhận"/"Tiếp tục") + keyevent Enter**.
- Không có `"xac minh"` → raise `[otp-enter] TikTok OTP screen unavailable after
  Recents recovery` L10226 / `TIKTOK_REGISTRATION_RESTART_REQUIRED` L10220.

## Đề xuất tối thiểu (5 điểm, provider-local, KHÔNG đụng automation-core)

1. **Propagate context**: `_try_get_otp_outlook_cdp(device_id, prefer_magic_link=False,
   not_before=None)` + `_try_get_otp_browser(..., prefer_magic_link=False,
   not_before=None)`; truyền từ `handle_tiktok_email_otp` L10374-10379 và
   `_request_and_read_fresh_tiktok_email_otp` (thêm param).
2. **Magic mode = CẤM numeric**: khi `prefer_magic_link=True`, cả 2 reader KHÔNG trả
   số 6 chữ số (bỏ nhánh scan số, trả None) → caller không bao giờ enter code.
3. **Outlook link-only handler** (mirror Gmail pattern): refresh inbox → mở mail
   TikTok MỚI NHẤT có timestamp ≥ not_before (evidence redacted) → bounded scroll
   xuống cuối (Outlook gom thread, button nằm cuối mail mới nhất) → tap **exact
   semantic action** (`_GMAIL_MAGIC_LINK_ACTIONS` L6168: "Xác minh email"/"Verify
   email"/"Xác nhận"/"Confirm"/"Click here"... — dùng chung `_semantic_clickable_node`
   L6185) → recapture verify transition → `"MAGIC_LINK"`; thiếu evidence → fail closed None.
4. **`enter_otp_code` fail-closed guard**: magic markers + không OTP EditText → save
   artifacts + raise `RuntimeError("[otp-enter] OTP_ENTRY_SCREEN_MISMATCH_MAGIC_LINK: ...")`;
   CẤM blind tap/Enter/"Tiếp tục" trên màn không field. Real OTP login (EditText
   <200px + "nhap ma") giữ path cũ.
5. **Resend path**: sau resend vẫn chỉ đọc link mới nhất; link hết hạn 20 phút,
   cooldown ~46-60s — tuân thủ rule 2-attempt.

**CẤM CDP JS click** cho magic link: `document.querySelector(...).click()` navigate
tab Chrome sang TikTok WEB, bypass deep-link app — chỉ UI semantic tap +
`_return_to_tiktok_after_magic_link` L9711 (đã có open-with dialog guard L9656).

## Test cases (khi implement)

- T1 regression: 8 case `test_login_magiclink_classify.py` + `test_detect_after_continue.py`
  giữ nguyên; 57 tests magic-link/Gmail pass.
- T2: `handle_tiktok_email_otp` non-Gmail + màn magic: mock CDP (DOM có 6 số) trả None
  khi prefer_magic_link=True; browser trả "MAGIC_LINK"; assert `enter_otp_code`/
  `type_into_node` KHÔNG gọi numeric.
- T3: `_try_get_otp_browser` magic mode: mail cũ (timestamp < not_before) → None,
  KHÔNG tap, không gọi nhánh `extract_otp_from_xml`.
- T4: `enter_otp_code` guard: "Kiểm tra hộp thư" + "Gửi lại email" + có substring
  "Xác minh email", không EditText → raise `OTP_ENTRY_SCREEN_MISMATCH_MAGIC_LINK`;
  không tap/shell/keyevent; artifacts lưu.
- T5 negative: màn OTP login thật vẫn enter — `test_enter_otp_foreground.py` giữ nguyên.
- T6: `_request_and_read_fresh_tiktok_email_otp` propagate prefer_magic_link/not_before
  vào cả 2 non-Gmail readers (assert kwargs).
- T7: classifier: "Gửi lại email" alone → `verify_email_pending`; có "nhập mã" kèm →
  `registered_otp` (priority real-OTP, L1733).
- Entry docs/ui-compatibility.md: ID đề xuất `tiktok-reg-magiclink-outlook-guard-20260811`.

## Rủi ro (bắt buộc xử lý)

1. **Click nhầm link (cao nhất)**: thread Outlook gom mọi mail TikTok — mail cũ trên,
   mới nhất CUỐI. Tap nhầm "Xác nhận" mail cũ → link hết hạn 20 phút → mất attempt,
   có thể mở URL sai. **Cấm** `find_text_tap("TikTok")` để mở mail (mở row đầu = mail
   cũ); khớp với bài Gmail 2026-08-08 (nút đỏ "Xác minh email", quoted-text expansion).
2. **Newest-mail evidence**: timestamp Outlook dạng "1:07 SA/AM"/"Hôm qua" — mở rộng
   parser từ `_gmail_preview_timestamp_age_minutes` L5748; thiếu evidence → fail
   closed, không đoán, không log OTP/token/link đầy đủ.
3. **Numeric lọt màn không field**: reader cấm numeric + `enter_otp_code` fail-closed
   = double protection (pattern Gmail guard 2026-08-08).
4. **`_post_auth_ui_state` trả `otp_required` cho màn magic** (substring "xac minh
   email" L4419) — guard phải dựa marker magic-link + sự tồn tại OTP EditText, không
   chỉ dựa state.
5. **Repo dirty sẵn** (AGENTS.md/tests/scripts modified từ trước) — stage đúng scope;
   file CRLF, `git diff --check`; pytest interpreter `tiktok-reg-recovery`
   (PYTHONPATH gồm site-packages + Tiktok_Reg + Hotmail).

## Tooling notes (confirmed lần này)

- `search_files` trả rg IO error với path `D:\...` trên git-bash → fallback
  `rg -n "pattern" -g '*.py' .` / grep qua terminal.
- `.runtime/audit_ml_raw*.json` = artifact audit cũ (deepseek-v4-flash-free,
  finish_reason length) — không phải evidence live mới.
- handoff.md entry cuối 2026-08-09; STT30 không có trong handoff repo — root cause
  theo mô tả parent + xác nhận bằng code path.