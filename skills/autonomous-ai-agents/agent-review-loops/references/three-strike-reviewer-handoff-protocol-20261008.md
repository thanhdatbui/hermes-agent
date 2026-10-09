# 3-Strike Reviewer Hand-off Protocol (2026-10-08)

## 1. Bối cảnh & Nguyên nhân ra đời
Trong phiên thẩm định `evidence_gate_verifier.py` ngày 08/10/2026, Coordinator và Reviewer (Claude Code CLI) đã rơi vào vòng lặp "bắt bẻ - sửa - bắt bẻ tiếp" kéo dài tới **13 vòng liên tiếp** (Ping-Pong Review Loop), gây tiêu tốn lượng lớn thời gian và context.
Khi User ra chỉ thị:
> *"Mày k sửa nữa. Bảo chính claude sửa"*
> *"v sửa rule đi, 3 lần reviewer vẫn chưa đạt thì ném cho reviewer sửa. gọi claude cli thiết kế rule đó bổ sung cho closeoutgate"*

Claude Code CLI được giao quyền tự sửa trực tiếp với đầy đủ công cụ (`Read`, `Edit`, `Write`, `Bash` kèm `--dangerously-skip-permissions`). Claude đã tự đọc mã nguồn, phát hiện và sửa đúng 2 bug logic tiềm ẩn, tự chạy test, dọn dẹp ledger và cấp `VERDICT: APPROVED` ngay trong 1 lượt duy nhất!

## 2. Nguyên lý Cốt lõi (The Adversarial Reviewer Paradox)
Khi chia vai cứng **Worker/Coordinator = Thợ code** và **Claude = Giám sát nghiệm thu**:
- Tâm lý Reviewer luôn là *adversarial* (cố tìm cho ra lý do để từ chối hoặc phát hiện rủi ro tầng sâu). Càng sửa các lỗi hiển hiện thì Reviewer càng soi sâu xuống các tầng thấp hơn (từ string matching -> replay attack -> race condition -> process liveness).
- Khi đưa bàn phím cho chính Reviewer tự sửa: Reviewer chuyển từ vị thế "bắt bẻ" sang vị thế "người chịu trách nhiệm giải pháp". Reviewer sẽ tự điều chỉnh code về đúng gu kỹ thuật khắt khe nhất của mình và tự nghiệm thu dứt điểm.

## 3. Quy chuẩn 3-Strike Reviewer Hand-off
- **Strike 1 & Strike 2 (Standard Remediation):**
  Coordinator / Worker tiếp nhận finding của Reviewer, phân tích nguyên nhân gốc, sửa code/test trong phạm vi allowlist, chạy focused test, và gửi lại Reviewer chấm điểm (không thay đổi).
- **Strike 3 (Reviewer Hand-off Trigger):**
  Khi cùng một `scope_hash` bị REJECT hoặc không đạt điểm (score < 85) **3 lần liên tiếp**:
  1. **CẤM Coordinator/Worker tiếp tục đoán mò và sửa tiếp ở vòng 4**.
  2. `closeout_gate.py` tự động phát hiện qua hàm `count_consecutive_rejections(repo, scope_hash)` dựa trên sổ cái `gate_audit.jsonl` và phát tín hiệu cảnh báo ra stderr:
     `[REVIEWER_HANDOFF_TRIGGERED: 3 consecutive rejections reached for scope_hash=... Coordinator/Worker MUST STOP guessing and hand the keyboard to the Reviewer (Claude CLI) to self-remediate...]`
  3. **Chuyển giao quyền can thiệp trực tiếp cho Reviewer (Claude Code CLI)**:
     - Lệnh gọi: `claude -p "<task spec + finding history + exact allowlist>" --allowedTools "Read,Edit,Write,Bash" --dangerously-skip-permissions --model sonnet`
     - Phạm vi khóa cứng: Reviewer CHỈ ĐƯỢC PHÉP sửa các file nằm trong allowlist của candidate hiện tại (`audit_binding.scope`), nghiêm cấm sửa lan man ra ngoài.
     - Reviewer tự đọc file, tự sửa theo tiêu chuẩn của mình, tự chạy test focused < 30s.
     - Reviewer tự chốt VERDICT: `APPROVED` (tiến hành commit/push theo quy trình closeout) hoặc `L3 BLOCKED` kèm báo cáo cụ thể nếu vấp phải xung đột kiến trúc không thể giải quyết trong scope.

## 4. Cơ chế Đếm Streak Không Thể Làm Giả (Tamper-Evident Counter)
- Counter **KHÔNG** dùng tham số dòng lệnh `--attempt N` (vì dễ bị spoof hoặc mất đồng bộ giữa các process).
- Counter được tính tự động từ lịch sử sổ cái `gate_audit.jsonl`:
  - Quét từ cuối file lên đầu cho cặp `(repo, scope_hash)`.
  - Đếm chuỗi các lượt liên tiếp không pass (`passed=False`).
  - Gặp một lượt `passed=True` hoặc một `scope_hash` khác -> Streak reset về 0 ngay lập tức.
  - Chỉ khi cùng một candidate scope bị từ chối 3 lần liên tiếp thì hand-off mới kích hoạt.

## 5. Bất biến Điều phối & Van An toàn Quota (Orchestration & Quota Invariants)
- **Áp dụng toàn diện (Closeout & Mid-Session):** Quy tắc 3-Strike áp dụng cho CẢ closeout reviews lẫn mọi vòng review code giữa phiên (mid-session review). Bất kỳ khi nào Reviewer từ chối 3 lần liên tiếp (kể cả UNRESOLVED do thiếu evidence), Coordinator BẮT BUỘC dừng tự sửa và chuyển giao quyền cho Reviewer.
- **Strike 3 KHÔNG làm dừng tiến trình Remediation:** Bất biến "REJECT = REMEDIATION, CẤM DỪNG" vẫn giữ nguyên 100%. Strike 3 chỉ thay đổi **NGƯỜI CẦM BÀN PHÍM (HOLDER OF THE KEYBOARD)** từ Worker/Coordinator sang chính Reviewer, tuyệt đối không phải là cớ để buông xuôi hay dừng closeout!
- **Van an toàn Quota Fallback:** Nếu Claude CLI chạm ngưỡng bảo vệ hạn mức 85% của 5h session (theo `claude-limit-protection`) hoặc dính rate-limit/lockout: BẮT BUỘC tự động fallback về cho Coordinator (thực hiện Emergency Surgery L2 O(1) nếu thỏa mãn ngân sách) HOẶC điều phối sang Sol High (:20129) vá thẳng theo Invariant chống đóng băng task. Tuyệt đối không để farm bị kẹt khi Claude hết quota!
