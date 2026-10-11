# Guard Contract & Scope Lock Rules khi Dispatch Worker trên Taadaa Farm

Tài liệu này tổng hợp các bẫy thực tế và quy tắc hợp lệ khi Coordinator phát lệnh `delegate_task` trên môi trường Taadaa Farm (Windows) để không bị vi phạm Coordinator Guard.

---

## 1. Scope Lock & Repo Whitelist Invariants

Khi dispatch Worker thực hiện task EDIT / FIX:

### Bẫy 1: Target nằm ngoài Whitelist (`OUT OF REPO WHITELIST`)
- **Lỗi thực tế:** `OUT OF REPO WHITELIST: File 'D:\OneDrive\TaadaaData\kibe\Tik4.xlsx' nằm ngoài whitelist ['D:\Taadaa']!`
- **Nguyên nhân:** Guard chỉ cho phép Scope Lock nhắm vào các file nằm trong repo whitelist (mặc định là `['D:\\Taadaa']`). Các file cấu hình/data bên ngoài như `D:/OneDrive/...` không được đưa trực tiếp vào `FILE: ...` của Scope Lock.
- **Giải pháp:**
  - Scope Lock bắt buộc trỏ vào một script/tool nằm trong `D:/Taadaa/` (ví dụ `FILE: D:/Taadaa/tools/...` hoặc `FILE: D:/Taadaa/scripts/...`).
  - Worker sẽ thực thi thông qua script đó để đọc/ghi file bên ngoài (kèm backup `.bak` và verify).

### Bẫy 2: Thiếu thẻ FILE tuyệt đối (`EDIT_MISSING_FILE` & `PATH_NOT_ABSOLUTE`)
- **Lỗi thực tế 1:** `EDIT_MISSING_FILE: Task EDIT bắt buộc có 'FILE: <đường_dẫn_tuyệt_đối>' (SCOPE LOCK MISSING TARGET FILE)`.
- **Lỗi thực tế 2:** `PATH_NOT_ABSOLUTE: '- D:\OneDrive\TaadaaData\kibe\Tik4.xlsx' không phải đường dẫn tuyệt đối`.
- **Nguyên nhân:**
  - Task edit bắt buộc khai báo rõ ràng `SCOPE LOCK:` kèm dòng `FILE: <đường_dẫn_tuyệt_đối>`.
  - Trong phần context/prompt, nếu viết gạch đầu dòng ngay trước đường dẫn (ví dụ `- D:/...`), bộ parser regex có thể bốc cả dấu `- ` thành token đường dẫn, dẫn đến không nhận diện được đường dẫn tuyệt đối chuẩn.
- **Giải pháp:**
  - Luôn ghi đường dẫn tuyệt đối sạch sẽ, không đính kèm bullet point `- ` dính liền:
    ```markdown
    SCOPE LOCK:
    FILE: D:/Taadaa/tools/update_tik_hashtags.py
    ```

### Bẫy 3: Quá số lượng file trong 1 task (`MULTI_FILE_VIOLATION`)
- **Lỗi thực tế:** `MULTI_FILE_VIOLATION: Phát hiện 3 files trong 1 task. Tối đa <= 2 files (1 file nghiệp vụ + 1 file test). Bắt buộc chẻ nhỏ task!`
- **Quy tắc cứng:** Mỗi subagent task chỉ được phép chứa tối đa 2 file trong Scope Lock (1 file nghiệp vụ + 1 file test). Nếu cần sửa nhiều file hơn, bắt buộc phải phân rã thành các task tuần tự hoặc bọc qua 1 entrypoint script duy nhất.

---

## 2. Ngân Sách T1 Coordinator & Kỷ Luật Không Viết Script Rác

- **Giới hạn T1 Coordinator:** Tối đa 5 files, <= 200 dòng cộng dồn cả session (`COORDINATOR WRITE DENIED`).
- Khi cần inspect / query data từ SQLite hoặc Excel:
  - Tận dụng các script/tool canonical có sẵn trong `D:/Taadaa/tools/` (ví dụ `inspect_machine.py`).
  - Dùng `python -c` với các lệnh read-only đơn giản, truyền `timeout <= 60s` để tránh `GUARD_FOREGROUND_TIMEOUT_MISSING`.
  - Tuyệt đối không viết tràn lan các file test tạm (`inspect_*.py`, `check_*.py`) làm cạn kiệt budget T1 trước khi đến bước sửa lỗi chính.

---

## 3. Template Dispatch Chuẩn Mực Cho Worker Thao Tác Dữ Liệu

Khi cần thao tác cập nhật cấu hình hoặc dữ liệu farm:

```python
delegate_task(
    goal="Sua D:/Taadaa/tools/sync_worker.py de cap nhat hashtag kenh",
    context="""SCOPE LOCK:
FILE: D:/Taadaa/tools/sync_worker.py

Yeu cau:
1. Doc file Excel/DB can xu ly, tao ban sao luu .bak truoc khi ghi.
2. Cap nhat chinh xac du lieu theo spec.
3. Verify lai noi dung sau khi ghi va in ra evidence ro rang.
Budget: <= 5 tool calls.
""",
    role="leaf"
)
```
