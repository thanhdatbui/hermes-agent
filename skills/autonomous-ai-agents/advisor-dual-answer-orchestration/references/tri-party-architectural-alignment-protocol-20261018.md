# Tri-Party Architectural Alignment Protocol (Coordinator + Sol + Claude)

## 1. Bối Cảnh Khi Kẹt Xung Đột Chính Sách (Policy Deadlock)
Khi hệ thống rơi vào xung đột giữa các cơ chế an toàn (ví dụ: Quality Gate Strict 85 vs Grace Band 80-84):
- Coordinator có xu hướng dao động giữa hai cực đoan: hoặc xóa bỏ Grace để ép điểm gây tê liệt vòng lặp, hoặc nới lỏng Grace biến thành đường vòng bỏ qua Gate.
- Sol Auditor tập trung vào phê bình, vạch lá tìm sâu các rủi ro tĩnh và edge case AST/Scope.
- Claude Planner tập trung vào thiết kế hệ thống, phân rã mô hình dữ liệu và cơ chế ký số token.

## 2. Quy Trình Hội Chẩn 3 Bên (Tri-Party Consultation Workflow)
1. **Bước 1 — Tham vấn Phản Biện Sol (:20129 `review`):**
   - Đặt câu hỏi phản biện trực tiếp tới Sol: "Làm sao để cơ chế ngoại lệ X hoạt động mà không xung đột với nguyên tắc bất biến Y?".
   - Thu thập các nguyên tắc phân định trách nhiệm từ góc nhìn auditor (Ví dụ: Strict 85 là Quality Gate mặc định; Grace 80-84 là CONDITIONAL_PASS, không phải generic pass).
2. **Bước 2 — Thiết Kế Kiến Trúc Khớp Nối Qua Claude Planner (`claude_worker.py --role planner`):**
   - Chuyển toàn bộ nguyên tắc phản biện của Sol sang Claude Planner để thiết kế hợp đồng dữ liệu, schema policy (`closeout_policy.json`), và hàm thẩm định duy nhất (`gate_common.py`).
   - Thiết lập nguyên tắc Single Source of Truth: Downstream tools (`safe_push`, `pre-push`) bị cấm hardcode logic so sánh ngưỡng; bắt buộc import và gọi hàm kiểm tra chung từ `gate_common`.
3. **Bước 3 — Đối Soát Toàn Diện Bởi Coordinator:**
   - Coordinator rà soát toàn bộ call-sites (`git grep`) trong hệ thống để tìm các điểm xung đột tiềm tàng: tên biến verdict, regex bắt buộc, format audit log, timeout và quota limits.
   - Chốt giải pháp bảo đảm tính tương thích ngược 100% trước khi thi công.
