# Diff Too Large & Strike 3 Reviewer Hand-off Remediation

## 1. Fail-Fast Diff Ceiling (MAX_DIFF_BYTES_GATE = 30,000 bytes)
- `closeout_gate.py` có cơ chế kiểm tra fail-fast ngay tại Step 2:
  `[Gate Fail-Fast: DIFF_TOO_LARGE] Diff quá lớn (N > 30000 bytes). Vi phạm quy chuẩn phân rã task O(1). Phải thu hẹp diff trước khi gọi Reviewer.`
- **Nguyên nhân phổ biến:**
  - Viết test suite quá dài dòng (nhiều fixture, lặp lại các kịch bản dài dòng thay vì dùng `@pytest.mark.parametrize`).
  - Gộp diff nhiều files hoặc các file đồng bộ định kỳ (`scripts/` và `scripts/hermes_cron/`) cùng phình to.
- **Cách khắc phục:**
  - Thu gọn file test bằng `@pytest.mark.parametrize` để cô đọng hàng chục test cases vào 10-20 dòng.
  - Tách bạch các assertion cốt lõi, xóa bỏ test functions phình to không cần thiết.
  - Kiểm tra dung lượng diff trước khi gọi closeout gate:
    `git --no-pager diff --no-ext-diff origin/master..HEAD | wc -c` đảm bảo < 25,000 bytes.

## 2. Ràng buộc Scope `--files` đối với Committed Changes
- Khi code đã được `git commit` ở HEAD:
  - `--files <file1> <file2>` BẮT BUỘC phải khớp chính xác 100% toàn bộ danh sách files có trong commit `HEAD~1..HEAD`.
  - Nếu commit gồm 3 files mà `--files` chỉ truyền 2 files, gate sẽ từ chối:
    `committed ... scope [...] != --files targets [...]; refusing partial committed scope`.
  - Không thể dùng `--files` để cherry-pick một phần của commit đã tạo. Nếu muốn cherry-pick, phải đưa commit về dạng `staged` (`git reset --soft origin/master`) và chỉ stage đúng các file mục tiêu.

## 3. Ràng buộc Audit Binding: Staged/Working-tree Candidate Overlaps Committed HEAD
- Lỗi `binding mismatch: staged/working-tree candidate overlaps committed HEAD` xảy ra khi:
  - Repo có file vừa nằm trong commit HEAD vừa có thay đổi unstaged trong working tree (dirty overlap).
  - Hoặc có staged diff nhưng không khớp với candidate scope đã trích xuất.
- **Khắc phục:**
  - Đảm bảo working tree sạch tuyệt đối trước khi chạy gate: `git status -s` không có file tracked nào bị `M` (modified) chưa commit hoặc dở dang.
  - Chạy `git add -u && git commit --amend` để gộp toàn bộ chỉnh sửa vào HEAD commit duy nhất.

## 4. Strike 3 Reviewer Hand-off Execution (Claude CLI)
- Khi gate trượt 3 lần liên tiếp trên cùng `scope_hash` (`count_consecutive_rejections >= 3`), gate kích hoạt:
  `[REVIEWER_HANDOFF_TRIGGERED: 4 consecutive rejections reached for scope_hash=...]`
- **Quy tắc bắt buộc:**
  1. CẢ Coordinator, Worker và Sol Repair ĐỀU PHẢI DỪNG LẠI việc đoán mò hoặc tạo patch proposal.
  2. Coordinator gọi trực tiếp **Claude CLI** làm Reviewer-with-write-access:
     `claude -p "<remediate_prompt>" --allowedTools "Read,Edit,Write,Bash" --dangerously-skip-permissions --max-turns 15`
  3. Claude CLI đọc toàn bộ findings của Reviewer, tự sửa code theo chuẩn của chính nó, chạy focused test pass 100%.
  4. Sau khi Claude CLI hoàn thành, Coordinator kiểm tra lại `git status` và `pytest`, commit sạch sẽ và chạy lại `closeout_gate.py`.

## 5. Đồng bộ 100% giữa Root Scripts và Hermes Cron
- Các repo có thư mục `scripts/hermes_cron/` song song với `scripts/`:
  - Reviewer Sol chấm điểm rất nặng lỗi **code duplication / drifting** (thường trừ 15-20 điểm nếu hai bản sao lệch nhau).
  - Bắt buộc đồng bộ byte-for-byte các block helper, signature hàm và telemetry logic giữa `scripts/<script>.py` và `scripts/hermes_cron/<script>.py`.
  - Thêm unit test kiểm tra đồng bộ tự động:
    `assert helper_block("script.py") == helper_block("hermes_cron/script.py")`.

## 6. Lỗi Môi Trường `GIT_EXTERNAL_DIFF` và Nhất Quán Microsecond Time Buffer
- **Sự cố `GIT_EXTERNAL_DIFF=""` rỗng:**
  - Nếu biến môi trường `GIT_EXTERNAL_DIFF` bị set thành chuỗi rỗng `""`, git diff sẽ cố execute command `""` và crash với lỗi:
    `error: cannot spawn : No such file or directory` / `fatal: external diff died, stopping at <file>`.
  - Khắc phục: Dùng cờ `--no-ext-diff` khi chạy lệnh git diff (`git --no-pager diff --no-ext-diff`) để ép git bỏ qua external diff command.
- **Nhất quán Microsecond trong hàm Time Buffer:**
  - Khi triển khai logic capping cuối ngày (`end_of_day = 23:59:59`), tuyệt đối tránh đặt `microsecond=999999` lúc so sánh nhưng lúc format lại ép về `microsecond=0`. Reviewer sẽ bắt lỗi off-by-1-microsecond không nhất quán.
  - Luôn thống nhất `dt.replace(hour=23, minute=59, second=59, microsecond=0)` cho cả điều kiện kẹp trần và kết quả trả về.
