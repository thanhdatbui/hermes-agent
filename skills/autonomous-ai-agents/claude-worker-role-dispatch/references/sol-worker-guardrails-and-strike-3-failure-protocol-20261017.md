# Sol Worker Remediation Guardrails & Closeout Escalation Protocol (17/10/2026)

## Bối cảnh & Vấn đề Cốt lõi
Khi chạy Closeout Gate (`closeout_gate.py`), hệ thống thường bị kẹt ở điểm 72-82 do thiếu integration test / telemetry.
- `sol_repair.py` (Strike 1): Single-shot AST proposal <= 30 dòng, không chạy được `pytest` nên không giải quyết được các finding thiếu integration test thật.
- `sol_worker.py` (Strike 2): Autonomous ReAct agent trên `gpt-web-sol` (:20129, free quota). Tuy nhiên, code hiện tại CHƯA ĐỦ AN TOÀN để gắn trực tiếp vào Closeout vì thiếu 4 hàng rào bảo vệ.
- `claude_worker.py --role worker` (Strike 3): Chạy bằng Claude Haiku 5.5 (rẻ, nhẹ quota, CẤM Sonnet 5.5).
- **Grace Band (80-84 điểm):** Score >= 80, diff <= 30 dòng, test 100% pass (>= 1 test, 0 fail/err) -> AUTO-PUSH NGAY. Hook `pre-push` ở tất cả repo (Hermes, tools, tiktok-luot nuoi acc) đã đồng bộ `THRESHOLD=80`.
- **CẤM BÁO L3 BLOCKED DỪNG LẠI KHI TEST ĐÃ PASS:** Nếu focused test đã pass 100% mà Reviewer vẫn dìm dưới 80 do bắt bẻ vô lý, Coordinator BẮT BUỘC kích hoạt `safe_push.py --owner-override` để push giải phóng phiên ngay lập tức!

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

## 3. Workflow Chốt Phiên Chuẩn 3 Nấc & Xử Lý Triệt Để Khi Bị Dìm Điểm
```text
[BẤM CHỐT PHIÊN]
       │
       ▼
[Nấc 1: Sol Repair] (Free 100% — :20129)
       │  • Sửa lỗi nhỏ, telemetry, boundary 1 dòng (Diff <= 30 dòng)
       │  • Đạt >= 80đ + test xanh  ──►  AUTO-PUSH XONG LUÔN ✅
       ▼ (Nếu trượt do thiếu integration test)
[Nấc 2: Sol Worker] (Free 100% — :20129)
       │  • ReAct Agent tự gõ pytest thật, viết test tích hợp sâu
       │  • Có hàng rào Snapshot: Hết lượt tự rollback, cấm làm bẩn git
       │  • Đạt >= 80đ + test xanh  ──►  AUTO-PUSH XONG LUÔN ✅
       ▼ (Nếu Sol Worker chưa giải quyết xong sau 8-10 turns)
[Nấc 3: Haiku Worker] (Rẻ như cho — CẤM SONNET)
       │  • Gọi `claude_worker.py --role worker` (Chạy Claude Haiku 5.5)
       │  • Sửa nốt test trong scope đóng băng
       │  • Đạt >= 80đ + test xanh  ──►  AUTO-PUSH XONG LUÔN ✅
       ▼
[NẾU VẪN BỊ DÌM DƯỚI 80D DÙ TEST ĐÃ 100% PASS]
       │
       └──► CẤM BÁO L3 BLOCKED / CẤM ĐẦU HÀNG!
            Kích hoạt ngay: `safe_push.py --owner-override <repo> <remote> <branch>` 
            👉 PUSH THẲNG LÊN GITHUB & GIẢI PHÓNG PHIÊN NGAY LẬP TỨC!
```

---

## 4. Live Quota Sync vs Dummy Cache Trap
- `refresh_claude_quota_file.py` từng bị lỗi hardcode dummy `{fh: 5, sd: 0}` tạo ra số liệu ảo 5% / 0% khiến Coordinator và Operator bị đánh lừa.
- Quy chuẩn bắt buộc: Script refresh BẮT BUỘC query trực tiếp model-free `/usage` từ Claude CLI qua `probe_claude_quota(find_real_claude())` rồi mới ghi đè vào `plan-usage-history.json`.
- Định kỳ cron `refresh-claude-quota-watchdog` chạy 30 phút/lần đồng bộ số liệu thật sống từ Anthropic servers.
