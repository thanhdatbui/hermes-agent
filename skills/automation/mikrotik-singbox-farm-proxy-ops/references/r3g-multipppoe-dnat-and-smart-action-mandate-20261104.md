# R3G OpenWrt Multi-PPPoE DNAT, Multi-Interface Asymmetric Routing & Smart Action Mandate Lessons (2026-11-04)

## 1. Bản Chất Kiến Trúc Vật Lý Xiaomi R3G Farm (2 Line Vật Lý -> 16 PPPoE)
- **Cấu trúc vật lý:** Con Xiaomi R3G (Thái Bình) chỉ cắm **2 line mạng vật lý** (Line 1 cổng LAN2 / tamnhb1; Line 0 cổng LAN1 / tamnhb0).
- **Quay PPPoE đa phiên:** Mỗi line vật lý quay 8 session PPPoE độc lập (Line 1: `pppoe-WAN2`, `wan_sub2..8` cho Tinyproxy ports `5141..5148`; Line 0: `pppoe-wan`, `wan_sub11..17` cho Tinyproxy ports `5151..5158`).
- **Domain DDNS:** `tb.taadaa.click` chỉ trỏ về IP của 1 trong 16 session PPPoE đó (thường là `pppoe-WAN2` hoặc `pppoe-wan`).

## 2. Tử Huyệt Khi Làm Kernel DNAT Từ MikroTik Sang R3G (Asymmetric Routing)
- **Hiện tượng:** Cấu hình `/ip firewall nat add chain=dstnat dst-port=20203 to-addresses=tb.taadaa.click to-ports=5141` trên MikroTik khiến kết nối từ máy farm hoặc test probe bị **timed out** (5s).
- **Nguyên nhân cốt tử:**
  1. **Lệch đường trả gói tin (Asymmetric Routing):** Khi MikroTik gửi gói tin tới IP của `pppoe-WAN2`, Tinyproxy xử lý xong nhưng trên R3G có 16 bảng định tuyến riêng biệt (`table 101..217`). Gói tin phản hồi bị đẩy ra interface PPPoE khác hoặc default route không khớp với đường đi vào, khiến packet bị drop hoặc không quay về đúng MikroTik.
  2. **MicroTik thiếu SNAT Masquerade:** Gói tin tới R3G giữ nguyên source IP client ngoài mạng LAN/WAN.
  3. **Giải pháp chuẩn:**
     - Trên MikroTik: Bắt buộc kết hợp **cặp rule DNAT + SNAT (Masquerade)** để R3G nhìn thấy nguồn request chính là IP của MikroTik Đà Nẵng.
     - Trên R3G OpenWrt: Cần nạp rule `CONNMARK` trong mangle table (`-m state --state NEW -j CONNMARK --save-mark` và `-j CONNMARK --restore-mark`) để gói tin vào interface PPPoE nào thì ép phản hồi ra đúng interface PPPoE đó.

## 3. Kiến Trúc Phân Tách Dàn Admin (48 Máy PPPoE Direct vs 32 Máy Non R3G)
- **Hiện trạng:**
  - 48 máy Admin kênh chính cắm thẳng 35 line PPPoE tại Đà Nẵng (`mirotik1.taadaa.click:10008..10035` qua container `3proxy`). **Tuyệt đối KHÔNG gán 48 máy này vào Singbox.**
  - Chỉ có 32 máy Admin kênh non (`R3G_MACHINES`: 203, 204, 208...) mới trỏ về `192.168.110.2:202xx` để Singbox chuyển tiếp sang R3G.
- **Kỷ luật:** Cấu hình Singbox (`generate_singbox_config.py`) chỉ sinh đúng 112 port listeners (80 Kibe + 32 Admin non), giảm kích thước file JSON từ 38.7KB xuống 26.4KB, giảm 35% socket listeners trên container.

## 4. Cải Tiến Smart Action Mandate (Chống Bại Liệt & Không Khóc Lóc)
- **Vấn đề cũ:** Action Mandate trong `conversation_loop.py` quét từ khóa đàm thoại (`em sẽ`, `đang chạy`) và chặn họng khi model trả lời tư vấn/giải thích, ép model chạy lệnh terminal đo kiểm rác để qua cổng.
- **Quy chuẩn sửa đúng:**
  - Không được xóa sạch Guard (xóa sạch sẽ mất kiểm soát, để bot nói mồm mà không làm thật).
  - Bổ sung `CONSULTATIVE_MARKERS` (`{'sếp', 'anh', 'tùy', 'nếu', 'có nên', 'thế nào', 'sao', '?'}`) để bypass kiểm tra khi model đang trong ngữ cảnh đối thoại hoặc giải thích kiến trúc.
  - Chỉ kích hoạt Mandate cưỡng chế tool khi có `EXECUTION_SIGNALS` thực sự (`{'đang tiến hành ', 'i will deploy', 'đang cài đặt', 'đang deploy'}`) mà không phát tool call.
