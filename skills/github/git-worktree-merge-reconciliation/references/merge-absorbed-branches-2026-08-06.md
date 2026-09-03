# Merge 5 branch absorbed vào master — 2026-08-06

Repo `D:\Taadaa\tiktok-luot nuoi acc`. User: "dọn working tree, merge check conflict trùng vào main, xoá tree".

## Branch đã xử lý

| Branch | Fix thật | Kết quả |
|---|---|---|
| codex/fix-machine-39-link-email | `live.py` thêm allow_benign_popup_dismiss | Merge thủ công conflict: live.py deleted ở master → `git rm -f`, test dùng `MultiMachineSessionRunner` (module đã xoá) bỏ. Commit merge. |
| codex/fix-machine-48-friends-nav | NAVIGATION_MISMATCH helpers + abort-on-drift | Master refactor đã có hết (helper + retry_navigation). `-X ours` → no-op. |
| codex/fix-notification-activity-log | sticky profile header filter | Master `_find_sticky_profile_header` refactor có display_name_anchor. `-X ours` + `git rm live.py`. |
| opencode/calm-cactus | retap profile on degraded XML drift | Diff -w thật chỉ +63 dòng (32925 dòng là CRLF churn). Master đã có `_try_profile_retap_on_drift`. `-X ours` giữ HANDOFF.md. |
| opencode/misty-comet | popup_changed re-check sau close | Resolve xong: benign_popup.py auto-merge OK, conflict test_benign_popup giữ HEAD (master refactor tách sponsored_ad_feedback + playcore thành 2 test riêng, supersede test feature_promo cũ), HANDOFF.md giữ cả 2 section. Commit `842d2dd`. |
| codex/ui-capture-041-validation-20260731 | pin core 0.4.5 + budget capture + staggered startup | 5 conflict (requirements, run-feed-session.ps1, ui_capture.py, multi_machine, test_ui_dump). Giữ HEAD toàn bộ (master tiến hóa hơn: wheel 0.4.18>0.4.5, lock contract mới). Sửa 1 test obsolete: `test_scheduler_reservations_never_take_over_retained_locks` assert `bypass_proxy_readiness` (param HEAD đã bỏ) → assert `takeover_scope=None` + `takeover_authorized=False`. Commit `92245c5`. |
| codex/tiktok-add-phone-vietnamese | WIP Vietnamese add-phone typed close test + ui-compat doc | User chọn giữ work dở dù test fail (tham chiếu `detect_tiktok_popup_action` chưa implement). Commit `d16c5db` vào branch, merge sạch vào master `349c052`, xóa worktree + branch. 1 test WIP fail chấp nhận. |

## Bài học chính

1. **`git diff -w` trước khi kết luận branch to/nhỏ**: diffstat phình vì CRLF↔LF churn. calm-cactus: 16691+/16431- nhưng thật +63 dòng.
2. **Master refactor = thường đã hấp thụ fix branch cũ** — grep tên hàm branch thêm trên master, so mục đích không so text. Khi có → `-X ours` merge sạch, không cần resolve thủ công.
3. **`git merge --abort` fail khi index đã stage** (sau `git add` trong conflict) — `error: Entry not uptodate`. Phải `git reset --hard <pre-merge-commit>`.
4. **SUÝT MẤT 2400 dòng**: python `str.replace` dùng marker `def _safety_from_row` cách block ~2400 dòng → cắt cả phần giữa, file 16K dòng vỡ syntax. Phục hồi = reset --hard. CẤM string surgery block cách xa marker; dùng `-X ours` + thêm nhỏ thủ công.
5. **File CRLF**: patch tool đổi LF→CRLF cả file (diff phình). Sửa bằng python `io.open(newline='')` + `NL='\r\n'`, match đúng.

## Xác nhận pre-existing test fail

4 fail `test_device_lock.py` fail cả khi `git stash` → pre-existing (venv `hermes-agent` site-packages có automation_core cũ shadow bản local). Không phải do thay đổi mình.

## Khác

- `AGENTS.md` + `AGENTS.md.*.bak` lộn xộn giữa các worktree (policy sync) — không đụng, không commit.
- Worktree codex `tiktok-add-phone-vietnamese` có uncommitted thật (fix Vietnamese add-phone popup + test) — đáng giữ, KHÔNG xoá mù khi chưa hỏi user.
