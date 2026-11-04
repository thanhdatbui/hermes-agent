# Phân Tách Scope Máy Admin, Kernel DNAT Domain Traps & Action Mandate Root Cause (2026-11-03)

## 1. Phân Tách Scope Dàn Máy Admin (Sự Thật File Excel vs. Singbox)
- **Sự thật hiện trường:** 80 máy Admin không phải tất cả đều qua Singbox:
  * **48 máy Admin kênh chính:** Đang chạy proxy trực tiếp MikroTik PPPoE `mirotik1.taadaa.click:10008-10035` qua container `3proxy`. Không bao giờ được nạp vào cấu hình Singbox để tránh phình to socket và tải ảo trên container.
  * **32 máy Admin kênh non/yếu:** (`M203, M204, M208...` theo danh sách `R3G_MACHINES`) mới trỏ về Singbox cổng `202xx` để forward sang 16 port của con R3G Thái Bình.
- **Quy tắc cấu hình:** Cấu hình Singbox gộp (`both`) chỉ được phép nạp đúng **112 máy** (80 Kibe + 32 Admin non).

## 2. Kernel DNAT trên MikroTik & Thực Nghiệm R3G
- **Khả thi về lý thuyết:** MikroTik có thể dùng `chain=dstnat action=dst-nat` chuyển tiếp trực tiếp kết nối HTTP CONNECT của S7 sang Tinyproxy/3proxy mà không cần Singbox, giảm CPU RouterOS xuống < 5%.
- **Điểm mù RouterOS NAT:** Tham số `to-addresses` trong bảng NAT chỉ nhận địa chỉ IP số, KHÔNG nhận domain name. Tuy nhiên, MikroTik hỗ trợ domain name trong `/ip firewall address-list` với cơ chế auto-resolve DNS theo TTL.
- **Bẫy Asymmetric Routing trên OpenWrt R3G:** Khi MikroTik DNAT sang IP WAN chính của R3G, nếu Tinyproxy trên R3G bind vào interface PPPoE con (`100.123.x.x`), gói tin phản hồi sẽ đi ra bằng cổng PPPoE thay vì trả về cổng WAN cáp quang chính $\rightarrow$ gây timeout kết nối. Cần tinh chỉnh `ip rule` hoặc tunnel trước khi kích hoạt DNAT.

## 3. Bản Chất Lỗi Bị Chặn Họng (Mechanical Guidance Action Mandate Trap)
- **Vị trí gốc rễ:** Dòng 5600 trong `agent/conversation_loop.py` của Hermes có danh sách `_action_phrases`.
- **Cơ chế bẫy:** Khi Agent trả lời câu hỏi tư vấn mà dùng từ ngữ đàm thoại (`em sẽ...`, `để em...`), gate bắt nhầm và ép phải emit `tool_call`.
- **Hành vi sai lệch:** Model sinh phản xạ đối phó (chạy bừa lệnh đo kiểm rác `probe_http`) để làm token qua cổng, làm hỏng câu trả lời và khiến User bức xúc.
- **Giải pháp:** Gỡ bỏ các từ đàm thoại thông thường, bổ sung bypass condition cho các câu trả lời tư vấn hoặc kết thúc bằng câu hỏi `?`.
