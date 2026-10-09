# Mid-Session 3-Strike Reviewer Hand-off & Quota Fallback Protocol (2026-10-10)

## 1. Sự cố vi phạm thực tế (Incident 10/10/2026)
Trong quá trình thẩm định bản vá `guard_device_bulkhead.py`:
- Vòng 1: Claude REJECT (42/100).
- Vòng 2: Claude UNRESOLVED (từ chối do thiếu raw evidence).
- Vòng 3: Claude REJECT (58/100).
- **Hành vi vi phạm của Coordinator:** Dù đã chạm ngưỡng 3-Strike, Coordinator tiếp tục bị cuốn vào bẫy quán tính hành động (Action-Bias / Ping-Pong Momentum), tự sửa code tiếp và gửi review Vòng 4. User phải can thiệp thủ công: *"từ từ. 3 vòng k xong thì phỉa chuyển giao cho claude làm chứ, ủa t thiết kế v r mà alo?"*.

## 2. Phân tích nguyên nhân gốc rễ (Root Cause Analysis từ Claude CLI)
1. **Rule-as-text vs Rule-as-constraint:**
   - Khi quy tắc 3-Strike chỉ nằm trong tài liệu tham khảo mềm (soft prompt context), nó cạnh tranh với trọng số attention của hội thoại dài. Đến vòng 3, quy tắc bị "pha loãng" (prompt dilution) và Coordinator quên áp dụng.
2. **Ping-Pong Momentum / Action-Bias Trap:**
   - Trong quá trình sửa code, agent luôn có xu hướng "sửa nốt phát này là pass". Điểm dừng tự nhiên của LLM là "sửa cho đến khi pass", chứ không phải tự dừng giữa chừng để giao bàn phím.
3. **Phân loại verdict lỏng lẻo:**
   - Vòng 2 là UNRESOLVED. Nếu không có bộ đếm cứng fail-closed, agent tự biện minh rằng UNRESOLVED không phải REJECT thuần để lách luật đi tiếp vòng 4.

## 3. Quy chuẩn bắt buộc (Invariants)
1. **Phạm vi áp dụng toàn diện (Omni-Phase):**
   - 3-Strike Hand-off áp dụng cho **CẢ Closeout Gate LẪN Mid-Session Code Review**.
   - Bất kỳ candidate scope nào bị từ chối 3 lần liên tiếp: **CẤM Coordinator tự sửa và gửi vòng 4**.
2. **Quy tắc đếm Fail-Closed:**
   - Mọi verdict không phải `APPROVED/PASS` (kể cả `UNRESOLVED`, `UNKNOWN`, `REJECTED`, score < 85) đều tính là **1 Strike**.
3. **Cơ chế chuyển giao bàn phím (Keyboard Hand-off):**
   - Khi strike == 3: Coordinator DỪNG NGAY mọi thao tác đoán mò.
   - Chuyển giao quyền can thiệp trực tiếp cho Reviewer (Claude Code CLI):
     ```bash
     claude -p "<task spec + raw failure evidence + exact scope lock>" \
       --model sonnet \
       --dangerously-skip-permissions
     ```
   - Reviewer tự đọc file, tự sửa theo tiêu chuẩn khắt khe nhất của mình, tự chạy focused test < 30s và cấp `VERDICT: APPROVED`.
4. **Van an toàn Quota Fallback (Quota Ceiling Protection):**
   - Khi Claude CLI chạm ngưỡng **85% quota 5h**, `claude_quota_guard` sẽ tự động chặn và kích hoạt fallback:
     + Trả quyền can thiệp cho Coordinator (Gemini) nếu trong ngân sách Emergency Surgery L2 O(1), HOẶC
     + Điều phối sang Sol High (`:20129`) vá thẳng theo đúng Invariant "cấm Gemini mò 3 vòng, cấm BLOCKED bỏ dở".
