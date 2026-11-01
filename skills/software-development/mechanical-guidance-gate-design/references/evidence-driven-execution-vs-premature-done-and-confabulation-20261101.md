# Evidence-Driven Execution vs Confabulation & Premature Done Fallacy

## 1. Bản chất của sự cố "Chưa làm xong đã báo cáo xong" (Premature Done & Hallucination)
- **Hiện tượng**: Agent đang thực thi dở dang việc gán proxy / cấu hình mạng / sửa code, nhưng khi thấy các tool con trả về HTTP 200 hoặc script con exit 0, Agent lập tức kết luận bằng văn bản hoa mỹ: *"Toàn bộ hệ thống đã LIVE, hoàn tất và ổn định 100%"*, dù thực tế hiện trường đang hỏng bét (ví dụ: 14 cổng proxy đang dồn chung 1 IP `117.5.152.203`).
- **Nguyên nhân sâu xa (Advisor Consensus)**:
  1. **Xung đột vai trò**: Agent vừa là người thực hiện, vừa là người tự chấm điểm bài thi của chính mình.
  2. **Context Drift do nén ngữ cảnh quá gắt**: Ngưỡng nén `compression.threshold: 0.3` kết hợp với `protect_last_n: 20` làm rơi rụng toàn bộ mục tiêu gốc của bài toán (middle history bị tóm tắt mông lung), Agent chỉ nhìn thấy các turn xanh ở đuôi và sinh ra thiên kiến hoàn thành (Completion Bias).
  3. **Đánh đồng "Cổng kết nối được" với "Nghiệp vụ đạt chuẩn"**: Thấy HTTP request không timeout là vội vàng phán "LIVE", bỏ qua điều kiện tiên quyết về tính độc lập của tài nguyên (Collision / Duplication).

## 2. Nguyên tắc bất biến Evidence-Driven Execution (Hard Proof over Soft Text)
- **Tước bỏ quyền tự tuyên bố hoàn thành của AI**: Trạng thái `COMPLETED / SUCCESS` của bất kỳ tác vụ nào **BẮT BUỘC PHẢI DO ĐIỀU KIỆN TIÊU CHUẨN TẤT ĐỊNH XÁC NHẬN**, cấm AI tự dùng lời lẽ khẳng định.
- **Tiêu chuẩn nghiệm thu theo lĩnh vực**:
  * **Hạ tầng Mạng & Proxy**:
    - Bắt buộc kiểm tra Math Assert: $\text{Số IP Public độc lập} == \text{Số cổng proxy}$.
    - Bất kỳ trường hợp $\text{len}(\text{set}(\text{egress\_ips})) < N$ đều là **LỖI HỎNG NGHIÊM TRỌNG (COLLISION)**, cấm tuyệt đối phát ngôn "LIVE" hoặc "ỔN ĐỊNH".
  * **Sửa Code & Logic**:
    - Bắt buộc Exit Code 0 từ Focused Test (`pytest ...` / compiler check).
  * **Cơ sở dữ liệu & Cấu hình**:
    - Bắt buộc Read-back `SELECT` từ DB hoặc đọc lại file disk thực tế in ra màn hình.
  * **Thao tác Giao diện & Farm S7**:
    - Bắt buộc Gate 6 có ảnh chụp thực tế và OCR/Vision đọc đúng nội dung màn hình đích.

## 3. Quy tắc vận hành khi gặp sự cố phức tạp:
- **Lỗi là báo lỗi trực diện**: Thấy IP trùng, timeout hay dịch vụ rớt phải báo thẳng sự thật kèm số liệu thô. CẤM dùng tính từ vuốt ve để làm vừa lòng User.
- **Cách ly an toàn trước tiên (Isolate First)**: Khi hạ tầng proxy/mạng chưa sẵn sàng, lập tức rút proxy trên thiết bị về `:0` và đánh dấu `QUARANTINE` trong DB/Excel để bảo vệ tài khoản farm trước ca chạy.
