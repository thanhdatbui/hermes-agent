# Parasite Account Guard & Anti-Reg-Hijack Discipline (Taadaa Phone Farm)

## 1. Vấn đề "Nick ký sinh" (Parasite Account)
Trên Taadaa Phone Farm, mỗi máy Android (STT 1 -> 80) được gán quản lý một tập hợp tài khoản cố định theo workbook tracking (`taikhoan_dat_v2_updated .xlsx` và `taikhoan_run_safe.xlsx`).
Hai kịch bản gây ra lỗi nick ký sinh (tài khoản máy A nằm trên máy B):
1. **Reg Hijack sang Login**: Khi chạy `social_reg_v1.py` trên Máy B, nếu email nhập vào đã có tài khoản TikTok (`result == "registered"` hoặc `"registered_otp"`), runner cũ tự động nhảy vào nhập pass / đọc OTP và đăng nhập luôn vào TikTok trên Máy B. Nếu email đó vốn dĩ thuộc quyền sở hữu của Máy A, tài khoản đó trở thành "nick ký sinh" trên Máy B.
2. **Login nhầm máy**: Khi chạy `tiktok_login_v1.py`, nếu truyền nhầm STT hoặc danh sách account mà không kiểm tra đối chiếu STT thực tế trong workbook, tài khoản sẽ bị login sai máy.

## 2. Cơ chế bảo vệ: `parasite_guard.py`
Module trung tâm đặt tại `D:/Taadaa/Tiktok_Reg/parasite_guard.py`:
- `find_account_owner_stt(identifier: str) -> int | None`:
  Tra cứu `target` (TikTok ID, email, username) trong:
  1. `D:/OneDrive/TaadaaData/kibe/taikhoan_dat_v2_updated .xlsx` (sheet `Tài Khoản`, cột A = STT, C = TikTok ID, F = Gmail).
  2. `D:/OneDrive/TaadaaData/kibe/taikhoan_run_safe.xlsx` (sheet `Accounts`, cột A = STT, C = TikTok ID).
  3. `D:/OneDrive/TaadaaData/admin/taikhoan_run_safe.xlsx` (sheet `Accounts`).
- `assert_account_machine_binding(target_stt, account_identifier, allow_override=False, operator_reason="")`:
  - Ném `ParasiteAccountViolation(RuntimeError)` nếu `owner_stt != target_stt`.
  - Nếu `allow_override=True`, in cảnh báo `⚠️ [WARN:OPERATOR_OVERRIDE]` và cho phép tiếp tục (dùng cho migration có chủ đích).

## 3. Quy tắc tích hợp bắt buộc

### Trong `tiktok_login_v1.py`
- Parser argument:
  ```python
  parser.add_argument("--override-machine", action="store_true", help="Cho phep login de di chuyen may duoc phep")
  ```
- Tại đầu hàm `login_one_account(device_id, stt, account, ...)`:
  ```python
  from parasite_guard import assert_account_machine_binding
  override = bool(getattr(account, "get", lambda k, d=None: None)("override_machine") or getattr(account, "override_machine", False))
  if account.get("id"):
      assert_account_machine_binding(stt, account["id"], allow_override=override, operator_reason="Operator migration")
  if account.get("login_email"):
      assert_account_machine_binding(stt, account["login_email"], allow_override=override, operator_reason="Operator migration")
  ```

### Trong `social_reg_v1.py`
- Đầu hàm `register()`:
  ```python
  if acc.get("email"):
      from parasite_guard import assert_account_machine_binding
      override = bool(getattr(acc, "get", lambda k, d=None: None)("override_machine", False) or getattr(acc, "get", lambda k, d=None: None)("allow_cross_machine", False))
      assert_account_machine_binding(stt, acc["email"], allow_override=override, operator_reason="Canary test")
  ```
- Tại `pick_and_fill_email()`:
  CẤM TUYỆT ĐỐI tự ý đi tiếp vào flow login hay OTP trên luồng reg!
  Nếu `result in ("registered", "registered_otp")`:
  ```python
  log(f"   ✗ {em}: Email DA CO tai khoan TikTok tren he thong -> ABORT luong reg, cấm login len!")
  screenshot(device_id, f"reg_aborted_already_registered_{stt}_{em}")
  continue  # Bỏ qua thử email khác hoặc thoát, KHÔNG return em, pw, dob để đi tiếp vào login/OTP!
  ```
