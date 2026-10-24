# Cross-Host LAN Large-Payload Transfer & Execution Gates

## 1. Bối cảnh & Rào cản Kỹ thuật
Khi điều phối truyền dữ liệu dung lượng lớn (game, media, backup > 10GB) giữa máy chủ chính (Kibe `192.168.110.123`) và máy trạm Farm (Admin `192.168.110.119`):

1. **Rào cản xác thực SMB (Windows Network Share):**
   - Hai máy tính sử dụng hai tài khoản cục bộ Windows khác nhau (`Kibe` và `Admin`) không cùng domain.
   - Cổng 445 thông nhưng truy cập share (`\\192.168.110.123\TiktokShare`) bị Windows từ chối truy cập ẩn danh (`Access Denied / PermissionDenied`). Agent không được hỏi hoặc lưu mật khẩu Windows của User.

2. **Tường lửa Windows (Inbound Firewall) trên Kibe:**
   - Kibe Windows Firewall mặc định chặn các kết nối Inbound trên các port lạ (ví dụ port 28888).
   - Khi chạy HTTP server tạm thời trên Kibe ở cổng chưa khai báo firewall, máy Admin kết nối sang sẽ bị treo ngắt kết nối (TCP handshake timeout).
   - Các cổng Kibe đã được mở sẵn cho Farm Admin gồm: port `1905` (TikTok Dashboard) và `20129` (OmniRoute).

3. **Tam giác xung đột giữa các cơ chế bảo vệ:**
   - **Foreground Timeout Gate:** Giới hạn cứng `timeout <= 60s`. Với dữ liệu lớn (>40GB cần 15-20 phút), lệnh foreground chắc chắn bị ngắt giữa chừng.
   - **Background Console-Hide Policy:** Bắt buộc lệnh chạy ngầm phải ẩn cửa sổ console để không cướp chuột/focus của User đang làm việc.
   - **Terminal Allowlist Gate:** Chính sách Default-Deny chỉ cho phép một số lệnh định danh trước, chặn các trình bao ẩn cửa sổ tùy ý.
   - **Cronjob Resolver Parity:** Script chạy qua cron/watchdog cần được đồng bộ ở cả `~/.hermes/scripts/` và thư mục runtime cục bộ để tránh lỗi nhận diện đường dẫn.

---

## 2. Rủi ro Biến Động Dung Lượng Đĩa Admin (Disk Volatility)
- **Tốc độ ngốn đĩa của Farm:** Trình cào video tự động `video goc may 2` và bộ nhớ đệm luồng `GoogleDriveCache` trên Admin chạy liên tục 24/7.
- **Biến động thực tế:** Ổ `D:` Admin có thể tụt từ `91.8 GB free` xuống còn `33.7 GB free` chỉ sau vài giờ tải video.
- **Quy tắc an toàn bất biến:**
  - Tuyệt đối KHÔNG dùng số liệu dung lượng đĩa cũ trong phiên để quyết định copy file lớn.
  - Trước khi copy bất kỳ file/folder dung lượng lớn nào (như bản game PBE ~46 GB), BẮT BUỘC kiểm tra dung lượng trống live qua `admin_ssh.py` ngay tại thời điểm thực thi.
  - Nếu `FreeSpace < Dung_lượng_chép + 15 GB buffer`: BẮT BUỘC DỪNG NGAY để bảo toàn đệm tối thiểu cho Farm render, không được ép ghi làm tràn 100% đĩa gây sập Farm.

---

## 3. Kiến Trúc Khuyến Nghị Cho Tác Vụ Truyền File LAN
1. **Truyền streaming trực tiếp on-the-fly:**
   - Thay vì nén file `.tar` tạm thời ra đĩa Kibe (tốn thêm 92 GB dung lượng đệm), dùng `tarfile` streaming trực tiếp qua HTTP response `mode="w|"` và client Admin giải nén song song `mode="r|"`.
2. **Kênh truyền an toàn vượt tường lửa:**
   - Tận dụng SSH Reverse Port Forwarding (`ssh -R <port>:localhost:<port> admin-farm`) thông qua SSH key có sẵn thay vì mở port HTTP trực tiếp trên card mạng LAN vật lý.
3. **Thực thi qua Canonical Wrapper trong Allowlist:**
   - Đưa script truyền LAN vào thư mục canonical `D:/Taadaa/tools/` và khai báo trong allowlist hệ thống hoặc trigger qua Task Scheduler / Cronjob đã đồng bộ đầy đủ file.
