# CRLF Diff Inflation & Strike 3 Reviewer Hand-off Execution

## 1. Cạm Bẫy Phình To Diff Do Ký Tự Xuống Dòng CRLF (CRLF Diff Inflation)

### 1.1 Hiện tượng (Symptom)
Sau khi Worker áp dụng patch một hàm nhỏ (~25 dòng) vào file script trên Windows, `git diff --numstat` hoặc diff trong `closeout_gate.py` đột ngột tăng vọt lên:
```text
1023    998    deploy/hermes-home/scripts/cron_gpm_gmail_nurture.py
```
Hậu quả: Reviewer AI của Closeout Gate từ chối duyệt (REJECT) ngay lập tức với nhận xét:
> *"Kiến trúc vẫn chứa rủi ro do file script bị thay đổi gần như toàn bộ (~1000 dòng thay đổi), trong khi chưa có bằng chứng regression suite rộng hơn ngoài một file test."*

### 1.2 Nguyên nhân gốc rễ (Root Cause)
- Repository Git trên Linux/cross-platform lưu trữ file với định dạng kết thúc dòng chuẩn **LF (`\n`)**.
- Các công cụ soạn thảo, Python file write hoặc patch engine trên môi trường Windows mặc định có thể ghi ra **CRLF (`\r\n`)**.
- Git coi toàn bộ các dòng có CRLF thay thế LF là dòng bị sửa đổi, khiến diff hiển thị toàn bộ nội dung file bị xóa và thêm lại, dù logic chỉ sửa vài dòng.

### 1.3 Quy tắc xử lý bắt buộc
Trước khi gọi `closeout_gate.py` hoặc tính `git diff --numstat`:
1. Kiểm tra diff với cờ bỏ qua khoảng trắng cuối dòng:
   ```bash
   git diff --ignore-space-at-eol --stat <file>
   ```
   Nếu diff thật sự chỉ vài chục dòng nhưng `--numstat` báo hàng nghìn dòng $\rightarrow$ file đã bị dính CRLF.
2. Chuẩn hóa ngay lập tức về LF:
   ```python
   from pathlib import Path
   p = Path("<file_path>")
   content = p.read_bytes()
   if b"\r\n" in content:
       p.write_bytes(content.replace(b"\r\n", b"\n"))
   ```
3. Sau khi chuẩn hóa, `git diff --numstat` sẽ trở về đúng kích thước O(1) thực tế.

---

## 2. Kỷ Luật Đường Dẫn Tuyệt Đối & Phân Vai Trong Strike 3 Reviewer Hand-off

### 2.1 Cạm bẫy đường dẫn tương đối khi gọi Claude CLI
- Khi Closeout Gate chạm ngưỡng 3 lần từ chối liên tiếp trên cùng `scope_hash`, cờ `[REVIEWER_HANDOFF_TRIGGERED]` được kích hoạt theo `HERMES_SUBAGENT_RULES.md`.
- Coordinator gọi Claude CLI bên trong thư mục repo con (ví dụ `workdir: D:/Taadaa/Hermes`).
- **Lỗi phổ biến:** Trong prompt giao việc cho Claude CLI, Coordinator viết lệnh tương đối `tools/closeout_gate.py` hoặc `closeout_gate.py`.
- **Hậu quả:** Claude CLI tìm kiếm trong repo `D:/Taadaa/Hermes/tools/` và kết luận:
  > *"không tìm thấy file này tồn tại thật (file được HERMES_SUBAGENT_RULES.md khai là canonical ở tools/closeout_gate.py, nhưng path đó không có trên máy này). Vì vậy tôi không thể chạy bước xác nhận..."*

### 2.2 Quy tắc điều phối chuẩn cho Strike 3
1. **Luôn dùng đường dẫn tuyệt đối:**
   Mọi công cụ hệ thống ngoài repo (như `closeout_gate.py`, `inspect_machine.py`, `evidence_gate_verifier.py`) BẮT BUỘC phải truyền đường dẫn tuyệt đối:
   `D:/Taadaa/tools/closeout_gate.py`
2. **Rõ ràng về vai trò tự nghiệm thu của Claude CLI:**
   - Trong cơ chế Strike 3 Reviewer Hand-off, **Claude CLI chính là Reviewer có quyền ghi (Reviewer-with-write-access)**.
   - Claude CLI tự đọc code, tự đọc lịch sử findings, tự vá code theo tiêu chuẩn của chính nó, và tự chạy focused pytest để xác nhận chất lượng.
   - Claude CLI không cần phải cố gắng chạy lệnh gate đệ quy lên chính nó nếu không cần thiết; sau khi Claude CLI hoàn tất và pass test, Coordinator sẽ kích hoạt lại `closeout_gate.py` để ghi nhận block audit chính thức.
