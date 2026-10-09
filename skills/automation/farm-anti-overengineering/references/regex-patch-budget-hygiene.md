# Regex Patching & Tool Budget Discipline on Windows Farm

## 1. Context & Trigger
Khi thực hiện patch contract có giới hạn ngân sách tool call nghiêm ngặt (ví dụ: budget <= 10-15 tool calls) trên các script Taadaa (Python/PowerShell), các lỗi escape chuỗi regex và syntax error có thể nhanh chóng làm cạn kiệt ngân sách vòng lặp của agent.

## 2. Các cạm bẫy thường gặp (Pitfalls)

### A. Patch Tool JSON Unescaping với `\r\n` và Windows Paths (`\runtime`)
- **Hiện tượng**:
  - Khi truyền `r"[^\r\n]+"` qua tham số JSON của `patch(mode='replace')`, ký tự `\r` (carriage return) có thể bị runtime JSON unescape thành byte 0x0D (literal CR/newline).
  - Đặc biệt nguy hiểm với đường dẫn Windows chứa thư mục bắt đầu bằng chữ `r` (ví dụ `r"D:\Taadaa\runtime\..."`): `\r` trước `untime` bị JSON parser giải mã thành carriage return `\x0D`, làm vỡ chuỗi thành 2 dòng (`D:\Taadaa` xuống dòng `untime`), gây ngay lập tức `SyntaxError: unterminated string literal`.
- **Hậu quả**: File Python bị ngắt dòng ngay giữa đường dẫn hoặc regex, làm hỏng cú pháp file.
- **Giải pháp**:
  - Khi dùng `patch`, phải double-escape backslash cho path: `r"D:\\Taadaa\\runtime\\..."`.
  - Tránh truyền literal `\r` qua tool parameters nếu không chắc chắn JSON serializer bảo toàn.
  - Khi code chứa các escape sequence phức tạp (`\r`, `\n`, `\s`) hoặc đường dẫn Windows nhạy cảm, nên dùng helper script qua `write_file` thay vì cố gắng patch nhiều lần qua `patch`.

### B. Python `re.sub()` Template Escape Trap (`bad escape \s`, `bad escape \T`)
- **Hiện tượng**:
  - Khi dùng Python script để thay thế đoạn code bằng `re.sub(pattern, replacement, text)`, hàm `re.sub` tự động parse chuỗi `replacement` theo cú pháp regex template (để xử lý backreferences như `\1`, `\g<name>`). Ký tự `\s` trong chuỗi code Python bị hiểu là regex escape không hợp lệ -> ném lỗi `re.error: bad escape \s`.
  - Tương tự trong regex pattern, đường dẫn Windows thô chứa `\T` (ví dụ `\Taadaa`) ném lỗi `re.error: bad escape \T`.
- **Giải pháp**:
  - Luôn ưu tiên dùng `str.replace(old, new, 1)` cho các đoạn code cố định thay vì `re.sub`.
  - Nếu bắt buộc dùng regex: dùng `re.escape(path)` cho pattern, và dùng callable trong `re.sub`: `re.sub(pattern, lambda m: replacement, text, count=1)`. Khi truyền callable lambda, Python không parse escape template trong chuỗi trả về.

### C. Windows CRLF (`\r\n`) Multiline String Match Trap
- **Hiện tượng**: File Python trên Windows thường lưu bằng CRLF (`\r\n`). Khi dùng Python script chạy qua bash terminal để `str.replace` đoạn code nhiều dòng, string literal trong script dùng LF (`\n`), dẫn đến `old_block in content` trả về `False` (hoặc `AssertionError: old not found`).
- **Giải pháp**:
  - Chuẩn hóa CRLF về LF trước khi thay thế:
    ```python
    is_crlf = "\r\n" in content
    content = content.replace("\r\n", "\n")
    content = content.replace(old_lf, new_lf)
    if is_crlf:
        content = content.replace("\n", "\r\n")
    ```

### C. Terminal Bash Quoting trên Windows (MSYS/Git-Bash)
- **Hiện tượng**: Gọi `python -c "..."` chứa single quotes lồng nhau hoặc newline trong bash terminal trên Windows dễ gây lỗi `unexpected EOF while looking for matching ''`.
- **Giải pháp**: Tạo file script tạm bằng `write_file`, thực thi bằng `terminal`, và xóa ngay sau khi chạy xong (`rm temp.py`).

## 3. Quy tắc bảo toàn Tool Budget
1. Nếu lệnh patch gặp lỗi cú pháp (SyntaxError do newline/escape), **dừng ngay việc thử lại mù quáng** với tool `patch`.
2. Tạo ngay một helper script Python chính xác bằng `write_file`, dùng `str.replace` hoặc `re.sub(..., lambda m: repl, ...)`.
3. Chạy helper script trong 1 turn duy nhất và dọn dẹp file tạm, tiết kiệm ít nhất 4-6 tool calls.
