# TikTok Tracker & Dashboard Invariants (Metrics, History API & SVG Chart)

## 1. Bản chất chỉ số sức khỏe kênh TikTok (Follower & Tim vs View)
- Profile công khai TikTok (`https://www.tiktok.com/@username`) KHÔNG có trường tổng view toàn kênh (`playCount` chỉ gắn trên từng video riêng lẻ).
- Tuyệt đối KHÔNG cào sâu từng video để gom tổng view cho farm quy mô lớn (~1.000 nick) vì số request nhân lên 5-10x sẽ làm sập proxy pool và dính SlardarWAF / Rate-limit của TikTok.
- Thước đo sức khỏe chuẩn xác và an toàn nhất là:
  * **Followers**: Độ giữ chân & tăng trưởng kênh.
  * **Tim (Hearts)**: Tương tác thực tế của video (video có view tự khắc tim tăng; video 0 view/flop thì tim đứng im `delta_heart = 0`).
  * **Đã Follow (Following)**: Tiến độ nuôi / follow chéo & tự nhiên.
  * **Số Video**: Tần suất up video.

## 2. Thiết kế History API & Query Optimization
- Endpoint `/api/history?username=...`:
  * Query bảng `snapshots` theo `username = ?` với index `(username, timestamp ASC)`.
  * Gom theo ngày (`substr(timestamp, 1, 10)`): Lấy bản ghi snapshot mới nhất trong ngày.
  * Tính delta giữa các ngày liên tiếp (`delta_follower`, `delta_following`, `delta_heart`, `delta_video`).
  * Gắn kèm thông tin máy & phân cụm (`farm_account_info`: `may`, `host_id`, `cluster`).
  * Đảm bảo truy vấn trả về < 1ms, không khóa SQLite.

## 3. Kiến trúc SVG Line Chart nội tại (Zero External Dependencies)
- Dashboard single-file HTTP server (`tiktok_dashboard.py`) không dùng thư viện ngoài nặng nề.
- SVG Line Chart tự động scale với `viewBox="0 0 600 220"`:
  * `linearGradient` cho vùng fill gradient dưới đường line.
  * `polyline` vẽ đường chỉ số chính xác theo tọa độ tính toán tự động.
  * `circle` tại từng mốc ngày kèm tooltip tương tác hover/touch hiển thị ngày + số lượng + delta.
  * Tích hợp thanh pill-buttons chuyển 4 chỉ số: Follower, Tim, Đã Follow, Video.
  * Kèm bảng lịch sử mini tóm tắt chi tiết bên dưới biểu đồ.

## 4. Dispatcher Instruction cho Monolith / Single-File Server
- Khi Coordinator đã xác định 100% anchor và code contract, prompt dispatch worker CẤM cho worker dùng `read_file` đọc lại từ đầu tới cuối file lớn (tránh cạn budget 15 calls).
- Ép worker thực thi lệnh cập nhật trực tiếp qua 1 lệnh terminal script Python và chạy test / restart server ngay.
