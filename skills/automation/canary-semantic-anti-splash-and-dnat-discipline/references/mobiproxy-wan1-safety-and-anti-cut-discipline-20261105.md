# Kỷ Luật Bất Biến Vận Hành MobiProxy: Cấm Ngắt / Xóa Kết Nối WAN 1 & Cấm Chạy Mù Lệnh Gỡ Mạng (2026-11-05)

## 1. Bản Chất Sự Cố Nghiêm Trọng (RCA)
- **Bối cảnh:** Cần quy hoạch lại số kết nối trên 4 cổng LAN của box MobiProxy (`test.taadaa.click`) từ cấu hình cũ (`lan1=10, lan2=10, lan3=10, lan4=8`) sang cấu hình phẳng chuẩn (`lan1=8, lan2=8, lan3=8, lan4=8`).
- **Hành vi sai lầm:**
  Sau khi gọi `network.plan`, Agent chạy vòng lặp tự động xóa toàn bộ cài đặt cũ:
  `for lan in [4, 3, 2, 1]: network.delete_lan(lan)`.
- **Hậu quả thảm khốc:**
  * Cổng `LAN 1` (`proxy01`) trên box MobiProxy chính là **đường cấp IP Internet WAN (Default Route) và cập nhật DDNS Cloudflare**.
  * Khi xóa LAN 1, kết nối PPPoE bị hạ xuống (`down`). Box lập tức mất kết nối Internet ra ngoài.
  * Vì mất Internet, box không thể nhận thêm bất kỳ lệnh API nào tiếp theo (`network.install` bị treo).
  * Con box bị cô lập hoàn toàn từ xa, buộc con người phải can thiệp vật lý tại hiện trường (vi phạm nghiêm trọng nguyên tắc cấm làm phiền nhân sự tại trạm).

## 2. Các Bất Biến Cấm Tuyệt Đối (Hard Invariants)

### INVARIANT 1: CỔNG WAN 1 / PPPOE-PROXY01 LÀ VÙNG CẤM BẤT KHẢ XÂM PHẠM
- **CẤM TUYỆT ĐỐI** gọi API `network.delete_lan` hoặc ngắt kết nối đối với `LAN 1` từ xa qua mạng Internet WAN.
- Trong mọi kịch bản re-install hoặc re-plan:
  * Tuyệt đối KHÔNG xóa LAN 1 trước khi có đường truyền thay thế.
  * Khi cần đổi số kết nối hoặc tài khoản: Gọi trực tiếp `network.install` với tham số mới (`lan=1, count=8...`) để hệ thống tự động ghi đè in-place, **CẤM dùng `delete_lan` xóa trắng**.

### INVARIANT 2: NGUYÊN TẮC OUT-OF-BAND & KHÔNG PHỤ THUỘC MỘT ĐƯỜNG TRUYỀN
- Nếu một thiết bị mạng chỉ có duy nhất 1 IP WAN public để quản trị từ xa, mọi hành động ngắt mạng trên interface quản trị đó đều là **hành vi tự sát**.
- Bắt buộc kiểm tra: Có đường truy cập dự phòng (như Tailscale, SSH qua router phụ, hoặc IP LAN) hay không. Nếu KHÔNG có đường dự phòng ➔ **DỪNG LẠI NGAY LẬP TỨC**, cấm can thiệp vào interface mạng chính.

### INVARIANT 3: CẤM TỰ ĐỘNG HÓA VÒNG LẶP HẠ TẦNG (NO BLIND INFRA LOOPS)
- Cấm viết script vòng lặp `for lan in [4, 3, 2, 1]: delete...` trên các thiết bị mạng phần cứng.
- Mọi thao tác đổi cấu hình mạng phải thực hiện từng bước tuần tự (step-by-step), kiểm tra ping/health check sau mỗi bước, nếu thấy rủi ro mất kết nối phải dừng lại ngay.

## 3. Kiến Trúc Cổng & Tài Khoản Gốc MobiProxy (Lưu Trữ Khẩn Cấp)
- **Tài khoản PPPoE 4 LAN:**
  * LAN 1: `hyn_gftth_datlp3` / `2TJFUO`
  * LAN 2: `hyn_gftth_datlp2` / `KG6YK5`
  * LAN 3: `hyn_gftth_datlp2` / `KG6YK5`
  * LAN 4: `hyn_gftth_datlp0` / `U6C7JB`
- **Mật khẩu quản trị web:** `N0spam@23102025`
- **Quy tắc phân bổ an toàn:**
  Gửi `network.plan` với `counts: {1: 8, 2: 8, 3: 8, 4: 8}`, sau đó gọi `network.install` từng LAN riêng lẻ, bắt đầu từ `LAN 2 -> LAN 3 -> LAN 4`. Đối với `LAN 1`, chỉ thực hiện cài đè in-place, không bao giờ delete.
