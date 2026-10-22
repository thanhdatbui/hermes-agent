# Claude CLI Quota Guard, Silent Fallback & Safe Push Invariants

## 1. Cơ Chế Silent Fallback Trong Closeout Gate
- **Kiến trúc 2 tầng Reviewer trong `closeout_gate.py`:**
  * **Tier 0 (Primary):** Claude Sonnet CLI (`claude -p - --model sonnet --effort high`) được cấu hình để gửi trọn vẹn diff và log kiểm thử mà không bị ràng buộc trần 37KB.
  * **Tier 1 (Fallback):** OmniRoute `:20129` (Sol High qua `gpt-web-sol`). Chịu sự quản lý của `sol_payload_guard.py` với trần payload 37KB.
- **Bẫy Quota Guard Exit 20:**
  * Khi tài khoản Claude CLI đạt hạn mức (Quota 5h >= 85% hoặc tuần >= 90%), `claude_quota_guard.py` chặn lệnh và trả về exit code 20.
  * `run_claude_review_pipe()` trong `closeout_gate.py` bắt `returncode != 0` và trả về `None`.
  * Gate tự động và âm thầm fallback xuống Tier 1 OmniRoute (:20129).
  * **Hậu quả:** Coordinator tưởng rằng Sonnet đang chấm, nhưng thực tế toàn bộ các lần review đều do Sol High thực hiện.
  * **Cách nhận diện:** Kiểm tra telemetry trong `D:/Taadaa/logs/gate_audit.jsonl` trường `details.base_url`. Nếu thấy `http://localhost:20129/...` thay vì `claude_cli:sonnet`, nghĩa là Claude CLI đã bị block hoặc rớt xuống fallback.

## 2. Bẫy Truncation Của Sol Payload Guard Khi Fallback
- Khi bị rớt xuống Sol High, nếu file diff lớn (>25-30KB, ví dụ các bộ test mock dài), `sol_payload_guard.py` tự động cắt tỉa (`hunks elided`) và gắn nhãn `[TRUNCATION_MANIFEST]`.
- Sol Auditor khi phát hiện manifest bị cắt sẽ fail-closed và trả về `<escape>NEED_CONTEXT:<path></escape>`, chấm 0 điểm toàn diện.
- Sonnet CLI không bị áp trần 37KB này, do đó khi chuyển hẳn sang Sonnet CLI thật, review sẽ đọc được trọn vẹn 100% diff và test suite.

## 3. Kỷ Luật Tuyệt Đối Với `safe_push.py` (Chống Cowboy Push)
- **Hard Invariant:** `closeout_gate.py` bắt buộc phải trả về `Verdict: APPROVED (Score >= 85)` trước khi bất kỳ commit nào được push lên remote.
- **Cơ chế phòng thủ của `safe_push.py`:**
  * Nếu repo chưa có audit APPROVED hợp lệ cho HEAD commit sha, `safe_push.py` chặn với lỗi `BLOCKED_GATE_NOT_APPROVED`.
  * Nếu Coordinator cố tình truyền cờ `--owner-override`, script tiếp tục chặn với `BLOCKED_AGENT_OVERRIDE` (quyền override chỉ dành cho người dùng thật).
- **CẤM TUYỆT ĐỐI GÕ `git push` TRỰC TIẾP:**
  * Khi `safe_push.py` từ chối, CẤM Coordinator tự tiện gõ `git push origin <branch>` để lách rào.
  * Hành vi này coi là cowboy push vi phạm quy chuẩn nghiêm trọng nhất.
  * **Hành động đúng:** Khi kẹt review do hết quota hoặc chưa đủ 85 điểm:
    1. Kiểm tra `python D:/Taadaa/tools/claude_quota_guard.py status`.
    2. Nếu quota hết (100%): Báo cáo trung thực thời gian reset và trạng thái test (xanh 100%, canary pass). Chờ reset hoặc xin phép user override.
    3. Tuyệt đối không được force push code chưa có audit pass.
