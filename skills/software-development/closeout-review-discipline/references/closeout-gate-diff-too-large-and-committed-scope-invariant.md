# Closeout Gate DIFF_TOO_LARGE & Committed Scope Invariant

## Bối Cảnh & Cơ Chế Hoạt Động (15/10/2026)

Trong quy trình chốt phiên (`closeout_gate.py`), Step 2 (`EXTRACT CANDIDATE DIFF`) có các rào chắn fail-fast nghiêm ngặt nhằm đảm bảo tính toàn vẹn của diff và tránh tràn context của Reviewer Sol:

1. **Rào Chắn Kích Thước Diff (`MAX_DIFF_BYTES_GATE = 30_000` bytes):**
   - Khi tổng diff vượt quá 30,000 bytes (~30KB), script sẽ lập tức báo lỗi:
     `[Gate Fail-Fast: DIFF_TOO_LARGE] Diff quá lớn (X > 30000 bytes). Vi phạm quy chuẩn phân rã task O(1). Phải thu hẹp diff trước khi gọi Reviewer.`
   - Nguyên nhân phổ biến: File unit test (`tests/test_*.py`) được sinh ra quá dài dòng, chứa nhiều mock database hoặc đa luồng lặp đi lặp lại khiến kích thước diff phình to.

2. **Cơ Chế Khóa Toàn Bộ Phạm Vi Commit (`Refusing Partial Committed Scope`):**
   - Khi commit đã được tạo (`HEAD` commit), nếu dùng cờ `--files <target1> <target2>` mà bỏ qua file test đã commit:
     `committed <base>..HEAD scope [...] != --files targets [...]; refusing partial committed scope`
   - `closeout_gate.py` cấm đánh giá thiên lệch một phần của commit đã hoàn tất (TOCTOU prevention).

## Quy Trình Xử Lý Chuẩn Khi Gặp DIFF_TOO_LARGE

### Cách 1: Thu Gọn File Test Về Mức Tối Giản (Khuyến Nghị)
- Không viết test suite đồ sộ hàng trăm dòng trong cùng PR/commit sửa code.
- Gom các assertion thành parameterized tests hoặc tập trung vào các nhánh logic mới (<= 250 dòng).
- Giữ diff của file test < 5KB để tổng diff toàn bộ repo luôn `< 30,000 bytes`.

### Cách 2: Tách Phạm Vi Bằng Staged Diff (`mode == 'staged'`)
- Nếu commit đã lỡ chứa file test quá lớn:
  1. Chạy `git reset --soft origin/master` để đưa toàn bộ thay đổi về staging area.
  2. Bỏ stage file test: `git restore --staged tests/test_*.py`.
  3. Chỉ stage đúng các file production cần review: `git add scripts/...`.
  4. Chạy `closeout_gate.py --files scripts/...`.
  5. Trong chế độ `staged`, `closeout_gate.py` xác nhận `staged == targets` và dirty của target == 0, cho phép đánh giá diff < 30KB trong khi test vẫn chạy pass từ working tree.

## Rào Chắn Điều Phối Worker Contract (`TASK_KIND: EDIT`)

Khi Coordinator hết ngân sách T1 và bắt buộc dispatch Worker qua `delegate_task`:
- `TASK_KIND: EDIT` bắt buộc có đủ:
  - `FILE: <đường_dẫn_tuyệt_đối>`
  - `OLD_STRING: <<< ... >>>` (thẻ block chính xác `<<<` và `>>>`)
  - `NEW_STRING: <<< ... >>>`
  - `FOCUSED_TEST: python -m pytest <file>::<test_node> -q` (hoặc `python -m py_compile <file>`). CẤM viết plain `pytest <file>`.
  - `FAIL_FAST: Nếu trong <= 3 iterations đầu thấy scope bất khả thi với budget 15 calls thì DỪNG NGAY (ABORT)`
