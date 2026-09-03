# Quy Tắc Điều Phối Subagent (Coordinator-Worker Delegation) (2026-09-03)

## 1. Cơ Chế Bất Đồng Bộ Của Hermes Delegation
- Lệnh `delegate_task` của Hermes Agent chạy hoàn toàn ở chế độ **background (bất đồng bộ)**.
- Khi dispatch task thành công, tool trả về ngay lập tức với `status: dispatched`.
- Subagent làm việc độc lập trong sub-session và sub-terminal riêng biệt.
- Khi subagent hoàn thành, runtime của Hermes tự động gom toàn bộ kết quả tóm tắt và đẩy thẳng vào cuộc hội thoại như một tin nhắn mới (`[ASYNC DELEGATION BATCH COMPLETE — deleg_...]`).

## 2. Anti-Pattern: Vòng Lặp `sleep` Chờ Subagent
- **Hiện tượng lỗi:** Sau khi gọi `delegate_task`, Coordinator trong session chính liên tục gọi lệnh `sleep 15` / `sleep 10` trong terminal để block phiên làm việc nhằm chờ worker kết thúc.
- **Hậu quả:**
  1. Triệt tiêu hoàn toàn tính đa nhiệm bất đồng bộ của hệ thống.
  2. Khiến người dùng trên Telegram thấy bot bị im lặng, treo đơ suốt 10-15 phút không phản hồi.
  3. Gây khó chịu và làm gián đoạn khả năng điều hướng / tương tác của người dùng.

## 3. Quy Tắc Vận Hành Chuẩn Xác (Best Practice)
1. **Phản hồi ngay sau khi Dispatch:**
   - Ngay sau khi gọi `delegate_task`, Coordinator gửi ngay thông báo ngắn gọn cho người dùng: "Đang phân công worker thực hiện task X...".
   - Tuyệt đối KHÔNG gọi lệnh `sleep` để giữ terminal.
2. **Tiếp tục trao đổi & sẵn sàng nhận lệnh mới:**
   - Phiên chính hoàn toàn rảnh rỗi để giải đáp thắc mắc, nhận lệnh mới hoặc chuẩn bị các khâu tiếp theo.
3. **Tiếp nhận kết quả tự động:**
   - Khi có tin nhắn `[ASYNC DELEGATION BATCH COMPLETE]`, Coordinator đọc tóm tắt kết quả, kiểm tra lại artifact/code diff và chạy các bước verification / closeout tiếp theo.
