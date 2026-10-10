# Pre-login Gmail Live Gate & Subprocess Parent Lock Inheritance (2026-09-25)

## 1. Bối cảnh & Hiện tượng
- Khi cronjob / watchdog phục hồi tài khoản (`cron_m3_restore_annhubvqttr.py`) gọi `tiktok_login_v1.py`, script login lập tức trả về `exit=2` sau vài giây mà không thực hiện được thao tác đăng nhập nào trên TikTok.
- Đồng thời, tài khoản cần đăng nhập (`an.nhuan.work64541@gmail.com`) dính cảnh báo xác minh bảo mật của Google trên thiết bị, khiến app Gmail bị treo ở trạng thái `Đang nhận thư của bạn…` và không đồng bộ OTP.

---

## 2. Các nguyên nhân cốt lõi

### A. Bẫy Device Lock khi gọi Subprocess (Exit=2)
- Script watchdog cha đã gọi `acquire_device_lock(machine=3, serial=..., project="tiktok-login-restore")`.
- Khi gọi subprocess `python tiktok_login_v1.py 3 --email ...`, script con cũng cố gọi `acquire_device_lock()`.
- Do thiếu cờ `--allow-parent-lock`, `tiktok_login_v1.py` phát hiện thiết bị đang bị lock bởi tiến trình cha và quăng `DeviceLockNeedsUserDecision`, dẫn đến `exit=2` ngay lập tức.
- **Kỷ luật:** Mọi runner/watchdog cha khi gọi `tiktok_login_v1.py` BẮT BUỘC phải truyền `--allow-parent-lock` và đảm bảo tên project cha nằm trong whitelist `PARENT_LOCK_PROJECTS`.

### B. Thiếu cổng Pre-login Live Check cho Gmail & Cạm bẫy "Gmail DIE = TikTok DIE" (P0 Warning)
- Nếu tài khoản Gmail đã DIE hoặc bị mất phiên / dính Action Required, việc mở app TikTok, điều hướng đến form OTP và chờ lấy mã 150s sẽ gây lãng phí tài nguyên và làm kẹt màn hình máy farm.
- Cần có cơ chế fail-fast: kiểm tra liveness của Gmail trước khi thực hiện bất kỳ thao tác UI nào.
- 🚨 **CẠM BẪY PHÁN BỪA TÀI KHOẢN DIE (COORDINATOR TRIAGE TRAP - 2026-10-10)**:
  * Tuyệt đối **CẤM ĐÁNH ĐỒNG "Gmail die = TikTok die"**!
  * Rất nhiều tài khoản TikTok có **2FA Authenticator TOTP** (`twofa` key trong Excel) đã đăng ký từ trước. Khi đăng nhập, TikTok chỉ yêu cầu Password + 6 số TOTP sinh từ Authenticator app, **HOÀN TOÀN KHÔNG CẦN OTP GMAIL**.
  * Khi đối soát hoặc thấy máy báo `ACCOUNT_MISSING`, Coordinator BẮT BUỘC kiểm tra: (1) Cột 2FA trong Master Excel có secret key không? (2) Bảng `snapshots` trong `tiktok_tracker.db` tài khoản có còn trạng thái `LIVE` không?
  * Nếu tài khoản có 2FA và vẫn `LIVE` trên TikTok: Đây là tài sản có giá trị (tuổi cao, có sẵn video/followers), **CẤM TUYỆT ĐỐI phán nick die để reg nick mới đè lên**, mà phải ưu tiên đăng nhập khôi phục bằng TOTP.

---

## 3. Quy chuẩn Pre-login Gmail Live Gate (Fail-Fast)

Trong `tiktok_login_v1.py`:
1. Ngay đầu hàm `login_one_account`:
   ```python
   login_email = (account.get("login_email") or "").strip()
   if login_email.lower().endswith("@gmail.com"):
       log(f"   [gmail-live-gate] Kiem tra live Gmail truoc khi login: {login_email}")
       try:
           is_live = check_gmail_is_live(login_email)
       except Exception as exc:
           log(f"   [gmail-live-gate] warning: check_gmail_is_live gap ngoai le: {exc} -> fallback cho phep tiep tuc")
           is_live = True
       if is_live is False:
           log(f"   [gmail-live-gate] BLOCKED: Gmail {login_email} DIE (xac nhan boi checkmail.live) -> SKIP login")
           return False
   ```
2. **Quy tắc an toàn & Bẫy Chặn Sai Với Tài Khoản 2FA (2026-10-02 Update)**:
   - **BẪY CHẶN SAI (FALSE BLOCKER)**: Khi tài khoản đã có đầy đủ `TikTok ID`, `tiktok_pass` và `twofa` (mã bí mật TOTP base32), script sẽ đăng nhập trực tiếp qua ID + Password + nhập mã Authenticator TOTP (`handle_tiktok_authenticator_2fa`). Tài khoản KHÔNG BAO GIỜ cần nhận mã OTP qua hòm thư Gmail!
   - Nếu để `_gmail_live_gate` chặn mù quáng, khi proxy checkmail chập chờn hoặc checkmail.live timeout/DIE, tài khoản hoàn toàn khỏe mạnh sẽ bị chặn oan (`[login] Gmail live gate blocked <mail>; no UI action will be attempted`).
   - **Bắt buộc điều kiện bypass & Telemetry**:
     ```python
     has_2fa_auth = bool(account.get("id") and account.get("tiktok_pass") and account.get("twofa"))
     if has_2fa_auth:
         log(f"[telemetry:gmail-live] action=bypass_2fa_auth account={account.get('id')} has_2fa=true")
     elif not _gmail_live_gate(account.get("login_email")):
         log(f"[login] Gmail live gate blocked {account.get('login_email')}; no UI action will be attempted")
         return False
     ```
   - **Pitfall khi viết Unit Test / Mock Account**: Trong `login_one_account`, các trường metadata như `account.get('sheet', '')`, `account.get('row', '')` phải dùng `.get()` an toàn; tránh truy cập trực tiếp `account['sheet']` trong f-string vì f-string được evaluate trước khi gọi `log(...)`, gây `KeyError` nếu mock account trong unit test thiếu các trường này.
   - Gmail DIE (`is_live is False` và KHÔNG có 2FA TOTP đầy đủ) $\rightarrow$ Dừng ngay lập tức (return False), KHÔNG mở app TikTok (`open_app`), KHÔNG chạm vào UI thiết bị.
   - Gmail LIVE hoặc có đủ `id + pass + twofa` $\rightarrow$ Cho phép tiếp tục flow login bình thường.
   - Tài khoản Hotmail/Outlook $\rightarrow$ Bỏ qua gate này để không làm chậm tiến trình.

---

## 5. Triage Lỗi Exit Code 1 Do TRACKING_WORKBOOK_WRITE_LOCKED (False Failure)
- **Hiện tượng**: Chạy `tiktok_login_v1.py` hoàn thành tất cả các bước nhưng tiến trình thoát với `exit code 1` kèm dòng cuối:
  ```text
  [gate] BLOCK TRACKING_WORKBOOK_WRITE_LOCKED: D:\OneDrive\TaadaaData\kibe\taikhoan_dat_v2_updated .xlsx :: [Errno 9] Bad file descriptor
  ! upsert_tracking_account: TRACKING_WORKBOOK_WRITE_LOCKED
  STOPPED: TRACKING_WORKBOOK_WRITE_LOCKED
  ```
- **Bản chất**: Thao tác đăng nhập trên app điện thoại **ĐÃ THÀNH CÔNG 100%**:
  * Log đã ghi nhận: `✓ [login-success] home feed UI proof: <mail>`
  * Profile đã được xác nhận: `[profile] handle=@<id> name=...`
  * Lỗi chỉ xảy ra ở bước cuối cùng khi script cố gắng ghi nhật ký thành công ngược lại file Excel `taikhoan_dat_v2_updated .xlsx` nhưng file đang bị khóa bởi tiến trình OneDrive Sync hoặc Excel khác trên máy.
- **Kỷ luật điều phối**:
  * CẤM vội vàng kết luận "login thất bại" khi thấy exit code 1.
  * BẮT BUỘC kiểm tra dòng log phía trên: nếu thấy `[login-success]` và `profile selected`, hãy chụp ảnh màn hình Profile hoặc Switcher trên điện thoại (`screencap`) để xác nhận trực quan. Nếu nick đã nằm trong app TikTok, nhiệm vụ đăng nhập thực tế đã HOÀN THÀNH.


---

## 4. Kỷ luật Chẩn đoán Blocker (Chống Đổ Lỗi Công Cụ)
- Trên Farm Windows, đường dẫn `adb.exe` chuẩn luôn được khai báo tại `C:\Program Files (x86)\xiaowei\tools\adb.exe` hoặc biến `ADB_PATH` trong module `social_reg_v1`.
- Tuyệt đối CẤM Coordinator vội vàng kết luận "blocker do thiếu công cụ adb trong PATH" khi bash không tìm thấy lệnh `adb` thô. Bắt buộc kiểm tra file code và chạy với full path của ADB trước khi báo cáo.
