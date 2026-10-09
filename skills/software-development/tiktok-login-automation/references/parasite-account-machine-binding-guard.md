# Parasite Account Machine Binding Guard (2026-09-24)

Kỷ luật ràng buộc thiết bị 1-1 chống đăng nhập tài khoản sang máy khác (Parasite Account) trong `tiktok_login_v1.py`.

---

## 1. NGUYÊN TẮC CỐT LÕI (CORE INVARIANTS)

1. **Ràng buộc thiết bị 1-1:**
   Mỗi nick TikTok (ID và Login Email) chỉ được gán cho một STT máy duy nhất trong tracking workbook (`taikhoan_dat_v2_updated .xlsx` hoặc `taikhoan_run_safe.xlsx`).
2. **Re-login nick bị văng:**
   Khi nick bị văng khỏi TikTok trên máy được gán (`target_stt == owner_stt`), tool login `tiktok_login_v1.py` luôn luôn cho phép đăng nhập lại bình thường 100%.
3. **Chống nick ký sinh (Parasite Prevention):**
   Nếu nick được chỉ định đăng nhập vào máy khác (`target_stt != owner_stt`), tool sẽ ném lỗi `ParasiteAccountViolation` và dừng ngay lập tức.
4. **Cơ chế di chuyển máy có chủ đích (Migration Override):**
   Nếu máy cũ hỏng hoặc Operator chủ động di chuyển nick sang máy mới, bắt buộc phải truyền cờ `--override-machine`. Khi có cờ này, tool sẽ in log cảnh báo `⚠️ [WARN:OPERATOR_OVERRIDE]` và cho phép tiếp tục.

---

## 2. CODE TÍCH HỢP TRONG `tiktok_login_v1.py`

```python
# 1. Thêm CLI argument
parser.add_argument("--override-machine", action="store_true", help="Cho phep login de di chuyen may duoc phep")

# 2. Kiểm tra tại entrypoint login_one_account()
from parasite_guard import assert_account_machine_binding

override = bool(account.get("override_machine", False))
if account.get("id"):
    assert_account_machine_binding(stt, account["id"], allow_override=override, operator_reason="Operator migration")
if account.get("login_email"):
    assert_account_machine_binding(stt, account["login_email"], allow_override=override, operator_reason="Operator migration")
```

---

## 3. CHECKLIST KHI GẶP NICK BỊ VĂNG
- [ ] Xác nhận máy thực hiện login là đúng máy sở hữu nick theo `taikhoan_dat_v2_updated .xlsx` hoặc `taikhoan_run_safe.xlsx`.
- [ ] Chạy lệnh canonical:
  ```bash
  python tiktok_login_v1.py <STT> --email <ID_hoặc_Email> --ss
  ```
- [ ] Nếu là trường hợp chuyển máy sang STT mới:
  ```bash
  python tiktok_login_v1.py <STT_mới> --email <ID_hoặc_Email> --override-machine --ss
  ```
