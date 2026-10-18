# Closeout Gate Handoff Lock, Scope Bleed & Grace Band Discipline (2026-10-18)

## 1. Bối Cảnh & Vấn Đề Gặp Phải
Trong phiên làm việc chốt phiên (`Done` / closeout), Coordinator thường mắc 3 sai lầm nghiêm trọng dẫn đến việc dừng lại phân trần, khóc lóc hoặc kẹt vòng lặp vô tận:
1. **Scope Bleed & Partial Committed Scope:** Khi working tree hoặc local git ahead `origin/main` có các commit / staged files từ ca khác, việc chạy `closeout_gate.py --files <target>` bị từ chối với lỗi `refusing partial committed scope` hoặc `staged files != --files targets`.
2. **Reviewer Handoff Lock (Strike 3-4):** Khi điểm review < 85/80 liên tiếp >= 3 lần trên cùng một `scope_hash`, gate kích hoạt khóa cơ học `D:/Taadaa/runtime/handoff_lock_active.json`. Lúc này Coordinator/Worker/Sol Repair cố sửa tiếp là vi phạm gate handoff.
3. **Bẫy Cày Điểm Vụn Vặt Lên 85 (Anti-Score-Chasing):** Coordinator tự ý hiểu nhầm là phải ép đủ 85 điểm mới được push, dẫn đến việc đi sửa format, docstring, telemetry thừa thãi dù bộ test đã pass 100%, khiến diff phình to và Reviewer trừ điểm ngược lại.

## 2. Quy Tắc Cơ Học & Kỷ Luật Điều Phối

### A. Grace Band 80-84 Là Điểm Duyệt Tự Động (Auto-Push)
- Toàn bộ codebase thật (`closeout_policy.json`, `gate_common.py`, `closeout_gate.py`, `safe_push.py`) đều đồng bộ:
  * Điểm >= 85: `STRICT_APPROVED`.
  * Điểm 80–84: `GRACE_APPROVED` nếu thỏa mãn: Unit test xanh 100%, numstat <= 30 dòng, <= 2 files, 0 critical findings.
- Khi đạt điểm trong Grace Band (>= 80), Gate tự động cấp token và cho phép `safe_push.py` đẩy lên Git.
- CẤM TUYỆT ĐỐI bắt Sol High hay Claude cày điểm từ 80-84 lên 85.

### B. Xử Lý Khi Kích Hoạt Reviewer Handoff Lock
- Khi gate in:
  `[REVIEWER_HANDOFF_TRIGGERED: N consecutive rejections reached for scope_hash=...]`
  và tạo file `D:/Taadaa/runtime/handoff_lock_active.json`:
  1. Coordinator, Worker và Sol Repair BẮT BUỘC DỪNG SỬA MÒ NGAY LẬP TỨC.
  2. Kích hoạt chuyển giao cho Claude CLI: `python D:/Taadaa/tools/claude_worker.py --role worker --file <target>`.
  3. Nếu Claude CLI hoặc fallback timeout / cạn quota mà vẫn chưa đạt điểm duyệt:
     * Chuyển trạng thái task sang **L3 BLOCKED**.
     * Báo cáo ngắn gọn, đính kèm bằng chứng cơ học: điểm reviewer gần nhất, số test pass (ví dụ: 132/132 passed), đường dẫn file lock `handoff_lock_active.json`.
     * **CẤM TUYỆT ĐỐI:** Không tự ý sửa tay vượt ngân sách O(1), không reset/revert code ca khác, không xóa file lock, và không dừng lại phân trần xin lỗi dài dòng trong chat.

### C. Cơ Chế Pre-closeout Short-Circuit Cho Task ADB/Farm
- Khi phiên làm việc thuần túy thao tác ADB/UI trên điện thoại (đổi bio, ghim video, cấu hình nick) mà không có diff code mới:
  * `check_pre_closeout_short_circuit(repo, targets)` tự động nhận diện target files đã khớp 100% remote upstream (`origin/main`).
  * Gate tự động exit 0 với `[ALREADY_PUSHED]` trong 0.1s, hoàn toàn không gọi Sol Reviewer.
  * Khi User gõ "Done", Coordinator kiểm tra short-circuit trước để tránh kéo các commit dở dang cũ vào review.
