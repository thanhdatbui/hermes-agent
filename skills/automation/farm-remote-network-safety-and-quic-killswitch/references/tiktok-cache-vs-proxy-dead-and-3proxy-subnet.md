# Tri Thức Đối Soát Hiện Trường & Tường Lửa Fail-Closed (TikTok Cache vs Proxy Dead)

## 1. Cạm Bẫy Ảo Giác Video Buffer Cache Nội Bộ Của TikTok
Khi proxy chết hoặc bị cố tình ngắt kết nối để kiểm tra cơ chế Fail-Closed:
- **Hiện tượng:** Người vận hành hoặc Agent mở app TikTok và vẫn thấy lướt được 1–2 video đầu tiên.
- **Bản chất kỹ thuật:** Player của TikTok (`TTNet / ExoPlayer`) tự động nạp sẵn (buffer/cache) các phân đoạn video tiếp theo vào RAM/Flash cache từ phiên chạy trước.
- **Tiêu chuẩn kiểm chứng sự thật hiện trường (Ground Truth Inspection):**
  1. Không kết luận máy "vẫn có mạng" chỉ vì thấy 1–2 video đầu chạy.
  2. Bắt buộc chuyển sang tab **Cửa hàng (TikTok Shop)** hoặc gõ thanh **Tìm kiếm**:
     - Nếu có mạng thật: Sản phẩm, giá tiền, ảnh thumbnail sẽ bung ra ngay lập tức.
     - Nếu mạng đã bị chặn thành công (Fail-Closed): Toàn bộ biến thành các ô vuông xám rỗng (**Skeleton Loading Cards**), thanh tìm kiếm rỗng không ra kết quả.
  3. Kiểm tra thanh trạng thái Wi-Fi: Biểu tượng Wi-Fi xuất hiện dấu chấm than nhỏ hoặc không nhận được ping ngoại vi.
  4. Kiểm tra socket Kernel máy thật: Bằng lệnh `/proc/net/tcp6`, socket trỏ tới proxy nội bộ kẹt cứng ở trạng thái `SYN_SENT` (mã `02`), hoàn toàn không có socket `ESTABLISHED` nào kết nối tới máy chủ CDN ngoài.

## 2. Bẫy Tách Subnet 3proxy Container (10001–10035) vs R3G DNAT (20201–20280)
- Dàn máy Admin phân hóa 2 cơ chế proxy:
  - Máy như M204 dùng cổng `20204` trỏ thẳng qua Kernel DNAT tới router R3G Thái Bình.
  - Các máy như M205, M207 dùng cụm cổng `10001–10035` trỏ tới container 3proxy nội bộ (`172.16.0.0/16` trên MikroTik).
- **Lỗ hổng chặn nhầm:** Khi siết chặt tường lửa bảng `Filter FORWARD` và vô hiệu hóa rule allow rộng `*10`, nếu chỉ mở rule cho phép dải IP proxy ngoài mà quên mở subnet container nội bộ `172.16.0.0/16`, toàn bộ các máy dùng port 10001–10035 sẽ bị rớt mạng oan.
- **Quy tắc bắt buộc trên MikroTik Filter FORWARD:**
  ```routeros
  /ip firewall filter
  add chain=forward action=accept src-address=192.168.110.0/24 dst-address=172.16.0.0/16 comment="ALLOW_FARM_TO_3PROXY_CONTAINER"
  ```
  Rule này bắt buộc phải nằm trên các rule Drop để đảm bảo lưu lượng nội bộ giữa farm và container proxy không bị ngắt.
