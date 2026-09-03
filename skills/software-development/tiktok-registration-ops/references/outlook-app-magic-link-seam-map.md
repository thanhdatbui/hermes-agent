# Outlook-app magic-link branch — current-tree seam map (2026-08-15, máy 38)

Read-only review của dirty worktree (HEAD 3836702 / reg-stable-0722, dirty fixes chưa commit). Mục đích: seam tối thiểu để thêm nhánh magic-link Outlook-app cho signup TikTok mà không mất fix dirty, và cảnh báo tương thích với implementation Chrome cũ.

## Current tree state (sau revert 0722 + dirty fixes)

- `social_reg_v1.py` 6777 dòng. Dirty: no-auto-lock (`device_lock.py`), `_fetch_post_auth_email_code` (routing [8b]/[9] → Outlook app), `_try_get_otp_outlook_app` shim (không nhận password, `_password=None`), resume mailbox read, profile detection, deferred tracking.
- Untracked mới: `hotmail_provider.py` + `tests/test_hotmail_provider.py` + `tests/test_post_auth_email_verification.py` (fix post-auth routing máy 38).
- `hotmail_provider.py` = thin adapter: `read_tiktok_otp_from_outlook_app` → `D:\Taadaa\Hotmail\flows\hotmail_login.py` (load qua importlib, module `_taadaa_canonical_hotmail_login`, root override env `TAADAA_HOTMAIL_REPO`). KHÔNG forward password. Artifact dir `machine-<stt>` khi có `stt`.

## Seam tối thiểu (consumer-only)

1. `handle_tiktok_email_otp` (L5933) — nhánh non-Gmail L5979–6003 hiện gọi thẳng `_try_get_otp_outlook_app` (numeric only). Cần: classify màn hiện tại (magic-link markers: `kiem tra hop thu`/`gui lai email`/`lien ket duoc gui`/`sign up with a link`) → magic-link → gọi provider magic-link mới; numeric → giữ nguyên. Provider trả `"MAGIC_LINK"` → return ngay (L6038–6040 đã có sẵn nhánh `code == "MAGIC_LINK"`). Caller L6430 đã xử lý `result_7c == "MAGIC_LINK"` (sleep + dismiss "Mở bằng TikTok") — **không cần sửa caller**.
2. Fail-closed: provider trả None trên màn magic-link → raise `OUTLOOK_MAGIC_LINK_ACTION_NOT_VERIFIED` TRƯỚC nhánh resend L5986–6003 (không resend mù, không rơi numeric).
3. `_fetch_post_auth_email_code` (L5577) — màn post-auth "Xác minh email" ([8b]/[9]) cũng có thể là magic-link: cùng routing ở CẢ 2 call site (L3680, L6251). Grep mọi call site, không chỉ [7c].
4. `enter_otp_code` (L5872) — **CHƯA có guard magic-link**. Cần fail-closed `OTP_ENTRY_SCREEN_MISMATCH_MAGIC_LINK` khi màn còn "Kiểm tra hộp thư" (hiện không có EditText OTP → tap center mù).

## Provider-side (D:\Taadaa\Hotmail, canonical)

- `read_tiktok_otp_from_outlook_app` (flows/hotmail_login.py L900) chỉ đọc numeric OTP từ TikTok-labelled subtree (`_tiktok_otp_from_outlook_xml` L872: node subtree chứa "tiktok" + regex 6 số). KHÔNG có entrypoint magic-link.
- Entrypoint mới đề xuất: `read_tiktok_magic_link_from_outlook_app(adb, device, email, artifact_dir, *, timeout)` cạnh reader numeric — dùng lại `open_outlook_app`/`_outlook_app_open_inbox_from_archive`/`_outlook_app_account_present`/`tap_text`/`ui_xml`: (a) swipe-refresh inbox, (b) chọn mail TikTok mới nhất có time evidence, (c) mở mail, (d) tap semantic action `Xác minh email`/`Verify email`/`Confirm` (KHÔNG tap `here`), (e) recapture verify TikTok transition, (f) trả `"MAGIC_LINK"`.
- **CHƯA có bằng chứng live** rằng mail magic-link TikTok trong Outlook app expose nút link clickable cho uiautomator — cần 1 probe live (dump + screenshot) TRƯỚC khi code để quyết định semantic tap vs fail-closed.

## Historical Chrome implementation (ebf6e4f) — KHÔNG dùng được

- `_read_outlook_magic_link_with_evidence` + `_outlook_magic_link_cdp_tap_target` + `_open_outlook_inbox_verified` mở `com.android.chrome` + CDP `localabstract:chrome_devtools_remote` + VIEW intent `-n Chrome` — vi phạm rule Outlook-app-only (user 2026-08-14).
- Phụ thuộc đã bị XOÁ khi revert 0722: `_semantic_clickable_node`, `_xml_packages`, `_return_to_tiktok_after_magic_link`, `_outlook_inbox_visible`, `MAGIC_LINK_SCREEN_HINTS`, `_classify_after_continue_flat`, `_outlook_login`. Merge nguyên bản = kéo lại toàn bộ Chrome stack + lỗi success giả STT30 (tap link chỉ đưa TikTok foreground màn cũ "Kiểm tra hộp thư", chưa verify).
- CHỈ tái dùng: `_outlook_newest_tiktok_row` (clickable + time token + loại url_bar, y ≥ 240), `_OUTLOOK_MAGIC_LINK_ACTIONS` label list, và pattern regression tests (`tests/test_login_outlook_magiclink_branch.py` — fixture toàn `com.android.chrome` package, phải viết lại cho `com.microsoft.office.outlook`).

## Test/verify checklist (khi implement)

- Unit consumer (mock `hotmail_provider`, không đụng device):
  1) magic-link screen routes hotmail → magic provider, không gọi numeric, không `enter_otp_code`;
  2) numeric screen giữ nguyên path cũ;
  3) provider None → raise `OUTLOOK_MAGIC_LINK_ACTION_NOT_VERIFIED`, parametrize env `{None,"1","0"}`;
  4) provider "MAGIC_LINK" → return ngay, caller L6430 xử lý;
  5) post-auth [8b]/[9] cùng routing magic-link;
  6) `enter_otp_code` reject magic-link screen;
  7) adapter test: không password, artifact dir `machine-<stt>`, timeout truyền đúng.
- Provider (Hotmail repo): `_tiktok_otp_from_outlook_xml` không trả code trên mail link-only; newest-row selection; semantic action không tap `here`.
- Static: `py_compile` cả 2 repo, `git diff --check`, focused suite bằng `env -u PYTHONPATH /d/Taadaa/python-envs/automation/Scripts/python -m pytest`. Test mới CRLF.
- Live (sau code, máy 38): preflight `mResumedActivity` = màn magic-link TikTok → resume canonical → evidence: provider Outlook-app mở, inbox verified + identity, newest TikTok mail, semantic action, transition recapture → `MAGIC_LINK` → màn "Tạo mật khẩu"/birthday (không phải foreground cũ).
