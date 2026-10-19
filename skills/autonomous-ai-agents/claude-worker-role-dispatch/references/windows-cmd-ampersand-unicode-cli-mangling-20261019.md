# Windows CMD.EXE Argument Mangling với Ký Tự Ampersand (&) và Non-ASCII Unicode Trong NPM CLI Wrappers (19/10/2026)

## 1. Hiện Tượng & Triệu Chứng Lỗi
Khi điều phối Worker qua Single Dispatch Gateway (`dispatch_worker.py` -> `claude_worker.py`):
```bash
python D:/Taadaa/tools/dispatch_worker.py --workdir "D:/Taadaa/GPM auto" --file "scripts/run_oauth_s7_pipeline.py" '... URL https://accounts.google.com/ServiceLogin?flowName=GlifWebSignIn&flowEntry=ServiceLogin&hl=vi ...'
```
Lệnh lập tức thất bại với các triệu chứng sau:
1. Console in ra lỗi command của shell:
   ```text
   'flowEntry' is not recognized as an internal or external command,
   operable program or batch file.
   'hl' is not recognized as an internal or external command,
   operable program or batch file.
   ```
2. Worker Claude Haiku phản hồi prompt bị cắt cụt giữa chừng:
   ```text
   Your patch contract was also cut off after flowName=GlifWebSignIn, so the REPLACE WITH block was incomplete.
   ```
3. `dispatch_worker.py` bắt được cụm từ `is not recognized as an internal`, phân loại nhầm thành `ENV error` và dừng khẩn cấp (không fallback sang Agy CLI).
4. Tương tự, khi prompt chứa các ký tự Unicode như `✓`, `✗`, `•`, console cmd.exe báo lỗi:
   ```text
   '?' is not recognized as an internal or external command
   ```

## 2. Nguyên Nhân Gốc Rễ Kỹ Thuật (Root Cause)
1. **NPM Batch Wrapper trên Windows:**
   - Trên môi trường Windows, binary thực thi của Claude Code CLI là một batch shim: `C:\Users\Kibe\AppData\Roaming\npm\claude.cmd`.
   - Khi Python gọi `subprocess.run([claude, "-p", prompt_input])` trên Windows, hệ điều hành bắt buộc phải gọi `cmd.exe /c` để chạy file `.cmd`.
2. **Cơ Chế Phân Tích Lệnh Của CMD.EXE:**
   - `cmd.exe` trên Windows luôn thực hiện tiền xử lý (pre-parsing) toàn bộ dòng lệnh trước khi chuyển tham số vào script.
   - Ký tự `&` (Ampersand) là toán tử phân tách lệnh tuần tự trong Windows shell (`command1 & command2`). Dù tham số đã được bọc nháy trong Python `subprocess`, `cmd.exe` vẫn bóc nháy và ngắt chuỗi tại ký tự `&`, biến phần sau dấu `&` thành một lệnh shell độc lập (`flowEntry=...`).
   - Ký tự Unicode (non-ASCII) trong console codepage mặc định của Windows bị phân rã thành dấu chấm hỏi `?`. Trong cmd.exe, `?` là ký tự đại diện (wildcard) và khi đứng đầu câu lệnh sẽ bị coi là một command shell không hợp lệ.

## 3. Quy Tắc Phòng Tránh & Khắc Phục (Invariants)
1. **CẤM TUYỆT ĐỐI ký tự Ampersand (`&`) trong chuỗi Prompt truyền qua CLI:**
   - Trong text prompt: Dùng từ `and` hoặc dấu phẩy `,`, tuyệt đối cấm dùng `&`.
   - Trong URL ví dụ hoặc regex: Cắt gọn query string (dùng URL gốc `https://accounts.google.com/ServiceLogin?hl=vi` thay vì chuỗi dài nhiều tham số nối bằng `&`), hoặc mô tả bằng lời: "URL ServiceLogin với tham số hl bằng vi".
2. **CẤM ký tự Non-ASCII (Unicode Ticks / Bullets) trong chuỗi Prompt dòng lệnh:**
   - Thay `✓` bằng `SUCCESS` hoặc `v`.
   - Thay `✗` bằng `FAIL` hoặc `x`.
   - Thay bullet `•` bằng gạch đầu dòng `-`.
   - Giữ toàn bộ contract prompt ở định dạng thuần ASCII để đảm bảo an toàn 100% khi đi qua `cmd.exe`.
3. **Ưu tiên truyền Prompt qua File khi nội dung phức tạp:**
   - Đối với các patch contract lớn có chứa nhiều code mẫu phức tạp, lưu contract vào file tạm hoặc đọc trực tiếp thay vì nhồi chuỗi multiline phức tạp qua command line arguments.
