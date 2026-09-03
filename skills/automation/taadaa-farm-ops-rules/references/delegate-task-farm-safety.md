# Delegate-Task Farm Safety Guard

## Pitfall: Subagent không bị ràng buộc bởi farm safety rule nếu coordinator truyền context sai

**Sự cố (03/09/2026):** Coordinator dispatch `delegate_task` để fix alert Máy 74, nhưng
context truyền cho subagent mô tả lệnh `grep -rn`, `os.walk`, hoặc quét thư mục rộng.
Subagent không biết rule farm safety, nên thực thi quét đĩa — vi phạm quy tắc.

## Checklist trước khi dispatch delegate_task cho farm fix

Trước khi gọi `delegate_task` để xử lý alert `[MÁY N]`:

1. **Đọc lại context sẽ truyền cho subagent.**
2. **Kiểm tra context KHÔNG chứa:**
   - `grep -r`, `grep -rn`
   - `find /path -name`
   - `os.walk`
   - `glob(recursive=True)`
   - Bất kỳ lệnh quét đĩa diện rộng nào
3. **Thay thế bằng:**
   - `python D:/Taadaa/tools/inspect_machine.py <N>` — lấy hiện trường máy N
   - Lệnh ADB trực tiếp theo serial: `adb -s <serial> shell ...`
   - `git grep -n "pattern" path/to/specific/file.py` — chỉ tìm trong file cụ thể
4. **Truyền đường dẫn file cụ thể** thay vì thư mục:
   - ✅ `context_file: python_runner/flows/benign_popup.py`
   - ❌ `context: tìm file liên quan trong python_runner/`

## Quy tắc root cause thật

Khi user hỏi "vì sao lỗi", phân tích bằng:
1. XML hiện trường từ `inspect_machine.py`
2. `git grep -n "function_name" path/to/file.py`
3. `read_file` trực tiếp vào file nghi vấn

KHÔNG dispatch subagent chỉ để "đi tìm file nghi vấn" — đó là nhiệm vụ của coordinator.
