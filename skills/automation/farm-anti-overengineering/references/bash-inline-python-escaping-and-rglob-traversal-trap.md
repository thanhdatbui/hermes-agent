# Bash Inline Python Escaping Mangling & Path.rglob() Windows Traversal Pitfalls

## 1. Sự cố Bash Inline `python -c` làm gãy Regex và Path (`\r\n`, `\t`)
### Hiện tượng
Khi sửa file qua terminal bằng inline script:
```bash
python -c '
...
new_code = """
m = re.search(r"Artifacts:\s*([^\r\n]+)", output)
p = Path(r"D:\Taadaa\tiktok-luot nuoi acc")
"""
...
'
```
Trong môi trường Git Bash / MSYS trên Windows:
- Ký tự `\r\n` trong regex `[^\r\n]+` bị bash unescape thành newline thật $\rightarrow$ vỡ regex thành 2 dòng:
  ```python
  m = re.search(r"Artifacts:\s*([^
  ]+)", output)
  ```
  Dẫn đến `SyntaxError: unterminated string literal`.
- Chuỗi `\t` trong đường dẫn `r"D:\Taadaa\tiktok-..."` bị bash unescape thành tab character thật (`D:\Taadaa\t...`) làm hỏng đường dẫn thư mục.

### Quy tắc phòng tránh
1. **Ưu tiên tuyệt đối công cụ `patch`:** Dùng tool `patch` có sẵn của agent với chuỗi thuần, không bao giờ đẩy code chứa regex phức tạp hoặc backslash Windows qua `python -c` trong terminal.
2. **Nếu bắt buộc dùng Python script trong terminal:**
   - Tuyệt đối không dùng string template trực tiếp chứa `\r`, `\n`, `\t`.
   - Sử dụng raw file payload hoặc base64 decode:
     ```python
     import base64
     code = base64.b64decode(b"...").decode("utf-8")
     ```
   - Luôn chạy `python -m py_compile <file>` ngay lập tức để bắt lỗi cú pháp nếu có.

---

## 2. Bẫy `Path.rglob()` trên Repo chứa thư mục Runs (`.ai-runs`, `runs`)
### Hiện tượng
Khi tìm kiếm file trong repo farm:
```python
for py in p.rglob("*.py"):
    if ".ai-runs" in str(py): continue
```
Dù code có lệnh `if ... in str(py): continue`, hàm `Path.rglob()` của Python vẫn duyệt đệ quy qua toàn bộ cây thư mục vật lý trên ổ cứng trước khi yield file. Trên ổ cứng Windows chứa hàng vạn file artifacts/logs, lệnh này bị treo I/O và dính timeout cứng 900s (15 phút), làm cạn kiệt ngân sách lượt gọi và đơ phiên.

### Quy tắc cưỡng chế
1. **CẤM TUYỆT ĐỐI `Path.rglob()` hoặc `os.walk()` trên root repo farm:**
   - Chỉ dùng non-recursive glob: `p.glob("*.py")` hoặc `(p / "scripts").glob("*.py")`.
2. **Chỉ định trực tiếp file flow đã biết:**
   - Tra cứu O(1) qua các file scripts quy ước: `scripts/run_night_chain_pipeline.py`, `scripts/run-feed-session.ps1`, `run_batch_live_2fa.py`.
