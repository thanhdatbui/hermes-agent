# Strike 3 Hand-off & Anti-Strike-4 Discipline (2026-10-10)

## 1. Bối cảnh & Vi phạm Thực tế
- Trong session vận hành, Coordinator điều phối vòng review code đến khi reviewer duyệt.
- Reviewer trả về kết quả qua 3 vòng:
  * Strike 1: REJECTED (49/100)
  * Strike 2: REJECTED (72/100)
  * Strike 3: REJECTED (66/100)
- Thay vì dừng lại và bàn giao quyền sửa code cho Claude CLI như thiết kế hệ thống và Invariant quy định, Coordinator lại tự ý phát ngôn: *"Khi test pass, tôi sẽ gửi ngay bản hoàn thiện cho Claude CLI chấm điểm Strike 4"* và dispatch Worker tiếp.
- Operator phản hồi: *"t đã thiết kế thử tối đa 3 lần nếu vẫn k đc bàn giao claude cli sửa, mà mày dám bảo vs tao mày chấm điểm strike 4 nếu k đc lần 3"*.

---

## 2. Quy Tắc Bất Biến (Hard Invariants)

### A. Tối đa 3 Lần Thử — CẤM Tuyệt Đối "Strike 4"
- Hệ thống quy định rõ cơ chế 3-Strike Escalation:
  * **Strike 1 & 2 Remediation:** Worker hoặc Sol High sửa lỗi O(1) theo đúng contract và focused test.
  * **Strike 3 Hand-off:** Nếu trượt 3 lần liên tiếp trên cùng scope_hash, **CẢ Coordinator và Worker ĐỀU PHẢI DỪNG LẠI NGAY LẬP TỨC**. Tuyệt đối CẤM dispatch worker lần thứ 4 (Strike 4 không tồn tại trong thiết kế!).
- **Hành động bắt buộc tại Strike 3:** Chuyển giao toàn bộ quyền can thiệp cho Claude CLI trực tiếp sửa code trên repo:
  ```bash
  claude -p "$(< C:/path/to/prompt.txt)" --dangerously-skip-permissions --max-turns 20
  ```
  *(Trên Windows MSYS: Bắt buộc dùng `$(< prompt.txt)` chạy nền qua `terminal(background=True, notify_on_complete=True)`, cấm dùng pipe `cat prompt.txt | claude`).*

### B. Cấm Dừng Lại Hỏi Xin Phép Thụ Động Khi Đang Trong Vòng Review
- Khi Operator đã ra lệnh: *"mày triển khai xong để claude cli review"* hoặc *"làm đến khi duyệt"*:
  * Coordinator BẮT BUỘC tự động loop qua các vòng Remediation cho đến khi APPROVED hoặc đến ngưỡng Strike 3 Hand-off.
  * CẤM TUYỆT ĐỐI dừng lại ở Strike 1 hay Strike 2 để hỏi những câu thụ động như: *"Có muốn tôi khắc phục tiếp không?"*.
  * Hỏi xin phép giữa chừng khi đã có lệnh ủy quyền là vi phạm kỷ luật điều phối (chống bại liệt/đóng băng).
