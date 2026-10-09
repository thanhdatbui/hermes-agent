# Evaluating Third-Party Skill Frameworks and Plugins (e.g. obra/superpowers)

## 1. Bối cảnh & Hiện tượng
Người dùng hoặc cộng đồng thường đề xuất tích hợp các bộ framework phương pháp luận bên ngoài (như `obra/superpowers`, `speckit`, v.v.) vào Hermes Agent nhằm cải thiện chất lượng coding và lập kế hoạch.

Tuy nhiên, trước khi tích hợp bất kỳ plugin hay bộ skill bên ngoài nào, Coordinator bắt buộc phải phân tích kỹ cơ chế thực thi bên dưới (hooks, prompt injections, context overhead) thay vì chỉ nhìn vào lời giới thiệu tính năng.

---

## 2. Vì sao KHÔNG cài đặt toàn bộ framework dạng Plugin có Hook cưỡng chế?
Nhiều framework (như `obra/superpowers`) khi đóng gói cho Hermes Agent thường sử dụng hook vòng đời:
- Khai báo `provides_hooks: [pre_llm_call]` trong `plugin.yaml`.
- Tại `__init__.py`, hàm `pre_llm_call` tự động tiêm một đoạn bootstrap markdown rất dài (`<EXTREMELY_IMPORTANT>... You have superpowers... Follow it now...`) vào đầu mọi phiên hoặc mọi turn.

### Các xung đột nghiêm trọng:
1. **Phá vỡ vai trò Coordinator O(1) & Farm Safety Invariants**:
   - Bootstrap của framework bên ngoài thường ép agent: *"Bắt buộc hỏi rõ yêu cầu, brainstorming trước khi làm bất kỳ hành động nào, cấm sờ vào code hay thăm dò file khi chưa thông báo skill..."*.
   - Trong hệ thống điều phối tác vụ nhanh / cứu hộ Phone Farm, khi nhận Farm Alert `[MÁY N]`, Coordinator cần trích xuất O(1) (`inspect_machine.py <N>`), định vị anchor duy nhất và dispatch worker ngay. Nếu bị bootstrap chặn lại để "phỏng vấn/brainstorming", quy trình ứng cứu sẽ bị tê liệt hoàn toàn.
2. **Analysis Paralysis & Vi phạm Anti-Overengineering**:
   - Ép quy trình cồng kềnh cho các tác vụ vận hành (run batch, check live, triage lỗi nhỏ), biến một thao tác 1 bước thành cuộc hội thoại dài dòng.
3. **Context Bloat & Chậm trễ (TTFT Overhead)**:
   - Việc tiêm hàng ngàn tokens bootstrap vào prompt mỗi phiên làm phình context vô ích, tốn token chi phí và tăng độ trễ phản hồi của LLM.

---

## 3. Bản chất: Prompt Nagging vs Tooling/Contract Enforcing
- **Mô hình Prompt Nagging (Framework ngoài như Superpowers)**: Dùng prompt dài để nài nỉ/đe dọa agent tự giác tuân thủ quy trình. Mô hình này rất mong manh khi gặp context dài hoặc model reasoning tầm trung.
- **Mô hình Tooling/Contract Enforcing (Kiến trúc chuẩn Hermes Taadaa)**:
  * Phân vai rạch ròi: Coordinator O(1) không sửa code trực tiếp; Worker làm việc trong sandbox độc lập qua `delegate_task`.
  * Ràng buộc bằng Hook vật lý và Hard Gates: 5 Gates Anti-Insanity, Gate 6 Visual Evidence (`MEDIA:`), và Closeout Gate độc lập (`closeout_gate.py` exit code 0).
  * Ràng buộc bằng Compiler Phase (Sol Planner Tầng A sinh Patch Contract đóng trước khi dispatch).

---

## 4. Quy trình Cherry-Pick & Adapt an toàn
Khi phát hiện một framework ngoài có ý tưởng hay, **tuyệt đối không cài cả plugin**:
1. **Bóc tách từng Skill đơn lẻ**: Kiểm tra thư mục `skills/` của framework đó (ví dụ: `systematic-debugging`, `test-driven-development`, `writing-plans`).
2. **Loại bỏ Bootstrap cưỡng chế**: Bỏ toàn bộ cơ chế hook `pre_llm_call` hoặc các câu lệnh ép buộc chào hỏi/hỏi vặn vô lý.
3. **Bản địa hóa vào thư mục Skill nội bộ**: Lưu dưới dạng skill gọi theo nhu cầu (`skill_view`) hoặc gắn vào task instructions của Worker subagent khi dispatch.
4. **Kiểm tra độ trùng lặp**: Luôn kiểm tra thư viện skill hiện có trước khi thêm mới để tránh làm phình danh mục skill (`skills_list`).
