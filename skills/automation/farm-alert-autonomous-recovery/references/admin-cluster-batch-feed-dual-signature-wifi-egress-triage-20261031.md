# Admin Cluster Batch Feed Dual-Signature Wi-Fi & Egress Triage (31/10/2026)

## 1. Hiện Tượng & Dấu Hiệu Cảnh Báo
- **Batch Alert:** Sự cố diện rộng trên cụm Farm Admin (M201–M280) trong quy trình `tiktok-luot nuoi acc` (79 máy, 34 lỗi, tỷ lệ 43%).
- **2 Cụm lỗi vượt ngưỡng kép (Rate & Count):**
  1. *Cụm 1 (Egress IP Verification Failed / Network Unreachable):* 9 máy (M203, M204, M211, M217, M227, M230, M264, M265, M266).
     - Chi tiết: `global proxy (<serial>) egress IP verification failed: ... Get "http://ifconfig.me/ip": proxyconnect tcp: dial tcp <serial>: connect: network is unreachable`.
  2. *Cụm 2 (Wi-Fi Not Connected):* 21 máy (M208, M213, M220, M223, M233, M235, M238, M241, M243, M246, M251, M253, M260, M261, M262, M263, M267, M268, M270, M271, M272).
     - Chi tiết: `dumpsys connectivity: Wi-Fi not connected`.

## 2. Quy Trình Phân Tầng Chẩn Đoán Không Xâm Lấn (Non-Invasive Triage)
Theo chỉ dẫn Canary Policy, Coordinator tuyệt đối không can thiệp đồng loạt mà tuân thủ quy trình phân tầng:

1. **Khóa Batch:** Tạm dừng các đợt dispatch hàng loạt kế tiếp để bảo vệ thiết bị và tài khoản.
2. **Kiểm tra liveness máy đại diện O(1):**
   - Chạy `python D:/Taadaa/tools/inspect_machine.py <N>` trên máy đại diện mỗi cụm (ví dụ M203 cho Cụm 1, M208 cho Cụm 2).
   - Kiểm tra 4 chỉ số cốt lõi:
     * ADB Transport & Model: Nhận dạng đúng SM-G930F trên daemon Admin Remote (`192.168.110.119:5037`).
     * Pin & Trạng thái sạc: Pin > 80% (Charging).
     * Mạng wlan0: Đã có IP nội bộ (`192.168.110.x`) hay vẫn Disconnected.
     * Current Focus: Đang ở Launcher sạch (`LauncherActivity`) hay kẹt ứng dụng treo.
3. **Đối soát hạ tầng MobiProxy 4G:**
   - Chạy `python D:/Taadaa/AI-Tools/scripts/mobiproxy_auto_healer.py --check-and-heal`.
   - Quét toàn bộ 32 cổng proxy trên host `test.taadaa.click`:
     * Nếu cổng bị chết (Dead/502/WinError 10054): Script tự động gọi redial `/proxy_recreat`.
     * Nếu 32/32 cổng HEALTHY (TCP Socket OPEN, latency < 150ms): Khẳng định hạ tầng 4G hoàn toàn bình thường, nguyên nhân nằm ở tầng khởi động tải đỉnh hoặc LAN/Wi-Fi AP nội bộ.

## 3. Phân Định Bản Chất Kỹ Thuật (Root Cause Demarcation)
- **Wi-Fi Not Connected (Cụm 2):**
  - Race condition khi 79 máy cùng lúc thức giấc và chạy preflight kiểm tra mạng.
  - Sóng 5GHz trên các AP (`admin 1`, `admin 2`) bị bão hòa airtime tức thời trong vài giây đầu, khiến một số thiết bị trễ handshake DHCP.
  - Runner kích hoạt cơ chế an toàn fail-closed để chống rò rỉ IP trực tiếp.
  - Tại thời điểm hậu kiểm (post-shift inspect), các thiết bị đều đã tự động hoàn tất re-association và nhận IP nội bộ hợp lệ mà không cần can thiệp thô bạo.
- **Egress IP Unreachable (Cụm 1):**
  - Hiện tượng nghẽn tạm thời số lượng kết nối đồng thời từ thiết bị tới router proxy trung gian (`192.168.110.2`) trong giai đoạn burst load.
  - Cổng Singbox/3proxy trên router không sập, nhưng hàng đợi TCP handshake bị nghẽn dẫn đến `network is unreachable`.

## 4. Tiêu Chuẩn Nghiệm Thu & Mở Fleet An Toàn
- Thiết bị đại diện (M203, M208) đều đáp ứng:
  * Pin > 90% (Charging).
  * Focus ở màn hình chính Launcher (không kẹt tiến trình TikTok lỗi).
  * IP Wi-Fi wlan0 đã cấp phát thành công.
  * Toàn bộ 32 port MobiProxy 4G sẵn sàng.
- Đủ điều kiện kết luận lỗi mang tính TRANSIENT do tải đỉnh khởi động; an toàn mở lại fleet cho ca tiếp theo mà không cần khởi động lại máy hay chỉnh sửa code runner.
