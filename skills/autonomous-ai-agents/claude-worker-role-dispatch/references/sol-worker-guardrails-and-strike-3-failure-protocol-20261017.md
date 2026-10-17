# Sol Worker Remediation Guardrails & Strike 3 Terminal Failure Protocol (17/10/2026)

## Bối cảnh & Vấn đề Cốt lõi
Khi chạy Closeout Gate (`closeout_gate.py`), hệ thống thường bị kẹt ở điểm 72-82 do thiếu integration test / telemetry.
- `sol_repair.py` (Strike 1-2): Single-shot AST proposal <= 30 dòng, không chạy được `pytest` nên không giải quyết được các finding thiếu integration test thật.
- `sol_worker.py`: Autonomous ReAct agent trên `gpt-web-sol` (:20129, free quota). Tuy nhiên, code hiện tại CHƯA ĐỦ AN TOÀN để gắn trực tiếp vào Closeout vì thiếu 4 hàng rào bảo vệ.
- Strike 3 Hand-off: Nếu Strike 3 vẫn fail, tuyệt đối CẤM sinh Strike 4, kích hoạt Hard Stop và L3 BLOCKED.

---

## 1. 4 Hàng Rào An Toàn Bắt Buộc Trước Khi Dùng Sol Worker Cho Closeout
Theo tư vấn kiến trúc của Claude Sonnet 5.5:

1. **Snapshot & Atomic Rollback:**
   - Trước khi `sol_worker` chạy, snapshot git status/hash của target files.
   - Nếu tiến trình kết thúc không phải `ACTION: DONE` kèm test passed (bao gồm cả trường hợp hết turns `exit 124` hoặc timeout), BẮT BUỘC tự động `git checkout -- <files>` để trả lại working tree sạch 100%, cấm để lại patch dở dang.

2. **Trần Diff Tích Lũy (Cumulative Diff Ceiling):**
   - Giới hạn cứng: tổng diff sau tất cả các turns $\le 100$ dòng và $\le 2$ files (trong allowlist).
   - Vượt trần là tự ngắt ngay và revert.

3. **Bảo Vệ Tính Toàn Vẹn Của Test (Test Preservation Guard):**
   - Cấm sửa hoặc xóa các câu lệnh `assert` có sẵn trong test suite.
   - Chỉ được phép bổ sung test case mới hoặc assert mới.

4. **Kiểm Chứng Lệnh Verify Hợp Lệ:**
   - Lệnh `ACTION: COMMAND` để nghiệm thu phải là lệnh chạy test thật vào đúng file test liên quan (ví dụ: `python -m pytest tests/test_... -q`).
   - Cấm chấp nhận các cờ né tránh như `--collect-only` hoặc chạy file test không liên quan.

---

## 2. Bản Chất Của "Turns" Trong ReAct Agent
- **1 Turn:** Là 1 lượt gọi model (round-trip) bên trong CÙNG 1 LẦN THỰC THI (ví dụ: Read file = turn 1, Patch = turn 2, Pytest = turn 3).
- **KHÔNG PHẢI:** Không phải là 1 lần sửa file toàn cục và không phải là 1 lần chạy lại Closeout Gate.
- Một chu trình sửa code + test chuẩn thường cần 7–10 turns. Mặc định `max_turns = 8` là hợp lý; nếu đặt 5 turns sẽ quá chật và dễ bị ngắt giữa chừng.

---

## 3. Quy Trình Xử Lý Khi Strike 3 Vẫn Thất Bại (Strike 3 Failure Protocol)
Nếu sau Strike 3 (sau khi Claude Haiku / Agy CLI đã sửa và Sonnet review) mà Gate vẫn REJECTED hoặc trượt điểm:

1. **CẤM TUYỆT ĐỐI STRIKE 4:**
   - Không sinh thêm bất kỳ lượt sửa mò hay retry nào.
   - Tất cả Coordinator, Worker và Claude CLI đều bị tước quyền sửa tiếp trên `scope_hash` này.

2. **KÍCH HOẠT L3 BLOCKED & ROLLBACK:**
   - Pre-push hook chặn đứng lệnh push do thiếu audit record `APPROVED >= 85`.
   - Rollback các thay đổi không hoàn chỉnh về trạng thái commit sạch.
   - Coordinator xuất biên bản bằng chứng (Evidence Report) nêu rõ failing test và xung đột kiến trúc/scope.

3. **3 LỐI THOÁT CHO OPERATOR:**
   - **Phương án 1 (Hủy bỏ an toàn):** Giữ nguyên commit cũ đang ổn định để farm chạy tiếp.
   - **Phương án 2 (Tách Task lớn):** Đưa vấn đề kiến trúc ra khỏi Closeout, mở task riêng biệt.
   - **Phương án 3 (Owner Override):** Nếu Operator xác nhận code đã an toàn qua Canary máy thật:
     `python D:/Taadaa/tools/safe_push.py --owner-override <repo> <remote> <branch>`
