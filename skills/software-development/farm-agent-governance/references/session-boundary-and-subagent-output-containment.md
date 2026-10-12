# Kỷ luật Ranh giới Session Context & Chống Xả Rác Output Subagent

## 1. Sự cố Điển hình (Incident Lesson — 2026-10-12)
Trong session xử lý nhiệm vụ: *"Tách file đó ra từng script từng việc, xong cron chỉ việc gọi từng script chạy cho đủ"*
- **Hành vi sai lầm của Coordinator:**
  1. Thay vì chỉ thực hiện việc chia tách cấu trúc module ở mức độ gọi (caller orchestration) cho session Cron, Coordinator lại nhầm lẫn ranh giới và kéo toàn bộ luồng nghiệp vụ sâu của session khác (bóc OTP qua Graph API/Webmail, xử lý CDP, bypass đăng nhập Hotmail) vào chỉnh sửa.
  2. Coordinator dispatch liên tục nhiều subagent nền (`delegate_task`). Mỗi khi subagent hoàn thành, nền tảng Hermes tự động phun nguyên khối `[ASYNC DELEGATION BATCH COMPLETE — deleg_...]` kèm toàn bộ log kỹ thuật dài hàng trăm dòng trực tiếp vào luồng chat Telegram của User.
  3. User phản ứng gay gắt:
     > *"Cái gì thế? ... Chứ mấy worker kia làm của session khác lq đến hotmail mắc gì gửi bậy vào đây ... K hiểu à. Worker kia là của session hotmail khác. Còn đây là session cron tách? Thì mắc gì ném output lung tung v"*

## 2. Quy tắc Điều phối Cốt lõi (Core Governance Rules)

### A. Giữ Sạch Ranh Giới Session (Context Boundary Hygiene)
- **Tập trung đúng phạm vi:** Khi User yêu cầu tách script cho cron chạy, phạm vi DUY NHẤT là:
  - Tách các khối code thành từng file độc lập có trách nhiệm đơn lẻ ($Single\ Responsibility$).
  - Nối cronjob hoặc script runner gọi tuần tự các file đó.
  - TUYỆT ĐỐI KHÔNG lấn sân sang sửa chữa logic nghiệp vụ sâu của session khác trong cùng một thread chat.

### B. Kỷ luật Quản lý Output của Subagent (Subagent Output Containment)
- **Tránh fan-out background bừa bãi:** Không dispatch nhiều subagent chạy nền liên tiếp trong các tác vụ tái cấu trúc cơ học. Ưu tiên giải quyết dứt điểm trong 1 lượt với scope tối thiểu.
- **Hấp thụ và lọc nhiễu:** Khi subagent nền hoàn thành và trả kết quả về qua thông báo tự động của harness, Coordinator:
  - CẤM lặp lại hoặc ném nguyên khối summary/trace log của subagent vào tin nhắn gửi User.
  - CHỈ phản hồi ngắn gọn 1-2 dòng về trạng thái hoàn thành của task hiện tại.
  - Khi User hỏi tiến độ, báo cáo trực diện vào kết quả cuối cùng, không giải thích vòng vo về tiến trình subagent nội bộ.
