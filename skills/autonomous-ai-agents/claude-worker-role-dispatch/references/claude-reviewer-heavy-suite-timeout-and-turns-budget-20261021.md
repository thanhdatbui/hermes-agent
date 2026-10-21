# Claude Reviewer Heavy-Suite Timeout & Turns Budget Invariant (2026-10-21)

## 1. Hiện tượng & Căn nguyên sự cố

Trong phiên thi công cơ chế 3 Gate cơ học (`plan_exec_gate.py` và `test_plan_exec_gate.py` gồm 59 integration tests):
- Khi gọi `claude_worker.py --role reviewer --timeout 150`, tiến trình liên tục bị chết với:
  ```text
  Error: Reached max turns (8)ERROR: timed out after 150s
  exit code 124
  ```
- **Phân tích căn nguyên:**
  1. *Thời gian chạy test Windows:* Riêng việc chạy 59 tests git thật trên Windows đã ngốn **43.55s**.
  2. *Tiêu hao turns:* Claude Code CLI (`claude-sonnet-5-5`) khi khởi động:
     - Turn 1-2: Bash/Read kiểm tra git diff và trạng thái file.
     - Turn 3-4: Chạy `pytest` (mất 43s) và đọc output.
     - Turn 5-6: Soi các ca kiểm thử giả mạo (tamper tests) và edge-case.
     - Turn 7-8: Cố gắng tổng hợp báo cáo.
  3. Giá trị mặc định `default_turns = 8` và `--timeout 150` khiến Claude CLI vừa chạm trần turns vừa bị caller (harness) ngắt ngang ở giây 150, sinh ra lỗi `timeout` giả và làm tê liệt vòng lặp nghiệm thu.

---

## 2. Quy chuẩn cấp ngân sách Reviewer cho Test Suite nặng

Khi task có test suite chạy trên 20s hoặc nhiều hơn 30 test cases:
1. **Nâng trần Turns lên mức tối đa (`--max-turns 15`):**
   - Chạm đúng `hard_cap_turns = 15` của role `reviewer`.
   - CẤM để mặc định `default_turns = 8` cho các bài audit tích hợp.
2. **Nâng trần Timeout tối thiểu 300s (`--timeout 300`):**
   - Đảm bảo thời gian cho Claude chạy test 1-2 lần (mất 40-90s) và phân tích sâu AST/diff mà không bị ngắt cụt.
   - Luôn kẹp cờ chạy ngầm `terminal(background=True, notify_on_complete=True, timeout=360)` ở tầng Coordinator.
3. **Kẹp chỉ thị kiểm tra tập trung trong Prompt:**
   - Chỉ định rõ lệnh test focused cụ thể: `"Chỉ chạy pytest <test_file> -q và đọc diff của đúng 2 file mục tiêu, không explore rộng"`.

---

## 3. Bài học thiết kế Gate cơ học chống Worker giả mạo (HMAC Canonical Signing)

Trong quá trình đối soát với Claude Reviewer cho `plan_exec_gate.py`:
1. **Canonical Payload HMAC:**
   - Ký HMAC băm nửa vời (chỉ băm hash content) là lỗ hổng chí mạng: Worker có thể sửa lén `base_commit_sha` để che giấu commit ngoài scope, hoặc sửa `plan_sha256` mà signature vẫn hợp lệ.
   - BẮT BUỘC ký canonical payload gồm toàn bộ các trường trọng yếu:
     `f"{gate}:{task_id}:{status}:{plan_sha256}:{evidence_pack_sha256}:{base_commit_sha}"`.
   - Gate B và Gate C bắt buộc xác thực chữ ký trước khi tin tưởng bất kỳ trường nào.
2. **CẤM DEFAULT SECRET trong mã nguồn:**
   - Không để fallback `DEFAULT_GATE_HMAC_SECRET` trong source code; nếu biến môi trường `GATE_HMAC_SECRET` không tồn tại $\rightarrow$ BẮT BUỘC HARD-FAIL / REJECT ngay lập tức.
3. **Receipt PASS là bất biến (Non-overwritable):**
   - Receipt đã PASS tuyệt đối không được ghi đè, kể cả khi file bị hỏng (malformed/corrupted) hay worker truyền cờ `--force`. Receipt REJECT thì được phép chạy lại.
