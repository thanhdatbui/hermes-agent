# Base HEAD~1 Cumulative Diff Trap & Worker Bashless Edit Protocol (2026-10-22)

## 1. Bối Cảnh Hiện Trường (Incident Context)
Trong phiên closeout module OAuth S7 GPM (`run_oauth_s7_pipeline.py` và `test_run_oauth_s7_pipeline.py`), điều phối viên gặp phải 3 vấn đề liên hoàn:
1. **Than phiền và kể lể (Whining / Excuses Trap):** Khi bị hỏi *"Là sao vẫn chưa xong r khóc nhữa? Mày có phải gemini k v"*, agent phản hồi bằng một bản tường trình dài dòng về việc reviewer từ chối và giải thích lý do khách quan thay vì hành động dứt điểm và đưa ra giải pháp kỹ thuật trực diện.
2. **Bẫy Diff Tích Lũy Base `HEAD~1` (Cumulative Diff Accumulation):**
   - Phiên trước đã commit `4e4de25` (`[L2-surgery]...` thêm 134 dòng test).
   - Working tree hiện tại sửa tiếp logic và bổ sung test cases mới.
   - Khi chạy `closeout_gate.py --base HEAD~1 --files scripts/run_oauth_s7_pipeline.py tests/test_run_oauth_s7_pipeline.py`, Git tính diff từ `HEAD~1` đến Working Tree (bao gồm toàn bộ commit `4e4de25` cộng với thay đổi chưa commit).
   - Tổng diff vọt lên **28.274 bytes** (~300 dòng diff), vượt quá trần diff share 80% của `SOL_TARGET_BYTES` (36.000B -> ~28KB).
   - `sol_payload_guard.py` lập tức kích hoạt `[TRUNCATION_MANIFEST]`, cắt tỉa các hunks trong file test và chèn khuyến cáo `NEED_CONTEXT`. Reviewer Sol High thấy diff bị cắt cụt liền phán quyết `NEED_CONTEXT:tests/test_...` với Score 0.
3. **Bẫy Tool-Lock `Read,Edit` Cấm `Bash` Của Worker Haiku:**
   - Trong `claude_worker.py`, vai trò worker được cấp quyền `Read,Edit` và đưa vào danh sách đen `Bash,Write...`.
   - Nếu prompt giao việc cho worker chứa chỉ thị "Chạy pytest để verify" hoặc chứa cú pháp có dấu ngoặc đơn shell `$(...)` / `_mock_env(...)` không bọc kỹ, worker sẽ bị chặn hoặc báo lỗi `No shell tool is loaded / bash: command substitution error`.

---

## 2. Nguyên Tắc & Quy Trình Khắc Phục (Actionable Protocol)

### A. Kỷ Luật Ứng Xử Trực Diện (Anti-Whining Invariant)
- **CẤM TUYỆT ĐỐI** kể khổ, giải thích lòng vòng ("Sol trừ điểm vì...", "chưa đạt vì thiếu cái này cái kia") khi chưa xong việc.
- Cấu trúc phản hồi chuẩn mực khi user truy vấn tiến độ:
  1. Xác nhận tình trạng hiện tại bằng 1 dòng thực tế (Test pass bao nhiêu, Canary máy nào).
  2. Nêu chính xác điểm nghẽn kỹ thuật cơ học (Ví dụ: "Diff đang 28KB bị dính Truncation Manifest của Sol").
  3. Kế hoạch/hành động dứt điểm đang thực thi ngay lập tức.

### B. Kiểm Soát Ngân Sách Diff Tích Lũy (`--base HEAD~1`)
- Khi repo đã có commit ở đỉnh `HEAD` từ sub-task trước:
  - Kiểm tra `git diff HEAD~1..HEAD` xem commit trước đã chiếm bao nhiêu byte diff.
  - Nếu commit trước đã chiếm > 12KB, việc tiếp tục sửa working tree trên cùng file sẽ làm diff tích lũy `HEAD~1..WORKDIR` vượt ngưỡng 22KB-25KB.
  - **Kỹ thuật Compaction bắt buộc:**
    * Sử dụng `@contextmanager` gom toàn bộ boilerplate mock (`_mock_pipeline`).
    * Sử dụng `@pytest.mark.parametrize` gộp các hàm test cùng cấu trúc thành 1 hàm duy nhất.
    * Đưa số dòng diff của file test về dưới 120 dòng để tổng diff tích lũy không vượt quá 20.000 bytes.

### C. Kỷ Luật Prompting Cho Haiku Worker (Bashless Edit Contract)
- Khi `claude_worker.py` khóa tool ở chế độ `Read,Edit`:
  - **CẤM** yêu cầu worker chạy `pytest` hoặc lệnh terminal.
  - **BẮT BUỘC** ghi rõ trong prompt: *"Edit only <file> using Edit tool. Do NOT run bash or pytest."*
  - Bọc toàn bộ code mẫu hoặc chỉ thị bằng single quote `'...'` hoặc heredoc an toàn, tránh để dấu ngoặc đơn rơi vào command substitution của MSYS bash.
  - Coordinator tự chạy `pytest` trong session chính để nghiệm thu sau khi worker hoàn thành.
