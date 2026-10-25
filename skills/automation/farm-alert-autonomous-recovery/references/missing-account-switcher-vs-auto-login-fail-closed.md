# Missing Account on Multi-Account Switcher: Triage, Fail-Closed Architecture & Reconcile Recovery

## 1. Hiện Tượng & Câu Hỏi Thường Gặp
Khi chạy batch Feed / Upload Hook, hệ thống phát cảnh báo P0:
```text
UploadHook: [ERROR] scripts.tiktok_workflow.state_machine: [ACCOUNT_SWITCHER_FAILED] select account failed: ACCOUNT_MISSING: expected account was not found. Cần MANUAL_REVIEW...
```
Người vận hành thường thắc mắc: *"Thiếu acc sao runner không tự gọi script TikTok Login để đăng nhập bù vào máy luôn?"*

## 2. Ba Điểm Nghẽn Kỹ Thuật Khiến Runner Không Tự Động Login Bù

### A. State Machine chỉ kích hoạt login khi máy "trắng acc" (0 account)
- Trong `scripts.tiktok_workflow.state_machine.py`:
  - `_fail_account_switcher()` chỉ gán `recovery_handler = "tiktok_login"` nếu cờ `context.is_no_account_login_required` được bật.
  - Cờ này được quyết định bởi `_is_no_account_login_surface()`: bắt buộc XML phải chứa chuỗi *"đăng nhập vào tài khoản hiện có"* / *"log in to an existing account"*.
  - Khi máy đã có sẵn một số account (ví dụ 7/8 account trên M211), giao diện hiển thị là bottom-sheet *Chuyển đổi tài khoản* chứa 7 username. Điều kiện trắng acc không thỏa mãn -> State machine xếp vào `ACCOUNT_SWITCHER_FAILED: ACCOUNT_MISSING` -> trạng thái cuối cùng là `MANUAL_REVIEW`, **hoàn toàn không emit `LOGIN_RECOVERY_REQUIRED`**.

### B. Cấu hình Admin để trống lệnh handler (`config-admin.yaml`)
- Trong `D:/Taadaa/Tiktok-video/config-admin.yaml`:
  ```yaml
  login_recovery_command: []
  ```
- Dù state machine có emit cờ login recovery thì `login_recovery.py` vẫn trả về `LOGIN_RECOVERY_NO_HANDLER` (exit code 3) do danh sách lệnh đang rỗng.

### C. Chốt chặn Fail-Closed trong Batch Runner (`run_tiktok_upload_batch.ps1:483-488`)
- Ngay cả khi worker trả về `LOGIN_RECOVERY_REQUIRED`, batch runner PowerShell có chốt chặn an toàn:
  ```powershell
  if ($report.status -eq 'LOGIN_RECOVERY_REQUIRED') {
      Write-Host "Máy $runner.Machine: LOGIN_RECOVERY_REQUIRED; dừng fail-closed, không tự recovery/requeue."
  }
  ```
- **Lý do thiết kế:** Ca nuôi/upload chạy song song trên hàng chục máy (fleet 79 máy). Đăng nhập tài khoản mới trên TikTok dễ bị kích hoạt Captcha ghép hình xoay vòng hoặc OTP Email/SMS, gây chiếm giữ thiết bị 10–15 phút làm nghẽn toàn batch. Hơn nữa, thao tác login mới bất thường trong phiên feed có rủi ro bị hệ thống bảo mật TikTok đánh giá bất thường (Device Suspect) làm văng checkpoint liên đới các nick còn lại trên máy.

## 3. Quy Trình Nạp Bù Tài Khoản Đúng Chuẩn (Actionable Reconcile Flow)
Để nạp nick còn thiếu vào slot trống của thiết bị mà không ảnh hưởng đến batch đang chạy:

1. **Sử dụng công cụ Reconcile chuyên dụng:**
   Script chuẩn: `D:/Taadaa/tiktok-log-in/scripts/reconcile_tiktok_accounts.py` (dùng engine `login_runner.account_reconcile` kết nối `Tiktok_Reg`).

2. **Cú pháp lệnh nạp bù 1 máy cụ thể (ví dụ M211 thiếu nick khanhcoi6114):**
   ```bash
   python D:/Taadaa/tiktok-log-in/scripts/reconcile_tiktok_accounts.py \
       --workbook "D:/OneDrive/TaadaaData/admin/taikhoan_run_safe.xlsx" \
       --machines 211 \
       --expected-username khanhcoi6114 \
       --adb-path "C:/Program Files (x86)/xiaowei/tools/adb.exe" \
       --login-project "D:/Taadaa/Tiktok_Reg" \
       --allow-live-reconcile
   ```

3. **Nguyên lý thực thi an toàn:**
   - Script tự động đối soát nick trong workbook với UI Switcher thực tế trên máy.
   - Bấm "Thêm tài khoản", thực hiện flow login có proxy xoay và giải mã IMAP OTP độc lập.
   - Sau khi login thành công, verify lại Switcher có đủ 8 slot trước khi nhả device lock.
