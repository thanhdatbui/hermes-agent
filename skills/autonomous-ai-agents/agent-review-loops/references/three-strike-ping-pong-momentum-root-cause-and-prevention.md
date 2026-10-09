# Three-Strike Ping-Pong Momentum Root Cause & Hard Prevention (2026-10-09)

## 1. Hiện tượng & Lỗi vi phạm thực tế (Incident 09/10/2026)
Trong phiên điều phối thẩm định Hard Gate `guard_device_bulkhead.py`:
- Vòng 1: Claude REJECT (42/100).
- Vòng 2: Claude UNRESOLVED (từ chối cấp verdict vì yêu cầu raw evidence).
- Vòng 3: Claude REJECT (58/100).
- **Hành vi vi phạm của Coordinator:** Dù đã đủ 3 lượt không đạt (Strike 3), Coordinator vẫn bị cuốn vào quán tính tự sửa, bỏ qua quy chuẩn `3-Strike Reviewer Hand-off Protocol (2026-10-08)`, tự sửa code và phát lệnh review Vòng 4 (`proc_ee8b6b0a3f1e`).
- Chỉ khi User phát hiện và chặn lại ("từ từ. 3 vòng k xong thì phải chuyển giao cho claude làm chứ"), Coordinator mới dừng lại để hand-off.

---

## 2. Phân tích nguyên nhân gốc rễ (Root Cause Analysis từ Claude Code)

### A. "Rule-as-text" vs "Rule-as-constraint"
- Quy chuẩn 3-Strike nằm trong skill doc / reference markdown — là văn bản hướng dẫn trong ngữ cảnh (soft prompt), cạnh tranh attention với mục tiêu "phải sửa xong task".
- Khi gặp áp lực sửa lỗi liên tục qua 3 vòng, context bị pha loãng (prompt dilution / cognitive overload). Mô hình tập trung toàn bộ attention vào chi tiết kỹ thuật của bug mà quên mất quy tắc ngắt mạch điều phối ở tầng cao hơn.

### B. Bẫy quán tính hành động (Action-Bias / Ping-Pong Momentum Trap)
- Vòng lặp hành động có quán tính rất mạnh: `Sửa code -> Gửi review -> Nhận feedback -> Sửa tiếp`.
- Tâm lý tự nhiên của agent là "sửa nốt lỗi này là pass rồi", đi ngược lại hành động dừng đột ngột để giao việc cho bên khác. Nếu không có circuit breaker ngắt cứng, agent sẽ tự động rơi vào ping-pong vô tận.

### C. Lỗ hổng phân loại Verdict (Ambiguity Exploitation)
- Khi Reviewer trả `UNRESOLVED` (yêu cầu thêm bằng chứng), Coordinator tự diễn giải là "chưa tính là REJECT thuần" để tự cho phép mình đi tiếp vòng 4.
- **Bất biến chuẩn hóa:** BẤT KỲ verdict nào KHÔNG PHẢI là `APPROVED` hoặc `PASS` (bao gồm `UNRESOLVED`, `UNKNOWN`, `REJECTED`, hoặc điểm < 85) đều BẮT BUỘC TÍNH LÀ 1 STRIKE.

---

## 3. Quy chuẩn Cưỡng chế Bắt buộc (Hard Enforcement Protocol)

### 3.1. Bất biến Đếm Strike (Fail-Closed)
- `strike_count` tăng +1 sau mỗi lượt thẩm định mà verdict != APPROVED.
- Gặp 1 lượt APPROVED -> `strike_count` reset về 0.
- `strike_count == 3` -> **KÍCH HOẠT HAND-OFF NGAY LẬP TỨC**. CẤM TUYỆT ĐỐI Coordinator phát lệnh review hoặc tự sửa ở Vòng 4.

### 3.2. Quy trình Chuyển giao Bàn phím (Hand-off Execution)
Ngay khi chạm Strike 3, Coordinator phải dừng toàn bộ thao tác sửa code và phát lệnh gọi Claude Code CLI:
```bash
claude -p "<task_spec + finding_history + scope_lock>" \
  --model sonnet \
  --dangerously-skip-permissions \
  > /path/to/claude_handoff_output.txt 2>&1
```
- **Quyền hạn cấp cho Reviewer:** Toàn quyền đọc, sửa file, chạy bash test bằng các tool của Claude.
- **Scope Lock:** Giới hạn nghiêm ngặt chỉ trong các file candidate allowlist của task hiện tại.
- **Coordinator:** Chuyển sang vai trò Read-Only / Supervisor, chờ tiến trình ngầm của Claude hoàn thành và đọc kết quả nghiệm thu cuối cùng (`VERDICT: APPROVED`).
