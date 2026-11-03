# Host Reboot Gateway Half-Open Long-Polling Stall vs Auto-Resume Stuck Turn RCA

## 1. Hiện tượng & Tình huống (Post-Reboot Amnesia / Stall)
- Máy chủ / Windows Host vừa reset hoặc reboot xong.
- Người dùng thấy Gateway hoặc Telegram bot không phản hồi (>10 phút không có request nào lên OmniRoute `:20129`).
- **Phản xạ sai lầm của Agent**: 
  - Vội vàng kết luận "cần restart Gateway vì code chưa nạp vào RAM", bỏ qua sự thật hiển nhiên là *máy vừa reset thì Gateway đã tự động khởi động lại rồi*.
  - Đoán mò session đang chạy `omni-free` hoặc đổ lỗi bừa cho model free trong khi session không hề dùng `omni-free`.

## 2. Bản chất kỹ thuật & 2 Cơ chế nghẽn sau Reboot
1. **Half-Open TCP Socket trên Telegram Long-Polling (Silent Stall)**:
   - Khi máy host đột ngột reset/reboot, các kết nối TCP Long-polling (`https://api.telegram.org/bot.../getUpdates`) đang duy trì qua proxy (WARP socks5 / Viettel HTTP) bị ngắt bất ngờ không kịp bắt tay TCP FIN/RST.
   - Khi Windows khởi động lại và Gateway chạy lên, socket long-poll có thể rơi vào trạng thái ngậm (Half-Open). Phía Telegram Server vẫn tưởng kết nối cũ hoặc giữ hàng đợi, tin nhắn gửi trên Telegram hiển thị 2 dấu tick `✓✓` nhưng không được push về Gateway cho đến khi Keepalive timeout (thường từ 5–12 phút).
2. **Auto-Resume Khôi phục Turn kẹt (Tool Execution / Command Timeout ngâm)**:
   - Khi Gateway khởi động lại sau crash/reboot, cơ chế `preserve_in_flight_sessions` khôi phục lại các session đang dở dang (`active_agents: N`).
   - Nếu trước khi reboot, session đang thực thi lệnh terminal nặng hoặc tool call bị gián đoạn, khi resume lại Hermes có thể ngâm chờ timeout kịch trần (mặc định trần timeout lên tới 600s / 10 phút).
   - Trong suốt thời gian này, agent không thể hoàn tất turn để gửi request tiếp theo lên OmniRoute, tạo ra khoảng mù 10 phút trên Dashboard OmniRoute (`TI: 0 | TO: 0`).

## 3. Quy trình Chẩn đoán O(1) Bắt buộc
1. **Kiểm tra thời điểm Gateway khởi động**:
   - Đọc `gateway_state.json` hoặc lệnh Python kiểm tra `create_time` của process `pythonw.exe`.
   - Nếu `create_time` khớp thời điểm boot máy $\rightarrow$ Gateway đã tự restart, KHÔNG yêu cầu restart lại lần nữa.
2. **Kiểm tra OmniRoute liveness trực tiếp**:
   - Bắn HTTP POST test trực tiếp vào `http://192.168.110.123:20129/v1/chat/completions` với model active (ví dụ `ag-gemini-pool-3`, `gemini-web`, `ag-sonnet`).
   - Nếu trả về HTTP 200 trong 2–6s $\rightarrow$ OmniRoute bình thường, vấn đề nằm ở tầng Polling/Session của Gateway.
3. **Giải phóng ngay lập tức**:
   - Hướng dẫn người dùng gửi `/new` hoặc `/reset` ngay trong topic/thread bị treo để ngắt turn ngâm và hủy bỏ trạng thái kẹt dở dang.
