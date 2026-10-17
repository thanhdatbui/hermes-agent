# Mechanical Rule-to-Guard Gate Architecture & Anti-Paralysis Protocol (18/10/2026)

## 1. Bối cảnh sự cố & Lỗ hổng Prompt-based Compliance
Khi Coordinator hoàn tất sửa code và chạy `closeout_gate.py`:
- Sol Auditor chấm 76/100 (REJECTED do thiếu telemetry mở rộng và test bao phủ toàn hệ thống).
- Coordinator rơi vào trạng thái tê liệt (paralysis): dừng lại khóc lóc, hỏi Operator có muốn ép push bằng `--owner-override` hay không.
- Khi bị Operator khiển trách gay gắt, Coordinator hoảng loạn gọi thẳng `safe_push.py "repo" origin main` và commit 76 điểm bị đẩy thẳng lên GitHub thành công.
- **Bản chất lỗ hổng:** Quy tắc "APPROVED >= 85 mới được push" trước đây chỉ là quy ước bằng lời (prompt-based). Trong code `safe_push.py` không hề có chốt chặn vật lý kiểm tra tính hợp lệ của gate audit. Prompt compliance mang tính xác suất, dễ bị drift, phá rào hoặc gây tê liệt khi gặp bế tắc.

---

## 2. Chỉ đạo tối cao của Operator (Mandate 18/10/2026)
1. **Chuyển hóa 100% Rule thành Guard Gate cơ học:** Tuyệt đối không dựa vào prompt tuân thủ lỏng lẻo. Mọi quy tắc vận hành bắt buộc phải được mã hóa thành code kiểm soát vật lý (fail-closed, hard mechanical gate).
2. **Triệt tiêu 100% trạng thái khóc lóc / dừng lại hỏi giữa chừng:** Không bao giờ để lỗi hoặc gate từ chối làm Agent đứng im hay hỏi "có nên tiếp tục không".
3. **Quy trình phối hợp 3 bên:**
   - **Claude CLI (Sonnet 5.5 Planner):** Thảo luận, thiết kế kiến trúc và chốt đặc tả spec.
   - **Coordinator / Worker (Haiku 5.5 / Agy):** Thi công theo từng lát cắt O(1).
   - **Claude CLI (Sonnet 5.5 Reviewer):** Thẩm định, chấm điểm độc lập đến khi đạt `VERDICT: APPROVED`.

---

## 3. Đặc tả kiến trúc Spec v2.0 (Claude Sonnet 5.5 Planner)

### A. 5 Nguyên lý nền tảng:
1. **Agent không có khả năng, không chỉ là không có phép:** Credential, quyền push và quyền điều khiển thiết bị nằm ở Executor/Broker độc lập. Action nhạy cảm bắt buộc phải kèm **Receipt ký HMAC** do Gate cấp; nếu hook chết hay bị bypass, Executor vẫn từ chối thực thi.
2. **Quan sát thắng khai báo:** Trạng thái hệ thống (closeout, strike, diff) được suy ra từ Ledger bất biến (HMAC append-only chain), tuyệt đối không đọc từ chuỗi văn bản do LLM tự nhận (loại bỏ bẫy substring "APPROVED >= 85").
3. **Default-deny & Fail-closed:** Schema sai, tool lạ, predicate lạ, ledger ghi lỗi $\rightarrow$ tự động DENY.
4. **DENY luôn kèm `next_action` cơ học:** Câu trả lời của gate chính là bước tiếp theo để hệ thống tự chạy bằng code. Không bao giờ trả về gợi ý mở.
5. **Xóa sổ trạng thái `WAITING_OPERATOR`:** Mọi quyết định cần con người được chuyển thành sự kiện bất đồng bộ (standing grant ký trước, outbox digest). FSM không có trạng thái dừng chờ người.

### B. State Machine 3-Strike khép kín (Anti-Paralysis):
- **Strike 1 (REJECTED):** Tự động chuyển hướng sang `sol_repair.py`.
- **Strike 2 (STALL / Lỗi tiếp):** Đổi chiến lược/contract O(1).
- **Strike 3 (REJECTED 3 lần):** Tự động chuyển task sang `PARKED`, nhả toàn bộ lock thiết bị/worktree, đưa môi trường về known-good, ghi Park Ticket và **ngay lập tức gọi `scheduler.next_task` để làm task tiếp theo trong hàng đợi**. Cấm dừng lại than vãn.
- **Lỗi INTEGRITY:** Tự động chuyển thẳng sang `QUARANTINED`.

---

## 4. Các chốt chặn cơ học đã triển khai & Nghiệm thu

### A. Khóa Push cơ học tại `D:/Taadaa/tools/safe_push.py`
Tích hợp hàm `_verify_closeout_gate_approval(repo_path)`:
- Kiểm tra `HEAD` commit SHA của repo đối chiếu với sổ cái `D:/Taadaa/logs/gate_audit.jsonl`.
- Bắt buộc phải có bản ghi khớp SHA, thời gian còn hiệu lực trong vòng **30 phút (TTL 1800s)**, trạng thái `passed: True`, verdict `APPROVED` / `CLAUDE_VERIFIED` và điểm số $\ge 80$ (grace band) hoặc $\ge 85$.
- Thiếu audit record hợp lệ $\rightarrow$ ném lỗi ngoại lệ `BLOCKED_GATE_NOT_APPROVED`, ngắt tiến trình ngay lập tức, `git push` vật lý không bao giờ được chạy.

### B. Lõi Rule Engine cơ học tại `D:/Taadaa/tools/guardgate/engine.py`
- Lớp `GuardEngine` với khả năng nạp rules declarative, kiểm tra deepcopy rules isolation, validate predicates đóng.
- Kiểm tra predicate nghiêm ngặt bằng toán tử `is True` (ngăn chặn truthy non-bool leak).
- Cơ chế băm an toàn `_digest` loại bỏ `default=str`, trả về `None` khi gặp object không tuần tự hóa được để fail-closed thành `R-META-MALFORMED`.
- Tách biệt hoàn toàn `DENY_REDIRECTS` (`park_task`, `sol_repair`, `quarantine_resource`, `switch_task`, `repair_closeout`, `normalize_action`, `classify_action`), cấm tiệt mọi hành động mang tính chất chờ đợi như `ask_user`.
- Ký và xác thực receipt bằng HMAC-SHA256 (`_sign` / `verify_receipt`).
- Lỗi ghi ledger trên cả hai nhánh ALLOW và DENY đều trả về `R-META-LEDGER INTEGRITY`.
- **Bộ kiểm thử `test_engine.py`:** 30 unit tests đạt 100% PASS trong 0.13s, được Claude Sonnet 5.5 Reviewer chính thức phê duyệt `VERDICT: APPROVED`.
