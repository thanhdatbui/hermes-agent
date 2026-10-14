# Telegram Reporting Hygiene & Cron Delivery Architecture

## 1. Context & Motivation (Anti-Spam & Operational Clarity)
Trong các hệ thống tự động hoá quy mô lớn (như Phone Farm với hàng chục thiết bị hoặc hàng chục cron jobs chạy ngầm), việc để các tiến trình nền tự do in stdout vào kênh trao đổi chính (`origin`) dẫn đến:
- Làm loãng ngữ cảnh điều phối (Context Bloat), khiến Coordinator và người vận hành bị ngợp trong đống log thô.
- Gây lỗi mất thread định tuyến: `configured thread_id <ID> was not found; delivered without thread_id` khi topic đích bị thay đổi hoặc đóng.

## 2. Mô hình "Hộp Thư Agent" (Agent Mailbox & Topic Routing)
Áp dụng kiến trúc phân luồng tin nhắn qua Telegram Forum Topics / Channels:
1. **Interactive Control Lane (`origin` / DM Topic):**
   - Chỉ dùng cho lệnh điều phối trực tiếp từ người dùng và phản hồi của Coordinator.
   - Chỉ nhận cảnh báo khẩn cấp cấp độ P0 (sập toàn bộ farm, đứt mạng, cháy nổ, deadlock).
2. **Executive Summary Lane (Topic Báo Cáo Định Kỳ):**
   - Nhận báo cáo tổng kết của các ca (Ca 1/2/3, Báo cáo 6h, Báo cáo cuối ngày).
   - Chỉ hiển thị Executive Summary ngắn gọn (xem chuẩn ở Mục 3).
3. **Raw Telemetry / Debug Lane (Local Files / Debug Topic):**
   - Log chi tiết từng bước, stacktrace, danh sách từng máy: KHÔNG in ra stdout của bot.
   - Lưu trữ tại file tĩnh: `D:/Taadaa/reports/<date>/<task_name>.md` hoặc `runtime/audit_logs/`.

## 3. Quy chuẩn Executive Summary (Mobile-First Dashboard)
Mọi script watchdog hoặc cron runner khi gửi báo cáo về Telegram bắt buộc tuân thủ format <= 10 dòng (vừa vặn 1 màn hình điện thoại):

```text
📊 [BÁO CÁO CA / PHIÊN: TIKTOK FEED]
• Trạng thái: ✅ HOÀN THÀNH (Ca 1 - 3 phiên)
• Sức khỏe Farm: 78/80 máy ONLINE (97.5%)
• Tiến độ Slot: 234/240 slots PASS (97.5%)
• Cần can thiệp: 2 máy (M12: Captcha, M45: Rớt Wi-Fi)
📁 File chi tiết: D:/Taadaa/reports/2026-10-15/feed_ca1.md
```

## 4. Kỷ luật cấu hình Cron Delivery Targets
Khi tạo hoặc cập nhật cron job qua `cronjob(action='create'|'update')`:
1. **CẤM TUYỆT ĐỐI** dùng `deliver: origin` cho các watchdog chạy ngầm chu kỳ ngắn (<= 15 phút).
2. **Watchdog nội bộ / Silent Healer:** Dùng `deliver: local` kết hợp `no_agent: true`. Script thiết kế theo pattern watchdog im lặng: chỉ in stdout khi có sự cố thật sự; khi bình thường stdout = rỗng (không gửi gì).
3. **Báo cáo định kỳ:** Trỏ đích danh về Channel/Topic chuyên biệt qua `deliver: telegram:<chat_id>:<thread_id>` thay vì dùng `origin`.

## 5. Tách biệt Pipeline Stateless Media (Cloud Decoupling)
Đối với các pipeline không liên quan trực tiếp đến thiết bị vật lý (như cào video Douyin/YouTube, transcode ffmpeg, bóc transcript, dịch thuật, render):
- **CẤM CHẠY TRÊN HOST ĐIỀU KHIỂN FARM:** CPU/RAM/Network spikes từ ffmpeg và yt-dlp làm nghẽn bus USB, gây rớt ADB và timeout ATX-agent.
- **MÔ HÌNH CLOUD RUNNER:**
  - Đóng gói pipeline media thành standalone runner độc lập trên Cloud VPS / Docker / Grok Bot.
  - Kết nối qua Cloud Storage trung gian (OneDrive, S3, Rclone).
  - PC Farm chỉ thực hiện thao tác O(1): nhận video thành phẩm đã sync về đĩa để nạp vào thiết bị.
