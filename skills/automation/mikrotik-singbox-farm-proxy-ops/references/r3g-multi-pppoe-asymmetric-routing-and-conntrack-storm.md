# R3G Multi-PPPoE Asymmetric Routing, Conntrack Zombie Storm & Action Mandate Governance (Session Learnings 2026-11-04)

## 1. R3G Multi-PPPoE (16 Sessions trên 2 Line) & Asymmetric Routing Pitfall
- **Hiện trường vật lý:** Xiaomi R3G (ImmortalWrt 21.02) cắm đúng 2 line vật lý (LAN1, LAN2), mỗi line quay đa phiên 8 session PPPoE (tổng 16 interfaces: `pppoe-WAN2`, `wan_sub2..8` trên Line 1; `pppoe-wan`, `wan_sub11..17` trên Line 0).
- **Lỗi Asymmetric Routing khi Kernel DNAT:**
  - Khi router khác (MikroTik Đà Nẵng) gửi gói tin TCP đến IP WAN của R3G (ví dụ `tb.taadaa.click:5141`), gói tin chui vào qua interface `pppoe-WAN2`.
  - Tiến trình `tinyproxy` trên R3G xử lý, nhưng khi phản hồi, do R3G có tới 16 bảng định tuyến riêng (`table 101..217`), kernel đẩy gói tin trả về qua bảng default/interface PPPoE khác (`pppoe-wan_subX`).
  - Gói tin phản hồi không quay về lại IP nguồn đúng đường đi $\rightarrow$ TCP Handshake gãy, kết nối bị `timed out`.
- **Giải pháp:** Cần dùng `CONNMARK` trong iptables mangle (`--save-mark` ở PREROUTING và `--restore-mark` ở OUTPUT) để ép gói tin vào bằng interface nào thì bắt buộc trả lời ra đúng interface đó.

## 2. MobiProxy Web v3.0.67 "Áp Dụng Cho Tất Cả Proxy" UI Dummy
- **Hiện tượng:** Trên web `test.taadaa.click/index.php#security`, combobox chọn `Không xác thực` và bấm nút `Áp dụng cho tất cả proxy`, nhưng sau đó test curl vẫn bị `HTTP Error 407: Proxy Authentication Required`.
- **Bản chất:** Nút bấm hàng loạt trên giao diện web này là UI Dummy / chưa nối backend thực sự. Các port `5101..5138` vẫn giữ nhãn `strong` trong cấu hình 3proxy gốc. Muốn bỏ auth bắt buộc phải sửa template 3proxy trực tiếp trên box. Do đó các client không hỗ trợ User/Pass (như DNAT thuần) không thể kết nối trực tiếp nếu box chưa nhả auth thật sự.

## 3. Conntrack Zombie Connections Storm do Default Timeout 1d
- **Hiện tượng:** 160 phone Samsung S7 sau khi kết thúc ca nuôi acc đã đóng app TikTok về màn hình Home Launcher, nhưng CPU MikroTik 4 core vẫn kẹt ở 93%–97%, và đo được lưu lượng `veth-singbox` lên tới 66.000–127.000 pps!
- **Nguyên nhân:** Bảng `/ip firewall connection tracking` tích tụ hơn **102.864 kết nối ma** do thông số `tcp-established-timeout = 1d` (24 giờ). Gói tin stream video/CDN của TikTok bị đóng dở dang không gửi TCP FIN/RST, router tiếp tục giữ và polling hàng vạn kết nối suốt 24h.
- **Khắc phục chuẩn công nghiệp:**
  - `tcp-established-timeout`: giảm từ `1d` $\rightarrow$ `1h` (hoặc `30m`).
  - `generic-timeout`: giảm từ `10m` $\rightarrow$ `2m`.
  - `udp-stream-timeout`: giảm từ `3m` $\rightarrow$ `1m`.
  - `udp-timeout`: giảm từ `30s` $\rightarrow$ `10s`.
  - Lập tức thu hồi hàng vạn kết nối rác, không làm ảnh hưởng đến các ca nuôi kế tiếp (vì kết nối thật luôn có keep-alive tự reset timer).

## 4. Mechanical Guidance Action Mandate & Consultative Intent Decoupling
- **Hiện tượng:** Khi Agent trả lời câu hỏi tư vấn, giải thích kiến trúc hoặc chất vấn của User mà có chứa các cụm từ đàm thoại (`"em sẽ"`, `"đang chạy"`, `"để em"`), Gate Action Mandate tưởng nhầm là "hứa thi công hệ thống mà không gọi tool", dẫn đến việc chặn họng câu trả lời, ép Agent phát lệnh terminal đo kiểm rác rưởi để "làm vé qua cổng", làm mất sạch câu trả lời thực sự khiến User ức chế.
- **Khắc phục:**
  - Phân tách rõ rệt giữa **Execution Intent** và **Consultative Intent**.
  - Nếu câu trả lời có chứa các từ khóa đối thoại/trưng cầu ý kiến (`'sếp'`, `'anh'`, `'tùy'`, `'?'`) $\rightarrow$ Phải tự động BYPASS Action Mandate.
  - Mandate chỉ được phép kích hoạt khi ngữ cảnh là lệnh thi công thực sự (`fix`, `deploy`, `cài đặt`) mà không có tool call.
