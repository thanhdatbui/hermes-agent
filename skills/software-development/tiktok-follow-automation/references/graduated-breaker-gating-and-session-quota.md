# Graduated Breaker Gating, IP vs Trust Score & Session Quota

## 1. Cạm bẫy đối soát Cầu Dao: 0 Proxy Ngắt != 0 Dính Nhả
- **Cơ chế phân tầng ngắt IP (`follow_state.py`):**
  * `trip_ip_breaker()` được thiết kế CÓ CHỌN LỌC: CHỈ giật cầu dao ngắt proxy khi tài khoản bị nhả là **Nick Cấp Khỏe / Đã Tốt Nghiệp (`was_graduated is True`)**.
  * Với **Nick Non / Chưa Tốt Nghiệp (`was_graduated is False`)**: Hệ thống chỉ phạt Cooldown tài khoản (3 - 15 ngày tùy streak), **KHÔNG ngắt IP Circuit Breaker**.
  * *Lý do thiết kế:* Tránh việc nick non thiếu trust tự chết làm sập oan proxy của các máy anh em khỏe mạnh.
- **Quy tắc đối soát bất biến cho Coordinator:**
  * **CẤM TUYỆT ĐỐI** kết luận "toàn farm sạch sẽ, không dính nhả" chỉ dựa vào việc bảng `ip_circuit_breaker` có 0 proxy bị ngắt mới.
  * BẮT BUỘC đối soát hiện trường qua các file state: `runs/state/follow_state_*.json` tìm `last_failed_date == today` hoặc `reason` chứa `bị nhả` / `FOLLOW_FAILED`.

## 2. Quy luật Hiện trường: IP Sạch vs Trust Score của Nick (Thực nghiệm 12/10/2026)
- **Hiện tượng:**
  * Sáng (08:14): Proxy vừa mãn hạn 48h (cực sạch), các nick tốt nghiệp Row 2 (M17, M23: >220 ngày tuổi, >10 video) chạy Module 2 follow mượt mà 12 - 14 lượt (100% trúng nick farm).
  * Trưa (12:14): Cùng các máy và IP đó, khi chuyển ca sang Row 4 (nick non, probation), tất cả các nick non nhảy vào đều bị TikTok nuốt/nhả ngay lượt đầu tiên (`anchor @... bị nhả sau vuốt`).
- **Bài học vận hành:**
  * Tình trạng bị nhả follow không đồng nghĩa với proxy bẩn hay đứt kết nối. Thuật toán TikTok kiểm tra nghiêm ngặt Inbound Trust của nick.
  * Nick non khi chưa đủ tích lũy tương tác/tuổi nick rất dễ bị silent-drop dù chạy trên dải IP tĩnh sạch nhất.

## 3. Trần Quota Mỗi Phiên (Session Quota Standardization)
- **Chuẩn hóa quota mỗi phiên:** `budget_per_session_min = 10`, `budget_per_session_max = 15` (trước đây là 10 - 20).
- **Phân bổ:**
  * 1 ca gồm 2 phiên: mỗi phiên chạy 10 - 15 lượt $\rightarrow$ tổng ngày đạt 20 - 30 follow cho nick tốt nghiệp.
  * Nick `probation_tier1`: Chỉ cấp 1 - 2 follow/ngày để đo phản ứng thuật toán.
  * Nick `probation_tier2`: Cấp 5 - 8 follow/ngày.
