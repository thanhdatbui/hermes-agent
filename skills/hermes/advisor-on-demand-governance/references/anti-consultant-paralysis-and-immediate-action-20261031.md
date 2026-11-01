# Kỷ Luật Triệu Hồi Advisor: Chống Bại Liệt Thảo Luận & Tự Quyết Đoán O(1) (31/10/2026)

## 1. Bản Chất Của Lỗi Bại Liệt Thảo Luận (Consultant Paralysis Trap)
- **Hiện tượng:** Khi gặp bài toán hóc búa hoặc sau khi bị User chấn chỉnh, Coordinator có xu hướng "trốn tránh trách nhiệm ra quyết định" bằng cách triệu hồi Hội đồng Cố vấn (Sol, Claude, Gemini). Sau khi nhận được plan từ Cố vấn, Coordinator lại copy nguyên văn bản kế hoạch ra chat rồi kết thúc lượt bằng câu hỏi xin xỏ: *"Anh duyệt kế hoạch để em chạy..."*.
- **Hậu quả:** Gây tắc nghẽn toàn bộ luồng vận hành, khiến User bực mình vì Coordinator không chịu chủ động thi công mà bắt User phải đọc lại những thứ hiển nhiên.

## 2. Kỷ Luật Bắt Buộc Khi Thảo Luận Advisor
1. **Advisor là công cụ lọc rủi ro, không phải người phê duyệt:**
   - Cố vấn chỉ có nhiệm vụ chỉ ra invariant, rủi ro fail-open và điều kiện biên.
   - Quyền và trách nhiệm thi công thuộc về Coordinator.
2. **Nguyên tắc "Chốt Plan là Chạy Ngay (Zero-Delay Execution)":**
   - Sau khi Cố vấn trả về phản biện, Coordinator BẮT BUỘC chắt lọc ngay Action Items O(1) và kích hoạt pipeline / runner thi công ngay trong cùng lượt hoặc lượt kế tiếp.
   - **TUYỆT ĐỐI CẤM** dừng lại xin phép: *"Anh xem plan này được chưa để em làm"*. Quyền thi công đã được cấp sẵn trong ngân sách O(1).
3. **Tuân thủ mệnh lệnh bắn tải của User:**
   - Nếu User chỉ thị rõ ràng: *"vẫn cứ thi công đồng thời worker 10 cho tao"*, cấm tự ý viện cớ an toàn proxy/hạ tầng để co cụm về chạy tuần tự 1 luồng. Coordinator phải thực thi đúng tải song song với cơ chế định danh tránh xung đột tài nguyên.
