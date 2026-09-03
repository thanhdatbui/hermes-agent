# Tiktok_Reg recovery runs 2026-08-06 — per-target signatures & evidence

## Scope
10 máy mail chưa reg TikTok (detector `_detect_clean.py` → `_clean_targets.json`):
STT 30, 31, 34, 36, 38, 39, 54, 55, 57, 66 (5 Hotmail + 5 Gmail). Chạy
`scripts/run_tiktok_recovery_new_handler.py --stt ... --target-file _clean_targets.json
--max-workers N --full-scope-takeover --recover-after-failure` bằng venv
`D:\Taadaa\python-envs\tiktok-reg-recovery` (automation-core 0.4.31).

## Run 1 `20260806-065254` — 10/10 FINAL_BLOCKED, 0 workbook write
| STT | signature | note |
|---|---|---|
| 30 | PROCESS_EXIT_1 | TikTok crash về Launcher sau relaunch (`fail_tiktok_not_foreground_after_launch`) |
| 31 | GMAIL_OTP_TIMEOUT | Gmail search "TikTok" timeout 150s (UI treo, không phải thiếu OTP) |
| 34 | PROCESS_EXIT_1 | OTP thật `097038` bị "Skip stale opened-message code" — extract nhầm `111034` trong email |
| 36 | GMAIL_TARGET_ACCOUNT_NOT_LISTED | account không có trong AccountManager; recovery đòi phone verify |
| 38 | ADB_TRANSPORT_RECOVERY_FAILED | lock cross-project `hotmail-change-info` |
| 39 | NO_HANDLER_IMPLEMENTED:DEVICE_NOT_PROVISIONED | giữ (đã biết, KNOWN_NO_HANDLER) |
| 54 | HOTMAIL_OTP_TIMEOUT → LoginBlocked | mail die → đã xóa source + Audit Pending (có backup) |
| 55 | GMAIL_TARGET_ACCOUNT_NOT_LISTED → CAPTCHA | mail đã xóa source (CAPTCHA-confirmed, có backup) |
| 57 | OTP_REJECTED_NO_FRESH_CODE | resend → CDP trả đúng code cũ đã reject → refuse reuse |
| 66 | PROCESS_EXIT_1 | profile tab không vào được |

## Run 2 `20260806-090334` (sau 3 fix code) — 6/6 FINAL_BLOCKED
| STT | signature | note |
|---|---|---|
| 30 | PROCESS_EXIT_1 | vào profile + dropdown OK nhưng tap "Thêm tài khoản" không tìm thấy nút (`[04_add_account]`) |
| 31 | GMAIL_OTP_TIMEOUT | search timeout; sau đó Google yêu cầu đăng nhập lại → mail-die Audit Pending (account không trên máy) |
| 34 | GMAIL_TARGET_ACCOUNT_NOT_LISTED | fix OTP marker-node ĐÃ ĂN (hết "Skip stale"); máy mất account Gmail trên máy (`target_account_unverified`) |
| 36 | GMAIL_TARGET_ACCOUNT_NOT_LISTED | dừng sớm hơn: `GMAIL_RECOVERY_AVATAR_POSTCONDITION_FAILED`; mail giữ nguyên |
| 57 | PROCESS_EXIT_1 | `ADB_TRANSPORT_LOST_AFTER_VERIFIED_PERSISTENT_CAPTURE` → UI XML rỗng |
| 66 | OTP_REJECTED_NO_FRESH_CODE | fix swipe chưa kịp chạy (dừng trước nhánh đó) |

## Root cause chung sau 2 run
- Phần lớn máy Gmail (34, 36, 31) **mất account trên máy** — AccountManager không có mail
  target (`pm list accounts` / `dumpsys account | grep -i "name="` → không thấy). Đây là vấn đề
  Gmail account list/session, không phải OTP. Cần re-add account hoặc live probe trước retry OTP.
- STT 54/55 mất mail (đã xóa khỏi source) — không retry được, cần nguồn mail mới.
- STT 30 cần fix selector "Thêm tài khoản"; STT 57/66 cần máy ổn định transport + fix nhánh swipe.

## Evidence paths
- Run dirs: `.runtime/Taadaa/Tiktok_Reg/artifacts/runs/recovery-new-handler/20260806-065254/`
  và `20260806-090334/` — mỗi máy có `stt_*/recovery_ledger.json` + `attempt_*/stdout.log`.
- UI dumps Gmail STT 34 (có email `truongthuy111034@gmail.com` + code `097038`):
  `ui_dumps/gmail_opened_tiktok_message_truongthuy111034_...xml` (+ `_top`, `_scrolled`).
- Backup mail die: `workbook-backups/taikhoan_dat_v2_updated _before_mail_die_audit_*.xlsx`,
  `gmail_clean_v2_before_captcha_delete_*.xlsx` (đã verify 54/55 không còn trong source lẫn tracking).
