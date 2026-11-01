# Kỷ Luật Điều Tra Sự Cố Router R3G Thái Bình & Bài Học CGNAT

## 1. Bản Chất Hiện Tượng CGNAT và Egress Public IP trên R3G
- **Line 0 (`tamnhb0` trên `lan1`):** Nhận 8 IP Public Viettel độc lập trực tiếp trên interface (`117.5.x`, `116.107.x`).
- **Line 1 (`tamnhb1` trên `lan2`):** Nhận dải IP nội bộ CGNAT `100.77.x.x` (hoặc `100.123.x.x`).
- **Bài học cốt tử từ thực tế lịch sử (Ngày 30/10 - Session 2001887 & 2001926):**
  - Mặc dù interface `pppoe-WAN2` nhận IP `100.77.143.90`, nhưng khi Tinyproxy **BIND CHÍNH XÁC VÀO TỪNG IP ĐÓ** (`Bind $ip_addr`) và gửi request ra Internet (`http://api.ipify.org`):
  - Phía ngoài Internet nhìn thấy mỗi cổng proxy nổ ra một IP Public Viettel riêng biệt (`117.5.152.204`, `117.5.153.102`, `117.5.153.105`...).
  - **NGUYÊN NHÂN GỐC KHIẾN HÔM NAY BỊ DỒN 1 IP VÀ TIMEOUT:**
    1. Trong script sinh cấu hình `/root/generate_all_proxies.sh` dòng bind bị comment out: `#Bind $ip_addr`. Khi không có directive `Bind`, toàn bộ 16 tiến trình proxy bị đẩy theo Default Route của OpenWrt đi ra ngoài bằng đúng 1 IP duy nhất (`117.5.152.203`).
    2. File `/etc/tinyproxy/instances/tp_*.conf` thiếu chỉ thị `Allow 0.0.0.0/0` dẫn đến khi gọi từ ngoài WAN vào bị lỗi `403 Access denied`.
    3. File DNS `/etc/resolv.conf` trên R3G bị Tailscale ghi đè trỏ vào `100.100.100.100`. Khi Tailscale rớt nhịp, Tinyproxy không phân giải được tên miền ra Internet và trả về lỗi `500 Unable to connect`. Sửa cứng lại `nameserver 8.8.8.8` giải quyết triệt để vấn đề này.

## 2. Kỷ Luật Điều Tra (Cấm Đoán Mò & Cấm Đổ Lỗi Ngoại Vi)
1. **Lời nhắc của User là kim chỉ nam:** Khi User khẳng định *"bữa trước fix được rồi"* hoặc *"cắm sang box khác chạy được"*, Coordinator bắt buộc phải dùng `session_search` lục lại đúng phiên cũ để xem lịch sử gõ lệnh và kết quả terminal thật, cấm lười biếng rồi đổ thừa cho nhà mạng.
2. **Kiểm tra chỉ thị Bind đầu tiên:** Khi gặp sự cố "toàn bộ proxy chung 1 IP" trên router OpenWrt đa WAN, việc đầu tiên phải kiểm tra là cấu hình instance proxy có đang mở `Bind <ip_addr>` của từng interface hay không.
3. **Bảo toàn mạng đang chạy:** Khi can thiệp Line 1 (`lan2`), tuyệt đối không được chạm vào Line 0 (`lan1`) đang giữ kết nối quản trị SSH và mạng nuôi phone farm.
4. **Kiểm chứng Math Assert:** Bắt buộc chạy script kiểm tra `len(set(unique_ips)) == 16` chứng minh 16/16 IP Public độc lập trước khi tuyên bố hoàn tất.

