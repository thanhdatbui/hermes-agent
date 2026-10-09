# Quy Tắc Chống Nick Ký Sinh & Cấm Biến Tool Reg Thành Login Lén (Parasite Account Invariant)

## 1. Sự Cố Gốc & Bài Học Xương Máu
- **Hiện tượng**: Khi chạy test email `odessostuffen14@hotmail.com` trên Máy 201, màn hình TikTok trả về *"Bạn đã đăng ký"*. Coordinator ngộ nhận là *"mail cũ bị bên ngoài reg trước"*, rồi tự ý bấm *"Tiếp tục"* và lấy mã OTP từ Microsoft Graph API điền vào. TikTok đăng nhập thẳng tài khoản `@lethanhlan14` vào Máy 201.
- **Hậu quả nghiêm trọng**: Tài khoản `@lethanhlan14` thực chất đã được Farm reg thành công trên Máy 22 từ trưa. Thao tác trên biến nó thành **nick ký sinh (parasite account)** đăng nhập song song trên 2 thiết bị vật lý khác nhau (Máy 22 dàn Kibe và Máy 201 dàn Admin), có nguy cơ cực cao bị TikTok quét checkpoint / ban nick.
- **Nguyên nhân cốt tử**:
  1. Thiếu bước tra cứu Source of Truth (`taikhoan_dat_v2_updated .xlsx`) trước khi probe/test.
  2. Tool reg thiếu chốt chặn màn hình (Screen State Chokepoint), tự động chuyển tiếp từ reg sang login khi thấy email đã có tài khoản.
  3. Thiếu cơ chế kiểm tra ràng buộc cứng giữa tài khoản và thiết bị (Account-Machine Binding).

---

## 2. Kiến Trúc Phòng Vệ Cấp Code (`parasite_guard.py`)

Module `D:/Taadaa/Tiktok_Reg/parasite_guard.py` triển khai 3 lớp phòng vệ độc lập:

### A. Screen State Chokepoint trong `social_reg_v1.py`
Khi luồng đăng ký phát hiện email đã có tài khoản TikTok (`result in ("registered", "registered_otp")` hoặc fallback hints):
```python
if result == "registered_otp":
    log(f"   ✗ {em}: DA CO TikTok va dang o OTP/verify → ABORT email nay tren luong reg, CAM login len!")
    save_ui_xml(device_id, f"fail_{stt}_email_already_registered_otp_{idx}")
    shell(device_id, "input", "keyevent", "4")
    time.sleep(2.0)
    continue

if result == "registered":
    log(f"   ✗ {em}: DA CO tai khoan TikTok tren he thong → ABORT email nay tren luong reg, CAM login len!")
    save_ui_xml(device_id, f"fail_{stt}_email_already_registered_{idx}")
    shell(device_id, "input", "keyevent", "4")
    time.sleep(2.5)
    ...
    continue
```
👉 **BẮT BUỘC DỪNG NGAY (Abort)**, chụp ảnh lưu artifact, bấm BACK đưa máy về an toàn. **CẤM TUYỆT ĐỐI** bấm Tiếp tục hay bóc OTP từ Graph API để login lén vào máy khác.

### B. Hard Machine Binding (`assert_account_machine_binding`)
Trước khi thao tác bất kỳ tài khoản nào:
- Tra cứu STT máy sở hữu từ master tracking workbook (`taikhoan_dat_v2_updated .xlsx`, `taikhoan_run_safe.xlsx`).
- Nếu `owner_stt != target_stt` và không có cờ `allow_override` -> Ném ngay ngoại lệ `ParasiteAccountViolation`, chặn đứng hoàn toàn thao tác gõ phím / login.
- Tích hợp tại:
  - `tiktok_login_v1.py`: Kiểm tra cả `account['id']` và `account['login_email']`.
  - `social_reg_v1.py`: Kiểm tra `target_email` trước khi khởi chạy form reg.

### C. Structured Telemetry, Concurrency & Audit Fallback Persistence
- Ghi log định danh `[telemetry:parasite-guard] action=... target_stt=... account=... status=... reason=...`.
- Thread-safe: Sử dụng `_AUDIT_LOCK = threading.Lock()` để serialize mọi lượt ghi audit file đồng thời từ các threads.
- Persist toàn bộ audit events dạng JSONL vào `D:/Taadaa/runtime/audit/parasite_guard_audit.jsonl` (cấu hình qua env `PARASITE_GUARD_AUDIT_LOG`).
- Resilient Fallback: Khi primary audit storage gặp lỗi (PermissionError / disk / network drive), tự động fallback append vào `%TEMP%/parasite_guard_audit_fallback.jsonl`, không làm crash pipeline farm.
- Farm Alerting: Khi phát hiện vi phạm parasite account (nhánh block, non-override), tự động gửi Telegram alert `send_farm_machine_alert(machine=t_stt, script_name="ParasiteAccountGuard", status_text="PARASITE_ACCOUNT_BLOCKED")`.

### D. Kiến Trúc Abstraction (`AccountOwnershipStore`)
- Tách riêng interface `AccountOwnershipStore` và triển khai `ExcelAccountOwnershipStore` đọc các tracking workbooks (`taikhoan_dat_v2_updated .xlsx`, `taikhoan_run_safe.xlsx`).
- Hỗ trợ dynamic workbook path qua `os.environ.get("TIKTOK_REG_TRACKING_WORKBOOK")`.
- Top-level import hoisting: Luôn import `assert_account_machine_binding` ở đầu file (`social_reg_v1.py`, `tiktok_login_v1.py`), TUYỆT ĐỐI CẤM import động bên trong thân hàm (`login_one_account`, `register`) để tránh lỗi ImportError ngầm khi chạy batch.

---

## 3. Phân Định Rõ Ràng Nghiệp Vụ (Không Chặn Oan)

1. **Pool Auto (Batch)**:
   - Tool tự động bốc mail từ kho.
   - Bị chặn cứng 100% nếu mail/id đã thuộc máy khác trong tracking.
2. **Re-login nick bị văng (99% ca vận hành)**:
   - Chạy bằng tool chuyên dụng `python tiktok_login_v1.py <STT> --email <ID>`.
   - Vì account thuộc đúng STT máy đó, Guard kiểm tra `owner_stt == target_stt` -> **ALLOW 100% tự động**, không bao giờ bị nghẽn.
3. **Di chuyển máy có chủ đích (Migration)**:
   - Máy cũ hỏng, chuyển nick sang máy mới:
     + Cách 1: Cập nhật STT mới vào workbook tracking.
     + Cách 2: Dùng cờ `--override-machine` (ví dụ `python tiktok_login_v1.py <new_stt> --email <ID> --override-machine`). Guard cho phép và ghi nhận audit log rõ ràng.
4. **Canary Explicit (`--email`)**:
   - Lệnh canary test do Operator chỉ định: Guard ghi nhận cảnh báo `[WARN:OPERATOR_OVERRIDE]` và cho phép chạy tiếp, tuyệt đối không chặn nhầm canary của User.

---

## 4. Cạm Bẫy Đếm Số Lượng Nick Trên Switcher (TikTok v46+ & S7)
- **Hiện tượng**: Trên TikTok v46+ (đặc biệt S7 Android 8), nút *"Thêm tài khoản"* dùng chung `resource-id` (`com.ss.android.ugc.trill:id/lli`) với các dòng tài khoản trong Switcher RecyclerView.
- **Hậu quả**: Nếu đếm số node theo `resource-id` đơn thuần, máy có 7 nick thực tế + 1 nút "Thêm tài khoản" sẽ bị đếm thành 8 node $\rightarrow$ Tool ngộ nhận máy đã đầy 8 nick, văng lỗi `MACHINE_FULL_8_ACCOUNTS` và từ chối reg dù máy vẫn còn slot trống!
- **Invariant Fix**:
  ```python
  _acc_count = sum(
      1 for _n in _root.iter("node")
      if any(k in _n.attrib.get("resource-id", "") for k in ["n72", "lkp", "l9b", "lpw", "l_z", "lrq", "lli", "ndk"])
      and not any(x in (_n.attrib.get("text", "") + _n.attrib.get("content-desc", "")).lower() for x in ["thêm tài khoản", "add account", "add another"])
  )
  ```
  BẮT BUỘC loại trừ các node có text/desc chứa *"thêm tài khoản"*, *"add account"*, *"add another"* để bộ đếm phản ánh chính xác số tài khoản thực tế.
