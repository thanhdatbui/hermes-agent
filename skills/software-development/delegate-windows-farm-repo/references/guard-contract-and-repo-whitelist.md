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

## 3. Template Dispatch Chuẩn Mực & Bộ Quy Tắc Contract Guard Cho Task EDIT

Khi dispatch Worker thực hiện sửa code (`TASK_KIND: EDIT`), Coordinator Guard kiểm tra nghiệm ngặt 7 trường sau. Thiếu bất kỳ trường nào lệnh dispatch sẽ bị reject ngay lập tức:

### 7 Thành phần bắt buộc trong Context của Task EDIT:
1. `TASK_KIND: EDIT` (Bắt buộc).
2. `FILE: <<<\n<đường_dẫn_tuyệt_đối>\n>>>` (Bắt buộc nằm trong whitelist `['D:\\Taadaa']`, nên bọc trong `<<< ... >>>` để regex block parser trích xuất sạch sẽ, không đính kèm bullet point `- ` dính liền).
3. `OLD_STRING: <<< ... >>>` (Đoạn code gốc cần thay thế, bọc trong triple angle brackets `<<<` và `>>>`).
4. `NEW_STRING: <<< ... >>>` (Đoạn code mới thay thế, bọc trong triple angle brackets `<<<` và `>>>`).
5. `DIFF_BUDGET`: Tổng số dòng thay đổi dự tính BẮT BUỘC `<= 30 dòng`. Nếu vượt quá, guard sẽ báo `DIFF_BUDGET_EXCEEDED` và reject; phải chẻ nhỏ task thành các sub-task O(1).
6. `FOCUSED_TEST`: Bắt buộc đúng cú pháp chuẩn:
   - Dạng pytest: `FOCUSED_TEST: python -m pytest <file.py>::<test_node> -q` (LƯU Ý: `<file.py>` là đường dẫn tương đối, `<test_node>` là single test function/method identifier, CẤM lồng class `Class::test` vì regex parser chỉ nhận 1 cặp `::` với 1 identifier; không bọc nháy kép).
   - Hoặc dạng compile: `FOCUSED_TEST: python -m py_compile <file.py>` (đường dẫn file tương đối, ví dụ `python -m py_compile scripts/target.py`).
7. `FAIL_FAST`: Bắt buộc chứa câu lệnh Fail-Fast nguyên văn:
   `FAIL_FAST: Nếu trong <= 3 iterations đầu thấy scope bất khả thi với budget 15 calls thì DỪNG NGAY (ABORT) và trả về anchor + proposed contract, cấm đốt hết budget để mò file rồi fail im lặng.`

### Bẫy Bổ Sung (Tránh Reject Ngay Lập Tức):
- **Bẫy Monolith (`MONOLITH DISPATCH BLOCKED`):** CẤM dispatch worker sửa file monolith `*_smoke.py` cho popup (`COORDINATOR GUARD - MONOLITH DISPATCH BLOCKED`). Nếu phát hiện popup mới cần dismiss trên monolith, Coordinator phải dùng quyền Emergency Surgery (L2) xử lý trực tiếp O(1) (<= 15 dòng, 1 test focused <30s) hoặc đưa vào modular registry (`benign_popup_registry.py`).
- **Bẫy Closeout Gate & Sol Repair Fallback:**
  - Lệnh terminal chạy `closeout_gate.py` ở foreground bắt buộc `timeout <= 60s`.
  - Khi Reviewer trả về `< 85` (REJECTED, Strike 1 & 2), BẮT BUỘC chạy `sol_repair.py` độc quyền trước. Chỉ khi `sol_repair.py` exit != 0 / crash / validation fail mới được fallback dispatch Worker.
  - Reviewer thường trừ điểm các lỗi: quên đóng file (`wb.close()` trong `finally`), thiếu unit test độc lập cho nhánh retry/failure mới.

### Template Chuẩn Task EDIT (Copy & Điền):
```python
delegate_task(
    goal="Vá lỗi X trong D:/Taadaa/repo/file.py",
    context="""TASK_KIND: EDIT
FILE: D:/Taadaa/repo/scripts/target.py
OLD_STRING: <<<
        old_line_1
        old_line_2
>>>
NEW_STRING: <<<
        new_line_1
        new_line_2
>>>
FOCUSED_TEST: python -m py_compile scripts/target.py
FAIL_FAST: Nếu trong <= 3 iterations đầu thấy scope bất khả thi với budget 15 calls thì DỪNG NGAY (ABORT) và trả về anchor + proposed contract, cấm đốt hết budget để mò file rồi fail im lặng.

Repo working directory: D:/Taadaa/repo
""",
    role="leaf"
)
```
