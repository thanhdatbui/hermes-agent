# "Mật khẩu sai" khi login TikTok bằng pass source — email ĐÃ CÓ nick TikTok (2026-08-21)

## Triệu chứng (máy 2 — `lieuhoan1210200302@gmail.com`)

- Flow reg chạy tới màn OTP: "Mã xác minh email đã hết hạn" lặp đi lặp lại (code cũ `954753`),
  bấm Gửi lại mã nhưng thư mới không về (hoặc về mà script đọc nhầm code cũ).
- Thử hướng **"Đăng nhập bằng mật khẩu"** với pass từ source workbook → TikTok báo exact
  **"Mật khẩu sai"**.
- Kết luận: email này **đã đăng ký TikTok từ trước** với một pass KHÁC (không phải pass trong
  gmail_clean_v2 / source) — đây là email cũ lẫn vào danh sách target, không phải mail mới để reg.

## Xử lý ĐÚNG (fail-closed)

- KHÔNG tự đoán/đổi pass — nhập sai nhiều lần có thể khóa/flag nick (OTP bị giới hạn rate).
- KHÔNG xóa email khỏi source khi chưa confirm (đây không phải mail chết — nick tồn tại thật,
  "Mật khẩu sai" là bằng chứng nick sống).
- Screencap + báo user: email đã có nick TikTok cũ, cần user quyết định (giữ nguyên hiện trường
  máy, lock, không reg tiếp bằng mail đó).
- Nếu cần xác minh thêm: search tracking workbook cũ (`taikhoan_dat_v2_updated .xlsx`) theo email
  xem có nickname nào ứng với mail này không.

## Phân biệt 3 trường hợp kẹt OTP

| Triệu chứng | Kết luận | Hành động |
|---|---|---|
| "Mã xác minh email đã hết hạn" + pass source sai | Nick TikTok ĐÃ TỒN TẠI (pass khác) | Báo user, không đoán pass |
| Gmail-health → "Xác nhận bạn không phải là rô-bốt" (reCAPTCHA) | Google CAPTCHA — mail chặn re-login | Script tự remove source + Audit Pending (fail-closed) |
| Gmail-health → forced re-login KHÔNG captcha | Google re-login (session OAuth chết) | Cần nhập lại pass Google tay 1 lần rồi chạy lại reg |

## Nguồn: session 2026-08-21, máy 2 & 42