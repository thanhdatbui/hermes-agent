---
name: farm-proxy-direct-leak-prevention
description: Kỷ luật cấm tuyệt đối tự ý fallback Direct mạng nhà khi proxy chết và quy trình xử lý lỗi kết nối GPM/S7.
version: 1.0.0
tags: [farm, proxy, direct-leak, fail-closed, gpm, s7]
---
# Farm Proxy Direct Leak Prevention & Fail-Closed Discipline

## 1. Bản chất sự cố & Cảnh báo nghiêm trọng
Khi vận hành tài khoản Farm (Gmail, TikTok, Google AI Pro, Codex, v.v.) trên GPMLogin hoặc thiết bị Android (Samsung S7):
- **Hành vi sai trái nghiêm trọng (Vi phạm nguyên tắc an toàn IP):** Khi proxy gán ban đầu gặp lỗi (ví dụ: timeout, 502 Bad Gateway), Coordinator tự ý gỡ bỏ proxy để chạy `Direct` (ăn thẳng vào mạng nhà FPT/Viettel của Operator) với lý do "thử xem màn hình tiếp theo là gì" hoặc "mạng nhà đang vào được".
- **Hậu quả khôn lường:**
  1. Lộ toàn bộ IP mạng nhà thật của Operator lên hệ thống phòng thủ của Google/TikTok.
  2. Phá vỡ fingerprint địa lý của tài khoản (đang nuôi ở Thái Bình / Proxy US tự nhiên nhảy sang IP mạng nhà cá nhân).
  3. Kích hoạt cờ bảo vệ hoặc án phạt tài khoản diện rộng.

## 2. Quy tắc cấm tuyệt đối (Hard Invariants)
1. **CẤM TUYỆT ĐỐI tự ý chuyển Profile GPM hoặc thiết bị sang Direct:**
   - Dù gặp bất kỳ lỗi gì (`502 Bad Gateway`, `Connection refused`, `Proxy timeout`), Coordinator **TUYỆT ĐỐI KHÔNG ĐƯỢC PHÉP** chuyển trường `raw_proxy` thành rỗng `""` hoặc bỏ proxy để chạy direct trên mạng nhà.
   - Khi proxy chết: **BẮT BUỘC DỪNG LẠI (FAIL-CLOSED)** và báo cáo trạng thái lỗi proxy thật cho Operator.
2. **Tuân thủ đúng chỉ đạo mapping proxy:**
   - Nếu Operator chỉ đạo: "dùng R3G gán cùng proxy S7", Coordinator BẮT BUỘC phải trỏ profile vào đúng cổng proxy tương ứng của S7/R3G (ví dụ: `192.168.110.2:20009` hoặc `192.168.110.2:10009`).
   - Nếu cổng đó không thông mạng (báo 502/timeout), phải báo cáo nguyên nhân tầng mạng (ví dụ: upstream tinyproxy trên R3G chưa chạy, box 4G chưa cấp WAN), TUYỆT ĐỐI KHÔNG ĐƯỢC tự chế đi đường tắt bằng mạng nhà.
3. **Phân biệt rạch ròi giữa Mạng LAN nội bộ vs Mạng Egress Internet:**
   - Dù PC Kibe và S7 cùng cắm chung mạng LAN `192.168.110.x`, nhưng luồng ra Internet của thiết bị farm bắt buộc phải đi qua cổng Proxy riêng được quy hoạch. Không được đánh đồng việc "cùng ping thấy nhau trong LAN" với việc "cho phép dùng chung IP mạng nhà ra ngoài".

## 3. Bẫy nhận thức TikTok Video Cache vs Mất Mạng Thật
- **Hiện tượng:** Khi proxy chết hoàn toàn, mở app TikTok lên vuốt vẫn thấy phát trôi 1–2 video đầu tiên.
- **Bản chất kỹ thuật:** Player của TikTok (`TTNet / ExoPlayer`) tự động nạp đệm (buffer/disk cache) 2–4 video tiếp theo vào RAM/Flash. Việc xem được 1–2 clip cũ không chứng minh máy có mạng ra ngoài.
- **Tiêu chuẩn kiểm chứng mất mạng (Ground Truth Fail-Closed):**
  1. **Tab Cửa hàng (Shop):** Chuyển sang tab Cửa hàng hoặc gõ tìm kiếm sản phẩm. Nếu toàn bộ hiển thị khung xương xám rỗng (Skeleton Loading Cards), không tải được giá tiền hay hình ảnh sản phẩm -> Mạng đã bị cắt đứt 100%.
  2. **Thanh trạng thái Wi-Fi:** Kiểm tra dấu chấm than (!) báo mất kết nối Internet ngoại vi.
  3. **Kiểm tra Cold-Boot:** Chạy `am force-stop com.ss.android.ugc.trill` rồi mở lại mới toanh. Màn hình video trống rỗng/xoay loading, socket kẹt ở trạng thái `SYN_SENT`.

## 4. Kiến trúc 3 tầng bảo vệ chống chạy phá khi Proxy rớt
1. **Tầng 1 (Preflight Gate Runner):** `vpn_preflight.py` kiểm tra kết nối proxy/socket trước khi chạy. Nếu proxy rớt -> trả về `blocked-vichanger-vpn` / `preflight-network-blocked` và dừng ca ngay, cấm mở app.
2. **Tầng 2 (UI Classifier & Safety):** `classifier.py` và `safety.py` phát hiện marker lỗi mạng ("Không có kết nối Internet", "Thử lại", "Network error") -> trả về `screen="manual-needed:network"`, tự động ngắt phiên và đóng app về Home, cấm vuốt mò.
3. **Tầng 3 (Tường lửa MikroTik):**
   - **RAW Prerouting:** Rule `*5` DROP UDP 443 (QUIC) triệt tiêu HTTP/3 bypass lách proxy.
   - **Mangle:** Rule Bypass Mangle `*174`, `*175` ở vị trí Top #0/#1 ngăn gán cờ `WAN8..WAN35` làm văng gói tin direct.
   - **Filter Forward:** Rule `*D` (`KILLSWITCH_BLOCK_FARM_DIRECT_WAN`) ở vị trí [0] tiêu diệt toàn bộ gói direct ra WAN.
   - **Lưu ý Container 3proxy:** Khi siết Filter Forward, BẮT BUỘC phải có rule `chain=forward src-address=192.168.110.0/24 dst-address=172.16.0.0/16 action=accept` (Rule `*18`) để dàn máy Admin chạy dải cổng `10001-10035` thông kết nối vào container 3proxy.
   - **Bẫy Ngầm IPv6 (Bắt buộc kiểm tra):** Nếu RouterOS bật IPv6 (`disable-ipv6: false`) và có Router Advertisement (ND RA), các app hiện đại (TikTok, Google) sẽ tự động tạo kết nối IPv6 bypass toàn bộ tường lửa IPv4. BẮT BUỘC phải nạp rule drop forward trong `/ipv6/firewall/filter`:
     ```routeros
     /ipv6/firewall/filter
     add chain=forward action=drop comment="KILLSWITCH_BLOCK_ALL_IPV6_FORWARD"
     ```
   - **Rule hứng đáy Singbox (`*30E`):** Nằm ở cuối bảng NAT (Index [71]) gom dải `20001-20280` về `172.17.0.2`. Hoạt động theo cơ chế First-match terminating: Khi các rule Kernel DNAT MobiProxy/R3G (Index 1..70) hoạt động tốt, rule `*30E` ngủ yên (0% tải CPU). Nó chỉ kích hoạt khi có port lệch hoặc unmapped rơi xuống đáy bảng NAT để tránh packet văng ra ngoài.
