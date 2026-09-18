# Proactive Sol Planner & Action-First Watchdog Guidelines (2026-09-19)

## 1. Bài học về Lệch pha giữa "Execution Hook" và "Cognitive Phase" (Vì sao sếp phải nhắc gọi Sol?)

### Vấn đề:
- Pre-tool hook `guard_dispatch_contract.py` chỉ chặn ở giây phút gọi `delegate_task` nếu thiếu `SOL_PLAN_ID`.
- Tuy nhiên, trong pha chẩn đoán (Investigation & Chat Phase), Coordinator hay rơi vào bẫy thụ động: tìm ra bug xong thì chat giải thích dài dòng với user, tự thảo luận giải pháp rồi hỏi "Sếp duyệt để em làm", mà không chạy Sol.
- Hậu quả: User phải nhắc "Sao không gọi Sol lên plan?".

### Quy tắc khắc phục triệt để:
- **Tiên đề nhận thức (Cognitive Invariant)**: Ngay khi chẩn đoán xác định nguyên nhân là lỗi logic code (Non-T0), Coordinator **BẮT BUỘC gọi `python D:/Taadaa/tools/sol_planner.py` NGAY TRONG LƯỢT ĐÓ**.
- Đề xuất giải pháp gửi cho User phải đi kèm luôn `SOL_PLAN_ID`, chẩn đoán từ Sol và bảng phân rã Task (T1..Tn).
- CẤM TUYỆT ĐỐI đề xuất suông hoặc xin duyệt mà chưa có Sol Plan.

---

## 2. Tiêu chuẩn Báo cáo Watchdog Farm (Action-First Session Delta)

### Vấn đề của báo cáo cũ:
- In snapshot tĩnh từ database chậm cập nhật hoặc Workbook (vd: "Đã có 240/532 acc, còn 292 máy chưa up").
- Gom cụm mù mờ dạng `Khác (26)`.
- Không thể hiện được trong ca chạy vừa rồi hệ thống đã làm được những gì, up được bao nhiêu máy, máy nào lỗi.

### Chuẩn hóa báo cáo Action-First:
Mọi báo cáo tổng kết watchdog/cron phải có đủ 4 phần:
1. **Khung giờ & Quy mô ca**: Thời gian chạy thực tế, số batch đã kích hoạt.
2. **Session Delta (Thành quả trong ca)**:
   - Số máy thành công mới (+X acc): liệt kê danh sách máy cụ thể.
   - Số máy thất bại mới: liệt kê danh sách máy kèm mã lỗi rõ ràng.
3. **Bóc tách nhóm Bỏ qua (Safe Skip)**:
   - Dưỡng sinh (Organic Rest): danh sách máy.
   - Age-gate / Nick ngâm < 10 ngày: danh sách máy.
   - Thiếu video / chưa render: danh sách máy.
   - TUYỆT ĐỐI CẤM gom chung thành `Khác (N)`.
4. **Luỹ kế toàn Farm**: Tiến độ tổng thể và số máy còn tồn sau ca.
