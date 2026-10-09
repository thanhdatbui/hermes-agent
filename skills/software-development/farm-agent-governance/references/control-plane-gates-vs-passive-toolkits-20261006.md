# Triết Lý Kiến Trúc: Control Plane Gates vs. Passive Toolkits (06/10/2026)

## 1. Bối Cảnh & Vấn Đề Thực Tế Từ Cộng Đồng

Trong thực tế ứng dụng AI Coding Agent (Codex, Claude Code, GPT), cộng đồng lập trình viên thường vấp phải hai "bệnh án" kinh điển:

1. **Chất lượng trồi sụt (45–65%) & Cãi cùn quy tắc:**
   - Đưa toolkit cho model, nhét graph/quy tắc vào system prompt.
   - Khi chạy sai hoặc bỏ sót kế thừa, model phản hồi biện minh: *"Do bạn không yêu cầu kế thừa nên tôi không làm"*.
   - Nguyên nhân: **Context Bleed & Stochastic Drift**. Càng nhét nhiều hướng dẫn và graph vào context window, tín hiệu quy tắc càng bị suy hao. LLM bản chất là công cụ dự đoán token xác suất, không phải máy trạng thái bất biến; dùng prompt để ép duy trì Invariants là sai công cụ.

2. **Vòng lặp Review vô tận ("Mấy chục round chưa sạch bug"):**
   - Cho Agent lên plan $\rightarrow$ thực thi từng bước $\rightarrow$ đưa lại cho chính Agent (hoặc LLM khác) review bằng prompt cho tới khi hết bug.
   - Kết quả: sửa bug A đẻ ra bug B, loop hàng chục round tốn token mà không sạch bug.
   - Nguyên nhân: **Self-Referential Trap & Thiếu Deterministic Test Harness**. Review thuần văn bản (prompt review) là ảo giác chồng ảo giác. Không có bộ harness khách quan làm mốc tham chiếu thực tế, agent rơi vào trò chơi đập chuột (Whack-a-Mole).

---

## 2. So Sánh Bản Chất: Toolkit vs. Control Plane Gate

| Tiêu chí | "Toolkit (khoá bằng code)" | Hệ thống Gate / Control Plane (Taadaa/Hermes) |
| :--- | :--- | :--- |
| **Bản chất** | **Passive Tooling** (Thư viện hàm, function calling). Agent tự quyết định khi nào gọi, gọi cái gì. | **Deterministic Control Plane** (Khung điều khiển cưỡng bức ngoài band). Nằm ngoài tầm can thiệp của LLM. |
| **Cơ chế thực thi** | **Stochastic (Xác suất):** Dựa vào System Prompt để nài nỉ LLM "hãy nhớ dùng tool", "hãy tuân thủ rule". | **Mechanical (Cơ học):** Cắm chốt ở tầng Hook hệ điều hành / Subprocess (`guard_*.py`, AST parser, exit code). |
| **Quyền lực** | Agent-driven (Agent nắm quyền điều phối). | Engine-driven State Machine (Hạ tầng nắm quyền sinh sát). |
| **Khi vi phạm** | LLM giải trình, cãi cùn, đùn đẩy trách nhiệm. | **Fail-closed lập tức:** Exit Code $\neq$ 0, chặn write/commit ở cấp OS, rollback state. |
| **Kiểm tra kết quả** | LLM tự đọc code review bằng mắt (ảo giác). | **Evidence-first:** Verification Receipt (pytest offline mock, `py_compile`, visual screenshot `MEDIA:`). |

> **Quy tắc định danh:**
> - **Toolkit** là *cái búa, cái kìm* đưa vào tay Agent.
> - **Gate** là *hệ thống đường ray, vô lăng và phanh khẩn cấp* nhốt Agent vào một hành lang cơ học chuẩn xác.

---

## 3. Năm Trụ Cột Cơ Học Chặn Đứng Thất Bại Của Agent

1. **Physical OS / Subprocess Hooks (Không tin vào sự tự giác):**
   - Các file guard (`guard_selector_change.py`, `guard_dispatch_contract.py`, `pre-commit`) chặn trực tiếp các lệnh vi phạm.
   - Cố tình quét đĩa bừa bãi (`search_files` root) $\rightarrow$ Hook OS chặn đứng (`[GUARD_SEARCH_FILES_ROOT]`).
   - Cố tình thêm pattern trốn việc (`safe_skip`, `return True`) $\rightarrow$ Pre-commit từ chối commit ngay lập tức.

2. **O(1) Scope Lock (Khoá bán kính sát thương):**
   - Giới hạn cứng thay đổi: $\le 2$ files, $\le 30$ dòng diff, 1 focused test $< 30$s.
   - Ngăn chặn triệt để tình trạng Agent "tự ý refactor", sửa lan man sang các module khác.

3. **Invariants Ngoài Band Thay Vì Dặn Dò Trong Prompt:**
   - Các quy tắc kiến trúc (kế thừa, schema, typing) được chuyển hoàn toàn thành **AST Linter & Static Analysis**.
   - Nếu vi phạm: Gate trả về mã lỗi kèm dòng AST trace cụ thể. LLM buộc phải sửa đúng lỗi kỹ thuật đó, không có cơ hội tranh luận hay đổ lỗi cho người dùng.

4. **Circuit Breakers & Fail-Fast Cứng (Gate 3 & Gate 4):**
   - Quy định tối đa 2 lần thất bại cấu trúc (Structural failure).
   - Worker trong $\le 3$ iterations nhận thấy scope bất khả thi bắt buộc **ABORT ngay** và trả về anchor + contract đề xuất, cấm đốt hết budget rồi fail im lặng.
   - Thang leo thang tuần tự L0 $\rightarrow$ L1 $\rightarrow$ L2 (Emergency Surgery) $\rightarrow$ L3 BLOCKED có bằng chứng thật $\rightarrow$ L4 Clarify. Triệt tiêu hoàn toàn thảm họa chạy mấy chục round review lãng phí.

5. **Independent Quantitative Closeout Gate (`closeout_gate.py`):**
   - Thẩm định độc lập bằng model chuyên trách (Sol Auditor) chấm điểm theo Scorecard 100 điểm với ngưỡng cứng $\ge 85/100$.
   - Chỉ nghiệm thu khi có đủ Verification Receipt: pytest pass 100%, diff sạch, không dính anti-skip, và log/canary thực tế.

---

## 4. Đúc Kết Kiến Trúc

> **"LLM chỉ là động cơ sinh mã (Engine). Hệ thống Gate mới là khung gầm, hệ thống lái và phanh ABS."**
> 
> Động cơ có thể bất định tùy ý, nhưng chiếc xe chỉ được phép lăn bánh trên đúng đường ray sắt mà Control Plane đã khóa cứng. Mọi nỗ lực nâng cao độ tin cậy bằng cách kéo dài prompt hay vẽ thêm graph đều thất bại nếu thiếu hệ thống cưỡng chế cơ học bằng code ngoài band.
