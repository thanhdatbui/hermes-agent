# Bash Shell Immunity (`shlex.join`), Native Binary Resolution & Decoupled Mandate Schema

## 1. Bối Cảnh Thực Tế & Lỗ Hổng Phát Hiện Qua Review Độc Lập (Claude Sonnet 100/100 Audit)

Trong quá trình chuẩn hóa Action Mandate và sửa các lỗ hổng điều phối, reviewer độc lập đã bóc trần 4 cạm bẫy bảo mật và kiến trúc nghiêm trọng:

### Bẫy 1: `subprocess.list2cmdline` Bị Thủng Trên Git-Bash / POSIX Shell
- **Hiện tượng:** Khi hook sinh ra lệnh `required_action.command` để Coordinator hoặc Agent chạy qua Git-Bash / MSYS2, nếu dùng `subprocess.list2cmdline(command_parts)`:
  - `list2cmdline` chỉ áp dụng quy tắc trích dẫn của MSVCRT trên Windows. Nó chỉ bọc nháy kép `"` khi token chứa khoảng trắng.
  - Nếu prompt không có khoảng trắng (ví dụ `a&calc`), `&` được in trần ra ngoài và trở thành toán tử nối lệnh của shell.
  - Ngay cả khi có khoảng trắng, chuỗi chỉ được bọc trong nháy kép `"..."`. Trong POSIX / Git-Bash, các ký tự `$var` và backtick `` `whoami` `` bên trong nháy kép **vẫn bị shell mở rộng và thực thi ngầm**!
- **Hậu quả:** Prompt do LLM sinh ra hoặc trích từ log/file chứa metacharacters có thể gây command injection hoặc làm sai lệch nội dung task.
- **Giải pháp Bất Biến:** BẮT BUỘC sử dụng `shlex.join(command_parts)`. `shlex.join` sử dụng nháy đơn `'...'` chuẩn POSIX, vô hiệu hóa hoàn toàn `$`, `` ` ``, `&`, `|`, `"`, bảo đảm 100% token được truyền nguyên vẹn vào `argv` của tiến trình con mà không bị shell can thiệp.

### Bẫy 2: Shim `.cmd` / `.bat` Kích Hoạt `cmd.exe` Dù Đã Tắt `shell=True`
- **Hiện tượng:** Khi gọi `claude` trên Windows, `shutil.which("claude")` ưu tiên trả về file shim của npm/winget (`C:\Users\...\claude.cmd`).
  - Dù `subprocess.run(cmd, shell=False)` đã tắt `shell=True`, hệ điều hành Windows khi thấy đuôi `.cmd` hoặc `.bat` vẫn bắt buộc phải gọi tiến trình `cmd.exe /c` ngầm để thông dịch file batch đó!
  - `cmd.exe` không tuân theo quy tắc escape của POSIX, dễ bị vỡ quote khi gặp `"` và ký tự `&`, đồng thời tự ý mở rộng biến môi trường `%VAR%`.
- **Giải pháp Bất Biến:** Trên Windows (`os.name == 'nt'`), BẮT BUỘC ưu tiên tìm nạp binary thực thi gốc `shutil.which("claude.exe")`. Nếu chỉ tìm thấy `.cmd` hoặc `.bat`, bắt buộc fail-fast báo lỗi `claude_cli_missing` và từ chối chạy qua shim batch file.

### Bẫy 3: Lệch Pha Đường Dẫn Giữa `--file` Tương Đối và `--workdir` Tuyệt Đối
- **Hiện tượng:** Khi hook trích xuất `candidate_file` từ nhãn `FILE: hooks/guard_x.py` (đường dẫn tương đối) và resolve `workdir` về git root (`D:/Taadaa/tools`), nếu hook đang chạy ở thư mục khác với git root, worker con nhận `--workdir D:/Taadaa/tools --file hooks/guard_x.py` sẽ phân giải sai đường dẫn file.
- **Giải pháp Bất Biến:** BẮT BUỘC gọi `Path(candidate_file).resolve()` ngay sau khi trích xuất để `--file` luôn là đường dẫn tuyệt đối, đồng bộ tuyệt đối với `--workdir` ở bất kỳ `cwd` nào.

### Bẫy 4: Lẫn Lộn Văn Xuôi Vào Trường `command` Của Action Mandate
- **Hiện tượng:** Với các nhánh chặn không có lệnh CLI chạy được (ví dụ: tạo file thiếu `FILE:`, điều tra thiếu `BUDGET:`), nếu nhét câu văn hướng dẫn tiếng Việt vào trường `command`, các công cụ tự động hóa đọc payload sẽ nhận nhầm văn xuôi là lệnh shell và cố chạy, gây crash cú pháp. Ngược lại, nếu để `command: ""` mà không có trường chỉ dẫn riêng, consumer in "LỆNH THOÁT O(1)" sẽ nhận chuỗi rỗng.
- **Giải pháp Bất Biến:** Chuẩn hóa schema Action Mandate tách bạch 2 trường:
  ```json
  {
    "action": "block",
    "rule_id": "<RULE_ID>",
    "message": "[<RULE_ID>] <reason>\nHƯỚNG DẪN: <guidance>\nCHỈ DẪN: <instruction>",
    "guidance": "<guidance>",
    "required_action": {
      "command": "",
      "instruction": "Bổ sung nhãn 'FILE: <đường_dẫn_tuyệt_đối>' vào context rồi dispatch lại.",
      "description": "..."
    }
  }
  ```
  Hàm helper `emit_block` bắt buộc `strip()` mọi trường và xác thực có ít nhất 1 trong 2 trường `(command, instruction)` không rỗng.

---

## 2. Tiêu Chuẩn Kiểm Thử Chống Regression (Verification Checklist)

1. **Test Bash Round-Trip Thật:** Chạy lệnh đề xuất qua `bash -c "<command>"` thật (nếu có bash) với script echo argv để kiểm chứng các ký tự `$HOME`, `` `whoami` ``, `&`, `"`, `'` đến được `sys.argv` nguyên vẹn 100%, không bị expand hay execute.
2. **Test Shims Rejection:** Monkeypatch `shutil.which` trả về `.cmd` $\to$ xác nhận worker từ chối chạy (`EXIT_NO_CLAUDE`), trả về `.exe` $\to$ chấp nhận và chạy với `shell=False`.
3. **Test Mandate Whitespace Robustness:** Truyền `command=None`, `command="   "` đi kèm `instruction` hợp lệ $\to$ xác nhận `emit_block` làm sạch thành `command: ""` và hiển thị `CHỈ DẪN:`, không văng `AttributeError`.
