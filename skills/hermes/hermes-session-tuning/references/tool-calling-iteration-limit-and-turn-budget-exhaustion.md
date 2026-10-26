# Tool-Calling Iteration Cap, Budget Exhaustion & Anti-Paralysis Protocol

## 1. The "Maximum Tool-Calling Iterations" Trap

### Triệu chứng & Bối cảnh
Khi xử lý các chuỗi tác vụ phức tạp trong một turn duy nhất (ví dụ: chuỗi vá code nhiều file, chạy test suite, kích hoạt Closeout Gate, đối soát kết quả review, và chạy remediation loop), Coordinator hoặc Worker đột ngột bị runtime ngắt họng bằng prompt cưỡng chế:
```text
You've reached the maximum number of tool-calling iterations allowed. Please provide a final response summarizing what you've found and accomplished so far, without calling any more tools.
```

### Nguyên nhân kỹ thuật chính xác trong nhân Hermes
1. **Cơ chế đếm & ngắt nhịp per-turn (`agent/conversation_loop.py` & `turn_finalizer.py`)**:
   - Mỗi turn chat, `turn_context.py:258` tạo mới ngân sách: `agent.iteration_budget = IterationBudget(agent.max_iterations)`.
   - Vòng lặp chính tại `conversation_loop.py:789`:
     `while (api_call_count < agent.max_iterations and agent.iteration_budget.remaining > 0)...`
   - Mỗi lần model gọi tool, `api_call_count` tăng 1 và `iteration_budget.consume()` trừ 1 slot.
   - Khi hết budget (`remaining <= 0`), `turn_finalizer.py:82-97` phát hiện và gọi `agent._handle_max_iterations(messages, api_call_count)`.
   - Hàm `chat_completion_helpers.py:1738` tước bỏ toàn bộ công cụ và bơm prompt cưỡng chế:
     `"You've reached the maximum number of tool-calling iterations allowed. Please provide a final response summarizing what you've found and accomplished so far, without calling any more tools."`

2. **Nguồn gốc con số 20 lượt (`api_calls=20/20 budget=20/20`)**:
   - `gateway/run.py:1399` đọc `_current_max_iterations()` từ `HERMES_MAX_ITERATIONS` trong `.env` hoặc `agent.max_turns` trong `config.yaml`.
   - Nếu trong `config.yaml`, session profile, hoặc channel override đặt `max_turns: 20`, Agent sẽ bị khóa cứng trần 20 tool calls cho mỗi user turn. Với các task DevOps/Coding phức tạp (vừa patch code, vừa chạy focused test, vừa gọi closeout review, vừa remediation), 20 lượt là quá hẹp.

---

## 2. Kỷ Luật Phản Ứng: Chống Bại Liệt & Chống Khóc Lóc (User Correction 26/10/2026)

### Anti-Pattern: Bại Liệt / Buông Xuôi ("Khóc Lóc")
- Khi bị runtime ép dừng bằng câu nhắc trên, Agent thường có phản xạ tâm lý sai lầm: Coi như task đã thất bại, viết văn phong than vãn, buông tay tóm tắt hiện trường rồi dừng lại chờ đợi mà không nêu rõ bước hành động tiếp theo.
- **Phản ứng của Operator**: Cực kỳ bực mình vì Agent "đang làm giữa chừng bỗng dưng đứng im khóc lóc" (`"là sao mày đéo hoàn thành, mà dừng lại khóc lóc? Tao hỏi lí do mày dừng lại bại liệt"`).

### Rule: Bộ đếm Reset theo Turn mới — Sẵn sàng Thực thi Tức thì
1. **Hiểu rõ bản chất cơ học**: Trần lặp tool-calling **chỉ có hiệu lực trong đúng 1 turn hội thoại đó**. Ngay khi Operator gửi tin nhắn tiếp theo (bất kể ngắn gọn như `"Done"`, `"Làm"`, hay `"Làm tiếp đi"`), bộ đếm lượt gọi tool **được reset về 0 hoàn toàn**.
2. **Quy tắc phản hồi chuẩn khi bị trần ép dừng**:
   - **CẤM** phân trần dài dòng, than thở hay xin lỗi sáo rỗng.
   - **Xác nhận ngắn gọn 3 điểm**:
     1. Những gì ĐÃ LÀM XONG (kèm bằng chứng test/diff cụ thể).
     2. Điểm nghẽn kỹ thuật duy nhất còn lại (ví dụ: đang chờ chạy Closeout Gate vòng 2).
     3. **Cam kết hành động dứt điểm ở turn sau**: Nêu rõ đúng 1 lệnh O(1) sẽ thực thi ngay khi Operator kích hoạt turn mới (không để Operator phải đoán).

---

## 3. Giải Pháp Tinh Chỉnh & Nâng Trần Runtime (Engine Tuning)

### Nâng trần trong nhân Hermes
- Trong `D:\Taadaa\Hermes\agent\chat_completion_helpers.py`: Nâng `MAX_TOOL_CALL_ITERATIONS` từ 25 lên **`100`** hoặc **`200`** để tương thích hoàn toàn với cấu hình `agent.max_turns: 200` trong `config.yaml`.
- Trong `agent/iteration_budget.py`: Đảm bảo các công cụ kiểm chứng read-only (như `git status`, `read_file`, `pytest`) có cơ chế refund hoặc không tính gộp vào budget sửa đổi để tránh cạn kiệt ngân sách sớm.
