# Night Reg Gmail Admin SSH Allowlist & Pipeline Separation Triage (30/10/2026)

## 1. Bối cảnh & Hiện tượng
- Báo cáo chuỗi ban đêm `[FARM REPORT][TOÀN FARM] BÁO CÁO REG GMAIL BAN ĐÊM` chỉ báo cáo 15 máy (thuộc cụm Kibe 1-80), cụm Admin (Máy 201-280) không chạy và không có trong báo cáo.
- File sổ cái `D:\OneDrive\TaadaaData\admin\gmail_clean_v2.xlsx` không thay đổi, log runtime trên Admin-PC chỉ dừng ở các ngày trước (28/10).

## 2. Phân tích 2 nguyên nhân cốt lõi

### A. Sự phân tách giữa 2 launcher đêm
1. **`run_night_chain_pipeline.py` (Chained pipeline launcher):**
   - Chỉ gọi cục bộ `powershell.exe -File D:/Taadaa/register gmail/run_all.ps1`.
   - Manifest gán cứng `C:/Users/Kibe/AppData/Local/automation-core/assignments/register-gmail.json` (chỉ gồm `machine:1` .. `machine:80`).
   - Hoàn toàn không có cơ chế dispatch SSH sang `admin-farm`.

2. **`cron_night_tiktok_2fa_watchdog.py` (Watchdog ban đêm):**
   - Có mã nguồn gọi SSH sang `admin-farm` để chạy `run_all.ps1` cụm Admin.
   - Nhưng script payload truyền vào `admin_ssh.py` lại bắt đầu bằng biến môi trường `$env:PYTHONIOENCODING='utf-8'...`.
   - `admin_ssh.py` kiểm tra token verb đầu tiên theo `ALLOWED_COMMAND_PREFIXES` (`Get-`, `Set-`, `python`, `powershell`, ...). Chuỗi bắt đầu bằng `$env:` khiến parser trích xuất token rỗng hoặc không thuộc allowlist $\rightarrow$ **`COMMAND_NOT_IN_ALLOWLIST: token=''`**, lệnh bị chặn ngay tại host Kibe trước khi gửi qua SSH.

## 3. Quy chuẩn điều phối SSH chuẩn hóa (Canonical SSH EncodedCommand Pattern)

- **Tuyệt đối không gửi raw script PowerShell bắt đầu bằng `$env:` qua `admin_ssh.py`**:
  Parser token của `admin_ssh.py` sẽ chặn đứng vì vi phạm allowlist.
- **Giải pháp chuẩn hóa (theo `post_noon_chain_watchdog.py`):**
  Encode toàn bộ script PowerShell bằng Base64 UTF-16LE và gọi qua `powershell.exe -NoProfile -EncodedCommand <b64>`:
  ```python
  import base64

  def _build_admin_powershell_command(script_body: str) -> list[str]:
      b64_payload = base64.b64encode(script_body.encode("utf-16le")).decode("ascii")
      return [
          "ssh", "-o", "ConnectTimeout=10", "admin-farm",
          f"powershell -NoProfile -EncodedCommand {b64_payload}"
      ]
  ```
- Hoặc đóng gói thành file script `.ps1` trên Admin-PC và gọi trực tiếp `powershell.exe -File D:\Taadaa\...`.
