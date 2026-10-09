# Parasite Account Guard & Reg-to-Login Hijack Prevention (2026-09-24)

Kỷ luật code-level chống tạo nick ký sinh (parasite account) và cấm tuyệt đối luồng đăng ký (social_reg_v1.py) tự ý biến thành luồng đăng nhập lén.

---

## 1. BỐI CẢNH SỰ CỐ (INCIDENT POST-MORTEM)

- **Hiện tượng:** Để kiểm tra 1 email Hotmail (`odessostuffen14@hotmail.com`) đã qua TikTok chưa, Coordinator lấy Máy 201 (dàn Admin) ra test.
- Khi nhập email, TikTok hiện thông báo: **"Bạn đã đăng ký - Hãy nhấn vào Tiếp tục để đăng nhập vào tài khoản của bạn"**.
- Coordinator tự tiện bấm "Tiếp tục", bóc mã OTP từ Graph API rồi nhập vào màn hình.
- **Hậu quả nghiêm trọng:** Tài khoản `@lethanhlan14` (vốn đã được Farm reg thành công từ trưa nay trên **Máy 22**) bị đăng nhập phiên lên cả **Máy 201**, tạo thành **nick ký sinh trên 2 thiết bị khác nhau**, có nguy cơ bị TikTok quét trùng IP / checkpoint.
- **Căn nguyên:**
  1. *Thiếu kiểm tra Source of Truth:* Con mail đã được reg xong và lưu vào hàng 176 sheet "Tài Khoản" của `taikhoan_dat_v2_updated .xlsx`, nhưng Coordinator không tra cứu mà tự giả định là "chưa reg" rồi vác đi test lại.
  2. *Thiếu chốt chặn code-level:* Code `social_reg_v1.py` cũ có nhánh `if result == "registered": if is_preferred: return em, pw, dob` dẫn tuột vào luồng đăng nhập nếu email đã tồn tại.
  3. *Chỉ đạo tối cao của User:* **"Đừng có lưu memory gì hết vì mày không bao giờ tuân thủ — phải có phương án khắc phục triệt để bằng code."**

---

## 2. NGUYÊN TẮC CỐT LÕI (INVARIANTS)

1. **QUYỀN SỞ HỮU THIẾT BỊ 1-1:** Mỗi tài khoản TikTok (ID / Email) chỉ được phép tồn tại và đăng nhập trên DUY NHẤT một máy STT đã được phân bổ trong tracking workbook (`taikhoan_dat_v2_updated .xlsx` hoặc `taikhoan_run_safe.xlsx`).
2. **CẤM REG-TO-LOGIN HIJACKING:** Tool đăng ký (`social_reg_v1.py`) CHỈ ĐƯỢC PHÉP tạo nick mới. Khi TikTok báo "Bạn đã đăng ký" hoặc đòi OTP đăng nhập, tool PHẢI DỪNG NGAY (Abort), cấm tuyệt đối bấm "Tiếp tục" hay nhập OTP.
3. **PHÂN BIỆT RE-LOGIN VS MIGRATION:**
   - **Re-login nick bị văng:** Dùng `tiktok_login_v1.py`. Nếu đăng nhập vào đúng máy sở hữu (`target_stt == owner_stt`) -> PASS 100%.
   - **Chuyển máy (Migration):** Cập nhật workbook trước, hoặc truyền cờ chỉ định `--override-machine`.

---

## 3. KIẾN TRÚC BẢO VỆ (`parasite_guard.py`)

Module `D:/Taadaa/Tiktok_Reg/parasite_guard.py` hoạt động như single chokepoint:

```python
from parasite_guard import assert_account_machine_binding, ParasiteAccountViolation

# Kiểm tra ràng buộc máy trước khi thao tác
assert_account_machine_binding(
    target_stt=stt,
    account_identifier=account_id_or_email,
    allow_override=override_flag,
    operator_reason="Canary test / Migration"
)
```

- **Cơ chế:**
  - Tra cứu STT máy sở hữu qua `find_account_owner_stt()` từ các file (hỗ trợ override linh hoạt qua biến môi trường `PARASITE_GUARD_WORKBOOK_PATH` hoặc config):
    + `D:/OneDrive/TaadaaData/kibe/taikhoan_dat_v2_updated .xlsx`
    + `D:/OneDrive/TaadaaData/kibe/taikhoan_run_safe.xlsx`
    + `D:/OneDrive/TaadaaData/admin/taikhoan_run_safe.xlsx`
  - Nếu `owner_stt != target_stt`:
    + Mặc định: Ném `ParasiteAccountViolation` -> HARD ABORT, chặn đứng thao tác gõ phím / ADB, ghi log audit `parasite_guard_audit.jsonl` và bắn cảnh báo Telegram farm alerting.
    + Nếu có `allow_override=True`: In log cảnh báo `⚠️ [WARN:OPERATOR_OVERRIDE]` và cho phép tiếp tục.

---

## 4. TÍCH HỢP VÀO CÁC TOOL CHÍNH

### A. Trong `tiktok_login_v1.py`:
- Thêm CLI flag: `--override-machine`
- Top-level import ở đầu module (dùng try/except relative vs absolute fallback):
  ```python
  try:
      from .parasite_guard import assert_account_machine_binding
  except ImportError:
      from parasite_guard import assert_account_machine_binding
  ```
- Tại đầu hàm `login_one_account()` (xóa bỏ import cục bộ):
  ```python
  override = bool(account.get("override_machine", False))
  if account.get("id"):
      assert_account_machine_binding(stt, account["id"], allow_override=override, operator_reason="Operator migration")
  if account.get("login_email"):
      assert_account_machine_binding(stt, account["login_email"], allow_override=override, operator_reason="Operator migration")
  ```

### B. Trong `social_reg_v1.py`:
- Top-level import ở đầu file (sau các import ban đầu, dùng try/except fallback):
  ```python
  try:
      from .parasite_guard import assert_account_machine_binding, ParasiteAccountViolation
  except ImportError:
      from parasite_guard import assert_account_machine_binding, ParasiteAccountViolation
  ```
- Tại đầu hàm `register()` (xóa bỏ import cục bộ):
  ```python
  target_email = preferred_email or acc.get("email")
  if target_email:
      override = bool(acc.get("override_machine") or acc.get("allow_cross_machine"))
      try:
          assert_account_machine_binding(stt, target_email, allow_override=override, operator_reason="Canary reg")
      except ParasiteAccountViolation as pv:
          log(f"⚠ [PARASITE_BLOCKED] {pv}")
          dev_lease.release()
          return False
  ```
- Tại phát hiện màn hình đã đăng ký (`registered` / `registered_otp`):
  ```python
  if result in ("registered", "registered_otp"):
      log(f"   ✗ {em}: Email DA CO tai khoan TikTok tren he thong -> ABORT email nay tren luong reg, CAM login len!")
      save_ui_xml(device_id, f"fail_{stt}_email_already_registered_{idx}")
      shell(device_id, "input", "keyevent", "4")
      time.sleep(2.0)
      continue
  ```

---

## 5. QUY TRÌNH DỌN DẸP NICK KÝ SINH KHI BỊ SỰ CỐ (LOGOUT PLAYBOOK)

Khi lỡ đăng nhập nhầm nick lên máy khác, bắt buộc thực hiện theo đúng các bước sau để trả máy về sạch sẽ:

1. **Mở Hồ sơ:** Tap nút Hồ sơ (`input tap 972 1857` hoặc OCR tìm bounds `Hồ sơ`).
2. **Mở Menu 3 gạch:** Tap góc trên cùng bên phải (`input tap 1002 144`).
3. **Mở Cài đặt và quyền riêng tư:** OCR tìm chữ "Cài đặt và quyền riêng tư" (thường tọa độ y ~ 1248).
4. **Cuộn xuống đáy trang Settings:**
   ```bash
   for i in $(seq 1 4); do input swipe 540 1600 540 300 250; sleep 1; done
   ```
5. **Bấm Đăng xuất:** OCR tìm chữ "Đăng xuất" (thường tọa độ y ~ 1662).
6. **Xác nhận Đăng xuất:** Tại popup "Bạn có chắc chắn muốn đăng xuất?", tap nút đỏ "Đăng xuất" ở giữa màn hình.
7. **Nghiệm thu Switcher:**
   - Tap vào tên tài khoản trên header để mở dropdown switcher.
   - Dùng WinRT OCR hoặc dump XML xác nhận nick ký sinh đã biến mất hoàn toàn.
   - Chụp ảnh `screencap` gửi báo cáo cho User kèm `MEDIA:<path_anh>`.
   - Force-stop TikTok và đưa máy về Home.
