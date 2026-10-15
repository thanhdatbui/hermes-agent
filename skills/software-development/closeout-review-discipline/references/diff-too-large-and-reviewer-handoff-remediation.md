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

## 7. Cấm Cosmetic Reformatting để Lách Line Budget & Bắt Buộc Test Trực Tiếp Cho Logic Fix
- **Chống Cosmetic Reformatting:**
  - Tuyệt đối CẤM nén nhiều imports lên 1 dòng (`import os, sys, subprocess...`) hoặc gộp các khối `with / if` thành 1 dòng để lách line budget (ví dụ <= 1450 dòng). Sol Auditor sẽ coi đây là hành vi trốn tránh / code smell, vi phạm PEP 8 và trừ thẳng 15-20 điểm Architecture & Safety.
  - Cách xử lý line budget chuẩn: Tách các hàm helper không cốt lõi hoặc xóa các docstring/comments dư thừa, giữ nguyên cấu trúc PEP 8 dễ đọc.
- **Bắt buộc Unit Test trực tiếp cho Logic Fix:**
  - Khi sửa bug (ví dụ `negative minutes clamping`, `parse_reconcile_iso_dt` giữ microsecond), KHÔNG ĐƯỢC chỉ trông chờ vào test cũ pass ngầm. Bắt buộc viết test case trực tiếp assert riêng cho logic mới (ví dụ assert clamp về `00:00:00`, assert microsecond preserved, assert `minutes==0` suppress telemetry log).
  - Thiếu test trực tiếp cho code diff mới = Reviewer đánh rớt ngay vì coi là "test nông, không chứng minh được tính đúng đắn của logic mới".
- **Sự Cố Watchdog Cronjob Đứt Gãy Khi Chạy Từ AppData:**
  - Khi script watchdog chạy qua Hermes cron (`%LOCALAPPDATA%\hermes\scripts\<script>.py`), `sys.path[0]` là thư mục AppData. Nếu script trong repo được chia nhỏ thành package con (`scripts/watchdog/`), bản copy ở AppData sẽ văng `ModuleNotFoundError: No module named 'watchdog'`.
  - Quy tắc: Cấu hình cronjob trỏ thẳng tới file script gốc trong repo (`D:/Taadaa/tiktok-luot nuoi acc/scripts/<script>.py`) hoặc bắt buộc có đoạn boilerplate nạp `_candidate_dirs` vào `sys.path` trước mọi import nội bộ.

## 8. Bẫy Cắt Tỉa Code Sol Payload Guard & Quy Chuẩn Thắt Chặt Assertion
- **Bẫy Cắt Tỉa Code (`sol_payload_guard` Truncation Trap):**
  - Khi git diff thô vượt quá 20,000–25,000 bytes, `sol_payload_guard` tự động cắt tỉa các khối code lớn (`... [N dòng bị lược]`) để ép payload dưới trần an toàn HTTP tránh lỗi 413.
  - Hậu quả: Reviewer Sol không nhìn thấy toàn bộ code/test thật nên trừ nặng 20–30 điểm với lý do *"THIẾU NGHIÊM TRỌNG: code/test bị truncate, không thể audit toàn bộ tính đúng đắn"*.
  - Biện pháp phòng tránh: Bắt buộc giữ diff code < 15,000 bytes (tốt nhất 5,000–10,000 bytes). Sử dụng `git reset --soft origin/master` gộp commit dọn sạch noise và test thừa trước khi chạy closeout gate.
- **Thắt chặt Assertion cho Test Happy Path:**
  - CẤM viết assertion lỏng lẻo như `assert any("khớp" in line for line in res)` hoặc chỉ assert không văng Exception.
  - Reviewer sẽ bắt lỗi ngay: *"Happy-path test assertion quá lỏng, không verify giá trị delta cụ thể"*.
  - Bắt buộc assert chính xác chuỗi kết quả và giá trị delta thực tế:
    `assert "M4 (@user) : script 5 lượt - web 5 lượt - khớp" in report` và `assert "+5 Following thật" in report`.
- **Kiểm Thử Normal-Path Song Song với Edge-Case:**
  - Khi sửa logic biên (ví dụ microsecond capping cuối ngày), ngoài test case cho edge-case bị cap, BẮT BUỘC phải có test case cho **normal-path có microsecond nhưng KHÔNG bị cap** (ví dụ `08:30:00.500000 + 10m = 08:40:00`) để chứng minh không làm sai lệch luồng nghiệp vụ thông thường.
- **Chống Trùng Lặp Telemetry Log (Duplicate Logging):**
  - Không emit 2 dòng log liên tiếp cho cùng 1 event (ví dụ vừa log `capped boundary ...` vừa log `[RECONCILE_BUFFER_TELEMETRY] ... capped=True`). Reviewer coi đây là code cẩu thả / log noise và trừ điểm Observability.
- **Ngân Sách Turns Cho Claude CLI Strike 3 Hand-Off:**
  - Khi ủy quyền cho Claude CLI tự sửa ở Strike 3 (`claude -p`), cấp tối thiểu `--max-turns 25` hoặc `30` (thay vì 15) để đảm bảo Claude CLI đủ budget đọc file, sửa code và chạy test pass mà không bị ngắt giữa chừng vì chạm trần turns.
