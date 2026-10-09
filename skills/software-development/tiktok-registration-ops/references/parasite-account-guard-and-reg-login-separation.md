# Parasite Account Guard & Tách Bạch Luồng Reg - Login (2026-09-24)

## 1. Sự Cố "Nick Ký Sinh" (Incident Context - 2026-09-24)
- **Hành vi sai lầm:** Để kiểm tra 1 email Hotmail (`odessostuffen14@hotmail.com`) đã qua TikTok hay chưa, Coordinator lấy Máy 201 (dàn Admin) ra thử. Khi TikTok hiển thị màn hình *"Bạn đã đăng ký"* (Account already registered), Coordinator đã tiện tay bấm *"Tiếp tục"* và lấy mã OTP từ Microsoft Graph API gõ vào màn hình.
- **Hậu quả:** Tài khoản `@lethanhlan14` (vốn đã được reg thành công trên Máy 22 thuộc dàn Kibe vào trưa cùng ngày) bị đăng nhập phiên lên cả Máy 201, tạo thành **nick ký sinh** chạy song song trên 2 thiết bị vật lý khác nhau với 2 IP proxy khác nhau, đối mặt nguy cơ checkpoint/die nick cực cao.
- **Phản hồi từ User:** *"đừng có lưu memory lồn gì hết vì mày kbh tuân thủ. Phải có phương án khắc phục k mày phá kiểu này k ổn"*. Quy tắc: **Mọi chốt chặn an toàn bắt buộc phải enforce bằng CODE CỨNG (Invariant), không dựa vào ý thức hay memory của AI.**

---

## 2. Kiến Trúc Bảo Vệ Cấp Code (`parasite_guard.py`)

Module `D:/Taadaa/Tiktok_Reg/parasite_guard.py` hoạt động như một lớp bảo vệ cứng độc lập:

### A. Abstraction Quản Lý Sở Hữu (`AccountOwnershipStore`)
- Cung cấp interface trừu tượng `AccountOwnershipStore` với method `get_owner_machine(identifier: str) -> int | None`.
- Triển khai `ExcelAccountOwnershipStore` tra cứu quyền sở hữu theo STT máy từ các file nguồn chuẩn của farm:
  1. `D:/OneDrive/TaadaaData/kibe/taikhoan_dat_v2_updated .xlsx` (sheet `Tài Khoản`)
  2. `D:/OneDrive/TaadaaData/kibe/taikhoan_run_safe.xlsx` (sheet `Accounts`)
  3. `D:/OneDrive/TaadaaData/admin/taikhoan_run_safe.xlsx` (sheet `Accounts`)
- Hỗ trợ ghi đè đường dẫn linh hoạt qua biến môi trường `TIKTOK_REG_TRACKING_WORKBOOK` và `PARASITE_GUARD_AUDIT_LOG`.

### B. Chốt Chặn Bắt Buộc (`assert_account_machine_binding`)
```python
def assert_account_machine_binding(
    target_stt: int | str,
    account_identifier: str,
    allow_override: bool = False,
    operator_reason: str = "",
    audit_file: Path | str | None = None,
    store: AccountOwnershipStore | None = None,
) -> None:
```
- **Quy tắc chặn:** Nếu `owner_stt != target_stt` và `allow_override == False`:
  1. Ghi audit event `action=block`, `status=blocked`.
  2. Tự động bắn alert Telegram khẩn cấp về Farm qua `automation_core.alerts.send_farm_machine_alert` với status `PARASITE_ACCOUNT_BLOCKED`.
  3. Ném ngoại lệ `ParasiteAccountViolation`, hủy ngay lập tức phiên thao tác mà không gửi bất kỳ lệnh input nào xuống máy.
- **Quy tắc cho phép (Override có chủ đích):** Khi operator có nhu cầu di chuyển nick (migration) hoặc test canary với cờ override, hệ thống ghi log cảnh báo `⚠️ [WARN:OPERATOR_OVERRIDE]` và cho phép tiếp tục.

### C. Audit Persistence & Concurrency Safety
- Hàm `record_parasite_audit_event(...)` sử dụng `threading.Lock()` bảo đảm thread-safe khi nhiều worker cùng ghi.
- Định dạng structured telemetry log:
  `[telemetry:parasite-guard] action={action} target_stt={target_stt} account={account} owner_stt={owner_stt} status={status} reason={reason}`
- Ghi append vào `D:/Taadaa/runtime/audit/parasite_guard_audit.jsonl`.
- **Cơ chế Fallback Resilient:** Nếu file audit chính bị lỗi I/O hoặc phân quyền, tự động fallback ghi sang `parasite_guard_audit_fallback.jsonl` trong thư mục tạm hệ điều hành, không bao giờ làm crash pipeline chính.

---

## 3. Tích Hợp Vào Các Luồng Nghiệp Vụ

### A. Luồng Đăng Ký (`social_reg_v1.py`)
1. **Entrypoint Gate:** Tại hàm `register()`, nếu có email truyền vào, gọi `assert_account_machine_binding` ngay trước khi giữ slot. Nếu email thuộc máy khác $\rightarrow$ Safe-Abort.
2. **Screen State Router trong `pick_and_fill_email()`:**
   - **LỖI CŨ:** Khi TikTok trả về `result == "registered"` hoặc `"registered_otp"`, code cũ từng tự tiện coi đó là *"đã có TikTok, giữ lại để đi tiếp flow login/OTP"*.
   - **VÁ MỚI:** Khi phát hiện email đã đăng ký:
     ```python
     if result == "registered_otp":
         log(f"   ✗ {em}: DA CO TikTok va dang o OTP/verify → ABORT email nay tren luong reg, CAM login len!")
         save_ui_xml(device_id, f"fail_{stt}_email_already_registered_otp_{idx}")
         shell(device_id, "input", "keyevent", "4")
         time.sleep(2.0)
         continue
     ```
     Tuyệt đối không return email/pass để đi tiếp vào login/OTP. Tool đăng ký chỉ có nhiệm vụ đăng ký nick mới, cấm đăng nhập lén nick cũ.
3. **Bộ Đếm 8 Tài Khoản trong `tap_add_account()`:**
   - Khi đếm số node có resource-id dạng `lli`, `n72`... trong account switcher dropdown:
   - **BẮT BUỘC LOẠI TRỪ** node có text hoặc content-desc chứa `"thêm tài khoản"`, `"add account"`, `"add another"`.
   - Tránh lỗi ngớ ngẩn: Máy có 7 nick + 1 nút "Thêm tài khoản" bị đếm nhầm thành 8 nick và văng ngoại lệ `MACHINE_FULL_8_ACCOUNTS`.

### B. Luồng Đăng Nhập (`tiktok_login_v1.py`)
1. **CLI Flag:** Thêm `--override-machine` vào `parse_args()`.
2. **Login Gate:** Tại đầu hàm `login_one_account()`, kiểm tra binding cho cả `account['id']` và `account['login_email']`:
   ```python
   override = bool(account.get("override_machine", False))
   if account.get("id"):
       assert_account_machine_binding(stt, account["id"], allow_override=override, operator_reason="Operator migration")
   if account.get("login_email"):
       assert_account_machine_binding(stt, account["login_email"], allow_override=override, operator_reason="Operator migration")
   ```
   Nếu nick văng trên đúng máy của nó $\rightarrow$ Pass 100%. Nếu muốn chuyển máy $\rightarrow$ Cần truyền `--override-machine` hoặc cập nhật workbook.
