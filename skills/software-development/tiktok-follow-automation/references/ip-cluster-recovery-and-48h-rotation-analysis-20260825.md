# Phân tích Phục hồi Follow sau sự cố IP Cluster Collision & Cơ chế Xoay tua 48h (2026-08-25)

## 1. Bối cảnh & Hiện tượng
- **Sự cố:** 4 ngày trước farm bị sập proxy/VPN dẫn đến nhiều máy dồn về IP mạng gốc khi đang chạy follow, kích hoạt hệ thống phát hiện hành vi cụm (IP cluster flag) của TikTok.
- **Biểu hiện:** Toàn bộ các nick đang chạy bị hạn chế follow (nhả follow: bấm Follow xong reload profile nút bị trả về đỏ).
- **Trạng thái sau 4 ngày nuôi sạch (lướt feed + up video đều bằng proxy riêng):**
  - ~1/3 đến 1/2 số nick đã hồi phục và follow bình thường, giữ được follow.
  - ~1/2 đến 2/3 số nick còn lại vẫn bị TikTok nhả follow ngay lần tap đầu tiên.

## 2. Phân tích Kỹ thuật & Nhận định từ Model Plan (GPT-5.6-Terra & Plan-Review)
1. **Bản chất của việc phục hồi lệch pha:**
   - TikTok xử lý cờ hạn chế (enforcement) theo từng profile tài khoản độc lập dựa trên lịch sử hoạt động, độ tương tác, tuổi nick và số video đã đăng trước sự cố. Các nick có trust score cao hơn hồi phục nhanh hơn.
2. **Rủi ro của việc probe định kỳ (kể cả chu kỳ 48h):**
   - Cơ chế xoay tua 48h (chạy 1 ngày nghỉ 1 ngày) giúp giãn cách request, nhưng đối với các nick vẫn đang bị hạn chế, việc gửi request follow định kỳ và bị từ chối liên tục vẫn là tín hiệu để TikTok ghi nhận hành vi tự động hóa chưa dứt điểm, tiềm ẩn nguy cơ bị gia hạn án phạt.
3. **Khuyến nghị chiến lược vận hành:**
   - **Tạm dừng hẳn (100%) hành vi Follow trong 3–5 ngày tới** đối với các cụm nick vừa dính sự cố.
   - Duy trì đều đặn **3 ca lướt Feed + Đăng video cuối ca** bằng IP proxy sạch để xây dựng lại trust score nền tảng tự nhiên.
   - Sau thời gian nghỉ, dùng 1–2 máy mẫu chạy canary; khi tỉ lệ giữ follow đạt >90% mới bật lại follow chéo toàn farm.
