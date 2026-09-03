# Reg session 2026-08-16 — email-icon bounds, fallback, DOB/OTP race

Batch: 4 hotmail máy 38/54/57/66 (sau khi login Outlook app xong hết).
Kết quả: 38 ✅ (augustusdant7), 54 ✅, 57 ✅ (derekbwpt78), 66 ⏳ kẹt QuickNote variant.

## 1. `[06_email_option]` — email icon bounds SAI trên layout mới (máy 57/66)

Symptom: `[06_email_option] Không tìm thấy: Email / icon email` — màn
`I18nSignUpActivity` (signup v2) hiển thị form SĐT (`+84`/`Số điện thoại`) +
3 icon đăng nhập nhanh KHÔNG text, không có tab "Email/tên người dùng".

Root cause: code cũ tìm icon email trong vùng **y 1540-1800** (ước lượng từ
layout Samsung keyboard cũ) — nhưng hàng icon thật nằm ở **y 873-1017**
(máy 57 XML thật: clickable views `[169,873][313,1017]`, `[337,873][481,1017]`,
`[511,873][905,1017]`; nút "Tạo tài khoản" nằm trong icon 3). Icon trái nhất
= email → center **(241, 945)**.

Fix đã code (`social_reg_v1.py`, nhánh layout mới):
1. **Hardcode mới**: `800 <= cy <= 1100 and cx <= 350 and (x2-x1)>=100 and (y2-y1)>=100` → tap.
2. **Fallback dynamic (resolution/build-agnostic)**: tìm EditText (class ends
   `.EditText`) → `phone_top = center_y`; rồi mọi clickable view vuông ≥100x100
   với `y1 > phone_top` → `email_icon = min(candidates, key=(cy, cx))` (trái nhất,
   trên cùng). Log `→ fallback dynamic: icon email <coord>`.

Verified: tap (241,945) trên máy 57 → `email form: True` → reg chạy tiếp ✅.

## 2. DOB/OTP race (máy 38) — OTP dính vào field ngày sinh

Symptom: OTP đã nhập xong + Enter, TikTok lập tức chuyển sang màn
"Ngày sinh của bạn là ngày nào?" — script vẫn còn type OTP → `712503` dính
vào date-picker field (ảnh thấy rõ số OTP trong ô ngày sinh).

Fix direction: sau OTP-entry + Enter, **re-check màn trước khi type tiếp**;
nếu birthday screen (`ngay sinh`/`birthday` markers) → dừng type, gọi
`fill_birthday(device_id, dob_str, stt=...)`. DOB workbook trống (máy 38
augustus = None) → `fill_birthday` fallback **01/01/1999** vẫn chạy được.
Sau `fill_birthday` → post-tap `screen=password` → tiếp tục
`fill_password_and_login` + `handle_post_auth_screens` + `wait_login_success`.

## 3. Resume từ màn giữa flow (KHÔNG restart)

Máy 38 kẹt màn password TikTok sau DOB → `social_reg_v1.py 38 --resume
--email augustusdanteamathyst7@hotmail.com --ss` → **SUCCESS** (row 301,
Tik=300, ID=augustusdant7). Resume chạy đúng bước còn lại, không phá state.

## 4. QuickNote VARIANT (máy 66) — ĐÃ FIX XONG

`OUTLOOK_APP_INBOX_NOT_REACHED_FROM_ARCHIVE` khi reader mở Outlook app: màn
privacy dialog 3 mục ("Những nội dung quan trọng của bạn ở ngay đây" /
"Quyền riêng tư của bạn là ưu tiên hàng đầu" / "Bạn đang nắm quyền kiểm soát")
+ nút OK xanh — **KHÔNG có tiêu đề "Ghi chú nhanh"** nên
`_outlook_app_quick_note_visible` (title-based) miss.

**Fix đã land** (`flows/hotmail_login.py`): detect khi ≥2/3 marker chuẩn hóa có
mặt — marker PHẢI giữ chữ **`đ`**: `"nhung noi dung quan trong cua ban o ngay
đay"`, `"quyen rieng tu cua ban la uu tien hang đau cua chung toi"`, `"ban đang
nam quyen kiem soat"`. ⚠️ `normalize_text` (NFD) strip dấu nhưng KHÔNG đổi
`đ`→`d` (đ không có combining char) — viết `"ngay day"` sẽ không bao giờ match
`"ngay đay"`. Xử lý: swipe down (`input swipe 540 1200 540 400 400`) rồi tap OK
(fallback `(539,1703)`; máy 66 tap thật `(540,1705)` ăn). 2 regression test:
`test_quick_note_variant_b_privacy_bullets` (True) +
`test_quick_note_variant_b_needs_two_markers` (1 bullet = False).

Kết quả máy 66: tap OK → `folder: True` CentralActivity → reg chạy lại lần 2
đang chạy (proc reg_66_v2).

## Notes

- Rotation guard: `accelerometer_rotation 0` + `user_rotation 0` +
  `wm user-rotation lock 0` trước mọi run; verify bằng `settings get` +
  PIL size (phải portrait 1080x1920). `prepare_device(lock_rotation=True)`
  có thể bật lại accel=1 trên Samsung — runner phải re-assert.
- ADB daemon chết khi chạy `wm user-rotation lock` → `adb devices` rớt serial;
  chờ và re-query, đừng kết luận máy mất.
- `run_adb` mock: `c.args[2]=="input"`, slice `c.args[4:]` mới lấy tọa độ tap.
