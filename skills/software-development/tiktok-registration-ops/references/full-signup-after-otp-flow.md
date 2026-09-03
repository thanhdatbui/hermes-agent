# Full signup flow after OTP — machine 57 (2026-08-14)

Verified live on máy 57 (`ce11160b54ee2f3403`, email `DerekMudryk198575@hotmail.com`,
branch `reg-stable-0722` commit `09e3d1d`). Flow: email → OTP (Outlook app) → "Tạo mật khẩu"
→ "Tạo tên" → home feed → profile `@derekbwpt78` → tracking row 453 written automatically.

## Screen progression (after email submit, signup mode)

1. **OTP screen** — "Nhập mã" + "Sử dụng liên kết này **hoặc nhập mã** được gửi đến <email>"
   + 6 EditText OTP + "Gửi lại mã" + countdown `54s`. User confirmed (2026-08-14): in SIGNUP flow
   this is the **registration OTP screen** (email chưa reg) — NOT `REGISTERED_LOGIN_DEFERRED`.
   OTP đúng → TikTok chuyển tiếp; OTP sai → lỗi, không tiến.
2. **"Tạo mật khẩu"** (create password) — requirements: 8–20 chars, 1 letter + 1 digit +
   1 special (`# ? ! @`); live checkmarks + "Mật khẩu mạnh" when satisfied. Nút `Tiếp tục`
   `enabled="false"` until password valid.
   - **Pitfall: password `$`/`*` bị shell nuốt** — `type_into_node` mặc định `sensitive=False`
     → `input_text` → bash expands `$7` → field thiếu ký tự → nút disabled mãi.
     Fix committed: call `type_into_node(..., sensitive=True)` (AdbKeyboard IME + base64 broadcast)
     at every password call site. Verify: đếm dots trong field — 28 dots = 14 chars OK, 13 = thiếu.
     Nếu đã nhập thiếu: xóa field (tap → `KEYCODE_MOVE_END` → 28× `keyevent 67`) → retype sensitive.
   - **Pitfall: nút `Tiếp tục` bounds DỊCH khi keyboard đóng/mở** (y 1681 keyboard mở → 1806 sau
     `keyevent 4` ẩn keyboard). Nút có `clickable="false"` nhưng `enabled="true"` → `input tap`
     vẫn ăn khi đúng bounds. Luôn dump lại lấy bounds mới trước khi tap; keyboard mở → `keyevent 4`
     trước. Committed: `hide_keyboard()` thêm keyevent 4, `fill_password_and_login` tap
     "Tiếp tục"/fallback (540,1806) thay vì coord cũ (409,657).
3. **"Tạo tên"** (display name) — field `0/30`, nút "Tiếp tục" (bounds [96,1728][984,1884]).
   Màn này dùng "Tiếp tục" chứ KHÔNG phải "Lưu" — `fill_name` cũ tìm "Lưu"/(1050,150) sai → kẹt.
   Committed: `fill_name` thử "Lưu" trước, fallback "Tiếp tục", fallback coord (540,1806).
4. **Home feed** — `Trang chủ/Bạn bè/Hộp thư/Hồ sơ` bottom bar = login success.
5. **Profile verify** — tap tab Hồ sơ (972,1857) → dump: display name + `@username` thật +
   follower/thích = 0 → proof account MỚI (không phải success giả / account cũ).

## Auto-tracking write

`--resume` trên máy đã login (không `--defer-tracking-write`) → `wait_login_success` →
`ensure_profile_completed_and_track` → **tự ghi tracking**:
```
[login-success] success UI proof: <email>
[profile] handle=@<username> name='<name>'
[tracking] saved row <N>: Tik=<row> ID=<username> email=<email>
✅ SUCCESS: <email>
```
Backup trước khi ghi: `data/backup/taikhoan_dat_v2_updated_before_account_success_*.xlsx`.
Verify bằng đọc workbook (cột GMAIL chứa email, ID chứa @username) — không chỉ tin log.

## Key user rules encoded from this session

- **Thao tác tay qua được bước nào → patch script bước đó NGAY** (user: "handle lại" = sửa script,
  không phải bấm tay rồi bỏ). Commit + test trước khi chạy máy khác.
- Reg mà máy đang login account cũ → nhánh **Add account** là ĐÚNG THIẾT KẾ (giữ acc cũ, thêm mới),
  không logout, không nghi ngờ.
- Đọc OTP Hotmail → **app Outlook** (đã login sẵn) thay vì Chrome. Activity lấy từ
  `cmd package resolve-activity --brief com.microsoft.office.outlook` (`.MainActivity`,
  đừng đoán `.activities.MainActivity` → `Error type 3`). Wire: non-Gmail → app trước,
  `_try_get_otp_browser` (Chrome) chỉ fallback cuối.
- No auto-lock (user 2026-08-14): lock chỉ khi `DEVICE_LOCK_ENABLED=1`; gặp lock active
  (PID sống) → dừng + báo user. Khi lock tắt phải tự check process trùng trước khi chạy.
