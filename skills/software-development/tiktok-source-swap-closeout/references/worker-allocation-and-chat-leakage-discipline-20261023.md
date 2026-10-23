# Kỷ Luật Phân Bổ Tài Nguyên (Worker 40 vs Worker 1) & Chống Rò Rỉ Suy Nghĩ Nháp

## 1. Định chuẩn phân bổ tài nguyên Cào vs Render (2026-10-23)
- **Tác vụ cào video (Scraping/Downloader):**
  - Đặt target đúng **40 video Shorts** sạch độc quyền (`min_videos = 40` / `target_count = 40`).
  - Sử dụng proxy MikroTik hoặc direct failover (`player_client: ['android']` trên YouTube Shorts).
- **Tác vụ Render (FFmpeg Batch Rendering):**
  - BẮT BUỘC đặt `--parallel 1` (**Worker 1**).
  - Lý do: Host farm chịu tải đồng thời nhiều tác vụ (ADB, scrcpy, Singbox, nuôi nick). Tăng parallel render ffmpeg sẽ chiếm dụng 100% CPU/GPU, gây crash các container hoặc gián đoạn luồng tự động nuôi nick.
  - Khi xử lý chuỗi va chạm đa máy: Viết launcher tuần tự, chờ tiến trình render máy trước kết thúc mới kích hoạt máy tiếp theo.

## 2. Kỷ luật phát ngôn của Coordinator (Chống rò rỉ suy nghĩ vào Chat)
- **Hiện tượng lỗi**: Model có xu hướng xuất các câu suy luận nháp ("LOOK AT THAT", "BINGO", "ĐỐI SOÁT...") vào trường `content` trong khi đang gọi `tool_calls`.
- **Cơ chế Gateway**: Hermes coi mọi chữ trong trường `content` là tin nhắn người dùng cần đọc và gửi thẳng ra Telegram API.
- **Kỷ luật bắt buộc**:
  - Khi phát lệnh gọi tool: BẮT BUỘC giữ `content` rỗng hoặc chỉ thông báo 1 dòng trạng thái ngắn gọn.
  - Toàn bộ phân tích, đối soát, kiểm tra logic phải được giữ kín trong luồng nội bộ, chỉ gửi tin nhắn tổng kết nghiệm thu khi tác vụ đã hoàn thành có bằng chứng.
