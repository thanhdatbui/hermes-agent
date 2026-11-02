# Kỷ luật kiểm thử Live Command qua Remote SSH (Chống bẫy Mock Xanh ảo)

## 1. Bối cảnh & Bẫy "Mock xanh là tưởng chạy thật"
- Khi viết unit test cho các module gọi lệnh SSH từ xa sang máy phụ (như `admin_ssh.py` gọi sang Admin-PC):
  - Subagent thường dùng `@patch("subprocess.run")` hoặc mock trực tiếp output trả về.
  - Test suite báo pass 100%, nhưng thực tế trên môi trường chạy thật lệnh PowerShell lại bị chặn đứng bởi **Security Allowlist** (`COMMAND_NOT_IN_ALLOWLIST`, exit code 2).
  - Kết quả: Code release chạy ngầm hàng đêm lỗi liên tục nhưng không ai biết do tưởng test đã pass.

## 2. Nguyên tắc kiểm thử cơ học O(1) bắt buộc
- **BẮT BUỘC Live Probe 1 lệnh thực tế:** Khi sửa hoặc viết bất kỳ logic nào gọi lệnh qua `admin_ssh.py`, bắt buộc chạy 1 lệnh test live command thật qua `admin_ssh.py` sang `admin-farm` để kiểm tra exit code.
- **Tiêu chuẩn chấp thuận:**
  - `exit code == 0` (hoặc trả về payload thật).
  - Tuyệt đối CẤM nghiệm thu nếu lệnh bị `COMMAND_NOT_IN_ALLOWLIST` (exit code 2).
  - Không chấp nhận hoàn thành chỉ dựa vào kết quả mock unit test trong phòng thí nghiệm ảo.

## 3. Quy chuẩn câu lệnh PowerShell tương thích Allowlist
- `admin_ssh.py` kiểm tra token đầu tiên của lệnh PowerShell theo danh sách cho phép (`Get-`, `Set-`, `python`, `cat`...).
- **CẤM:** Mở đầu câu lệnh bằng gán biến `$var = ...` (ví dụ: `$min = ...; $items = ...`). Lệnh này sẽ bị parse token đầu là rỗng hoặc tên biến, dẫn đến bị chặn ngay tại cửa.
- **CHUẨN:** Mở đầu trực tiếp bằng cmdlet được cho phép:
  ```powershell
  # Đúng chuẩn - mở đầu bằng Get-Content:
  Get-Content (Get-ChildItem -Path 'D:\CodexRuntime\...\summary.json' -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -First 1).FullName -Raw -Encoding UTF8
  ```
