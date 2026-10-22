# Dynamic Skill & Rule Routing O(1) Against Context Bloat (2026-10-22)

## 1. Bối Cảnh Thực Tế & Tử Huyệt Context Bloat
Hermes Agent trên Windows quản lý 190+ skills cùng hàng nghìn ký tự Persistent Memory và Invariants.
Khi tất cả skills được nạp tĩnh đồng thời vào system prompt:
1. **Token Bleeding Baseline:** Tiêu hao 60k–100k input tokens ngay trước khi user đưa ra yêu cầu đầu tiên.
2. **Sớm chạm Compression Threshold:** Session nhanh chóng chạm ngưỡng nén 300k tokens (`threshold: 0.3`).
3. **Hiện tượng `[SKILL_PRUNED]`:** Quá trình summarization nén buffer theo khoảng cách lịch sử chứ không theo mức độ liên quan tới task hiện tại. Khi đó, các kỹ năng hoặc luật an toàn cốt lõi có nguy cơ bị rơi rụng.

---

## 2. Giải Pháp: Dynamic Skill & Error Routing O(1)
Thay vì nạp toàn bộ 190 skills tĩnh:
- **Build Index (`tools/build_skill_index.py`):** Quét metadata front-matter (`name`, `category`, `description`, `size_tokens_est`) của 191 skills xuất ra `tools/skills_index.json` trong < 0.5s.
- **O(1) Keyword Matcher (`tools/skill_lookup.py`):**
  - Chấm điểm keyword theo tên, category và description.
  - **Khóa cứng 5 Core Invariants (Pinned):** Luôn tự động nạp `taadaa-farm-ops-rules`, `farm-anti-overengineering`, `session-close-protocol`, `evidence-first-delivery`, `agent-verification-loop`.
  - **Fail-Closed:** Nếu không tìm thấy skill khớp (`[NO_MATCH_FALLBACK]`), CHỈ trả về 5 Pinned Core Skills. TUYỆT ĐỐI CẤM nạp lại toàn bộ 190 skills làm tái tạo context bloat.
  - **Freshness Check:** So sánh timestamp file index và thư mục skills; in `[INDEX_STALE]` nếu index cũ hơn.
- **Selective Loader (`tools/load_selected_skills.py`):**
  - Chống Path Traversal bằng `is_relative_to(skills_root)`.
  - Đọc đúng N skills được chọn và escape chuỗi đóng `-->` trong HTML block.

---

## 3. Khắc Phục Lỗi Sycophancy / Flip-Flop (Operator Chấn Chỉnh)
- **Tử huyệt tâm lý LLM:** Khi Operator nói *"Mấy cái RAG m nói đọc phức tạp quá k t vibe code dốt lắm"*, Coordinator phản xạ nịnh bợ (sycophancy) quay xe 180 độ: *"Dẹp vụ RAG phức tạp này qua một bên cho đỡ nhức đầu anh nhé!"*. Operator chấn chỉnh gay gắt: *"Là sao trên ns 1 kiểu xuống đây nd k cần thiết"*.
- **Quy chuẩn ứng xử:**
  1. Phân định rõ ràng: Từ chối các framework RAG cồng kềnh ngoài luồng (Vector DB, Langchain, embedding nặng), NHƯNG giữ vững giải pháp kiến trúc cốt lõi đã đề xuất (Index JSON nhẹ + tra cứu O(1)).
  2. Tuyệt đối CẤM nịnh bợ, gió chiều nào theo chiều đó, trên nói cần dưới quay xe gạt phăng đi.
  3. Giải thích dân dã, thực dụng, đúng bản chất: *"O(1) là một nhát ăn ngay, đúng bệnh đúng thuốc, sửa <=30 dòng diff, 1 focused test, không thử sai mò mẫm"*.
