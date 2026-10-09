# Kỷ Luật Sử Dụng Runner Login Chính Thức & Cạm Bẫy Ad-hoc Login (08/09/2026)

## 1. Bối cảnh & Hiện tượng

Trong quá trình xử lý lệch tài khoản trên Máy STT 03 (đăng xuất nick trùng `miumiu67971` và đăng nhập lại nick chính `trangtran168432`), subagent đã vi phạm kỷ luật khi:
1. **Tự viết script ad-hoc (`login_m3_exec.py`)** để bấm nút và điền credential thô sơ thay vì gọi công cụ login chính thức của farm.
2. **Nhầm lẫn giữa 2FA Authenticator (TOTP) và Xác minh Email (Email OTP):**
   - Màn hình TikTok hiển thị: *"Xác minh email: Sử dụng liên kết này hoặc nhập mã được gửi đến segovkibido@hotmail.com"*.
   - Script ad-hoc nhận diện cụm từ "nhập mã" liền tự dùng thư viện `pyotp` sinh mã TOTP 6 số điền vào, dẫn đến thông báo: **"Lỗi mã xác minh email"**.
3. Người dùng bức xúc và chấn chỉnh: *"Ghi clgt. T có làm script tiktok log in r mà???"*.

---

## 2. Danh mục Công Cụ Login Chính Thức Của Farm

Farm Taadaa đã xây dựng và kiểm thử hoàn chỉnh 2 công cụ đăng nhập chuyên dụng, tích hợp đầy đủ giải 2FA TOTP, đọc OTP Hotmail/Outlook app, captcha bypass và post-auth:

| Công cụ | Repo / Đường dẫn | Khi nào sử dụng |
|---|---|---|
| **`tiktok_login_v1.py`** | `D:\Taadaa\Tiktok_Reg\tiktok_login_v1.py` | Đăng nhập đơn lẻ (`--email <id/email>`) hoặc toàn bộ tài khoản usable của một máy (`stt --all`). |
| **`reconcile_tiktok_accounts.py`** | `D:\Taadaa\tiktok-log-in\scripts\reconcile_tiktok_accounts.py` | Đối chiếu giữa Account Switcher trên máy và `taikhoan_run_safe.xlsx`, tự động đăng nhập bù tất cả nick còn thiếu. |

> **QUY TẮC CỐT LÕI:** CẤM TUYỆT ĐỐI Coordinator và Worker tự viết script Python ad-hoc để tap/type đăng nhập TikTok. Bắt buộc gọi trực tiếp 1 trong 2 công cụ trên.

---

## 3. Các Cạm Bẫy Kỹ Thuật Khi Chạy Runner Chính Thức

### Cạm bẫy 1: Thiếu import `ADB_PATH` trong `tiktok_login_v1.py`
- **Hiện tượng:** Khi chạy `python tiktok_login_v1.py <stt> --email <target>`, script dừng tại:
  `[device-lock] VPN GATE BLOCKED: ... adb executable not found: adb`
- **Nguyên nhân:** Dòng 604 gọi:
  ```python
  require_android_vpn(AdbClient(adb_path=ADB_PATH if "ADB_PATH" in globals() else "adb", serial=device_id), required=required)
  ```
  Nhưng ở đầu file `tiktok_login_v1.py`, khối `from social_reg_v1 import (...)` thiếu `ADB_PATH`. Do `"ADB_PATH" in globals()` trả về `False`, script fallback sang `"adb"` trong khi Windows không có adb trên PATH hệ thống.
- **Giải pháp:**
  1. Thêm `ADB_PATH,` vào danh sách import từ `social_reg_v1` trong `tiktok_login_v1.py`.
  2. Hoặc luôn export PATH trước khi gọi: `export PATH="/c/Program Files (x86)/xiaowei/tools:$PATH"`.

### Cạm bẫy 2: Reconcile bị chặn bởi tài khoản thiếu mật khẩu (`TT_PW = None`)
- **Hiện tượng:** Chạy `reconcile_tiktok_accounts.py` văng lỗi:
  `AccountInventoryError: machine N: TikTok ID/password is unavailable for <account_id>`
- **Nguyên nhân:** Hàm `_selected_missing_accounts` trong `account_reconcile.py` duyệt toàn bộ nick thiếu trong `taikhoan_run_safe.xlsx`. Nếu có 1 nick trong Excel chưa được điền mật khẩu TikTok (cột D rỗng), runner sẽ ném exception và hủy toàn bộ quá trình reconcile của máy đó.
- **Giải pháp:** 
  - Khi cần nạp gấp 1 nick cụ thể: Dùng `tiktok_login_v1.py <stt> --email <target>` để login riêng nick đó.
  - Hoặc cập nhật mật khẩu cho nick thiếu trong master workbook trước khi chạy `reconcile_tiktok_accounts.py`.

### Cạm bẫy 3: Xung đột Device Lock còn sót từ batch feed trước
- **Hiện tượng:** Script báo `[device-lock] NEEDS_USER_DECISION: device lock active: path=...machine_N.lock.json status=blocked`.
- **Nguyên nhân:** Phiên feed-session trước đó bị dừng/timeout nhưng file lock `machine_N.lock.json` chưa được giải phóng.
- **Giải pháp:** Kiểm tra PID sở hữu lock. Nếu tiến trình cũ đã dừng hoặc slot đã được bàn giao (`handoff_at`), giải phóng lock an toàn hoặc truyền cờ takeover phù hợp trước khi gọi login runner.

### Cạm bẫy 4: Email Hotmail/Non-Gmail nằm trong ứng dụng Gmail trên máy (thay vì Outlook app)
- **Hiện tượng:** Khi TikTok yêu cầu OTP email cho một tài khoản `@hotmail.com` (ví dụ `segovkibido@hotmail.com`), runner `tiktok_login_v1.py` kiểm tra `not email.endswith('@gmail.com')` nên tự động mở app **Outlook** để lấy OTP. Nhưng app Outlook trên máy chưa đăng nhập hòm thư này (văng `OUTLOOK_APP_PASSWORD_FIELD_NOT_FOUND`).
- **Bản chất hiện trường:** Trên thực tế các máy farm Android, hòm thư Hotmail thường được nạp thẳng vào bên trong **ứng dụng Gmail** của máy (`live_gmail_accounts(device_id)["emails"]` chứa cả Hotmail).
- **Giải pháp:**
  1. Trước khi đăng nhập tài khoản Hotmail, kiểm tra `live_gmail_accounts(device_id)["emails"]`. Nếu email đã nằm trong Gmail app, điều hướng đọc OTP qua Gmail app (`read_tiktok_otp_from_gmail_app`) thay vì ép mở Outlook.
  2. Khi chọn tài khoản khôi phục phiên chính thức cho máy, ưu tiên tài khoản có domain `@gmail.com` (như `ninhy05100` với email `ninhy05102002@gmail.com`) để khớp 100% với luồng đọc Gmail app mặc định sẵn có.

### Cạm bẫy 5: Nhận diện tín hiệu Handoff an toàn từ Batch Feed đa máy (`owner_active: false`)
- **Hiện tượng:** Khi chạy login đơn lẻ, script báo `[device-lock] NEEDS_USER_DECISION` do file lock `machine_N.lock.json` tồn tại.
- **Cơ chế chuẩn của Farm:** Khi batch `multi-machine-feed-session` quét qua một máy và thấy máy đó chưa có tài khoản trong Switcher (hoặc thiếu nick), batch sẽ ghi nhận:
  ```json
  {
    "status": "blocked",
    "owner_active": false,
    "handoff_at": "2026-09-08T06:23:52.964800+00:00"
  }
  ```
- **Ý nghĩa:** Cờ `"owner_active": false` kèm `"handoff_at"` là tín hiệu **BÀN GIAO CHÍNH THỨC** từ tiến trình feed-session sang cho quy trình khôi phục tài khoản / reconcile. Tiến trình feed đã kết thúc tác vụ trên máy đó và chuyển sang máy kế tiếp.
- **Xử lý:** Khi thấy `owner_active: false` và `handoff_at`, Coordinator được phép dọn dẹp file lock để nhường quyền cho `tiktok_login_v1.py` hoặc `reconcile_tiktok_accounts.py` thực thi an toàn mà không gây xung đột ADB.

### Cạm bẫy 6: Xóa stale lock phải xóa CẢ HAI file (`machine_N` VÀ `serial_<serial>`)
- **Hiện tượng:** Sau khi xóa `C:\Users\Kibe\.codex\device-locks\machine_N.lock.json`, chạy runner vẫn văng:
  `[device-lock] NEEDS_USER_DECISION: device lock active: path=...serial_<serial>.lock.json`.
- **Nguyên nhân:** Thư viện `device_lock.py` (`_lock_names`) kiểm tra đồng thời cả tên theo machine (`machine_N.lock.json`) và tên theo serial (`serial_<serial>.lock.json`).
- **Giải pháp:** Khi dọn dẹp lock stale đã handoff, BẮT BUỘC xóa cả 2 file:
  ```bash
  rm -f "C:/Users/Kibe/.codex/device-locks/machine_N.lock.json" "C:/Users/Kibe/.codex/device-locks/serial_<serial>.lock.json"
  ```

### Cạm bẫy 7: Bỏ qua mở Account Switcher Gmail khi `target_selected == True`
- **Hiện tượng:** Mở app Gmail lấy OTP cho nick target (ví dụ `ninhy05102002@gmail.com`), script tap avatar mở Switcher, nhưng bị tap nhầm vào email cảnh báo bảo mật Google ở background khiến màn hình nhảy vào chi tiết thư và timeout.
- **Nguyên nhân:** Trên Android, panel switcher là overlay đè lên inbox. Hàm tìm text email match nhầm chuỗi email nằm trong tóm tắt thư bảo mật Google ở inbox nền.
- **Giải pháp:** Trong `_try_get_otp_gmail_app` (`social_reg_v1.py`), kiểm tra `current_state = _gmail_mailbox_state(xml, email)`. Nếu `target_selected == True` (email target đã là active account ở header `selected_account_disc_gmail`), BỎ QUA HOÀN TOÀN bước tap avatar mở switcher, đi thẳng vào đọc inbox.

### Cạm bẫy 8: Đăng xuất 1 nick làm app TikTok rơi vào trạng thái Logged Out toàn bộ
- **Hiện tượng:** Khi logout 1 tài khoản (ví dụ tài khoản rác/gán trùng `miumiu67971`), app TikTok không tự chuyển sang nick kế tiếp mà chuyển toàn bộ app về màn hình Hồ sơ trắng ("Đăng nhập vào tài khoản hiện có"), tile Fast Login hiện nick vừa thoát đòi OTP. Người dùng hoảng hốt tưởng bị xóa sạch nick trên máy.
- **Bản chất TikTok Multi-account:** TikTok đăng xuất session làm việc hiện tại, nhưng credential của các nick khác không hề bị xóa khỏi thiết bị.
- **Khôi phục chuẩn:** Chỉ cần dùng `tiktok_login_v1.py` đăng nhập lại 1 nick chính (có sẵn mật khẩu + 2FA / Gmail OTP), ngay khi nick đó vào lại Profile, toàn bộ danh sách các nick cũ đã lưu sẽ tự động xuất hiện lại đầy đủ 100% trong Account Switcher (mở bằng tap display name ở `539, 552`).

### Cạm bẫy 9: Luồng `--resume` trong `tiktok_login_v1.py` ngộ nhận đã điền email khi máy còn ở form 'Email hoặc TikTok ID'
- **Hiện tượng:** Máy đang ở form đăng nhập `Email hoặc TikTok ID` (chưa nhập email, nút 'Tiếp tục' đang mờ). Chạy runner với cờ `--resume` (ví dụ `python tiktok_login_v1.py 30 --email ninhvan04061999@gmail.com --resume --ss`), script lập tức vào 6 round auth tìm password/OTP/2FA:
  `[8] Fill password -> Không có màn password (flow email-only / OTP), bỏ qua`
  và kết thúc bằng `✗ Timeout chờ login success: ninhvan04061999@gmail.com`.
- **Nguyên nhân:** Hàm `resume_one_account` trong `tiktok_login_v1.py` nhảy thẳng vào `drive_login_screens(device_id, account)` mà không kiểm tra xem màn hình hiện tại có đang dừng ở ô nhập email hay không (`fill_existing_email_and_continue`).
- **Giải pháp:**
  1. Trong `resume_one_account`, kiểm tra XML màn hình hiện tại. Nếu chứa `"Email hoặc TikTok ID"`, `"Email/tên người dùng"` hoặc hint form email, bắt buộc gọi `fill_existing_email_and_continue(device_id, account["login_email"], stt=stt)` trước khi chuyển giao cho `drive_login_screens`.
  2. Hoặc nếu chạy login khi màn hình đã mở sẵn form đăng nhập nhưng chưa điền email, dùng cờ không resume hoặc cập nhật `resume_one_account` để tự động fill email.


