# Quy tắc Theo dõi Hạn 7 Ngày & Đổi Info Hotmail (2026-08-21)

Tài liệu chuẩn hoá cơ chế kiểm soát tuổi tài khoản (7 ngày ngâm) trước khi đổi thông tin bảo mật, quy tắc ghi nhận biến động dữ liệu, cơ chế Chrome Web vs Outlook App, và tra cứu lịch sử tài khoản trên farm.

---

## 1. Cơ chế Kiểm soát 7 Ngày Ngâm (`MIN_LOGIN_AGE_DAYS = 7`)

- **Nguồn ngày nạp:** Cột 7 (`ngày tạo`) hoặc Cột 8 (`mã phục hồi` / fallback alias `created`) trong `D:\OneDrive\TaadaaData\kibe\gmail_clean_v2.xlsx`.
- **Cách tính:** `age_days = date.today() - created_date`.
- **Cổng phân loại (`flows/hotmail_change_info.py`):**
  - `age_days < 7`: Đánh dấu `LOGIN_TOO_RECENT` -> Từ chối can thiệp để tránh bị Microsoft checkpoint.
  - `age_days >= 7`: Đạt điều kiện (`eligible = True`), cho phép chạy quy trình đổi pass + logout thiết bị + gắn mail khôi phục.
  - `created_date is None`: Đánh dấu `LOGIN_DATE_MISSING_OR_INVALID` -> Đã được backfill về `2026-07-01` theo chỉ đạo của user.

---

## 2. Kiến trúc Change Info: Chrome Web vs Outlook App

- **Bản chất kỹ thuật:** Microsoft quy định các tác vụ quản trị tài khoản cấp cao (đổi mật khẩu, đăng xuất mọi nơi "Sign out everywhere", gắn/xóa mail khôi phục) **bắt buộc phải thao tác qua cổng Web của Microsoft** (`https://account.microsoft.com/security` / `https://account.live.com/password/Change`).
- **Ứng dụng Outlook trên điện thoại** chỉ là Email Client (giao diện đọc/gửi thư), không chứa các menu cấu hình bảo mật tài khoản Microsoft.
- **Quy trình chuẩn trên Farm:**
  1. Script `flows/hotmail_change_info.py` và `flows/hotmail_security.py` mở **Google Chrome trên máy điện thoại Android** (chạy dưới IP proxy riêng của máy đó).
  2. Thực hiện đăng nhập -> Đổi mật khẩu mới -> Bấm "Sign out everywhere" -> Gắn mail khôi phục `thanhdatbui1995@gmail.com` (và đọc OTP xác minh).
  3. Ghi đè mật khẩu mới vào `gmail_clean_v2.xlsx` (Cột 3), xóa Token cũ (Cột 9).
  4. Đăng nhập lại mật khẩu mới vào **App Outlook** trên máy farm để giữ trạng thái Inbox sống.

---

## 3. Quy tắc Đánh dấu Đã Đổi Info (Tránh đổi lặp)

Khi một tài khoản Hotmail thực hiện đổi thông tin thành công:
1. **Ghi đè Pass mới:** Cập nhật mật khẩu mới vào **Cột 3 (`pass mail`)** của `gmail_clean_v2.xlsx` và tạo file snapshot backup `.backup_before_password_update_machine_XX_...`.
2. **Gắn Mail khôi phục:** Cập nhật `thanhdatbui1995@gmail.com` vào **Cột 5 (`mail khôi phục`)**.
3. **Vô hiệu hoá Token:** Token OAuth2 cũ của shop chết ngay khi đổi pass -> Làm trống/xóa giá trị ở **Cột 9 (`token`)** để chuyển hẳn sang chế độ bảo mật hoàn toàn, tránh script gọi token cũ.
4. **Không cần tạo Token mới:** Token chỉ có giá trị phục vụ Reg TikTok siêu tốc qua Graph API trong 7 ngày đầu. Khi đã đổi pass và có TikTok, tài khoản đã nằm sẵn trong app Outlook trên máy farm để nhận mã khi cần.
5. **Bằng chứng Artifact:** Lưu snapshot kết quả tại `.ai-runs/hotmail-change-info/.../result.json` với `password_changed: true` và `status: SUCCESS`.

---

## 4. Phân loại Toàn bộ 57 Hotmail trong Kho (Tính đến 21/08/2026)

- **🟢 Nhóm 1 (Đã đủ điều kiện >= 7 ngày):** 4 tài khoản ngâm từ 21/07/2026 (31 ngày, có artifact verified trong `.ai-runs`):
  - Row 112 (Máy 30): `susannemortimerabby9@hotmail.com` (Pass: `C@V1f8Q8dlPL%Ea1wQ`)
  - Row 113 (Máy 30): `krystalsophroniaadonis7@hotmail.com` (Pass: `JOHz3w7526`)
  - Row 142 (Máy 38): `florencenaomierayven6@hotmail.com` (Pass: `qAd7Cr7861`)
  - Row 196 (Máy 54): `eulaliaphilomenaclementina7@hotmail.com` (Pass: `sOWjyO6488`)

- **🟡 Nhóm 2 (Đã nạp lâu từ T2–T6/2026, ngâm 60–180 ngày):** 22 tài khoản trên các máy 1, 3, 5, 8, 9, 13, 15, 19, 24, 27, 31, 35, 40, 42, 60, 61, 64, 66, 68.

- **🟠 Nhóm 3 (Mới nạp trong Tháng 8/2026 — Đang chờ đủ 7 ngày):** 26 tài khoản (nạp từ 16/08 đến 21/08).

- **🔵 Nhóm 4 (5 tài khoản thiếu ngày đã backfill `2026-07-01` ngày 21/08):**
  - Row 16 (Máy 04): `BronsonTrussel163815@hotmail.com` (Pass: `iclfks199129`)
  - Row 126 (Máy 34): `yobifqtxkbhpzmxf@hotmail.com` (Trống pass)
  - Row 141 (Máy 38): `augustusdanteamathyst7@hotmail.com` (Pass: `JsiGUx3600`)
  - Row 200 (Máy 56): `bajuriyanong@hotmail.com` (Pass: `mQbCac56`)
  - Row 206 (Máy 57): `DerekMudryk198575@hotmail.com` (Pass: `qtkxxf426684`)

---

## 5. Khóa thiết bị khi chạy Change Info
- Sử dụng `automation_core.device_lock.acquire_device_lock`:
  ```python
  acquire_device_lock(
      machine=m,
      serial=s,
      project='hotmail-change-info',
      command='change-info',
      user_authorized=True,
      allow_takeover=True,
      takeover_scope=FULL_SCOPE_TAKEOVER,
      takeover_authorized=True,
      takeover_reason='user authorized change info',
      bypass_proxy_readiness=True,
  )
  ```
