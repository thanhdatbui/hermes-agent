# Windows Subprocess CLI Prompt Truncation & Worker Tool Parity Quirks

## 1. Bẫy Cắt Cụt Prompt do Ký Tự Ngắt Dòng `\n` trên Windows Subprocess

### Triệu chứng
Khi gọi `claude -p <prompt>` qua `subprocess.run(shell=False)` trên Windows:
- Ký tự `\n` trong chuỗi prompt khiến argument parser cắt cụt toàn bộ nội dung phía sau dòng đầu tiên.
- Prompt truyền vào:
  ```text
  Target file: D:/Taadaa/tools/watchdog_smart.py\n\nNhiệm vụ: Cập nhật hàm A, B, C...
  ```
- Binary `claude` chỉ nhận được:
  ```text
  Target file: D:/Taadaa/tools/watchdog_smart.py
  ```
- Worker đọc file xong nhưng không thấy nhiệm vụ nên trả lời:
  *"The file exists, but your message names only the file and no task. What do you want done with it?"*

### Khắc phục chuẩn
BẮT BUỘC flatten toàn bộ chuỗi prompt thành một dòng duy nhất (thay thế ngắt dòng bằng khoảng trắng) trước khi truyền vào mảng lệnh:
```python
prompt_input = " ".join(build_prompt(args.prompt, args.file).splitlines()).strip()
cmd = [claude, "-p", prompt_input, ...]
```

---

## 2. Bẫy Khóa Quyền Bất Đối Xứng Khiến Worker Bị Tê Liệt

### Vấn đề
- Nếu worker được giao nhiệm vụ: "Sửa file X và chạy `python -m py_compile X` để kiểm tra", nhưng wrapper lại áp đặt:
  ```python
  cmd += ["--disallowedTools", "Write,Bash,NotebookEdit,..."]
  ```
- Worker bị tước quyền `Bash`, dẫn đến việc không thể thực thi lệnh kiểm chứng theo yêu cầu của prompt.
- Thấy yêu cầu verify nhưng không có công cụ, worker sẽ rơi vào trạng thái bối rối, dừng lại hỏi người dùng thay vì hành động.

### Khắc phục
- Cung cấp cờ `--allow-bash` cho worker khi có yêu cầu kiểm tra hoặc chạy test focused:
  ```python
  if args.allow_bash:
      allowed_tools = "Read,Edit,Bash" if target_path else "Read,Edit,Write,Bash"
  ```
- Đảm bảo công cụ cấp cho worker tương thích hoàn toàn với các bước hành động được yêu cầu trong prompt.

---

## 3. Cơ Chế Tra Cứu Quota Live từ OmniRoute (:20129) cho Agy CLI Pool

### Vấn đề
- Nếu worker pool (như `ag_cli.py`) duyệt tuần tự danh sách tài khoản cục bộ mà không tra cứu trạng thái quota thời gian thực, nó sẽ liên tục gắp các tài khoản đang dính 429 Resource Exhausted, gây lặp jitter và thất bại hàng loạt.

### Khắc phục chuẩn
- Truy vấn trực tiếp live cache từ OmniRoute:
  - `GET http://127.0.0.1:20129/api/providers` để map `connection_id` $\leftrightarrow$ `email`.
  - `GET http://127.0.0.1:20129/api/usage/provider-limits` để lấy `remainingPercentage` theo model family pool (`gemini-3.1-flash-lite` / `gemini-3.7-flash-tiered`).
- Loại bỏ hoàn toàn các account có `remainingPercentage <= 0.0` hoặc `is_exhausted = True`.
- Sắp xếp thứ tự ưu tiên gắp account theo `remainingPercentage DESC` trước khi fallback sang LRU.
