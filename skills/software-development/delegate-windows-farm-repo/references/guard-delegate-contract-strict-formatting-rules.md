# Quy Chuẩn Định Dạng Bắt Buộc Của Hard Gate #3 Dispatch Guard (guard_delegate_contract.py)

Khi Coordinator ủy quyền sửa code qua `delegate_task(role='leaf', ...)` cho các tác vụ `TASK_KIND: EDIT`, hook `guard_delegate_contract.py` thực thi kiểm tra fail-closed nghiêm ngặt theo các quy tắc sau:

## 1. Các Thẻ Khởi Đầu Bắt Buộc
- **`TASK_KIND: EDIT`**: Bắt buộc ở dòng đầu tiên.
- **`FILE: <đường_dẫn_tuyệt_đối>`**: Bắt buộc là đường dẫn tuyệt đối (ví dụ `FILE: D:/Taadaa/tiktok-luot nuoi acc/scripts/feed_session_watchdog.py`). Tuyệt đối CẤM đường dẫn tương đối.
- **`FOCUSED_TEST: <lệnh_chuẩn>`**:
  + Với pytest: `FOCUSED_TEST: python -m pytest <file.py>::<test_node> -q` (bắt buộc tên file trần, đúng 1 dấu phân tách `::`, có cờ `-q`, KHÔNG bọc dấu nháy kép `"`, KHÔNG có đường dẫn thư mục `tests/` hay ổ đĩa `D:/`).
  + Với py_compile: `FOCUSED_TEST: python -m py_compile <file.py>` (bắt buộc tên file trần, KHÔNG có cờ `-q`, TUYỆT ĐỐI KHÔNG bọc dấu nháy kép `"` quanh đường dẫn file vì regex guard sẽ bị gãy).

## 2. Delimiter Bắt Buộc Cho Code Snippets
- `OLD_STRING: <<<`
  `<code_cũ>`
  `>>>`
- `NEW_STRING: <<<`
  `<code_mới>`
  `>>>`
- **CẤM TUYỆT ĐỐI**:
  + Cấm bọc markdown backticks (`` ``` ``) bên trong delimiter.
  + Cấm để dòng đầu tiên của `OLD_STRING` và `NEW_STRING` giống nhau nếu dùng regex đơn dòng fallback (tránh bẫy `OLD_EQUALS_NEW`).
  + **Bẫy chèn hàm mới trước hàm cũ (`OLD_EQUALS_NEW` trên `@staticmethod` / Anchor Prefix Collision):** Khi chèn một hàm mới ngay trước một hàm có sẵn mà cả hai đều bắt đầu bằng decorator chung (ví dụ `@staticmethod` hoặc `@classmethod`), dòng đầu tiên của `OLD_STRING` và `NEW_STRING` đều là `@staticmethod`. Khi parser so sánh dòng mở đầu, guard sẽ chặn: `OLD_EQUALS_NEW: Đoạn mã cũ và mới #1 hoàn toàn giống nhau`. Khắc phục: Mở rộng `OLD_STRING` lên dòng phía trên (ví dụ hằng số `MAX_...` hoặc dòng comment phía trên) để dòng mở đầu của `OLD_STRING` và `NEW_STRING` khác biệt nhau.
  + Bắt buộc tính duy nhất tuyệt đối `c == 1` (`ANCHOR_NOT_UNIQUE`): Đoạn mã cũ trong `OLD_STRING: <<< ... >>>` phải xuất hiện DUY NHẤT 1 lần trong file đích. Nếu xuất hiện từ 2 lần trở lên (ví dụ cùng lặp lại pattern mở file/loop trong nhiều hàm khác nhau), guard lập tức chặn với: `ANCHOR_NOT_UNIQUE: Đoạn mã cũ #1 xuất hiện N lần trong '...'. Bắt buộc c == 1!`. Khắc phục: Mở rộng `OLD_STRING` bao gồm thêm dòng khai báo hàm (`def ...`) hoặc context xung quanh để đảm bảo c == 1, đồng thời vẫn bảo toàn tổng số dòng $\le 30$.
  + Tổng diff dòng không vượt quá 30 dòng (`DIFF_BUDGET_EXCEEDED`): Cả đoạn cũ và mới cộng lại phải $\le 30$ dòng. Nếu vượt quá, guard chặn cứng và yêu cầu chẻ nhỏ task.

## 3. Câu Lệnh Fail-Fast Nguyên Văn
Bắt buộc chứa ĐẦY ĐỦ VÀ NGUYÊN VĂN câu lệnh (CẤM viết tắt hoặc chế câu khác):
`FAIL_FAST: Nếu trong <= 3 iterations đầu thấy scope bất khả thi với budget 15 calls thì DỪNG NGAY (ABORT) và trả về anchor + proposed contract, cấm đốt hết budget để mò file rồi fail im lặng.`

## 4. Bẫy Token Phụ Tránh Vi Phạm `PATH_NOT_ABSOLUTE`
- Tránh viết các dòng có dạng `1. Trong ...` hoặc chứa từ khóa `FILE`, `path`, `db` nếu theo sau là chuỗi không phải đường dẫn tuyệt đối chuẩn, vì regex kiểm tra path trong guard sẽ bắt nhầm và quăng lỗi:
  `PATH_NOT_ABSOLUTE: '1. Trong ...' không phải đường dẫn tuyệt đối`.
- Khi khai báo nhiều file đích (tối đa <= 2 files, kể cả test file), lặp lại thẻ `FILE:` riêng biệt cho từng file:
  ```text
  FILE: D:/Taadaa/.../target.py
  FILE: D:/Taadaa/.../tests/test_target.py
  ```
  Tuyệt đối CẤM dùng dạng danh sách `TARGET_FILES:\n1. ...\n2. ...` vì regex guard sẽ báo `EDIT_MISSING_FILE`.

## 5. Bẫy Python f-string Chứa JS/CSS Double Braces `{{` và `}}` (`ANCHOR_NOT_FOUND`)
- Trong các script Python monolith dựng dashboard/server nhúng HTML/JS bằng f-string đa dòng (ví dụ `tiktok_dashboard.py`), mọi object JavaScript và khối CSS đều dùng cặp ngoặc nhọn kép `{{` và `}}` để thoát (escape) f-string.
- Nếu trong `OLD_STRING: <<< ... >>>`, Coordinator copy code JavaScript với ngoặc đơn chuẩn `{` và `}` thì chuỗi tìm kiếm sẽ không bao giờ khớp với nội dung file thật trên đĩa, khiến guard quăng lỗi:
  `ANCHOR_NOT_FOUND: Đoạn mã cũ #N không tìm thấy trong bất kỳ file đích nào!`.
- **Khắc phục:** Khi lấy anchor và soạn diff cho khối JS/CSS nhúng trong Python f-string, bắt buộc giữ nguyên cặp ngoặc nhọn kép `{{` và `}}` cả ở `OLD_STRING` lẫn `NEW_STRING`.

## 6. Bẫy Guard Self-Protection Khi Nhúng Đường Dẫn Runtime Nội Bộ Trong Tool Argument
- **Hiện tượng:** Nếu trong `context` hoặc bất kỳ tham số nào của tool (`read_file`, `patch`, `delegate_task`) chứa các substring nhạy cảm của runtime user profile (`%LOCALAPPDATA%` trỏ tới user profile) hoặc thư mục guard bảo vệ:
  Hệ thống lập tức kích hoạt `GUARD SELF-PROTECTION / GUARD SOURCE BLACKLISTED` và chặn đứng tác vụ.
- **Khắc phục:** Luôn trỏ tới source repository (`D:/Taadaa/Hermes/deploy/hermes-home/scripts/...`) hoặc OneDrive sync repository (`D:/OneDrive/Taadaa_Sync_Shared/hermes-cron/scripts/...`). Không nhúng trực tiếp đường dẫn runtime nội bộ người dùng vào argument.

## 7. Kỹ Thuật O(1) Local-Assignment Để Tránh `DIFF_BUDGET_EXCEEDED` (> 30 Dòng)
- **Hiện tượng:** Guard chặn task nếu tổng số dòng nghiệp vụ trong `OLD_STRING` + `NEW_STRING` vượt quá 30 dòng.
- **Khắc phục:** Tránh bọc cấu trúc ngữ cảnh lớn quanh cả khối lệnh (làm thay đổi thụt lề 30-50 dòng). Khởi tạo biến/đối tượng ngay trước khối lệnh (ví dụ `executor = concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS)`), giữ nguyên thân khối lệnh để diff chỉ còn $\le 5$ dòng.

## 8. Quy Chuẩn Bắt Buộc Khi Dispatch `TASK_KIND: INVESTIGATE` (Budget <= 5 Calls & Strict Fail-Fast)
- **Hiện tượng:** Khi dispatch worker làm nhiệm vụ đọc/thăm dò/trích xuất hiện trường (`TASK_KIND: INVESTIGATE`), nếu prompt ghi budget > 5 (ví dụ: "Max budget: 10 calls", "Tối đa 8 tool calls"), guard chặn đứng:
  `⛔ [COORDINATOR GUARD - CONTRACT VIOLATION]: INVESTIGATE_BUDGET_EXCEEDED: Budget điều tra (10 calls) > 5. Task đọc tối đa 5 calls.`
- **Quy tắc bất biến:**
  1. Dòng đầu context: `TASK_KIND: INVESTIGATE`
  2. Khai báo ngân sách: BẮT BUỘC $\le 5$ calls (ví dụ `BUDGET: <= 5 calls` hoặc `Max budget: 5 calls`). Tuyệt đối không đề cập bất kỳ con số nào > 5 trong context.
  3. Bắt buộc có câu lệnh Fail-Fast: `FAIL_FAST: Dừng ngay nếu thiết bị offline, không tìm thấy file hoặc tiến trình gặp lỗi không thể phục hồi.`
  4. CẤM ngụy trang sửa code: `goal` tuyệt đối không chứa các từ khóa sửa đổi (`sửa`, `patch`, `edit`, `fix`, `thay`, `revert`). Dùng động từ trung tính: `Vận hành`, `Kiểm tra`, `Khảo sát`, `Thu thập`, `Trích xuất`.

## 9. Rào Cản Môi Trường Coordinator: Default-Deny Terminal & Disabled Execute-Code
- **Hiện tượng:**
  + Chạy `terminal` với các lệnh ad-hoc như `python -c "..."` hoặc `git -C <repo> log ...` bị chặn: `⛔ [COORDINATOR GUARD - TERMINAL BLOCKED]: COORDINATOR TERMINAL BLOCKED (DEFAULT-DENY): Lệnh '...' không nằm trong allowlist của Coordinator!`.
  + Gọi `execute_code` bị chặn: `⛔ [COORDINATOR GUARD - EXECUTE_CODE DISABLED]: Coordinator không được dùng execute_code để tránh ghi mã lậu hoặc bypass! Hãy dùng terminal/read_file/patch.`.
- **Khắc phục:**
  + Với các thao tác đọc hiện trường file/thư mục: Ưu tiên dùng `read_file` (với offset/limit).
  + Khi bắt buộc phải chạy lệnh shell/Python thăm dò nằm ngoài allowlist của Coordinator: Dispatch Worker qua `delegate_task` với `TASK_KIND: INVESTIGATE` (ngân sách $\le 5$ calls, fail-fast). Worker có terminal session độc lập và không bị giới hạn bởi allowlist của Coordinator.

