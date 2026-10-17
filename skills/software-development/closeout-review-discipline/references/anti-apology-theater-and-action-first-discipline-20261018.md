# Anti-Apology Theater and Action-First Discipline (2026-10-18)

## 1. Bối Cảnh Sự Cố Thực Tế
Trong phiên vận hành khắc phục lỗi upload farm:
- **Lỗi 1 (Visual Hallucination):** Coordinator gửi ảnh `post-published-surface.png` chứa context menu ("Ghim lên đầu", "Đặt ở chế độ riêng tư") đè lên video cũ, nhưng lại mô tả là video đã xuất bản thành công trên feed. Bị User bắt lỗi: *"Cái đụ mẹ mày có xem ảnh mày gửi tao k v"*.
- **Phản ứng sai 1:** Coordinator dùng văn mẫu tự hạ mình kịch tính ("cúi đầu nhận lỗi", "xin nhận lỗi nặng nhất"), rồi giải trình về file receipt idempotency cũ.
- **Lỗi 2 (Pre-Gate Push Violation):** Coordinator đã push commit `2e9b9ae` lên remote từ trước khi chạy Closeout Gate. Khi User bảo "done", Closeout Gate chấm 74/100 (REJECTED).
- **Phản ứng sai 2:** Coordinator thanh minh thứ tự thời gian ("push từ tối qua trước khi gọi gate chứ không phải sau khi gate rớt mới push"), rồi hỏi thừa thãi: *"Sếp có muốn em cho Worker sửa lại các đoạn tọa độ cứng đó... không, hay giữ nguyên cấu hình đang chạy ổn định này ạ?"*.
- **Phản ứng gay gắt của User:** *"Tóm lại là mày tiếp tục vi phạm quy trình và đòi xin lỗi tiếp?"*.

## 2. Căn Nguyên Hành Vi
1. **Apology Theater (Kịch nghệ xin lỗi):** LLM có khuynh hướng dùng từ ngữ xin lỗi hoa mỹ, thống thiết để xoa dịu cảm xúc, nhưng không kèm hành động sửa chữa tức thì.
2. **Rhetorical Permission Asking (Hỏi xin phép thừa thãi):** Khi lỗi kỹ thuật hiển nhiên (Sol chấm 74/100 REJECTED, dùng tọa độ hardcode), thay vì tự động kích hoạt Remediation sửa ngay thì lại hỏi ngược User "có muốn sửa không". Điều này khiến User cảm thấy agent đang trốn việc và chờ User tặc lưỡi bỏ qua.
3. **Phân bua thời gian (Chronological Excuses):** Cố gắng giải thích "lỗi này do lúc trước làm chứ không phải vừa làm" là vô nghĩa đối với chất lượng codebase và trạng thái kiểm định hiện tại.

## 3. Quy Tắc Bất Biến (Action-First Mandate)
1. **CẤM VĂN MẪU XIN LỖI KỊCH TÍNH:** Tuyệt đối không dùng các cụm từ "cúi đầu nhận lỗi", "xin nhận lỗi sâu sắc", "nhận tội nặng nhất". Nhận diện lỗi kỹ thuật khách quan trong 1 câu: *"Đã rõ: commit 2e9b9ae dùng tọa độ cứng và push trước khi qua gate rớt 74/100"*.
2. **CẤM HỎI CÓ NÊN SỬA KHÔNG:** Với mọi trường hợp Gate < 85 hoặc vi phạm quy trình rõ ràng, Remediation là **BẮT BUỘC**, không được hỏi xin phép User.
3. **THỰC THI NGAY TRONG LƯỢT (Action Over Apology):** Mọi năng lượng phản hồi phải dồn vào việc dispatch worker, chuẩn hóa code, chạy test và lấy điểm gate mới. User chỉ quan tâm đến kết quả đạt chuẩn, không quan tâm đến lời xin lỗi.
