# Windows Subprocess Execution & Action Mandate Completeness (Reviewer Remediation)

## 1. Bối Cảnh Sự Cố & Thẩm Định Độc Lập (Claude Reviewer 58/100 FAIL)
Trong phiên làm việc ngày 2026-10-24, khi triển khai Action Mandate và xử lý lỗi khởi chạy binary `.cmd` trên Windows, bản vá đầu tiên đạt 56/56 unit test nhưng bị Claude Reviewer chấm **58/100 (REJECTED / FAIL)** vì hai lỗi kiến trúc:
1. Lỗ hổng Command Injection nghiêm trọng do sử dụng `shell=(os.name == "nt")` trong runner wrapper.
2. Action Mandate trong dispatch gate bị "nửa vời": lệnh thoát trong `required_action.command` chứa placeholder (`<repo>`, `<target>`, `<prompt>`), không thể copy-paste chạy ngay trong O(1), đồng thời text `message` mâu thuẫn với `required_action`.

---

## 2. Bẫy Tử Thần: `shell=True` Trên Windows & Lỗ Hổng Command Injection

### 2.1. Bản chất kỹ thuật của lỗi WinError 2
Khi gọi CLI binary trên Windows mà file thực thi là một batch script (`.cmd` hoặc `.bat` như `claude.cmd`), hàm `subprocess.run(cmd, shell=False)` sẽ ném lỗi:
```text
FileNotFoundError: [WinError 2] The system cannot find the file specified
```
Nguyên nhân: Windows CreateProcess API chỉ tự động nạp các file nhị phân `.exe`. Các file kịch bản `.cmd` và `.bat` bắt buộc phải được thông dịch bởi trình thông dịch lệnh `cmd.exe`.

### 2.2. Sai lầm chết người khi bật `shell=True`
Nhiều kỹ sư vội vã thêm `shell=(os.name == "nt")`. Đây là một lỗ hổng bảo mật nghiêm trọng vì:
1. **Lệch chuẩn Quoting của Python:** Hàm `subprocess.list2cmdline` của Python chỉ thực hiện escape theo quy chuẩn của C-Runtime (MSVC). Nó **HOÀN TOÀN KHÔNG ESCAPE** các metacharacter của `cmd.exe` như `&`, `|`, `<`, `>`, `^`, `%`.
2. **Command Injection Đã Được Chứng Minh (PoC):**
   Nếu đối số hoặc prompt chứa chuỗi:
   ```bash
   hello" & echo INJECTED_BY_SHELL & echo "x
   ```
   Dấu ngoặc kép `"` làm vỡ chuỗi quote của cmd.exe, và toán tử `&` khiến `cmd.exe` thực thi lệnh thứ hai `echo INJECTED_BY_SHELL` một cách độc lập!
   Vì worker chạy với cờ `--dangerously-skip-permissions`, bất kỳ chuỗi prompt injection nào từ git log, file lỗi hoặc dữ liệu không tin cậy đều có thể chiếm quyền điều khiển shell bên ngoài sandbox.
3. **Mở Rộng Biến Môi Trường Âm Thầm:**
   Chuỗi `100%COMPUTERNAME% done` bị cmd.exe mở rộng thành `100DESKTOP-3PFPGQC done`, làm sai lệch hoàn toàn ngữ nghĩa prompt của LLM.
4. **Giới Hạn Độ Dài Dòng Lệnh 8.191 Ký Tự:**
   `cmd.exe` có giới hạn cứng 8.191 ký tự cho toàn bộ command line. Prompt lớn gửi tới LLM qua CLI sẽ bị crash ngầm mà không có thông báo lỗi rõ ràng.

### 2.3. Giải pháp chuẩn mực (Safe Execution Without `shell=True`)
1. **Bảo tồn `shell=False`:** Tuyệt đối giữ nguyên `shell=False` cho mọi subprocess nhận input từ bên ngoài.
2. **Explicit Interpreter Invocation:** Nếu file binary kết thúc bằng `.cmd` hoặc `.bat`:
   ```python
   comspec = os.environ.get("COMSPEC", "cmd.exe")
   cmd = [comspec, "/c", target_bin, *args]
   subprocess.run(cmd, shell=False, ...)
   ```
3. **File/Stdin Payload Passing:** Với prompt dài hoặc chứa ký tự đặc biệt, không truyền qua CLI argument `-p "..."` mà ghi ra file tạm hoặc pipe qua `stdin`:
   ```python
   subprocess.run([target_bin, "-p", "-"], input=prompt_text, text=True, shell=False)
   ```

---

## 3. Quy Chuẩn Action Mandate Đầy Đủ (Anti-Placeholder Invariant)

### 3.1. Tác hại của Placeholder trong `required_action`
Khi một hook chặn thao tác của Coordinator và trả về:
```json
{
  "action": "block",
  "required_action": {
    "command": "python D:/Taadaa/tools/dispatch_worker.py --workdir <repo> [--file <target>] <prompt>"
  }
}
```
Các chuỗi `<repo>`, `<target>`, `<prompt>` là placeholder chết. Coordinator không thể copy-paste chạy ngay mà bắt buộc phải parse chuỗi, đoán mò đường dẫn và điền tham số. Nếu Coordinator đang trong trạng thái bối rối (cognitive strain), nó sẽ tiếp tục phạm lỗi hoặc rơi vào vòng lặp phân trần.

### 3.2. Tiêu chuẩn Nội Suy Hoàn Chỉnh (100% Interpolated Command)
Lệnh trong `required_action.command` BẮT BUỘC phải sẵn sàng chạy ngay trong O(1):
```python
target_arg = f' --file "{target_file}"' if target_file else ""
safe_goal = goal[:100].replace('"', '\\"').replace("\n", " ").strip()
cmd_mandate = f'python D:/Taadaa/tools/dispatch_worker.py --workdir "{os.getcwd()}"{target_arg} "{safe_goal}"'
```

### 3.3. Nhất Quán Giữa Message, Guidance và Required Action
Tránh tình trạng "trống đánh xuôi kèn thổi ngược":
- `message`: Nói rõ "Hãy thi công qua dispatch_worker.py (Single Gateway)".
- `guidance`: Giải thích lý do cấm delegate_task và hướng dẫn dùng dispatch_worker.py.
- `required_action.command`: Chứa đúng lệnh gọi dispatch_worker.py đã được nội suy.
- `required_action.description`: Mô tả chính xác hiệu quả khi chạy lệnh đó.
Tuyệt đối không để trường `message` nhắc công cụ này trong khi `required_action` lại đưa lệnh của công cụ khác.
