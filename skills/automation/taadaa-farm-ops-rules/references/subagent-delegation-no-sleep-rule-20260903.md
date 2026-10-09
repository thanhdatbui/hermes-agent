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

## 4. Tránh Khoảng Lặng Quá Lâu Khi Worker Đang Chạy (> 5-10 Phút)
- **Anti-Pattern:** Giao phó câu hỏi tra cứu farm cho subagent rồi im lặng hoàn toàn suốt 30-60 phút. Khi worker gặp trục trặc mạng/timeout hoặc phân tích quá sâu, user không nhận được thông tin và cho rằng hệ thống đang bị treo hoặc quét đĩa diện rộng.
- **Quy tắc khắc phục:**
  1. **Triage O(1) Nhanh Tại Phiên Chính:** Với các thắc mắc về số liệu run ("tại sao máy fail", "tại sao follow skip"), Coordinator đọc nhanh file tổng kết `summary.txt` của batch gần nhất tại `D:/Taadaa/runtime/kibe/live/<today>/<run_dir>/summary.txt` (đọc 1 file trong 2 giây, không quét đĩa). Trả lời ngay số liệu tổng quan (ví dụ: 26 máy dính `skipped-device-locked`, 34 máy skip do `under-5-videos`).
  2. **Cập nhật tiến độ chủ động:** Nếu task phân tích mã nguồn/sửa code cần worker chạy lâu, báo sơ bộ hiện trạng cho user trước, không để khoảng lặng quá 5-10 phút.
