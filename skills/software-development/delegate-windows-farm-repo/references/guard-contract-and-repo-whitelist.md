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

### Bẫy 2: Thiếu thẻ FILE tuyệt đối (`EDIT_MISSING_FILE` & `PATH_NOT_ABSOLUTE` & `MISSING_TASK_KIND`)
- **Lỗi thực tế 1:** `EDIT_MISSING_FILE: Task EDIT bắt buộc có 'FILE: <đường_dẫn_tuyệt_đối>' (SCOPE LOCK MISSING TARGET FILE)`.
- **Lỗi thực tế 2:** `PATH_NOT_ABSOLUTE: '- D:\OneDrive\TaadaaData\kibe\Tik4.xlsx' không phải đường dẫn tuyệt đối`.
- `MISSING_TASK_KIND: Bắt buộc khai báo 'TASK_KIND: EDIT' hoặc 'TASK_KIND: INVESTIGATE' trong context (SCOPE LOCK MISSING TARGET FILE)`.
- *Lưu ý về TASK_KIND:* Có 3 task kinds hợp lệ:
  * `TASK_KIND: EDIT` (bắt buộc kèm `FILE: ...`, `OLD_STRING: <<< ... >>>`, `NEW_STRING: <<< ... >>>`).
  * `TASK_KIND: CREATE` (dùng khi tạo file mới hoàn toàn, KHÔNG yêu cầu `OLD_STRING`/`NEW_STRING`, nhưng vẫn bắt buộc có `FILE: <<< <đường_dẫn_tuyệt_đối> >>>` và `FOCUSED_TEST: ...`).
  * `TASK_KIND: INVESTIGATE` (dùng cho task chỉ đọc/khảo sát, cấm sửa code).
- **Lỗi thực tế 4:** `PATH_NOT_ABSOLUTE: '- Goal: Ghi đè toàn bộ nội dung file D:\Taadaa\tools\...' không phải đường dẫn tuyệt đối`.
- **Nguyên nhân:**
  - Mọi task dispatch bắt buộc khai báo rõ ràng `TASK_KIND: EDIT` hoặc `TASK_KIND: INVESTIGATE` ngay đầu context.
  - Task edit bắt buộc khai báo rõ ràng `SCOPE LOCK:` kèm dòng `FILE: <đường_dẫn_tuyệt_đối>`.
  - Trong phần context/prompt, nếu viết gạch đầu dòng ngay trước đường dẫn (ví dụ `- D:/...` hoặc `- Goal: sửa file D:/...`), bộ parser regex của guard quét toàn bộ context tìm token đường dẫn và bốc cả câu dính dấu gạch đầu dòng `- `, dẫn đến fail kiểm tra `os.path.isabs()` và văng `PATH_NOT_ABSOLUTE`.
- **Giải pháp:**
  - Luôn ghi đường dẫn tuyệt đối sạch sẽ, bọc trong triple angle brackets `<<<` và `>>>`:
    ```markdown
    TASK_KIND: EDIT
    FILE: <<<
    D:/Taadaa/tools/update_tik_hashtags.py
    >>>
    ```
  - Trong các câu mô tả khác trong context, KHÔNG viết đường dẫn tuyệt đối gắn liền sau dấu bullet point `- `. Dùng tên file tương đối hoặc tách dòng.
  - Khi Coordinator hết ngân sách T1 (`COORDINATOR WRITE DENIED`), giải pháp duy nhất để chạy tác vụ mới là dispatch Worker qua `delegate_task` với `TASK_KIND: CREATE` và bọc trong `FILE: <<< D:/Taadaa/... >>>`. CẤM cố gắng gọi write_file tiếp trong phiên chính.

### Bẫy 3: Quá số lượng file trong 1 task (`MULTI_FILE_VIOLATION`)
- **Lỗi thực tế:** `MULTI_FILE_VIOLATION: Phát hiện 3 files trong 1 task. Tối đa <= 2 files (1 file nghiệp vụ + 1 file test). Bắt buộc chẻ nhỏ task!`
- **Quy tắc cứng:** Mỗi subagent task chỉ được phép chứa tối đa 2 file trong Scope Lock (1 file nghiệp vụ + 1 file test). Nếu cần sửa nhiều file hơn, bắt buộc phải phân rã thành các task tuần tự hoặc bọc qua 1 entrypoint script duy nhất.

### Bẫy 4: Xung đột Scope Lock khi Dispatch Đồng Thời (Concurrent Worker Collision)
- **Lỗi thực tế:** `[WORKER GATE - SCOPE LOCK BREACH]: Worker đang cố sửa file 'FILE_A' nằm ngoài danh sách Scope Lock được cấp phép: ['FILE_B']!`
- **Nguyên nhân:** Khi Coordinator dispatch nhiều worker song song hoặc dispatch worker mới trong khi worker cũ vẫn đang chạy trong cùng repo workspace, Scope Lock của worker sau sẽ ghi đè Scope Lock toàn cục của repo. Worker trước khi thực hiện ghi file sẽ bị kiểm tra chéo với danh sách của worker sau và bị chặn ngay lập tức.
- **Quy tắc cứng:** CẤM TUYỆT ĐỐI dispatch song song 2 task EDIT trong cùng một repo workspace nếu không tạo `git worktree` riêng. Trong cùng 1 working copy, mọi task sửa code bắt buộc phải chạy tuần tự (serialize): đợi worker trước hoàn tất kết quả mới dispatch worker tiếp theo.

### Bẫy 5: Cháy Budget Khảo Sát trên Monolith > 1.500 dòng (Exploration Budget Burnout)
- **Lỗi thực tế:** Worker chạm trần budget 12-15 calls khi đọc/tìm kiếm và abort mà chưa kịp áp dụng bất kỳ patch nào (`files_modified == 0`).
- **Nguyên nhân:** Trên các file monolith lớn (> 1.500 đến 15.000+ dòng như `state_machine.py`, `tiktok_dashboard.py`), nếu Coordinator không cấm mò file, Worker có xu hướng tự chạy `grep`, `search_files`, hoặc chia nhỏ `read_file` để tìm số dòng chính xác. Trong môi trường sandbox Worker, các lệnh shell này thường bị hook filter chặn hoặc timeout, khiến Worker đốt sạch 15 iterations vào tìm kiếm vô nghĩa.
- **Quy tắc cứng:**
  - Đối với file monolith, Coordinator BẮT BUỘC tự dùng `grep -n` O(1) kiểm tra anchor duy nhất (`count == 1`), soạn sẵn exact `OLD_STRING` và `NEW_STRING`.
  - **Chỉ thị dập tắt hành vi mò mẫm:** Trong context dispatch, BẮT BUỘC ghi rõ:
    * *"CẤM dùng grep, CẤM dùng search_files, CẤM đọc toàn bộ file."*
    * *"GỌI NGAY tool patch() trong turn 1 với path, old_string và new_string đã cung cấp sẵn. Tool patch() tự động dùng fuzzy match 9 chiến lược để định vị và thay thế chính xác mà không cần biết số dòng."*
    * *"Sau khi patch xong, tại turn 2 chạy đúng lệnh FOCUSED_TEST và kết thúc ngay."*

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
6. `FOCUSED_TEST`: Bắt buộc đúng cú pháp chuẩn (nếu dùng bare `pytest ... -v` sẽ bị Guard reject ngay với `INVALID_FOCUSED_TEST_FORMAT`):
   - Dạng pytest: `FOCUSED_TEST: python -m pytest <file.py>::<test_node> -q` (LƯU Ý: `<file.py>` là đường dẫn tương đối hoặc tuyệt đối sạch không có khoảng trắng; `<test_node>` là single test function/method identifier, CẤM lồng class `Class::test` vì regex parser chỉ nhận 1 cặp `::` với 1 identifier; CẤM chạy bare file như `pytest file.py` mà không có `python -m pytest ...::<test_node> -q` vì regex hook kiểm tra chặt `python -m pytest \S+::\w+ -q`).
     * **BẪY KHO CÓ KHOẢNG TRẮNG (SPACES IN REPO PATH — 2026-10-14):** Với các repo có khoảng trắng trong tên thư mục (như `D:/Taadaa/tiktok-luot nuoi acc`), nếu truyền đường dẫn tuyệt đối (kể cả có nháy kép), regex `\S+` của Coordinator Guard sẽ tokenize trượt và văng `INVALID_FOCUSED_TEST_FORMAT`. BẮT BUỘC `cd` vào thư mục repo trước và chỉ truyền đường dẫn tương đối sạch không có khoảng trắng (ví dụ `FOCUSED_TEST: python -m pytest tests/test_runner.py::test_foo -q`).
   - Hoặc dạng compile: `FOCUSED_TEST: python -m py_compile <file.py>` (đường dẫn file tương đối, ví dụ `python -m py_compile scripts/target.py`).
7. `FAIL_FAST`: Bắt buộc chứa câu lệnh Fail-Fast nguyên văn:
   `FAIL_FAST: Nếu trong <= 3 iterations đầu thấy scope bất khả thi với budget 15 calls thì DỪNG NGAY (ABORT) và trả về anchor + proposed contract, cấm đốt hết budget để mò file rồi fail im lặng.`

### Bẫy Bổ Sung (Tránh Reject Ngay Lập Tức):
- **Bẫy `EDIT_MISSING_FILE` & `MULTI_FILE_VIOLATION` (Cấm gộp nhiều file):** Khi task cần sửa nhiều file (ví dụ `follow_health_helper.py` và `tiktok_dashboard.py`), nếu nhồi cả 2 file vào goal hoặc context (`FILE: path1 và FILE: path2`), regex của guard sẽ không nhận diện được target duy nhất hoặc phát hiện quá số lượng file cho phép (`MULTI_FILE_VIOLATION: Phát hiện N files trong 1 task. Tối đa <= 2 files (1 file nghiệp vụ + 1 file test)`). BẮT BUỘC chẻ nhỏ thành các lệnh `delegate_task` riêng biệt, mỗi lệnh nhắm đúng 1 file duy nhất.
- **Bẫy Pseudo-URI & URI Parameters Trong Snippets (`PATH_NOT_ABSOLUTE` - 2026-10-15):** Trong context/prompt, nếu đưa các đoạn code hoặc chuỗi kết nối URI như `f"file:{db_path}?mode=ro"` hay `sqlite3.connect('file:...?...')`, regex kiểm tra path của guard sẽ bắt chuỗi `file:{db_path}?mode=ro` và kiểm tra `os.path.isabs()`, gây lỗi `PATH_NOT_ABSOLUTE: '{db_path}?mode=ro", uri=True)' không phải đường dẫn tuyệt đối`. Tránh đưa các URI kết nối dạng `file:{...}` vào context khi mô tả code, hoặc tách rời để regex guard không bắt nhầm thành file path.
- **Bẫy Sol Repair Streaming Timeout Fallback (Strike 1 & 2):** Khi chạy `sol_repair.py`, nếu model streaming bị treo hoặc ném `Model call failed: Timeout exceeded during streaming` (exit code 1), điều kiện "Sol Repair chưa hỏng" bị phá vỡ. Coordinator ĐƯỢC PHÉP kích hoạt Fallback Worker qua `delegate_task` ngay lập tức để tiếp tục vòng lặp remediation mà không bị vi phạm First-Responder Monopoly.
- **Bẫy `OLD_EQUALS_NEW` (Bắt buộc dùng `<<<` và `>>>` cho từng hunk):** Nếu không bọc block code cũ và mới trong triple angle brackets `<<<` và `>>>` (ví dụ dùng bare text hoặc backticks), hoặc nhồi nhiều anchor/hunk (Anchor 1, Anchor 2) vào chung một trường, bộ parser regex của hook sẽ parse trượt ranh giới giữa `OLD_STRING:` và `NEW_STRING:`, dẫn đến lỗi giả `OLD_EQUALS_NEW: Đoạn mã cũ và mới #1 hoàn toàn giống nhau`. BẮT BUỘC dùng đúng cú pháp `OLD_STRING: <<<\n...\n>>>` và `NEW_STRING: <<<\n...\n>>>`.
- **Bẫy Monolith (`MONOLITH DISPATCH BLOCKED`):** CẤM dispatch worker sửa file monolith `*_smoke.py` cho popup (`COORDINATOR GUARD - MONOLITH DISPATCH BLOCKED`). Nếu phát hiện popup mới cần dismiss trên monolith, Coordinator phải dùng quyền Emergency Surgery (L2) xử lý trực tiếp O(1) (<= 15 dòng, 1 test focused <30s) hoặc đưa vào modular registry (`benign_popup_registry.py`).
- **Bẫy Closeout Gate & Sol Repair Fallback:**
  - Lệnh terminal chạy `closeout_gate.py` ở foreground bắt buộc `timeout <= 60s`.
  - Khi Reviewer trả về `< 85` (REJECTED, Strike 1 & 2), BẮT BUỘC chạy `sol_repair.py` độc quyền trước. Chỉ khi `sol_repair.py` exit != 0 / crash / validation fail mới được fallback dispatch Worker.
  - Reviewer thường trừ điểm các lỗi: quên đóng file (`wb.close()` trong `finally`), thiếu unit test độc lập cho nhánh retry/failure mới.
- **Bẫy Line Ending CRLF vs LF Làm Thổi Phồng Git Diff (`git diff --numstat` Inflation Pitfall - 2026-10-11):**
  - **Hiện tượng**: Worker trên Windows sửa một file nhỏ (ví dụ thêm 25 dòng code), nhưng khi nộp bài cho `closeout_gate.py` thì Reviewer chấm REJECTED / đánh rớt với lý do: *"Kiến trúc vẫn chứa rủi ro do file script bị thay đổi gần như toàn bộ (~1000 dòng thay đổi)"*.
  - **Nguyên nhân gốc rễ**: Kho git lưu file dưới dạng line ending LF (`\\n`), nhưng khi Worker hoặc editor trên Windows ghi/patch file lại ghi bằng CRLF (`\\r\\n`). Khi chạy `git diff` mặc định (không có cờ `-w` / `--ignore-space-at-eol`), git xem toàn bộ 1000+ dòng trong file đều bị thay đổi! Closeout Gate trích xuất raw diff gửi cho AI Reviewer (Sol High / Reviewer), khiến Reviewer tưởng Worker đã viết lại cả file lớn và từ chối phê duyệt.
  - **Khắc phục bắt buộc**:
    - Trước khi chạy Closeout Gate hoặc sau khi Worker patch xong, Coordinator BẮT BUỘC kiểm tra `git diff --numstat <files>`.
    - Nếu phát hiện số dòng thay đổi vượt trội bất thường (ví dụ: +1023 / -998 trên một hàm nhỏ), kiểm tra ngay CRLF: `data.count(b'\\r\\n')`.
    - Chạy chuẩn hóa line ending về LF: `content.replace(b'\\r\\n', b'\\n')` trước khi commit hoặc gọi `closeout_gate.py`.

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
