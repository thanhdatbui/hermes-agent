# Mid-Session Review 3-Strike Hand-off and Quota Fallback (2026-10-09)

## 1. Bối cảnh & Hiện tượng (The Mid-Session Review Blindspot)
Protocol 3-Strike ban đầu được thiết kế gắn liền với `closeout_gate.py` (chốt phiên). Tuy nhiên, trong các đợt **thẩm định code giữa phiên (Mid-Session Review Loop)** — ví dụ khi sửa hook, script tools, hoặc các tính năng kỹ thuật mà Coordinator tự invoke `claude -p`:
- Vì không chạy qua `closeout_gate.py`, không có counter tự động trong `gate_audit.jsonl` ngắt mạch.
- Coordinator rơi vào **Bẫy quán tính hành động (Action-Bias / Ping-Pong Momentum)**: sửa code -> gửi review -> bị reject -> tiếp tục tự sửa vòng 4, vòng 5... thay vì dừng lại chuyển giao bàn phím cho Reviewer (Claude CLI).
- User đã phải trực tiếp can thiệp chặn họng: *"từ từ. 3 vòng k xong thì phải chuyển giao cho claude làm chứ, ủa t thiết kế v r mà alo?"*

## 2. Quy chuẩn 3-Strike cho Mid-Session Review
Bất kể là cuối phiên (Closeout) hay giữa phiên (Mid-Session):
1. **Quy tắc Strike Count:**
   - Mỗi lần Reviewer từ chối (REJECT) hoặc từ chối cấp verdict do thiếu bằng chứng (UNRESOLVED) đều tính là **1 Strike**.
   - Strike 1 & Strike 2: Coordinator / Worker tiếp thu nhận xét, sửa code trong phạm vi cho phép, chạy test focused < 30s và gửi lại.
   - **Strike 3 (Hard Stop):** Chạm ngưỡng 3 lần liên tiếp không đạt -> **CẤM TUYỆT ĐỐI Coordinator tiếp tục đoán mò hoặc tự sửa ở vòng 4!**
2. **Kích hoạt Hand-off (Đưa bàn phím cho Reviewer):**
   - Coordinator chuyển giao toàn bộ quyền sửa trực tiếp cho Claude Code CLI:
     ```bash
     claude -p "<task_spec + scope_lock + finding_history>" --dangerously-skip-permissions --model sonnet
     ```
   - Phạm vi khóa cứng (Scope Lock): Claude CLI CHỈ được sửa các file đã khai báo trong scope, tự chạy test, tự nghiệm thu và đưa ra verdict chính thức.

## 3. Van an toàn Quota Fallback (Khi Claude CLI chạm ngưỡng giới hạn)
User ra chỉ thị rõ ràng về mối quan hệ giữa Hand-off và Quota Guard:
> *"Nhưng nếu claude chạm mức budget quota t thiết kế thì vẫn fallback về cho coordinator sửa chứ"*

**Nguyên tắc Fallback:**
1. **Ưu tiên bàn phím:** Khi chạm Strike 3, Claude CLI luôn là lựa chọn số 1 để dứt điểm bất đồng kỹ thuật.
2. **Kiểm tra Quota Guard trước khi gọi:** Luôn kiểm tra `claude-limit-protection` (ngưỡng an toàn 85% quota 5h, lockout state).
3. **Kích hoạt Fallback khi Quota cạn:** Nếu Claude CLI bị chặn bởi quota guard (hoặc trả về lỗi 429 / quota limit):
   - **KHÔNG ĐƯỢC ĐÓNG BĂNG SESSION.**
   - Kích hoạt cơ chế Fallback theo thứ tự:
     + **Nấc 1 (Sol High - Port :20129):** Điều phối sang Sol High vá thẳng theo Invariant *"Gate reject: Sol High (:20129) vá thẳng, cấm Gemini mò 3 vòng, cấm BLOCKED bỏ dở"*.
     + **Nấc 2 (Coordinator Emergency Surgery L2):** Nếu thỏa mãn điều kiện exact diff O(1) (≤ 2 files, ≤ 30 dòng, test focused < 30s, offline/mocked), Coordinator được phép tự vá lần cuối kèm tiền tố commit `[L2-surgery]`.
     + **Nấc 3 (L3 BLOCKED kèm Evidence):** Nếu cả Sol High và L2 đều không khả thi, đánh dấu L3 BLOCKED có bằng chứng đầy đủ, tuyệt đối không spam thêm các vòng review vô nghĩa.
