# Máy 38 2026-08-15: hardcoded email bug + reg-mới path + resume sai màn

Session tail evidence (sau khi provider đã qua được inbox gate): máy 38 `florencenaomierayven6@hotmail.com`, các fix chưa commit lúc ghi.

## 1. Bug: email HARDCODE trong `[8b]` email-confirm (social_reg_v1.py L6382)

- Dòng: `type_into_node(device_id, em_nodes[0], "bobbyxruizz0s0o@gmail.com", label="email-full", clear=True)` — hardcode thay vì `email` tham số.
- Hậu quả: resume với `--email florencen...` vẫn type `bobbyxruizz0s0o@gmail.com` vào màn xác minh → màn hiện "Sử dụng liên kết này hoặc nhập mã được gửi đến bobbyxruizz0s0o@gmail.com" → flow verify sai account → `[8b-0]`→`[8b-5]` loop 6 lần → `[9]` timeout → `PENDING` exit 2.
- Fix: `type_into_node(device_id, em_nodes[0], email, ...)` (email là tham số `handle_post_auth_screens(device_id, email, stt=None, max_rounds=6)` L6283).
- Verify: `grep -n "bobbyxruizz" social_reg_v1.py tests/` = 0. Các `*.test0X@hotmail.com` L92+ là config test accounts hợp lệ — không xóa.
- Rule chung: grep `type_into_node` và assert mọi email/password dùng BIẾN.

## 2. Màn "Tài khoản không tồn tại" + "Tạo tài khoản mới" = REG MỚI

Trình tự quan sát được (sau khi sửa email field tay từ bobbyxruizz → florencen):

1. Màn "Đăng nhập — Bạn đã đăng ký" + "Hãy nhấn vào Tiếp tục để đăng nhập..." + email field chứa email + nút "Tiếp tục" (rid `ffe`).
2. Tap "Tiếp tục" (bounds DỊCH theo keyboard: 1806 khi mở, 1681 khi đóng) → màn mới: "Tài khoản không tồn tại" + **"Tạo tài khoản mới"** (~(297,1033)) + "Tiếp tục".
3. Tap "Tạo tài khoản mới" → màn "Đăng ký" tab Điện thoại/Email + email điền sẵn + "Tiếp tục".
4. Tap "Tiếp tục" (1681) → **màn magic-link**: "Kiểm tra hộp thư của bạn — Bạn có thể đăng ký bằng liên kết được gửi đến <email>" + "Gửi lại email sau 51 giây" (cooldown từ lúc gửi).

Đây là path REG cho email chưa có account — tracking "DA CO tai khoan" cũ STALE. Email thật sự chưa reg (màn "Tài khoản không tồn tại" là proof).

## 3. Resume sai màn → `[8b]` loop

- `[resume-dbg] package=tiktok kiem_tra_email=N` = màn hiện tại KHÔNG có marker "kiem tra email" → nhánh magic-link L6842 (`kiem tra hop thu`) không fire → rơi vào `[8b]` type email loop → PENDING.
- Trước resume PHẢI verify màn đúng: texts chứa "Kiểm tra hộp thư của bạn" + "Gửi lại email". Màn "Đăng ký"/feed → xử lý tay trước.

## 4. Sửa email field tay trên TikTok

Tap field (focused=true) → `input keyevent KEYCODE_MOVE_END` → loop ~40× `input keyevent 67` → `input text '<email>'` → verify texts. Không có clear-all.

## 5. Trạng thái máy sau các attempt (evidence timeline)

- 16:03 resume14: type bobbyxruizz vào màn xác minh (bug L6382) → màn "Xác minh email... gửi đến bobbyxruizz..." 
- 16:08-16:10: sửa tay field → florencen → "Tài khoản không tồn tại" → "Tạo tài khoản mới" → màn Đăng ký → tap Tiếp tục → màn magic-link florencen 16:11 (mail mới, cooldown 51s).
- 16:13 resume15: màn lúc đó KHÔNG phải magic-link (do [8b] trước đó tap làm đổi) → loop → PENDING.
- 16:17 resume16: tương tự — `kiem_tra_email=N` → loop → PENDING.
- 16:21+: màn magic-link vẫn hiện (mail 16:11 còn hiệu lực ~20 phút) — resume đúng màn mới vào provider.

## 6. Provider trả `MAGIC_LINK` NHƯNG TikTok vẫn màn "Kiểm tra hộp thư" = link HẾT HẠN (false positive)

- 16:32 provider chạy probe trực tiếp → `RESULT: MAGIC_LINK` — nhưng sau đó TikTok VẪN ở màn
  "Kiểm tra hộp thư của bạn" (mResumedActivity = SignUpOrLoginActivity, texts không đổi).
- Nguyên nhân: provider tap link mail **16:11** (giờ 16:32 = 21 phút → hết hạn ~20 phút).
  TikTok nhận deep-link nhưng TỪ CHỐI (expired) → vẫn màn magic-link. Provider trả MAGIC_LINK
  vì `after` XML chứa `com.ss.android.ugc.trill` (TikTok foreground) — nhưng foreground ≠ verified.
- **Đây là false-positive còn sót trong provider**: sau tap link, chỉ check
  `"com.ss.android.ugc.trill" in after` (L1322) là TikTok foreground — KHÔNG verify màn đã đổi
  khỏi "Kiểm tra hộp thư". Màn "Kiểm tra hộp thư" vẫn là TikTok → trả MAGIC_LINK dù link expired.
- **Bài học**: `MAGIC_LINK` trả về ≠ email verified. Verify tiếp bằng UI TikTok: texts chứa
  "Kiểm tra hộp thư" / "Gửi lại email" sau khi provider trả MAGIC_LINK = link expired → resend
  ("Gửi lại email") lấy mail MỚI → provider lại (trong 20 phút). Màn ĐÃ đổi (Nhập mã 6 số /
  Tạo mật khẩu / Nhập địa chỉ email điền sẵn) = verified thật → tiếp flow.
- Cần patch provider tương lai: sau tap link, recapture check KHÔNG còn "kiem tra hop thu" mới
  trả MAGIC_LINK (mirror pitfall cũ "TikTok foreground sau tap link KHÔNG = magic-link verified").

## 7. Resend "Gửi lại email" KHÔNG tạo mail mới (kẹt cuối session)

- Tap "Gửi lại email" nhiều lần (16:33→16:41) với bounds đúng (540,1687 — lấy từ XML, nút
  `enabled=true clickable=true` màu đỏ active) → inbox Outlook vẫn chỉ có mail cũ nhất 16:11,
  KHÔNG có mail mới. Màn TikTok không hiện countdown "Gửi lại email sau X giây" trong XML.
- Khả năng: TikTok chặn resend spam (cooldown dài hơn sau nhiều lần), hoặc mail mới bị Outlook
  lọc vào tab khác/Spam, hoặc countdown hiển thị bằng view vẽ không expose trong XML.
- Chẩn đoán đúng: mở Outlook → đọc list row TikTok + time — nếu KHÔNG có mail mới hơn mail
  đang dùng → resend chưa thành công. Đừng vội provider lại.
- Hướng xử lý chưa giải quyết xong trong session: chờ cooldown dài (5-10 phút) rồi resend 1 lần,
  verify mail mới về inbox TRƯỚC khi chạy provider; hoặc user bấm tay nút trên máy 38.
