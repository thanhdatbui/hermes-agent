# gmail-health check: 2 bugs đã fix + CAPTCHA detection + manual signup flow (2026-08-21)

Session: máy 42 (`tanglam2811200242@gmail.com`) OTP không bao giờ về; máy 78 (`DebiDenbesten20198@hotmail.com`) đăng ký tay hoàn chỉnh.

## Vì sao gmail-health KHÔNG BAO GIỜ chạy được trước đây (2 bug, đã fix trong social_reg_v1.py)

1. **`node_has_target` chặn resource-id dài >50 ký tự**: điều kiện `len(v) <= 50` trong
   `node_has_target(attrs, targets)` khiến resource-id `com.google.android.gm:id/selected_account_disc_gmail`
   (52 ký tự) không bao giờ match → `find_node_in_xml(…, "selected_account_disc_gmail")` trả None →
   `_tap_gmail_avatar_for_health_check` luôn thất bại → health check thoát `gmail_avatar_not_found`
   (elapsed ~3s) mà chưa kiểm tra gì. **Fix: bỏ hẳn giới hạn `len(v) <= 50`** (substring match thuần).

2. **`_continue_google_relogin_for_captcha_check` tap nhầm email text không clickable**: hàm tìm node
   chứa text email rồi tap như "chọn tài khoản" — nhưng trên màn "Xác minh danh tính của bạn" đó là
   text hiển thị (clickable=false) → tap vô ích → vòng lặp sau thấy bounds y hệt → `google_signin_stalled`
   → dừng fail-closed sai nguyên nhân (không bao giờ đi tiếp sang màn nhập pass/CAPTCHA).
   **Fix: chỉ tap khi `target_account["clickable"]` là True**, còn không thì fallthrough sang nhánh
   continuation/manual-blocker.

## Sau fix — flow phát hiện CAPTCHA thật (máy 42)

- Màn Google: "Xác minh danh tính của bạn — Để bảo mật tài khoản, Google cần xác minh danh tính.
  Vui lòng đăng nhập lại" → script tap "TIẾP THEO" → màn kế tiếp:
  **"Xác nhận bạn không phải là rô-bốt" / reCAPTCHA / "Tôi không phải là người máy"**
  (`recaptcha` marker → `_is_google_captcha_xml` → `captcha_detected=True`).
- Gmail-health detect CAPTCHA → fail-closed đúng thiết kế: KHÔNG giải reCAPTCHA, KHÔNG nhập pass
  Google → script xóa email khỏi source (có backup) + append `MAIL_DIE_GOOGLE_RELOGIN_REQUIRED`
  vào sheet "Audit Pending" của tracking workbook.
- Phân biệt: thông báo "Gmail: N thư mới" vẫn về = mail SỐNG, chỉ bị Google chặn re-login/CAPTCHA —
  không phải dead account.

## Stale-OTP waterfall (chưa fix — cần xử lý tiếp)

Triệu chứng: script luôn tìm thấy code CŨ trong conversation Gmail đang mở sẵn
(`Code from recent already-open TikTok conversation: 740813 timestamp='05:50'`) → `code` không None →
KHÔNG bao giờ rơi vào nhánh `if not code:` → health check không chạy → nhập code hết hạn liên tục
(TikTok báo "Mã xác minh email đã hết hạn" sau Enter).
**Cần**: detect "đã hết hạn" trên màn TikTok → đóng conversation cũ + pull-refresh → chỉ khi vẫn
không có code mới mới chạy health check.

## Manual signup hoàn chỉnh (khi script bỏ lỡ bước — máy 78)

1. Màn đăng nhập báo **"Tài khoản không tồn tại"** → email CHƯA có TikTok → tap **"Tạo tài khoản mới"**.
2. Form email (tab Email, email đã điền sẵn) → **Tiếp tục** → "Kiểm tra email của bạn" → TikTok gửi OTP.
3. Đọc OTP hotmail trực tiếp qua Graph (KHI Outlook app kẹt consent — xem dưới):
   `read_tiktok_otp_from_graph_token(device, email, stt=N, timeout=150)` (import từ `hotmail_provider`).
   Gọi trực tiếp từ Python: `from hotmail_provider import read_tiktok_otp_from_graph_token`.
4. Nhập OTP (adb text), Enter.
5. **DOB picker calibration** (S7 1080x1920): day/month/year columns x≈240/540/840, band y 1149–1546;
   nút kết quả `id/kud` (132,846–984,990). Swipe nhanh `duration=100` ≈ 15+ năm/đợt nhiều lần,
   swipe chậm `duration=300` ≈ 3 năm/lần → dò từng bước; kiểm tra dòng "21 tháng 8, 2006" mỗi lần.
   Đến năm mục tiêu → **Tiếp tục** → dialog "Xem lại ngày sinh / OK" → OK.
6. **Tạo mật khẩu**: ô pass `(138,456)–(762,516)`, yêu cầu ≥8 ký tự + chữ + số + ký tự đặc biệt
   (`# ? ! @`). adb `input text` mất ký tự đặc biệt — nhập ~11 ký tự (vd `G9#kP7qW2!x`), xóa sạch
   bằng keyevent 67 × N trước khi nhập lại. Nút Tiếp tục (96,855–984,1011).
7. "Tạo biệt danh" → **Bỏ qua** (24,72–228,228) → vào màn chính.
8. Profile tab → "Thêm tên" → nhập tên → Lưu → dialog "Đặt biệt danh? Xác nhận/Hủy" → Xác nhận (541,1104).
9. Chạy lại `social_reg_v1.py <stt> --resume --email <mail> --ss` để script tự ensure name +
   ghi tracking (empty row re-read + backup + saved row). Xóa lock `*.lock.json` trước khi chạy lại.

## Outlook "Inapp UnifiedConsent" (máy 78) — bẫy

Mở Outlook app → dính màn consent Microsoft (landscape 1920x1080, nút OK, webview "Ghi chú nhanh về
tài khoản Microsoft"). Tap OK/scroll không qua được, Back không thoát. **→ Force-stop Outlook
(`am force-stop com.microsoft.office.outlook`) và dùng đường Graph token thay thế** — script
`[otp-graph]` tự chọn Graph trước Outlook. Notification "Chọn bàn phím" (Chọn bàn phím) treo trên
status bar = IME picker từng hiện — dismiss bằng Back trong script.

## PITFALL: patch tool làm hỏng indent Python

`patch(mode=replace)` với block nhiều dòng bị fuzzy-match → sinh IndentationError (3 lần trong session).
**Quy trình an toàn**: (a) patch 1–2 dòng đơn; hoặc (b) dùng python heredoc sửa theo line-index:
```bash
python - <<'EOF'
path = r'...social_reg_v1.py'
lines = open(path, encoding='utf-8').readlines()
# unindent 4 spaces cho dòng 5143–5157 (0-based 5142–5156)
for i in range(5142, 5156):
    if lines[i].startswith('    '):
        lines[i] = lines[i][4:]
open(path, 'w', encoding='utf-8').writelines(lines)
EOF
```
Luôn verify `python -m py_compile social_reg_v1.py` sau mỗi sửa.