# Multi-Cluster Farm Synchronization & Alert Architecture (2026-09-21)

## 1. Bản chất phân bố cụm Farm (Kibe vs Admin)
- **Cụm Kibe (Local)**: Máy 1–80, kết nối USB direct, trạm đặt tại Thái Bình.
- **Cụm Admin (Remote)**: Máy 201–280, kết nối LAN socket TCP `.119:5037`, trạm máy đặt tại Đà Nẵng.
- Hai cụm đặt tại hai tỉnh thành khác nhau, sử dụng 2 pool proxy 4G tách biệt (khác dải IP và ASN).

## 2. Timing & Synchronization (Có cần Delay giữa 2 cụm không?)
- **Quy tắc**: **GIỮ NGUYÊN CHẠY CÙNG GIỜ, KHÔNG THÊM DELAY**.
- **Lý do kỹ thuật**:
  1. Hai cụm ở 2 địa lý và dải IP hoàn toàn độc lập nên không có tương quan mạng để TikTok phát hiện cụm (cluster detection).
  2. Runner đã tích hợp sẵn **Session Jitter (1–3 phút)** + **Machine Stagger (2–8s/máy)** + **Randomize Machine Order**. 80 máy mỗi bên tự động rải đều thời gian mở app trong suốt 7–10 phút, không có hiện tượng burst đồng loạt 1 giây.
  3. Thêm delay 15–20 phút làm xé nhỏ lịch scheduler và kéo dài thời gian vô ích.

## 3. Quy chuẩn Báo cáo: Watchdog Session Report vs Batch Alert
- **Watchdog Report cuối phiên (`feed_session_watchdog.py`)**: BẮT BUỘC gộp 1 tin nhắn duy nhất toàn Farm (`【FARM KIBE】` và `【FARM ADMIN】`).
- **Batch Alert lỗi hệ thống (`batch_aggregator.py`)**: Tự động bắt cặp Sibling (`runtime/kibe` ↔ `runtime/admin`) để gộp lỗi của cả 2 cụm thành **1 tin nhắn duy nhất `【TOÀN FARM】`**, kèm marker `.sent` chống gửi lặp.

## 4. Giao tiếp & Kỷ luật phản hồi với User
- Khi user hỏi dấu `?` hoặc `.` hoặc thể hiện bực mình: Tuyệt đối không dùng văn mẫu xin lỗi lòng vòng hay nịnh bợ.
- Trả lời trực diện vào câu hỏi chính (CÓ / KHÔNG / NGUYÊN NHÂN CỤ THỂ) trong 1–2 câu đầu tiên.
