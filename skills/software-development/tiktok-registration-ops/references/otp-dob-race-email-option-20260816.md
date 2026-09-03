# OTP→DOB race + [06_email_option] layout (live 2026-08-16, batch 4 hotmail)

Session: login 4 hotmail vào Outlook app (38/54/57/66) xong → chạy TikTok reg
`_run_all_targets.py --full-scope-takeover`. Kết quả: **54 SUCCESS**, còn
**38 FAILED_EXIT_2, 57/66 FAILED_EXIT_1**. Đây là 2 blocker riêng biệt cần
handle tiếp trong `social_reg_v1.py` (chưa xong cuối session — user đang hướng dẫn).

## Blocker 1 — Máy 38: OTP bị nhập nhầm vào field ngày sinh (timing race)

Symptom (log + screenshot `38_09_result_145335.png`):
```
[otp-enter] no confirm button -> sent Enter
✓ Email verification code entered (login-success fallback)
✗ Timeout chờ login success
```
Ảnh cho thấy màn **"Ngày sinh của bạn là ngày nào?"** (bước 7d birthday) với
chuỗi OTP (vd `712503`) bị dính vào **date picker field** — tức OTP type đúng
xong, TikTok chuyển sang màn birthday RẤT NHANH, và script (hoặc type tiếp /
hoặc `handle_tiktok_email_otp` verify sau đó) làm text OTP rơi vào ô ngày sinh.

Root cause: flow 7c (`handle_tiktok_email_otp`) → `time.sleep(D_LONG)` →
7d check `["ngay sinh", "birthday", ...]` → `fill_birthday`. Giữa OTP submit và
7d-check, màn đổi nên text nhập bị lệch field. Cần:
- Trước khi type OTP (và sau mỗi Enter), re-check màn có phải OTP screen
  (`otp_screen_hints`) — nếu đã thành "ngay sinh" thì DỪNG type, chuyển thẳng 7d.
- Nếu OTP digits xuất hiện trong ô ngày sinh → xóa (select-all + DEL) rồi
  `fill_birthday(device_id, found_dob, stt)` — đừng để date picker sai.
- `fill_birthday` đã tồn tại (social_reg_v1.py:3266) — vấn đề chỉ là timing gate
  trước nó, không phải thiếu handler.

## Blocker 2 — Máy 57/66: `[06_email_option]` không tìm thấy Email/Username

Log:
```
→ thử tap trực tiếp Email/Username
✗ Không thấy: ('BỎ QUA', 'Bỏ qua', 'SKIP', 'Skip')
✗ Không thấy: ('Email/tên người dùng', ... 'Email')
✗ STOPPED: [06_email_option] Không tìm thấy: Email / icon email
```
XML fail (`fail_06_email_option_144355.xml`): chỉ có `Số điện thoại`, `+84`,
`VN`, `Đăng nhập`, `Tạo tài khoản` — màn I18nSignUpActivity **không expose tab
email** (khác layout đã fix trước đó cho máy 38/57: "Nhập địa chỉ email" +
field + "Tiếp tục" + domain chips @gmail/@outlook/@hotmail).

Chưa có lời giải cuối session (user đang chỉ). Hướng kiểm tra:
- Có thể màn này là **màn đăng ký SĐT** và cần chuyển tab/tìm link
  "Đăng ký bằng email" / "Dùng email" — hoặc Back về màn chọn phương thức.
- So sánh `fail_06_email_option_093639.xml` (layout mới ĐÃ fix được — domain
  chips) vs `fail_06_email_option_144355.xml` (layout này KHÔNG có chips) —
  có thể cùng activity nhưng 2 nhánh entry khác nhau (signup vs login).
- Gửi ảnh cho user khi gặp lại — user nhìn 1 phát ra hướng đúng.

## Ghi chú batch

- Reg 4 máy chạy **song song bình thường** (chỉ hotmail login/add-mail là tuần tự) —
  `_run_all_targets.py` tự song song, kết quả từng STT độc lập.
- Batch artifacts: `/d/Taadaa/runtime/kibe/artifacts/runs/social-batch-all/<ts>/batch_1/stt_<n>/stdout.log`
- Ảnh fail: `D:\Taadaa\Tiktok_Reg\screenshots_social/<stt>_09_result_<ts>.png`
- UI dumps: `D:\Taadaa\runtime\kibe\artifacts\ui_dumps\fail_06_email_option_<ts>.xml`
