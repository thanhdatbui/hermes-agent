# MobiProxy 38 Ports Full DNAT Offload & Conntrack Tuning Protocol (2026-11-05)

## 1. Ngữ cảnh & Bài toán Tải CPU trên MikroTik RouterOS x86
- **Triệu chứng:** CPU MikroTik x86_64 chạm ngưỡng 95% - 98% (cả 4 core quá tải), card mạng ảo `veth-singbox` gánh 66.000 - 127.000 packets/giây (pps) và 122 Mbps lưu lượng video TikTok từ 160 điện thoại Samsung S7.
- **Nguyên nhân cốt lõi:**
  1. Máy ảo Docker Container chạy L7 Singbox trên RouterOS bị nghẽn chi phí chuyển ngữ cảnh (context switching) và bóc tách gói tin phần mềm.
  2. Bảng theo dõi kết nối Conntrack tích tụ kỷ lục 102.864 kết nối do mặc định `tcp-established-timeout: 1d` (24 tiếng), khiến các luồng video cũ của app TikTok không gửi FIN/RST bị giữ lại làm router phải liên tục quét polling.

## 2. Quy trình Tự Động Hóa Mở Khóa No-Auth 38 Port MobiProxy (Web v3.0.67)
Nút "Áp dụng cho tất cả proxy" ở trang `#security` chỉ là UI stub/lỗi backend không reload tiến trình 3proxy. Bắt buộc phải duyệt từng hàng trên bảng danh sách proxy `#proxies`:

### A. Cơ chế tương tác HTML5 Dialog Form
1. Hàng table chứa thẻ `<details class="action-menu"><summary aria-label="Tác vụ proxyXX">•••</summary>`.
2. Mở details: `details.open = true` hoặc click `summary`.
3. Click button mở modal: `button[data-action="proxy-access"]`.
4. Modal mở ra là một thẻ `<form method="dialog" action="index.php#proxies">`.
5. Đổi select mode: `visibleSelect.value = 'none'` rồi phát sự kiện `change`.
6. Submit form bắt buộc click đúng nút: `document.querySelector('#access-save').click()`.
7. Kiểm tra trạng thái: Cột `XÁC THỰC` (cột thứ 5 trong row) phải chuyển từ `strong` sang nhãn xám `none`.

### B. Kiểm thử xác thực No-Auth
Gửi HTTP request trực tiếp vào từng port (ví dụ 5101..5138):
- Thất bại: HTTP Error 407 (Proxy Authentication Required) -> Chưa đổi thành công hoặc chưa reload.
- Thành công: HTTP 200 OK trả về đúng IP Public Viettel của SIM tương ứng với latency < 0.6s.

## 3. Cấu hình MikroTik Kernel DNAT cho Dàn Máy Kibe (M1..M38)
1. Lấy IP Public hiện tại của MobiProxy (`test.taadaa.click`), ví dụ `117.5.190.84`.
2. Nạp hàng loạt 38 rule DNAT cho từng port:
   - Chain: `dstnat`
   - Action: `dst-nat`
   - Protocol: `tcp`
   - Dst-port: `20001` .. `20038`
   - To-addresses: `<IP_MOBIPROXY>`
   - To-ports: `5101` .. `5138`
   - Comment: `DNAT_KIBE_M{i}_TO_MOBIPROXY_{port}`
3. Di chuyển toàn bộ các rule DNAT này lên đứng trước rule Singbox `*30E` (`destination=*30E`).
4. Gói tin từ điện thoại S7 được chip phần cứng MikroTik chuyển tiếp thẳng ở tốc độ dây cáp (wire-speed), hoàn toàn bypass máy ảo Docker Singbox.

## 4. Tối ưu Thông Số Conntrack Timeouts trên MikroTik
Thực hiện nạp qua REST API hoặc Terminal để dọn bão kết nối ma và duy trì bảng kết nối sạch:
```routeros
/ip firewall connection tracking
set tcp-established-timeout=1h
set generic-timeout=2m
set udp-stream-timeout=1m
set udp-timeout=10s
```
- Khi hạ `tcp-established` từ 24h xuống 1h, các kết nối rác tự động bị tiêu hủy sau 60 phút không có gói tin.
- Các luồng cày video TikTok đang chạy vẫn được bảo vệ tuyệt đối do mỗi gói tin đi qua đều tự động reset lại timer.

## 5. Cơ Chế Khóa Cơ Học Chống Lộ IP Gốc (Fail-Closed Killswitch)
- **Tường Lửa MikroTik (Filter Rules):**
  - `*D` (`KILLSWITCH_BLOCK_FARM_DIRECT_WAN`): `chain=forward src-address=192.168.10.0/24 action=drop` cấm tiệt điện thoại S7 đi thẳng Internet Đà Nẵng.
  - `*8` (`KILLSWITCH_FARM_DNS_UDP`): Drop toàn bộ DNS UDP 53 trực tiếp ra ngoài.
  - `*9` (`KILLSWITCH_FARM_QUIC_UDP`): Drop toàn bộ UDP 443 (chặn cơ chế tự cứu mạng Cronet/QUIC của TikTok).
- **Trạng Thái Khi Proxy Hỏng:**
  - S7 gửi request tới `200XX` bị drop/timeout.
  - Android hiện dấu chấm than trên icon Wi-Fi, app báo mất mạng an toàn, không bao giờ lộ IP Đà Nẵng.

## 6. Kết Quả Đo Kiểm Thực Tế Đạt Được
- **Tải CPU MikroTik x86:** Rơi thẳng từ **97.6% xuống còn 0.4% - 1.8%** (gần như 0%).
- **Lưu lượng veth-singbox:** Giảm từ **127.114 pps xuống còn 284 pps**.
- **Độ trễ Proxy:** Giảm từ 1.5s xuống còn **0.44s - 0.54s**.
- **Trạng thái S7 qua ADB (`dumpsys connectivity`):** `Capabilities: INTERNET & VALIDATED & FOREGROUND`, sóng Wi-Fi căng đét, không có dấu chấm than, hoạt động ổn định 100%.
- **Kiểm tra IP trực tiếp trên S7:** Truy cập `icanhazip.com`, `httpbin.org/ip`, và `whoer.net` đều trả về đúng 100% IP Public của SIM 4G Thái Bình (`117.5.190.84`), điểm ẩn danh 100% Anonymity.
