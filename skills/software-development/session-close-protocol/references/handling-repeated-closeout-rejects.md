# Kỷ luật xử lý khi Closeout Gate bị Reject lặp lại (User giục chốt phiên)

Khi user yêu cầu "Chốt phiên" nhưng code surgery đang bị AI Reviewer (OmniRoute / Sol :20129) reject lặp đi lặp lại:

1. **Giới hạn vòng lặp (Max 2 iterations)**:
   - Tối đa delegate 2 lần để sửa theo review comments.
   - Nếu reviewer vẫn tiếp tục reject các vấn đề mang tính lý thuyết hoặc kiến trúc quá rộng (ngoài phạm vi của patch contract ban đầu), trong khi mã nguồn đã qua kiểm tra cú pháp (`py_compile` exit code 0) và tiến trình runtime đang vận hành ổn định:
   - **Dừng ngay lập tức**, không cố chấp sửa thêm để rơi vào vòng xoáy delay.

2. **Giao tiếp chủ động & dứt khoát**:
   - Khi user hỏi "Xong chưa" hoặc "Ủa r nãy h nói xong ch chốt phiên r sao ch chốt v", tuyệt đối không im lặng, không đưa ra lời hứa hẹn mơ hồ và không giải thích kỹ thuật quá dài dòng.
   - Báo cáo thẳng vào trọng tâm:
     - Tình trạng mã nguồn thực tế (đã verify cú pháp, runtime đang chạy an toàn).
     - Điểm nghẽn review hiện tại (AI Reviewer đang bắt bẻ chi tiết gì).
     - Đề xuất giải pháp tức thì: Commit thẳng với ghi chú hoặc chờ duyệt.
