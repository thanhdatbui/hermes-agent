# Magic-link transition verification — STT30 live attempts (2026-08-11)

Chuỗi 2 attempt live cuối của STT30 (serial `ce0217126cd4bc640c`, email hotmail redacted)
sau khi nhánh Outlook magic-link đã tap được link thật. Đây là các root cause cuối cùng
khiến flow "tưởng success nhưng chưa verify" — khác hẳn các bug trước (IME che, anchor
ngoài viewport, forward bị remove sớm) đã được fix trong cùng ngày.

## Triệu chứng (2 attempt giống hệt nhau, 19:48 và 20:05)

```
[otp-magiclink] CDP anchor href=.../email_verification?... rect_css=[33,545,293,44] dpr=3
[otp-magiclink] MAGIC_LINK verified transition -> return MAGIC_LINK   ← SAI: chỉ vì TikTok foreground
✓ Magic link đã tap → TikTok sẽ tự xử lý
[8b] Handle post-auth screens → Unknown screen → dừng vòng lặp
[9] Wait for login success
✓ Thanh cong: <email> | hint='Kiểm tra hộp thư của bạn'               ← FALSE POSITIVE
[10] Ensure profile name + tracking → [02_profile] Khong vao duoc tab Ho so/Profile → STOPPED
[final] focus=SignUpOrLoginActivity
```

Sau tap link: TikTok foreground NHƯNG vẫn ở màn "Kiểm tra hộp thư của bạn" — email
chưa được TikTok xác nhận.

## Root cause 1 — foreground ≠ verified

- `_verify_visual_magic_link_transition` chỉ check `APP_PACKAGE in _xml_packages(after_xml)`
  hoặc open-with dialog → deep-link mở app lên màn CŨ = "verified" sai.
- Nhánh Outlook `_read_outlook_magic_link_with_evidence` trả `"MAGIC_LINK"` NGAY sau đó,
  KHÔNG chờ state đổi — trong khi Gmail path có `_return_to_tiktok_after_magic_link`
  (chờ 60s tới khi state ∈ {success, registration_entry, password_required} hoặc
  `_is_tiktok_signup_transition_xml`).
- Fix: sau tap gọi `_return_to_tiktok_after_magic_link(device_id, timeout=90)`. Chỉ khi
  hàm này trả về (không raise `MAGIC_LINK_TIKTOK_RETURN_UNVERIFIED`) mới return
  "MAGIC_LINK"; nếu raise/timeout → return None → caller fail closed
  `OUTLOOK_MAGIC_LINK_ACTION_NOT_VERIFIED`.

## Root cause 2 — success_hints "Hộp thư" false positive trong `_wait_login_success`

- `success_hints` chứa `"Hộp thư"/"Hop thu"` (cùng "Trang chủ", "Bạn bè", "Hồ sơ", "Đề xuất"...).
- Màn magic-link "Kiểm tra hộp thư của bạn" chứa text "hộp thư" → `find_node_in_xml`
  match → log `✓ Thanh cong ... hint='Kiểm tra hộp thư của bạn'` → return True.
- Fix: xóa `"Hộp thư"/"Hop thu"` khỏi success_hints + guard: flat chứa
  `kiem tra hop thu` / `gui lai email` / `gui lai ma` → continue chờ (không bao giờ success).

## Root cause 3 — magic link hết hạn (~20 phút)

- Mail TikTok được gửi 17:57 (3 lần resend spam từ bug cũ), tap lúc 19:48 → link EXPIRED.
- TikTok nhận deep-link nhưng không xác nhận → vẫn màn "Kiểm tra hộp thư".
- Fix vận hành: khi máy nằm lâu ở màn magic-link, bấm **"Gửi lại email"** trên màn TikTok
  (log: coord ~(540,1687), rid `com.ss.android.ugc.trill:id/tkn`) → chờ mail mới ~1 phút →
  resume ngay (link mới còn hạn).
- Phân biệt: nếu CDP probe OK + tap OK + TikTok foreground nhưng vẫn màn chờ → khả năng
  cao là expiry, không phải bug tap — resend rồi retry trước khi sửa code.

## Root cause 4 — resume từ sai màn → nhánh numeric OTP

- Resume chỉ nhận diện magic-link khi TikTok foreground màn magic-link.
- Máy đang ở Chrome (mail mở) mà resume: `[resume-dbg] package=other kiem_tra_email=N`
  → `prefer_magic_link=False` → `[7c]` chạy `_try_get_otp_outlook_cdp` (numeric reader)
  → `[otp-enter] Quay lại TikTok, nhập OTP` → `OTP screen unavailable` → STOPPED.
- Đưa TikTok lên foreground TRƯỚC khi resume:
  - `am start -a android.intent.action.MAIN -c android.intent.category.LAUNCHER -p com.ss.android.ugc.trill`
    → FAIL "unable to resolve Intent" (activity không export).
  - Đúng: `monkey -p com.ss.android.ugc.trill -c android.intent.category.LAUNCHER 1`
    → verify `mResumedActivity` = `SignUpOrLoginActivity` → mới resume.

## Checklist trước khi live lại (sau fix 2 lỗi code)

1. TikTok foreground ở `SignUpOrLoginActivity` (màn magic-link) — monkey + dumpsys.
2. Mail TikTok MỚI (resend < ~15 phút) — nếu không, tap "Gửi lại email" (540,1687) trước.
3. Lock sạch: `machine_30.lock.json` + `serial_<serial>.lock.json` — PID chết mới rm.
4. Chạy: `SOCIAL_PREFERRED_EMAIL=<email> python -u social_reg_v1.py 30 --ss --defer-tracking-write --resume`.
5. Đọc kết quả: log phải có `[7c] MAGIC_LINK TikTok transition verified` (state đổi thật)
   hoặc `[9] ✓ Thanh cong ... hint='Hồ sơ'/'Đề xuất'` (không phải "Kiểm tra hộp thư").
