# ATX SIGKILL + Profile instability + expected_marker design — máy 34, 2026-08-07

Session detail for the `tiktok-login-reconcile` skill. Máy 34 = SM-G930K,
TikTok 46.x, reg/login `truongthuy111034@gmail.com` (Tik 266) trên profile
đang login `@yobi1965`.

## Chuỗi sự kiện (thứ tự fix)

1. **uiautomator treo vô hạn** — atx-agent PID treo `futex_wait_queue_me`
   (S-state), `uiautomator dump` E=137 ("Terminated"), runner kẹt transport
   recovery loop. Core `_recover_uiautomator` dùng `pkill -f` (SIGTERM) →
   atx không chết.
2. **Root cause**: SIGTERM không ăn process treo futex. Fix: `pkill -9 -f`
   (SIGKILL). Live test 3/3: `pkill -9 -f atx-agent` + `am force-stop
   com.github.uiautomator` → dump E=0. Core 0.4.43 (`a57ab2b`), test
   `test_ui_dump.py` cập nhật kỳ vọng `["pkill", "-9", "-f", ...]`.
3. **expected_marker design bug**: adapter `dump_ui(expected_marker="hồ sơ")`
   — tab "Hồ sơ" có trên MỌI màn (kể cả feed) → dump feed vẫn pass → core
   nhận feed → `SWITCHER_ANCHOR_AMBIGUOUS`. Fix: marker = display_name
   (`extract_profile_identity` → "yobi"), rỗng thì bỏ marker.
4. **Classifier feed-vs-profile** — commit `86c122d` (xem SKILL.md section).
5. **Run 182529 THẮNG**: profile → dropdown verified → "Thêm tài khoản"
   (540,1788, desc 'Th?m t?i kho?n', rid l_z) → tab Email (540,596) →
   nhập email → tap login → Gmail inbox đúng acc → fast-path code 14:54
   (mail CŨ) → nhập OTP → OTP screen biến mất → FINAL_BLOCKED
   `[otp-enter] TikTok OTP screen unavailable after Recents recovery`.
6. **Orphan lock self-block**: runner sau đó fail 39s `DEVICE_LOCKED` với log
   rỗng. Lock `machine_34.lock.json` pid 46076 + `serial_ce031603b3158b0b02.
   lock.json` pid 43652 — cả 2 pid đã chết (wmic trả rỗng; tasklist có thể
   silent-fail nên dùng wmic). `rm -f` cả 2 → chạy được.
7. **Profile instability**: run 184028 tap profile → "profile selected" (log)
   nhưng dump fail = feed (không username) → SWITCHER_ANCHOR_AMBIGUOUS lần
   nữa. TikTok chạy lâu trên máy 3GB RAM → tap profile → splash → feed loop.
   Cần reboot (fresh TikTok) trước retry — thành công 182529 nhờ vừa reboot.

## Coordinates live-proven máy 34 (SM-G930K, 1080x1920)

- Profile tab bottom: (972, 1857), desc 'H? s?', rid `com.ss.android.ugc.trill:id/o3i`
- Tên user "yobi" header: [435,117][645,183] → tap (540,150) mở dropdown
- "Thêm tài khoản": [252,1758][614,1818] → tap (540,1788), desc 'Th?m t?i kho?n', rid l_z
- Tab Email trên màn login: (540,596) text 'Email ho?c TikTok ID'

## Audit wrapper fails (cùng ngày)

| Wrapper | Lỗi | Workaround |
|---|---|---|
| invoke-gemini-9router-audit.ps1 | exit 23, 9router 400 "Invalid JSON body", context_files rỗng | bỏ ContextPath hoặc cấu đúng context; theo ladder → next |
| invoke-opencode-audit.ps1 | exit 1 OPENCODE_AUDIT_FAILED_NON_QUOTA (nemotron→ling cascade) | theo ladder → next |
| invoke-command-code-9router-audit.ps1 | `#requires -Version 7.0` — pwsh trên PATH có thể là 5.1 | verify `$PSVersionTable` hoặc dùng `C:\Program Files\PowerShell\7\pwsh.exe` |
| Fallback cuối | Codex reviewer độc lập (fresh, read-only, verdict APPROVED/MINOR_FIXES/REJECT) | theo AGENTS.md ladder |

## Lessons class-level

- **SIGKILL > SIGTERM cho process Android treo** (atx-agent futex) — pkill -9.
- **expected_marker phải đặc trưng màn** — tab label chung = vô dụng.
- **"profile selected" log ≠ profile thật** — verify dump có username; nếu
  dump fail không username → chưa vào profile → reboot.
- **Orphan device-lock**: runner tự chặn lock cũ — dọn cả machine_ + serial_
  khi pid chết (wmic verify).
- **Fast-path Gmail phải pull-refresh trước** khi đọc preview — nếu không
  đọc code cũ (timestamp cũ) → OTP sai.
