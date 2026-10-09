# Parasite Account Guard & Farm Alert Integration

## 1. Context & Danger of Parasite Accounts
Trên farm nhiều máy (Samsung S7 farm), mỗi máy (STT) sở hữu một danh sách account xác định trong workbook (`taikhoan_dat_v2_updated .xlsx` / `taikhoan_run_safe.xlsx`).
"Tài khoản ký sinh" (Parasite Account) xảy ra khi một script login hoặc register trên Máy A lại cố thao tác với tài khoản thuộc quyền sở hữu của Máy B:
- Gây mất đồng bộ phiên (session clash / kick login giữa các máy).
- Bị TikTok gắn cờ bot / thiết bị lạ đăng nhập bất thường.
- Làm hỏng tiến độ farm và làm lệch mapping dữ liệu slot.

## 2. Kiến trúc Bảo vệ (Parasite Guard Architecture)
`parasite_guard.py` cung cấp cơ chế bảo vệ cứng:
1. `find_account_owner_stt(identifier)`: Tra cứu STT sở hữu tài khoản qua username TikTok hoặc Gmail trong tracking workbooks.
2. `assert_account_machine_binding(target_stt, account_identifier, allow_override=False, ...)`:
   - Nếu `owner_stt is not None and owner_stt != target_stt`:
     - Nếu `allow_override=True`: log cảnh báo + audit event status=`allowed`, cho phép đi tiếp (thao tác di chuyển có chủ đích của operator).
     - Nếu không override:
       - Log structured audit event status=`blocked` vào file audit JSONL.
       - Gửi farm alert qua `automation_core.alerts.send_farm_machine_alert(machine=target_stt, script_name="ParasiteAccountGuard", status_text="PARASITE_ACCOUNT_BLOCKED", ...)`.
       - Raise `ParasiteAccountViolation` để chặn đứng hành vi sai lệch ngay lập tức.

## 3. Best Practices & Invariants khi Tích hợp vào Consumer Repos

### A. Top-Level Import Hoisting
- **Không dùng lazy import trong hàm:** Không đặt `from parasite_guard import ...` sâu bên trong các hàm thực thi (`login_one_account`, `register`).
- **Đưa lên top-level với fallback safe import:**
  ```python
  try:
      from .parasite_guard import assert_account_machine_binding, ParasiteAccountViolation
  except ImportError:
      from parasite_guard import assert_account_machine_binding, ParasiteAccountViolation
  ```
- **Lý do:** Lỗi import, cú pháp, hoặc thiếu module được phát hiện ngay khi nạp module thay vì chờ đến giữa chu trình chạy automation thực tế.

### B. Cấu hình Đường dẫn qua Biến Môi trường (Configurable Env Overrides)
- Trong `parasite_guard.py`, ưu tiên đọc đường dẫn từ environment trước khi dùng đường dẫn mặc định:
  ```python
  DEFAULT_TRACKING_PATH = Path(os.environ.get("TIKTOK_REG_TRACKING_WORKBOOK") or r"D:/OneDrive/TaadaaData/kibe/taikhoan_dat_v2_updated .xlsx")
  DEFAULT_AUDIT_LOG = Path(os.environ.get("PARASITE_GUARD_AUDIT_LOG") or r"D:/Taadaa/runtime/audit/parasite_guard_audit.jsonl")
  ```
- Giúp pytest fixture, sandbox, hoặc runner ở các môi trường cô lập có thể trỏ vào file test mà không ảnh hưởng workbook thật.

### C. Farm Alerting Integration & Fail-Safe Handling
- Khi phát hiện vi phạm, phát tín hiệu cảnh báo tập trung về farm:
  ```python
  try:
      from automation_core.alerts import send_farm_machine_alert
      send_farm_machine_alert(
          machine=t_stt,
          serial="",
          script_name="ParasiteAccountGuard",
          account=account_identifier,
          error_reason=f"Attempted parasite operation on machine {t_stt} while owned by {owner_stt}",
          status_text="PARASITE_ACCOUNT_BLOCKED",
      )
  except Exception:
      pass
  ```
- Luôn bọc lệnh alert trong `try...except Exception: pass` để lỗi mạng hoặc API alert không làm lu mờ ngoại lệ chính `ParasiteAccountViolation`.

## 4. Verification Pattern
Kiểm thử guard và consumer hooks với pytest:
```bash
PYTHONPATH="D:/Taadaa/Tiktok_Reg;D:/Taadaa/automation-core" python -m pytest tests/test_parasite_guard.py -v -p no:cacheprovider
```
Đảm bảo kiểm tra đủ 4 nhánh:
1. Verify hợp lệ khi `owner == target`.
2. Block và raise `ParasiteAccountViolation` khi `owner != target`.
3. Cho phép khi có cờ `allow_override=True`.
4. Không crash nếu workbook bị hỏng định dạng (`load_workbook` exception handling).
