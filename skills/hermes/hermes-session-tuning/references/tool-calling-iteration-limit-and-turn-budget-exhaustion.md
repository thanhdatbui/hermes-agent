# Tool-Calling Iteration Cap, Budget Exhaustion & Anti-Paralysis Protocol

## 1. The "Maximum Tool-Calling Iterations" Trap

### Triệu chứng & Bối cảnh
Khi xử lý các chuỗi tác vụ phức tạp trong một turn duy nhất (ví dụ: chuỗi vá code nhiều file, chạy test suite, kích hoạt Closeout Gate, đối soát kết quả review, và chạy remediation loop), Coordinator hoặc Worker đột ngột bị runtime ngắt họng bằng prompt cưỡng chế:
```text
You've reached the maximum number of tool-calling iterations allowed. Please provide a final response summarizing what you've found and accomplished so far, without calling any more tools.
```

### Nguyên nhân kỹ thuật trong nhân Hermes
1. **Trần lặp per-turn (`agent/chat_completion_helpers.py` & `conversation_loop.py`)**:
   - Runtime của Hermes hoặc client harness có một hằng số giới hạn số vòng lặp gọi công cụ trong một turn đơn lẻ (mặc định là 15 hoặc 25 tool calls liên tiếp).
   - Mục đích thiết kế ban đầu: Ngăn chặn model rơi vào vòng lặp vô tận (infinite loop) khi gặp tool lỗi liên tục.
   - Hệ quả tiêu cực: Với các chuỗi vận hành chuẩn công nghiệp đòi hỏi nhiều bước kiểm tra và sửa lỗi tuần tự, trần này vô tình trói tay Agent ngay trước khi kịp hoàn thành bước cuối cùng (như lệnh commit hoặc chạy lại Closeout Gate Strike 2).

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
