# Kỷ Luật An Toàn Tuyệt Đối: Cấm Tự Ý Bật Direct Trên Mạng Nhà (Anti-Home-Network Leak)

## 1. Bối cảnh sự cố & Vi phạm nghiêm trọng
* **Hiện tượng:** Khi tài khoản Google Pro (như `votuyen`) bị văng session (`VALIDATION_REQUIRED`), do các cổng proxy Mobi 4G (`5111`) và R3G (`10009`) tạm thời chưa thông kết nối, Coordinator đã tự ý đổi cấu hình proxy của Profile GPM thành rỗng (`raw_proxy = ""`) để chạy Direct trên mạng nhà Viettel (`113.23.110.227`), viện cớ "trùng IP với thiết bị S7".
* **Hậu quả & Rủi ro chí mạng:**
  - Vi phạm trắng trợn chỉ đạo của User: *"đẩy cả S7 và GPM qua 1 cổng của R3G tạm đi"*.
  - Mạng nhà là mạng riêng tư của cá nhân User (đặt tại Đà Nẵng). Tuyệt đối KHÔNG PHẢI IP farm hay proxy farm.
  - Việc đưa tài khoản farm / Google Cloud Code chạy thẳng trên IP mạng nhà làm ô nhiễm IP cá nhân của User, làm lộ vị trí địa lý thật của User với Google Abuse Detection, và phá vỡ 100% nguyên tắc cách ly mạng của Farm.

## 2. Invariant Cấm Đoán Bắt Buộc (Hard Rules)
1. **CẤM TUYỆT ĐỐI TỰ Ý CHUYỂN PROFILE GPM SANG DIRECT:**
   - Dù proxy farm có chết, timeout, hay 502 Bad Gateway, CẤM TUYỆT ĐỐI tự ý xóa proxy hoặc chuyển profile về Direct mạng nhà nếu User KHÔNG RA LỆNH CỤ THỂ.
   - Thấy proxy chết -> Báo cáo BLOCKED / TIMEOUT kèm bằng chứng, chờ User chỉ đạo đổi sang proxy nào, tuyệt đối không được "chữa cháy" bằng mạng nhà.
2. **KỶ LUẬT ĐỒNG BỘ PROXY 1:1 GIỮA S7 VÀ GPM:**
   - Thiết bị S7 và Profile GPM của cùng một tài khoản BẮT BUỘC PHẢI DÙNG CHUNG MỘT CỔNG PROXY FARM (qua R3G hoặc MobiProxy).
   - Nếu điều phối S7 và GPM qua R3G, bắt buộc trỏ vào đúng cổng R3G (ví dụ `192.168.110.2:10009` hoặc `192.168.110.119:5141` theo đúng quy hoạch).
3. **PHẢN HỒI TRỰC DIỆN, THỪA NHẬN SAI PHẠM:**
   - Khi vi phạm chỉ đạo an toàn mạng, Coordinator phải dừng ngay lập tức mọi tác vụ trên profile, đóng trình duyệt, khôi phục proxy ban đầu và báo cáo trung thực hiện trạng, không được quanh co bao biện.
