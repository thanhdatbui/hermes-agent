# Antigravity VM Rescue & OmniRoute Quota Pitfalls

Kinh nghiệm xử lý tài khoản Antigravity Pro dính Google 403 `VALIDATION_REQUIRED` ("Verify your account to continue") qua VMware Workstation (`ag-onboard.vmx`).

---

## 1. Lỗi vmrun `deleteFileInGuest` bị Access Denied do thuộc tính ReadOnly

- **Triệu chứng**:
  ```text
  RuntimeError: deleteFileInGuest failed, exit code 4294967295
  vmrun: Error: You do not have access rights to this file
  ```
- **Nguyên nhân**: File kit trong VM baseline (`C:\ag-kit\sing-box\config-*.json`) mang cờ thuộc tính ReadOnly (`attrib +r` / `Attributes: ReadOnly, Archive`). Lệnh `deleteFileInGuest` của vmrun dùng API Win32 `DeleteFileW` thuần nên bị từ chối quyền truy cập (Access Denied).
- **Khắc phục triệt để**:
  Thay vì gọi `deleteFileInGuest`, dùng PowerShell trong guest với cờ `-Force` để xoá file trước khi copy:
  ```python
  vmrun_guest(
      "runProgramInGuest", VMX,
      r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe",
      "-ExecutionPolicy", "Bypass", "-Command",
      f"if (Test-Path -LiteralPath '{guest_path}') {{ Remove-Item -LiteralPath '{guest_path}' -Force }}"
  )
  vmrun_guest("copyFileFromHostToGuest", VMX, local_path, guest_path)
  ```

---

## 2. Lỗi Timeout 15s khi bật TUN trong Guest (`start-tun2.ps1`)

- **Triệu chứng**:
  ```text
  RuntimeError: guest script C:\vm_run_tun_5111.ps1 failed, exit code 4294770688
  ```
- **Nguyên nhân**: Script `start-tun2.ps1` kiểm tra IP gốc qua `curl`, khởi động sing-box service, sleep 2s và kiểm tra lại IP mới qua proxy. Quá trình này mất từ 18–25 giây. Việc gọi `vmrun runProgramInGuest` với `timeout=15` mà không có cờ `-noWait` khiến tiến trình bị kill và ném mã lỗi timeout, mặc dù thực tế TUN đã bật thành công và IP đã chuyển sang proxy.
- **Khắc phục**:
  Chạy wrapper qua `runProgramInGuest` với cờ `-noWait`, hoặc nâng timeout lên `>= 60s`, sau đó poll file log `C:\tun_<port>_log.txt` từ host để xác nhận dòng `OK - toan bo VM dang di qua proxy`.

---

## 3. Cạm bẫy OmniRoute Model Cooldown Cache gây chẩn đoán sai BLOCKED vs QUOTA_EXHAUSTED

- **Hiện tượng**: Tài khoản thực tế bị Google chặn 403 `VALIDATION_REQUIRED` nhưng script quét `scan_pro_accounts.py` lại báo `QUOTA_EXHAUSTED`.
- **Nguyên nhân**:
  - `isolated_chat_test` mặc định gửi request test tới model `antigravity/gemini-3.8-flash-tiered`.
  - Nếu trước đó model này vừa bị lỗi hoặc dính rate limit trên OmniRoute, OmniRoute kích hoạt cơ chế cooldown nội bộ (`credentials_cooling: 1`, `code: model_cooldown`, `reset_seconds: 450`).
  - Request test bị OmniRoute chặn ngay ở tầng proxy và trả về `429`, khiến classifier ngộ nhận là tài khoản hết quota bình thường thay vì bị Google khoá.
- **Khắc phục**:
  - Kiểm tra `GET /api/usage/provider-limits` mục `caches[<connectionId>].quotas` để xem tỷ lệ quota còn lại của tài khoản (`remainingPercentage`).
  - Nếu quota vẫn còn (ví dụ `gemini-3.7-flash-tiered` còn > 10%) mà test 3.8 bị cooldown, test chéo ngay với model `antigravity/gemini-3.7-flash-high` để bóc trần lỗi 403 `Verify your account to continue` thật sự từ Google upstream.
